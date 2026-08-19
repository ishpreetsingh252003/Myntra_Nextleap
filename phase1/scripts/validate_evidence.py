"""Validate evidence packets against the Phase 1 evidence schema and taxonomies.

Usage:
    python scripts/validate_evidence.py path/to/packets.json [--taxonomies config/taxonomies]
    python scripts/validate_evidence.py --sample   # runs the golden-set sample against schema

Requires: pydantic (schema), PyYAML (taxonomies).
"""
from __future__ import annotations

import json
import pathlib
import sys

import jsonschema
import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCHEMA_PATH = ROOT / "schemas" / "evidence.schema.json"
DEFAULT_TAXO_DIR = ROOT / "config" / "taxonomies"
GOLDEN_SAMPLE = ROOT / "data" / "golden_set" / "golden_evidence_sample.json"


def load_schema() -> dict:
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        return json.load(f)


def load_taxonomy_ids(taxo_dir: pathlib.Path) -> dict[str, set[str]]:
    """Load known IDs per taxonomy type -> set of ids."""
    ids: dict[str, set[str]] = {}
    with open(taxo_dir / "behaviours.yaml", encoding="utf-8") as f:
        ids["behaviours"] = {item["id"] for item in yaml.safe_load(f)["behaviours"]}
    with open(taxo_dir / "barriers.yaml", encoding="utf-8") as f:
        ids["barriers"] = {item["id"] for item in yaml.safe_load(f)["barriers"]}
    with open(taxo_dir / "segments.yaml", encoding="utf-8") as f:
        ids["segments"] = {item["id"] for item in yaml.safe_load(f)["segments"]}
    return ids


def validate_packet(packet: dict, known_ids: dict[str, set[str]]) -> list[str]:
    errors: list[str] = []

    def bad(field: str, value: str, allowed: set[str]) -> None:
        if value not in allowed and value not in {"OTH", "NONE-STATED"}:
            errors.append(f"{field} '{value}' not in taxonomy")

    for ref in ("behaviours",):
        for value in packet.get(ref, []):
            bad(f"{ref}.{value}", value, known_ids["behaviours"])
    for value in packet.get("barriers", []):
        bad(f"barriers.{value}", value, known_ids["barriers"])
    for value in packet.get("segment_hints", []):
        bad(f"segment_hints.{value}", value, known_ids["segments"])

    for field in ("confidence",):
        for key, level in packet.get(field, {}).items():
            if level not in {"high", "medium", "low"}:
                errors.append(f"confidence['{key}'] invalid level '{level}'")

    return errors


def main(argv: list[str]) -> int:
    schema = load_schema()
    known = load_taxonomy_ids(DEFAULT_TAXO_DIR)

    if "--sample" in argv:
        packets = json.loads(GOLDEN_SAMPLE.read_text(encoding="utf-8"))
        label = str(GOLDEN_SAMPLE)
    else:
        path = pathlib.Path(argv[1]) if argv else None
        if not path:
            print("usage: validate_evidence.py <packets.json> | --sample")
            return 2
        packets = json.loads(path.read_text(encoding="utf-8"))
        label = str(path)

    if isinstance(packets, dict):
        packets = packets.get("evidence_packets", [])

    total_errors = 0
    validator = jsonschema.Draft202012Validator(schema)
    for packet in packets:
        schema_errors = sorted(
            validator.iter_errors(packet),
            key=lambda e: ".".join(str(p) for p in e.path),
        )
        taxonomy_errors = validate_packet(packet, known)
        errors = [e.message for e in schema_errors] + taxonomy_errors
        if errors:
            total_errors += 1
            print(f"\n[FAIL] {packet.get('packet_id', '?')}")
            for e in errors:
                print(f"       - {e}")
        else:
            print(f"[OK]   {packet.get('packet_id', '?')}")

    print(f"\nPackets: {len(packets)}  Failed: {total_errors}  (source: {label})")
    return 1 if total_errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))