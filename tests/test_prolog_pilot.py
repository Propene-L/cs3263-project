from __future__ import annotations

from pathlib import Path

import pytest

from museum_guide.artgraph import extract_connected_subgraph, export_prolog_facts, load_graph
from museum_guide.prolog_bridge import PrologError, find_swipl, run_pilot_query

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(find_swipl() is None, reason="SWI-Prolog is not installed")
def test_generated_facts_support_real_prolog_unification(tmp_path):
    graph = load_graph(ROOT / "data" / "samples" / "mini_artgraph.ttl")
    sample, topics = extract_connected_subgraph(graph, "9000001")
    facts = tmp_path / "facts.pl"
    export_prolog_facts(sample, topics, facts, snapshot_id="synthetic_test")
    rows = run_pilot_query(facts, ROOT / "logic" / "pilot_rules.pl", "ag_9000001")
    assert {row["kind"] for row in rows} == {
        "artist_context",
        "style_context",
        "genre_context",
        "medium_context",
    }
    assert all(row["fact_ids"] for row in rows)
    assert all(row["rule_id"].startswith("r_context_") for row in rows)


def test_prolog_bridge_rejects_executable_text():
    with pytest.raises(PrologError, match="Unsafe Prolog topic ID"):
        run_pilot_query("missing", "missing", "x),halt")


