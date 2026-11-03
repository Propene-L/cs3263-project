"""Run with python -m unittest discover -s tests -p test_audit_diagnostic_questions.py -v"""
import math
import unittest
from evaluation.audit_diagnostic_questions import (
    active_observations, eligible_explanations, plausible_explanations,
    score_question, summary, binary_entropy, visible_support, explanation_key,
    PROLOG, LLM,
)

EVIDENCE = {
    "hypotheses": [
        {"id": "h_water", "attribute_type": "tag", "value_id": "t1"},
        {"id": "h_oil", "attribute_type": "medium", "value_id": "m1"},
        {"id": "h_music", "attribute_type": "tag", "value_id": "t2"},
        {"id": "h_portrait", "attribute_type": "genre", "value_id": "g1"},
        {"id": "h_style", "attribute_type": "style", "value_id": "s1"},
    ],
    "artworks": {
        "w1": {"attributes": [{"type": "tag", "value_id": "t1", "fact_ids": ["f1"]}]},
        "w2": {"attributes": [{"type": "tag", "value_id": "t1", "fact_ids": ["f2"]}]},
        "w3": {"attributes": [
            {"type": "tag", "value_id": "t1", "fact_ids": ["f3"]},
            {"type": "medium", "value_id": "m1", "fact_ids": ["f4"]},
        ]},
        "w4": {"attributes": [{"type": "tag", "value_id": "t2", "fact_ids": ["f5"]}]},
        "wp": {"attributes": [
            {"type": "tag", "value_id": "t2", "fact_ids": ["f6"]},
            {"type": "genre", "value_id": "g1", "fact_ids": ["f7"]},
        ]},
    },
}


def obs(i, kind, target, **kwargs):
    return {"id": i, "kind": kind, "object_id": target, **kwargs}


def scenario(likes, other=(), **kwargs):
    return {"observations": [obs(f"l{i}", "likes", x) for i, x in enumerate(likes)] + list(other), **kwargs}


def question(kind, components):
    return {"asked_clarification": "True", "question_kind": kind,
            "question_components": __import__("json").dumps(components)}


class DiagnosticAuditTests(unittest.TestCase):
    def test_noisy_water_excludes_incidental_oil(self):
        s = scenario(["w1", "w2", "w3"])
        p = plausible_explanations(EVIDENCE, s, "competitive")
        self.assertEqual(p["min_required_support"], 2)
        self.assertIn("atomic:h_water", p["keys"])
        self.assertNotIn("atomic:h_oil", p["keys"])
        self.assertFalse(score_question(question("atomic", ["h_oil"]), p)["diagnostic_candidate"])
        self.assertTrue(score_question(question("atomic", ["h_water"]), p)["diagnostic_candidate"])

    def test_strict_permissive_sensitivity(self):
        s = scenario(["w1", "w2", "w3"])
        self.assertNotIn("atomic:h_oil", plausible_explanations(EVIDENCE, s, "strict")["keys"])
        self.assertIn("atomic:h_oil", plausible_explanations(EVIDENCE, s, "permissive")["keys"])

    def test_independent_likes_need_not_share_a_feature(self):
        s = scenario(["w1", "w4"])
        p = plausible_explanations(EVIDENCE, s, "competitive")
        self.assertEqual(p["max_liked_support"], 1)
        self.assertIn("atomic:h_water", p["keys"])
        self.assertIn("atomic:h_music", p["keys"])

    def test_explicit_independent_interests_do_not_justify_a_pair(self):
        s = scenario(["wp"], [obs("c1", "explicit_interest", "h_music"), obs("c2", "explicit_interest", "h_portrait")])
        p = plausible_explanations(EVIDENCE, s, "competitive")
        self.assertNotIn("all_of:h_music+h_portrait", p["keys"])
        self.assertNotIn("atomic:h_music", p["keys"])

    def test_explanation_rejection_and_superseding(self):
        s = scenario(["w1"], [obs("o1", "explicit_interest", "h_water"),
                              obs("o2", "reject_atomic_explanation", "h_water", supersedes="o1")])
        active = active_observations(s)
        self.assertNotIn("o1", [o["id"] for o in active])
        p = plausible_explanations(EVIDENCE, s, "competitive")
        self.assertNotIn("atomic:h_water", p["keys"])

    def test_masked_fact_removes_oil_support(self):
        s = scenario(["w3"], hidden_fact_ids=["f4"])
        self.assertNotIn("h_oil", visible_support(EVIDENCE, s)["w3"])
        self.assertNotIn("atomic:h_oil", plausible_explanations(EVIDENCE, s, "permissive")["keys"])

    def test_candidate_pair_only_allowlisted_attribute_types(self):
        keys = {explanation_key(kind, cs) for kind, cs in eligible_explanations(EVIDENCE)}
        self.assertIn("all_of:h_music+h_portrait", keys)
        self.assertNotIn("all_of:h_oil+h_water", keys)
        self.assertNotIn("all_of:h_music+h_water", keys)

    def test_other_option_produces_binary_proxy(self):
        p = plausible_explanations(EVIDENCE, scenario(["w1"]), "competitive")
        score = score_question(question("atomic", ["h_water"]), p)
        self.assertTrue(score["diagnostic_candidate"])
        self.assertAlmostEqual(score["structural_proxy_bits"], 1.0)
        self.assertEqual(binary_entropy(0), 0)
        self.assertAlmostEqual(binary_entropy(0.5), 1)

    def test_invalid_question_does_not_count(self):
        p = plausible_explanations(EVIDENCE, scenario(["w1"]), "competitive")
        for q in [question("all_of", ["h_water"]), question("atomic", ["h_oil", "h_water"]),
                  {"asked_clarification": "False"}]:
            self.assertFalse(score_question(q, p)["diagnostic_candidate"])

    def test_summary_counts_missed_questions_as_zero(self):
        rows = []
        for sid in ["a", "b"]:
            for method in [PROLOG, LLM]:
                asked = sid == "a" or method == PROLOG
                diagnostic = asked and method == PROLOG
                rows.append({"scenario_id":sid,"method":method,"expected_action":"clarify",
                             "asked_clarification":asked,"diagnostic_candidate":diagnostic,
                             "structural_proxy_bits":1.0 if diagnostic else 0.0})
        out = summary(rows)
        self.assertEqual(out[PROLOG]["effective_diagnostic_recall_over_needed"], 1)
        self.assertEqual(out[LLM]["effective_diagnostic_recall_over_needed"], 0)


if __name__ == "__main__":
    unittest.main()
