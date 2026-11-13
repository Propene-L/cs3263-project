from __future__ import annotations

import csv
from pathlib import Path

import pytest

from evaluation.depth_analysis.clarification_decisions import (
    analyse_clarification_decisions,
)
from evaluation.depth_analysis.difficulty import analyse_difficulty
from evaluation.depth_analysis.interaction_ablation import (
    _summarize_condition,
    evaluate_ablation,
)
from evaluation.depth_analysis.llm_failures import analyse_llm_failures
from evaluation.depth_analysis.multi_round import (
    analyse_multi_round,
    run_multi_round_analysis,
    validate_headline_totals,
    write_csv,
)


ROOT = Path(__file__).resolve().parents[1]


def _method_result(
    *,
    initial_count: int,
    rounds: list[dict],
    correctly_resolved: bool,
    initially_solvable: bool,
    initially_resolved: bool,
    initially_unsolvable: bool,
    stopping_reason: str,
) -> dict:
    return {
        "initial_hypothesis_count": initial_count,
        "rounds": rounds,
        "question_count": sum(bool(item.get("selected")) for item in rounds),
        "correctly_resolved": correctly_resolved,
        "initially_solvable": initially_solvable,
        "initially_resolved": initially_resolved,
        "initially_unsolvable": initially_unsolvable,
        "stopping_reason": stopping_reason,
    }


def _selected_round(index: int, remaining: int, eliminated: int) -> dict:
    return {
        "round": index,
        "selected": True,
        "remaining_hypothesis_count": remaining,
        "eliminated_hypothesis_ids": [f"h_{index}_{item}" for item in range(eliminated)],
    }


def _fixture_results() -> dict:
    method = "test_method"
    records = [
        (
            "resolved_after_one",
            _method_result(
                initial_count=3,
                rounds=[_selected_round(1, 1, 2)],
                correctly_resolved=True,
                initially_solvable=True,
                initially_resolved=False,
                initially_unsolvable=False,
                stopping_reason="resolved_unique",
            ),
        ),
        (
            "round_limit",
            _method_result(
                initial_count=3,
                rounds=[
                    _selected_round(1, 2, 1),
                    _selected_round(2, 2, 0),
                    _selected_round(3, 2, 0),
                ],
                correctly_resolved=False,
                initially_solvable=True,
                initially_resolved=False,
                initially_unsolvable=False,
                stopping_reason="round_limit",
            ),
        ),
        (
            "selection_error",
            _method_result(
                initial_count=2,
                rounds=[
                    {
                        "round": 1,
                        "active_hypothesis_ids_before": ["h_a", "h_b"],
                        "selection_error": "synthetic error",
                    }
                ],
                correctly_resolved=False,
                initially_solvable=True,
                initially_resolved=False,
                initially_unsolvable=False,
                stopping_reason="selection_error",
            ),
        ),
        (
            "initially_resolved",
            _method_result(
                initial_count=1,
                rounds=[],
                correctly_resolved=True,
                initially_solvable=False,
                initially_resolved=True,
                initially_unsolvable=False,
                stopping_reason="initially_resolved",
            ),
        ),
        (
            "initially_unsolvable",
            _method_result(
                initial_count=2,
                rounds=[],
                correctly_resolved=False,
                initially_solvable=False,
                initially_resolved=False,
                initially_unsolvable=True,
                stopping_reason="no_valid_discriminative_question",
            ),
        ),
    ]
    return {
        "configuration": {"methods": [method], "max_rounds": 3},
        "scenario_count": len(records),
        "scenarios": [
            {"scenario_id": scenario_id, "methods": {method: result}}
            for scenario_id, result in records
        ],
    }


def test_fixed_cohort_denominator_and_terminal_carry_forward() -> None:
    resolution, trajectory = analyse_multi_round(_fixture_results())
    summary = resolution[0]

    assert summary["initially_solvable_count"] == 3
    assert [summary[f"resolved_after_round_{index}_count"] for index in range(4)] == [
        0,
        1,
        1,
        1,
    ]
    assert [row["fixed_cohort_size"] for row in trajectory] == [3, 3, 3, 3]
    assert [row["fixed_cohort_mean_active_hypotheses"] for row in trajectory] == pytest.approx(
        [8 / 3, 5 / 3, 5 / 3, 5 / 3], abs=1e-6
    )
    assert [row["selected_question_count_this_round"] for row in trajectory] == [
        0,
        2,
        1,
        1,
    ]


