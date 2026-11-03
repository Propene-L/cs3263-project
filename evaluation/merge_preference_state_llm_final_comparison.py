"""Merge original, conservatively repaired, and targeted-rerun LLM results."""
from __future__ import annotations

import csv
import hashlib
import json
import statistics
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone

from evaluation.diagnose_preference_state_llm_invalid import (
    SavedResponseTransport,
    conservative_json_parse,
    conservative_schema_aliases,
    raw_output_text,
)
from evaluation.evaluate_preference_state_corrected import (
    LLM,
    ROOT,
    evaluate_result,
    make_state,
    read_jsonl,
)
from museum_guide.preference_state_llm import CorrectedDirectPreferenceStateLLM


PROLOG = "compositional_prolog"
NORMALIZED_PATH = ROOT / "evaluation/preference_state_llm_normalized_results.json"
DIAGNOSTIC_PATH = ROOT / "evaluation/preference_state_llm_invalid_diagnostic.json"
ORIGINAL_CALL_PATH = ROOT / "evaluation/preference_state_llm_single_pass_calls.json"
RERUN_RESULT_PATH = ROOT / "evaluation/preference_state_llm_invalid_rerun_results.json"
RERUN_CALL_PATH = ROOT / "evaluation/preference_state_llm_invalid_rerun_calls.json"
RESULT_PATH = ROOT / "evaluation/preference_state_llm_final_comparison_results.json"
SUMMARY_PATH = ROOT / "evaluation/preference_state_llm_final_comparison_summary.csv"
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


