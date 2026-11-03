"""Visitor utterance to an allowlisted state delta.

Manual mode is an explicit offline command language. Hybrid mode accepts only
structured extraction output from a configured provider; the model never
selects the symbolic action or supplies executable Prolog.
"""

from __future__ import annotations

import os
import shlex
from dataclasses import dataclass
from typing import Any, Protocol


PREFERENCE_KINDS = frozenset({
    "likes", "dislikes", "explicit_interest", "explicit_rejection",
    "explicit_conjunction", "reject_conjunction",
    "reject_atomic_explanation", "reject_pair_explanation",
})


@dataclass(frozen=True, slots=True)
class ProposedObservation:
    kind: str
    object_id: str
    components: tuple[str, ...] = ()
    supersedes: str | None = None


@dataclass(frozen=True, slots=True)
class TurnDelta:
    events: tuple[ProposedObservation, ...] = ()
    knowledge_updates: tuple[tuple[str, str], ...] = ()
    answer: str = "none"
    topic_id: str | None = None
    explain: bool = False
    skip: bool = False
    change_topic: bool = False


def as_payload(delta: TurnDelta) -> dict[str, Any]:
    return {
        "events": [
            {
                "kind": event.kind,
                "object_id": event.object_id,
                "components": list(event.components),
                "supersedes": event.supersedes,
            }
            for event in delta.events
        ],
        "knowledge_updates": [
            {"topic_id": topic_id, "status": status}
            for topic_id, status in delta.knowledge_updates
        ],
        "answer": delta.answer,
        "topic_id": delta.topic_id,
        "explain": delta.explain,
        "skip": delta.skip,
        "change_topic": delta.change_topic,
    }


def validate_delta(
    value: dict[str, Any],
    *,
    artworks: set[str],
    hypotheses: set[str],
    topics: set[str],
    previous_ids: set[str],
    pending: dict[str, Any] | None,
) -> TurnDelta:
    """Validate a proposed change atomically before mutating session state."""
    required = {
        "events", "knowledge_updates", "answer", "topic_id",
        "explain", "skip", "change_topic",
    }
    if not isinstance(value, dict) or set(value) != required:
        raise ValueError("Invalid state-delta fields")
    if any(type(value[name]) is not bool for name in ("explain", "skip", "change_topic")):
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
    for row in value["events"]:
        if not isinstance(row, dict) or set(row) != {
            "kind", "object_id", "components", "supersedes"
        }:
            raise ValueError("Invalid preference observation fields")
        kind = row["kind"]
        object_id = row["object_id"]
        components = row["components"]
        supersedes = row["supersedes"]
        if kind not in PREFERENCE_KINDS or not isinstance(object_id, str) or not isinstance(components, list):
            raise ValueError("Invalid preference observation")
        if supersedes is not None and (
            not isinstance(supersedes, str) or supersedes not in previous_ids
        ):
            raise ValueError("Correction cannot supersede a nonexistent observation")
        if kind in {"likes", "dislikes"}:
            valid = object_id in artworks and not components
        elif kind in {"explicit_interest", "explicit_rejection", "reject_atomic_explanation"}:
            valid = object_id in hypotheses and not components
        else:
            valid = (
                object_id == "preference_pair"
                and len(components) == 2
                and len(set(components)) == 2
                and set(components) <= hypotheses
            )
        if not valid:
            raise ValueError("Preference observation refers to invalid objects")
        events.append(ProposedObservation(kind, object_id, tuple(components), supersedes))

    updates: list[tuple[str, str]] = []
    for row in value["knowledge_updates"]:
        if not isinstance(row, dict) or set(row) != {"topic_id", "status"}:
            raise ValueError("Invalid knowledge-update fields")
        if row["topic_id"] not in topics or row["status"] not in {
            "known", "not_known", "unknown"
        }:
            raise ValueError("Invalid knowledge-update value")
        updates.append((row["topic_id"], row["status"]))
    return TurnDelta(
        tuple(events), tuple(updates), value["answer"], value["topic_id"],
        value["explain"], value["skip"], value["change_topic"],
    )


class ManualExtractor:
    """Parse explicit offline commands; this is not natural-language understanding."""

    def extract(self, text: str, **_: Any) -> dict[str, Any]:
        try:
            words = shlex.split(text.strip().lower())
        except ValueError as exc:
            raise ValueError("Unterminated command quotation") from exc
        if not words:
            return as_payload(TurnDelta())
        operation, *args = words
        if operation in {"yes", "no", "unsure"} and not args:
            return as_payload(TurnDelta(answer=operation))
        if operation in {"like", "dislike", "interested", "reject"} and len(args) == 1:
            kind = {
                "like": "likes", "dislike": "dislikes",
                "interested": "explicit_interest", "reject": "explicit_rejection",
            }[operation]
            return as_payload(TurnDelta(events=(ProposedObservation(kind, args[0]),)))
        if operation in {"conjunction", "reject-pair"} and len(args) == 2:
            kind = "explicit_conjunction" if operation == "conjunction" else "reject_pair_explanation"
            return as_payload(TurnDelta(events=(
                ProposedObservation(kind, "preference_pair", tuple(args)),
            )))
        if operation == "correct" and len(args) == 3 and args[1] in {
            "like", "dislike", "interested", "reject"
        }:
            kind = {
                "like": "likes", "dislike": "dislikes",
                "interested": "explicit_interest", "reject": "explicit_rejection",
            }[args[1]]
            return as_payload(TurnDelta(events=(
                ProposedObservation(kind, args[2], supersedes=args[0]),
            )))
        if operation in {"know", "dont-know", "unknown"} and len(args) == 1:
            status = {
                "know": "known", "dont-know": "not_known", "unknown": "unknown",
            }[operation]
            return as_payload(TurnDelta(knowledge_updates=((args[0], status),)))
        if operation == "topic" and len(args) == 1:
            return as_payload(TurnDelta(topic_id=args[0], change_topic=True))
        if operation == "explain" and len(args) == 1:
            return as_payload(TurnDelta(topic_id=args[0], explain=True))
        if operation == "skip" and not args:
            return as_payload(TurnDelta(skip=True))
        return as_payload(TurnDelta())