def test_stopping_reasons_and_question_elimination_are_kept_separate() -> None:
    resolution, _ = analyse_multi_round(_fixture_results())
    summary = resolution[0]

    assert summary["resolution_stop_count"] == 2
    assert summary["resolved_after_question_stop_count"] == 1
    assert summary["initially_resolved_stop_count"] == 1
    assert summary["no_discriminative_pair_stop_count"] == 1
    assert summary["round_limit_stop_count"] == 1
    assert summary["error_stop_count"] == 1
    assert (
        summary["mean_hypotheses_eliminated_per_selected_question_all_scenarios"]
        == 0.75
    )
    assert (
        summary["mean_hypotheses_eliminated_per_selected_question_fixed_cohort"]
        == 0.75
    )


def test_committed_results_reproduce_headline_denominator_and_totals() -> None:
    import json

    results = json.loads(
        (ROOT / "evaluation" / "phase_1_1_results.json").read_text(encoding="utf-8")
    )
    resolution, _ = analyse_multi_round(results)
    validate_headline_totals(resolution)

    assert {row["initially_solvable_count"] for row in resolution} == {57}


def test_csv_output_is_stable(tmp_path: Path) -> None:
    resolution, trajectory = analyse_multi_round(_fixture_results())
    first = tmp_path / "first.csv"
    second = tmp_path / "second.csv"
    write_csv(first, resolution + trajectory[:0])
    write_csv(second, resolution + trajectory[:0])
    assert first.read_bytes() == second.read_bytes()

    with first.open(encoding="utf-8", newline="") as handle:
        assert next(csv.DictReader(handle))["method"] == "test_method"


def test_generated_artifacts_are_deterministic_and_figure_uses_saved_csv(
    tmp_path: Path,
) -> None:
    pytest.importorskip("matplotlib")
    first = tmp_path / "first"
    second = tmp_path / "second"
    summary = run_multi_round_analysis(
        ROOT / "evaluation" / "phase_1_1_results.json", first
    )
    run_multi_round_analysis(
        ROOT / "evaluation" / "phase_1_1_results.json", second
    )

    assert summary["fixed_cohort_size"] == 57
    assert (first / "multi_round_trajectory.csv").is_file()
    assert (first / "fig_multi_round_resolution.png").stat().st_size > 10_000
    assert (first / "fig_multi_round_resolution.svg").stat().st_size > 10_000
    for name in (
        "multi_round_resolution.csv",
        "multi_round_trajectory.csv",
        "fig_multi_round_resolution.png",
        "fig_multi_round_resolution.svg",
    ):
        assert (first / name).read_bytes() == (second / name).read_bytes()


def test_difficulty_breakdown_uses_paired_scenarios() -> None:
    import json

    results = json.loads(
        (ROOT / "evaluation" / "phase_1_1_results.json").read_text(encoding="utf-8")
    )
    rows = analyse_difficulty(results)
    by_key = {(row["stratum"], row["method"]): row for row in rows}

    assert by_key[("exactly_2", "compositional_prolog")]["scenario_count"] == 14
    assert by_key[("3_or_more", "compositional_prolog")]["scenario_count"] == 43
    hard = by_key[("3_or_more", "compositional_prolog")]
    assert hard["resolved_count"] == 30
    assert hard["paired_method_only_success_count"] == 18
    assert hard["paired_single_rule_only_success_count"] == 1
    assert (
        hard["paired_method_only_success_count"]
        + hard["paired_single_rule_only_success_count"]
        + hard["paired_both_success_count"]
        + hard["paired_neither_success_count"]
        == hard["scenario_count"]
    )


def test_multi_world_summary_keeps_scenario_as_sample_unit() -> None:
    scenario_rows = [
        {
            "category": "ambiguous",
            "world_count": 2,
            "expected_action_type": "clarify",
            "conditions": {
                "full_corrected_v2": {
                    "result": {"decision": {"action_type": "clarify"}},
                    "metrics": {
                        "primary_explanation_accuracy": 0.5,
                        "explanation_precision": 0.5,
                        "explanation_recall": 1.0,
                        "false_interaction_rate": 0.5,
                        "false_atomic_interest_rate": 0.0,
                        "action_type_accuracy": 1.0,
                        "top1_relevance": 0.5,
                        "appropriate_abstention": 1.0,
                    },
                }
            },
        }
    ]
    summary = _summarize_condition(scenario_rows, "full_corrected_v2")
    ambiguous = next(row for row in summary if row["category"] == "ambiguous")

    assert ambiguous["scenario_count"] == 1
    assert ambiguous["world_count"] == 2
    assert ambiguous["primary_explanation_accuracy"] == 0.5


