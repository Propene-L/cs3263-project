from __future__ import annotations

import json
import hashlib
from pathlib import Path

import pytest

from museum_guide.clarification import (
    ClarificationObservation,
    ClarificationState,
    PrologError,
    default_engine,
)
from museum_guide.clarification_baselines import (
    AttributeContrastSelector,
    DirectLLMSelector,
    RandomPairSelector,
    ValidatedLLMObservationExtractor,
)
from museum_guide.prolog_bridge import find_swipl

ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_catalog() -> dict:
    return json.loads(
        (ROOT / "data" / "curated" / "clarification_topic_catalog.json").read_text(
            encoding="utf-8"
        )
    )


def load_evidence() -> dict:
    return json.loads(
        (ROOT / "data" / "curated" / "clarification_evidence.json").read_text(
            encoding="utf-8"
        )
    )


def pair_state(session_id: str = "test_session") -> ClarificationState:
    return ClarificationState(
        session_id=session_id,
        observations=(
            ClarificationObservation("obs_test_music", "explicit_interest", "h_musical_subject"),
            ClarificationObservation("obs_test_style", "explicit_interest", "h_expressionist_style"),
        ),
        allowed_artwork_ids=tuple(load_catalog()["allowed_candidate_ids"]),
    )


@pytest.mark.skipif(find_swipl() is None, reason="SWI-Prolog is not installed")
def test_real_engine_returns_valid_proof_tree():
    result = default_engine(ROOT).clarify(pair_state())
    assert result["status"] == "selected"
    question = result["question"]
    assert question["statistics"]["distinguished_hypothesis_pair_count"] >= 1
    assert question["proof"]["artgraph_fact_ids"]
    assert question["proof"]["children"][1]["children"]


@pytest.mark.skipif(find_swipl() is None, reason="SWI-Prolog is not installed")
def test_sessions_are_isolated_and_single_hypothesis_stops():
    engine = default_engine(ROOT)
    selected = engine.clarify(pair_state("isolated_pair"))
    single = ClarificationState(
        session_id="isolated_single",
        observations=(
            ClarificationObservation("obs_only", "explicit_interest", "h_musical_subject"),
        ),
        allowed_artwork_ids=tuple(load_catalog()["allowed_candidate_ids"]),
    )
    stopped = engine.clarify(single)
    assert selected["status"] == "selected"
    assert stopped["status"] == "no_discriminative_question"
    assert stopped["active_hypothesis_ids"] == ["h_musical_subject"]


def test_response_correction_replaces_prior_answer():
    state = pair_state()
    question = {
        "question_id": "q_ag_8966_ag_8388",
        "option_a": {"artwork_id": "ag_8966"},
        "option_b": {"artwork_id": "ag_8388"},
    }
    first = state.apply_response(question, "prefer_a", "obs_answer_1")
    corrected = first.apply_response(question, "prefer_b", "obs_answer_2")
    assert len(corrected.asked_questions) == 1
    assert corrected.asked_questions[0].response == "prefer_b"
    assert corrected.asked_questions[0].response_observation_id == "obs_answer_2"


@pytest.mark.skipif(find_swipl() is None, reason="SWI-Prolog is not installed")
def test_unsafe_id_is_rejected_before_prolog_execution():
    state = ClarificationState(
        session_id="unsafe);halt",
        observations=(),
        allowed_artwork_ids=("ag_8966",),
    )
    with pytest.raises(PrologError, match="Unsafe session ID"):
        default_engine(ROOT).clarify(state)


def test_random_and_overlap_baselines_are_independent_and_deterministic():
    state = pair_state()
    random_selector = RandomPairSelector(seed=7)
    assert random_selector.select(state) == random_selector.select(state)
    overlap = AttributeContrastSelector(load_evidence()).select(
        state, ["h_musical_subject", "h_expressionist_style"]
    )
    assert overlap is not None
    assert overlap.method == "raw_attribute_contrast"
    assert overlap.score == 2.0


class FakeTransport:
    def complete_json(self, payload: dict) -> dict:
        eligible = payload["eligible_artwork_ids"]
        return {
            "option_a_id": eligible[0],
            "option_b_id": eligible[1],
            "rationale": "mock transport output, not an evaluation result",
        }


def test_direct_llm_interface_is_mockable_and_allowlist_validated():
    selector = DirectLLMSelector(FakeTransport(), load_evidence())
    result = selector.select(
        pair_state(), ["h_musical_subject", "h_expressionist_style"]
    )
    assert result is not None
    assert result.method == "direct_llm"
    assert result.option_a_id in pair_state().allowed_artwork_ids


class FakeExtractionTransport:
    def complete_json(self, payload: dict) -> dict:
        assert "do not select a question" in payload["task"].lower()
        return {
            "observations": [
                {
                    "id": "obs_extracted_1",
                    "kind": "likes",
                    "object_id": "ag_10472",
                }
            ]
        }


def test_llm_to_prolog_extractor_can_only_propose_allowlisted_state():
    extractor = ValidatedLLMObservationExtractor(FakeExtractionTransport())
    observations = extractor.extract(
        "I liked Study for The Cellist.",
        allowed_artwork_ids=set(pair_state().allowed_artwork_ids),
        allowed_hypothesis_ids={"h_musical_subject"},
    )
    assert observations == (
        {"id": "obs_extracted_1", "kind": "likes", "object_id": "ag_10472"},
    )


def test_real_dataset_artifacts_have_expected_scope():
    report = json.loads(
        (ROOT / "docs" / "clarification_dataset_report.json").read_text(
            encoding="utf-8"
        )
    )
    assert report["selection"]["artwork_count"] == 112
    assert report["selection"]["triple_count"] == 2232
    assert len(report["hypotheses"]) == 10
    assert all(
        len(row["examples"]) >= 2
        for row in report["contrast_analysis"]
        if row["potential_ordered_pair_count"] > 0
    )


def test_controlled_benchmark_contains_twenty_non_gold_scenarios():
    lines = (
        ROOT / "evaluation" / "clarification_scenarios.jsonl"
    ).read_text(encoding="utf-8").splitlines()
    scenarios = [json.loads(line) for line in lines]
    assert len(scenarios) == 20
    assert sum(not row["expected_has_question"] for row in scenarios) == 2
    assert all("gold" not in row for row in scenarios)


def test_executed_evaluation_is_labeled_and_direct_llm_is_not_fabricated():
    results = json.loads(
        (ROOT / "evaluation" / "clarification_results.json").read_text(
            encoding="utf-8"
        )
    )
    assert results["scenario_count"] == 20
    assert results["direct_llm"] == "not_run_missing_configuration_or_flag"
    assert results["summary"]["compositional_prolog"]["valid_question_rate"] == 1.0
    assert results["summary"]["compositional_prolog"]["repeated_question_count"] == 0
    assert "not human preference" in results["simulation_notice"]


def test_phase_1_manifest_hashes_are_reproducible():
    phase = json.loads(
        (ROOT / "docs" / "dataset_manifest.json").read_text(encoding="utf-8")
    )["phase_1_clarification"]
    artifacts = {
        phase["sample"]: phase["sample_sha256"],
        phase["topic_catalog"]: phase["topic_catalog_sha256"],
        phase["baseline_evidence"]: phase["baseline_evidence_sha256"],
        phase["selection_report"]: phase["selection_report_sha256"],
        phase["prolog_facts"]: phase["prolog_facts_sha256"],
        phase["benchmark"]: phase["benchmark_sha256"],
        phase["executed_results"]: phase["executed_results_sha256"],
    }
    for relative_path, expected in artifacts.items():
        assert sha256(ROOT / relative_path) == expected
