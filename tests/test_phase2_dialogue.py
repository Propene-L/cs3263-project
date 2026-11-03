"""Phase 2 tests: mock external Prolog/LLM, test the REAL integrated workflow.

Do not confuse these fake-backed tests with live provider or SWI-Prolog tests.
"""
from __future__ import annotations

import json
from pathlib import Path
from dataclasses import replace
import pytest

from museum_guide.knowledge_layer import Topic, TopicLibrary, KnowledgeState, next_knowledge_action
from museum_guide.dialogue import MuseumDialogue
from museum_guide.turn_extraction import ManualExtractor, ValidatedTurnExtractor, StateDelta, as_payload, validate_delta
from museum_guide.response_renderer import render_action
from museum_guide.direct_dialogue import DirectDialogueSelector

FIXTURE_ROOT = Path(__file__).resolve().parents[1]

EVIDENCE = {
    "hypotheses": [
        {"id":"h_style", "attribute_type":"style", "value_id":"v_style", "label":"bold style"},
        {"id":"h_portrait", "attribute_type":"genre", "value_id":"v_portrait", "label":"portrait"},
    ],
    "artworks": {
        "ag_1": {"label":"Liked portrait", "artist_id":"a_1", "attributes":[
            {"type":"style", "value_id":"v_style", "fact_ids":["agf_1"]},
            {"type":"genre", "value_id":"v_portrait", "fact_ids":["agf_2"]}]},
        "ag_2": {"label":"Portrait alternative", "artist_id":"a_2", "attributes":[
            {"type":"style", "value_id":"v_style", "fact_ids":["agf_3"]},
            {"type":"genre", "value_id":"v_portrait", "fact_ids":["agf_4"]}]},
    }
}
TOPICS = TopicLibrary([
    Topic("c_style", "art style", (), ("h_style",), "A reviewed instructional explanation.", "s_1", "https://example.org/source"),
    Topic("c_portrait", "portrait", ("c_style",), ("h_portrait",), "Portraits show people.", "s_2", "https://example.org/portrait"),
])


def fake_result(state):
    obs = state.observations
    confirmed = any(x.kind == "explicit_interest" for x in obs)
    if confirmed:
        decision = {"action_type": "recommend", "artwork_id": "ag_2", "question": None}
    elif any(x.kind == "likes" for x in obs):
        decision = {"action_type": "clarify", "artwork_id": None,
                    "question": {"kind":"confirm_explanation", "explanation":{"kind":"atomic","components":["h_style"]}}}
    else:
        decision = {"action_type": "insufficient_evidence", "artwork_id": None, "question": None}
    return {"status":"ok", "decision":decision,"preference_explanations":[],"ranked_actions":[]}


class FakeProlog:
    calls = 0
    def infer(self, state):
        self.calls += 1
        return fake_result(state)


class NoProlog:
    def infer(self, state):
        raise AssertionError("Direct-LLM path must not invoke Prolog")


class FakeTurnExtractor:
    def __init__(self, answer): self.answer = answer
    def extract(self, text, **kwargs): return self.answer


def guide(engine=None, extractor=None, direct=None):
    return MuseumDialogue(EVIDENCE, TOPICS, preference_engine=engine or FakeProlog(),
                          extractor=extractor, direct_selector=direct,
                          candidate_artworks=("ag_1", "ag_2"))


def test_knowledge_prerequisite_is_asked_without_inventing_ignorance():
    s = KnowledgeState()
    a = next_knowledge_action(TOPICS, s, "c_portrait")
    assert a["type"] == "ask_knowledge" and a["topic_id"] == "c_style"
    assert s.status("c_style") == "unknown"
    s.asked.add("c_style")
    b = next_knowledge_action(TOPICS, s, "c_portrait")
    assert b["type"] == "explain" and s.status("c_style") == "unknown"
    s.presented.add("c_style")
    c = next_knowledge_action(TOPICS, s, "c_portrait")
    assert c["type"] == "ask_knowledge" and c["topic_id"] == "c_portrait"


