"""Summarize saved clarification timing and question-quality audits."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from evaluation.depth_analysis.multi_round import write_csv


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _bool(value: str) -> bool | None:
    if value == "True":
        return True
    if value == "False":
        return False
    return None


def analyse_clarification_decisions(root: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    base = root / "evaluation" / "clarification_analysis"
    onepass = _load_json(base / "onepass_robustness_summary.json")
    final = _load_json(base / "final_robustness_summary.json")
    diagnostic = _load_json(
        root
        / "evaluation"
        / "diagnostic_question_analysis"
        / "diagnostic_question_summary.json"
    )
    question_rows = _load_csv(base / "final_robustness_questions.csv")
    diagnostic_rows = _load_csv(
        root
        / "evaluation"
        / "diagnostic_question_analysis"
        / "final_competitive_questions.csv"
    )
    rows: list[dict[str, Any]] = []
    for source_name, source in (("onepass", onepass), ("final_repaired", final)):
        for method, metrics in source["methods"].items():
            rows.append(
                {
                    "record_type": "stage_1_when_to_ask",
                    "source": source_name,
                    "scenario_id": "",
                    "method": method,
                    "scenario_count": metrics["scenario_count"],
                    "expected_clarification_count": metrics[
                        "expected_clarification_count"
                    ],
                    "tp": metrics["tp"],
                    "fp": metrics["fp"],
                    "fn": metrics["fn_valid"] + metrics["fn_invalid"],
                    "precision": metrics["clarification_precision"],
                    "recall": metrics[
                        "clarification_recall_including_invalid_as_missed"
                    ],
                    "asked_count": metrics["clarification_questions_asked"],
                    "grounding_rate_given_asked": metrics[
                        "question_grounding_rate_given_asked"
                    ],
                    "competitive_diagnostic_rate_given_asked": "",
                    "diagnostic_when_needed_count": "",
                    "multi_world_questions_asked": metrics[
                        "ambiguous_multi_world_questions_asked"
                    ],
                    "multi_world_split_count": metrics[
                        "questions_splitting_multi_world_profiles"
                    ],
                    "world_information_gain_bits": metrics[
                        "mean_oracle_world_information_gain_bits"
                    ],
                    "question_components": "",
                    "question_grounded": "",
                    "world_split": "",
                    "notes": "invalid output counts as missed clarification when clarification was expected",
                }
            )
    competitive = diagnostic["sources"]["final"]["competitive"]
    for method, metrics in competitive.items():
        final_metrics = final["methods"][method]
        rows.append(
            {
                "record_type": "stage_2_what_to_ask",
                "source": "final_repaired",
                "scenario_id": "",
                "method": method,
                "scenario_count": metrics["total_scenarios"],
                "expected_clarification_count": metrics[
                    "expected_clarification_count"
                ],
                "tp": "",
                "fp": "",
                "fn": "",
                "precision": "",
                "recall": "",
                "asked_count": metrics["asked_count"],
                "grounding_rate_given_asked": final_metrics[
                    "question_grounding_rate_given_asked"
                ],
                "competitive_diagnostic_rate_given_asked": metrics[
                    "diagnostic_targeting_rate_given_asked"
                ],
                "diagnostic_when_needed_count": metrics[
                    "diagnostic_when_needed_count"
                ],
                "multi_world_questions_asked": final_metrics[
                    "ambiguous_multi_world_questions_asked"
                ],
                "multi_world_split_count": final_metrics[
                    "questions_splitting_multi_world_profiles"
                ],
                "world_information_gain_bits": final_metrics[
                    "mean_oracle_world_information_gain_bits"
                ],
                "question_components": "",
                "question_grounded": "",
                "world_split": "",
                "notes": "quality rates are conditional on the method having asked",
            }
        )

    by_scenario: dict[str, list[dict[str, str]]] = {}
    for item in question_rows:
        if item["asked_clarification"] == "True":
            by_scenario.setdefault(item["scenario_id"], []).append(item)
    both_asked = sorted(
        scenario_id
        for scenario_id, items in by_scenario.items()
        if {item["method"] for item in items}
        >= {"compositional_prolog", "direct_llm_state_reasoning"}
    )
    diagnostic_lookup = {
        (item["scenario_id"], item["method"]): item for item in diagnostic_rows
    }
    paired_details = []
    for scenario_id in both_asked:
        for item in sorted(by_scenario[scenario_id], key=lambda row: row["method"]):
            detail = diagnostic_lookup[(scenario_id, item["method"])]
            record = {
                "record_type": "matched_both_asked_case",
                "source": "final_repaired",
                "scenario_id": scenario_id,
                "method": item["method"],
                "scenario_count": "",
                "expected_clarification_count": "",
                "tp": "",
                "fp": "",
                "fn": "",
                "precision": "",
                "recall": "",
                "asked_count": 1,
                "grounding_rate_given_asked": "",
                "competitive_diagnostic_rate_given_asked": "",
                "diagnostic_when_needed_count": "",
                "multi_world_questions_asked": item["world_count"],
                "multi_world_split_count": "",
                "world_information_gain_bits": item["world_information_gain_bits"],
                "question_components": item["question_components"],
                "question_grounded": item["question_grounded"],
                "world_split": item["world_split"],
                "notes": (
                    "competitive_diagnostic="
                    + detail["diagnostic_candidate"]
                    + "; structural_proxy_bits="
                    + detail["structural_proxy_bits"]
                ),
            }
            rows.append(record)
            paired_details.append(
                {
                    "scenario_id": scenario_id,
                    "method": item["method"],
                    "components": json.loads(item["question_components"]),
                    "grounded": _bool(item["question_grounded"]),
                    "diagnostic": _bool(detail["diagnostic_candidate"]),
                    "world_split": _bool(item["world_split"]),
                    "world_information_gain_bits": (
                        float(item["world_information_gain_bits"])
                        if item["world_information_gain_bits"]
                        else None
                    ),
                }
            )
    metadata = {
        "scenario_count": 32,
        "both_asked_scenario_count": len(both_asked),
        "both_asked_scenario_ids": both_asked,
        "paired_details": paired_details,
        "counterfactual": final["counterfactual_shared_prolog_updater"],
        "no_new_llm_calls": True,
    }
    return rows, metadata


def write_analysis(metadata: dict[str, Any], root: Path, path: Path) -> None:
    final = _load_json(
        root / "evaluation" / "clarification_analysis" / "final_robustness_summary.json"
    )
    onepass = _load_json(
        root
        / "evaluation"
        / "clarification_analysis"
        / "onepass_robustness_summary.json"
    )
    p_final = final["methods"]["compositional_prolog"]
    l_final = final["methods"]["direct_llm_state_reasoning"]
    l_one = onepass["methods"]["direct_llm_state_reasoning"]
    details = {
        (item["scenario_id"], item["method"]): item for item in metadata["paired_details"]
    }
    text = f"""# Clarification timing versus question quality

