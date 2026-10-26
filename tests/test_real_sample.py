from __future__ import annotations

import hashlib
import json
from pathlib import Path

from museum_guide.artgraph import RELATION_PREDICATES, load_graph
from museum_guide.prolog_bridge import run_pilot_query

ROOT = Path(__file__).resolve().parents[1]


def test_manifest_matches_committed_real_sample():
    manifest = json.loads((ROOT / "docs" / "dataset_manifest.json").read_text())
    sample_path = ROOT / "data" / "curated" / "artgraph_v1_seed_8142.ttl"
    digest = hashlib.sha256(sample_path.read_bytes()).hexdigest()
    prolog_digest = hashlib.sha256(
        (ROOT / "logic" / "generated_facts.pl").read_bytes()
    ).hexdigest()
    graph = load_graph(sample_path)
    assert digest == manifest["sample_hash"]
    assert prolog_digest == manifest["prolog_facts_sha256"]
    assert len(graph) == manifest["sample_triple_count"] == 32
    assert sum(1 for _, predicate, _ in graph if predicate in RELATION_PREDICATES) == 13
    assert manifest["license_status"].startswith("UNRESOLVED")


def test_real_sample_prolog_proof_names_rules_and_facts():
    rows = run_pilot_query(
        ROOT / "logic" / "generated_facts.pl",
        ROOT / "logic" / "pilot_rules.pl",
        "ag_8142",
    )
    by_kind = {row["kind"]: row for row in rows}
    assert by_kind["artist_context"]["topic"] == "ag_850"
    assert by_kind["artist_context"]["rule_id"] == "r_context_artist"
    assert by_kind["style_context"]["topic"] == "ag_46"
    assert all(fact_id.startswith("agf_") for row in rows for fact_id in row["fact_ids"])

