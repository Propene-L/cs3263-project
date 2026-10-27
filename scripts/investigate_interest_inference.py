"""Reproducible Phase 0.75 ArtGraph interest-inference investigation."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from museum_guide.artgraph import (
    _node_label,
    _node_type,
    export_prolog_facts,
    load_graph,
    sha256_file,
    stable_topic_id,
    write_sorted_rdf,
)
from museum_guide.domain import Topic
from museum_guide.interest_exploration import (
    audit_interest_data,
    build_interest_index,
    candidate_tag_subsets,
    extract_interest_subgraph,
    overlap_profile,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--audit-output", required=True)
    parser.add_argument("--scenario-output", required=True)
    parser.add_argument("--rdf-output", required=True)
    parser.add_argument("--catalog-output", required=True)
    parser.add_argument("--prolog-output", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    started = time.perf_counter()
    print("stage=load_graph", flush=True)
    graph = load_graph(args.input)
    print(f"stage=build_index triples={len(graph)} elapsed={time.perf_counter()-started:.2f}", flush=True)
    index = build_interest_index(graph)
    print(f"stage=audit artworks={len(index.artworks)} elapsed={time.perf_counter()-started:.2f}", flush=True)
    audit = audit_interest_data(graph, index)
    print(f"stage=candidate_subsets elapsed={time.perf_counter()-started:.2f}", flush=True)
    subsets = candidate_tag_subsets(index, limit=5)
    if len(subsets) < 5:
        raise RuntimeError(f"Expected five candidate subsets, found {len(subsets)}")
    recommended = subsets[0]
    print(f"stage=scenarios recommended={recommended['candidate_id']} elapsed={time.perf_counter()-started:.2f}", flush=True)
    candidate_ids = recommended["artwork_ids"]
    candidate_uris = {
        artwork
        for artwork in index.artworks
        if stable_topic_id(artwork) in set(candidate_ids)
    }

    examples = recommended["examples"]
    seed_ids: list[str] = []
    for example in examples:
        seed_ids.extend((example["left"]["id"], example["right"]["id"]))
    seed_ids = list(dict.fromkeys(seed_ids))
    if len(seed_ids) < 3:
        seed_ids.extend(candidate_ids[: 3 - len(seed_ids)])

    uri_by_id = {stable_topic_id(uri): uri for uri in index.artworks}
    scenarios = [
        {
            "scenario_id": "single_known_primary",
            "semantics": "familiarity supplies weak, assumption-labeled interest evidence",
            "known_artwork_ids": [seed_ids[0]],
            "liked_artwork_ids": [],
            "disliked_artwork_ids": [],
            "viewed_artwork_ids": [seed_ids[0]],
            "rejected_artwork_ids": [],
            "overlap_profile": overlap_profile(index, [uri_by_id[seed_ids[0]]], candidate_uris),
        },
        {
            "scenario_id": "two_known_repeated_evidence",
            "semantics": "two familiar artworks can repeat an attribute signal",
            "known_artwork_ids": seed_ids[:2],
            "liked_artwork_ids": [],
            "disliked_artwork_ids": [],
            "viewed_artwork_ids": seed_ids[:2],
            "rejected_artwork_ids": [],
            "overlap_profile": overlap_profile(index, [uri_by_id[value] for value in seed_ids[:2]], candidate_uris),
        },
        {
            "scenario_id": "explicit_positive",
            "semantics": "explicit liking is distinct from familiarity and yields strong signals",
            "known_artwork_ids": [],
            "liked_artwork_ids": [seed_ids[0]],
            "disliked_artwork_ids": [],
            "viewed_artwork_ids": [seed_ids[0]],
            "rejected_artwork_ids": [],
            "overlap_profile": overlap_profile(index, [uri_by_id[seed_ids[0]]], candidate_uris),
        },
        {
            "scenario_id": "positive_and_negative",
            "semantics": "negative attribute evidence blocks candidates with a matching negative signal",
            "known_artwork_ids": [],
            "liked_artwork_ids": [seed_ids[0]],
            "disliked_artwork_ids": [seed_ids[2]],
            "viewed_artwork_ids": [seed_ids[0], seed_ids[2]],
            "rejected_artwork_ids": [],
            "overlap_profile": overlap_profile(index, [uri_by_id[seed_ids[0]], uri_by_id[seed_ids[2]]], candidate_uris),
        },
        {
            "scenario_id": "rejected_candidate_filter",
            "semantics": "a previously rejected candidate is excluded without changing museum facts",
            "known_artwork_ids": seed_ids[:2],
            "liked_artwork_ids": [],
            "disliked_artwork_ids": [],
            "viewed_artwork_ids": seed_ids[:2],
            "rejected_artwork_ids": [seed_ids[2]],
            "overlap_profile": overlap_profile(index, [uri_by_id[value] for value in seed_ids[:2]], candidate_uris),
        },
    ]

    report = {
        "schema_version": "0.75",
        "source": args.input,
        "source_sha256": sha256_file(args.input),
        "audit": audit,
        "candidate_subsets": subsets,
        "recommended_candidate_id": recommended["candidate_id"],
    }
    Path(args.audit_output).write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    Path(args.scenario_output).write_text(json.dumps({"schema_version": "0.75", "scenarios": scenarios}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"stage=extract elapsed={time.perf_counter()-started:.2f}", flush=True)
    sample, nodes = extract_interest_subgraph(graph, candidate_ids)
    write_sorted_rdf(sample, args.rdf_output)
    topics = []
    for node in nodes:
        node_type = _node_type(graph, node)
        if node_type is not None:
            topics.append(
                Topic(
                    id=stable_topic_id(node),
                    type=node_type,
                    label=_node_label(graph, node),
                    source_uri=str(node),
                    properties={},
                )
            )
    topics.sort(key=lambda topic: (topic.type.value, topic.id))
    catalog = {
        "schema_version": "0.75",
        "candidate_policy": "Only bounded real ArtGraph artworks are eligible recommendation candidates.",
        "topics": [
            {
                "id": topic.id,
                "type": topic.type.value,
                "label": topic.label,
                "source_uri": topic.source_uri,
                "properties": topic.properties,
            }
            for topic in topics
        ],
        "allowed_candidate_ids": candidate_ids,
    }
    Path(args.catalog_output).write_text(json.dumps(catalog, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    export = export_prolog_facts(
        sample,
        topics,
        args.prolog_output,
        snapshot_id="artgraph_v1_phase_0_75_interest_dev",
        source_dataset_uri="https://zenodo.org/records/6337958",
    )
    print(f"stage=complete elapsed={time.perf_counter()-started:.2f}", flush=True)
    print(
        json.dumps(
            {
                "candidate_subsets": [
                    {"id": value["candidate_id"], "anchor": value["anchor_tag"], "stats": value["stats"]}
                    for value in subsets
                ],
                "recommended": recommended["candidate_id"],
                "sample_triples": len(sample),
                "topics": len(topics),
                "prolog": export,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
