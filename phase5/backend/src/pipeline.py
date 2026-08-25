"""Phase 5 pipeline: evidence packets -> segmentation -> clustering -> quantification."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from .clustering import cluster_packets
from .quantification import quantify
from .segmentation import assign_segments
from .storage import Storage


class Pipeline:
    def __init__(self, storage: Storage, cfg: dict[str, Any], run_id: str | None = None):
        self.storage = storage
        self.cfg = cfg
        self.version = cfg.get("extractor_version", "segmentation-v1.0")
        self.run_id = run_id or f"p5_{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"

    def run(self, packets: Iterator[dict[str, Any]]) -> dict[str, Any]:
        self.storage.start_run(self.run_id)
        self.storage.reset()

        all_packets = list(packets)
        segment_rules = self.cfg.get("segments", [])

        # Step 1: segment assignment
        for pkt in all_packets:
            pkt["assigned_segments"] = assign_segments(pkt, segment_rules)
            self.storage.save_packet(pkt)

        # Step 2: theme clustering
        cluster_result = cluster_packets(all_packets, self.cfg)
        for i, pkt in enumerate(all_packets):
            pkt["cluster_id"] = cluster_result["labels"][i] if i < len(cluster_result["labels"]) else 0
            pkt["cluster_label"] = cluster_result["cluster_labels"].get(pkt["cluster_id"], "")

        # Step 3: quantification
        quant = quantify(all_packets, cluster_result["labels"], cluster_result["cluster_labels"])

        # save quantification tables
        self.storage.save_quantification(quant)
        for pkt in all_packets:
            self.storage.save_packet(pkt)  # update with cluster info

        summary = (
            f"packets={len(all_packets)} clusters={cluster_result['n_clusters']} "
            f"silhouette={cluster_result['silhouette']}"
        )
        self.storage.finish_run(self.run_id, quant, summary)
        return {
            "run_id": self.run_id,
            "total_packets": len(all_packets),
            "clusters": cluster_result["n_clusters"],
            "silhouette": cluster_result["silhouette"],
            "cluster_labels": cluster_result["cluster_labels"],
            "quantification": quant,
            "extractor_version": self.version,
        }
