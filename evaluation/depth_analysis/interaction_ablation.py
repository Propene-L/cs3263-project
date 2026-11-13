"""Controlled evaluation-only ablation of corrected-v2 interaction inference."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import statistics
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence

from evaluation.depth_analysis.multi_round import write_csv
from evaluation.evaluate_preference_state_corrected import (
    evaluate_result,
    make_state,
    read_jsonl,
    signature,
)
from museum_guide.preference_state import (
    PreferenceStateEngine,
    default_preference_state_engine,
)


CONDITIONS = ("full_corrected_v2", "no_interaction_ablation")
METRICS = (
    "primary_explanation_accuracy",
    "explanation_precision",
    "explanation_recall",
    "false_interaction_rate",
    "false_atomic_interest_rate",
    "action_type_accuracy",
    "top1_relevance",
    "appropriate_abstention",
)
CATEGORY_ORDER = (
    "true_atomic",
    "multiple_independent",
    "true_conjunction",
    "noisy",
    "contradictory",
    "missing_evidence",
    "ambiguous",
    "explicit_correction",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _mean(values: Sequence[float | int | bool | None]) -> float | None:
    filtered = [float(value) for value in values if value is not None]
    return round(statistics.fmean(filtered), 6) if filtered else None


def make_ablation_engine(root: Path) -> PreferenceStateEngine:
    return PreferenceStateEngine(
        facts_path=root / "logic" / "clarification_generated_facts.pl",
        hypotheses_path=root / "logic" / "clarification_hypotheses.pl",
        rules_path=root
        / "evaluation"
        / "depth_analysis"
        / "preference_state_no_interaction_rules.pl",
        entry_point="write_corrected_preference_state_json",
        evidence_path=root / "data" / "curated" / "clarification_evidence.json",
    )


def _stable_result(result: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "preference_explanations": result["preference_explanations"],
        "primary_explanation": result.get("primary_explanation"),
        "ranked_actions": result["ranked_actions"],
        "decision": result["decision"],
        "unresolved_explanation_count": result["unresolved_explanation_count"],
        "active_observation_ids": result["active_observation_ids"],
        "superseded_observation_ids": result["superseded_observation_ids"],
        "observation_evidence": result["observation_evidence"],
    }


def _question_key(result: Mapping[str, Any]) -> tuple[str, tuple[str, ...]] | None:
    question = result["decision"].get("question")
    if not question:
        return None
    explanation = question["explanation"]
    return explanation["kind"], tuple(sorted(explanation["components"]))


def _primary_key(result: Mapping[str, Any]) -> tuple[str, tuple[str, ...]] | None:
    primary = result.get("primary_explanation")
    if not primary:
        return None
    return primary["kind"], tuple(sorted(primary["components"]))


def _explanation_signature(result: Mapping[str, Any]) -> list[tuple[Any, ...]]:
    return sorted(
        (
            item["kind"],
            tuple(sorted(item["components"])),
            item["status"],
        )
        for item in result["preference_explanations"]
    )


def _change_record(full: Mapping[str, Any], ablated: Mapping[str, Any]) -> dict[str, Any]:
    full_explanations = _explanation_signature(full)
    ablated_explanations = _explanation_signature(ablated)
    removed = [item for item in full_explanations if item not in ablated_explanations]
    decision_changed = full["decision"]["action_type"] != ablated["decision"]["action_type"]
    recommendation_changed = full["decision"].get("artwork_id") != ablated["decision"].get(
        "artwork_id"
    )
    question_changed = _question_key(full) != _question_key(ablated)
    explanation_changed = full_explanations != ablated_explanations
    if not any((explanation_changed, decision_changed, recommendation_changed, question_changed)):
        outcome = "no_change"
    elif decision_changed:
        outcome = f"action_{full['decision']['action_type']}_to_{ablated['decision']['action_type']}"
    elif recommendation_changed:
        outcome = "recommendation_changed"
    elif question_changed:
        outcome = "different_clarification_question"
    else:
        outcome = "explanation_only_change"
    return {
        "explanation_set_changed": explanation_changed,
        "primary_explanation_changed": _primary_key(full) != _primary_key(ablated),
        "action_type_changed": decision_changed,
        "recommendation_changed": recommendation_changed,
        "clarification_question_changed": question_changed,
        "removed_explanations": [
            {"kind": kind, "components": list(components), "status": status}
            for kind, components, status in removed
        ],
        "ablation_outcome": outcome,
    }


def _clarification_counts(items: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    tp = sum(
        item["expected_action_type"] == "clarify"
        and item["result"]["decision"]["action_type"] == "clarify"
        for item in items
    )
    fp = sum(
        item["expected_action_type"] != "clarify"
        and item["result"]["decision"]["action_type"] == "clarify"
        for item in items
    )
    fn = sum(
        item["expected_action_type"] == "clarify"
        and item["result"]["decision"]["action_type"] != "clarify"
        for item in items
    )
    return {
        "clarification_true_positive_count": tp,
        "clarification_false_positive_count": fp,
        "clarification_false_negative_count": fn,
        "clarification_necessity_precision": round(tp / (tp + fp), 6)
        if tp + fp
        else None,
        "clarification_necessity_recall": round(tp / (tp + fn), 6)
        if tp + fn
        else None,
    }


def _summarize_condition(
    scenario_rows: Sequence[Mapping[str, Any]], condition: str
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for category in (*CATEGORY_ORDER, "overall"):
        selected = [
            row
            for row in scenario_rows
            if category == "overall" or row["category"] == category
        ]
        items = [
            {
                "expected_action_type": row["expected_action_type"],
                "result": row["conditions"][condition]["result"],
                "metrics": row["conditions"][condition]["metrics"],
            }
            for row in selected
        ]
        summary = {
            "condition": condition,
            "category": category,
            "scenario_count": len(items),
            "world_count": sum(row["world_count"] for row in selected),
        }
        for metric in METRICS:
            summary[metric] = _mean([item["metrics"][metric] for item in items])
        summary.update(_clarification_counts(items))
        rows.append(summary)
    return rows


def validate_full_against_saved(
    scenario_rows: Sequence[Mapping[str, Any]], saved_path: Path
) -> None:
    saved = json.loads(saved_path.read_text(encoding="utf-8"))
    saved_by_id = {row["scenario_id"]: row for row in saved["scenarios"]}
    for row in scenario_rows:
        expected = saved_by_id[row["scenario_id"]]["methods"]["compositional_prolog"]
        if "result" not in expected:
            raise ValueError(f"Saved full result missing for {row['scenario_id']}")
        if signature(row["conditions"]["full_corrected_v2"]["result"]) != signature(
            expected["result"]
        ):
            raise ValueError(
                f"Full corrected-v2 behavior changed for {row['scenario_id']}"
            )


def evaluate_ablation(
    root: Path,
    scenario_path: Path,
    evidence_path: Path,
    saved_full_path: Path,
) -> dict[str, Any]:
    scenarios = read_jsonl(scenario_path)
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    engines = {
        "full_corrected_v2": default_preference_state_engine(root),
        "no_interaction_ablation": make_ablation_engine(root),
    }
    scenario_rows: list[dict[str, Any]] = []
    for scenario in scenarios:
        state = make_state(scenario)
        conditions: dict[str, Any] = {}
        for condition, engine in engines.items():
            result = engine.infer(state)
            metrics = evaluate_result(result, scenario, state, evidence)
            metrics.pop("runtime_ms", None)
            conditions[condition] = {
                "result": _stable_result(result),
                "metrics": metrics,
            }
        change = _change_record(
            conditions["full_corrected_v2"]["result"],
            conditions["no_interaction_ablation"]["result"],
        )
        scenario_rows.append(
            {
                "scenario_id": scenario["scenario_id"],
                "category": scenario["category"],
                "subset": scenario["subset"],
                "world_count": len(scenario["worlds"]),
                "expected_action_type": scenario["expected_action_type"],
                "conditions": conditions,
                "changes": change,
            }
        )
    validate_full_against_saved(scenario_rows, saved_full_path)
    summary_rows = [
        item
        for condition in CONDITIONS
        for item in _summarize_condition(scenario_rows, condition)
    ]
    changes = {
        field: sum(bool(row["changes"][field]) for row in scenario_rows)
        for field in (
            "explanation_set_changed",
            "primary_explanation_changed",
            "action_type_changed",
            "recommendation_changed",
            "clarification_question_changed",
        )
    }
    changes["scenario_ids_with_any_change"] = [
        row["scenario_id"]
        for row in scenario_rows
        if any(
            row["changes"][field]
            for field in (
                "explanation_set_changed",
                "action_type_changed",
                "recommendation_changed",
                "clarification_question_changed",
            )
        )
    ]
    return {
        "schema_version": "1.0",
        "policy_full": "corrected_v2",
        "policy_ablation": "corrected_v2 with only c_interaction/3 disabled",
        "scenario_count": len(scenarios),
        "scenario_unit_count": len(scenarios),
        "world_count": sum(len(scenario["worlds"]) for scenario in scenarios),
        "multi_world_policy": "average worlds within each scenario before aggregation",
        "source_sha256": {
            str(scenario_path.relative_to(root)): _sha256(scenario_path),
            str(evidence_path.relative_to(root)): _sha256(evidence_path),
            "logic/preference_state_corrected_rules.pl": _sha256(
                root / "logic" / "preference_state_corrected_rules.pl"
            ),
            "evaluation/depth_analysis/preference_state_no_interaction_rules.pl": _sha256(
                root
                / "evaluation"
                / "depth_analysis"
                / "preference_state_no_interaction_rules.pl"
            ),
        },
        "summary": summary_rows,
        "change_counts": changes,
        "scenarios": scenario_rows,
    }


def generate_ablation_figure(csv_path: Path, png_path: Path, svg_path: Path) -> None:
    os.environ.setdefault(
        "MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "cs3263-matplotlib")
    )
    import matplotlib as mpl

    mpl.use("Agg")
    mpl.rcParams.update(
        {"font.family": "DejaVu Sans", "font.size": 9, "svg.hashsalt": "cs3263-ablation-v1"}
    )
    import matplotlib.pyplot as plt
    import numpy as np

    with csv_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    categories = (
        "true_conjunction",
        "multiple_independent",
        "noisy",
        "ambiguous",
    )
    labels = ("True conjunction", "Independent", "Noisy", "Ambiguous")
    x = np.arange(len(categories))
    width = 0.36
    figure, axes = plt.subplots(1, 2, figsize=(11.5, 4.8), constrained_layout=True)
    colours = {"full_corrected_v2": "#0072B2", "no_interaction_ablation": "#E69F00"}
    condition_labels = {
        "full_corrected_v2": "Full corrected-v2",
        "no_interaction_ablation": "No inferred interaction",
    }
    for axis, metric, title in (
        (axes[0], "primary_explanation_accuracy", "Primary-explanation accuracy"),
        (axes[1], "false_interaction_rate", "False-interaction rate"),
    ):
        for index, condition in enumerate(CONDITIONS):
            values = [
                100
                * float(
                    next(
                        row[metric]
                        for row in rows
                        if row["condition"] == condition and row["category"] == category
                    )
                )
                for category in categories
            ]
            bars = axis.bar(
                x + (index - 0.5) * width,
                values,
                width,
                label=condition_labels[condition],
                color=colours[condition],
            )
            axis.bar_label(bars, fmt="%.0f", padding=2, fontsize=8)
        axis.set_title(title)
        axis.set_xticks(x, labels, rotation=18, ha="right")
        axis.set_ylim(0, 110)
        axis.set_ylabel("Scenario-level mean (%)")
        axis.grid(axis="y", alpha=0.25)
    handles, labels_out = axes[0].get_legend_handles_labels()
    figure.legend(handles, labels_out, loc="outside lower center", ncol=2, frameon=False)
    figure.suptitle("Ablating inferred conjunctions: c_interaction/3", fontweight="bold")
    metadata = {"Creator": "evaluation.depth_analysis", "Date": None}
    figure.savefig(png_path, dpi=200, metadata=metadata)
    figure.savefig(svg_path, metadata=metadata)
    plt.close(figure)


def write_findings(result: Mapping[str, Any], path: Path) -> None:
    summary = {
        (row["condition"], row["category"]): row for row in result["summary"]
    }
    changes = result["change_counts"]
    changed_ids = changes["scenario_ids_with_any_change"]
    lines = [
        "# Interaction-inference ablation findings",
        "",
        "The ablation executed the same corrected-v2 Prolog policy, facts, observations, "
        "candidate sets, ranking, and decision rules while replacing only `c_interaction/3` "
        "with failure. The production rule file was not edited. Alternative authored worlds "
        "were averaged within each of the 32 scenarios; the 36 worlds were not treated as "
        "independent samples.",
        "",
        "## Category results",
        "",
        "| Category | Full primary accuracy | Ablated primary accuracy | Full false interaction | Ablated false interaction | Full action accuracy | Ablated action accuracy |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for category in CATEGORY_ORDER:
        full = summary[("full_corrected_v2", category)]
        ablated = summary[("no_interaction_ablation", category)]
        lines.append(
            f"| {category} | {100*full['primary_explanation_accuracy']:.1f}% | "
            f"{100*ablated['primary_explanation_accuracy']:.1f}% | "
            f"{100*full['false_interaction_rate']:.1f}% | "
            f"{100*ablated['false_interaction_rate']:.1f}% | "
            f"{100*full['action_type_accuracy']:.1f}% | "
            f"{100*ablated['action_type_accuracy']:.1f}% |"
        )
    lines.extend(
        [
            "",
            "## Causal interpretation",
            "",
            f"The explanation set changed in **{changes['explanation_set_changed']}/32** scenarios; "
            f"the action type changed in **{changes['action_type_changed']}/32**, the selected "
            f"recommendation in **{changes['recommendation_changed']}/32**, and the clarification "
            f"question in **{changes['clarification_question_changed']}/32**. Changed scenario IDs: "
            + (", ".join(f"`{item}`" for item in changed_ids) or "none")
            + ".",
            "",
            "1. **True conjunctions:** all four robustness cases state their conjunction explicitly. "
            "They therefore remain available through `c_explicit/5`; disabling inferred interaction "
            "does not remove them. This benchmark cannot attribute their accuracy to `c_interaction/3`.",
            "2. **Independent interests:** the guard against combining separately confirmed interests "
            "already prevents inferred conjunctions, so the ablation should have no benefit here.",
            "3. **Ambiguous evidence:** the changed cases show whether the provisional interaction is "
            "removed and whether the system asks an atomic rather than conjunctive clarification. "
            "This is the main measured effect of the rule.",
            "   In `ambiguous_albert`, the full policy asked whether Expressionist style and portrait "
            "genre formed a conjunction; the ablation instead asked about Expressionism movement. "
            "Removing the inferred interaction eliminated the category's 12.5% false-interaction "
            "rate, but also reduced explanation recall from 100.0% to 87.5% and top-1 relevance "
            "from 87.5% to 75.0% under the two-world scenario average.",
            "4. **Non-conjunction categories:** unchanged results are a useful isolation check. Any "
            "change outside scenarios containing an inferred interaction would indicate an over-broad ablation.",
            "",
            "## Limitations",
            "",
            "The 32 scenarios were authored controlled worlds, not observations from museum visitors. "
            "The true-conjunction category exercises explicit representation rather than inferred "
            "conjunction discovery, so a future independently reviewed benchmark would be required to "
            "estimate the accuracy benefit of `c_interaction/3` on genuinely latent conjunctions.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def run_interaction_ablation(root: Path, output_directory: Path) -> dict[str, Any]:
    scenario_path = root / "evaluation" / "preference_state_robustness_scenarios.jsonl"
    evidence_path = root / "data" / "curated" / "clarification_evidence.json"
    saved_path = root / "evaluation" / "preference_state_corrected_results.json"
    result = evaluate_ablation(root, scenario_path, evidence_path, saved_path)
    json_path = output_directory / "interaction_ablation_results.json"
    csv_path = output_directory / "interaction_ablation_summary.csv"
    png_path = output_directory / "fig_interaction_ablation.png"
    svg_path = output_directory / "fig_interaction_ablation.svg"
    findings_path = output_directory / "interaction_ablation_findings.md"
    json_path.write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    write_csv(csv_path, result["summary"])
    generate_ablation_figure(csv_path, png_path, svg_path)
    write_findings(result, findings_path)
    return {
        "scenario_count": result["scenario_count"],
        "world_count": result["world_count"],
        "change_counts": result["change_counts"],
        "outputs": [
            str(json_path),
            str(csv_path),
            str(png_path),
            str(svg_path),
            str(findings_path),
        ],
    }

