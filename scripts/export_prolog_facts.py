"""Convert a validated ArtGraph subgraph into safe ground Prolog facts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from museum_guide.artgraph import export_prolog_facts, load_graph
from museum_guide.domain import Topic, TopicType


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--snapshot-id", required=True)
    parser.add_argument(
        "--source-dataset-uri",
        default="https://zenodo.org/records/6337958",
    )
    args = parser.parse_args()
    graph = load_graph(args.input)
    catalog = json.loads(args.catalog.read_text(encoding="utf-8"))
    topics = [
        Topic(
            id=item["id"],
            type=TopicType(item["type"]),
            label=item["label"],
            source_uri=item["source_uri"],
            properties=item.get("properties", {}),
        )
        for item in catalog["topics"]
    ]
    report = export_prolog_facts(
        graph,
        topics,
        args.output,
        snapshot_id=args.snapshot_id,
        source_dataset_uri=args.source_dataset_uri,
    )
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

