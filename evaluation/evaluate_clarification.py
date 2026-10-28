"""Run controlled active-clarification experiments and ablations."""

from __future__ import annotations

import argparse
import json
import statistics
import time
from pathlib import Path
from typing import Any

from museum_guide.clarification import (
    ClarificationObservation,
    ClarificationState,
    default_engine,
)
from museum_guide.clarification_baselines import (
    AttributeContrastSelector,
    BaselineQuestion,
    DirectLLMSelector,
    HTTPJSONLLMTransport,
    RandomPairSelector,
)

ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--scenarios", default=str(ROOT / "evaluation" / "clarification_scenarios.jsonl")
    )
    parser.add_argument(
        "--output", default=str(ROOT / "evaluation" / "clarification_results.json")
    )
    parser.add_argument("--max-rounds", type=int, default=3)
    parser.add_argument("--run-direct-llm", action="store_true")
    return parser.parse_args()


def load_jsonl(path: str | Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in Path(path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def make_state(scenario: dict[str, Any], mode: str = "compositional") -> ClarificationState:
    return ClarificationState(
        session_id=scenario["scenario_id"],
        observations=tuple(ClarificationObservation(**item) for item in scenario["observations"]),
        allowed_artwork_ids=tuple(scenario["allowed_artwork_ids"]),
        rejected_hypothesis_ids=tuple(scenario["rejected_hypothesis_ids"]),
        mode=mode,
    )


class IndependentEvidenceJudge:
    """Checks contrasts from exported positive facts, independently of Prolog proofs."""

    def __init__(self, evidence: dict[str, Any]) -> None:
        self.definition = {
            item["id"]: (item["attribute_type"], item["value_id"])
            for item in evidence["hypotheses"]
        }
        self.attributes = {
            artwork: {
                (item["type"], item["value_id"])
                for item in record["attributes"]
            }
            for artwork, record in evidence["artworks"].items()
        }

    def prediction(self, hypothesis: str, option_a: str, option_b: str) -> str:
        attribute = self.definition[hypothesis]
        support_a = attribute in self.attributes.get(option_a, set())
        support_b = attribute in self.attributes.get(option_b, set())
        if support_a and not support_b:
            return "prefer_a"
        if support_b and not support_a:
            return "prefer_b"
        return "unknown"

    def distinction_count(
        self, hypotheses: list[str], option_a: str, option_b: str
    ) -> int:
        predictions = [self.prediction(item, option_a, option_b) for item in hypotheses]
        return sum(
            left != "unknown" and right != "unknown" and left != right
            for index, left in enumerate(predictions)
            for right in predictions[index + 1 :]
        )


def active_from_result(result: dict[str, Any]) -> list[str]:
    return list(result.get("active_hypothesis_ids", []))


def run_symbolic_rounds(
    scenario: dict[str, Any], judge: IndependentEvidenceJudge, max_rounds: int
) -> dict[str, Any]:
    engine = default_engine(ROOT)
    state = make_state(scenario)
    questions: list[dict[str, Any]] = []
    started = time.perf_counter()
    for round_index in range(max_rounds):
        result = engine.clarify(state)
        active = active_from_result(result)
        if result["status"] != "selected":
            break
        question = result["question"]
        option_a = question["option_a"]["artwork_id"]
        option_b = question["option_b"]["artwork_id"]
        independent_count = judge.distinction_count(active, option_a, option_b)
        hidden_response = judge.prediction(
            scenario["hidden_hypothesis_id"], option_a, option_b
        )
        response = hidden_response if hidden_response != "unknown" else "unsure"
        questions.append(
            {
                "question_id": question["question_id"],
                "option_a": option_a,
                "option_b": option_b,
                "independent_distinction_count": independent_count,
                "logically_valid_by_independent_evidence": independent_count > 0,
                "simulated_response": response,
            }
        )
        state = state.apply_response(
            question, response, f"obs_eval_response_{round_index + 1}"
        )
        if len(active) <= 1:
            break
    final_result = engine.clarify(state)
    elapsed_ms = (time.perf_counter() - started) * 1000
    question_ids = [item["question_id"] for item in questions]
    return {
        "method": "compositional_prolog",
        "questions": questions,
        "question_count": len(questions),
        "repeated_question_count": len(question_ids) - len(set(question_ids)),
        "initial_hypothesis_count": len(scenario["hypothesis_ids"]),
        "remaining_hypothesis_count": len(final_result["active_hypothesis_ids"]),
        "resolved_to_one": len(final_result["active_hypothesis_ids"]) == 1,
        "runtime_ms": round(elapsed_ms, 3),
        "final_status": final_result["status"],
    }


def evaluate_pair(
    method: str,
    pair: Any,
    hypotheses: list[str],
    judge: IndependentEvidenceJudge,
    elapsed_ms: float,
) -> dict[str, Any]:
    if pair is None:
        return {
            "method": method,
            "selected": False,
            "independent_distinction_count": 0,
            "logically_valid_by_independent_evidence": False,
            "runtime_ms": round(elapsed_ms, 3),
        }
    count = judge.distinction_count(
        hypotheses, pair.option_a_id, pair.option_b_id
    )
    return {
        "method": method,
        "selected": True,
        "option_a": pair.option_a_id,
        "option_b": pair.option_b_id,
        "independent_distinction_count": count,
        "logically_valid_by_independent_evidence": count > 0,
        "runtime_ms": round(elapsed_ms, 3),
    }


def aggregate(rows: list[dict[str, Any]], method: str) -> dict[str, Any]:
    method_rows = [row[method] for row in rows]
    if method == "compositional_prolog":
        valid = [
            question["logically_valid_by_independent_evidence"]
            for row in method_rows
            for question in row["questions"]
        ]
        distinctions = [
            question["independent_distinction_count"]
            for row in method_rows
            for question in row["questions"]
        ]
        return {
            "scenario_count": len(method_rows),
            "question_count": sum(row["question_count"] for row in method_rows),
            "valid_question_rate": round(sum(valid) / len(valid), 4) if valid else None,
            "mean_distinguished_pairs_per_question": round(statistics.fmean(distinctions), 4) if distinctions else None,
            "resolved_to_one_count": sum(row["resolved_to_one"] for row in method_rows),
            "mean_runtime_ms": round(statistics.fmean(row["runtime_ms"] for row in method_rows), 3),
            "repeated_question_count": sum(row["repeated_question_count"] for row in method_rows),
        }
    selected = [row for row in method_rows if row.get("selected")]
    return {
        "scenario_count": len(method_rows),
        "selected_count": len(selected),
        "valid_selected_rate": round(
            sum(row["logically_valid_by_independent_evidence"] for row in selected)
            / len(selected),
            4,
        ) if selected else None,
        "mean_distinguished_pairs": round(
            statistics.fmean(row["independent_distinction_count"] for row in selected), 4
        ) if selected else None,
        "mean_runtime_ms": round(statistics.fmean(row["runtime_ms"] for row in method_rows), 3),
    }


def phase_1_main() -> None:
    args = parse_args()
    scenarios = load_jsonl(args.scenarios)
    evidence = json.loads(
        (ROOT / "data" / "curated" / "clarification_evidence.json").read_text(
            encoding="utf-8"
        )
    )
    judge = IndependentEvidenceJudge(evidence)
    random_selector = RandomPairSelector()
    overlap_selector = AttributeContrastSelector(evidence)
    direct_transport = HTTPJSONLLMTransport.from_environment() if args.run_direct_llm else None
    direct_selector = DirectLLMSelector(direct_transport, evidence) if direct_transport else None
    engine = default_engine(ROOT)
    rows: list[dict[str, Any]] = []

    for scenario in scenarios:
        hypotheses = [
            item for item in scenario["hypothesis_ids"]
            if item not in scenario["rejected_hypothesis_ids"]
        ]
        compositional = run_symbolic_rounds(scenario, judge, args.max_rounds)

        single_state = make_state(scenario, mode="single_rule")
        started = time.perf_counter()
        single_result = engine.clarify(single_state)
        single_elapsed = (time.perf_counter() - started) * 1000
        if single_result["status"] == "selected":
            question = single_result["question"]
            single_pair = BaselineQuestion(
                "single_rule_prolog",
                question["option_a"]["artwork_id"],
                question["option_b"]["artwork_id"],
                question["deterministic_score"],
                {},
            )
        else:
            single_pair = None

        base_state = make_state(scenario)
        started = time.perf_counter()
        random_pair = random_selector.select(base_state)
        random_elapsed = (time.perf_counter() - started) * 1000
        started = time.perf_counter()
        overlap_pair = overlap_selector.select(base_state, hypotheses)
        overlap_elapsed = (time.perf_counter() - started) * 1000

        direct_row: dict[str, Any] = {"method": "direct_llm", "status": "not_run"}
        if direct_selector is not None:
            started = time.perf_counter()
            direct_pair = direct_selector.select(
                base_state, hypotheses, scenario_text=scenario["description"]
            )
            direct_elapsed = (time.perf_counter() - started) * 1000
            direct_row = evaluate_pair(
                "direct_llm", direct_pair, hypotheses, judge, direct_elapsed
            )

        rows.append(
            {
                "scenario_id": scenario["scenario_id"],
                "expected_has_question": scenario["expected_has_question"],
                "compositional_prolog": compositional,
                "single_rule_prolog": evaluate_pair(
                    "single_rule_prolog", single_pair, hypotheses, judge, single_elapsed
                ),
                "raw_attribute_contrast": evaluate_pair(
                    "raw_attribute_contrast", overlap_pair, hypotheses, judge, overlap_elapsed
                ),
                "random_eligible": evaluate_pair(
                    "random_eligible", random_pair, hypotheses, judge, random_elapsed
                ),
                "direct_llm": direct_row,
            }
        )

    summary = {
        method: aggregate(rows, method)
        for method in (
            "compositional_prolog",
            "single_rule_prolog",
            "raw_attribute_contrast",
            "random_eligible",
        )
    }
    result = {
        "schema_version": "1.0",
        "scenario_count": len(scenarios),
        "simulation_notice": "Controlled responses use the declared recorded-support model; they are not human preference outcomes.",
        "direct_llm": "executed" if direct_selector else "not_run_missing_configuration_or_flag",
        "summary": summary,
        "scenarios": rows,
    }
    Path(args.output).write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps(summary, indent=2))
    if direct_selector is None:
        print("direct_llm=not_run_missing_configuration_or_flag")


def main() -> None:
    """Run the Phase 1.1 shared-horizon evaluator on the established path."""

    import sys

    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from evaluation.phase_1_1_evaluate import main as phase_1_1_main

    phase_1_1_main()


if __name__ == "__main__":
    main()
