"""Audit the official ArtGraph RDF archive and emit reproducible statistics."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from museum_guide.artgraph import find_seed_candidates, graph_audit, load_graph, sanitize_artgraph


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument(
        "--sanitized-output",
        type=Path,
        default=Path("data/raw/artgraph-facts.sanitized.ttl"),
    )
    parser.add_argument("--output", type=Path, default=Path("docs/artgraph_audit.json"))
    args = parser.parse_args()
    sanitation = sanitize_artgraph(args.input, args.sanitized_output)
    graph = load_graph(args.sanitized_output)
    report = {
        "sanitation": sanitation,
        "audit": graph_audit(graph),
        "seed_candidates": find_seed_candidates(graph),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

