"""Phase 1 tests: evidence schema + taxonomy configs are loadable and consistent."""
from __future__ import annotations

import json
import pathlib

import jsonschema
import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCHEMA = json.loads((ROOT / "schemas" / "evidence.schema.json").read_text(encoding="utf-8"))
VALIDATOR = jsonschema.Draft202012Validator(SCHEMA)
GOLDEN = json.loads(
    (ROOT / "data" / "golden_set" / "golden_evidence_sample.json").read_text(encoding="utf-8")
)

TAXONOMY_FILES = {
    "behaviours": "behaviours.yaml",
    "barriers": "barriers.yaml",
    "segments": "segments.yaml",
}


def load_taxonomy(name: str) -> dict:
    with open(ROOT / "config" / "taxonomies" / TAXONOMY_FILES[name], encoding="utf-8") as f:
        return yaml.safe_load(f)


def test_taxonomies_load():
    for name in TAXONOMY_FILES:
        assert load_taxonomy(name), f"{name} should load with items"


def test_taxonomy_ids_unique_and_prefixed():
    prefixes = {"behaviours": "BEH-", "barriers": "PB-", "segments": "SEG-"}
    for name, prefix in prefixes.items():
        items = load_taxonomy(name)[name]
        ids = [item["id"] for item in items]
        assert len(ids) == len(set(ids)), f"{name} ids must be unique"
        assert all(i.startswith(prefix) for i in ids), f"{name} ids must use {prefix} prefix"


def test_taxonomy_items_have_required_fields():
    required = {
        "behaviours": ["id", "name", "label", "description"],
        "barriers": ["id", "name", "label", "description"],
        "segments": ["id", "name", "label", "signal"],
    }
    for name, keys in required.items():
        for item in load_taxonomy(name)[name]:
            for key in keys:
                assert key in item, f"{name} item {item.get('id')} missing '{key}'"


def test_golden_sample_validates_against_schema():
    for packet in GOLDEN["evidence_packets"]:
        errors = list(VALIDATOR.iter_errors(packet))
        assert not errors, f"{packet['packet_id']}: {[e.message for e in errors]}"


def test_golden_packets_reference_existing_taxonomy_ids():
    known = {
        "behaviours": {i["id"] for i in load_taxonomy("behaviours")["behaviours"]},
        "barriers": {i["id"] for i in load_taxonomy("barriers")["barriers"]},
        "segments": {i["id"] for i in load_taxonomy("segments")["segments"]},
    }
    for packet in GOLDEN["evidence_packets"]:
        for value in packet["behaviours"]:
            assert value in known["behaviours"] | {"OTH"}, packet["packet_id"]
        for value in packet["barriers"]:
            assert value in known["barriers"] | {"NONE-STATED", "OTH"}, packet["packet_id"]
        for value in packet["segment_hints"]:
            assert value in known["segments"] | {"OTH"}, packet["packet_id"]


def test_golden_packets_preserve_three_level_distinction():
    for packet in GOLDEN["evidence_packets"]:
        tl = packet["three_level"]
        assert tl["said"] == packet["quote"], "said must equal the verbatim quote"
        assert tl["inferred"], "inferred must not be empty"
        assert tl["concluded"], "concluded must not be empty"