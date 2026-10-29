"""Deterministically normalize saved LLM labels to IDs and rescore offline."""
from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone

from evaluation.evaluate_preference_state_corrected import (
    LLM,
    ROOT,
    evaluate_result,
    make_state,
    read_jsonl,
    summarize,
)
from museum_guide.preference_state_llm import CorrectedDirectPreferenceStateLLM


PROLOG = "compositional_prolog"
CALL_PATH = ROOT / "evaluation/preference_state_llm_single_pass_calls.json"
STRICT_PATH = ROOT / "evaluation/preference_state_llm_single_pass_results.json"
REFERENCE_PATH = ROOT / "evaluation/preference_state_corrected_results.json"
RESULT_PATH = ROOT / "evaluation/preference_state_llm_normalized_results.json"
SUMMARY_PATH = ROOT / "evaluation/preference_state_llm_normalized_summary.csv"
END_TO_END_METRICS = (
    "explanation_coverage",
    "primary_explanation_accuracy",
    "explanation_precision",
    "explanation_recall",
    "top1_relevance",
    "recall_at_k",
    "precision_at_k",
    "hit_at_k",
    "action_type_accuracy",
    "decision_validity",
)


class SavedResponseTransport:
    def __init__(self, response: dict) -> None:
        self.response = response

    def complete_json(self, payload: dict) -> dict:
        return deepcopy(self.response)


