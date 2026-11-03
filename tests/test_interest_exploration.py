from __future__ import annotations

from pathlib import Path

from rdflib import URIRef

from museum_guide.artgraph import RESOURCE_PREFIX, load_graph
from museum_guide.interest_exploration import (
    audit_interest_data,
    build_interest_index,
    candidate_tag_subsets,
    overlap_profile,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "data" / "samples" / "interest_artgraph.ttl"


def uri(identifier: int) -> URIRef:
    return URIRef(f"{RESOURCE_PREFIX}{identifier}")


def test_synthetic_about_audit_establishes_artwork_to_tag_semantics():
    graph = load_graph(FIXTURE)
    index = build_interest_index(graph)
    audit = audit_interest_data(graph, index)
    assert audit["artwork_count"] == 3
    assert audit["tag_entity_count"] == 2
    assert audit["about_triple_count"] == 5
    assert audit["about_semantics"]["observed_type_pairs"][0]["domain"] == "Artwork"
    assert audit["about_semantics"]["observed_type_pairs"][0]["range"] == "Tag"
    assert audit["multi_tag_overlap"]["artworks_with_two_tag_cross_artist_peer"] == 2


def test_synthetic_candidate_and_overlap_are_descriptive_not_inference():
    graph = load_graph(FIXTURE)
    index = build_interest_index(graph)
    subsets = candidate_tag_subsets(
        index,
        minimum_artworks=2,
        maximum_artworks=3,
        minimum_artists=2,
        limit=1,
    )
    assert subsets[0]["anchor_tag"]["id"] == "ag_9200201"
    assert subsets[0]["stats"]["artist_count"] == 3
    profile = overlap_profile(index, [uri(9200001)], {uri(9200001), uri(9200002), uri(9200003)})
    assert profile["candidate_counts_at_least"]["2"] == 1
    assert profile["top_candidates"][0]["id"] == "ag_9200002"

