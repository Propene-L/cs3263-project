from __future__ import annotations
import hashlib
import csv
import json
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import pytest

from museum_guide.preference_state import PreferenceObservation as O, PreferenceState, default_preference_state_engine, validate_state
from museum_guide.preference_state_comparator import InteractionPythonBaseline, explanation_key
from museum_guide.preference_state_llm import CorrectedDirectPreferenceStateLLM
from museum_guide.prolog_bridge import PrologError
from evaluation.evaluate_preference_state_corrected import (
    state_metrics,ranking_metrics,make_state,signature,apply_response,controlled_response,
)
from scripts.build_preference_state_robustness import build, audit, order_candidates

ROOT=Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def evidence(): return json.loads((ROOT/"data/curated/clarification_evidence.json").read_text(encoding="utf-8"))
@pytest.fixture(scope="module")
def cases(): return build()[0]
@pytest.fixture(scope="module")
def engine(): return default_preference_state_engine(ROOT)


def flagship():
    return PreferenceState("flagship_corrected",(O("l","likes","ag_8416"),O("d1","dislikes","ag_13231"),O("d2","dislikes","ag_8296")),("ag_8415","ag_20804","ag_14531","ag_8145"))


def test_randomized_target_positions_and_builder_reproducibility():
    robust,original=build();r2,o2=build()
    assert robust==r2 and original==o2
    positions={s["candidate_artwork_ids"].index(s["construction"]["target_artwork_id"]) for s in original}
    assert positions=={0,1,2,3,4}
    assert all(s["candidate_order_seed"] for s in original+robust)
    report=audit(robust,original)
    assert report["scenario_count"]==32
    assert set(report["categories"].values())=={4}
    assert report["identical_history_overlap"]==0 and not report["group_overlap"]
    assert report["world_count"]==36


def test_coverage_does_not_hide_spurious_explanations_or_primary_error():
    gold=[{"kind":"atomic","components":["h_musical_subject"]}]
    wrong={"kind":"all_of","components":["h_portrait_genre","h_oil_medium"],"status":"interaction_candidate"}
    correct={**gold[0],"status":"candidate"}
    r={"preference_explanations":[wrong,correct],"primary_explanation":wrong}
    m=state_metrics(r,gold)
    assert m["explanation_coverage"] and not m["primary_explanation_accuracy"]
    assert m["explanation_precision"]==0.5 and m["explanation_recall"]==1
    assert m["false_interaction_rate"] and m["false_interaction_prioritized"]


def test_mixed_and_rejected_are_not_asserted_and_atomic_is_not_conjunction():
    pair={"kind":"all_of","components":["h_expressionist_style","h_portrait_genre"]}
    r={"preference_explanations":[{"kind":"atomic","components":[h],"status":"candidate"} for h in pair["components"]],"primary_explanation":None}
    m=state_metrics(r,[pair]);assert m["explanation_precision"]==0 and m["explanation_recall"]==0
    r["preference_explanations"]=[{**pair,"status":"mixed"}]
    assert state_metrics(r,[pair])["explanation_coverage"]
    assert state_metrics(r,[pair])["asserted_explanation_count"]==0


def test_ranking_recall_is_not_hit_at_k():
    actions=[{"artwork_id":a} for a in ["a","b","c"]]
    m=ranking_metrics(actions,["a","d","e","f"])
    assert m["recall_at_k"]==0.25 and m["precision_at_k"]==pytest.approx(1/3) and m["hit_at_k"]


def test_flagship_is_provisional_with_exact_provenance_and_abstention(engine):
    r=engine.infer(flagship());e=next(e for e in r["preference_explanations"] if e["kind"]=="all_of")
    assert e["status"]=="interaction_candidate"
    assert r["primary_explanation"] is None and r["decision"]["action_type"]=="clarify"
    assert set(e["proof"]["observation_ids"])=={"l","d1","d2"}
    assert set(e["proof"]["artgraph_fact_ids"])=={"agf_8a4cce07ba2a1ca7c617","agf_622844512b2c37462fa9","agf_bc28f5fe332dea18b2b7","agf_b9a2ae950dd18cec4bac"}
    assert "a_component_rejection_can_suggest_interaction" in e["proof"]["assumption_ids"]
    assert len(e["proof"]["not_recorded_components"])==2


