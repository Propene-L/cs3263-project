from __future__ import annotations

import json
from pathlib import Path

import pytest

from museum_guide.artgraph import (
    ArtGraphError,
    extract_connected_subgraph,
    export_prolog_facts,
    load_graph,
    sanitize_artgraph,
    stable_fact_id,
    stable_topic_id,
    write_sorted_rdf,
    write_topic_catalog,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "data" / "samples" / "mini_artgraph.ttl"


def test_sanitizer_removes_only_appended_neo4j_preview(tmp_path):
    source = tmp_path / "dirty.ttl"
    source.write_text(
        "@prefix x: <https://example.test/> .\n"
        "x:a x:p x:b .\n"
        ":POST http://localhost:7474/rdf/example\n"
        "x:untrusted x:p x:tail .\n",
        encoding="utf-8",
    )
    output = tmp_path / "clean.ttl"
    report = sanitize_artgraph(source, output)
    assert report["kept_lines"] == 2
    assert report["removed_lines"] == 2
    assert report["marker_line"] == 3
    assert "untrusted" not in output.read_text(encoding="utf-8")


def test_stable_ids_are_deterministic_and_reject_foreign_uris():
    uri = "https://www.gennarovessio.com/artgraph-resources#123"
    assert stable_topic_id(uri) == "ag_123"
    assert stable_fact_id("s", "p", "o") == stable_fact_id("s", "p", "o")
    with pytest.raises(ArtGraphError, match="Not an ArtGraph resource URI"):
        stable_topic_id("https://example.test/123")


def test_connected_extraction_and_catalog_are_reproducible(tmp_path):
    graph = load_graph(FIXTURE)
    sample, topics = extract_connected_subgraph(graph, "9000001")
    assert len(topics) == 5
    assert len(sample) == len(graph)
    first = tmp_path / "first.ttl"
    second = tmp_path / "second.ttl"
    write_sorted_rdf(sample, first)
    write_sorted_rdf(sample, second)
    assert first.read_bytes() == second.read_bytes()
    catalog = tmp_path / "catalog.json"
    write_topic_catalog(topics, catalog)
    payload = json.loads(catalog.read_text(encoding="utf-8"))
    assert "ag_9000001" not in payload["allowed_candidate_ids"]
    assert set(payload["allowed_candidate_ids"]) == {
        "ag_9000002",
        "ag_9000003",
        "ag_9000004",
        "ag_9000005",
    }


def test_export_creates_ground_prolog_facts_with_source_ids(tmp_path):
    graph = load_graph(FIXTURE)
    sample, topics = extract_connected_subgraph(graph, "9000001")
    output = tmp_path / "facts.pl"
    report = export_prolog_facts(sample, topics, output, snapshot_id="synthetic_test")
    text = output.read_text(encoding="utf-8")
    assert report["fact_count"] > 0
    assert "created_by(ag_9000001, ag_9000002, agf_" in text
    assert "source_fact(agf_" in text
    assert "https://www.gennarovessio.com/artgraph-schema#createdBy" in text