@pytest.fixture(scope="module")
def ablation_result() -> dict:
    return evaluate_ablation(
        ROOT,
        ROOT / "evaluation" / "preference_state_robustness_scenarios.jsonl",
        ROOT / "data" / "curated" / "clarification_evidence.json",
        ROOT / "evaluation" / "preference_state_corrected_results.json",
    )


def test_interaction_ablation_changes_only_the_intended_inference(
    ablation_result: dict,
) -> None:
    by_id = {row["scenario_id"]: row for row in ablation_result["scenarios"]}
    ambiguous = by_id["ambiguous_albert"]
    full = ambiguous["conditions"]["full_corrected_v2"]["result"]
    ablated = ambiguous["conditions"]["no_interaction_ablation"]["result"]

    assert any(
        item["kind"] == "all_of" and item["status"] == "interaction_candidate"
        for item in full["preference_explanations"]
    )
    assert not any(
        item["status"] == "interaction_candidate"
        for item in ablated["preference_explanations"]
    )
    assert ambiguous["changes"]["clarification_question_changed"] is True
    assert ambiguous["changes"]["action_type_changed"] is False
    assert ablation_result["change_counts"]["scenario_ids_with_any_change"] == [
        "ambiguous_albert"
    ]


def test_explicit_conjunction_survives_ablation(ablation_result: dict) -> None:
    scenario = next(
        row
        for row in ablation_result["scenarios"]
        if row["scenario_id"] == "conjunction_style_portrait"
    )
    for condition in ("full_corrected_v2", "no_interaction_ablation"):
        explanations = scenario["conditions"][condition]["result"][
            "preference_explanations"
        ]
        assert any(
            item["kind"] == "all_of" and item["status"] == "explicitly_confirmed"
            for item in explanations
        )
    assert scenario["changes"]["explanation_set_changed"] is False


def test_default_prolog_behavior_matches_committed_results(ablation_result: dict) -> None:
    # evaluate_ablation validates every full result against the committed signatures.
    assert ablation_result["scenario_count"] == 32
    production_rules = (
        ROOT / "logic" / "preference_state_corrected_rules.pl"
    ).read_text(encoding="utf-8")
    assert "c_interaction(V, Cs, Proof)" in production_rules
    assert ":- abolish(c_interaction/3)." not in production_rules


def test_invalid_llm_outputs_stay_in_end_to_end_denominator() -> None:
    rows, metadata = analyse_llm_failures(ROOT)
    summary = {
        row["metric"]: row
        for row in rows
        if row["record_type"] == "summary_metric"
    }

    assert metadata["strict_valid_count"] == 2
    assert metadata["normalized_valid_count"] == 31
    assert metadata["accepted_after_repair_count"] == 53
    assert metadata["valid_decision_count"] == 51
    assert metadata["total_requests"] == 77
    assert summary["end_to_end_action_correctness"]["numerator"] == 34
    assert summary["end_to_end_action_correctness"]["denominator"] == 56


def test_clarification_analysis_keeps_timing_and_quality_separate() -> None:
    rows, metadata = analyse_clarification_decisions(ROOT)
    stage_1 = [row for row in rows if row["record_type"] == "stage_1_when_to_ask"]
    stage_2 = [row for row in rows if row["record_type"] == "stage_2_what_to_ask"]

    assert len(stage_1) == 4
    assert len(stage_2) == 2
    assert metadata["both_asked_scenario_ids"] == [
        "ambiguous_cellist",
        "independent_feline_impressionist",
        "noisy_water",
    ]
    cellist = [
        item
        for item in metadata["paired_details"]
        if item["scenario_id"] == "ambiguous_cellist"
    ]
    assert next(item for item in cellist if item["method"] == "compositional_prolog")[
        "world_split"
    ] is False
    assert next(
        item for item in cellist if item["method"] == "direct_llm_state_reasoning"
    )["world_split"] is True