def test_cycle_unknown_prerequisite_and_source_validation():
    base = Topic("c_a", "A", ("c_b",), (), "A", "src", "https://example.org")
    with pytest.raises(ValueError, match="Unknown prerequisite"):
        TopicLibrary([base])
    b = Topic("c_b", "B", ("c_a",), (), "B", "src", "https://example.org")
    with pytest.raises(ValueError, match="Cycle"):
        TopicLibrary([base, b])


def test_manual_flow_learns_interest_then_recommends():
    g = guide()
    session = g.new_session()
    session, r1 = g.run_turn(session, "like ag_1")
    assert r1["action"] == "clarify_interest"
    assert r1["state"]["pending"]["type"] == "clarify_interest"
    old = session
    session, r2 = g.run_turn(session, "yes")
    assert r2["action"] == "recommend"
    assert r2["sources"][0]["fact_ids"] == ["agf_3", "agf_4"]
    assert len(old.preferences) == 1 and len(session.preferences) == 2
    assert session.preferences[1]["kind"] == "explicit_interest"


def test_manual_knowledge_flow_tracks_presented_not_known():
    g = guide(); s = g.new_session()
    s,r = g.run_turn(s,"topic c_portrait")
    assert r["action"] == "ask_knowledge"
    s,r = g.run_turn(s,"no")
    assert r["action"] == "explain" and "c_style" in s.knowledge.presented
    assert s.knowledge.status("c_style") == "not_known"
    assert r["sources"] == [{"source_id":"s_1","url":"https://example.org/source","topic_id":"c_style"}]
    s,r = g.run_turn(s,"topic c_portrait")
    assert r["action"] == "ask_knowledge" and r["state"]["pending"]["topic_id"] == "c_portrait"
    s,r = g.run_turn(s,"unsure")
    assert r["action"] == "explain" and s.knowledge.status("c_portrait") == "unknown"


def test_unsupported_extraction_is_rejected_without_mutating_session():
    g = guide(extractor=FakeTurnExtractor(as_payload(StateDelta(events=()))))
    s = g.new_session()
    bad = as_payload(StateDelta()); bad["events"] = [{"kind":"likes","object_id":"ag_999", "components":[],"supersedes":None}]
    g.extractor = FakeTurnExtractor(bad)
    with pytest.raises(ValueError, match="invalid objects"):
        g.run_turn(s, "I liked an unknown artwork", mode="hybrid")
    assert s.turn_index == 0 and not s.preferences


def test_pending_answer_and_skip_never_duplicate_question():
    g=guide();s=g.new_session()
    s,_=g.run_turn(s,"like ag_1")
    s,r=g.run_turn(s,"unsure")
    assert r["action"] == "insufficient_evidence"
    assert s.pending is None
    s,r=g.run_turn(s,"like ag_1")
    assert r["action"] == "insufficient_evidence"
    assert len(s.preferences)==2


def test_correction_keeps_history_and_supersedes_prior_event():
    g=guide();s=g.new_session()
    s,_=g.run_turn(s,"like ag_1")
    oid=s.preferences[0]["id"]
    s,_=g.run_turn(s,f"correct {oid} dislike ag_1")
    assert len(s.preferences)==2 and s.preferences[1]["supersedes"]==oid


def test_direct_mode_does_not_touch_prolog_and_validates_actions():
    class FixedDirect:
        def select(self, sess, evidence, library, candidates, *, latest_utterance=""):
            assert latest_utterance == "I liked the portrait"
            return {"type":"clarify_interest","explanation":{"kind":"atomic","components":["h_portrait"]},
                    "rule_id":"direct_llm_selection", "trace": []}
    event=as_payload(StateDelta(events=(__import__('museum_guide.turn_extraction',fromlist=['ProposedObservation']).ProposedObservation("likes","ag_1"),)))
    g=guide(engine=NoProlog(), extractor=FakeTurnExtractor(event),direct=FixedDirect());s=g.new_session()
    s,r=g.run_turn(s,"I liked the portrait",mode="direct_llm")
    assert r["action"] == "clarify_interest"
    assert r["state"]["pending"]["explanation"]["components"] == ["h_portrait"]


