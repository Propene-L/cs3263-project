"""Run fair, shared-horizon Phase 1.1 clarification experiments."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import statistics
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Sequence

from evaluation.exact_python_selector import ExactObjectivePythonSelector
from evaluation.shared_simulator import EvidenceModel, replay_responses
from museum_guide.clarification import (
    AskedQuestion,
    ClarificationObservation,
    ClarificationState,
    default_engine,
)
from museum_guide.clarification_baselines import (
    AttributeContrastSelector,
    BaselineQuestion,
    DirectLLMSelector,
    OpenAIResponsesTransport,
    RandomPairSelector,
    eligible_artworks,
)

ROOT = Path(__file__).resolve().parents[1]
METHODS = (
    "compositional_prolog",
    "single_rule_prolog",
    "raw_attribute_contrast",
    "random_eligible",
    "exact_objective_python",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--scenarios", default=str(ROOT / "evaluation" / "clarification_scenarios.jsonl")
    )
    parser.add_argument(
        "--output", default=str(ROOT / "evaluation" / "phase_1_1_results.json")
    )
    parser.add_argument(
        "--summary-csv", default=str(ROOT / "evaluation" / "phase_1_1_summary.csv")
    )
    parser.add_argument(
        "--trajectory-csv",
        default=str(ROOT / "evaluation" / "phase_1_1_round_trajectory.csv"),
    )
    parser.add_argument(
        "--visualization",
        default=str(ROOT / "evaluation" / "phase_1_1_comparison.svg"),
    )
    parser.add_argument(
        "--llm-output", default=str(ROOT / "evaluation" / "phase_1_1_llm_results.json")
    )
    parser.add_argument("--max-rounds", type=int, default=3)
    parser.add_argument("--run-direct-llm", action="store_true")
    parser.add_argument(
        "--llm-track",
        choices=("structured", "natural_language"),
        default="structured",
    )
    return parser.parse_args()


def load_jsonl(path: str | Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in Path(path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_state(scenario: dict[str, Any], mode: str = "compositional") -> ClarificationState:
    questions = tuple(
        AskedQuestion(
            id=item["id"],
            option_a_id=item["option_a_id"],
            option_b_id=item["option_b_id"],
            response_observation_id=item.get("response_observation_id"),
            response=item.get("response"),
        )
        for item in scenario.get("preloaded_questions", [])
    )
    return ClarificationState(
        session_id=scenario["scenario_id"],
        observations=tuple(
            ClarificationObservation(**item) for item in scenario["observations"]
        ),
        allowed_artwork_ids=tuple(scenario["allowed_artwork_ids"]),
        asked_questions=questions,
        rejected_hypothesis_ids=tuple(scenario["rejected_hypothesis_ids"]),
        mode=mode,
    )


def _symbolic_pair(result: dict[str, Any], method: str) -> BaselineQuestion | None:
    if result["status"] != "selected":
        return None
    question = result["question"]
    return BaselineQuestion(
        method=method,
        option_a_id=question["option_a"]["artwork_id"],
        option_b_id=question["option_b"]["artwork_id"],
        score=float(question["deterministic_score"]),
        metadata={"prolog_result": result},
    )


def _select(
    method: str,
    state: ClarificationState,
    active: Sequence[str],
    scenario: dict[str, Any],
    selectors: dict[str, Any],
) -> tuple[BaselineQuestion | None, dict[str, Any]]:
    if method in {"compositional_prolog", "single_rule_prolog"}:
        mode = "compositional" if method == "compositional_prolog" else "single_rule"
        symbolic_state = ClarificationState(
            session_id=state.session_id,
            observations=state.observations,
            allowed_artwork_ids=state.allowed_artwork_ids,
            asked_questions=state.asked_questions,
            rejected_hypothesis_ids=state.rejected_hypothesis_ids,
            mode=mode,
        )
        result = selectors["engine"].clarify(symbolic_state)
        return _symbolic_pair(result, method), {
            "prolog_active_hypothesis_ids": result["active_hypothesis_ids"],
            "proof": result.get("question", {}).get("proof"),
        }
    if method == "raw_attribute_contrast":
        return selectors[method].select(state, list(active)), {}
    if method == "random_eligible":
        return selectors[method].select(state), {}
    if method == "exact_objective_python":
        return selectors[method].select(state, list(active)), {}
    if method == "direct_llm":
        selector: DirectLLMSelector = selectors[method]
        pair = selector.select(
            state,
            list(active),
            scenario_text=scenario.get("natural_language_utterance", scenario["description"]),
            track=selectors.get("llm_track", "structured"),
        )
        return pair, {"llm_record": selector.last_record}
    raise ValueError(f"Unknown method: {method}")


def run_method(
    method: str,
    scenario: dict[str, Any],
    model: EvidenceModel,
    selectors: dict[str, Any],
    max_rounds: int,
) -> dict[str, Any]:
    state = make_state(
        scenario,
        mode="single_rule" if method == "single_rule_prolog" else "compositional",
    )
    initial_declared = tuple(
        sorted(
            item
            for item in scenario["hypothesis_ids"]
            if item not in scenario["rejected_hypothesis_ids"]
        )
    )
    active = replay_responses(model, initial_declared, state.asked_questions)
    initial_active = active
    initially_has_question = (
        len(active) > 1
        and model.has_discriminative_pair(active, eligible_artworks(state))
    )
    rounds: list[dict[str, Any]] = []
    selection_runtimes: list[float] = []
    constraint_violations = 0
    repeated_questions = 0
    correct_no_question = False
    false_no_question = False
    llm_records: list[dict[str, Any]] = []
    stopping_reason = "round_limit"
    started_scenario = time.perf_counter()

    if len(active) <= 1:
        stopping_reason = "initially_resolved"

    for round_index in range(max_rounds if len(active) > 1 else 0):
        eligible_before = eligible_artworks(state)
        independently_has_question = model.has_discriminative_pair(active, eligible_before)
        started = time.perf_counter()
        try:
            pair, selector_metadata = _select(method, state, active, scenario, selectors)
            selection_error = None
        except Exception as exc:  # record one method failure without losing other methods
            pair = None
            selector_metadata = {}
            selection_error = f"{type(exc).__name__}: {exc}"
        elapsed_ms = (time.perf_counter() - started) * 1000
        selection_runtimes.append(elapsed_ms)
        if selector_metadata.get("llm_record") is not None:
            llm_records.append(selector_metadata["llm_record"])

        if selection_error is not None:
            stopping_reason = "selection_error"
            rounds.append(
                {
                    "round": round_index + 1,
                    "active_hypothesis_ids_before": list(active),
                    "selection_runtime_ms": round(elapsed_ms, 3),
                    "selection_error": selection_error,
                }
            )
            break

        if pair is None:
            correct_no_question = not independently_has_question
            false_no_question = independently_has_question
            stopping_reason = (
                "no_valid_discriminative_question"
                if correct_no_question
                else "false_no_question"
            )
            rounds.append(
                {
                    "round": round_index + 1,
                    "active_hypothesis_ids_before": list(active),
                    "selected": False,
                    "independently_available_question": independently_has_question,
                    "selection_runtime_ms": round(elapsed_ms, 3),
                }
            )
            break

        option_a, option_b = sorted((pair.option_a_id, pair.option_b_id))
        pair_key = (option_a, option_b)
        previous_pairs = {
            tuple(sorted((item.option_a_id, item.option_b_id)))
            for item in state.asked_questions
        }
        constraint_reasons: list[str] = []
        if option_a == option_b:
            constraint_reasons.append("identical_options")
        if option_a not in eligible_before or option_b not in eligible_before:
            constraint_reasons.append("option_not_eligible")
        if pair_key in previous_pairs:
            constraint_reasons.append("repeated_pair")
            repeated_questions += 1
        if constraint_reasons:
            constraint_violations += 1

        statistics_row = model.statistics(active, option_a, option_b)
        formally_valid = (
            not constraint_reasons
            and statistics_row["distinguished_hypothesis_pair_count"] > 0
        )
        scripted = scenario.get("simulated_responses", [])
        response = (
            scripted[round_index]
            if round_index < len(scripted)
            else model.simulated_response(
                scenario["hidden_hypothesis_id"], option_a, option_b
            )
        )
        transition = model.transition(active, option_a, option_b, response)
        exact_best = model.best_pair(active, eligible_before)
        exact_pair = list(exact_best[:2]) if exact_best else None
        prolog_consistent = selector_metadata.get("prolog_active_hypothesis_ids")
        round_row = {
            "round": round_index + 1,
            "active_hypothesis_ids_before": list(active),
            "selected": True,
            "selected_artwork_ids": [option_a, option_b],
            "predicted_response_partition": statistics_row["predicted_response_partition"],
            "distinguished_hypothesis_pair_count": statistics_row[
                "distinguished_hypothesis_pair_count"
            ],
            "response_split_imbalance": statistics_row["response_split_imbalance"],
            "unknown_prediction_count": statistics_row["unknown_prediction_count"],
            "independent_deterministic_score": statistics_row["deterministic_score"],
            "selector_reported_score": pair.score,
            "formally_valid_selected_question": formally_valid,
            "simulated_response": response,
            "eliminated_hypothesis_ids": list(transition.eliminated),
            "active_hypothesis_ids_after": list(transition.after),
            "remaining_hypothesis_count": len(transition.after),
            "hidden_hypothesis_survived": scenario["hidden_hypothesis_id"] in transition.after,
            "constraint_violations": constraint_reasons,
            "selection_runtime_ms": round(elapsed_ms, 3),
            "exact_objective_optimal_pair": exact_pair,
            "matches_exact_objective_optimum": exact_pair == [option_a, option_b],
        }
        if prolog_consistent is not None:
            round_row["prolog_active_state_matches_shared"] = list(active) == prolog_consistent
        if selector_metadata.get("proof") is not None:
            round_row["proof"] = selector_metadata["proof"]
        rounds.append(round_row)

        question = {
            "question_id": f"q_{option_a}_{option_b}",
            "option_a": {"artwork_id": option_a},
            "option_b": {"artwork_id": option_b},
        }
        state = state.apply_response(
            question, response, f"obs_eval_{method}_{round_index + 1}"
        )
        active = transition.after
        if constraint_reasons:
            stopping_reason = "constraint_violation"
            break
        if len(active) <= 1:
            stopping_reason = "resolved_unique"
            break

    scenario_runtime_ms = (time.perf_counter() - started_scenario) * 1000
    selected_rounds = [item for item in rounds if item.get("selected")]
    return {
        "method": method,
        "initial_hypothesis_count": len(initial_active),
        "initial_active_hypothesis_ids": list(initial_active),
        "rounds": rounds,
        "question_count": len(selected_rounds),
        "constraint_violation_count": constraint_violations,
        "repeated_question_count": repeated_questions,
        "correct_no_question_decision": correct_no_question,
        "false_no_question_decision": false_no_question,
        "final_active_hypothesis_ids": list(active),
        "remaining_hypothesis_count": len(active),
        "hidden_hypothesis_survived": scenario["hidden_hypothesis_id"] in active,
        "correctly_resolved": active == (scenario["hidden_hypothesis_id"],),
        "initially_resolved": len(initial_active) <= 1,
        "initially_solvable": initially_has_question,
        "initially_unsolvable": len(initial_active) > 1 and not initially_has_question,
        "stopping_reason": stopping_reason,
        "selection_runtime_ms": [round(item, 3) for item in selection_runtimes],
        "scenario_runtime_ms": round(scenario_runtime_ms, 3),
        "llm_records": llm_records,
    }


def aggregate(rows: list[dict[str, Any]], method: str) -> dict[str, Any]:
    method_rows = [row["methods"][method] for row in rows]
    rounds = [item for row in method_rows for item in row["rounds"]]
    selected = [item for item in rounds if item.get("selected")]
    valid = [item for item in selected if item["formally_valid_selected_question"]]
    runtimes = [value for row in method_rows for value in row["selection_runtime_ms"]]
    successful_questions = [
        row["question_count"]
        for row in method_rows
        if row["correctly_resolved"] and not row["initially_resolved"]
    ]
    round_remaining: dict[int, list[int]] = defaultdict(list)
    for item in selected:
        round_remaining[item["round"]].append(item["remaining_hypothesis_count"])
    return {
        "scenario_count": len(method_rows),
        "selection_attempt_count": len(rounds),
        "selected_question_count": len(selected),
        "selected_question_rate": round(len(selected) / len(rounds), 4) if rounds else None,
        "formally_valid_selected_question_rate": round(len(valid) / len(selected), 4)
        if selected
        else None,
        "invalid_selection_count_per_all_scenarios": sum(
            not item["formally_valid_selected_question"] for item in selected
        ),
        "invalid_selections_per_scenario": round(
            sum(not item["formally_valid_selected_question"] for item in selected)
            / len(method_rows),
            4,
        ),
        "invalid_selection_rate_per_selection_attempt": round(
            sum(not item["formally_valid_selected_question"] for item in selected)
            / len(rounds),
            4,
        )
        if rounds
        else None,
        "correct_no_question_count": sum(
            row["correct_no_question_decision"] for row in method_rows
        ),
        "false_no_question_count": sum(
            row["false_no_question_decision"] for row in method_rows
        ),
        "constraint_violation_rate": round(
            sum(row["constraint_violation_count"] for row in method_rows) / len(selected), 4
        )
        if selected
        else 0.0,
        "mean_distinguished_hypothesis_pairs_per_selected_question": round(
            statistics.fmean(
                item["distinguished_hypothesis_pair_count"] for item in selected
            ),
            4,
        )
        if selected
        else None,
        "mean_active_hypotheses_remaining_after_round": {
            str(index): round(statistics.fmean(values), 4)
            for index, values in sorted(round_remaining.items())
        },
        "correct_resolution_after_interaction_count": sum(
            row["correctly_resolved"] and not row["initially_resolved"]
            for row in method_rows
        ),
        "correct_resolution_rate_over_initially_solvable": round(
            sum(
                row["correctly_resolved"] and not row["initially_resolved"]
                for row in method_rows
            )
            / sum(row["initially_solvable"] for row in method_rows),
            4,
        ),
        "initially_resolved_count": sum(row["initially_resolved"] for row in method_rows),
        "initially_unsolvable_count": sum(row["initially_unsolvable"] for row in method_rows),
        "hidden_hypothesis_retention_rate": round(
            sum(row["hidden_hypothesis_survived"] for row in method_rows)
            / len(method_rows),
            4,
        ),
        "mean_questions_for_successful_resolution": round(
            statistics.fmean(successful_questions), 4
        )
        if successful_questions
        else None,
        "unresolved_after_round_limit_count": sum(
            row["stopping_reason"] == "round_limit" for row in method_rows
        ),
        "repeated_question_rate": round(
            sum(row["repeated_question_count"] for row in method_rows) / len(selected), 4
        )
        if selected
        else 0.0,
        "mean_question_selection_runtime_ms": round(statistics.fmean(runtimes), 3)
        if runtimes
        else None,
        "median_question_selection_runtime_ms": round(statistics.median(runtimes), 3)
        if runtimes
        else None,
        "mean_total_scenario_runtime_ms": round(
            statistics.fmean(row["scenario_runtime_ms"] for row in method_rows), 3
        ),
        "worst_case_scenario_runtime_ms": round(
            max(row["scenario_runtime_ms"] for row in method_rows), 3
        ),
    }


def write_summary_csv(path: Path, summary: dict[str, Any]) -> None:
    fields = [
        "method",
        "scenario_count",
        "selected_question_count",
        "formally_valid_selected_question_rate",
        "correct_no_question_count",
        "false_no_question_count",
        "correct_resolution_after_interaction_count",
        "correct_resolution_rate_over_initially_solvable",
        "hidden_hypothesis_retention_rate",
        "mean_questions_for_successful_resolution",
        "mean_distinguished_hypothesis_pairs_per_selected_question",
        "mean_question_selection_runtime_ms",
        "median_question_selection_runtime_ms",
        "mean_total_scenario_runtime_ms",
        "repeated_question_rate",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for method, metrics in summary.items():
            writer.writerow({"method": method, **{key: metrics.get(key) for key in fields[1:]}})


def write_trajectory_csv(path: Path, summary: dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["method", "round", "mean_active_hypotheses_remaining"])
        for method, metrics in summary.items():
            for round_index, value in metrics[
                "mean_active_hypotheses_remaining_after_round"
            ].items():
                writer.writerow([method, round_index, value])


def write_svg(path: Path, summary: dict[str, Any]) -> None:
    methods = list(summary)
    width, height = 960, 80 + len(methods) * 54
    bars: list[str] = []
    for index, method in enumerate(methods):
        y = 45 + index * 54
        rate = summary[method]["correct_resolution_rate_over_initially_solvable"]
        bar_width = int(rate * 430)
        bars.extend(
            [
                f'<text x="10" y="{y + 16}" font-size="13">{method}</text>',
                f'<rect x="290" y="{y}" width="430" height="22" fill="#e5e7eb"/>',
                f'<rect x="290" y="{y}" width="{bar_width}" height="22" fill="#2563eb"/>',
                f'<text x="730" y="{y + 16}" font-size="13">{rate:.1%}</text>',
                f'<text x="790" y="{y + 16}" font-size="12">{summary[method]["mean_question_selection_runtime_ms"]} ms/q</text>',
            ]
        )
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">'
        '<rect width="100%" height="100%" fill="white"/>'
        '<text x="10" y="24" font-size="18" font-weight="bold">Controlled three-round resolution and selector runtime</text>'
        + "".join(bars)
        + "</svg>\n"
    )
    path.write_text(svg, encoding="utf-8", newline="\n")


def benchmark_composition(scenarios: list[dict[str, Any]], model: EvidenceModel) -> dict[str, Any]:
    categories = defaultdict(int)
    solvable_three_plus = 0
    for scenario in scenarios:
        state = make_state(scenario)
        initial = replay_responses(
            model,
            sorted(
                item
                for item in scenario["hypothesis_ids"]
                if item not in scenario["rejected_hypothesis_ids"]
            ),
            state.asked_questions,
        )
        if len(initial) <= 1:
            categories["initially_resolved"] += 1
        elif model.has_discriminative_pair(initial, eligible_artworks(state)):
            categories["initially_solvable"] += 1
            if len(initial) >= 3:
                solvable_three_plus += 1
        else:
            categories["initially_unsolvable"] += 1
    return {
        "all_generated_scenarios": len(scenarios),
        **categories,
        "initially_solvable_with_three_or_more_hypotheses": solvable_three_plus,
        "development_count": sum(item.get("subset") == "development" for item in scenarios),
        "held_out_count": sum(item.get("subset") == "held_out" for item in scenarios),
    }


def analysis_breakdowns(
    rows: list[dict[str, Any]], methods: Sequence[str]
) -> dict[str, Any]:
    def candidate_bucket(count: int) -> str:
        if count <= 10:
            return "small_2_to_10"
        if count <= 60:
            return "medium_11_to_60"
        return "large_61_plus"

    dimensions: dict[str, Any] = {
        "initial_hypothesis_count": lambda row, method: [
            str(row["methods"][method]["initial_hypothesis_count"])
        ],
        "attribute_family": lambda row, method: row["attribute_families"] or ["unspecified"],
        "correlation": lambda row, method: [row["correlation_group"]],
        "support_condition": lambda row, method: [
            "missing_or_ambiguous"
            if set(row["case_tags"])
            & {
                "incomplete_evidence",
                "missing_attributes",
                "unknown_or_same_direction_predictions",
                "early_answer_no_reduction",
                "neither_no_reduction",
            }
            else "ordinary_positive_support"
        ],
        "candidate_count": lambda row, method: [
            candidate_bucket(row["allowed_candidate_count"])
        ],
        "clarification_rounds": lambda row, method: [
            str(row["methods"][method]["question_count"])
        ],
    }
    output: dict[str, Any] = {}
    for dimension, labels_for in dimensions.items():
        output[dimension] = {}
        for method in methods:
            groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
            for row in rows:
                for label in labels_for(row, method):
                    groups[label].append(row["methods"][method])
            output[dimension][method] = {
                label: {
                    "scenario_count": len(items),
                    "correct_resolution_after_interaction_count": sum(
                        item["correctly_resolved"] and not item["initially_resolved"]
                        for item in items
                    ),
                    "mean_questions": round(
                        statistics.fmean(item["question_count"] for item in items), 4
                    ),
                    "mean_scenario_runtime_ms": round(
                        statistics.fmean(item["scenario_runtime_ms"] for item in items), 3
                    ),
                }
                for label, items in sorted(groups.items())
            }
    return output


def main() -> None:
    args = parse_args()
    scenario_path = Path(args.scenarios)
    evidence_path = ROOT / "data" / "curated" / "clarification_evidence.json"
    scenarios = load_jsonl(scenario_path)
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    model = EvidenceModel(evidence)
    transport = OpenAIResponsesTransport.from_environment() if args.run_direct_llm else None
    direct_selector = DirectLLMSelector(transport, evidence) if transport else None
    selectors: dict[str, Any] = {
        "engine": default_engine(ROOT),
        "raw_attribute_contrast": AttributeContrastSelector(evidence),
        "random_eligible": RandomPairSelector(),
        "exact_objective_python": ExactObjectivePythonSelector(evidence),
        "llm_track": args.llm_track,
    }
    methods = list(METHODS)
    if direct_selector is not None:
        selectors["direct_llm"] = direct_selector
        methods.append("direct_llm")

    rows: list[dict[str, Any]] = []
    for scenario in scenarios:
        method_rows = {
            method: run_method(method, scenario, model, selectors, args.max_rounds)
            for method in methods
        }
        rows.append(
            {
                "scenario_id": scenario["scenario_id"],
                "subset": scenario.get("subset", "phase_1_regression"),
                "case_tags": scenario["case_tags"],
                "attribute_families": scenario.get("attribute_families", []),
                "correlation_group": scenario.get("correlation_group", "unspecified"),
                "hidden_hypothesis_id": scenario["hidden_hypothesis_id"],
                "allowed_candidate_count": len(scenario["allowed_artwork_ids"]),
                "methods": method_rows,
            }
        )

    summary = {method: aggregate(rows, method) for method in methods}
    if direct_selector is not None:
        llm_records = [
            record
            for row in rows
            for record in row["methods"]["direct_llm"]["llm_records"]
        ]
        usages = [
            record.get("transport_metadata", {}).get("usage", {})
            for record in llm_records
        ]
        summary["direct_llm"]["request_count"] = len(llm_records)
        summary["direct_llm"]["token_usage"] = {
            key: sum(int(item.get(key, 0) or 0) for item in usages)
            for key in ("input_tokens", "output_tokens", "total_tokens")
        }
    equivalence_rounds = [
        item
        for row in rows
        for item in row["methods"]["compositional_prolog"]["rounds"]
        if item.get("selected")
    ]
    prolog_state_checks = [
        item["prolog_active_state_matches_shared"]
        for row in rows
        for method in ("compositional_prolog", "single_rule_prolog")
        for item in row["methods"][method]["rounds"]
        if "prolog_active_state_matches_shared" in item
    ]
    result = {
        "schema_version": "2.0",
        "benchmark_version": "phase_1_1_controlled_v1",
        "scenario_count": len(scenarios),
        "dataset_snapshot": {
            "evidence_sha256": sha256(evidence_path),
            "scenarios_sha256": sha256(scenario_path),
        },
        "configuration": {
            "max_rounds": args.max_rounds,
            "random_seed": 3263,
            "methods": methods,
            "llm_track": args.llm_track,
        },
        "simulation_notice": (
            "Controlled responses use the declared recorded-positive-support model. "
            "They are not genuine human preference outcomes."
        ),
        "direct_llm": (
            "executed" if direct_selector else "not_executed_missing_configuration_or_flag"
        ),
        "benchmark_composition": benchmark_composition(scenarios, model),
        "summary": summary,
        "analysis_breakdowns": analysis_breakdowns(rows, methods),
        "exact_python_vs_compositional_prolog": {
            "selected_round_count": len(equivalence_rounds),
            "identical_optimum_count": sum(
                item["matches_exact_objective_optimum"] for item in equivalence_rounds
            ),
            "all_identical": all(
                item["matches_exact_objective_optimum"] for item in equivalence_rounds
            ),
        },
        "shared_state_vs_prolog_consistency": {
            "checked_round_count": len(prolog_state_checks),
            "matching_round_count": sum(prolog_state_checks),
            "all_matching": all(prolog_state_checks),
        },
        "scenarios": rows,
    }
    Path(args.output).write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    write_summary_csv(Path(args.summary_csv), summary)
    write_trajectory_csv(Path(args.trajectory_csv), summary)
    write_svg(Path(args.visualization), summary)
    if direct_selector is not None:
        llm_result = {
            "configuration": result["configuration"],
            "simulation_notice": result["simulation_notice"],
            "scenarios": [
                {
                    "scenario_id": row["scenario_id"],
                    "result": row["methods"]["direct_llm"],
                }
                for row in rows
            ],
        }
        Path(args.llm_output).write_text(
            json.dumps(llm_result, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    print(json.dumps(summary, indent=2))
    if direct_selector is None:
        print("direct_llm=not_executed_missing_configuration_or_flag")


if __name__ == "__main__":
    main()
