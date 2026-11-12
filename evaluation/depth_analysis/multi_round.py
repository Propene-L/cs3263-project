"""Fixed-cohort analysis of the saved Phase 1.1 clarification trajectories.

This module reads committed evaluator output only. It does not rerun selectors,
change scenarios, or infer new visitor responses.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import statistics
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


EXPECTED_FINAL_RESOLUTIONS = {
    "compositional_prolog": 44,
    "single_rule_prolog": 27,
    "raw_attribute_contrast": 35,
    "random_eligible": 1,
    "exact_objective_python": 44,
}

METHOD_LABELS = {
    "compositional_prolog": "Compositional Prolog",
    "single_rule_prolog": "Single-rule Prolog",
    "raw_attribute_contrast": "Raw attribute contrast",
    "random_eligible": "Random eligible",
    "exact_objective_python": "Exact Python",
}

METHOD_COLOURS = {
    "compositional_prolog": "#0072B2",
    "single_rule_prolog": "#D55E00",
    "raw_attribute_contrast": "#009E73",
    "random_eligible": "#CC79A7",
    "exact_objective_python": "#56B4E9",
}


def load_results(path: Path) -> dict[str, Any]:
    """Load and minimally validate the committed Phase 1.1 result artifact."""

    data = json.loads(path.read_text(encoding="utf-8"))
    required = {"configuration", "scenario_count", "scenarios"}
    missing = required.difference(data)
    if missing:
        raise ValueError(f"Missing Phase 1.1 result keys: {sorted(missing)}")
    if data["scenario_count"] != len(data["scenarios"]):
        raise ValueError("Declared scenario_count does not match scenario records")
    return data


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _method_result(scenario: Mapping[str, Any], method: str) -> Mapping[str, Any]:
    try:
        return scenario["methods"][method]
    except KeyError as exc:
        raise ValueError(
            f"Scenario {scenario.get('scenario_id', '<unknown>')} lacks method {method}"
        ) from exc


def _selected_rounds(method_result: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return [item for item in method_result["rounds"] if item.get("selected")]


def active_count_after_round(method_result: Mapping[str, Any], round_index: int) -> int:
    """Return the state size at a fixed horizon, carrying terminal states forward."""

    if round_index < 0:
        raise ValueError("round_index must be non-negative")
    active_count = int(method_result["initial_hypothesis_count"])
    for item in method_result["rounds"]:
        if int(item["round"]) > round_index:
            break
        if item.get("selected"):
            active_count = int(item["remaining_hypothesis_count"])
        else:
            active_count = len(item.get("active_hypothesis_ids_before", ())) or active_count
    return active_count


def _mean(values: Iterable[int | float]) -> float | None:
    materialized = list(values)
    return statistics.fmean(materialized) if materialized else None


def _round_float(value: float | None) -> float | None:
    return None if value is None else round(value, 6)


def _cohort_for_method(
    scenarios: Sequence[Mapping[str, Any]], method: str
) -> list[Mapping[str, Any]]:
    return [
        scenario
        for scenario in scenarios
        if bool(_method_result(scenario, method)["initially_solvable"])
    ]


def validate_shared_cohort(
    scenarios: Sequence[Mapping[str, Any]], methods: Sequence[str]
) -> tuple[str, ...]:
    """Ensure every method uses the same initially-solvable scenario IDs."""

    if not methods:
        raise ValueError("At least one method is required")
    cohorts = {
        method: tuple(
            scenario["scenario_id"]
            for scenario in _cohort_for_method(scenarios, method)
        )
        for method in methods
    }
    reference_method = methods[0]
    reference = cohorts[reference_method]
    for method in methods[1:]:
        if cohorts[method] != reference:
            raise ValueError(
                f"Initially-solvable cohort differs between {reference_method} and {method}"
            )
    return reference


def analyse_multi_round(
    results: Mapping[str, Any],
    *,
    max_rounds: int | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return aggregate resolution and per-round fixed-cohort trajectory rows."""

    methods = tuple(results["configuration"]["methods"])
    scenarios = results["scenarios"]
    cohort_ids = validate_shared_cohort(scenarios, methods)
    cohort_id_set = set(cohort_ids)
    horizon = int(max_rounds or results["configuration"]["max_rounds"])
    resolution_rows: list[dict[str, Any]] = []
    trajectory_rows: list[dict[str, Any]] = []

    for method in methods:
        method_results = [_method_result(scenario, method) for scenario in scenarios]
        cohort_results = [
            _method_result(scenario, method)
            for scenario in scenarios
            if scenario["scenario_id"] in cohort_id_set
        ]
        if not cohort_results:
            raise ValueError(f"Method {method} has an empty initially-solvable cohort")

        selected_questions = [
            item for result in cohort_results for item in _selected_rounds(result)
        ]
        all_selected_questions = [
            item for result in method_results for item in _selected_rounds(result)
        ]
        eliminated_counts = [
            len(item.get("eliminated_hypothesis_ids", ()))
            for item in selected_questions
        ]
        all_eliminated_counts = [
            len(item.get("eliminated_hypothesis_ids", ()))
            for item in all_selected_questions
        ]
        stop_counts = Counter(result["stopping_reason"] for result in method_results)
        error_reasons = {
            reason
            for reason in stop_counts
            if reason in {"selection_error", "constraint_violation", "false_no_question"}
            or reason.endswith("_error")
        }
        error_stops = sum(stop_counts[reason] for reason in error_reasons)
        recognised_stops = {
            "resolved_unique",
            "initially_resolved",
            "no_valid_discriminative_question",
            "round_limit",
        }.union(error_reasons)
        other_stops = sum(
            count for reason, count in stop_counts.items() if reason not in recognised_stops
        )

        resolution_row: dict[str, Any] = {
            "method": method,
            "method_label": METHOD_LABELS.get(method, method),
            "all_scenario_count": len(method_results),
            "initially_solvable_count": len(cohort_results),
            "initially_resolved_count": sum(
                bool(result["initially_resolved"]) for result in method_results
            ),
            "initially_unsolvable_count": sum(
                bool(result["initially_unsolvable"]) for result in method_results
            ),
            "selected_question_count_all_scenarios": len(all_selected_questions),
            "mean_hypotheses_eliminated_per_selected_question_all_scenarios": _round_float(
                _mean(all_eliminated_counts)
            ),
            "selected_question_count_fixed_cohort": len(selected_questions),
            "mean_hypotheses_eliminated_per_selected_question_fixed_cohort": _round_float(
                _mean(eliminated_counts)
            ),
            "resolution_stop_count": stop_counts["resolved_unique"]
            + stop_counts["initially_resolved"],
            "resolved_after_question_stop_count": stop_counts["resolved_unique"],
            "initially_resolved_stop_count": stop_counts["initially_resolved"],
            "no_discriminative_pair_stop_count": stop_counts[
                "no_valid_discriminative_question"
            ],
            "round_limit_stop_count": stop_counts["round_limit"],
            "error_stop_count": error_stops,
            "other_stop_count": other_stops,
        }

        for round_index in range(horizon + 1):
            resolved = sum(
                bool(result["correctly_resolved"])
                and int(result["question_count"]) <= round_index
                for result in cohort_results
            )
            fixed_counts = [
                active_count_after_round(result, round_index)
                for result in cohort_results
            ]
            if round_index == 0:
                asked_this_round: list[Mapping[str, Any]] = []
            else:
                asked_this_round = [
                    item
                    for result in cohort_results
                    for item in _selected_rounds(result)
                    if int(item["round"]) == round_index
                ]
            observed_counts = [
                int(item["remaining_hypothesis_count"]) for item in asked_this_round
            ]
            round_eliminated = [
                len(item.get("eliminated_hypothesis_ids", ()))
                for item in asked_this_round
            ]
            carried_forward = 0
            if round_index > 0:
                carried_forward = sum(
                    not any(
                        item.get("selected") and int(item["round"]) == round_index
                        for item in result["rounds"]
                    )
                    for result in cohort_results
                )
            previous_resolved = 0
            if round_index > 0:
                previous_resolved = sum(
                    bool(result["correctly_resolved"])
                    and int(result["question_count"]) <= round_index - 1
                    for result in cohort_results
                )

            trajectory_rows.append(
                {
                    "method": method,
                    "method_label": METHOD_LABELS.get(method, method),
                    "round": round_index,
                    "fixed_cohort_size": len(cohort_results),
                    "cumulative_resolved_count": resolved,
                    "cumulative_resolution_rate": round(
                        resolved / len(cohort_results), 6
                    ),
                    "newly_resolved_count": resolved - previous_resolved,
                    "fixed_cohort_mean_active_hypotheses": _round_float(
                        _mean(fixed_counts)
                    ),
                    "fixed_cohort_terminal_states_carried_forward_count": carried_forward,
                    "selected_question_count_this_round": len(asked_this_round),
                    "observed_question_subset_mean_active_after_question": _round_float(
                        _mean(observed_counts)
                    ),
                    "mean_hypotheses_eliminated_per_selected_question_this_round": _round_float(
                        _mean(round_eliminated)
                    ),
                }
            )
            resolution_row[f"resolved_after_round_{round_index}_count"] = resolved
            resolution_row[f"resolved_after_round_{round_index}_rate"] = round(
                resolved / len(cohort_results), 6
            )

        resolution_rows.append(resolution_row)

    return resolution_rows, trajectory_rows


