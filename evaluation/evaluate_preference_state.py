"""Evaluate independent visitor-state construction and next-action relevance."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import statistics
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

from museum_guide.preference_state import (
    PreferenceObservation,
    PreferenceState,
    default_preference_state_engine,
)
from museum_guide.preference_state_baselines import (
    DirectPreferenceStateLLM,
    PositiveAccumulationBaseline,
    PreferenceMethodResult,
    SignedAdditiveAtomicBaseline,
)

ROOT = Path(__file__).resolve().parents[1]
SCENARIOS_PATH = ROOT / "evaluation" / "preference_state_scenarios.jsonl"
EVIDENCE_PATH = ROOT / "data" / "curated" / "clarification_evidence.json"
OUTPUT_PATH = ROOT / "evaluation" / "preference_state_results.json"
SUMMARY_PATH = ROOT / "evaluation" / "preference_state_summary.csv"
LLM_OUTPUT_PATH = ROOT / "evaluation" / "preference_state_llm_results.json"
OFFLINE_METHODS = (
    "positive_attribute_accumulation",
    "signed_additive_atomic",
    "existing_atomic_prolog",
    "compositional_prolog",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenarios", default=str(SCENARIOS_PATH))
    parser.add_argument("--output", default=str(OUTPUT_PATH))
    parser.add_argument("--summary-csv", default=str(SUMMARY_PATH))
    parser.add_argument("--llm-output", default=str(LLM_OUTPUT_PATH))
    parser.add_argument("--run-direct-llm", action="store_true")
    parser.add_argument("--subset", choices=("all", "development", "held_out"), default="all")
    return parser.parse_args()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_scenarios(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def make_state(scenario: dict[str, Any], mode: str = "compositional") -> PreferenceState:
    return PreferenceState(
        session_id=scenario["scenario_id"],
        observations=tuple(
            PreferenceObservation(**item) for item in scenario["observations"]
        ),
        allowed_action_artwork_ids=tuple(scenario["candidate_artwork_ids"]),
        mode=mode,
    )


def prolog_result(method: str, result: dict[str, Any]) -> PreferenceMethodResult:
    return PreferenceMethodResult(
        method=method,
        preference_explanations=result["preference_explanations"],
        ranked_actions=result["ranked_actions"],
        metadata={"observation_evidence": result["observation_evidence"]},
    )


def run_method(
    method: str,
    scenario: dict[str, Any],
    selectors: dict[str, Any],
) -> tuple[PreferenceMethodResult, float]:
    started = time.perf_counter()
    if method == "positive_attribute_accumulation":
        result = selectors[method].infer(make_state(scenario))
    elif method == "signed_additive_atomic":
        result = selectors[method].infer(make_state(scenario))
    elif method in {"existing_atomic_prolog", "compositional_prolog"}:
        mode = "atomic" if method == "existing_atomic_prolog" else "compositional"
        raw = selectors["engine"].infer(make_state(scenario, mode=mode))
        result = prolog_result(method, raw)
    elif method == "direct_llm_state_reasoning":
        result = selectors[method].infer(
            make_state(scenario),
            natural_language_history=scenario["natural_language_history"],
        )
    else:
        raise ValueError(f"Unknown method: {method}")
    return result, (time.perf_counter() - started) * 1000


def normalized_explanation(explanation: dict[str, Any]) -> tuple[str, frozenset[str]]:
    return explanation["kind"], frozenset(explanation["components"])


def evaluate_method_result(
    scenario: dict[str, Any], result: PreferenceMethodResult, runtime_ms: float
) -> dict[str, Any]:
    latent_kind = scenario["latent_profile"]["kind"]
    latent_components = set(scenario["latent_profile"]["components"])
    normalized = [normalized_explanation(item) for item in result.preference_explanations]
    exact_profile_match = (latent_kind, frozenset(latent_components)) in normalized
    primary = result.preference_explanations[0] if result.preference_explanations else None
    primary_components = set(primary["components"]) if primary else set()
    component_precision = (
        len(primary_components & latent_components) / len(primary_components)
        if primary_components
        else 0.0
    )
    component_recall = (
        len(primary_components & latent_components) / len(latent_components)
        if latent_components
        else 0.0
    )
    predicted_atomic = {
        item["components"][0]
        for item in result.preference_explanations
        if item["kind"] == "atomic"
        and item.get("status") not in {"mixed", "explicitly_rejected"}
    }
    false_positive_atomic = predicted_atomic - latent_components
    false_positive_rate = (
        len(false_positive_atomic) / len(predicted_atomic)
        if predicted_atomic
        else 0.0
    )
    ranked_ids = [item["artwork_id"] for item in result.ranked_actions]
    relevant = set(scenario["relevant_artwork_ids"])
    k = min(3, len(ranked_ids))
    top_k = ranked_ids[:k]
    relevant_at_1 = bool(ranked_ids and ranked_ids[0] in relevant)
    relevant_at_k = bool(set(top_k) & relevant)
    precision_at_k = len(set(top_k) & relevant) / k if k else 0.0
    clarification_useful = set(scenario["clarification_useful_ids"])
    useful_at_1 = bool(ranked_ids and ranked_ids[0] in clarification_useful)
    return {
        "method": result.method,
        "preference_explanations": result.preference_explanations,
        "primary_explanation": primary,
        "exact_profile_match": exact_profile_match,
        "atomic_explanation_match": latent_kind == "atomic" and exact_profile_match,
        "interaction_explanation_match": latent_kind == "all_of" and exact_profile_match,
        "primary_component_precision": round(component_precision, 4),
        "primary_component_recall": round(component_recall, 4),
        "false_positive_atomic_interests": sorted(false_positive_atomic),
        "false_positive_atomic_interest_rate": round(false_positive_rate, 4),
        "ranked_actions": result.ranked_actions,
        "relevant_at_1": relevant_at_1,
        "relevant_at_k": relevant_at_k,
        "relevant_k": k,
        "precision_at_k": round(precision_at_k, 4),
        "irrelevant_action": not relevant_at_1,
        "clarification_useful_at_1": useful_at_1,
        "runtime_ms": round(runtime_ms, 3),
        "metadata": result.metadata,
    }


def aggregate(rows: list[dict[str, Any]], method: str) -> dict[str, Any]:
    attempted = [row["methods"][method] for row in rows]
    items = [item for item in attempted if "error" not in item]
    atomic = [
        row["methods"][method]
        for row in rows
        if row["family"] == "contrastive_atomic"
        and "error" not in row["methods"][method]
    ]
    interactions = [
        row["methods"][method]
        for row in rows
        if row["family"] == "compositional_interaction"
        and "error" not in row["methods"][method]
    ]
    if not items:
        return {
            "scenario_count": 0,
            "attempted_scenario_count": len(attempted),
            "error_count": len(attempted),
            "status": "no_valid_results",
        }
    return {
        "scenario_count": len(items),
        "attempted_scenario_count": len(attempted),
        "error_count": len(attempted) - len(items),
        "state_explanation_accuracy": round(
            statistics.fmean(item["exact_profile_match"] for item in items), 4
        ),
        "atomic_explanation_accuracy": round(
            statistics.fmean(item["atomic_explanation_match"] for item in atomic), 4
        )
        if atomic
        else None,
        "interaction_explanation_accuracy": round(
            statistics.fmean(
                item["interaction_explanation_match"] for item in interactions
            ),
            4,
        )
        if interactions
        else None,
        "mean_primary_component_precision": round(
            statistics.fmean(item["primary_component_precision"] for item in items), 4
        ),
        "mean_primary_component_recall": round(
            statistics.fmean(item["primary_component_recall"] for item in items), 4
        ),
        "mean_false_positive_atomic_interest_rate": round(
            statistics.fmean(
                item["false_positive_atomic_interest_rate"] for item in items
            ),
            4,
        ),
        "relevant_at_1": round(
            statistics.fmean(item["relevant_at_1"] for item in items), 4
        ),
        "relevant_at_3": round(
            statistics.fmean(item["relevant_at_k"] for item in items), 4
        ),
        "irrelevant_action_rate": round(
            statistics.fmean(item["irrelevant_action"] for item in items), 4
        ),
        "mean_precision_at_3": round(
            statistics.fmean(item["precision_at_k"] for item in items), 4
        ),
        "recommendation_relevant_at_1": round(
            statistics.fmean(item["relevant_at_1"] for item in interactions), 4
        )
        if interactions
        else None,
        "recommendation_mean_precision_at_3": round(
            statistics.fmean(item["precision_at_k"] for item in interactions), 4
        )
        if interactions
        else None,
        "clarification_useful_at_1": round(
            statistics.fmean(item["clarification_useful_at_1"] for item in atomic), 4
        )
        if atomic
        else None,
        "mean_runtime_ms": round(
            statistics.fmean(item["runtime_ms"] for item in items), 3
        ),
        "median_runtime_ms": round(
            statistics.median(item["runtime_ms"] for item in items), 3
        ),
    }


def family_breakdown(rows: list[dict[str, Any]], methods: list[str]) -> dict[str, Any]:
    output: dict[str, Any] = defaultdict(dict)
    for family in ("contrastive_atomic", "compositional_interaction"):
        family_rows = [row for row in rows if row["family"] == family]
        for method in methods:
            attempted = [row["methods"][method] for row in family_rows]
            items = [item for item in attempted if "error" not in item]
            if not items:
                output[family][method] = {
                    "scenario_count": 0,
                    "attempted_scenario_count": len(attempted),
                    "error_count": len(attempted),
                    "status": "no_valid_results",
                }
                continue
            output[family][method] = {
                "scenario_count": len(items),
                "attempted_scenario_count": len(attempted),
                "error_count": len(attempted) - len(items),
                "state_explanation_accuracy": round(
                    statistics.fmean(item["exact_profile_match"] for item in items), 4
                ),
                "relevant_at_1": round(
                    statistics.fmean(item["relevant_at_1"] for item in items), 4
                ),
                "mean_runtime_ms": round(
                    statistics.fmean(item["runtime_ms"] for item in items), 3
                ),
            }
    return dict(output)


def direct_llm_execution(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarize genuine API attempts without hiding refusals or failed cases."""

    method = "direct_llm_state_reasoning"
    results = [row["methods"][method] for row in rows]
    errors = [
        {"scenario_id": row["scenario_id"], "error": row["methods"][method]["error"]}
        for row in rows
        if "error" in row["methods"][method]
    ]
    usage_totals: dict[str, int | float] = defaultdict(int)
    completed_request_count = 0
    for result in results:
        if "error" in result:
            continue
        transport = (
            result.get("metadata", {})
            .get("llm_record", {})
            .get("transport_metadata", {})
        )
        completed_request_count += int(transport.get("request_count", 1))
        for key, value in transport.get("usage", {}).items():
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                usage_totals[key] += value
    return {
        "scenario_attempt_count": len(results),
        "successful_scenario_count": len(results) - len(errors),
        "failed_scenario_count": len(errors),
        "completed_api_request_count_including_retries": completed_request_count,
        "token_usage": dict(sorted(usage_totals.items())),
        "refusal_count": sum(
            "refus" in item["error"].lower() for item in errors
        ),
        "errors": errors,
        "request_count_note": (
            "Completed request counts include reported retries. Failed calls may have "
            "made retries that produced no response metadata."
        ),
    }


