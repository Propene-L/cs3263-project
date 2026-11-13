"""Reproduce all reviewed experimental-depth analyses from saved artifacts."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from evaluation.depth_analysis.clarification_decisions import (
    run_clarification_decision_analysis,
)
from evaluation.depth_analysis.difficulty import run_difficulty_analysis
from evaluation.depth_analysis.interaction_ablation import run_interaction_ablation
from evaluation.depth_analysis.llm_failures import run_llm_failure_analysis
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
    output_directory = args.output_directory.resolve()
    output_directory.mkdir(parents=True, exist_ok=True)
    summary = {
        "analysis_version": "experimental_depth_v1",
        "random_seed_policy": (
            "32631202 reserved for resampling/sensitivity checks; none performed. "
            "Historical saved random-selector output retains its recorded seed."
        ),
        "experiment_1_multi_round": run_multi_round_analysis(
            args.phase_1_1_results.resolve(), output_directory
        ),
        "experiment_2_difficulty": run_difficulty_analysis(
            args.phase_1_1_results.resolve(),
            ROOT / "data" / "curated" / "clarification_evidence.json",
            output_directory,
        ),
        "experiment_3_interaction_ablation": run_interaction_ablation(
            ROOT, output_directory
        ),
        "analysis_4_llm_failures": run_llm_failure_analysis(ROOT, output_directory),
        "analysis_5_clarification_decisions": run_clarification_decision_analysis(
            ROOT, output_directory
        ),
    }
    figures_directory = output_directory / "figures"
    figures_directory.mkdir(exist_ok=True)
    figure_names = sorted(
        path.name
        for path in output_directory.glob("fig_*")
        if path.suffix.lower() in {".png", ".svg"}
    )
    for name in figure_names:
        shutil.copy2(output_directory / name, figures_directory / name)
    summary["publication_figure_copies"] = [
        str(figures_directory / name) for name in figure_names
    ]
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

