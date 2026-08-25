"""Phase 6 pipeline: evidence DB -> opportunity scoring -> interview questions -> discovery report."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from .evidence_db import EvidenceDB
from .interview import generate_questions
from .report import render_discovery_report
from .scorer import rank_opportunities, score_opportunity
from .storage import Storage


class Pipeline:
    def __init__(self, storage: Storage, evidence_db: EvidenceDB, cfg: dict[str, Any],
                 run_id: str | None = None):
        self.storage = storage
        self.evidence_db = evidence_db
        self.cfg = cfg
        self.version = cfg.get("extractor_version", "opportunity-v1.0")
        self.run_id = run_id or f"p6_{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"

    def run(self, packets: Iterator[dict[str, Any]], quantification: dict[str, Any]) -> dict[str, Any]:
        self.storage.start_run(self.run_id)

        all_packets = list(packets)
        weights = self.cfg.get("scoring", {}).get("weights", {})

        # group packets by theme cluster
        themes: dict[str, list[dict[str, Any]]] = {}
        for pkt in all_packets:
            key = pkt.get("cluster_label", "unknown")
            themes.setdefault(key, []).append(pkt)

        # score each theme as an opportunity
        opportunities = []
        total = len(all_packets)
        for theme_label, theme_packets in themes.items():
            all_behs = []
            all_bars = []
            for p in theme_packets:
                all_behs.extend(p.get("behaviours", []))
                all_bars.extend(p.get("barriers", []))

            unique_behs = list(dict.fromkeys(all_behs))
            unique_bars = list(dict.fromkeys(all_bars))

            # evidence strength: high if >= 3 packets, medium if >= 2
            n = len(theme_packets)
            ev_strength = "high" if n >= 3 else ("medium" if n >= 2 else "low")

            # segment concentration: fraction of total
            seg_conc = n / max(total, 1)

            opp = score_opportunity(
                theme_label=theme_label,
                behaviours=unique_behs,
                barriers=unique_bars,
                frequency=n,
                total_packets=total,
                segment_concentration=seg_conc,
                evidence_strength=ev_strength,
                weights=weights,
            )
            opportunities.append(opp)

        ranked = rank_opportunities(opportunities)

        # generate interview questions + save to evidence DB
        for opp in ranked:
            questions = generate_questions(opp)
            opp["interview_questions"] = questions
            theme_packets = themes.get(opp["title"], [])
            self.evidence_db.save_opportunity(opp, theme_packets, questions)
            self.storage.save_opportunity(opp)

        # generate discovery report
        quant_path = self.storage.out_dir / "quantification.json"
        quant = quantification
        if quant_path.exists():
            quant = json.loads(quant_path.read_text(encoding="utf-8"))

        report = render_discovery_report(ranked, self.evidence_db.get_opportunities(), quant, self.cfg)
        (self.storage.out_dir / "discovery_report.md").write_text(report, encoding="utf-8")

        summary = (
            f"opportunities={len(ranked)} evidence_links={self.evidence_db.count_evidence_links()} "
            f"top_opportunity={ranked[0]['title'] if ranked else 'none'}"
        )
        self.storage.finish_run(self.run_id, {"ranked": len(ranked)}, summary)
        return {
            "run_id": self.run_id,
            "total_packets": total,
            "opportunities": len(ranked),
            "ranked": ranked,
            "report_path": str(self.storage.out_dir / "discovery_report.md"),
        }
