from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from museum_guide.dialogue import MuseumDialogue
from museum_guide.knowledge_layer import (
    KnowledgeState,
    Topic,
    TopicLibrary,
    default_knowledge_engine,
)
from museum_guide.prolog_bridge import PrologError
from museum_guide.turn_extraction import (
    ProposedObservation,
    TurnDelta,
    ValidatedTurnExtractor,
    as_payload,
    validate_delta,
)


ROOT = Path(__file__).resolve().parents[1]


def test_real_prolog_guidance_returns_recursive_proof() -> None:
    library = TopicLibrary.load(ROOT / "data" / "curated" / "education_topics.json")
    engine = default_knowledge_engine(ROOT)
    result = engine.infer(library, KnowledgeState(), "c_expressionist_portrait")
    decision = result["decision"]
    assert decision["action_type"] == "ask_knowledge"
    assert decision["topic_id"] == "c_art_style"
    assert decision["proof"]["path"] == [
        "c_expressionist_portrait", "c_expressionism", "c_art_style"
    ]


def test_real_prolog_guidance_changes_after_explicit_state() -> None:
    library = TopicLibrary.load(ROOT / "data" / "curated" / "education_topics.json")
    engine = default_knowledge_engine(ROOT)
    state = KnowledgeState(statuses={"c_art_style": "not_known"}, asked={"c_art_style"})
    result = engine.infer(library, state, "c_expressionist_portrait")
    assert result["decision"]["action_type"] == "explain"
    assert result["decision"]["rule_id"] == "r_explain_stated_not_known"


def test_dialogue_real_prolog_topic_flow_preserves_source_classification() -> None:
    guide = MuseumDialogue.from_repository(ROOT)
    session = guide.new_session("visitor_phase2_topic")
    session, first = guide.run_turn(session, "topic c_expressionist_portrait")
    assert first["action"] == "ask_knowledge"
    assert first["audit"]["trace"]["decision"]["proof"]["path"][-1] == "c_art_style"
    session, second = guide.run_turn(session, "no")
    assert second["action"] == "explain"
    assert session.knowledge.status("c_art_style") == "not_known"
    assert second["sources"][0]["provenance"] == "educational_guidance"


def test_dialogue_real_preference_engine_returns_artgraph_provenance() -> None:
    guide = MuseumDialogue.from_repository(ROOT)
    session = guide.new_session("visitor_phase2_preference")
    outputs = []
    for turn in ["like ag_8416", "dislike ag_13231", "dislike ag_8296", "yes"]:
        session, output = guide.run_turn(session, turn)
        outputs.append(output)
    assert outputs[-1]["action"] == "recommend"
    assert outputs[-1]["sources"][0]["provenance"] == "imported_artgraph_facts"
    assert outputs[-1]["sources"][0]["fact_ids"]
    assert outputs[-1]["audit"]["rule_id"] == "prolog_preference_recommendation"


def test_invalid_hybrid_delta_is_atomic() -> None:
    class BadExtractor:
        def extract(self, text: str, **kwargs):
            return {
                **as_payload(TurnDelta()),
                "events": [{
                    "kind": "likes", "object_id": "ag_fabricated",
                    "components": [], "supersedes": None,
                }],
            }

    guide = MuseumDialogue.from_repository(ROOT)
    guide.extractor = BadExtractor()
    session = guide.new_session("visitor_phase2_atomic")
    before = copy.deepcopy(session.snapshot())
    with pytest.raises(ValueError, match="invalid objects"):
        guide.run_turn(session, "I liked a made-up artwork", mode="hybrid")
    assert session.snapshot() == before


def test_answer_without_pending_is_rejected_atomically() -> None:
    guide = MuseumDialogue.from_repository(ROOT)
    session = guide.new_session("visitor_phase2_answer")
    with pytest.raises(ValueError, match="without a pending"):
        guide.run_turn(session, "yes")
    assert session.turn_index == 0


def test_explicit_explanation_does_not_invent_knowledge() -> None:
    guide = MuseumDialogue.from_repository(ROOT)
    session = guide.new_session("visitor_phase2_explain")
    session.knowledge.apply("c_portrait", "known")
    session, output = guide.run_turn(session, "explain c_portrait")
    assert output["action"] == "explain"
    assert session.knowledge.status("c_portrait") == "known"
    assert output["audit"]["rule_id"] == "r_explicit_explanation_request"


def test_unsafe_catalog_id_is_rejected_before_prolog() -> None:
    topic = Topic(
        "Bad ID", "bad", (), (), "text", "source", "https://example.org/source"
    )
    with pytest.raises(PrologError, match="Unsafe topic ID"):
        TopicLibrary([topic])


def test_delta_rejects_provider_action_injection() -> None:
    payload = as_payload(TurnDelta())
    payload["recommended_artwork_id"] = "ag_8416"
    with pytest.raises(ValueError, match="fields"):
        validate_delta(
            payload,
            artworks={"ag_8416"},
            hypotheses={"h_expressionist_style"},
            topics={"c_expressionism"},
            previous_ids=set(),
            pending=None,
        )


def test_validated_extractor_records_transport_metadata_but_not_private_fields() -> None:
    class Transport:
        def complete_json(self, payload):
            return {
                **as_payload(TurnDelta(events=(
                    ProposedObservation("likes", "ag_8416"),
                ))),
                "_transport_metadata": {"model": "mock-only"},
            }

    extractor = ValidatedTurnExtractor(Transport())
    result = extractor.extract(
        "liked portrait",
        pending=None,
        artworks={"ag_8416"},
        hypotheses={"h_expressionist_style"},
        topics={"c_expressionism"},
        previous_ids=set(),
    )
    assert "_transport_metadata" not in result
    assert extractor.last_record["metadata"] == {"model": "mock-only"}