def test_explicit_rejection_blocks_pair_and_preserves_independent_interest(engine):
    s=flagship();s=replace(s,observations=(*s.observations,O("r","explicit_rejection","h_expressionist_style"),O("i","explicit_interest","h_musical_subject")))
    r=engine.infer(s)
    assert not any(e["kind"]=="all_of" for e in r["preference_explanations"])
    assert r["decision"]["action_type"]=="recommend" and r["decision"]["artwork_id"]=="ag_14531"


def test_explicit_independent_interests_are_not_forced_into_pair(engine):
    s=flagship();s=replace(s,observations=(*s.observations,O("x","explicit_interest","h_expressionist_style"),O("y","explicit_interest","h_portrait_genre")))
    r=engine.infer(s)
    assert not any(e["status"]=="interaction_candidate" for e in r["preference_explanations"])
    assert sum(e["status"]=="explicitly_confirmed" for e in r["preference_explanations"])==2


def test_confirmation_survives_contradictory_artwork_and_raw_correction(engine):
    s=PreferenceState("correction_test",(O("o1","explicit_rejection","h_musical_subject"),
        O("o2","explicit_interest","h_musical_subject",supersedes="o1"),O("o3","dislikes","ag_10472")),("ag_14531","ag_8415"))
    r=engine.infer(s)
    assert r["primary_explanation"]["status"]=="explicitly_confirmed"
    assert r["decision"]["artwork_id"]=="ag_14531"
    assert r["superseded_observation_ids"]==["o1"] and "o1" not in r["active_observation_ids"]
    assert len(s.observations)==3
    assert r["primary_explanation"]["proof"]["negative_artwork_count"]==1


def test_declared_incompleteness_suppresses_contrast_and_preserves_mask(engine):
    s=replace(flagship(),hidden_fact_ids=("agf_622844512b2c37462fa9",),evidence_incomplete=True)
    r=engine.infer(s)
    assert not any(e["kind"]=="all_of" for e in r["preference_explanations"])
    assert r["decision"]["action_type"]=="insufficient_evidence"
    assert all("agf_622844512b2c37462fa9" not in e["artgraph_fact_ids"] for e in r["observation_evidence"])


def test_actual_yes_no_unsure_state_transitions(engine):
    s=flagship();before=engine.infer(s);q=before["decision"]["question"]
    yes=apply_response(s,q,"yes");after=engine.infer(yes)
    assert after["decision"]["action_type"]=="recommend" and after["decision"]["artwork_id"]=="ag_20804"
    assert yes.observations[:-1]==s.observations
    no=engine.infer(apply_response(s,q,"no"))
    assert not any(e["kind"]=="all_of" and e["status"]=="interaction_candidate" for e in no["preference_explanations"])
    assert apply_response(s,q,"unsure")==s


def test_denial_of_independent_interest_does_not_ban_conditional_interest(engine):
    s=flagship();q={"explanation":{"kind":"atomic","components":["h_expressionist_style"]}}
    r=engine.infer(apply_response(s,q,"no"))
    assert any(e["kind"]=="all_of" and e["status"]=="interaction_candidate" for e in r["preference_explanations"])
    assert "ag_20804" in [a["artwork_id"] for a in r["ranked_actions"]]


@pytest.mark.parametrize("name",["atomic_music","independent_style_portrait","conjunction_style_portrait","noisy_music","contradictory_music","missing_portrait_hidden","ambiguous_albert","correction_music"])
def test_python_prolog_equivalence_on_development_categories(name,cases,evidence,engine):
    s=make_state(next(s for s in cases if s["scenario_id"]==name))
    a=engine.infer(s);b=InteractionPythonBaseline(evidence).infer(s)
    assert signature(a)==signature(b)


def test_candidate_order_invariance(engine,evidence):
    s=flagship();a=engine.infer(s);b=InteractionPythonBaseline(evidence).infer(s)
    order,_=order_candidates(s.allowed_action_artwork_ids,"permutation",2)
    perm=replace(s,allowed_action_artwork_ids=tuple(order))
    assert signature(a)==signature(engine.infer(perm))
    assert signature(b)==signature(InteractionPythonBaseline(evidence).infer(perm))


def test_empty_history_abstains(engine):
    r=engine.infer(PreferenceState("empty",(),("ag_14531",)))
    assert r["decision"]["action_type"]=="insufficient_evidence"
    assert r["primary_explanation"] is None


