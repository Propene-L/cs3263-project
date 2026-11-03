"""Session-scoped Phase 2 orchestration for the museum guide.

Manual and optional hybrid extraction produce the same validated state delta.
SWI-Prolog remains authoritative for preference and educational next-action
selection; Python manages isolated state, validation, and rendering only.
"""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .knowledge_layer import (
    KnowledgeGuidanceEngine,
    KnowledgeState,
    TopicLibrary,
    default_knowledge_engine,
)
from .turn_extraction import ManualExtractor, ValidatedTurnExtractor, as_payload, validate_delta


@dataclass
class VisitorSession:
    id: str
    preferences: list[dict[str, Any]] = field(default_factory=list)
    knowledge: KnowledgeState = field(default_factory=KnowledgeState)
    goal_topic: str | None = None
    pending: dict[str, Any] | None = None
    asked_interest_questions: set[str] = field(default_factory=set)
    turns: list[dict[str, Any]] = field(default_factory=list)
    turn_index: int = 0
    last_inference: dict[str, Any] | None = None

    def snapshot(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "turn_index": self.turn_index,
            "preferences": copy.deepcopy(self.preferences),
            "knowledge": dict(self.knowledge.statuses),
            "presented": sorted(self.knowledge.presented),
            "skipped_topics": sorted(self.knowledge.skipped),
            "goal_topic": self.goal_topic,
            "pending": copy.deepcopy(self.pending),
        }


def question_key(explanation: dict[str, Any]) -> str:
    kind = explanation.get("kind")
    components = explanation.get("components")
    if kind not in {"atomic", "all_of"} or not isinstance(components, list) or not components:
        raise ValueError("Invalid clarification explanation")
    return f"{kind}:{'+'.join(sorted(components))}"


