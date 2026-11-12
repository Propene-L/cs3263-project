"""Decompose saved direct-LLM failures without making API calls."""

from __future__ import annotations

import csv
import json
import os
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any

from evaluation.depth_analysis.multi_round import write_csv


LLM_METHOD = "direct_llm_state_reasoning"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def analyse_llm_failures(root: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    normalized = _load(root / "evaluation" / "preference_state_llm_normalized_results.json")
    final = _load(root / "evaluation" / "preference_state_llm_final_comparison_results.json")
    diagnostic = _load(root / "evaluation" / "preference_state_llm_invalid_diagnostic.json")
    scenarios = {}
    for filename in (
        "preference_state_corrected_scenarios.jsonl",
        "preference_state_robustness_scenarios.jsonl",
    ):
        for line in (root / "evaluation" / filename).read_text(encoding="utf-8").splitlines():
            if line.strip():
                item = json.loads(line)
                scenarios[item["scenario_id"]] = item

    accepted = []
    decision_valid = []
    action_correct_accepted = []
    action_correct_valid_decision = []
    action_error_records: list[dict[str, Any]] = []
    invalid_decision_records: list[dict[str, Any]] = []
    for row in final["scenarios"]:
        scenario_id = row["scenario_id"]
        item = row["methods"][LLM_METHOD]
        if "metrics" not in item:
            continue
        accepted.append(scenario_id)
        metrics = item["metrics"]
        valid = bool(metrics["decision_validity"])
        correct = bool(metrics["action_type_accuracy"])
        if valid:
            decision_valid.append(scenario_id)
        if correct:
            action_correct_accepted.append(scenario_id)
        if valid and correct:
            action_correct_valid_decision.append(scenario_id)
        expected = scenarios[scenario_id]["expected_action_type"]
        predicted = item["decision"]["action_type"]
        if not valid:
            invalid_decision_records.append(
                {
                    "scenario_id": scenario_id,
                    "category": row["category"],
                    "expected_action": expected,
                    "predicted_action": predicted,
                }
            )
        elif not correct:
            action_error_records.append(
                {
                    "scenario_id": scenario_id,
                    "category": row["category"],
                    "expected_action": expected,
                    "predicted_action": predicted,
                }
            )

    denominator = int(final["scenario_count"])
    summary_metrics = [
        ("strict_structured_output_validity", int(normalized["strict_valid_count"]), denominator),
        (
            "validity_after_exact_label_normalization",
            int(normalized["normalized_valid_count"]),
            denominator,
        ),
        ("accepted_outputs_after_contract_repair", len(accepted), denominator),
        ("valid_decisions_after_repair", len(decision_valid), denominator),
        (
            "action_correctness_given_accepted_output",
            len(action_correct_accepted),
            len(accepted),
        ),
        (
            "action_correctness_given_valid_decision",
            len(action_correct_valid_decision),
            len(decision_valid),
        ),
        ("end_to_end_action_correctness", len(action_correct_accepted), denominator),
    ]
    rows: list[dict[str, Any]] = []
    for metric, numerator, metric_denominator in summary_metrics:
        rows.append(
            {
                "record_type": "summary_metric",
                "metric": metric,
                "numerator": numerator,
                "denominator": metric_denominator,
                "rate": round(numerator / metric_denominator, 6),
                "scenario_id": "",
                "category": "",
                "expected_action": "",
                "predicted_action": "",
                "error": "",
                "notes": "",
            }
        )
    total_requests = int(final["api_request_accounting"]["total_requests"])
    rows.append(
        {
            "record_type": "request_accounting",
            "metric": "total_requests_across_both_passes",
            "numerator": total_requests,
            "denominator": "",
            "rate": "",
            "scenario_id": "",
            "category": "",
            "expected_action": "",
            "predicted_action": "",
            "error": "",
            "notes": "56 initial + 21 targeted rerun requests; not an equal-budget comparison",
        }
    )
    for item in final["remaining_errors"]:
        scenario = scenarios[item["scenario_id"]]
        rows.append(
            {
                "record_type": "remaining_output_failure",
                "metric": "",
                "numerator": "",
                "denominator": "",
                "rate": "",
                "scenario_id": item["scenario_id"],
                "category": scenario.get("category", scenario.get("family", "")),
                "expected_action": scenario["expected_action_type"],
                "predicted_action": "invalid",
                "error": item["error"],
                "notes": "schema/serialization failure after targeted repair",
            }
        )
    for item in invalid_decision_records:
        rows.append(
            {
                "record_type": "schema_valid_invalid_decision",
                "metric": "",
                "numerator": "",
                "denominator": "",
                "rate": "",
                **item,
                "error": "decision violated deterministic output validity checks",
                "notes": "accepted structured output, invalid decision",
            }
        )
    for item in action_error_records:
        rows.append(
            {
                "record_type": "valid_decision_reasoning_error",
                "metric": "",
                "numerator": "",
                "denominator": "",
                "rate": "",
                **item,
                "error": "",
                "notes": "decision was schema-valid but action type disagreed with authored label",
            }
        )

    diagnostic_causes = Counter(item["cause"] for item in diagnostic["rows"])
    action_error_types = Counter(
        f"{item['expected_action']}->{item['predicted_action']}"
        for item in action_error_records
    )
    metadata = {
        "scenario_count": denominator,
        "strict_valid_count": int(normalized["strict_valid_count"]),
        "normalized_valid_count": int(normalized["normalized_valid_count"]),
        "accepted_after_repair_count": len(accepted),
        "valid_decision_count": len(decision_valid),
        "action_correct_count": len(action_correct_accepted),
        "total_requests": total_requests,
        "remaining_output_failure_count": len(final["remaining_errors"]),
        "invalid_decision_count": len(invalid_decision_records),
        "valid_decision_action_error_count": len(action_error_records),
        "diagnostic_cause_counts_before_targeted_rerun": dict(diagnostic_causes),
        "valid_decision_action_error_types": dict(action_error_types),
        "no_api_calls_made": True,
    }
    return rows, metadata


def generate_llm_figure(csv_path: Path, png_path: Path, svg_path: Path) -> None:
    os.environ.setdefault(
        "MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "cs3263-matplotlib")
    )
    import matplotlib as mpl

    mpl.use("Agg")
    mpl.rcParams.update(
        {"font.family": "DejaVu Sans", "font.size": 9.5, "svg.hashsalt": "cs3263-llm-failures-v1"}
    )
    import matplotlib.pyplot as plt

    with csv_path.open(encoding="utf-8", newline="") as handle:
        rows = {
            row["metric"]: row
            for row in csv.DictReader(handle)
            if row["record_type"] == "summary_metric"
        }
    metrics = (
        "strict_structured_output_validity",
        "validity_after_exact_label_normalization",
        "accepted_outputs_after_contract_repair",
        "valid_decisions_after_repair",
        "end_to_end_action_correctness",
    )
    labels = (
        "Strict\nID-only",
        "After exact-label\nnormalization",
        "Accepted after\nrepair",
        "Valid\ndecisions",
        "Correct action\nend-to-end",
    )
    counts = [int(rows[metric]["numerator"]) for metric in metrics]
    denominator = int(rows[metrics[0]]["denominator"])
    figure, axis = plt.subplots(figsize=(9.4, 4.9), constrained_layout=True)
    colours = ["#D55E00", "#E69F00", "#56B4E9", "#0072B2", "#009E73"]
    bars = axis.bar(labels, counts, color=colours, width=0.68)
    axis.bar_label(
        bars,
        labels=[f"{count}/{denominator}\n({100*count/denominator:.1f}%)" for count in counts],
        padding=3,
        fontsize=9,
    )
    axis.set_ylim(0, 60)
    axis.set_ylabel("Scenarios (fixed denominator 56)")
    axis.set_title("Direct-LLM output and decision failure decomposition")
    axis.grid(axis="y", alpha=0.25)
    axis.text(
        0.99,
        0.96,
        "77 requests: 56 initial + 21 targeted reruns",
        transform=axis.transAxes,
        ha="right",
        va="top",
        fontsize=8.5,
        color="#444444",
    )
    metadata = {"Creator": "evaluation.depth_analysis", "Date": None}
    figure.savefig(png_path, dpi=200, metadata=metadata)
    figure.savefig(svg_path, metadata=metadata)
    plt.close(figure)


def run_llm_failure_analysis(root: Path, output_directory: Path) -> dict[str, Any]:
    rows, metadata = analyse_llm_failures(root)
    csv_path = output_directory / "llm_failure_decomposition.csv"
    png_path = output_directory / "fig_llm_failure_decomposition.png"
    svg_path = output_directory / "fig_llm_failure_decomposition.svg"
    write_csv(csv_path, rows)
    generate_llm_figure(csv_path, png_path, svg_path)
    return {**metadata, "outputs": [str(csv_path), str(png_path), str(svg_path)]}

