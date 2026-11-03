"""Build the real ArtGraph Phase 1 active-clarification snapshot."""

from __future__ import annotations

import argparse
import json
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
from museum_guide.clarification_dataset import (
    HYPOTHESIS_DEFINITIONS,
    analyze_contrasts,
    evidence_catalog,
    select_clarification_artworks,
)
from museum_guide.domain import Topic
from museum_guide.interest_exploration import build_interest_index, extract_interest_subgraph


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--rdf-output", required=True)
    parser.add_argument("--catalog-output", required=True)
    parser.add_argument("--evidence-output", required=True)
    parser.add_argument("--report-output", required=True)
    parser.add_argument("--prolog-output", required=True)
    parser.add_argument("--per-hypothesis", type=int, default=12)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    graph = load_graph(args.input)
    index = build_interest_index(graph)
    artwork_ids, cohorts = select_clarification_artworks(
        index, per_hypothesis=args.per_hypothesis
    )
    sample, nodes = extract_interest_subgraph(graph, artwork_ids)
    write_sorted_rdf(sample, args.rdf_output)

    topics: list[Topic] = []
    for node in nodes:
        node_type = _node_type(graph, node)
        if node_type is None:
            continue
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
        "schema_version": "1.0",
        "snapshot_id": "artgraph_v1_phase_1_clarification",
        "allowed_candidate_ids": artwork_ids,
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
    }
    Path(args.catalog_output).write_text(
        json.dumps(catalog, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    evidence = evidence_catalog(index, artwork_ids)
    Path(args.evidence_output).write_text(
        json.dumps(evidence, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    report = {
        "schema_version": "1.0",
        "source": args.input,
        "source_sha256": sha256_file(args.input),
        "selection": {
            "method": "Artist-diverse deterministic cohorts for ten typed hypotheses.",
            "per_hypothesis_target": args.per_hypothesis,
            "artwork_count": len(artwork_ids),
            "topic_count": len(topics),
            "triple_count": len(sample),
            "cohorts": cohorts,
        },
        "hypotheses": [
            {
                "id": item.id,
                "attribute_type": item.attribute_type,
                "value_id": item.value_id,
                "label": item.label,
            }
            for item in HYPOTHESIS_DEFINITIONS
        ],
        "contrast_analysis": analyze_contrasts(index, artwork_ids),
    }
    Path(args.report_output).write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    export = export_prolog_facts(
        sample,
        topics,
        args.prolog_output,
        snapshot_id="artgraph_v1_phase_1_clarification",
        source_dataset_uri="https://zenodo.org/records/6337958",
    )
    print(
        json.dumps(
            {
                "artworks": len(artwork_ids),
                "topics": len(topics),
                "triples": len(sample),
                "prolog": export,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
