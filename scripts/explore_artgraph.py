"""Find and visualize structurally rich real ArtGraph candidate subgraphs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from museum_guide.artgraph import load_graph, write_sorted_rdf, write_topic_catalog
from museum_guide.exploration import (
    discover_candidate_subgraphs,
    predicate_inventory,
    write_graph_viewer,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-html", type=Path, required=True)
    parser.add_argument("--recommended-rdf", type=Path, required=True)
    parser.add_argument("--recommended-catalog", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--max-artworks", type=int, default=6)
    args = parser.parse_args()
    graph = load_graph(args.input)
    candidates = discover_candidate_subgraphs(
        graph, limit=args.limit, max_artworks=args.max_artworks
    )
    if len(candidates) < args.limit:
        raise SystemExit(
            f"Only {len(candidates)} candidates satisfied the structural filters"
        )
    report = {
        "schema_version": "1.0",
        "input": str(args.input),
        "selection_policy": {
            "requires_artist_movement": True,
            "minimum_artworks": 3,
            "minimum_entity_types": 4,
            "minimum_shared_relationships": 1,
            "minimum_independent_paths": 3,
            "max_artworks_per_candidate": args.max_artworks,
            "ranking": "Inference richness score, then stable artist ID.",
        },
        "predicate_inventory": predicate_inventory(graph),
        "recommended_candidate_id": candidates[0][0]["candidate_id"],
        "candidates": [summary for summary, _, _ in candidates],
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    write_graph_viewer(report, args.output_html)
    _, recommended_graph, recommended_topics = candidates[0]
    write_sorted_rdf(recommended_graph, args.recommended_rdf)
    write_topic_catalog(recommended_topics, args.recommended_catalog)
    print(
        json.dumps(
            {
                "candidate_count": len(candidates),
                "recommended": candidates[0][0],
                "json": str(args.output_json),
                "html": str(args.output_html),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

