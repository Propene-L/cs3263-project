"""Difficulty-stratified Phase 1.1 clarification analysis."""

from __future__ import annotations

import json
import os
import statistics
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence

from evaluation.depth_analysis.multi_round import (
    METHOD_COLOURS,
    METHOD_LABELS,
    load_results,
    validate_shared_cohort,
    write_csv,
)


def _mean(values: Sequence[float | int]) -> float | None:
    return round(statistics.fmean(values), 6) if values else None


def _stratum(initial_count: int) -> str:
    return "exactly_2" if initial_count == 2 else "3_or_more"


def analyse_difficulty(results: Mapping[str, Any]) -> list[dict[str, Any]]:
    methods = tuple(results["configuration"]["methods"])
    scenarios = results["scenarios"]
    cohort_ids = set(validate_shared_cohort(scenarios, methods))
    cohort = [s for s in scenarios if s["scenario_id"] in cohort_ids]
    initial_counts = {
        s["scenario_id"]: int(s["methods"][methods[0]]["initial_hypothesis_count"])
        for s in cohort
    }
    for scenario in cohort:
        counts = {
            int(scenario["methods"][method]["initial_hypothesis_count"])
            for method in methods
        }
        if len(counts) != 1:
            raise ValueError(
                f"Initial active count differs by method for {scenario['scenario_id']}"
            )

    rows: list[dict[str, Any]] = []
    for stratum in ("exactly_2", "3_or_more"):
        members = [
            scenario
            for scenario in cohort
            if _stratum(initial_counts[scenario["scenario_id"]]) == stratum
        ]
        single_success = {
            scenario["scenario_id"]: bool(
                scenario["methods"]["single_rule_prolog"]["correctly_resolved"]
            )
            for scenario in members
        }
        single_rate = statistics.fmean(single_success.values())
        for method in methods:
            method_results = [scenario["methods"][method] for scenario in members]
            success = {
                scenario["scenario_id"]: bool(
                    scenario["methods"][method]["correctly_resolved"]
                )
                for scenario in members
            }
            selected = [
                round_row
                for result in method_results
                for round_row in result["rounds"]
                if round_row.get("selected")
            ]
            runtimes = [
                float(value)
                for result in method_results
                for value in result["selection_runtime_ms"]
            ]
            successful_questions = [
                int(result["question_count"])
                for result in method_results
                if result["correctly_resolved"]
            ]
            resolution_rate = statistics.fmean(success.values())
            rows.append(
                {
                    "stratum": stratum,
                    "stratum_label": (
                        "Exactly 2 active hypotheses"
                        if stratum == "exactly_2"
                        else "3+ active hypotheses"
                    ),
                    "scenario_count": len(members),
                    "scenario_ids": "|".join(s["scenario_id"] for s in members),
                    "method": method,
                    "method_label": METHOD_LABELS.get(method, method),
                    "resolved_count": sum(success.values()),
                    "resolution_rate_within_three_questions": round(
                        resolution_rate, 6
                    ),
                    "mean_questions_per_successful_resolution": _mean(
                        successful_questions
                    ),
                    "selected_question_count": len(selected),
                    "mean_distinguished_pairs_per_selected_question": _mean(
                        [
                            int(item["distinguished_hypothesis_pair_count"])
                            for item in selected
                        ]
                    ),
                    "selection_attempt_count": len(runtimes),
                    "mean_selector_runtime_ms": _mean(runtimes),
                    "resolution_rate_difference_vs_single_rule": round(
                        resolution_rate - single_rate, 6
                    ),
                    "paired_method_only_success_count": sum(
                        success[sid] and not single_success[sid] for sid in success
                    ),
                    "paired_single_rule_only_success_count": sum(
                        single_success[sid] and not success[sid] for sid in success
                    ),
                    "paired_both_success_count": sum(
                        success[sid] and single_success[sid] for sid in success
                    ),
                    "paired_neither_success_count": sum(
                        not success[sid] and not single_success[sid] for sid in success
                    ),
                }
            )
    return rows


def generate_difficulty_figure(csv_path: Path, png_path: Path, svg_path: Path) -> None:
    import csv

    os.environ.setdefault(
        "MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "cs3263-matplotlib")
    )
    import matplotlib as mpl

    mpl.use("Agg")
    mpl.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 9.5,
            "svg.hashsalt": "cs3263-difficulty-v1",
        }
    )
    import matplotlib.pyplot as plt
    import numpy as np

    with csv_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    methods = list(dict.fromkeys(row["method"] for row in rows))
    strata = ["exactly_2", "3_or_more"]
    labels = [
        next(row["stratum_label"] for row in rows if row["stratum"] == stratum)
        + "\n"
        + f"n={next(row['scenario_count'] for row in rows if row['stratum'] == stratum)}"
        for stratum in strata
    ]
    x = np.arange(len(strata))
    width = 0.15
    figure, axis = plt.subplots(figsize=(9.5, 5.2), constrained_layout=True)
    for index, method in enumerate(methods):
        values = [
            100
            * float(
                next(
                    row["resolution_rate_within_three_questions"]
                    for row in rows
                    if row["stratum"] == stratum and row["method"] == method
                )
            )
            for stratum in strata
        ]
        bars = axis.bar(
            x + (index - (len(methods) - 1) / 2) * width,
            values,
            width,
            label=METHOD_LABELS.get(method, method),
            color=METHOD_COLOURS.get(method),
            hatch="//" if method == "exact_objective_python" else None,
        )
        axis.bar_label(bars, fmt="%.0f", padding=2, fontsize=8)
    axis.set_ylabel("Resolved within three questions (%)")
    axis.set_xticks(x, labels)
    axis.set_ylim(0, 110)
    axis.grid(axis="y", alpha=0.25)
    axis.set_title("Clarification performance by initial hypothesis-set size", pad=12)
    handles, legend_labels = axis.get_legend_handles_labels()
    figure.legend(
        handles,
        legend_labels,
        loc="outside lower center",
        ncol=3,
        frameon=False,
    )
    figure.savefig(
        png_path,
        dpi=200,
        metadata={"Creator": "evaluation.depth_analysis", "Date": None},
    )
    figure.savefig(
        svg_path,
        metadata={"Creator": "evaluation.depth_analysis", "Date": None},
    )
    plt.close(figure)


