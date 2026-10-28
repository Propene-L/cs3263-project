from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from museum_guide.preference_state import (
    PreferenceObservation,
    PreferenceState,
    default_preference_state_engine,
)
from museum_guide.preference_state_baselines import (
    DirectPreferenceStateLLM,
    PositiveAccumulationBaseline,
    SignedAdditiveAtomicBaseline,
)
from museum_guide.prolog_bridge import PrologError, find_swipl

ROOT = Path(__file__).resolve().parents[1]


def evidence() -> dict:
    return json.loads(
        (ROOT / "data" / "curated" / "clarification_evidence.json").read_text(
            encoding="utf-8"
        )
    )


def flagship_state(mode: str = "compositional") -> PreferenceState:
    return PreferenceState(
        session_id=f"flagship_{mode}",
        observations=(
            PreferenceObservation("obs_like_albert", "likes", "ag_8416"),
            PreferenceObservation("obs_dislike_bird", "dislikes", "ag_13231"),
            PreferenceObservation("obs_dislike_boy", "dislikes", "ag_8296"),
        ),
        allowed_action_artwork_ids=("ag_20804", "ag_8415"),
        mode=mode,
    )


def test_flagship_naive_baselines_prefer_required_distractor():
    positive = PositiveAccumulationBaseline(evidence()).infer(flagship_state())
    signed = SignedAdditiveAtomicBaseline(evidence()).infer(flagship_state())
    assert [(item["artwork_id"], item["score"]) for item in positive.ranked_actions] == [
        ("ag_8415", 3),
        ("ag_20804", 2),
    ]
    assert [(item["artwork_id"], item["score"]) for item in signed.ranked_actions] == [
        ("ag_8415", 2),
        ("ag_20804", 0),
    ]


@pytest.mark.skipif(find_swipl() is None, reason="SWI-Prolog is not installed")
def test_flagship_compositional_proof_and_ranking_are_exact():
    state = flagship_state()
    original_observations = state.observations
    result = default_preference_state_engine(ROOT).infer(state)
    interaction = next(
        item
        for item in result["preference_explanations"]
        if item["kind"] == "all_of"
    )
    assert interaction["components"] == [
        "h_expressionist_style",
        "h_portrait_genre",
    ]
    assert interaction["status"] == "interaction_candidate"
    assert interaction["proof"]["rule_id"] == "r_component_rejection_suggests_interaction"
    assert set(interaction["proof"]["observation_ids"]) == {
        "obs_like_albert",
        "obs_dislike_bird",
        "obs_dislike_boy",
    }
    assert {
        "agf_8a4cce07ba2a1ca7c617",
        "agf_622844512b2c37462fa9",
        "agf_bc28f5fe332dea18b2b7",
        "agf_b9a2ae950dd18cec4bac",
    } <= set(interaction["proof"]["artgraph_fact_ids"])
    assert result["ranked_actions"][0]["artwork_id"] == "ag_20804"
    assert result["ranked_actions"][0]["score"] == 1000
    assert result["ranked_actions"][1]["artwork_id"] == "ag_8415"
    assert state.observations == original_observations


@pytest.mark.skipif(find_swipl() is None, reason="SWI-Prolog is not installed")
def test_flagship_observation_evidence_preserves_all_declared_fact_provenance():
    result = default_preference_state_engine(ROOT).infer(flagship_state())
    fact_ids = {
        fact
        for item in result["observation_evidence"]
        for fact in item["artgraph_fact_ids"]
    }
    assert {
        "agf_8a4cce07ba2a1ca7c617",
        "agf_622844512b2c37462fa9",
        "agf_e3001683bd7d0266a162",
        "agf_7888e12232ccab014115",
        "agf_c642b6942e0c256567ca",
        "agf_bc28f5fe332dea18b2b7",
        "agf_b9a2ae950dd18cec4bac",
    } <= fact_ids
    assert {
        "agf_7f54f5f65b1cedf3fe4f",
        "agf_373d77fbb313b7f40e0d",
    } <= set(result["ranked_actions"][0]["proof"]["artgraph_fact_ids"])


def test_preference_state_rejects_unsafe_ids_before_prolog():
    state = PreferenceState(
        session_id="unsafe);halt",
        observations=(),
        allowed_action_artwork_ids=("ag_20804",),
    )
    with pytest.raises(PrologError, match="Unsafe session ID"):
        default_preference_state_engine(ROOT).infer(state)


class FakeStateTransport:
    def complete_json(self, payload: dict) -> dict:
        serialized = json.dumps(payload)
        assert "latent_profile" not in serialized
        assert "expected" not in serialized
        assert "prolog" not in serialized.lower()
        assert payload["visitor_history"]
        return {
            "inferred_preferences": [
                {
                    "kind": "all_of",
                    "components": [
                        "h_expressionist_style",
                        "h_portrait_genre",
                    ],
                }
            ],
            "next_action_type": "recommend",
            "artwork_id": "ag_20804",
            "rationale": "mock engineering output, not an experiment",
        }


def test_task_specific_direct_llm_interface_is_mockable_and_anti_leakage():
    direct = DirectPreferenceStateLLM(FakeStateTransport(), evidence())
    result = direct.infer(
        flagship_state(),
        natural_language_history="I liked Albert Kollmann but disliked two component examples.",
    )
    assert result.preference_explanations[0]["kind"] == "all_of"
    assert result.ranked_actions[0]["artwork_id"] == "ag_20804"
    assert direct.last_record["validated_result"]["next_action_type"] == "recommend"


def test_benchmark_has_two_real_artgraph_families_and_fixed_splits():
    scenarios = [
        json.loads(line)
        for line in (
            ROOT / "evaluation" / "preference_state_scenarios.jsonl"
        ).read_text(encoding="utf-8").splitlines()
    ]
    assert len(scenarios) == 24
    assert sum(item["family"] == "contrastive_atomic" for item in scenarios) == 12
    assert sum(item["family"] == "compositional_interaction" for item in scenarios) == 12
    assert {item["subset"] for item in scenarios} == {"development", "held_out"}
    assert scenarios[0]["scenario_id"] == "flagship_interaction_albert_kollmann"
    assert scenarios[1]["scenario_id"] == "flagship_contrastive_cellist"
    assert all("controlled" in item["benchmark_label_notice"].lower() for item in scenarios)


def test_executed_preference_state_results_are_labeled_and_not_mock_llm():
    results = json.loads(
        (ROOT / "evaluation" / "preference_state_results.json").read_text(
            encoding="utf-8"
        )
    )
    assert results["scenario_count"] == 24
    assert results["direct_llm"] == "not_executed_missing_configuration_or_flag"
    assert "not human preference" in results["controlled_label_notice"]
    assert results["summary"]["compositional_prolog"][
        "interaction_explanation_accuracy"
    ] == 1.0


def test_blind_review_items_include_factual_attributes_without_method_names():
    with (ROOT / "evaluation" / "preference_state_human_review.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 12
    assert all(row["action_a_recorded_attributes"] for row in rows)
    assert all(row["action_b_recorded_attributes"] for row in rows)
    assert all("agf_" in row["recorded_observation_evidence"] for row in rows)
    assert "method" not in " ".join(rows[0]).lower()