class MuseumDialogue:
    def __init__(
        self,
        evidence: dict[str, Any],
        library: TopicLibrary,
        *,
        preference_engine: Any,
        knowledge_engine: KnowledgeGuidanceEngine,
        extractor: Any = None,
        candidate_artworks: tuple[str, ...] | None = None,
    ) -> None:
        self.evidence = evidence
        self.library = library
        self.preference_engine = preference_engine
        self.knowledge_engine = knowledge_engine
        self.extractor = extractor
        self.manual_extractor = ManualExtractor()
        self.artworks = set(evidence["artworks"])
        self.hypotheses = {item["id"] for item in evidence["hypotheses"]}
        self.hypothesis_labels = {
            item["id"]: item["label"] for item in evidence["hypotheses"]
        }
        self.candidate_artworks = tuple(candidate_artworks or sorted(self.artworks))
        if not self.candidate_artworks or not set(self.candidate_artworks) <= self.artworks:
            raise ValueError("Invalid action artwork allowlist")
        for topic in library.topics.values():
            if not set(topic.hypotheses) <= self.hypotheses:
                raise ValueError(f"Topic {topic.id} uses a hypothesis outside the curated vocabulary")

    @classmethod
    def from_repository(
        cls,
        root: str | Path | None = None,
        *,
        use_llm: bool = False,
    ) -> "MuseumDialogue":
        from .preference_state import default_preference_state_engine

        project = Path(root) if root else Path(__file__).resolve().parents[1]
        evidence = json.loads(
            (project / "data" / "curated" / "clarification_evidence.json").read_text(
                encoding="utf-8"
            )
        )
        library = TopicLibrary.load(project / "data" / "curated" / "education_topics.json")
        extractor = ValidatedTurnExtractor.from_environment() if use_llm else None
        preferred = (
            "ag_8415", "ag_20804", "ag_14531", "ag_23352", "ag_25837", "ag_30919",
            "ag_10766", "ag_42361", "ag_14588", "ag_13233", "ag_10025", "ag_10472",
            "ag_16386", "ag_12372", "ag_21076", "ag_11912", "ag_18987", "ag_13231",
        )
        candidates = tuple(item for item in preferred if item in evidence["artworks"])
        if len(candidates) < 5:
            candidates = tuple(sorted(evidence["artworks"])[:18])
        return cls(
            evidence,
            library,
            preference_engine=default_preference_state_engine(project),
            knowledge_engine=default_knowledge_engine(project),
            extractor=extractor,
            candidate_artworks=candidates,
        )

    def new_session(self, session_id: str = "visitor_demo") -> VisitorSession:
        from .prolog_bridge import SAFE_ID

        if not isinstance(session_id, str) or not SAFE_ID.fullmatch(session_id):
            raise ValueError("Invalid session ID")
        return VisitorSession(id=session_id)

    def _preference_state(self, session: VisitorSession) -> Any:
        from .preference_state import PreferenceObservation, PreferenceState

        return PreferenceState(
            session.id,
            tuple(
                PreferenceObservation(
                    event["id"], event["kind"], event["object_id"],
                    tuple(event["components"]), event["supersedes"],
                )
                for event in session.preferences
            ),
            self.candidate_artworks,
        )

    def _add_preference(
        self,
        session: VisitorSession,
        *,
        kind: str,
        object_id: str,
        components: tuple[str, ...] = (),
        supersedes: str | None = None,
    ) -> None:
        event_id = f"obs_{session.turn_index}_{len(session.preferences) + 1}"
        session.preferences.append({
            "id": event_id,
            "kind": kind,
            "object_id": object_id,
            "components": list(components),
            "supersedes": supersedes,
        })

    def _apply_pending_answer(self, session: VisitorSession, answer: str) -> None:
        pending = session.pending
        if pending is None or answer == "none":
            return
        session.pending = None
        if pending["type"] == "clarify_interest":
            explanation = pending["explanation"]
            session.asked_interest_questions.add(question_key(explanation))
            if answer == "unsure":
                return
            is_pair = explanation["kind"] == "all_of"
            kind = (
                "explicit_conjunction" if answer == "yes" else "reject_pair_explanation"
            ) if is_pair else (
                "explicit_interest" if answer == "yes" else "reject_atomic_explanation"
            )
            self._add_preference(
                session,
                kind=kind,
                object_id="preference_pair" if is_pair else explanation["components"][0],
                components=tuple(explanation["components"]) if is_pair else (),
            )
        elif pending["type"] in {"ask_knowledge", "confirm_knowledge"}:
            if answer == "yes":
                session.knowledge.apply(pending["topic_id"], "known", confirmed=True)
            elif answer == "no":
                session.knowledge.apply(pending["topic_id"], "not_known", confirmed=True)
        else:
            raise ValueError("Invalid pending question")

    def _apply_delta(self, session: VisitorSession, delta: Any) -> None:
        session.turn_index += 1
        if delta.skip and session.pending:
            pending = session.pending
            if pending["type"] == "clarify_interest":
                session.asked_interest_questions.add(question_key(pending["explanation"]))
            elif pending["type"] in {"ask_knowledge", "confirm_knowledge"}:
                session.knowledge.skipped.add(pending["topic_id"])
            session.pending = None
        elif delta.answer != "none":
            self._apply_pending_answer(session, delta.answer)
        elif session.pending and (delta.events or delta.topic_id is not None or delta.knowledge_updates):
            if session.pending["type"] == "clarify_interest":
                session.asked_interest_questions.add(question_key(session.pending["explanation"]))
            session.pending = None
        for event in delta.events:
            self._add_preference(
                session,
                kind=event.kind,
                object_id=event.object_id,
                components=event.components,
                supersedes=event.supersedes,
            )
        for topic_id, status in delta.knowledge_updates:
            session.knowledge.apply(topic_id, status)
            session.knowledge.skipped.discard(topic_id)
        if delta.topic_id is not None:
            session.goal_topic = delta.topic_id
            if delta.change_topic:
                session.pending = None

    def _infer_preference(self, session: VisitorSession) -> dict[str, Any]:
        from .preference_state import validate_state

        state = self._preference_state(session)
        validate_state(state, self.evidence)
        result = self.preference_engine.infer(state)
        if result.get("status") != "ok" or not isinstance(result.get("decision"), dict):
            raise RuntimeError("Prolog produced an invalid preference-state decision")
        return result

    def _preference_action(
        self, session: VisitorSession, result: dict[str, Any]
    ) -> dict[str, Any]:
        decision = result["decision"]
        action_type = decision.get("action_type")
        if action_type == "clarify":
            question = decision.get("question")
            if not isinstance(question, dict) or question.get("kind") != "confirm_explanation":
                raise ValueError("Invalid Prolog clarification")
            explanation = question.get("explanation")
            key = question_key(explanation)
            if key in session.asked_interest_questions:
                return {
                    "type": "insufficient_evidence",
                    "rule_id": "r_no_repeat_unanswered_question",
                    "trace": result,
                }
            session.asked_interest_questions.add(key)
            session.pending = {
                "type": "clarify_interest", "explanation": copy.deepcopy(explanation)
            }
            return {
                "type": "clarify_interest",
                "explanation": explanation,
                "rule_id": "prolog_preference_clarification",
                "trace": result,
            }
        if action_type == "recommend":
            artwork_id = decision.get("artwork_id")
            observed = {
                event["object_id"]
                for event in session.preferences if event["kind"] in {"likes", "dislikes"}
            }
            if artwork_id not in self.candidate_artworks or artwork_id in observed:
                raise ValueError("Prolog recommended an invalid artwork")
            return {
                "type": "recommend",
                "artwork_id": artwork_id,
                "rule_id": "prolog_preference_recommendation",
                "trace": result,
            }
        if action_type != "insufficient_evidence":
            raise ValueError("Unsupported Prolog decision")
        return {
            "type": "insufficient_evidence",
            "rule_id": "prolog_preference_abstain",
            "trace": result,
        }

    def _knowledge_action(
        self, session: VisitorSession, *, force_explain: bool = False
    ) -> dict[str, Any]:
        if session.goal_topic is None:
            raise ValueError("Knowledge action requires a goal topic")
        result = self.knowledge_engine.infer(
            self.library,
            session.knowledge,
            session.goal_topic,
            force_explain=force_explain,
        )
        decision = result["decision"]
        action = {
            "type": decision["action_type"],
            "topic_id": decision["topic_id"],
            "rule_id": decision["rule_id"],
            "trace": result,
        }
        if action["type"] in {"ask_knowledge", "confirm_knowledge"}:
            session.knowledge.asked.add(action["topic_id"])
            session.pending = {"type": action["type"], "topic_id": action["topic_id"]}
        elif action["type"] == "explain":
            session.knowledge.presented.add(action["topic_id"])
        return action

    def run_turn(
        self,
        session: VisitorSession,
        user_text: str,
        *,
        mode: str = "manual",
    ) -> tuple[VisitorSession, dict[str, Any]]:
        """Apply one turn atomically; errors leave the supplied session untouched."""
        if mode not in {"manual", "hybrid"}:
            raise ValueError("Mode must be manual or hybrid")
        if not isinstance(user_text, str) or not user_text.strip() or len(user_text) > 4000:
            raise ValueError("Visitor turn must contain 1..4000 characters")
        working = copy.deepcopy(session)
        extractor = self.manual_extractor if mode == "manual" else self.extractor
        if extractor is None:
            raise RuntimeError("Hybrid mode requires a configured LLM state extractor")
        proposed = extractor.extract(
            user_text,
            pending=working.pending,
            artworks=self.artworks,
            hypotheses=self.hypotheses,
            topics=set(self.library.topics),
            previous_ids={event["id"] for event in working.preferences},
            history=working.turns,
            artwork_labels={key: value["label"] for key, value in self.evidence["artworks"].items()},
            hypothesis_labels=self.hypothesis_labels,
            topic_labels={key: value.label for key, value in self.library.topics.items()},
        )
        delta = validate_delta(
            proposed,
            artworks=self.artworks,
            hypotheses=self.hypotheses,
            topics=set(self.library.topics),
            previous_ids={event["id"] for event in working.preferences},
            pending=working.pending,
        )
        old_pending = copy.deepcopy(working.pending)
        self._apply_delta(working, delta)
        knowledge_continuation = (
            old_pending is not None
            and old_pending.get("type") in {"ask_knowledge", "confirm_knowledge"}
            and delta.answer in {"yes", "no", "unsure"}
        )
        if delta.skip:
            action = {"type": "acknowledge_skip", "rule_id": "r_honor_skip", "trace": {}}
        elif working.goal_topic and (
            delta.topic_id is not None
            or delta.explain
            or bool(delta.knowledge_updates)
            or knowledge_continuation
        ):
            action = self._knowledge_action(working, force_explain=delta.explain)
        elif delta.answer == "unsure" and old_pending and old_pending.get("type") == "clarify_interest":
            action = {"type": "insufficient_evidence", "rule_id": "r_respect_unsure", "trace": {}}
        elif not working.preferences and delta.knowledge_updates:
            action = {
                "type": "acknowledge_knowledge",
                "rule_id": "r_record_explicit_knowledge",
                "trace": {},
            }
        elif not working.preferences and not delta.events:
            action = {"type": "ask_open", "rule_id": "r_no_observation", "trace": {}}
        else:
            result = self._infer_preference(working)
            working.last_inference = result
            action = self._preference_action(working, result)

        from .response_renderer import render_action

        response = render_action(action, self.evidence, self.library, self.hypothesis_labels)
        if len(working.turns) >= 100:
            raise ValueError("Session turn limit reached; start a new session")
        working.turns.append({
            "visitor": user_text,
            "action_type": action["type"],
            "response": response["text"],
        })
        audit = {
            "mode": mode,
            "turn": working.turn_index,
            "validated_delta": as_payload(delta),
            "action": {key: value for key, value in action.items() if key != "trace"},
            "rule_id": action["rule_id"],
            "trace": action.get("trace", {}),
            "sources": response["sources"],
        }
        return working, {
            "action": action["type"],
            "text": response["text"],
            "sources": response["sources"],
            "audit": audit,
            "state": working.snapshot(),
        }