def _name_hypothesis(hypothesis_id: str, labels: Mapping[str, str]) -> str:
    return f"{labels.get(hypothesis_id, hypothesis_id)} (`{hypothesis_id}`)"


def _case_section(
    scenario: Mapping[str, Any],
    hypothesis_labels: Mapping[str, str],
    artwork_labels: Mapping[str, str],
) -> str:
    lines = [
        f"## `{scenario['scenario_id']}`",
        "",
        f"Hidden controlled hypothesis: {_name_hypothesis(scenario['hidden_hypothesis_id'], hypothesis_labels)}.",
        "",
    ]
    for method in ("compositional_prolog", "single_rule_prolog"):
        result = scenario["methods"][method]
        lines.extend(
            [
                f"### {METHOD_LABELS[method]}",
                "",
                "Initial active hypotheses: "
                + ", ".join(
                    _name_hypothesis(item, hypothesis_labels)
                    for item in result["initial_active_hypothesis_ids"]
                )
                + ".",
                "",
            ]
        )
        for item in result["rounds"]:
            if not item.get("selected"):
                lines.append(
                    f"- Round {item['round']}: no question selected; active set was "
                    + ", ".join(
                        _name_hypothesis(h, hypothesis_labels)
                        for h in item.get("active_hypothesis_ids_before", ())
                    )
                    + "."
                )
                continue
            option_a, option_b = item["selected_artwork_ids"]
            partition = item["predicted_response_partition"]
            partition_text = "; ".join(
                f"{response}: "
                + (
                    ", ".join(
                        _name_hypothesis(h, hypothesis_labels)
                        for h in partition[response]
                    )
                    or "none"
                )
                for response in ("prefer_a", "prefer_b", "unknown")
            )
            after = ", ".join(
                _name_hypothesis(h, hypothesis_labels)
                for h in item["active_hypothesis_ids_after"]
            )
            lines.append(
                f"- Round {item['round']}: selected {artwork_labels.get(option_a, option_a)} "
                f"(`{option_a}`) versus {artwork_labels.get(option_b, option_b)} (`{option_b}`). "
                f"Predicted partition — {partition_text}. The visitor response was "
                f"`{item['simulated_response']}`; eliminated "
                f"{len(item['eliminated_hypothesis_ids'])} hypothesis/hypotheses; active afterward: {after}."
            )
        lines.extend(
            [
                "",
                f"Outcome: `correctly_resolved={str(result['correctly_resolved']).lower()}`, "
                f"stop reason `{result['stopping_reason']}`, "
                f"{result['remaining_hypothesis_count']} active hypothesis/hypotheses remaining.",
                "",
            ]
        )
    return "\n".join(lines)


def write_contrasting_cases(
    results: Mapping[str, Any], evidence_path: Path, output_path: Path
) -> None:
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    hypothesis_labels = {item["id"]: item["label"] for item in evidence["hypotheses"]}
    artwork_labels = {
        artwork_id: item["label"] for artwork_id, item in evidence["artworks"].items()
    }
    by_id = {item["scenario_id"]: item for item in results["scenarios"]}
    selected = ("controlled_multi_16", "phase_1_1_multi_021")
    text = """# Contrasting multi-round clarification cases

These are paired trajectories from the committed Phase 1.1 result artifact.
Both methods receive identical states, candidate pools, response semantics, and
visitor responses. The examples show that aggregate discrimination is useful
but does not dominate for every hidden controlled hypothesis.

"""
    text += "\n\n".join(
        _case_section(by_id[scenario_id], hypothesis_labels, artwork_labels)
        for scenario_id in selected
    )
    text += """

## Interpretation

`controlled_multi_16` demonstrates the intended benefit: the compositional
selector considers all active hypothesis pairs and reaches the hidden singleton
before the three-question limit, whereas the single-rule selector does not.
`phase_1_1_multi_021` is the required counterexample. Its compositional choices
maximize aggregate pair distinction, but the hidden hypothesis produces
responses that preserve ambiguity; the single-rule trajectory happens to
resolve that particular hidden hypothesis. Neither case is evidence about
human preference behavior because the responses come from the declared
positive-support simulator.
"""
    output_path.write_text(text, encoding="utf-8", newline="\n")


def run_difficulty_analysis(
    result_path: Path, evidence_path: Path, output_directory: Path
) -> dict[str, Any]:
    results = load_results(result_path)
    rows = analyse_difficulty(results)
    csv_path = output_directory / "difficulty_breakdown.csv"
    png_path = output_directory / "fig_difficulty_breakdown.png"
    svg_path = output_directory / "fig_difficulty_breakdown.svg"
    cases_path = output_directory / "contrasting_cases.md"
    write_csv(csv_path, rows)
    generate_difficulty_figure(csv_path, png_path, svg_path)
    write_contrasting_cases(results, evidence_path, cases_path)
    return {
        "strata": {
            row["stratum"]: row["scenario_count"]
            for row in rows
            if row["method"] == "compositional_prolog"
        },
        "outputs": [str(csv_path), str(png_path), str(svg_path), str(cases_path)],
    }