def write_summary(path: Path, summary: dict[str, Any]) -> None:
    fields = [
        "method",
        "scenario_count",
        "state_explanation_accuracy",
        "atomic_explanation_accuracy",
        "interaction_explanation_accuracy",
        "mean_primary_component_precision",
        "mean_primary_component_recall",
        "mean_false_positive_atomic_interest_rate",
        "relevant_at_1",
        "relevant_at_3",
        "recommendation_relevant_at_1",
        "recommendation_mean_precision_at_3",
        "clarification_useful_at_1",
        "mean_runtime_ms",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for method, metrics in summary.items():
            writer.writerow({"method": method, **{key: metrics.get(key) for key in fields[1:]}})


def main() -> None:
    args = parse_args()
    scenario_path = Path(args.scenarios)
    scenarios = load_scenarios(scenario_path)
    if args.subset != "all":
        scenarios = [item for item in scenarios if item["subset"] == args.subset]
    evidence = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))
    selectors: dict[str, Any] = {
        "positive_attribute_accumulation": PositiveAccumulationBaseline(evidence),
        "signed_additive_atomic": SignedAdditiveAtomicBaseline(evidence),
        "engine": default_preference_state_engine(ROOT),
    }
    methods = list(OFFLINE_METHODS)
    direct = (
        DirectPreferenceStateLLM.from_environment(evidence)
        if args.run_direct_llm
        else None
    )
    if direct is not None:
        selectors["direct_llm_state_reasoning"] = direct
        methods.append("direct_llm_state_reasoning")

    rows = []
    for scenario in scenarios:
        method_rows: dict[str, Any] = {}
        for method in methods:
            try:
                result, runtime_ms = run_method(method, scenario, selectors)
                method_rows[method] = evaluate_method_result(
                    scenario, result, runtime_ms
                )
            except Exception as exc:
                method_rows[method] = {
                    "method": method,
                    "error": f"{type(exc).__name__}: {exc}",
                }
        rows.append(
            {
                "scenario_id": scenario["scenario_id"],
                "family": scenario["family"],
                "subset": scenario["subset"],
                "latent_profile": scenario["latent_profile"],
                "relevant_artwork_ids": scenario["relevant_artwork_ids"],
                "methods": method_rows,
            }
        )
    errors = [
        (row["scenario_id"], method, result["error"])
        for row in rows
        for method, result in row["methods"].items()
        if "error" in result
    ]
    offline_errors = [item for item in errors if item[1] in OFFLINE_METHODS]
    if offline_errors:
        raise RuntimeError(
            f"Preference-state offline evaluation failures: {offline_errors[:5]}"
        )

    summary = {method: aggregate(rows, method) for method in methods}
    output = {
        "schema_version": "1.0",
        "benchmark_version": "phase_1_2_preference_state_v1",
        "scenario_count": len(scenarios),
        "configuration": {
            "subset": args.subset,
            "methods": methods,
            "relevant_k": 3,
        },
        "dataset_snapshot": {
            "evidence_sha256": sha256(EVIDENCE_PATH),
            "scenarios_sha256": sha256(scenario_path),
        },
        "controlled_label_notice": (
            "Latent profiles define relevance over recorded support only; results are "
            "not human preference accuracy."
        ),
        "direct_llm": (
            "executed" if direct is not None else "not_executed_missing_configuration_or_flag"
        ),
        "direct_llm_execution": (
            direct_llm_execution(rows) if direct is not None else None
        ),
        "summary": summary,
        "family_breakdown": family_breakdown(rows, methods),
        "scenarios": rows,
    }
    Path(args.output).write_text(
        json.dumps(output, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    write_summary(Path(args.summary_csv), summary)
    if direct is not None:
        llm_rows = [
            {
                "scenario_id": row["scenario_id"],
                "result": row["methods"]["direct_llm_state_reasoning"],
            }
            for row in rows
        ]
        Path(args.llm_output).write_text(
            json.dumps(
                {
                    "configuration": output["configuration"],
                    "controlled_label_notice": output["controlled_label_notice"],
                    "scenarios": llm_rows,
                },
                indent=2,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
            newline="\n",
        )
    print(json.dumps(summary, indent=2))
    if direct is None:
        print("direct_llm=not_executed_missing_configuration_or_flag")


if __name__ == "__main__":
    main()
