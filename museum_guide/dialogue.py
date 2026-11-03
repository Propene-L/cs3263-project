"""Session-limited museum conversation pipeline.

Hybrid = LLM state extraction -> allowlist validation -> Prolog preference
reasoning / deterministic educational planner -> sourced template renderer.
Direct = same validated observations but LLM independently chooses an action;
it must never receive or call a Prolog decision.
"""
from __future__ import annotations

import copy
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .knowledge_layer import KnowledgeState, TopicLibrary, next_knowledge_action
from .turn_extraction import ManualExtractor, ValidatedTurnExtractor, validate_delta


@dataclass
class VisitorSession:
    id: str
    preferences: list[dict] = field(default_factory=list)
    knowledge: KnowledgeState = field(default_factory=KnowledgeState)
    goal_topic: str | None = None
    pending: dict | None = None
    asked_interest_questions: set[str] = field(default_factory=set)
    turns: list[dict] = field(default_factory=list)
    last_artwork_id: str | None = None
    turn_index: int = 0
    last_inference: dict | None = None

    def snapshot(self) -> dict:
        """Safe session summary for view/debug; no provider credentials or raw traces."""
        return {"id": self.id, "turn_index": self.turn_index,
                "preferences": list(self.preferences),
                "knowledge": dict(self.knowledge.statuses),
                "presented": sorted(self.knowledge.presented),
                "goal_topic": self.goal_topic,
                "pending": copy.deepcopy(self.pending)}


def question_key(explanation: dict) -> str:
    return explanation["kind"] + ":" + "+".join(sorted(explanation["components"]))


