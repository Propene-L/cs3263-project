"""Extract a bounded, deterministic, connected ArtGraph topic subgraph."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from museum_guide.artgraph import (
    extract_connected_subgraph,
    load_graph,
    sha256_file,
    write_sorted_rdf,
    write_topic_catalog,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--seed", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--catalog", type=Path, default=Path("data/curated/topic_catalog.json")
    )
    parser.add_argument("--max-depth", type=int, default=2)
    parser.add_argument("--max-neighbors-per-predicate", type=int, default=3)
    args = parser.parse_args()
    graph = load_graph(args.input)
    sample, topics = extract_connected_subgraph(
        graph,
        args.seed,
        max_depth=args.max_depth,
        max_neighbors_per_predicate=args.max_neighbors_per_predicate,
    )
    write_sorted_rdf(sample, args.output)
    write_topic_catalog(topics, args.catalog)
    summary = {
        "seed": args.seed,
        "topic_count": len(topics),
        "triple_count": len(sample),
        "output": str(args.output),
        "sample_sha256": sha256_file(args.output),
        "catalog": str(args.catalog),
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

