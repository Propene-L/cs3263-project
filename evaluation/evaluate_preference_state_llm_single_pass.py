"""Run one direct-LLM attempt per preference-state scenario.

This runner deliberately performs no retries, candidate-order permutations,
or clarification follow-up calls. It can reuse the two earlier smoke-case base
records so those scenarios are not called again. Prolog results are read from
the frozen corrected evaluation rather than rerun.
"""
from __future__ import annotations

import argparse
import csv
import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

from evaluation.evaluate_preference_state_corrected import (
    LLM,
    ROOT,
    Runner,
    evaluate,
    read_jsonl,
    summarize,
)


PROLOG = "compositional_prolog"
RESULT_PATH = ROOT / "evaluation/preference_state_llm_single_pass_results.json"
CALL_PATH = ROOT / "evaluation/preference_state_llm_single_pass_calls.json"
SUMMARY_PATH = ROOT / "evaluation/preference_state_llm_single_pass_summary.csv"
CHECKPOINT_PATH = ROOT / "evaluation/preference_state_llm_single_pass_checkpoint.jsonl"
SMOKE_RESULT_PATH = ROOT / "evaluation/preference_state_llm_smoke_soclaas_results.json"
SMOKE_CALL_PATH = ROOT / "evaluation/preference_state_llm_smoke_soclaas_calls.json"
REFERENCE_PATH = ROOT / "evaluation/preference_state_corrected_results.json"


def _exchange(record: dict) -> dict:
    return record.get("transport_metadata") or record.get("transport_exchange") or {}


def _usage(calls: list[dict]) -> tuple[int, dict[str, int]]:
    requests = 0
    usage: dict[str, int] = {}
    for call in calls:
        exchange = _exchange(call.get("record") or {})
        requests += int(exchange.get("request_count", 0))
        for key, value in (exchange.get("usage") or {}).items():
            if isinstance(value, int):
                usage[key] = usage.get(key, 0) + value
    return requests, usage


