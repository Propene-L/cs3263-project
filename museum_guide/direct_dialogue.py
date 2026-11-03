"""Independent direct-LLM action selector for complete museum conversations.

No call to Prolog preference decisions or the deterministic educational planner.
A shared extractor supplies validated state in both modes; direct model selects
its own next action from the same recorded visitor evidence.
"""
from __future__ import annotations

import os
from typing import Any



class DirectDialogueSelector:
    SCHEMA = {
        "type": "object", "additionalProperties": False,
        "properties": {
            "action_type": {"type": "string", "enum": ["clarify_interest", "recommend", "ask_knowledge", "explain", "insufficient_evidence"]},
            "artwork_id": {"type": ["string", "null"]},
            "topic_id": {"type": ["string", "null"]},
            "question_kind": {"type": ["string", "null"], "enum": ["atomic", "all_of", None]},
            "question_components": {"type": "array", "items": {"type": "string"}},
            "rationale": {"type": "string"},
        },
        "required": ["action_type", "artwork_id", "topic_id", "question_kind", "question_components", "rationale"],
    }

    def __init__(self, transport, evidence: dict, library):
        self.transport = transport
        self.evidence = evidence
        self.library = library
        self.last_record: dict | None = None

    @classmethod
    def from_environment(cls, evidence, library):
        from .clarification_baselines import OpenAIResponsesTransport
        api_key, model = os.environ.get("OPENAI_API_KEY"), os.environ.get("MUSEUM_LLM_MODEL")
        if not api_key or not model:
            raise RuntimeError("Direct mode requires OPENAI_API_KEY and MUSEUM_LLM_MODEL")
        transport = OpenAIResponsesTransport(
            api_key, model, endpoint=os.environ.get("MUSEUM_LLM_ENDPOINT", OpenAIResponsesTransport.DEFAULT_ENDPOINT),
            output_schema=cls.SCHEMA, schema_name="museum_direct_dialogue_action",
            system_prompt=("You are an independent museum-guide next-action selector. "
                           "Use only the recorded observations, visitor utterances, and provided ArtGraph/topic evidence. "
                           "Choose whether to clarify, recommend, check prior knowledge, explain, or abstain. "
                           "Do not assume an artwork's unrecorded attributes are false. Return a validated action only."),
        )
        return cls(transport, evidence, library)

    def select(self, session, evidence: dict, library, candidate_ids: tuple[str, ...], *, latest_utterance: str = "") -> dict:
        observed = {o["object_id"] for o in session.preferences if o["kind"] in {"likes", "dislikes"}}
        allowed = sorted(set(candidate_ids) - observed)
        payload = {
            "visitor_turns": session.turns[-12:],
            "latest_visitor_utterance": latest_utterance,
            "validated_observations": session.preferences,
            "knowledge_status": session.knowledge.statuses,
            "goal_topic": session.goal_topic,
            "pending_question": session.pending,
            "allowed_artworks": [{"artwork_id": aid, "label": evidence["artworks"][aid]["label"],
                                  "attributes": evidence["artworks"][aid]["attributes"]} for aid in allowed],
            "allowed_hypotheses": evidence["hypotheses"],
            "topics": [{"id": t.id, "label": t.label, "prerequisites": list(t.prerequisites)} for t in library.topics.values()],
            "required_output_schema": self.SCHEMA,
            "instruction": "Select ONE action. Never claim knowledge merely from an interest or a presented explanation.",
        }
        result = self.transport.complete_json(payload)
        clean = {k: v for k, v in result.items() if not k.startswith("_")}
        if set(clean) != set(self.SCHEMA["required"]):
            raise ValueError("Direct action has invalid fields")
        typ, aid, tid = clean["action_type"], clean["artwork_id"], clean["topic_id"]
        kind, cs = clean["question_kind"], clean["question_components"]
        ids = {h["id"] for h in evidence["hypotheses"]}
        if not isinstance(clean["rationale"], str) or not isinstance(cs, list):
            raise ValueError("Invalid direct action rationale/components")
        if typ == "recommend":
            if aid not in allowed or tid is not None or cs or kind is not None:
                raise ValueError("Invalid direct recommendation")
            # Structural compliance shared with hybrid: explicitly rejected
            # attributes cannot be silently reintroduced through a recommendation.
            record = evidence["artworks"][aid]
            supported = {(a["type"], a["value_id"]) for a in record["attributes"]}
            meta = {h["id"]: (h["attribute_type"], h["value_id"]) for h in evidence["hypotheses"]}
            excluded = {o["object_id"] for o in session.preferences if o["kind"] == "explicit_rejection"}
            if any(meta.get(h) in supported for h in excluded):
                raise ValueError("Direct recommendation conflicts with explicit rejection")
            action = {"type": "recommend", "artwork_id": aid}
        elif typ == "clarify_interest":
            if aid is not None or tid is not None or kind not in {"atomic", "all_of"} or len(cs) != (1 if kind == "atomic" else 2) or len(cs) != len(set(cs)) or not set(cs) <= ids:
                raise ValueError("Invalid direct clarification question")
            action = {"type": "clarify_interest", "explanation": {"kind": kind, "components": cs}}
        elif typ in {"ask_knowledge", "explain"}:
            if aid is not None or tid not in library.topics or cs or kind is not None:
                raise ValueError("Invalid direct knowledge action")
            action = {"type": typ, "topic_id": tid}
        elif typ == "insufficient_evidence":
            if aid is not None or tid is not None or cs or kind is not None:
                raise ValueError("Invalid direct abstention")
            action = {"type": "insufficient_evidence"}
        else:
            raise ValueError("Unknown direct action type")
        self.last_record = {"request": payload, "validated_result": clean,
                            "transport_metadata": result.get("_transport_metadata", {})}
        action.update(rule_id="direct_llm_selection", trace={"direct_method": True, "note": "no Prolog selector invoked"})
        return action