This analysis uses the existing 32-scenario robustness audit and saved LLM
outputs only. It separates the decision to ask from the quality of the selected
question.

## Stage 1 — when to ask

The authored `expected_action_type` is the clarification label; it is not a
human preference judgment. Compositional Prolog produced {p_final['tp']} true
positives, {p_final['fp']} false positives, and
{p_final['fn_valid'] + p_final['fn_invalid']} false negatives: precision and
recall were both {100*p_final['clarification_precision']:.1f}% (9/9 needed cases).

The one-pass LLM produced {l_one['tp']} TP, {l_one['fp']} FP, and
{l_one['fn_valid'] + l_one['fn_invalid']} FN, for
{100*l_one['clarification_precision']:.1f}% precision and
{100*l_one['clarification_recall_including_invalid_as_missed']:.1f}% recall.
After deterministic repair and targeted contract reruns it produced
{l_final['tp']} TP, {l_final['fp']} FP, and
{l_final['fn_valid'] + l_final['fn_invalid']} FN: precision and recall were
both {100*l_final['clarification_precision']:.1f}%. The repaired result uses
additional requests and is not an equal-budget single-shot comparison.

## Stage 2 — what to ask

Conditional on asking, Prolog grounded 9/9 questions in recorded positive
evidence and targeted a competitive explanation in 8/9. The repaired LLM
grounded 7/9 and targeted a competitive explanation in 6/9. These conditional
rates are selection-biased: every Prolog question occurred in a scenario whose
authored label required clarification, whereas only 3/9 LLM questions did; the
other six were false-positive clarifications. Accordingly, the effective
competitive diagnostic recall over the nine needed cases was 8/9 for Prolog
and 2/9 for the repaired LLM.

For multi-world scenarios, Prolog asked four questions and split the authored
worlds in three (mean oracle split entropy 0.75 bits). The repaired LLM asked in
one such scenario and split it (1.0 bit). This does not imply superior general
LLM question quality because the conditioning sets differ.

## Three matched cases where both asked

- `independent_feline_impressionist`: both methods asked about
  `h_feline_subject`; both questions were grounded and competitive-diagnostic.
- `noisy_water`: Prolog asked about `h_oil_medium`, which was grounded but not
  competitive-diagnostic under the audit. The LLM asked about
  `h_musical_subject`, which was neither grounded nor competitive-diagnostic.
- `ambiguous_cellist`: both questions were grounded and structurally
  diagnostic. Prolog asked about `h_expressionist_style`, which did not split
  the two authored worlds (0 bits); the LLM asked about `h_musical_subject`,
  which split them evenly (1 bit). This is the required counterexample to any
  claim that the Prolog question is always better.

Across these three matched scenarios, the common-updater replay increased mean
primary accuracy by 0.333 for the Prolog questions and 0.500 for the LLM
questions. The sample is only three selected cases.

## Counterfactual replay limitation

Both saved questions are answered by the same exact membership oracle and fed
into the same corrected Prolog updater. The replay therefore compares question
choice under a common update policy. It does **not** evaluate independent
multi-turn LLM adaptation, natural visitor replies, or a new LLM inference
after the answer. No new figure is generated because the existing
clarification chart plus the supporting CSV already expresses the timing and
quality separation without another redundant visualization.
"""
    path.write_text(text, encoding="utf-8", newline="\n")


def run_clarification_decision_analysis(
    root: Path, output_directory: Path
) -> dict[str, Any]:
    rows, metadata = analyse_clarification_decisions(root)
    csv_path = output_directory / "clarification_decision_summary.csv"
    markdown_path = output_directory / "clarification_decision_analysis.md"
    write_csv(csv_path, rows)
    write_analysis(metadata, root, markdown_path)
    return {**metadata, "outputs": [str(csv_path), str(markdown_path)]}

