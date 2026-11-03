"""End-to-end museum guide acceptance runner.

Only reports outcomes from genuine invocations. Fixtures are controlled scripted
cases, not human preference truth. Provider evaluation requires explicit config.
"""
from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path

from museum_guide.dialogue import MuseumDialogue

ROOT = Path(__file__).resolve().parents[1]


def load_jsonl(path: Path) -> list[dict]:
    cases = [json.loads(s) for s in path.read_text(encoding="utf-8").splitlines() if s.strip()]
    seen = set()
    for case in cases:
        if not isinstance(case.get("id"), str) or case["id"] in seen:
            raise ValueError("Duplicate or invalid scenario ID")
        seen.add(case["id"])
        if not isinstance(case.get("turns"), list) or not case["turns"]:
            raise ValueError("Every case must have turns")
        for turn in case["turns"]:
            if not isinstance(turn.get("visitor"), str):
                raise ValueError("Visitor input must be text")
    return cases


def evaluate(guide: MuseumDialogue, cases: list[dict], *, mode: str) -> dict:
    """No perfect visitor oracle: authored expected actions are fixtures only."""
    rows = []
    for case in cases:
        session = guide.new_session("case_" + case["id"])
        for index, spec in enumerate(case["turns"], start=1):
            try:
                next_session, result = guide.run_turn(session, spec["visitor"], mode=mode)
                session = next_session
                action, error = result["action"], None
                sources = result.get("sources", [])
                rule_id = result.get("audit", {}).get("rule_id")
                matches = action == spec["expected_action"] if "expected_action" in spec else None
                source_covered = bool(sources) if action in {"recommend", "explain"} else None
                status = "ok"
            except Exception as exc:
                action, matches, source_covered, sources, rule_id = None, False if "expected_action" in spec else None, None, [], None
                status, error = "error", f"{type(exc).__name__}: {exc}"
            rows.append({"scenario_id": case["id"], "turn": index, "mode": mode,
                         "visitor": spec["visitor"], "status": status,
                         "actual_action": action, "expected_action": spec.get("expected_action"),
                         "action_match_authored": matches,
                         "source_present_when_required": source_covered,
                         "rule_id": rule_id, "source_ids": [x.get("source_id") for x in sources],
                         "error": error})
            if status == "error":
                break
    labeled = [r["action_match_authored"] for r in rows if r["action_match_authored"] is not None]
    source_cases = [r["source_present_when_required"] for r in rows if r["source_present_when_required"] is not None]
    summary = {"mode": mode, "scenario_count": len(cases), "executed_turns": len(rows),
               "error_count": sum(r["status"] == "error" for r in rows),
               "authored_action_match": sum(labeled)/len(labeled) if labeled else None,
               "source_coverage_of_explain_or_recommend": sum(source_cases)/len(source_cases) if source_cases else None,
               "complete_scenarios": sum(any(r["scenario_id"] == c["id"] and r["turn"] == len(c["turns"]) and r["status"] == "ok" for r in rows) for c in cases),
               "warnings": ["Controlled authored actions, not independent visitor labels", "Manual mode is a scripted input interface, not a live model"]}
    return {"summary": summary, "turns": rows}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--mode", choices=["manual", "hybrid", "direct_llm"], default="manual")
    p.add_argument("--input", type=Path, default=ROOT / "evaluation" / "integrated_scenarios.jsonl")
    p.add_argument("--output", type=Path, default=ROOT / ".runtime" / "integrated_evaluation.json")
    args = p.parse_args()
    guide = MuseumDialogue.from_repository(ROOT, use_llm=args.mode != "manual", with_direct=args.mode == "direct_llm")
    cases = load_jsonl(args.input)
    report = evaluate(guide, cases, mode=args.mode)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], indent=2))
    print("Saved", args.output)


if __name__ == "__main__":
    main()
