"""Phase 4 pipeline: relevant corpus -> extract -> evidence packets + embeddings.

Orchestrates behaviour extraction, barrier extraction, unmet-need inference,
evidence packet assembly, and embedding generation.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from .barrier import RuleBarrierExtractor
from .behaviour import RuleBehaviourExtractor
from .evidence import EvidencePacketBuilder
from .embeddings import EmbeddingStore, Embedder
from .llm import LLMExtractor
from .storage import Storage
from .unmet_needs import UnmetNeedInferrer


class Pipeline:
    def __init__(self, storage: Storage, cfg: dict[str, Any], run_id: str | None = None):
        self.storage = storage
        self.cfg = cfg
        self.version = cfg.get("extractor_version", "extraction-v1.0")
        self.run_id = run_id or f"p4_{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
        self.behaviour_extractor = RuleBehaviourExtractor(cfg)
        self.barrier_extractor = RuleBarrierExtractor(cfg)
        self.unmet_inferrer = UnmetNeedInferrer(cfg)
        self.packet_builder = EvidencePacketBuilder(cfg, version=self.version)
        self.llm = LLMExtractor(cfg)
        self.embedder = Embedder(cfg)
        self.embed_store: EmbeddingStore | None = None
        self.per_source: dict[str, dict[str, int]] = {}

    def run(self, records: Iterator[dict[str, Any]]) -> dict[str, Any]:
        self.storage.start_run(self.run_id)
        self.storage.reset()

        all_records: list[dict[str, Any]] = []
        for rec in records:
            all_records.append(rec)

        texts = [str(r.get("clean_text") or r.get("text") or "") for r in all_records]
        embeddings = self.embedder.fit_transform(texts) if texts else []

        self.embed_store = EmbeddingStore(self.storage.out_dir)
        self.embed_store.reset()

        per_source: dict[str, dict[str, int]] = {}
        total = len(all_records)
        extracted = 0
        llm_used = 0

        for i, rec in enumerate(all_records):
            source = str(rec.get("source", "unknown"))
            track = per_source.setdefault(source, {"input": 0, "extracted": 0, "llm": 0})
            track["input"] += 1

            text = str(rec.get("clean_text") or rec.get("text") or "")
            extraction = self._extract(text, source)
            if extraction:
                extracted += 1
                track["extracted"] += 1
                if extraction.pop("_llm_used", False):
                    track["llm"] += 1
                    llm_used += 1

                pkt = self.packet_builder.build(rec, extraction)
                self.storage.save_packet(pkt)

                self.embed_store.save(
                    rec.get("id", f"rec-{i}"),
                    embeddings[i] if i < len(embeddings) else [],
                    metadata={"source": source, "behaviours": extraction.get("behaviours", [])},
                )

        self.per_source = per_source
        summary = (
            f"total={total} extracted={extracted} llm_used={llm_used} "
            f"offset_mismatches={self.packet_builder.offset_mismatches}"
        )
        self.storage.finish_run(self.run_id, per_source, summary)
        return {
            "run_id": self.run_id,
            "total_input": total,
            "extracted": extracted,
            "llm_used": llm_used,
            "offset_mismatches": self.packet_builder.offset_mismatches,
            "per_source": per_source,
            "extractor_version": self.version,
            "llm_available": self.llm.available(),
            "embedding_dim": self.embedder.embedding_dim(),
        }

    def _extract(self, text: str, source: str) -> dict[str, Any] | None:
        if not text or len(text) < 5:
            return None
        llm_result = self.llm.extract(text) if self.llm.available() else None
        if llm_result:
            llm_result["_llm_used"] = True
            return llm_result
        beh = self.behaviour_extractor.extract(text)
        bar = self.barrier_extractor.extract(text)
        needs = self.unmet_inferrer.infer(text, bar["barriers"])
        return {
            **beh, **bar,
            "unmet_needs": needs,
            "confidence": {**beh.get("behaviour_confidence", {}), **bar.get("barrier_confidence", {})},
            "_llm_used": False,
        }
