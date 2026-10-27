"""Offline multi-round Phase 1 clarification demonstration."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from museum_guide.clarification import (
    ClarificationObservation,
    ClarificationState,
    default_engine,
)

ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-rounds", type=int, default=3)
    parser.add_argument(
        "--responses",
        default="",
        help="Comma-separated simulated responses; otherwise prompt manually.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    catalog = json.loads(
        (ROOT / "data" / "curated" / "clarification_topic_catalog.json").read_text(
            encoding="utf-8"
        )
    )
    responses = [value.strip() for value in args.responses.split(",") if value.strip()]
    state = ClarificationState(
        session_id="demo_visitor",
        observations=(
            ClarificationObservation("obs_demo_like", "likes", "ag_10472"),
            ClarificationObservation(
                "obs_demo_nature", "explicit_interest", "h_nature_subject"
            ),
        ),
        allowed_artwork_ids=tuple(catalog["allowed_candidate_ids"]),
    )
    engine = default_engine(ROOT)
    for round_index in range(args.max_rounds):
        result = engine.clarify(state)
        print(json.dumps({"round": round_index + 1, **result}, indent=2))
        if result["status"] != "selected":
            break
        if round_index < len(responses):
            response = responses[round_index]
        else:
            response = input("Response [prefer_a/prefer_b/neither/unsure]: ").strip()
        state = state.apply_response(
            result["question"], response, f"obs_demo_response_{round_index + 1}"
        )


if __name__ == "__main__":
    main()
