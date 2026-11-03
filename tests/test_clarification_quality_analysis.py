"""Pure offline tests; no SWI-Prolog, network or API key needed."""
import unittest

from evaluation.analyze_clarification_quality import (
    analyze_cases, question_grounding, summarize_cases, summarize_loop, validate_question, world_partition,
)


def evidence():
    return {
        "hypotheses": [
            {"id": "h_music", "attribute_type": "tag", "value_id": "v_music"},
            {"id": "h_water", "attribute_type": "tag", "value_id": "v_water"},
            {"id": "h_portrait", "attribute_type": "genre", "value_id": "v_portrait"},
        ],
        "artworks": {
            "ag_like": {"label": "Liked", "attributes": [
                {"type": "tag", "value_id": "v_music", "fact_ids": ["f_music"]},
                {"type": "tag", "value_id": "v_water", "fact_ids": ["f_water"]},
            ]},
            "ag_dislike": {"label": "Disliked", "attributes": [
                {"type": "tag", "value_id": "v_water", "fact_ids": ["f_dislike_water"]},
            ]},
        },
    }


def question(*components):
    return {"kind": "confirm_explanation", "explanation": {
        "kind": "atomic" if len(components) == 1 else "all_of",
        "components": list(components),
    }}


def scenario(sid="s1", *, worlds=None, expected="clarify"):
    return {
        "scenario_id": sid,
        "benchmark_kind": "controlled_robustness",
        "subset": "held_out", "category": "contradictory",
        "expected_action_type": expected,
        "observations": [
            {"id": "o1", "kind": "likes", "object_id": "ag_like"},
            {"id": "o2", "kind": "dislikes", "object_id": "ag_dislike"},
        ],
        "hidden_fact_ids": [],
        "worlds": worlds or [{"profile": [{"kind": "atomic", "components": ["h_music"]}], "relevant_artwork_ids": ["ag_like"]}],
    }


def valid_decision(q):
    return {"decision": {"action_type": "clarify", "artwork_id": None, "question": q},
            "metrics": {"decision_validity": True}}