def sha256(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def raw_output_text(call: dict) -> str | None:
    record = call.get("record") or {}
    envelope = record.get("raw_response")
    if not envelope:
        envelope = (record.get("transport_exchange") or {}).get("raw_response")
    if not isinstance(envelope, dict):
        return None
    value = envelope.get("output_text")
    return value if isinstance(value, str) and value.strip() else None


def compact(method: dict) -> dict:
    if "error" in method:
        return {"error": method["error"]}
    result = method["result"]
    return {
        "metrics": method["metrics"],
        "normalizations": method.get("normalizations", []),
        "preference_explanations": result.get("preference_explanations", []),
        "primary_explanation": result.get("primary_explanation"),
        "decision": result.get("decision"),
        "ranked_actions": result.get("ranked_actions", []),
        "api_runtime_ms": result.get("runtime_ms"),
    }


def end_to_end(rows: list[dict], method: str) -> dict[str, float]:
    return {
        key: round(
            sum(
                float(row["methods"][method].get("metrics", {}).get(key) or 0.0)
                for row in rows
            )
            / len(rows),
            6,
        )
        for key in END_TO_END_METRICS
    }


def main() -> None:
    for path in (RESULT_PATH, SUMMARY_PATH):
        if path.exists():
            raise FileExistsError(f"Refusing to overwrite {path}")
    for path in (CALL_PATH, STRICT_PATH, REFERENCE_PATH):
        if not path.is_file():
            raise FileNotFoundError(path)

    evidence = json.loads(
        (ROOT / "data/curated/clarification_evidence.json").read_text(encoding="utf-8")
    )
    scenario_paths = [
        ROOT / "evaluation/preference_state_corrected_scenarios.jsonl",
        ROOT / "evaluation/preference_state_robustness_scenarios.jsonl",
    ]
    scenarios = [scenario for path in scenario_paths for scenario in read_jsonl(path)]
    calls = json.loads(CALL_PATH.read_text(encoding="utf-8"))["calls"]
    call_by_id = {call["scenario_id"]: call for call in calls}
    if len(call_by_id) != len(scenarios) or set(call_by_id) != {s["scenario_id"] for s in scenarios}:
        raise ValueError("Expected exactly one saved call for each scenario")

    reference = json.loads(REFERENCE_PATH.read_text(encoding="utf-8"))
    prolog_by_id = {
        row["scenario_id"]: deepcopy(row["methods"][PROLOG])
        for row in reference["scenarios"]
    }
    rows = []
    error_histogram: Counter[str] = Counter()
    accepted_normalization_count = 0
    attempted_normalization_count = 0
    for scenario in scenarios:
        scenario_id = scenario["scenario_id"]
        call = call_by_id[scenario_id]
        text = raw_output_text(call)
        if text is None:
            error = (call.get("record") or {}).get("error", "No response text")
            llm_method = {"error": error}
            error_histogram[error] += 1
        else:
            model = None
            try:
                parsed = json.loads(text)
                model = CorrectedDirectPreferenceStateLLM(
                    SavedResponseTransport(parsed), evidence
                )
                result = model.infer(
                    make_state(scenario),
                    natural_language_history=scenario["natural_language_history"],
                )
                result["runtime_ms"] = call.get("elapsed_ms")
                normalizations = model.last_record.get("normalizations", [])
                attempted_normalization_count += len(normalizations)
                accepted_normalization_count += len(normalizations)
                llm_method = {
                    "result": result,
                    "metrics": evaluate_result(
                        result, scenario, make_state(scenario), evidence
                    ),
                    "normalizations": normalizations,
                    "clarification": {"asked": False, "worlds": []},
                }
            except Exception as exc:
                if model is not None:
                    attempted_normalization_count += len(
                        model.last_record.get("normalizations", [])
                    )
                error = f"{type(exc).__name__}: {exc}"
                llm_method = {"error": error}
                error_histogram[error] += 1
        rows.append(
            {
                "scenario_id": scenario_id,
                "benchmark_kind": scenario["benchmark_kind"],
                "category": scenario.get("category", scenario.get("family")),
                "subset": scenario["subset"],
                "candidate_order": scenario["candidate_artwork_ids"],
                "world_count": len(scenario["worlds"]),
                "methods": {
                    PROLOG: prolog_by_id[scenario_id],
                    LLM: llm_method,
                },
            }
        )

    methods = [PROLOG, LLM]
    overall_summary = summarize(rows, methods)
    overall_end_to_end = {method: end_to_end(rows, method) for method in methods}
    group_summary = {
        group: summarize(
            [row for row in rows if row["benchmark_kind"] == group], methods
        )
        for group in sorted({row["benchmark_kind"] for row in rows})
    }
    group_end_to_end = {
        group: {
            method: end_to_end(
                [row for row in rows if row["benchmark_kind"] == group], method
            )
            for method in methods
        }
        for group in group_summary
    }
    subset_summary = {
        subset: summarize([row for row in rows if row["subset"] == subset], methods)
        for subset in sorted({row["subset"] for row in rows})
    }
    subset_end_to_end = {
        subset: {
            method: end_to_end(
                [row for row in rows if row["subset"] == subset], method
            )
            for method in methods
        }
        for subset in subset_summary
    }
    strict = json.loads(STRICT_PATH.read_text(encoding="utf-8"))
    output = {
        "version": "corrected_v2_llm_normalized",
        "executed_at_utc": datetime.now(timezone.utc).isoformat(),
        "derivation": "offline rescore of persisted raw responses; no API calls",
        "normalization_policy": {
            "accepted": [
                "allowlisted stable hypothesis ID",
                "exact unique official hypothesis label after trim and casefold",
            ],
            "rejected": ["fuzzy match", "substring match", "inferred synonym"],
            "uses_gold_or_prolog_output": False,
        },
        "scenario_count": len(rows),
        "strict_valid_count": strict["overall_summary"][LLM]["successful_scenario_count"],
        "normalized_valid_count": overall_summary[LLM]["successful_scenario_count"],
        "attempted_normalization_occurrence_count": attempted_normalization_count,
        "accepted_normalization_occurrence_count": accepted_normalization_count,
        "source_sha256": {
            str(CALL_PATH.relative_to(ROOT)): sha256(CALL_PATH),
            str(STRICT_PATH.relative_to(ROOT)): sha256(STRICT_PATH),
        },
        "error_histogram": dict(error_histogram.most_common()),
        "overall_summary": overall_summary,
        "overall_end_to_end_metrics_invalid_as_zero": overall_end_to_end,
        "group_summary": group_summary,
        "group_end_to_end_metrics_invalid_as_zero": group_end_to_end,
        "subset_summary": subset_summary,
        "subset_end_to_end_metrics_invalid_as_zero": subset_end_to_end,
        "scenarios": [
            {
                **{key: row[key] for key in (
                    "scenario_id", "benchmark_kind", "category", "subset",
                    "candidate_order", "world_count",
                )},
                "methods": {
                    method: compact(row["methods"][method]) for method in methods
                },
            }
            for row in rows
        ],
    }
    RESULT_PATH.write_text(
        json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    flat = []
    for scope, summaries, end_to_end_summaries in [
        ("overall", {"all": overall_summary}, {"all": overall_end_to_end}),
        ("benchmark", group_summary, group_end_to_end),
        ("subset", subset_summary, subset_end_to_end),
    ]:
        for group, method_rows in summaries.items():
            for method, values in method_rows.items():
                flat.append(
                    {
                        "scope": scope,
                        "group": group,
                        "method": method,
                        "scenario_count": values["scenario_count"],
                        "successful_scenario_count": values["successful_scenario_count"],
                        "error_count": values["error_count"],
                        "valid_decisions_per_attempt": values["valid_decisions_per_attempt"],
                        **values["metrics"],
                        **{
                            f"end_to_end_{key}": value
                            for key, value in end_to_end_summaries[group][method].items()
                        },
                    }
                )
    fields = sorted({key for row in flat for key in row})
    with SUMMARY_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(flat)
    print(
        json.dumps(
            {
                "strict_valid_count": output["strict_valid_count"],
                "normalized_valid_count": output["normalized_valid_count"],
                "attempted_normalization_occurrence_count": attempted_normalization_count,
                "accepted_normalization_occurrence_count": accepted_normalization_count,
                "error_histogram": output["error_histogram"],
                "overall_summary": overall_summary,
                "overall_end_to_end_metrics_invalid_as_zero": overall_end_to_end,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
