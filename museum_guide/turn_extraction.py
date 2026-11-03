"""Visitor utterance -> allowlisted state delta. No model may select hybrid actions.

Manual mode is an explicit command interface for offline tests. Hybrid mode
accepts only validated extraction JSON from a configured model/provider.
"""
from __future__ import annotations

import os
import shlex
from dataclasses import dataclass, field
from typing import Any, Protocol

PREFERENCE_KINDS = frozenset({
    "likes", "dislikes", "explicit_interest", "explicit_rejection",
    "explicit_conjunction", "reject_conjunction",
    "reject_atomic_explanation", "reject_pair_explanation",
})

@dataclass(frozen=True)
class ProposedObservation:
    kind: str
    object_id: str
    components: tuple[str, ...] = ()
    supersedes: str | None = None

@dataclass(frozen=True)
class StateDelta:
    events: tuple[ProposedObservation, ...] = ()
    knowledge_updates: tuple[tuple[str, str], ...] = ()
    answer: str = "none"     # none|yes|no|unsure, applies only to pending question
    topic_id: str | None = None
    explain: bool = False
    skip: bool = False
    change_topic: bool = False
    unparsed: bool = False


def validate_delta(value: dict[str, Any], *, artworks: set[str], hypotheses: set[str],
                   topics: set[str], previous_ids: set[str], pending: dict | None) -> StateDelta:
    """All-or-nothing validation. A malformed extraction never changes state."""
    required = {"events", "knowledge_updates", "answer", "topic_id", "explain", "skip", "change_topic"}
    if not isinstance(value, dict) or set(value) != required:
        raise ValueError("Invalid state-delta fields")
    if type(value["explain"]) is not bool or type(value["skip"]) is not bool or type(value["change_topic"]) is not bool:
        raise ValueError("Invalid state-delta flags")
    if value["answer"] not in {"none", "yes", "no", "unsure"}:
        raise ValueError("Invalid answer enum")
    if value["answer"] != "none" and pending is None:
        raise ValueError("Answer without a pending question")
    if value["topic_id"] is not None and value["topic_id"] not in topics:
        raise ValueError("Unknown topic ID")
    if not isinstance(value["events"], list) or not isinstance(value["knowledge_updates"], list):
        raise ValueError("Events and knowledge updates must be arrays")
    if len(value["events"]) > 8 or len(value["knowledge_updates"]) > 8:
        raise ValueError("Too many changes in one turn")
    events: list[ProposedObservation] = []
    for e in value["events"]:
        if not isinstance(e, dict) or set(e) != {"kind", "object_id", "components", "supersedes"}:
            raise ValueError("Invalid preference observation fields")
        kind, obj, components, supersedes = e["kind"], e["object_id"], e["components"], e["supersedes"]
        if kind not in PREFERENCE_KINDS or not isinstance(components, list) or not isinstance(obj, str):
            raise ValueError("Invalid preference observation")
        if supersedes is not None and (not isinstance(supersedes, str) or supersedes not in previous_ids):
            raise ValueError("Correction cannot supersede a nonexistent observation")
        if kind in {"likes", "dislikes"}:
            valid = obj in artworks and not components
        elif kind in {"explicit_interest", "explicit_rejection", "reject_atomic_explanation"}:
            valid = obj in hypotheses and not components
        else:
            valid = (obj == "preference_pair" and len(components) == 2
                     and len(set(components)) == 2 and set(components) <= hypotheses)
        if not valid:
            raise ValueError("Preference observation refers to invalid objects")
        events.append(ProposedObservation(kind, obj, tuple(components), supersedes))
    updates: list[tuple[str, str]] = []
    for row in value["knowledge_updates"]:
        if not isinstance(row, dict) or set(row) != {"topic_id", "status"}:
            raise ValueError("Invalid knowledge-update fields")
        if row["topic_id"] not in topics or row["status"] not in {"known", "not_known", "conflicted", "unknown"}:
            raise ValueError("Invalid knowledge-update value")
        updates.append((row["topic_id"], row["status"]))
    return StateDelta(tuple(events), tuple(updates), value["answer"], value["topic_id"],
                      value["explain"], value["skip"], value["change_topic"])


def as_payload(delta: StateDelta) -> dict:
    return {
        "events": [{"kind": e.kind, "object_id": e.object_id, "components": list(e.components),
                    "supersedes": e.supersedes} for e in delta.events],
        "knowledge_updates": [{"topic_id": k, "status": s} for k, s in delta.knowledge_updates],
        "answer": delta.answer, "topic_id": delta.topic_id,
        "explain": delta.explain, "skip": delta.skip, "change_topic": delta.change_topic,
    }