class ClarificationQualityTest(unittest.TestCase):
    def test_grounded_atomic_vs_unrelated_query(self):
        s = scenario()
        good = question_grounding(question("h_music"), s, evidence())
        self.assertTrue(good["grounded_and_unsettled"])
        self.assertEqual(good["support_fact_ids"], ["f_music"])
        self.assertEqual(good["liked_support_observation_ids"], ["o1"])
        unrelated = question_grounding(question("h_portrait"), s, evidence())
        self.assertTrue(unrelated["structurally_valid"])
        self.assertFalse(unrelated["grounded"])

    def test_conjunction_requires_cooccurrence_or_exact_explicit_statement(self):
        s = scenario()
        self.assertTrue(question_grounding(question("h_music", "h_water"), s, evidence())["grounded"])
        self.assertFalse(question_grounding(question("h_music", "h_portrait"), s, evidence())["grounded"])
        s["observations"] += [
            {"id": "o3", "kind": "explicit_interest", "object_id": "h_portrait"},
            {"id": "o4", "kind": "explicit_interest", "object_id": "h_music"},
        ]
        # Two independent atomic interests are NOT a conjunction declaration.
        self.assertFalse(question_grounding(question("h_music", "h_portrait"), s, evidence())["grounded"])

    def test_explicit_preference_settles_exact_atomic_question(self):
        s = scenario()
        s["observations"].append({"id": "o3", "kind": "explicit_interest", "object_id": "h_music"})
        g = question_grounding(question("h_music"), s, evidence())
        self.assertTrue(g["grounded"])
        self.assertFalse(g["unsettled"])

    def test_hidden_fact_cannot_ground_a_question(self):
        s = scenario()
        s["hidden_fact_ids"] = ["f_music"]
        self.assertFalse(question_grounding(question("h_music"), s, evidence())["grounded"])

    def test_invalid_question_components_or_ids(self):
        vocab = {x["id"] for x in evidence()["hypotheses"]}
        self.assertIsNone(validate_question(question("h_music", "h_music"), vocab))
        self.assertIsNone(validate_question(question("h_fabricated"), vocab))
        self.assertIsNone(validate_question({"kind": "other", "explanation": {"kind": "atomic", "components": ["h_music"]}}, vocab))

    def test_negative_only_support_is_contextual_not_positive_grounding(self):
        s = scenario()
        s["observations"] = [{"id": "o2", "kind": "dislikes", "object_id": "ag_dislike"}]
        g = question_grounding(question("h_water"), s, evidence())
        self.assertFalse(g["grounded"])
        self.assertTrue(g["contextually_related"])
        self.assertEqual(g["disliked_support_observation_ids"], ["o2"])

    def test_closed_loop_summary_averages_worlds_before_scenarios(self):
        cases = [scenario("a"), scenario("b")]
        cases[0]["worlds"] = [{"profile": []}, {"profile": []}]
        loop = [
            {"scenario_id": "a", "method": "compositional_prolog", "primary_accuracy_delta": 1,
             "explanation_precision_delta": 1, "explanation_recall_delta": 1,
             "top1_relevance_delta": 1, "top1_relevance_after": 1,
             "selected_recommendation_relevant_after": True},
            {"scenario_id": "a", "method": "compositional_prolog", "primary_accuracy_delta": 0,
             "explanation_precision_delta": 0, "explanation_recall_delta": 0,
             "top1_relevance_delta": 0, "top1_relevance_after": 0,
             "selected_recommendation_relevant_after": None},
            {"scenario_id": "a", "method": "direct_llm_state_reasoning", "primary_accuracy_delta": 0,
             "explanation_precision_delta": 0, "explanation_recall_delta": 0,
             "top1_relevance_delta": 0, "top1_relevance_after": 0,
             "selected_recommendation_relevant_after": False},
        ]
        report = summarize_loop(cases, loop)
        self.assertEqual(report["compositional_prolog"]["mean_delta_among_asked_scenarios"]["primary_accuracy_delta"], 0.5)
        self.assertEqual(report["compositional_prolog"]["mean_delta_among_all_expected_clarify_scenarios_missed_as_zero"]["primary_accuracy_delta"], 0.25)
        self.assertEqual(report["matched_both_asked"]["scenario_count"], 1)

    def test_world_split_only_multiworld(self):
        s = scenario(worlds=[
            {"profile": [{"kind": "atomic", "components": ["h_music"]}]},
            {"profile": [{"kind": "atomic", "components": ["h_water"]}]},
        ])
        g = world_partition(question("h_music"), s, {"h_music", "h_water"})
        self.assertTrue(g["world_split"])
        self.assertEqual(g["world_information_gain_bits"], 1.0)
        one_world = scenario()
        self.assertIsNone(world_partition(question("h_music"), one_world, {"h_music"})["world_information_gain_bits"])

    def test_invalid_output_is_false_negative_not_true_negative(self):
        s1 = scenario("s1", expected="clarify")
        s2 = scenario("s2", expected="recommend")
        data = {
            "s1": {"methods": {"compositional_prolog": valid_decision(question("h_music")),
                               "direct_llm_state_reasoning": {"error": "Invalid JSON"}}},
            "s2": {"methods": {"compositional_prolog": {"decision": {"action_type": "recommend", "artwork_id": "ag_like", "question": None}},
                               "direct_llm_state_reasoning": {"error": "Timeout"}}},
        }
        rows = analyze_cases([s1, s2], evidence(), data)
        by_method = summarize_cases(rows)
        p = by_method["compositional_prolog"]
        self.assertEqual((p["tp"], p["tn_valid"]), (1, 1))
        self.assertEqual(p["clarification_precision"], 1.0)
        self.assertEqual(p["clarification_recall_including_invalid_as_missed"], 1.0)
        llm = by_method["direct_llm_state_reasoning"]
        self.assertEqual((llm["tp"], llm["fn_invalid"], llm["tn_valid"]), (0, 1, 0))
        self.assertEqual(llm["invalid_outputs"], 2)
        self.assertEqual(llm["clarification_recall_including_invalid_as_missed"], 0.0)

    def test_non_grounded_clarification_is_recorded_as_failure(self):
        s = scenario()
        data = {"s1": {"methods": {
            "compositional_prolog": valid_decision(question("h_music")),
            "direct_llm_state_reasoning": valid_decision(question("h_portrait")),
        }}}
        rows = analyze_cases([s], evidence(), data)
        a = summarize_cases(rows)
        self.assertEqual(a["compositional_prolog"]["question_grounding_rate_given_asked"], 1.0)
        self.assertEqual(a["direct_llm_state_reasoning"]["question_grounding_rate_given_asked"], 0.0)
        self.assertEqual(a["direct_llm_state_reasoning"]["clarification_precision"], 1.0)


if __name__ == "__main__":
    unittest.main()
