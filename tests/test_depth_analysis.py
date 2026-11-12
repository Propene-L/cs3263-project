from __future__ import annotations

import csv
from pathlib import Path

import pytest

from evaluation.depth_analysis.multi_round import (
    analyse_multi_round,
    run_multi_round_analysis,
    validate_headline_totals,
    write_csv,
)


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
    root = Path(__file__).resolve().parents[1]
    import json

    results = json.loads(
        (root / "evaluation" / "phase_1_1_results.json").read_text(encoding="utf-8")
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
    root = Path(__file__).resolve().parents[1]
    first = tmp_path / "first"
    second = tmp_path / "second"
    summary = run_multi_round_analysis(
        root / "evaluation" / "phase_1_1_results.json", first
    )
    run_multi_round_analysis(
        root / "evaluation" / "phase_1_1_results.json", second
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