def validate_headline_totals(
    resolution_rows: Sequence[Mapping[str, Any]],
    *,
    expected: Mapping[str, int] = EXPECTED_FINAL_RESOLUTIONS,
    final_round: int = 3,
    expected_denominator: int = 57,
) -> None:
    """Fail loudly if the committed Phase 1.1 headline values are not reproduced."""

    by_method = {row["method"]: row for row in resolution_rows}
    for method, expected_count in expected.items():
        if method not in by_method:
            raise ValueError(f"Missing expected method: {method}")
        row = by_method[method]
        if int(row["initially_solvable_count"]) != expected_denominator:
            raise ValueError(
                f"{method}: expected denominator {expected_denominator}, "
                f"got {row['initially_solvable_count']}"
            )
        actual = int(row[f"resolved_after_round_{final_round}_count"])
        if actual != expected_count:
            raise ValueError(
                f"{method}: expected {expected_count} final resolutions, got {actual}"
            )


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"Cannot write empty CSV: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def read_trajectory_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def generate_figure_from_csv(
    trajectory_path: Path, png_path: Path, svg_path: Path
) -> None:
    """Generate both figure formats from the saved auditable trajectory CSV."""

    os.environ.setdefault(
        "MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "cs3263-matplotlib")
    )
    import matplotlib as mpl

    mpl.use("Agg")
    mpl.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 9.5,
            "axes.titlesize": 11,
            "axes.labelsize": 10,
            "legend.fontsize": 8.5,
            "svg.hashsalt": "cs3263-depth-analysis-v1",
        }
    )
    import matplotlib.pyplot as plt

    rows = read_trajectory_csv(trajectory_path)
    methods = list(dict.fromkeys(row["method"] for row in rows))
    plotted_rounds = sorted({int(row["round"]) for row in rows})
    figure, (resolution_axis, active_axis) = plt.subplots(
        1, 2, figsize=(12.0, 4.8), constrained_layout=True
    )

    for method in methods:
        method_rows = sorted(
            (row for row in rows if row["method"] == method),
            key=lambda row: int(row["round"]),
        )
        rounds = [int(row["round"]) for row in method_rows]
        rates = [100 * float(row["cumulative_resolution_rate"]) for row in method_rows]
        means = [
            float(row["fixed_cohort_mean_active_hypotheses"])
            for row in method_rows
        ]
        label = method_rows[0]["method_label"]
        style = "--" if method == "exact_objective_python" else "-"
        colour = METHOD_COLOURS.get(method)
        resolution_axis.plot(
            rounds,
            rates,
            marker="o",
            linewidth=2,
            markersize=4.5,
            linestyle=style,
            color=colour,
            label=label,
        )
        active_axis.plot(
            rounds,
            means,
            marker="o",
            linewidth=2,
            markersize=4.5,
            linestyle=style,
            color=colour,
            label=label,
        )

    resolution_axis.set_title("Cumulative correct resolution")
    resolution_axis.set_xlabel("Questions allowed")
    resolution_axis.set_ylabel("Initially solvable scenarios resolved (%)")
    resolution_axis.set_xticks(plotted_rounds)
    resolution_axis.set_ylim(0, 85)
    resolution_axis.grid(axis="y", alpha=0.25)
    resolution_axis.text(
        0.02,
        0.97,
        "Fixed denominator: 57 scenarios",
        transform=resolution_axis.transAxes,
        va="top",
        fontsize=8.5,
        color="#444444",
    )
    resolution_axis.text(
        0.98,
        0.03,
        "Exact Python overlaps compositional Prolog",
        transform=resolution_axis.transAxes,
        ha="right",
        va="bottom",
        fontsize=8,
        color="#444444",
    )

    active_axis.set_title("Remaining active hypotheses")
    active_axis.set_xlabel("Questions allowed")
    active_axis.set_ylabel("Mean active hypotheses")
    active_axis.set_xticks(plotted_rounds)
    active_axis.set_ylim(bottom=1)
    active_axis.grid(axis="y", alpha=0.25)
    active_axis.text(
        0.02,
        0.97,
        "Same 57 scenarios; terminal states carried forward",
        transform=active_axis.transAxes,
        va="top",
        fontsize=8.5,
        color="#444444",
    )

    handles, labels = active_axis.get_legend_handles_labels()
    figure.legend(
        handles,
        labels,
        loc="outside lower center",
        ncol=5,
        frameon=False,
    )
    figure.suptitle(
        "Multi-round uncertainty reduction under the controlled response model",
        fontsize=12,
        fontweight="bold",
    )
    png_path.parent.mkdir(parents=True, exist_ok=True)
    svg_path.parent.mkdir(parents=True, exist_ok=True)
    metadata = {"Creator": "evaluation.depth_analysis", "Date": None}
    figure.savefig(png_path, dpi=200, metadata=metadata)
    figure.savefig(svg_path, metadata=metadata)
    plt.close(figure)


def run_multi_round_analysis(
    input_path: Path, output_directory: Path
) -> dict[str, Any]:
    """Write the Experiment 1 CSVs and figure pair."""

    results = load_results(input_path)
    resolution_rows, trajectory_rows = analyse_multi_round(results)
    validate_headline_totals(resolution_rows)

    resolution_path = output_directory / "multi_round_resolution.csv"
    trajectory_path = output_directory / "multi_round_trajectory.csv"
    png_path = output_directory / "fig_multi_round_resolution.png"
    svg_path = output_directory / "fig_multi_round_resolution.svg"
    write_csv(resolution_path, resolution_rows)
    write_csv(trajectory_path, trajectory_rows)
    generate_figure_from_csv(trajectory_path, png_path, svg_path)

    return {
        "input": str(input_path),
        "input_sha256": sha256(input_path),
        "fixed_cohort_size": resolution_rows[0]["initially_solvable_count"],
        "outputs": [
            str(resolution_path),
            str(trajectory_path),
            str(png_path),
            str(svg_path),
        ],
        "final_resolutions": {
            row["method"]: row["resolved_after_round_3_count"]
            for row in resolution_rows
        },
    }

