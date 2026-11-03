"""Phase 1.2 clarification decision, grounding and paired counterfactual analysis.

Offline mode needs only saved Phase 1.2 files. --closed-loop additionally needs
SWI-Prolog and the existing museum_guide/evaluation modules.

No new LLM requests are made. A selected question from either method is
answered by the SAME declared profile-membership oracle, then passed to the
SAME corrected Prolog state updater. Thus the closed-loop result measures the
utility of QUESTION SELECTION under a fixed updater, not the quality of an
LLM's own second-turn reasoning or actual human responses.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PROLOG = "compositional_prolog"
LLM = "direct_llm_state_reasoning"
METHODS = (PROLOG, LLM)
SOURCES = {
    "onepass": "preference_state_llm_normalized_results.json",
    "final": "preference_state_llm_final_comparison_results.json",
}
SCENARIOS = (
    "preference_state_corrected_scenarios.jsonl",
    "preference_state_robustness_scenarios.jsonl",
)


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def explanation_key(e: dict) -> tuple[str, tuple[str, ...]]:
    return e["kind"], tuple(sorted(e["components"]))


def method_result(row: dict | None) -> dict | None:
    """Read either the original full evaluation or the compact comparison."""
    if not isinstance(row, dict) or "error" in row:
        return None
    if isinstance(row.get("result"), dict):
        return row["result"]
    if isinstance(row.get("decision"), dict):
        return row
    return None


def active_observations(scenario: dict) -> list[dict]:
    observations = scenario.get("observations", [])
    superseded = {o["supersedes"] for o in observations if o.get("supersedes")}
    return [o for o in observations if o["id"] not in superseded]


def build_support_index(evidence: dict, scenario: dict) -> dict[str, dict[str, list[str]]]:
    """Use only the attributes visible to a method, never hidden facts."""
    definitions = {
        (h["attribute_type"], h["value_id"]): h["id"]
        for h in evidence["hypotheses"]
    }
    hidden = set(scenario.get("hidden_fact_ids", []))
    result = {}
    for aid, art in evidence["artworks"].items():
        row: dict[str, list[str]] = {}
        for a in art["attributes"]:
            h = definitions.get((a["type"], a["value_id"]))
            if h and not (hidden & set(a["fact_ids"])):
                row[h] = sorted(set(row.get(h, []) + list(a["fact_ids"])))
        result[aid] = row
    return result


def validate_question(question: Any, vocabulary: set[str]) -> tuple[str, tuple[str, ...]] | None:
    if not isinstance(question, dict) or question.get("kind") != "confirm_explanation":
        return None
    e = question.get("explanation")
    if not isinstance(e, dict):
        return None
    kind, components = e.get("kind"), e.get("components")
    if kind not in {"atomic", "all_of"} or not isinstance(components, list):
        return None
    if len(components) != (1 if kind == "atomic" else 2):
        return None
    if any(not isinstance(c, str) for c in components):
        return None
    if len(set(components)) != len(components) or not set(components) <= vocabulary:
        return None
    return kind, tuple(sorted(components))


def question_grounding(
    question: Any, scenario: dict, evidence: dict, support: dict | None = None
) -> dict:
    """Conservative, METHOD-NEUTRAL observational grounding test.

    A question is observationally grounded only if a liked artwork records ALL
    the question's attributes (or the visitor explicitly expressed the exact
    interest). Independent atomic confirmations do not imply a conjunction.

    Grounding is NOT sufficient evidence of the user's real preference and is
    NOT equivalent to asking a useful or necessary question.
    """
    vocabulary = {h["id"] for h in evidence["hypotheses"]}
    valid = validate_question(question, vocabulary)
    baseline = {
        "structurally_valid": bool(valid),
        "grounded": False,
        "unsettled": False,
        "grounded_and_unsettled": False,
        "liked_support_observation_ids": [],
        "disliked_support_observation_ids": [],
        "explicit_support_observation_ids": [],
        "contextually_related": False,
        "support_fact_ids": [],
        "grounding_reason": "invalid_question",
    }
    if not valid:
        return baseline
    kind, components = valid
    support = support or build_support_index(evidence, scenario)
    liked, disliked, explicit, settled = [], [], [], []
    facts: set[str] = set()
    for o in active_observations(scenario):
        k, oid = o["kind"], o["object_id"]
        if k in {"likes", "dislikes"} and all(h in support.get(oid, {}) for h in components):
            (liked if k == "likes" else disliked).append(o["id"])
            for h in components:
                facts.update(support[oid][h])
        if kind == "atomic" and oid == components[0]:
            if k == "explicit_interest":
                explicit.append(o["id"])
            if k in {"explicit_interest", "explicit_rejection", "reject_atomic_explanation"}:
                settled.append(o["id"])
        if kind == "all_of" and tuple(sorted(o.get("components", []))) == components:
            if k == "explicit_conjunction":
                explicit.append(o["id"])
            if k in {"explicit_conjunction", "reject_conjunction", "reject_pair_explanation"}:
                settled.append(o["id"])
    grounded = bool(liked or explicit)
    # A clarified or explicitly rejected exact preference is already settled.
    unsettled = not bool(settled)
    baseline.update({
        "grounded": grounded,
        "contextually_related": bool(liked or disliked or explicit or settled),
        "unsettled": unsettled,
        "grounded_and_unsettled": grounded and unsettled,
        "liked_support_observation_ids": liked,
        "disliked_support_observation_ids": disliked,
        "explicit_support_observation_ids": explicit,
        "support_fact_ids": sorted(facts),
        "grounding_reason": (
            "liked_co_support" if liked else "explicit_interest" if explicit
            else "no_positive_observation_support"
        ),
    })
    return baseline


def world_partition(question: Any, scenario: dict, vocabulary: set[str]) -> dict:
    """Oracle-world split; only meaningful where >=2 alternative worlds exist."""
    key = validate_question(question, vocabulary)
    worlds = scenario.get("worlds", [])
    if key is None or len(worlds) < 2:
        return {"world_count": len(worlds), "world_split": None, "world_information_gain_bits": None}
    yes = sum(key in {explanation_key(x) for x in w["profile"]} for w in worlds)
    no = len(worlds) - yes
    p = yes / len(worlds)
    entropy = -sum(q * math.log2(q) for q in (p, 1 - p) if q > 0)
    return {
        "world_count": len(worlds),
        "world_split": bool(yes and no),
        "world_information_gain_bits": round(entropy, 6),
    }


def category_matches(scenario: dict, group: str) -> bool:
    kind = scenario["benchmark_kind"]
    return group == "all" or (group == "robustness" and kind == "controlled_robustness") or (
        group == "regression" and kind == "pattern_matched_regression"
    )


def load_dataset(root: Path, source: str, group: str) -> tuple[list[dict], dict, dict[str, dict]]:
    scenarios = [s for name in SCENARIOS for s in read_jsonl(root / "evaluation" / name)]
    scenarios = [s for s in scenarios if category_matches(s, group)]
    if not scenarios:
        raise ValueError("No scenarios matched the requested benchmark group")
    evidence = json.loads((root / "data" / "curated" / "clarification_evidence.json").read_text(encoding="utf-8"))
    path = root / "evaluation" / SOURCES[source]
    comparison = json.loads(path.read_text(encoding="utf-8"))
    result_rows = {r["scenario_id"]: r for r in comparison["scenarios"]}
    if len(result_rows) != len(comparison["scenarios"]):
        raise ValueError("Duplicate scenario ID in comparison artifact")
    missing = sorted({s["scenario_id"] for s in scenarios} - set(result_rows))
    if missing:
        raise ValueError(f"Comparison is missing {len(missing)} scenarios: {missing[:3]}")
    return scenarios, evidence, result_rows


def analyze_cases(scenarios: list[dict], evidence: dict, result_rows: dict[str, dict]) -> list[dict]:
    vocabulary = {h["id"] for h in evidence["hypotheses"]}
    out = []
    for scenario in scenarios:
        sid = scenario["scenario_id"]
        row = result_rows[sid]
        support = build_support_index(evidence, scenario)
        for method in METHODS:
            method_row = row.get("methods", {}).get(method)
            result = method_result(method_row)
            usable = result is not None and isinstance(result.get("decision"), dict)
            action = result["decision"].get("action_type") if usable else "invalid"
            asked = action == "clarify"
            question = result["decision"].get("question") if asked else None
            ground = question_grounding(question, scenario, evidence, support) if asked else None
            partition = world_partition(question, scenario, vocabulary) if asked else None
            expected = scenario["expected_action_type"]
            out.append({
                "scenario_id": sid,
                "benchmark_kind": scenario["benchmark_kind"],
                "category": scenario.get("category", scenario.get("family", "")),
                "subset": scenario["subset"],
                "method": method,
                "valid_output": usable,
                "output_error": method_row.get("error", "") if isinstance(method_row, dict) else "missing_method",
                "expected_action": expected,
                "predicted_action": action,
                "clarification_needed_by_authored_label": expected == "clarify",
                "asked_clarification": asked,
                "confusion": (
                    "invalid" if not usable else
                    "TP" if asked and expected == "clarify" else
                    "FP" if asked else
                    "FN" if expected == "clarify" else "TN"
                ),
                "question_kind": (question or {}).get("explanation", {}).get("kind", "") if asked else "",
                "question_components": (question or {}).get("explanation", {}).get("components", []) if asked else [],
                "structurally_valid_question": ground["structurally_valid"] if ground else None,
                "question_grounded": ground["grounded"] if ground else None,
                "question_contextually_related": ground["contextually_related"] if ground else None,
                "question_unsettled": ground["unsettled"] if ground else None,
                "question_grounded_and_unsettled": ground["grounded_and_unsettled"] if ground else None,
                "question_grounding_reason": ground["grounding_reason"] if ground else "",
                "question_evidence_observation_ids": sorted(ground["liked_support_observation_ids"] + ground["disliked_support_observation_ids"] + ground["explicit_support_observation_ids"]) if ground else [],
                "question_evidence_fact_ids": ground["support_fact_ids"] if ground else [],
                "world_count": len(scenario.get("worlds", [])),
                "world_split": partition["world_split"] if partition else None,
                "world_information_gain_bits": partition["world_information_gain_bits"] if partition else None,
                "decision_validity_reported": (method_row or {}).get("metrics", {}).get("decision_validity") if isinstance(method_row, dict) else None,
                "selected_recommendation_relevance_reported": (method_row or {}).get("metrics", {}).get("selected_recommendation_relevance") if isinstance(method_row, dict) else None,
            })
    return out


def safe_div(a: int | float, b: int | float) -> float | None:
    return round(a / b, 6) if b else None


def summarize_cases(rows: list[dict]) -> dict[str, dict]:
    total_cases = len({r["scenario_id"] for r in rows})
    result = {}
    for method in METHODS:
        subset = [r for r in rows if r["method"] == method]
        valid = [r for r in subset if r["valid_output"]]
        invalid = len(subset) - len(valid)
        tp = sum(r["confusion"] == "TP" for r in subset)
        fp = sum(r["confusion"] == "FP" for r in subset)
        fn = sum(r["confusion"] == "FN" for r in subset)
        # An invalid response on a clarification-needed case is a failure to
        # clarify; on a no-clarification-needed case it is NOT a true negative.
        fn_invalid = sum(not r["valid_output"] and r["clarification_needed_by_authored_label"] for r in subset)
        tn = sum(r["confusion"] == "TN" for r in subset)
        asked = [r for r in subset if r["asked_clarification"]]
        grounded = sum(r["question_grounded"] is True for r in asked)
        contextual = sum(r["question_contextually_related"] is True for r in asked)
        grounded_unsettled = sum(r["question_grounded_and_unsettled"] is True for r in asked)
        precision = safe_div(tp, tp + fp)
        recall = safe_div(tp, tp + fn + fn_invalid)
        f1 = safe_div(2 * precision * recall, precision + recall) if precision is not None and recall is not None else None
        ambiguous_asked = [r for r in asked if r["world_count"] > 1]
        result[method] = {
            "scenario_count": len(subset),
            "valid_outputs": len(valid),
            "invalid_outputs": invalid,
            "expected_clarification_count": sum(r["clarification_needed_by_authored_label"] for r in subset),
            "tp": tp, "fp": fp, "fn_valid": fn, "fn_invalid": fn_invalid, "tn_valid": tn,
            "clarification_precision": precision,
            "clarification_recall_including_invalid_as_missed": recall,
            "clarification_f1": f1,
            "clarification_questions_asked": len(asked),
            "question_grounding_rate_given_asked": safe_div(grounded, len(asked)),
            "question_contextual_relation_rate_given_asked": safe_div(contextual, len(asked)),
            "grounded_and_unsettled_rate_given_asked": safe_div(grounded_unsettled, len(asked)),
            "effective_grounded_clarification_recall": safe_div(
                sum(r["confusion"] == "TP" and r["question_grounded_and_unsettled"] is True for r in subset),
                sum(r["clarification_needed_by_authored_label"] for r in subset),
            ),
            "ambiguous_multi_world_questions_asked": len(ambiguous_asked),
            "questions_splitting_multi_world_profiles": sum(r["world_split"] is True for r in ambiguous_asked),
            "mean_oracle_world_information_gain_bits": round(
                sum(r["world_information_gain_bits"] for r in ambiguous_asked if r["world_information_gain_bits"] is not None) / len(ambiguous_asked), 6
            ) if ambiguous_asked else None,
        }
    if any(len([r for r in rows if r["method"] == method]) != total_cases for method in METHODS):
        raise AssertionError("Each method must appear once per scenario")
    return result


def run_closed_loop(root: Path, scenarios: list[dict], rows: list[dict], results: dict[str, dict], evidence: dict) -> list[dict]:
    """Replay selected questions through the shared corrected Prolog updater.

    For BOTH question sources, the starting state is the same saved Prolog
    state. The resulting differences isolate question choice, conditional on
    the shared update policy. The LLM is NOT called on visitor answers.
    """
    from evaluation.evaluate_preference_state_corrected import (
        apply_response, controlled_response, make_state, ranking_metrics, state_metrics,
    )
    from museum_guide.preference_state import default_preference_state_engine

    engine = default_preference_state_engine(root)
    case_lookup = {s["scenario_id"]: s for s in scenarios}
    output = []
    cache: dict[tuple[str, str, str], dict] = {}
    for r in rows:
        sid = r["scenario_id"]
        scenario = case_lookup[sid]
        if not r["asked_clarification"]:
            continue
        method = r["method"]
        prior = method_result(results[sid]["methods"][PROLOG])
        if prior is None:
            raise ValueError(f"Missing saved Prolog state for {sid}")
        q = method_result(results[sid]["methods"][method])["decision"]["question"]
        for world_i, world in enumerate(scenario["worlds"]):
            response = controlled_response(q, world["profile"])
            key = (sid, json.dumps(q, sort_keys=True), response)
            if key not in cache:
                state = make_state(scenario)
                updated_state = apply_response(state, q, response)
                cache[key] = engine.infer(updated_state)
            after = cache[key]
            gold = world["profile"]
            before_m = state_metrics(prior, gold)
            after_m = state_metrics(after, gold)
            before_r = ranking_metrics(prior["ranked_actions"], world["relevant_artwork_ids"])
            after_r = ranking_metrics(after["ranked_actions"], world["relevant_artwork_ids"])
            decision = after["decision"]
            selected = (decision["artwork_id"] in world["relevant_artwork_ids"]) if decision["action_type"] == "recommend" else None
            output.append({
                "scenario_id": sid, "method": method,
                "category": r["category"], "subset": r["subset"],
                "world_index": world_i, "world_count": len(scenario["worlds"]),
                "response": response,
                "question_grounded": r["question_grounded"],
                "expected_clarify": r["clarification_needed_by_authored_label"],
                "primary_accuracy_before": float(before_m["primary_explanation_accuracy"]),
                "primary_accuracy_after": float(after_m["primary_explanation_accuracy"]),
                "primary_accuracy_delta": float(after_m["primary_explanation_accuracy"]) - float(before_m["primary_explanation_accuracy"]),
                "explanation_precision_delta": float(after_m["explanation_precision"]) - float(before_m["explanation_precision"]),
                "explanation_recall_delta": float(after_m["explanation_recall"]) - float(before_m["explanation_recall"]),
                "top1_relevance_before": float(before_r["top1_relevance"]),
                "top1_relevance_after": float(after_r["top1_relevance"]),
                "top1_relevance_delta": float(after_r["top1_relevance"]) - float(before_r["top1_relevance"]),
                "post_action_type": decision["action_type"],
                "selected_recommendation_relevant_after": selected,
                "post_unresolved_explanation_count": after.get("unresolved_explanation_count"),
            })
    return output


def summarize_loop(cases: list[dict], loop_rows: list[dict]) -> dict:
    """Aggregate per SCENARIO; ambiguous worlds are not independent samples."""
    scenario_map = {s["scenario_id"]: s for s in cases}
    grouped: dict[str, dict[str, list[dict]]] = {m: defaultdict(list) for m in METHODS}
    for row in loop_rows:
        grouped[row["method"]][row["scenario_id"]].append(row)
    fields = (
        "primary_accuracy_delta", "explanation_precision_delta", "explanation_recall_delta",
        "top1_relevance_delta", "top1_relevance_after",
    )

    def per_case_mean(method: str, sid: str, field: str) -> float:
        entries = grouped[method].get(sid, [])
        return sum(r[field] for r in entries) / len(entries) if entries else 0.0

    expected_sids = [s["scenario_id"] for s in cases if s["expected_action_type"] == "clarify"]
    output: dict[str, Any] = {}
    for method in METHODS:
        questioned = list(grouped[method])
        conditional = {
            field: round(sum(per_case_mean(method, sid, field) for sid in questioned) / len(questioned), 6)
            if questioned else None
            for field in fields
        }
        # Missed clarification contributes zero to post-answer progress. This
        # is intentionally distinct from the selection-biased asked-only mean.
        unconditional = {
            field: round(sum(per_case_mean(method, sid, field) for sid in expected_sids) / len(expected_sids), 6)
            if expected_sids else None
            for field in fields[:-1]
        }
        post_decisions = [r for rows in grouped[method].values() for r in rows
                          if r["selected_recommendation_relevant_after"] is not None]
        output[method] = {
            "questioned_scenarios": len(questioned),
            "questioned_scenarios_expected_clarify": sum(scenario_map[sid]["expected_action_type"] == "clarify" for sid in questioned),
            "questioned_scenarios_not_expected_clarify": sum(scenario_map[sid]["expected_action_type"] != "clarify" for sid in questioned),
            "mean_delta_among_asked_scenarios": conditional,
            "mean_delta_among_all_expected_clarify_scenarios_missed_as_zero": unconditional,
            "post_selected_recommendation_relevance_conditional_on_recommend": safe_div(
                sum(bool(r["selected_recommendation_relevant_after"]) for r in post_decisions), len(post_decisions)
            ),
            "post_recommendations_made_across_worlds": len(post_decisions),
        }
    paired = set(grouped[PROLOG]) & set(grouped[LLM])
    output["matched_both_asked"] = {
        "scenario_count": len(paired),
        **{m: {
            "mean_primary_accuracy_delta": round(sum(per_case_mean(m, sid, "primary_accuracy_delta") for sid in paired) / len(paired), 6) if paired else None,
            "mean_top1_relevance_delta": round(sum(per_case_mean(m, sid, "top1_relevance_delta") for sid in paired) / len(paired), 6) if paired else None,
        } for m in METHODS},
    }
    return output


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list, tuple)) else v for k, v in row.items()})


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1], help="Repository root")
    parser.add_argument("--source", choices=("onepass", "final", "both"), default="both")
    parser.add_argument("--benchmark", choices=("robustness", "regression", "all"), default="robustness")
    parser.add_argument("--closed-loop", action="store_true", help="Replay selected questions with SWI-Prolog; makes NO LLM API calls")
    parser.add_argument("--output-dir", type=Path, help="Directory for new report files (default: evaluation/clarification_analysis)")
    args = parser.parse_args()
    root = args.root.resolve()
    outdir = (args.output_dir or root / "evaluation" / "clarification_analysis").resolve()
    outdir.mkdir(parents=True, exist_ok=True)
    sources = SOURCES.keys() if args.source == "both" else (args.source,)
    for source in sources:
        cases, evidence, result_rows = load_dataset(root, source, args.benchmark)
        rows = analyze_cases(cases, evidence, result_rows)
        summary = {
            "source": source, "benchmark": args.benchmark,
            "scenario_count": len(cases),
            "methods": summarize_cases(rows),
            "definitions": {
                "positive_label": "Authored expected_action_type == clarify (NOT independent human judgment)",
                "invalid_handling": "Invalid LLM output counts as missed clarification when clarify was expected, never as true negative",
                "grounding": "Positive: liked artwork records every queried component or exact explicit interest. Contextual relation additionally counts observed dislikes (weaker). Settled exact interests are not unresolved",
                "world_information_gain": "Binary yes/no partition entropy ONLY for the few scenarios with multiple authored latent worlds; no entropy metric for one-world cases",
                "ranking": "Saved model-derived ranking is NOT necessarily the LLM's chosen artwork",
            },
        }
        prefix = f"{source}_{args.benchmark}"
        write_csv(outdir / f"{prefix}_questions.csv", rows)
        if args.closed_loop:
            loop_rows = run_closed_loop(root, cases, rows, result_rows, evidence)
            write_csv(outdir / f"{prefix}_counterfactual_loop.csv", loop_rows)
            summary["counterfactual_shared_prolog_updater"] = summarize_loop(cases, loop_rows)
            summary["counterfactual_caveat"] = (
                "Both systems' question choices are evaluated with the SAME Prolog updater and an exact membership oracle. "
                "This does not evaluate real human replies or LLM follow-up reasoning. "
                "Per-method deltas conditional on asking are selection-biased; inspect the both-asked paired subset and ask-rate separately."
            )
        (outdir / f"{prefix}_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"{source}/{args.benchmark}: {len(cases)} scenarios, " + "; ".join(
            f"{m}: P={v['clarification_precision']} R={v['clarification_recall_including_invalid_as_missed']} "
            f"grounded={v['question_grounding_rate_given_asked']}" for m,v in summary["methods"].items()))
        print(f"Wrote {outdir / (prefix + '_summary.json')}")


if __name__ == "__main__":
    main()
