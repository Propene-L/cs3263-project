"""Diagnose normalized LLM failures without making API requests."""
from __future__ import annotations

import csv
import json
import re
from copy import deepcopy
from datetime import datetime, timezone

from evaluation.evaluate_preference_state_corrected import ROOT, make_state, read_jsonl
from museum_guide.preference_state_llm import CorrectedDirectPreferenceStateLLM


CALL_PATH = ROOT / "evaluation/preference_state_llm_single_pass_calls.json"
NORMALIZED_PATH = ROOT / "evaluation/preference_state_llm_normalized_results.json"
REPORT_PATH = ROOT / "evaluation/preference_state_llm_invalid_diagnostic.json"
CSV_PATH = ROOT / "evaluation/preference_state_llm_invalid_diagnostic.csv"


class SavedResponseTransport:
    def __init__(self, response: dict) -> None:
        self.response = response

    def complete_json(self, payload: dict) -> dict:
        return deepcopy(self.response)


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.casefold()).strip("_")


def raw_output_text(call: dict) -> str | None:
    record = call.get("record") or {}
    envelope = record.get("raw_response")
    if not envelope:
        envelope = (record.get("transport_exchange") or {}).get("raw_response")
    if not isinstance(envelope, dict):
        return None
    value = envelope.get("output_text")
    return value if isinstance(value, str) and value.strip() else None


def conservative_json_parse(text: str) -> tuple[dict | None, list[str], str | None]:
    repairs: list[str] = []
    candidate = text.strip()
    if candidate.startswith("```json") and candidate.endswith("```"):
        candidate = candidate[7:-3].strip()
        repairs.append("strip_exact_json_markdown_fence")
    try:
        value = json.loads(candidate)
        return value if isinstance(value, dict) else None, repairs, None
    except json.JSONDecodeError as original:
        try:
            value, end = json.JSONDecoder().raw_decode(candidate)
        except json.JSONDecodeError:
            return None, repairs, f"{type(original).__name__}: {original}"
        trailing = candidate[end:].strip()
        if isinstance(value, dict) and trailing and set(trailing) == {"}"}:
            repairs.append("ignore_only_extra_closing_brace_after_complete_object")
            return value, repairs, None
        return None, repairs, f"{type(original).__name__}: {original}"


def conservative_schema_aliases(
    value: dict, hypothesis_rows: dict[str, dict]
) -> tuple[dict, list[dict]]:
    output = deepcopy(value)
    ids = set(hypothesis_rows)
    slug_to_id: dict[str, str] = {}
    collisions: set[str] = set()
    for hypothesis_id, row in hypothesis_rows.items():
        label = row.get("label")
        if not isinstance(label, str):
            continue
        key = slug(label)
        previous = slug_to_id.get(key)
        if previous is not None and previous != hypothesis_id:
            collisions.add(key)
        else:
            slug_to_id[key] = hypothesis_id
    for key in collisions:
        slug_to_id.pop(key, None)
    changes: list[dict] = []

    def walk(item, path: str):
        if isinstance(item, dict):
            transformed = {key: walk(child, f"{path}.{key}") for key, child in item.items()}
            components = transformed.get("components")
            if (
                transformed.get("kind") == "conjunction"
                and isinstance(components, list)
                and len(components) == 2
            ):
                transformed["kind"] = "all_of"
                changes.append(
                    {
                        "path": f"{path}.kind",
                        "input": "conjunction",
                        "output": "all_of",
                        "rule": "unambiguous_schema_enum_alias",
                    }
                )
            return transformed
        if isinstance(item, list):
            transformed = [walk(child, f"{path}[{index}]") for index, child in enumerate(item)]
            if path.endswith(".components"):
                for index, component in enumerate(transformed):
                    if not isinstance(component, str) or component in ids:
                        continue
                    mapped = slug_to_id.get(slug(component))
                    # Exact labels are handled by the production normalizer. This
                    # diagnostic extends only to a collision-free slug rendering.
                    if mapped is not None and component.strip().casefold() != hypothesis_rows[mapped]["label"].strip().casefold():
                        transformed[index] = mapped
                        changes.append(
                            {
                                "path": f"{path}[{index}]",
                                "input": component,
                                "output": mapped,
                                "rule": "unique_official_label_slug_alias",
                            }
                        )
            return transformed
        return item

    return walk(output, "$"), changes


