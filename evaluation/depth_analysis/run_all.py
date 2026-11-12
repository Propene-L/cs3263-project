"""Entry point for reviewed experimental-depth phases.

At the current review gate this runs Experiment 1 only. Later experiments must
not be added until the Experiment 1 artifacts have received human review.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from evaluation.depth_analysis.multi_round import run_multi_round_analysis


ROOT = Path(__file__).resolve().parents[2]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--phase-1-1-results",
        type=Path,
        default=ROOT / "evaluation" / "phase_1_1_results.json",
    )
    parser.add_argument(
        "--output-directory",
        type=Path,
        default=ROOT / "evaluation" / "depth_analysis",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = {
        "completed_review_phase": "experiment_1_multi_round_uncertainty_reduction",
        "analysis": run_multi_round_analysis(
            args.phase_1_1_results.resolve(), args.output_directory.resolve()
        ),
        "next_review_gate": (
            "Human review is required before Experiment 2 difficulty stratification."
        ),
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