class JSONTransport(Protocol):
    def complete_json(self, payload: dict[str, Any]) -> dict[str, Any]: ...


class ValidatedTurnExtractor:
    """Ask a provider only for a proposed delta and retain an audit record."""

    SCHEMA: dict[str, Any] = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "events": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "kind": {"type": "string", "enum": sorted(PREFERENCE_KINDS)},
                        "object_id": {"type": "string"},
                        "components": {"type": "array", "items": {"type": "string"}},
                        "supersedes": {"type": ["string", "null"]},
                    },
                    "required": ["kind", "object_id", "components", "supersedes"],
                },
            },
            "knowledge_updates": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "topic_id": {"type": "string"},
                        "status": {"type": "string", "enum": ["known", "not_known", "unknown"]},
                    },
                    "required": ["topic_id", "status"],
                },
            },
            "answer": {"type": "string", "enum": ["none", "yes", "no", "unsure"]},
            "topic_id": {"type": ["string", "null"]},
            "explain": {"type": "boolean"},
            "skip": {"type": "boolean"},
            "change_topic": {"type": "boolean"},
        },
        "required": [
            "events", "knowledge_updates", "answer", "topic_id",
            "explain", "skip", "change_topic",
        ],
    }

    def __init__(self, transport: JSONTransport) -> None:
        self.transport = transport
        self.last_record: dict[str, Any] | None = None

    @classmethod
    def from_environment(cls) -> "ValidatedTurnExtractor":
        from .clarification_baselines import OpenAIResponsesTransport

        api_key = os.environ.get("OPENAI_API_KEY")
        model = os.environ.get("MUSEUM_LLM_MODEL")
        if not api_key or not model:
            raise RuntimeError("Hybrid mode requires OPENAI_API_KEY and MUSEUM_LLM_MODEL")
        return cls(OpenAIResponsesTransport(
            api_key,
            model,
            endpoint=os.environ.get(
                "MUSEUM_LLM_ENDPOINT", OpenAIResponsesTransport.DEFAULT_ENDPOINT
            ),
            output_schema=cls.SCHEMA,
            schema_name="museum_state_delta",
            system_prompt=(
                "Extract only the visitor's restricted museum state delta. Never select an action, "
                "recommend an artwork, invent museum facts, or infer unknown knowledge as not-known. "
                "Interpret yes/no/unsure only against the supplied pending question and use only IDs "
                "from the supplied allowlists. Return empty changes when the text is ambiguous."
            ),
        ))

    def extract(
        self,
        text: str,
        *,
        pending: dict[str, Any] | None,
        artworks: set[str],
        hypotheses: set[str],
        topics: set[str],
        previous_ids: set[str],
        history: list[dict[str, Any]] | None = None,
        artwork_labels: dict[str, str] | None = None,
        hypothesis_labels: dict[str, str] | None = None,
        topic_labels: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        payload = {
            "visitor_text": text,
            "pending_question": pending,
            "allowed_artwork_ids": sorted(artworks),
            "allowed_hypothesis_ids": sorted(hypotheses),
            "allowed_topic_ids": sorted(topics),
            "artwork_catalog": [
                {"id": key, "label": value}
                for key, value in sorted((artwork_labels or {}).items()) if key in artworks
            ],
            "hypothesis_catalog": [
                {"id": key, "label": value}
                for key, value in sorted((hypothesis_labels or {}).items()) if key in hypotheses
            ],
            "topic_catalog": [
                {"id": key, "label": value}
                for key, value in sorted((topic_labels or {}).items()) if key in topics
            ],
            "previous_observation_ids": sorted(previous_ids),
            "recent_turns": (history or [])[-4:],
            "instruction": "Return only a structured state delta, not the next action.",
        }
        self.last_record = {"request": payload, "status": "attempting"}
        try:
            result = self.transport.complete_json(payload)
            public_result = {key: value for key, value in result.items() if not key.startswith("_")}
            self.last_record.update({
                "status": "received",
                "response": public_result,
                "metadata": result.get("_transport_metadata", {}),
            })
            return public_result
        except Exception as exc:
            self.last_record.update({
                "status": "error", "error": f"{type(exc).__name__}: {exc}",
            })
            raise
