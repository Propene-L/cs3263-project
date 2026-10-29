"""Rerun only diagnostic-approved invalid LLM scenarios, once each."""
from __future__ import annotations

import argparse
import json
from copy import deepcopy
from datetime import datetime, timezone

from evaluation.evaluate_preference_state_corrected import (
    LLM,
    ROOT,
    Runner,
    evaluate,
    read_jsonl,
    summarize,
)


PROLOG = "compositional_prolog"
DIAGNOSTIC_PATH = ROOT / "evaluation/preference_state_llm_invalid_diagnostic.json"
REFERENCE_PATH = ROOT / "evaluation/preference_state_corrected_results.json"
RESULT_PATH = ROOT / "evaluation/preference_state_llm_invalid_rerun_results.json"
CALL_PATH = ROOT / "evaluation/preference_state_llm_invalid_rerun_calls.json"
CHECKPOINT_PATH = ROOT / "evaluation/preference_state_llm_invalid_rerun_checkpoint.jsonl"


def exchange(record: dict) -> dict:
    return record.get("transport_metadata") or record.get("transport_exchange") or {}


def usage(calls: list[dict]) -> tuple[int, dict[str, int]]:
    requests = 0
    totals: dict[str, int] = {}
    for call in calls:
        metadata = exchange(call.get("record") or {})
        requests += int(metadata.get("request_count", 0))
        for key, value in (metadata.get("usage") or {}).items():
            if isinstance(value, int):
                totals[key] = totals.get(key, 0) + value
    return requests, totals


def compact(method: dict) -> dict:
    if "error" in method:
        return {"error": method["error"]}
    result = method["result"]
    return {
        "metrics": method["metrics"],
        "preference_explanations": result.get("preference_explanations", []),
        "primary_explanation": result.get("primary_explanation"),
        "decision": result.get("decision"),
        "ranked_actions": result.get("ranked_actions", []),
        "normalizations": (result.get("llm_record") or {}).get("normalizations", []),
        "runtime_ms": result.get("runtime_ms"),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Continue only unfinished manifest IDs from the checkpoint.",
    )
    args = parser.parse_args()
    for path in (RESULT_PATH, CALL_PATH):
        if path.exists():
            raise FileExistsError(f"Refusing to overwrite {path}")
    if args.resume and not CHECKPOINT_PATH.is_file():
        raise FileNotFoundError("Resume requested but no checkpoint exists")
    if not args.resume and CHECKPOINT_PATH.exists():
        raise FileExistsError(f"Refusing to overwrite {CHECKPOINT_PATH}")

    diagnostic = json.loads(DIAGNOSTIC_PATH.read_text(encoding="utf-8"))
    target_ids = diagnostic["rerun_required_scenario_ids"]
    if len(target_ids) != 21 or len(set(target_ids)) != len(target_ids):
        raise ValueError("Expected exactly 21 unique diagnostic rerun IDs")
    evidence = json.loads(
        (ROOT / "data/curated/clarification_evidence.json").read_text(encoding="utf-8")
    )
    all_scenarios = {
        scenario["scenario_id"]: scenario
        for path in [
            ROOT / "evaluation/preference_state_corrected_scenarios.jsonl",
            ROOT / "evaluation/preference_state_robustness_scenarios.jsonl",
        ]
        for scenario in read_jsonl(path)
    }
    scenarios = [all_scenarios[scenario_id] for scenario_id in target_ids]

    rows: list[dict] = []
    calls: list[dict] = []
    if args.resume:
        for line in CHECKPOINT_PATH.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            checkpoint = json.loads(line)
            rows.append(checkpoint["row"])
            calls.append(checkpoint["call"])
    completed_ids = [row["scenario_id"] for row in rows]
    if len(completed_ids) != len(set(completed_ids)) or not set(completed_ids) <= set(target_ids):
        raise ValueError("Invalid checkpoint scenario IDs")
    remaining = [scenario for scenario in scenarios if scenario["scenario_id"] not in set(completed_ids)]

    runner = Runner(evidence, run_llm=True)
    if runner.llm is None:
        raise RuntimeError("LLM environment is not configured")
    runner.llm.transport.max_retries = 0
    runner.llm_calls.extend(calls)
    starting_calls = len(calls)
    for scenario in remaining:
        row = evaluate([scenario], runner, [LLM], loop=False)[0]
        call = runner.llm_calls[-1]
        call["source"] = "targeted_invalid_contract_rerun"
        rows.append(row)
        with CHECKPOINT_PATH.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(
                json.dumps({"row": row, "call": call}, ensure_ascii=False) + "\n"
            )
        print(f"Persisted {len(rows)}/{len(target_ids)} targeted scenarios", flush=True)
    if len(runner.llm_calls) - starting_calls != len(remaining):
        raise RuntimeError("One-request-per-unfinished-scenario invariant failed")
    if {row["scenario_id"] for row in rows} != set(target_ids):
        raise RuntimeError("Targeted rerun did not cover the exact manifest")

    reference = json.loads(REFERENCE_PATH.read_text(encoding="utf-8"))
    prolog_by_id = {
        row["scenario_id"]: deepcopy(row["methods"][PROLOG])
        for row in reference["scenarios"]
    }
    merged_rows = []
    for row in rows:
        scenario_id = row["scenario_id"]
        merged = deepcopy(row)
        merged["methods"][PROLOG] = prolog_by_id[scenario_id]
        merged_rows.append(merged)
    methods = [PROLOG, LLM]
    summary = summarize(merged_rows, methods)
    request_count, token_usage = usage(runner.llm_calls)
    if request_count != len(target_ids):
        raise RuntimeError("Request count differs from targeted scenario count")

    now = datetime.now(timezone.utc).isoformat()
    result_output = {
        "version": "corrected_v2_llm_targeted_invalid_rerun",
        "executed_at_utc": now,
        "target_source": str(DIAGNOSTIC_PATH.relative_to(ROOT)),
        "scenario_count": len(target_ids),
        "request_count_including_retries": request_count,
        "retry_count": request_count - len(target_ids),
        "token_usage": token_usage,
        "policy": {
            "one_request_per_manifest_id": True,
            "transport_retries": 0,
            "candidate_order_permutations": 0,
            "clarification_followup_calls": 0,
            "original_calls_replaced": False,
        },
        "summary": summary,
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
            for row in merged_rows
        ],
    }
    RESULT_PATH.write_text(
        json.dumps(result_output, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    CALL_PATH.write_text(
        json.dumps(
            {
                "version": result_output["version"],
                "executed_at_utc": now,
                "scenario_count": len(target_ids),
                "request_count_including_retries": request_count,
                "retry_count": result_output["retry_count"],
                "token_usage": token_usage,
                "calls": runner.llm_calls,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    CHECKPOINT_PATH.unlink()
    print(
        json.dumps(
            {
                "scenario_count": len(target_ids),
                "request_count": request_count,
                "retry_count": result_output["retry_count"],
                "token_usage": token_usage,
                "summary": summary,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