def main() -> None:
    for path in (REPORT_PATH, CSV_PATH):
        if path.exists():
            raise FileExistsError(f"Refusing to overwrite {path}")
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
    calls = {
        call["scenario_id"]: call
        for call in json.loads(CALL_PATH.read_text(encoding="utf-8"))["calls"]
    }
    normalized = json.loads(NORMALIZED_PATH.read_text(encoding="utf-8"))
    failures = {
        row["scenario_id"]: row["methods"]["direct_llm_state_reasoning"]["error"]
        for row in normalized["scenarios"]
        if "error" in row["methods"]["direct_llm_state_reasoning"]
    }
    rows = []
    for scenario_id, original_error in failures.items():
        scenario = scenarios[scenario_id]
        text = raw_output_text(calls[scenario_id])
        automatic_repairs: list = []
        post_repair_error = None
        if text is None:
            classification = "rerun_required"
            cause = "provider_failure_no_response"
        else:
            parsed, json_repairs, parse_error = conservative_json_parse(text)
            automatic_repairs.extend(json_repairs)
            if parsed is None:
                classification = "rerun_required"
                cause = "malformed_json_not_conservatively_recoverable"
                post_repair_error = parse_error
            else:
                transformed, alias_repairs = conservative_schema_aliases(
                    parsed,
                    CorrectedDirectPreferenceStateLLM(
                        SavedResponseTransport(parsed), evidence
                    ).index.hypothesis_rows,
                )
                automatic_repairs.extend(alias_repairs)
                model = CorrectedDirectPreferenceStateLLM(
                    SavedResponseTransport(transformed), evidence
                )
                try:
                    model.infer(
                        make_state(scenario),
                        natural_language_history=scenario["natural_language_history"],
                    )
                    classification = "offline_recoverable"
                    cause = "conservative_syntax_or_schema_alias"
                except Exception as exc:
                    classification = "rerun_required"
                    cause = "semantic_or_structural_contract_failure"
                    post_repair_error = f"{type(exc).__name__}: {exc}"
        rows.append(
            {
                "scenario_id": scenario_id,
                "benchmark_kind": scenario["benchmark_kind"],
                "category": scenario.get("category", scenario.get("family")),
                "original_error": original_error,
                "classification": classification,
                "cause": cause,
                "automatic_repairs": automatic_repairs,
                "post_repair_error": post_repair_error,
                "recommended_action": (
                    "rescore_saved_response_without_API"
                    if classification == "offline_recoverable"
                    else "one_targeted_API_rerun_with_stricter_ID_only_prompt_and_checkpoint"
                ),
            }
        )

    recoverable = sorted(row["scenario_id"] for row in rows if row["classification"] == "offline_recoverable")
    rerun = sorted(row["scenario_id"] for row in rows if row["classification"] == "rerun_required")
    output = {
        "version": "corrected_v2_llm_invalid_diagnostic",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "api_calls_made": 0,
        "input_invalid_scenario_count": len(rows),
        "offline_recoverable_count": len(recoverable),
        "rerun_required_count": len(rerun),
        "policy": {
            "allowed_repairs": [
                "strip an exact ```json ... ``` wrapper",
                "ignore only extra closing braces after one complete JSON object",
                "map a collision-free slug rendering of an official label",
                "map conjunction to all_of only when exactly two components are present",
            ],
            "forbidden_repairs": [
                "truncate or split component lists",
                "invent or remove explanations",
                "choose between contradictory duplicate statuses",
                "map non-vocabulary concepts by semantic similarity",
                "change actions, recommendations, or primary explanations",
            ],
        },
        "offline_recoverable_scenario_ids": recoverable,
        "rerun_required_scenario_ids": rerun,
        "rows": rows,
    }
    REPORT_PATH.write_text(
        json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    csv_rows = [
        {
            **{key: row[key] for key in (
                "scenario_id", "benchmark_kind", "category", "original_error",
                "classification", "cause", "post_repair_error", "recommended_action",
            )},
            "automatic_repairs": json.dumps(row["automatic_repairs"], ensure_ascii=False),
        }
        for row in rows
    ]
    with CSV_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(csv_rows[0]))
        writer.writeheader()
        writer.writerows(csv_rows)
    print(
        json.dumps(
            {
                "api_calls_made": 0,
                "offline_recoverable_count": len(recoverable),
                "offline_recoverable_scenario_ids": recoverable,
                "rerun_required_count": len(rerun),
                "rerun_required_scenario_ids": rerun,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