def _compact(method: dict) -> dict:
    if "error" in method:
        return {"error": method["error"]}
    result = method["result"]
    return {
        "metrics": method["metrics"],
        "preference_explanations": result.get("preference_explanations", []),
        "primary_explanation": result.get("primary_explanation"),
        "decision": result.get("decision"),
        "ranked_actions": result.get("ranked_actions", []),
        "runtime_ms": result.get("runtime_ms"),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--fresh-all",
        action="store_true",
        help="Call every scenario once instead of reusing prior smoke base calls.",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from the incremental checkpoint without repeating completed IDs.",
    )
    args = parser.parse_args()
    for path in (RESULT_PATH, CALL_PATH, SUMMARY_PATH):
        if path.exists():
            raise FileExistsError(f"Refusing to rerun or overwrite {path}")
    if args.resume and not CHECKPOINT_PATH.is_file():
        raise FileNotFoundError("Resume requested but no checkpoint exists")
    if not args.resume and CHECKPOINT_PATH.exists():
        raise FileExistsError(f"Refusing to overwrite {CHECKPOINT_PATH}")
    required_paths = [REFERENCE_PATH]
    if not args.fresh_all:
        required_paths.extend([SMOKE_RESULT_PATH, SMOKE_CALL_PATH])
    for path in required_paths:
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
    scenario_by_id = {scenario["scenario_id"]: scenario for scenario in scenarios}
    if len(scenario_by_id) != len(scenarios):
        raise ValueError("Duplicate scenario IDs")

    reused_methods: dict[str, dict] = {}
    reused_calls: list[dict] = []
    if not args.fresh_all:
        smoke_result = json.loads(SMOKE_RESULT_PATH.read_text(encoding="utf-8"))
        reused_methods = {
            row["scenario_id"]: deepcopy(row["methods"][LLM])
            for row in smoke_result["scenarios"]
        }
        if set(reused_methods) != {
            "flagship_interaction_albert_kollmann",
            "correction_music",
        }:
            raise ValueError("Unexpected smoke scenarios")

        smoke_calls = json.loads(SMOKE_CALL_PATH.read_text(encoding="utf-8"))["calls"]
        for scenario_id in sorted(reused_methods):
            expected_order = scenario_by_id[scenario_id]["candidate_artwork_ids"]
            matching = [
                call
                for call in smoke_calls
                if call["scenario_id"] == scenario_id
                and call.get("candidate_order") == expected_order
            ]
            if len(matching) != 1:
                raise ValueError(f"Expected one base smoke call for {scenario_id}")
            call = deepcopy(matching[0])
            call["source"] = "reused_prior_smoke_base_call"
            reused_calls.append(call)

    saved_rows: list[dict] = []
    saved_calls: list[dict] = []
    if args.resume:
        for line in CHECKPOINT_PATH.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            checkpoint = json.loads(line)
            saved_rows.append(checkpoint["row"])
            saved_calls.append(checkpoint["call"])
        saved_ids = [row["scenario_id"] for row in saved_rows]
        if len(saved_ids) != len(set(saved_ids)):
            raise ValueError("Checkpoint contains duplicate scenario IDs")
    else:
        saved_ids = []
    completed_ids = set(reused_methods) | set(saved_ids)
    remaining = [
        scenario for scenario in scenarios if scenario["scenario_id"] not in completed_ids
    ]
    runner = Runner(evidence, run_llm=True)
    if runner.llm is None:
        raise RuntimeError("LLM environment is not configured")
    runner.llm.transport.max_retries = 0
    runner.llm_calls.extend(saved_calls)
    new_rows = list(saved_rows)
    initial_call_count = len(runner.llm_calls)
    for index, scenario in enumerate(remaining, start=1):
        row = evaluate([scenario], runner, [LLM], loop=False)[0]
        new_rows.append(row)
        checkpoint = {
            "row": row,
            "call": runner.llm_calls[-1],
        }
        with CHECKPOINT_PATH.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(checkpoint, ensure_ascii=False) + "\n")
        completed = len(saved_rows) + index
        total_new = len(scenarios) - len(reused_methods)
        if completed % 8 == 0 or index == len(remaining):
            print(f"Evaluated {completed}/{total_new} scenarios", flush=True)
    if len(runner.llm_calls) - initial_call_count != len(remaining):
        raise RuntimeError("Single-pass invariant violated: call count differs from cases")
    for call in runner.llm_calls:
        call["source"] = "new_single_pass_call"

    new_methods = {
        row["scenario_id"]: row["methods"][LLM] for row in new_rows
    }
    reference = json.loads(REFERENCE_PATH.read_text(encoding="utf-8"))
    prolog_methods = {
        row["scenario_id"]: deepcopy(row["methods"][PROLOG])
        for row in reference["scenarios"]
    }

    rows = []
    for scenario in scenarios:
        scenario_id = scenario["scenario_id"]
        if scenario_id in reused_methods:
            llm_method = reused_methods[scenario_id]
        else:
            llm_method = new_methods[scenario_id]
        rows.append(
            {
                "scenario_id": scenario_id,
                "benchmark_kind": scenario["benchmark_kind"],
                "category": scenario.get("category", scenario.get("family")),
                "subset": scenario["subset"],
                "candidate_order": scenario["candidate_artwork_ids"],
                "world_count": len(scenario["worlds"]),
                "methods": {
                    PROLOG: prolog_methods[scenario_id],
                    LLM: llm_method,
                },
            }
        )

    methods = [PROLOG, LLM]
    group_summary = {
        name: summarize(
            [row for row in rows if row["benchmark_kind"] == name], methods
        )
        for name in sorted({row["benchmark_kind"] for row in rows})
    }
    overall_summary = summarize(rows, methods)
    subset_summary = {
        subset: summarize([row for row in rows if row["subset"] == subset], methods)
        for subset in sorted({row["subset"] for row in rows})
    }

    all_calls = reused_calls + runner.llm_calls
    request_count, token_usage = _usage(all_calls)
    if len(all_calls) != len(scenarios):
        raise RuntimeError("Expected exactly one selected base call per scenario")
    selected_ids = [call["scenario_id"] for call in all_calls]
    if len(set(selected_ids)) != len(selected_ids):
        raise RuntimeError("A scenario was selected more than once")

    now = datetime.now(timezone.utc).isoformat()
    compact_rows = [
        {
            **{key: row[key] for key in (
                "scenario_id", "benchmark_kind", "category", "subset",
                "candidate_order", "world_count",
            )},
            "methods": {method: _compact(row["methods"][method]) for method in methods},
        }
        for row in rows
    ]
    output = {
        "version": "corrected_v2_llm_single_pass",
        "executed_at_utc": now,
        "scenario_count": len(rows),
        "new_api_call_count": len(runner.llm_calls),
        "reused_prior_base_call_count": len(reused_calls),
        "selected_base_call_count": len(all_calls),
        "request_count_including_retries": request_count,
        "retry_count": request_count - len(all_calls),
        "policy": {
            "fresh_all": args.fresh_all,
            "resumed_from_checkpoint": args.resume,
            "one_selected_base_call_per_scenario": True,
            "transport_retries": 0,
            "candidate_order_permutations": 0,
            "clarification_followup_calls": 0,
            "prolog_reruns": 0,
            "smoke_cases_reused_not_rerun": sorted(reused_methods),
        },
        "token_usage": token_usage,
        "overall_summary": overall_summary,
        "group_summary": group_summary,
        "subset_summary": subset_summary,
        "scenarios": compact_rows,
    }
    RESULT_PATH.write_text(
        json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    CALL_PATH.write_text(
        json.dumps(
            {
                "version": output["version"],
                "executed_at_utc": now,
                "scenario_count": len(all_calls),
                "request_count_including_retries": request_count,
                "retry_count": output["retry_count"],
                "token_usage": token_usage,
                "calls": all_calls,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    flat = []
    for scope, summaries in [
        ("overall", {"all": overall_summary}),
        ("benchmark", group_summary),
        ("subset", subset_summary),
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
                    }
                )
    fields = sorted({key for row in flat for key in row})
    with SUMMARY_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(flat)
    CHECKPOINT_PATH.unlink()
    print(
        json.dumps(
            {
                "scenario_count": len(rows),
                "new_api_call_count": len(runner.llm_calls),
                "reused_prior_base_call_count": len(reused_calls),
                "retry_count": output["retry_count"],
                "token_usage": token_usage,
                "overall_summary": overall_summary,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
