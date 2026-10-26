from __future__ import annotations

from pathlib import Path

from museum_guide.artgraph import load_graph
from museum_guide.exploration import (
    discover_candidate_subgraphs,
    predicate_inventory,
    write_graph_viewer,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "data" / "samples" / "exploration_artgraph.ttl"


def test_candidate_discovery_uses_measurable_structural_filters():
    graph = load_graph(FIXTURE)
    candidates = discover_candidate_subgraphs(graph, limit=1)
    assert len(candidates) == 1
    summary, sample, topics = candidates[0]
    assert summary["artist_id"] == "ag_9100001"
    assert summary["stats"]["artwork_count"] == 3
    assert summary["stats"]["entity_type_count"] == 10
    assert summary["stats"]["independent_path_count"] >= 3
    assert summary["stats"]["shared_relationship_count"] >= 5
    assert len(sample) > 0
    assert len(topics) == summary["stats"]["entity_count"]


def test_predicate_inventory_and_html_preserve_source_triples(tmp_path):
    graph = load_graph(FIXTURE)
    inventory = {item["predicate"]: item for item in predicate_inventory(graph)}
    assert inventory["has_subject"]["frequency"] == 1
    assert inventory["has_period"]["frequency"] == 3
    assert inventory["part_of_series"]["domain"] == "Artwork"
    assert inventory["related_to_school"]["range"] == "Training"
    candidates = discover_candidate_subgraphs(graph, limit=1)
    report = {"candidates": [candidates[0][0]]}
    output = tmp_path / "viewer.html"
    write_graph_viewer(report, output)
    text = output.read_text(encoding="utf-8")
    assert "Synthetic Explorer Artist" in text
    assert "predicate_uri" in text
    assert "source_uri" in text
    # Escapes must remain JavaScript escapes. Literal newlines in this
    # single-quoted string make the entire viewer script fail to parse.
    assert "'\\n\\nPaths:\\n'" in text
    assert ".join('\\n')" in text

