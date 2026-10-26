"""Run the Phase 0 ArtGraph-to-Prolog pilot deduction."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from museum_guide.prolog_bridge import run_pilot_query


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--facts", type=Path, default=Path("logic/generated_facts.pl"))
    parser.add_argument("--rules", type=Path, default=Path("logic/pilot_rules.pl"))
    parser.add_argument("--artwork", required=True)
    args = parser.parse_args()
    print(json.dumps(run_pilot_query(args.facts, args.rules, args.artwork), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