class MuseumDialogue:
    def __init__(self, evidence: dict, library: TopicLibrary, *, preference_engine: Any,
                 extractor: Any = None, direct_selector: Any = None,
                 candidate_artworks: tuple[str, ...] | None = None):
        self.evidence = evidence
        self.library = library
        self.preference_engine = preference_engine
        self.extractor = extractor
        self.direct_selector = direct_selector
        self.manual_extractor = ManualExtractor()
        self.artworks = set(evidence["artworks"])
        self.hypotheses = {h["id"] for h in evidence["hypotheses"]}
        self.hypothesis_labels = {h["id"]: h["label"] for h in evidence["hypotheses"]}
        self.candidate_artworks = tuple(candidate_artworks or sorted(self.artworks))
        if not self.candidate_artworks or not set(self.candidate_artworks) <= self.artworks:
            raise ValueError("Invalid action artwork allowlist")
        for topic in library.topics.values():
            if not set(topic.hypotheses) <= self.hypotheses:
                raise ValueError(f"Topic {topic.id} uses a hypothesis outside the curated vocabulary")

    @classmethod
    def from_repository(cls, root: str | Path | None = None, *, use_llm: bool = False,
                        with_direct: bool = False) -> "MuseumDialogue":
        from .preference_state import default_preference_state_engine
        root = Path(root) if root else Path(__file__).resolve().parents[1]
        evidence = json.loads((root / "data/curated/clarification_evidence.json").read_text(encoding="utf-8"))
        library = TopicLibrary.load(root / "data/curated/education_topics.json")
        extractor = ValidatedTurnExtractor.from_environment() if use_llm else None
        direct = None
        if with_direct:
            from .direct_dialogue import DirectDialogueSelector
            direct = DirectDialogueSelector.from_environment(evidence, library)
        preferred = ("ag_8415", "ag_20804", "ag_14531", "ag_23352", "ag_25837", "ag_30919",
                     "ag_10766", "ag_42361", "ag_14588", "ag_13233", "ag_10025", "ag_10472",
                     "ag_16386", "ag_12372", "ag_21076", "ag_11912", "ag_18987", "ag_13231")
        candidates = tuple(a for a in preferred if a in evidence["artworks"])
        if len(candidates) < 5:
            candidates = tuple(sorted(evidence["artworks"])[:18])
        return cls(evidence, library, preference_engine=(None if with_direct else default_preference_state_engine(root)),
                   extractor=extractor, direct_selector=direct, candidate_artworks=candidates)

    def new_session(self, session_id: str = "visitor_demo") -> VisitorSession:
        from .prolog_bridge import SAFE_ID
        if not isinstance(session_id, str) or not SAFE_ID.fullmatch(session_id):
            raise ValueError("Invalid session ID")
        return VisitorSession(id=session_id)

    def _preference_state(self, session: VisitorSession):
        from .preference_state import PreferenceObservation, PreferenceState
        return PreferenceState(
            session.id,
            tuple(PreferenceObservation(e["id"], e["kind"], e["object_id"],
                                        tuple(e["components"]), e["supersedes"])
                  for e in session.preferences),
            self.candidate_artworks,
        )

    def _add_preference(self, session: VisitorSession, *, kind: str, object_id: str,
                        components: tuple[str, ...] = (), supersedes: str | None = None) -> None:
        next_id = f"obs_{session.turn_index}_{len(session.preferences)+1}"
        session.preferences.append({"id": next_id, "kind": kind,
                                    "object_id": object_id, "components": list(components),
                                    "supersedes": supersedes})
        if kind == "likes":
            session.last_artwork_id = object_id

    def _apply_pending_answer(self, session: VisitorSession, answer: str) -> None:
        pending = session.pending
        if pending is None or answer == "none":
            return
        session.pending = None
        if pending["type"] == "clarify_interest":
            exp = pending["explanation"]
            session.asked_interest_questions.add(question_key(exp))
            if answer == "unsure":
                return
            is_pair = exp["kind"] == "all_of"
            kind = ("explicit_conjunction" if answer == "yes" else "reject_pair_explanation") if is_pair else (
                "explicit_interest" if answer == "yes" else "reject_atomic_explanation")
            self._add_preference(session, kind=kind,
                                 object_id="preference_pair" if is_pair else exp["components"][0],
                                 components=tuple(exp["components"]) if is_pair else ())
        elif pending["type"] == "offer_topic":
            if answer == "yes":
                session.goal_topic = pending["topic_id"]
            elif answer in {"no", "unsure"}:
                session.knowledge.skipped.add(pending["topic_id"])
        elif pending["type"] in {"ask_knowledge", "confirm_knowledge"}:
            if answer == "yes":
                session.knowledge.apply(pending["topic_id"], "known", source="visitor_confirmation")
            elif answer == "no":
                session.knowledge.apply(pending["topic_id"], "not_known", source="visitor_confirmation")
            # 'unsure' remains unknown and the question will not repeat.
        else:
            raise ValueError("Invalid pending question")

    def _apply_delta(self, session: VisitorSession, delta) -> None:
        session.turn_index += 1
        if delta.skip and session.pending:
            pending = session.pending
            if pending["type"] == "clarify_interest":
                session.asked_interest_questions.add(question_key(pending["explanation"]))
            if pending["type"] in {"ask_knowledge", "confirm_knowledge"}:
                session.knowledge.skipped.add(pending["topic_id"])
            session.pending = None
        elif delta.answer != "none":
            self._apply_pending_answer(session, delta.answer)
        elif session.pending and (delta.events or delta.topic_id is not None or delta.knowledge_updates):
            # New subject replaces an unanswered question rather than making a
            # later unqualified 'yes' refer to an obsolete prompt.
            if session.pending["type"] == "clarify_interest":
                session.asked_interest_questions.add(question_key(session.pending["explanation"]))
            session.pending = None
        for e in delta.events:
            self._add_preference(session, kind=e.kind, object_id=e.object_id,
                                 components=e.components, supersedes=e.supersedes)
        for topic, status in delta.knowledge_updates:
            session.knowledge.apply(topic, status)
            if status in {"known", "not_known", "unknown"}:
                session.knowledge.skipped.discard(topic)
        if delta.topic_id is not None:
            session.goal_topic = delta.topic_id
            if delta.change_topic:
                session.pending = None
        if delta.explain and session.goal_topic:
            # Express educational content request without inventing knowledge.
            session.knowledge.asked.add(session.goal_topic)

    def _infer(self, session: VisitorSession) -> dict:
        if self.preference_engine is None:
            raise RuntimeError("No Prolog preference engine configured")
        from .preference_state import validate_state
        state = self._preference_state(session)
        validate_state(state, self.evidence)
        result = self.preference_engine.infer(state)
        if result.get("status") != "ok" or not isinstance(result.get("decision"), dict):
            raise RuntimeError("Prolog produced an invalid preference-state decision")
        return result

    def _preference_action(self, session: VisitorSession, result: dict) -> dict:
        decision = result["decision"]
        typ = decision["action_type"]
        if typ == "clarify":
            question = decision.get("question")
            if not isinstance(question, dict) or question.get("kind") != "confirm_explanation":
                raise ValueError("Invalid Prolog clarification")
            exp = question["explanation"]
            key = question_key(exp)
            if key in session.asked_interest_questions:
                return {"type": "insufficient_evidence", "rule_id": "r_no_repeat_unanswered_question",
                        "trace": result, "reason": "Visitor previously skipped or left this question unresolved"}
            session.asked_interest_questions.add(key)
            session.pending = {"type": "clarify_interest", "explanation": copy.deepcopy(exp)}
            return {"type": "clarify_interest", "explanation": exp,
                    "rule_id": "prolog_preference_clarification", "trace": result}
        if typ == "recommend":
            artwork_id = decision.get("artwork_id")
            if artwork_id not in self.candidate_artworks:
                raise ValueError("Prolog recommended outside action allowlist")
            if artwork_id in {x["object_id"] for x in session.preferences if x["kind"] in {"likes", "dislikes"}}:
                raise ValueError("Prolog recommended an observed artwork")
            action = {"type": "recommend", "artwork_id": artwork_id,
                      "rule_id": "prolog_preference_recommendation", "trace": result}
            primary = result.get("primary_explanation")
            components = primary.get("components", []) if isinstance(primary, dict) else []
            if not components:
                components = [o["object_id"] for o in session.preferences if o["kind"] == "explicit_interest"]
            if {"h_expressionist_style", "h_portrait_genre"} <= set(components) and "c_expressionist_portrait" in self.library.topics:
                topic = "c_expressionist_portrait"
            else:
                topic = self.library.from_hypotheses(components)
            if topic and topic not in session.knowledge.skipped:
                action["follow_up_topic"] = topic
                session.pending = {"type": "offer_topic", "topic_id": topic}
            return action
        if typ != "insufficient_evidence":
            raise ValueError("Unsupported Prolog decision")
        return {"type": "insufficient_evidence", "rule_id": "prolog_preference_abstain", "trace": result}

    def _educational_action(self, session: VisitorSession, *, force_explain: bool = False) -> dict:
        action = next_knowledge_action(self.library, session.knowledge, session.goal_topic, force_explain=force_explain)
        if action["type"] in {"ask_knowledge", "confirm_knowledge"}:
            session.knowledge.asked.add(action["topic_id"])
            session.pending = {"type": action["type"], "topic_id": action["topic_id"]}
        if action["type"] == "explain":
            session.knowledge.presented.add(action["topic_id"])
        return action

    def run_turn(self, session: VisitorSession, user_text: str, *, mode: str = "manual") -> tuple[VisitorSession, dict]:
        """Returns a new session; validation / engine errors do not mutate old state."""
        if mode not in {"manual", "hybrid", "direct_llm"}:
            raise ValueError("Mode must be manual, hybrid, or direct_llm")
        if not isinstance(user_text, str) or not user_text.strip() or len(user_text) > 4000:
            raise ValueError("Visitor turn must contain 1..4000 characters")
        working = copy.deepcopy(session)
        extractor = self.manual_extractor if mode == "manual" else self.extractor
        if extractor is None:
            raise RuntimeError(f"{mode} requires a configured LLM state extractor")
        proposed = extractor.extract(user_text, pending=working.pending, artworks=self.artworks,
                                     hypotheses=self.hypotheses, topics=set(self.library.topics),
                                     previous_ids={x["id"] for x in working.preferences},
                                     history=working.turns,
                                     artwork_labels={k:v["label"] for k,v in self.evidence["artworks"].items()},
                                     hypothesis_labels=self.hypothesis_labels,
                                     topic_labels={k:v.label for k,v in self.library.topics.items()})
        delta = validate_delta(proposed, artworks=self.artworks, hypotheses=self.hypotheses,
                               topics=set(self.library.topics),
                               previous_ids={x["id"] for x in working.preferences}, pending=working.pending)
        old_pending = working.pending
        self._apply_delta(working, delta)
        if delta.skip:
            action = {"type": "acknowledge_skip", "rule_id": "r_honor_skip", "trace": []}
        elif mode == "direct_llm":
            if self.direct_selector is None:
                raise RuntimeError("direct_llm requires a separately configured independent action selector")
            # Deliberately no call to preference_engine here.
            action = self.direct_selector.select(working, self.evidence, self.library,
                                                 self.candidate_artworks, latest_utterance=user_text)
            if action["type"] == "clarify_interest":
                working.pending = {"type": "clarify_interest", "explanation": action["explanation"]}
            elif action["type"] in {"ask_knowledge", "confirm_knowledge"}:
                working.knowledge.asked.add(action["topic_id"])
                working.pending = {"type": action["type"], "topic_id": action["topic_id"]}
            elif action["type"] == "explain":
                working.knowledge.presented.add(action["topic_id"])
        elif working.goal_topic and (delta.topic_id is not None or delta.explain or
                                      (old_pending and old_pending["type"] in {"ask_knowledge", "confirm_knowledge", "offer_topic"} and delta.answer == "yes") or
                                      (old_pending and old_pending["type"] in {"ask_knowledge", "confirm_knowledge"} and delta.answer in {"no", "unsure"})):
            action = self._educational_action(working, force_explain=delta.explain)
        elif old_pending and old_pending["type"] == "offer_topic" and delta.answer in {"no", "unsure"}:
            action = {"type": "acknowledge_skip", "rule_id": "r_decline_topic_offer", "trace": []}
        elif delta.answer == "unsure" and old_pending and old_pending["type"] == "clarify_interest":
            action = {"type": "insufficient_evidence", "rule_id": "r_respect_unsure", "trace": []}
        elif not working.preferences and delta.knowledge_updates and not working.goal_topic:
            action = {"type": "acknowledge_knowledge", "rule_id": "r_record_explicit_knowledge", "trace": []}
        elif not working.preferences and not delta.knowledge_updates:
            action = {"type": "ask_open", "rule_id": "r_no_observation", "trace": []}
        else:
            result = self._infer(working)
            working.last_inference = result
            action = self._preference_action(working, result)
        from .response_renderer import render_action
        response = render_action(action, self.evidence, self.library, self.hypothesis_labels)
        if len(working.turns) >= 100:
            raise ValueError("Session turn limit reached; start a new session")
        working.turns.append({"visitor": user_text, "action_type": action["type"], "response": response["text"]})
        audit = {"mode": mode, "turn": working.turn_index,
                 "validated_delta": proposed, "action": {k: v for k, v in action.items() if k != "trace"},
                 "rule_id": action["rule_id"], "trace": action.get("trace", []),
                 "sources": response["sources"]}
        return working, {"action": action["type"], "text": response["text"],
                         "sources": response["sources"], "audit": audit,
                         "state": working.snapshot()}
