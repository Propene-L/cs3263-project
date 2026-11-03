"""Audit diagnostic targeting of saved Phase 1.2 clarification questions.

Zero model/API calls. Reads committed Phase 1.2 scenarios, saved questions, and
reviewed ArtGraph attributes. Reports a transparent, assumption-dependent
plausible-explanation proxy; it is NOT a learned posterior, an empirical
information-gain estimate, or independent human relevance judgement.

Run from project root:
  python -m evaluation.audit_diagnostic_questions --source both
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
PROLOG = "compositional_prolog"
LLM = "direct_llm_state_reasoning"
METHODS = (PROLOG, LLM)
CATEGORIES = ("competitive", "strict", "permissive")
RESULT_FILES = {
    "final": "final_robustness_questions.csv",
    "onepass": "onepass_robustness_questions.csv",
}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    keys = list(dict.fromkeys(k for row in rows for k in row))
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict, tuple)) else v for k, v in row.items()})


def explanation_key(kind: str, components: Iterable[str]) -> str:
    return kind + ":" + "+".join(sorted(components))


def active_observations(scenario: dict) -> list[dict]:
    observations = scenario.get("observations", [])
    removed = {o["supersedes"] for o in observations if o.get("supersedes")}
    return [o for o in observations if o["id"] not in removed]


def visible_support(evidence: dict, scenario: dict) -> dict[str, set[str]]:
    """Use only facts visible to models; missing facts never imply negation."""
    mapping = {(h["attribute_type"], h["value_id"]): h["id"] for h in evidence["hypotheses"]}
    hidden = set(scenario.get("hidden_fact_ids") or [])
    return {
        aid: {mapping[(a["type"], a["value_id"])] for a in entry["attributes"]
              if (a["type"], a["value_id"]) in mapping and not hidden.intersection(a["fact_ids"])}
        for aid, entry in evidence["artworks"].items()
    }


def parse_explicit(observations: list[dict]) -> tuple[set[str], set[str]]:
    confirmed, rejected = set(), set()
    for o in observations:
        kind = o["kind"]
        if kind in {"explicit_interest", "explicit_rejection", "reject_atomic_explanation"}:
            k = explanation_key("atomic", [o["object_id"]])
        elif kind in {"explicit_conjunction", "reject_conjunction", "reject_pair_explanation"}:
            k = explanation_key("all_of", o.get("components", []))
        else:
            continue
        if kind in {"explicit_interest", "explicit_conjunction"}:
            confirmed.add(k)
        else:
            rejected.add(k)
    return confirmed, rejected


def eligible_explanations(evidence: dict) -> list[tuple[str, tuple[str, ...]]]:
    """Independently enumerate atomic and permitted cross-type pairs.

    These are *possible explanation forms*, not proof that a visitor holds any
    such interest. Never use gold profiles or Prolog outputs here.
    """
    definitions = {h["id"]: h["attribute_type"] for h in evidence["hypotheses"]}
    names = sorted(definitions)
    candidates = [("atomic", (h,)) for h in names]
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            types = {definitions[a], definitions[b]}
            if len(types) == 2 and types <= {"tag", "style", "genre"}:
                candidates.append(("all_of", (a, b)))
    return candidates


def plausible_explanations(evidence: dict, scenario: dict, threshold: str) -> dict:
    """Build an evidence-competition set without reading latent profiles.

    competitive: allow one fewer positive artwork than best-supported candidate
    strict: require recorded support in every liked artwork
    permissive: any liked artwork suffices

    Candidates explicitly settled by the visitor are excluded from questions.
    The competitive tolerance accommodates one outlier and multiple interests;
    sensitivity analysis is required because no threshold is psychological truth.
    """
    if threshold not in CATEGORIES:
        raise ValueError(threshold)
    visible = visible_support(evidence, scenario)
    observations = active_observations(scenario)
    likes = [visible[o["object_id"]] for o in observations if o["kind"] == "likes"]
    confirmed, rejected = parse_explicit(observations)
    scored = []
    for kind, components in eligible_explanations(evidence):
        k = explanation_key(kind, components)
        if k in confirmed or k in rejected:
            continue
        if kind == "all_of" and all(explanation_key("atomic", [h]) in confirmed for h in components):
            # Explicit independent interests do not alone establish conjunction.
            continue
        count = sum(set(components) <= liked_support for liked_support in likes)
        scored.append({"key": k, "kind": kind, "components": components, "liked_support_count": count})
    max_support = max((row["liked_support_count"] for row in scored), default=0)
    minimum = {
        "competitive": max(1, max_support - 1),
        "strict": max(1, len(likes)),
        "permissive": 1,
    }[threshold]
    viable = [row for row in scored if row["liked_support_count"] >= minimum]
    return {
        "viable": viable,
        "keys": {row["key"] for row in viable},
        "max_liked_support": max_support,
        "min_required_support": minimum,
        "liked_count": len(likes),
        "declared_missing_evidence": bool(scenario.get("evidence_incomplete") or scenario.get("hidden_fact_ids")),
        "explicit_confirmed": sorted(confirmed),
        "explicit_rejected": sorted(rejected),
    }


def binary_entropy(p: float) -> float:
    if p <= 0 or p >= 1:
        return 0.0
    return -p * math.log2(p) - (1-p) * math.log2(1-p)


def score_question(question_row: dict, space: dict) -> dict:
    """A structural proxy, not measured psychological information gain.

    The uniform demonstration space has one world for each viable *single*
    explanation, plus an 'other/unmodeled' world. Asking whether candidate X
    is true partitions one candidate against the remaining alternatives.
    We deliberately do NOT call this an empirical posterior or optimal policy.
    """
    if question_row.get("asked_clarification") != "True":
        return {"diagnostic_candidate": False, "structural_proxy_bits": 0.0, "question_key": ""}
    try:
        components = json.loads(question_row.get("question_components", "[]"))
        kind = question_row.get("question_kind", "")
        if kind not in {"atomic", "all_of"} or not isinstance(components, list):
            raise ValueError("invalid question")
        if len(components) != (1 if kind == "atomic" else 2) or len(set(components)) != len(components):
            raise ValueError("wrong arity")
        key = explanation_key(kind, components)
    except (ValueError, TypeError, json.JSONDecodeError):
        return {"diagnostic_candidate": False, "structural_proxy_bits": 0.0, "question_key": "invalid"}
    matched = key in space["keys"]
    p = 1 / (len(space["viable"]) + 1) if matched else 0.0
    return {"diagnostic_candidate": matched, "structural_proxy_bits": round(binary_entropy(p), 6), "question_key": key}


def audit(scenarios: list[dict], evidence: dict, questions: list[dict], threshold: str) -> list[dict]:
    by_id = {s["scenario_id"]: s for s in scenarios}
    expected = {(s["scenario_id"], m) for s in scenarios for m in METHODS}
    found = {(q["scenario_id"], q["method"]) for q in questions}
    if expected != found or len(found) != len(questions):
        raise ValueError(f"Question table scenario/method mismatch (missing={len(expected-found)}, extra={len(found-expected)})")
    spaces = {sid: plausible_explanations(evidence, s, threshold) for sid, s in by_id.items()}
    output = []
    for question in questions:
        sid = question["scenario_id"]
        s = by_id[sid]
        space = spaces[sid]
        score = score_question(question, space)
        output.append({
            "scenario_id": sid,
            "category": s.get("category", s.get("family")),
            "subset": s["subset"],
            "method": question["method"],
            "valid_output": question["valid_output"] == "True",
            "expected_action": question["expected_action"],
            "predicted_action": question["predicted_action"],
            "asked_clarification": question["asked_clarification"] == "True",
            "question_key": score["question_key"],
            "previous_grounding": question.get("question_grounded", ""),
            "diagnostic_candidate": score["diagnostic_candidate"],
            "structural_proxy_bits": score["structural_proxy_bits"],
            "viable_explanation_count": len(space["viable"]),
            "viable_explanations": sorted(space["keys"]),
            "max_liked_support": space["max_liked_support"],
            "min_required_support": space["min_required_support"],
            "liked_observation_count": space["liked_count"],
            "declared_missing_evidence": space["declared_missing_evidence"],
            "controlled_world_count": len(s["worlds"]),
            "controlled_world_information_gain_bits": (
                question.get("world_information_gain_bits") or ""
            ),
        })
    return output


def summary(rows: list[dict]) -> dict:
    output: dict[str, dict] = {}
    total_need = sum(r["expected_action"] == "clarify" for r in rows if r["method"] == PROLOG)
    for method in METHODS:
        group = [r for r in rows if r["method"] == method]
        asked = [r for r in group if r["asked_clarification"]]
        on_target = [r for r in asked if r["diagnostic_candidate"]]
        needed = [r for r in on_target if r["expected_action"] == "clarify"]
        output[method] = {
            "total_scenarios": len(group),
            "expected_clarification_count": total_need,
            "asked_count": len(asked),
            "diagnostic_targeted_count": len(on_target),
            "diagnostic_targeting_rate_given_asked": round(len(on_target) / len(asked), 6) if asked else None,
            "effective_diagnostic_recall_over_needed": round(len(needed) / total_need, 6) if total_need else None,
            "diagnostic_when_needed_count": len(needed),
            "mean_structural_proxy_bits_given_asked": round(sum(r["structural_proxy_bits"] for r in asked) / len(asked), 6) if asked else None,
            "unnecessary_clarification_count": sum(r["expected_action"] != "clarify" for r in asked),
        }
    return output


def build_blind_review(scenarios: list[dict], evidence: dict, questions: list[dict], audited: list[dict],
                       saved_decisions: dict[tuple[str, str], dict] | None = None,
                       seed: int = 32631204) -> tuple[list[dict], list[dict]]:
    """Produce unscored reviewer sheets. Never expose gold or method identity.

    Reviewers should be able to disagree with both the authored action label
    and the mechanical diagnostic candidate model.
    """
    by_id = {s["scenario_id"]: s for s in scenarios}
    rows = {(x["scenario_id"], x["method"]): x for x in questions}
    scores = {(x["scenario_id"], x["method"]): x for x in audited}
    labels = {h["id"]: h["label"] for h in evidence["hypotheses"]}
    visible_cache = {s["scenario_id"]: visible_support(evidence, s) for s in scenarios}
    saved_decisions = saved_decisions or {}

    def action_text(sid: str, method: str, row: dict) -> str:
        if row.get("valid_output") != "True":
            return "No valid output (interface failure)"
        if row["predicted_action"] == "clarify":
            cs = json.loads(row["question_components"])
            rendered = " and ".join(labels.get(x, x) for x in cs)
            suffix = " specifically together" if row["question_kind"] == "all_of" else " as an interest"
            return "Ask whether the visitor likes " + rendered + suffix
        if row["predicted_action"] == "recommend":
            decision = saved_decisions.get((sid, method), {})
            artwork_id = decision.get("artwork_id")
            if artwork_id in evidence["artworks"]:
                return "Recommend " + evidence["artworks"][artwork_id]["label"] + f" ({artwork_id})"
            return "Recommend an artwork (selected artwork not available in saved comparison)"
        return "Report insufficient evidence"

    sheet, key_rows = [], []
    for sid, s in by_id.items():
        p, l = rows[(sid, PROLOG)], rows[(sid, LLM)]
        ps, ls = scores[(sid, PROLOG)], scores[(sid, LLM)]
        if (p["predicted_action"] == l["predicted_action"] and
                p.get("question_components") == l.get("question_components") and
                ps["diagnostic_candidate"] == ls["diagnostic_candidate"]):
            continue
        hs = hashlib.sha256(f"{seed}:{sid}".encode()).digest()
        order = [PROLOG, LLM]
        random.Random(int.from_bytes(hs[:8], "big")).shuffle(order)
        order_q = [rows[(sid, m)] for m in order]
        evidence_text = []
        for o in active_observations(s):
            if o["kind"] not in {"likes", "dislikes"}:
                continue
            seen = visible_cache[sid].get(o["object_id"], set())
            artwork_label = evidence["artworks"][o["object_id"]]["label"]
            evidence_text.append(f"{o['id']} {o['kind']} {artwork_label}: " + ", ".join(sorted(labels[h] for h in seen)))
        sheet.append({
            "review_id": f"DQ_{len(sheet)+1:02d}", "scenario_id": sid,
            "visitor_history": s["natural_language_history"],
            "visible_observed_evidence": " | ".join(evidence_text),
            "declared_incomplete_evidence": bool(s.get("evidence_incomplete") or s.get("hidden_fact_ids")),
            "action_a": action_text(sid, order[0], order_q[0]),
            "action_b": action_text(sid, order[1], order_q[1]),
            "clarification_needed_yes_no_unsure": "",
            "more_diagnostic_a_b_equal_neither": "",
            "action_more_appropriate_a_b_equal_neither": "",
            "question_a_grounded_yes_no_unsure": "",
            "question_b_grounded_yes_no_unsure": "",
            "reviewer_notes": "",
        })
        key_rows.append({"review_id": sheet[-1]["review_id"], "scenario_id": sid,
                         "method_a": order[0], "method_b": order[1],
                         "predicted_a": order_q[0]["predicted_action"],
                         "predicted_b": order_q[1]["predicted_action"]})
    return sheet, key_rows


def run(root: Path, source: str = "both", output_dir: Path | None = None, make_review: bool = True) -> dict:
    scenario_paths = [root / "evaluation/preference_state_robustness_scenarios.jsonl"]
    scenarios = [s for p in scenario_paths for s in read_jsonl(p)]
    evidence = json.loads((root / "data/curated/clarification_evidence.json").read_text(encoding="utf-8"))
    out = output_dir or root / "evaluation/diagnostic_question_analysis"
    out.mkdir(parents=True, exist_ok=True)
    output = {"source_commit": "945b009db765d9321bf97dbeaaccc88c063cd4e3", "benchmark": "controlled_robustness", "scenario_count": len(scenarios), "sources": {}}
    for src in (RESULT_FILES if source == "both" else [source]):
        source_path = root / "evaluation/clarification_analysis" / RESULT_FILES[src]
        questions = read_csv(source_path)
        output["sources"][src] = {}
        for threshold in CATEGORIES:
            audited = audit(scenarios, evidence, questions, threshold)
            output["sources"][src][threshold] = summary(audited)
            write_csv(out / f"{src}_{threshold}_questions.csv", audited)
            if threshold == "competitive" and src == "final" and make_review:
                decisions = {}
                final_path = root / "evaluation/preference_state_llm_final_comparison_results.json"
                if final_path.is_file():
                    final = json.loads(final_path.read_text(encoding="utf-8"))
                    for row in final.get("scenarios", []):
                        for method, value in row.get("methods", {}).items():
                            result = value.get("result", value)
                            decisions[(row["scenario_id"], method)] = result.get("decision", {})
                sheet, key_rows = build_blind_review(scenarios, evidence, questions, audited, decisions)
                write_csv(out / "blind_review_questions.csv", sheet)
                write_csv(out / "blind_review_PRIVATE_key.csv", key_rows)
                output["blind_review_items"] = len(sheet)
    output["definitions"] = {
        "competitive": "Unsettled atomic or cross-type pair explains at least max(1, max liked-support count minus one) positive artworks.",
        "strict": "Unsettled explanation appears in every liked artwork.",
        "permissive": "Unsettled explanation appears in at least one liked artwork.",
        "candidate_vocabulary": "Atomic hypotheses and observed co-occurring tag-style, tag-genre or style-genre conjunctions. No latent labels read.",
        "structural_proxy_bits": "Entropy of yes/no for uniform mutually exclusive candidate explanations plus other. NOT an empirical or psychological information-gain estimate.",
        "limitations": "Only single-explanation-plus-other alternatives; observed preferences may be multi-interest, noisy, or driven by non-vocabulary attributes. Binary answer oracle and authored expected-action labels are not human truth.",
        "llm": "SOCLAAS default model; final source includes selectively repaired second chances. Always report one-pass separately.",
    }
    (out / "diagnostic_question_summary.json").write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--source", choices=("both", "onepass", "final"), default="both")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--no-review", action="store_true")
    args = parser.parse_args()
    summary_out = run(args.root.resolve(), args.source, args.output_dir, not args.no_review)
    print(json.dumps(summary_out["sources"], indent=2))
    print("Scenario count:", summary_out["scenario_count"])


if __name__ == "__main__":
    main()