@pytest.mark.parametrize("bad",[
    O("o","likes","ag_nonexistent"), O("o","likes);halt","ag_8416"),
    O("o","explicit_interest","h_invalid"), O("o","likes","ag_8416",supersedes="future"),
    O("o","explicit_conjunction","preference_pair",("h_oil_medium","h_oil_medium")),
])
def test_state_allowlist_and_corrections_rejected(bad,evidence):
    with pytest.raises(PrologError):validate_state(PreferenceState("bad",(bad,),("ag_20804",)),evidence)


class Fake:
    def __init__(self,result):self.result=result;self.payload=None
    def complete_json(self,payload):self.payload=payload;return deepcopy(self.result)


def valid_llm_response():
    e={"kind":"all_of","components":["h_expressionist_style","h_portrait_genre"]}
    return {"inferred_preferences":[{**e,"status":"interaction_candidate"}],"primary_explanation":None,
        "next_action_type":"clarify","artwork_id":None,"question_explanation":e,"rationale":"Engineering mock only."}


def test_direct_payload_leakage_mask_order_and_mocked_loop(evidence):
    transport=Fake(valid_llm_response());model=CorrectedDirectPreferenceStateLLM(transport,evidence)
    s=replace(flagship(),hidden_fact_ids=("agf_622844512b2c37462fa9",),evidence_incomplete=True)
    r=model.infer(s,natural_language_history="I liked Albert Kollmann.")
    payload=json.dumps(transport.payload)
    for forbidden in ["latent_profile","target_artwork_id","distractor","expected_action","construction","prolog","agf_622844512b2c37462fa9"]:
        assert forbidden not in payload.lower()
    assert [a["artwork_id"] for a in transport.payload["candidate_artworks"]]==list(s.allowed_action_artwork_ids)
    assert transport.payload["required_output_schema"]==model.OUTPUT_SCHEMA
    assert "property names verbatim" in transport.payload["output_instruction"]
    assert r["decision"]["action_type"]=="clarify" and model.last_record["status"]=="validated"


@pytest.mark.parametrize("change",[
    {"inferred_preferences":[{"kind":"atomic","components":["h_oil_medium","h_portrait_genre"],"status":"candidate"}]},
    {"inferred_preferences":[{"kind":"all_of","components":["h_oil_medium","h_oil_medium"],"status":"interaction_candidate"}]},
    {"inferred_preferences":[{"kind":"atomic","components":["h_fabricated"],"status":"candidate"}]},
    {"next_action_type":"execute_prolog"},
    {"next_action_type":"recommend","artwork_id":"ag_fabricated","question_explanation":None},
    {"question_explanation":{"kind":"all_of","components":["h_oil_medium"]}},
    {"primary_explanation":{"kind":"atomic","components":["h_oil_medium"]}},
])
def test_invalid_llm_outputs_are_rejected_and_recorded(change,evidence):
    model=CorrectedDirectPreferenceStateLLM(Fake({**valid_llm_response(),**change}),evidence)
    with pytest.raises(ValueError):model.infer(flagship(),natural_language_history="Visitor history")
    assert model.last_record["status"]=="error" and "raw_response" in model.last_record


def test_ambiguous_worlds_are_one_case_with_different_answers(cases):
    s=next(s for s in cases if s["scenario_id"]=="ambiguous_albert")
    q={"explanation":{"kind":"all_of","components":["h_expressionist_style","h_portrait_genre"]}}
    assert [controlled_response(q,w["profile"]) for w in s["worlds"]]==["yes","no"]


def test_preserved_artifact_hashes():
    manifest=json.loads((ROOT/"docs/preference_state_historical_manifest.json").read_text(encoding="utf-8"))
    for file,expected in manifest["sha256"].items():
        # Git text blobs use LF; Windows checkouts may use CRLF.
        content=(ROOT/file).read_bytes().replace(b"\r\n",b"\n")
        assert hashlib.sha256(content).hexdigest()==expected,file


def test_corrected_human_review_is_blind_randomized_and_unscored():
    with (ROOT/"evaluation/preference_state_corrected_human_review.csv").open(encoding="utf-8",newline="") as handle:
        rows=list(csv.DictReader(handle))
    assert len(rows)==16 and len({r["presentation_seed"] for r in rows})==16
    serialized=json.dumps(rows).lower()
    assert "compositional_prolog" not in serialized and "signed_additive" not in serialized
    assert all(not r["more_relevant_a_b_equal_neither"] and not r["reviewer_notes"] for r in rows)
    manifest=json.loads((ROOT/"docs/preference_state_human_review_manifest.json").read_text(encoding="utf-8"))
    assert manifest["contains_method_disagreements"] and manifest["contains_both_may_be_wrong_cases"]