def sha256(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def mean(values) -> float | None:
    usable = [float(value) for value in values if value is not None]
    return round(statistics.fmean(usable), 6) if usable else None


def conditional_summary(rows: list[dict], method: str) -> dict:
    methods = [row["methods"][method] for row in rows]
    successful = [item for item in methods if "metrics" in item]
    keys = sorted({key for item in successful for key in item["metrics"]})
    metrics = {
        key: mean(item["metrics"].get(key) for item in successful) for key in keys
    }
    return {
        "scenario_count": len(methods),
        "successful_scenario_count": len(successful),
        "error_count": len(methods) - len(successful),
        "valid_decisions_per_attempt": (
            sum(bool(item["metrics"].get("decision_validity")) for item in successful)
            / len(methods)
            if methods
            else None
        ),
        "metrics": metrics,
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


def compact_result(result: dict, metrics: dict, normalizations: list) -> dict:
    return {
        "metrics": metrics,
        "normalizations": normalizations,
        "preference_explanations": result.get("preference_explanations", []),
        "primary_explanation": result.get("primary_explanation"),
        "decision": result.get("decision"),
        "ranked_actions": result.get("ranked_actions", []),
        "runtime_ms": result.get("runtime_ms"),
    }


def main() -> None:
    for path in (RESULT_PATH, SUMMARY_PATH):
        if path.exists():
            raise FileExistsError(f"Refusing to overwrite {path}")
    source_paths = [
        NORMALIZED_PATH,
        DIAGNOSTIC_PATH,
        ORIGINAL_CALL_PATH,
        RERUN_RESULT_PATH,
        RERUN_CALL_PATH,
    ]
    for path in source_paths:
        if not path.is_file():
            raise FileNotFoundError(path)

    evidence = json.loads(
        (ROOT / "data/curated/clarification_evidence.json").read_text(encoding="utf-8")
    )
    scenarios = {
        scenario["scenario_id"]: scenario
        for path in [
            ROOT / "evaluation/preference_state_corrected_scenarios.jsonl",
            ROOT / "evaluation/preference_state_robustness_scenarios.jsonl",
        ]
        for scenario in read_jsonl(path)
    }
    normalized = json.loads(NORMALIZED_PATH.read_text(encoding="utf-8"))
    normalized_by_id = {row["scenario_id"]: row for row in normalized["scenarios"]}
    diagnostic = json.loads(DIAGNOSTIC_PATH.read_text(encoding="utf-8"))
    recoverable = set(diagnostic["offline_recoverable_scenario_ids"])
    rerun_ids = set(diagnostic["rerun_required_scenario_ids"])
    if len(recoverable) != 4 or len(rerun_ids) != 21 or recoverable & rerun_ids:
        raise ValueError("Unexpected diagnostic partition")
    original_calls = {
        call["scenario_id"]: call
        for call in json.loads(ORIGINAL_CALL_PATH.read_text(encoding="utf-8"))["calls"]
    }
    rerun = json.loads(RERUN_RESULT_PATH.read_text(encoding="utf-8"))
    rerun_by_id = {row["scenario_id"]: row for row in rerun["scenarios"]}
    if set(rerun_by_id) != rerun_ids:
        raise ValueError("Targeted rerun does not match diagnostic manifest")

    rows = []
    source_counts: Counter[str] = Counter()
    for scenario_id, scenario in scenarios.items():
        normalized_row = normalized_by_id[scenario_id]
        prolog_method = deepcopy(normalized_row["methods"][PROLOG])
        original_method = normalized_row["methods"][LLM]
        if "metrics" in original_method:
            llm_method = deepcopy(original_method)
            source = "original_exact_label_normalized"
        elif scenario_id in recoverable:
            text = raw_output_text(original_calls[scenario_id])
            if text is None:
                raise ValueError(f"Recoverable case lacks response text: {scenario_id}")
            parsed, json_repairs, parse_error = conservative_json_parse(text)
            if parsed is None:
                raise ValueError(parse_error)
            transformed, alias_repairs = conservative_schema_aliases(
                parsed,
                CorrectedDirectPreferenceStateLLM(
                    SavedResponseTransport(parsed), evidence
                ).index.hypothesis_rows,
            )
            model = CorrectedDirectPreferenceStateLLM(
                SavedResponseTransport(transformed), evidence
            )
            result = model.infer(
                make_state(scenario),
                natural_language_history=scenario["natural_language_history"],
            )
            result["runtime_ms"] = original_calls[scenario_id].get("elapsed_ms")
            normalizations = [
                *[{"rule": repair} for repair in json_repairs],
                *alias_repairs,
                *model.last_record.get("normalizations", []),
            ]
            llm_method = compact_result(
                result,
                evaluate_result(result, scenario, make_state(scenario), evidence),
                normalizations,
            )
            source = "original_conservative_offline_repair"
        elif scenario_id in rerun_ids:
            llm_method = deepcopy(rerun_by_id[scenario_id]["methods"][LLM])
            source = "targeted_contract_rerun"
        else:
            raise ValueError(f"No final-result source for {scenario_id}")
        source_counts[source] += 1
        rows.append(
            {
                "scenario_id": scenario_id,
                "benchmark_kind": scenario["benchmark_kind"],
                "category": scenario.get("category", scenario.get("family")),
                "subset": scenario["subset"],
                "candidate_order": scenario["candidate_artwork_ids"],
                "world_count": len(scenario["worlds"]),
                "llm_result_source": source,
                "methods": {PROLOG: prolog_method, LLM: llm_method},
            }
        )

    methods = [PROLOG, LLM]
    overall_summary = {method: conditional_summary(rows, method) for method in methods}
    overall_end_to_end = {method: end_to_end(rows, method) for method in methods}
    group_rows = {
        group: [row for row in rows if row["benchmark_kind"] == group]
        for group in sorted({row["benchmark_kind"] for row in rows})
    }
    group_summary = {
        group: {method: conditional_summary(items, method) for method in methods}
        for group, items in group_rows.items()
    }
    group_end_to_end = {
        group: {method: end_to_end(items, method) for method in methods}
        for group, items in group_rows.items()
    }
    remaining_errors = [
        {
            "scenario_id": row["scenario_id"],
            "error": row["methods"][LLM]["error"],
        }
        for row in rows
        if "error" in row["methods"][LLM]
    ]
    initial_calls = json.loads(ORIGINAL_CALL_PATH.read_text(encoding="utf-8"))
    rerun_calls = json.loads(RERUN_CALL_PATH.read_text(encoding="utf-8"))
    token_usage = {
        key: int(initial_calls.get("token_usage", {}).get(key, 0))
        + int(rerun_calls.get("token_usage", {}).get(key, 0))
        for key in {"input_tokens", "output_tokens", "total_tokens"}
    }
    output = {
        "version": "corrected_v2_llm_final_comparison",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "derivation": "offline merge; no API calls during merge",
        "scenario_count": len(rows),
        "source_counts": dict(source_counts),
        "remaining_error_count": len(remaining_errors),
        "remaining_errors": remaining_errors,
        "api_request_accounting": {
            "initial_single_pass_requests": initial_calls["request_count_including_retries"],
            "targeted_rerun_requests": rerun_calls["request_count_including_retries"],
            "total_requests": initial_calls["request_count_including_retries"]
            + rerun_calls["request_count_including_retries"],
            "total_retries": initial_calls["retry_count"] + rerun_calls["retry_count"],
            "token_usage": token_usage,
        },
        "source_sha256": {
            str(path.relative_to(ROOT)): sha256(path) for path in source_paths
        },
        "overall_summary": overall_summary,
        "overall_end_to_end_metrics_invalid_as_zero": overall_end_to_end,
        "group_summary": group_summary,
        "group_end_to_end_metrics_invalid_as_zero": group_end_to_end,
        "scenarios": rows,
    }
    RESULT_PATH.write_text(
        json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    flat = []
    for scope, summaries, end_summaries in [
        ("overall", {"all": overall_summary}, {"all": overall_end_to_end}),
        ("benchmark", group_summary, group_end_to_end),
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
                            for key, value in end_summaries[group][method].items()
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
                "source_counts": output["source_counts"],
                "remaining_errors": remaining_errors,
                "api_request_accounting": output["api_request_accounting"],
                "overall_summary": overall_summary,
                "overall_end_to_end_metrics_invalid_as_zero": overall_end_to_end,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