class ManualExtractor:
    """Deliberately explicit CLI commands; not natural-language understanding."""
    def extract(self, text: str, *, pending: dict | None = None, **_: Any) -> dict:
        try:
            words = shlex.split(text.strip().lower())
        except ValueError as exc:
            raise ValueError("Unterminated command quotation") from exc
        if not words:
            return as_payload(StateDelta(unparsed=True))
        op, *args = words
        if op in {"yes", "no", "unsure"} and not args:
            return as_payload(StateDelta(answer=op))
        if op in {"like", "dislike", "interested", "reject"} and len(args) == 1:
            kind = {"like": "likes", "dislike": "dislikes", "interested": "explicit_interest", "reject": "explicit_rejection"}[op]
            return as_payload(StateDelta(events=(ProposedObservation(kind, args[0]),)))
        if op in {"conjunction", "reject-pair"} and len(args) == 2:
            kind = "explicit_conjunction" if op == "conjunction" else "reject_pair_explanation"
            return as_payload(StateDelta(events=(ProposedObservation(kind, "preference_pair", tuple(args)),)))
        if op == "correct" and len(args) == 3 and args[1] in {"like", "dislike", "interested", "reject"}:
            kind = {"like": "likes", "dislike": "dislikes", "interested": "explicit_interest", "reject": "explicit_rejection"}[args[1]]
            return as_payload(StateDelta(events=(ProposedObservation(kind, args[2], supersedes=args[0]),)))
        if op in {"know", "dont-know", "unknown"} and len(args) == 1:
            status = {"know": "known", "dont-know": "not_known", "unknown": "unknown"}[op]
            return as_payload(StateDelta(knowledge_updates=((args[0], status),)))
        if op == "topic" and len(args) == 1:
            return as_payload(StateDelta(topic_id=args[0], change_topic=True))
        if op == "explain" and len(args) == 1:
            return as_payload(StateDelta(topic_id=args[0], explain=True))
        if op == "skip" and not args:
            return as_payload(StateDelta(skip=True))
        return as_payload(StateDelta(unparsed=True))


class JSONTransport(Protocol):
    def complete_json(self, payload: dict[str, Any]) -> dict[str, Any]: ...


class ValidatedTurnExtractor:
    """LLM output is only a *proposed* state delta and is validated downstream."""
    SCHEMA: dict[str, Any] = {
        "type": "object", "additionalProperties": False,
        "properties": {
            "events": {"type": "array", "items": {
                "type": "object", "additionalProperties": False,
                "properties": {
                    "kind": {"type": "string", "enum": sorted(PREFERENCE_KINDS)},
                    "object_id": {"type": "string"},
                    "components": {"type": "array", "items": {"type": "string"}},
                    "supersedes": {"type": ["string", "null"]},
                }, "required": ["kind", "object_id", "components", "supersedes"],
            }},
            "knowledge_updates": {"type": "array", "items": {
                "type": "object", "additionalProperties": False,
                "properties": {"topic_id": {"type": "string"},
                               "status": {"type": "string", "enum": ["known", "not_known", "unknown", "conflicted"]}},
                "required": ["topic_id", "status"],
            }},
            "answer": {"type": "string", "enum": ["none", "yes", "no", "unsure"]},
            "topic_id": {"type": ["string", "null"]},
            "explain": {"type": "boolean"},
            "skip": {"type": "boolean"},
            "change_topic": {"type": "boolean"},
        },
        "required": ["events", "knowledge_updates", "answer", "topic_id", "explain", "skip", "change_topic"],
    }

    def __init__(self, transport: JSONTransport):
        self.transport = transport
        self.last_record: dict[str, Any] | None = None

    @classmethod
    def from_environment(cls):
        from .clarification_baselines import OpenAIResponsesTransport
        api_key = os.environ.get("OPENAI_API_KEY")
        model = os.environ.get("MUSEUM_LLM_MODEL")
        if not api_key or not model:
            raise RuntimeError("Hybrid mode requires OPENAI_API_KEY and MUSEUM_LLM_MODEL")
        return cls(OpenAIResponsesTransport(
            api_key, model,
            endpoint=os.environ.get("MUSEUM_LLM_ENDPOINT", OpenAIResponsesTransport.DEFAULT_ENDPOINT),
            output_schema=cls.SCHEMA, schema_name="museum_state_delta",
            system_prompt=(
                "Convert the visitor's latest utterance into the restricted museum state delta. "
                "Never choose an action, recommend artwork, invent museum facts, or assume unknown means not_known. "
                "Only explicit knowledge assertions can set known/not_known. Interpret yes/no/unsure "
                "relative to pending_question if present. Use only allowed IDs. "
                "Translate artwork names by the supplied artwork_catalog; never guess unknown titles. "
                "If a label is ambiguous or the utterance is unsupported, return empty changes."
            ),
        ))

    def extract(self, text: str, *, pending: dict | None, artworks: set[str], hypotheses: set[str],
                topics: set[str], previous_ids: set[str], history: list[dict] | None = None,
                artwork_labels: dict[str, str] | None = None,
                hypothesis_labels: dict[str, str] | None = None,
                topic_labels: dict[str, str] | None = None) -> dict:
        payload = {"visitor_text": text, "pending_question": pending,
                   "allowed_artwork_ids": sorted(artworks),
                   "allowed_hypothesis_ids": sorted(hypotheses),
                   "allowed_topic_ids": sorted(topics),
                   "artwork_catalog": [{"id": k, "label": v} for k, v in sorted((artwork_labels or {}).items()) if k in artworks],
                   "hypothesis_catalog": [{"id": k, "label": v} for k, v in sorted((hypothesis_labels or {}).items()) if k in hypotheses],
                   "topic_catalog": [{"id": k, "label": v} for k, v in sorted((topic_labels or {}).items()) if k in topics],
                   "previous_observation_ids": sorted(previous_ids),
                   "recent_turns": (history or [])[-4:],
                   "instruction": "Return only a structured state delta, not the next action."}
        self.last_record = {"request": payload, "status": "attempting"}
        try:
            result = self.transport.complete_json(payload)
            self.last_record.update({"status": "received", "response": {k:v for k,v in result.items() if not k.startswith('_')},
                                     "metadata": result.get("_transport_metadata", {})})
            return {k: v for k, v in result.items() if not k.startswith("_")}
        except Exception as exc:
            self.last_record["status"] = "error"
            self.last_record["error"] = f"{type(exc).__name__}: {exc}"
            raise