def test_direct_selector_rejects_observed_artwork_and_wrong_question():
    class Transport:
        def __init__(self,value):self.value=value
        def complete_json(self,payload):return self.value
    s = guide().new_session();s.preferences.append({"id":"obs_1", "kind":"likes","object_id":"ag_1","components":[],"supersedes":None})
    good={"action_type":"clarify_interest", "artwork_id":None,"topic_id":None,
          "question_kind":"atomic","question_components":["h_style"],"rationale":"test"}
    selector=DirectDialogueSelector(Transport(good), EVIDENCE, TOPICS)
    r=selector.select(s,EVIDENCE,TOPICS,("ag_1","ag_2"))
    assert r["type"]=="clarify_interest"
    invalid=dict(good, action_type="recommend",artwork_id="ag_1",question_kind=None,question_components=[])
    selector.transport=Transport(invalid)
    with pytest.raises(ValueError,match="Invalid direct recommendation"):
        selector.select(s,EVIDENCE,TOPICS,("ag_1","ag_2"))


def test_hybrid_uses_validated_extraction_not_model_decision():
    proposal=as_payload(StateDelta(events=(__import__('museum_guide.turn_extraction',fromlist=['ProposedObservation']).ProposedObservation("likes","ag_1"),)))
    g=guide(extractor=FakeTurnExtractor(proposal));s=g.new_session()
    s,r=g.run_turn(s,"I liked the portrait",mode="hybrid")
    assert r["action"]=="clarify_interest" and r["audit"]["mode"]=="hybrid"


def test_topic_sources_are_bounded():
    r=render_action({"type":"explain","topic_id":"c_portrait"}, EVIDENCE, TOPICS,{"h_portrait":"portrait"})
    assert r["sources"][0]["url"]=="https://example.org/portrait"


def test_session_reset_is_explicit_not_persistent():
    g=guide();s=g.new_session()
    s,_=g.run_turn(s,"topic c_portrait")
    fresh=g.new_session("visitor_new")
    assert not fresh.knowledge.statuses and fresh.pending is None


def test_manual_respond_without_pending_is_rejected():
    g=guide();s=g.new_session()
    with pytest.raises(ValueError,match="without a pending"):
        g.run_turn(s,"yes")
    assert s.turn_index==0


def test_knowledge_conflict_is_confirmed_not_silently_overwritten():
    s=KnowledgeState()
    s.apply("c_style", "known")
    s.apply("c_style", "not_known")
    assert s.status("c_style") == "conflicted"
    a=next_knowledge_action(TOPICS,s,"c_style")
    assert a["type"]=="confirm_knowledge"
    s.apply("c_style", "not_known",source="visitor_confirmation")
    assert s.status("c_style") == "not_known"


def test_follow_up_topic_after_confirmed_preference():
    g=guide();s=g.new_session()
    s,_=g.run_turn(s,"like ag_1")
    s,r=g.run_turn(s,"yes")
    assert r["action"]=="recommend" and s.pending == {"type":"offer_topic","topic_id":"c_style"}
    assert "Would you like to explore" in r["text"]
    s,r=g.run_turn(s,"yes")
    assert r["action"]=="ask_knowledge" and s.goal_topic=="c_style"
    s,r=g.run_turn(s,"no")
    assert r["action"]=="explain" and "c_style" in s.knowledge.presented


def test_declined_topic_offer_does_not_trigger_repeat_recommendation():
    g=guide();s=g.new_session()
    s,_=g.run_turn(s,"like ag_1")
    s,_=g.run_turn(s,"yes")
    s,r=g.run_turn(s,"no")
    assert r["action"] == "acknowledge_skip" and s.pending is None


def test_explicit_explain_request_works_even_if_known():
    g=guide();s=g.new_session()
    s,_=g.run_turn(s,"know c_style")
    s,r=g.run_turn(s,"explain c_style")
    assert r["action"]=="explain" and s.knowledge.status("c_style")=="known"


def test_new_subject_clears_obsolete_pending_question():
    g=guide();s=g.new_session()
    s,_=g.run_turn(s,"like ag_1")
    s,_=g.run_turn(s,"topic c_portrait")
    assert s.pending["type"]=="ask_knowledge"
    assert s.goal_topic=="c_portrait"
