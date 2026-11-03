"""Finite sourced educational concept graph and deterministic knowledge planner.

Pedagogical prerequisites are curated policy edges; they are not claimed to be
ArtGraph edges. Unknown does not mean not-known; presented does not mean known.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping

STATUSES = frozenset({"known", "not_known", "unknown", "conflicted"})


@dataclass(frozen=True)
class Topic:
    id: str
    label: str
    prerequisites: tuple[str, ...]
    hypotheses: tuple[str, ...]
    explanation: str
    source_id: str
    source_url: str


class TopicLibrary:
    def __init__(self, topics: list[Topic]):
        self.topics = {t.id: t for t in topics}
        if len(self.topics) != len(topics) or not topics:
            raise ValueError("Topic IDs must be unique and nonempty")
        self._order = {}
        for topic in topics:
            if not topic.id.startswith("c_") or not topic.label or not topic.explanation:
                raise ValueError("Topic must have a safe ID, label and educational text")
            if not topic.source_id or not topic.source_url.startswith("https://"):
                raise ValueError(f"Topic {topic.id} needs a source URL and source ID")
            if len(set(topic.prerequisites)) != len(topic.prerequisites):
                raise ValueError("Duplicate prerequisite")
            for p in topic.prerequisites:
                if p not in self.topics:
                    raise ValueError(f"Unknown prerequisite {p!r}")
        visiting = set()
        def dfs(tid: str) -> tuple[str, ...]:
            if tid in visiting:
                raise ValueError("Cycle in concept prerequisites")
            if tid in self._order:
                return self._order[tid]
            visiting.add(tid)
            out: list[str] = []
            for dependency in self.topics[tid].prerequisites:
                for item in (*dfs(dependency), dependency):
                    if item not in out:
                        out.append(item)
            visiting.remove(tid)
            self._order[tid] = tuple(out)
            return tuple(out)
        for tid in self.topics:
            dfs(tid)

    @classmethod
    def load(cls, path: str | Path) -> "TopicLibrary":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if data.get("schema_version") != "1.0":
            raise ValueError("Unsupported topic schema")
        return cls([Topic(
            id=r["id"], label=r["label"],
            prerequisites=tuple(r["prerequisites"]),
            hypotheses=tuple(r["hypotheses"]),
            explanation=r["explanation"], source_id=r["source_id"],
            source_url=r["source_url"]
        ) for r in data["topics"]])

    def path(self, topic: str) -> tuple[str, ...]:
        if topic not in self.topics:
            raise ValueError(f"Unknown topic {topic}")
        return (*self._order[topic], topic)

    def from_hypotheses(self, ids: list[str] | tuple[str, ...]) -> str | None:
        """Pick a related topic, not a claim about knowledge or interest."""
        for hypothesis in ids:
            for t in self.topics.values():
                if hypothesis in t.hypotheses:
                    return t.id
        return None


@dataclass
class KnowledgeState:
    statuses: dict[str, str] = field(default_factory=dict)
    asked: set[str] = field(default_factory=set)
    presented: set[str] = field(default_factory=set)
    skipped: set[str] = field(default_factory=set)
    history: list[dict] = field(default_factory=list)

    def status(self, topic: str) -> str:
        return self.statuses.get(topic, "unknown")

    def apply(self, topic: str, status: str, *, source: str = "visitor") -> None:
        if status not in STATUSES:
            raise ValueError(f"Invalid knowledge status {status}")
        # Chronological explicit correction replaces status, not the audit trail.
        previous = self.statuses.get(topic, "unknown")
        if (source == "visitor" and previous in {"known", "not_known"}
                and status in {"known", "not_known"} and status != previous):
            self.history.append({"topic": topic, "status": status, "source": "conflicting_new_statement"})
            self.statuses[topic] = "conflicted"
            return
        self.history.append({"topic": topic, "status": status, "source": source})
        self.statuses[topic] = status


def next_knowledge_action(library: TopicLibrary, state: KnowledgeState, goal: str, *, force_explain: bool = False) -> dict:
    """Backward prerequisite traversal and forward readiness update.

    A visitor can request an explanation even if knowledge is unknown, but this
    marks only 'presented' after delivery. Repeated unanswered questions are
    never asked again in the same session.
    """
    path = library.path(goal)
    trace: list[dict] = []
    for tid in path:
        status = state.status(tid)
        trace.append({"topic": tid, "status": status, "rule": "prerequisite_first"})
        if tid in state.skipped or tid in state.presented:
            continue
        if status == "conflicted":
            return {"type": "confirm_knowledge", "topic_id": tid, "rule_id": "r_confirm_conflict", "trace": trace}
        if status == "known":
            continue
        if status == "not_known":
            return {"type": "explain", "topic_id": tid, "rule_id": "r_explain_not_known", "trace": trace}
        if status == "unknown" and tid not in state.asked and not force_explain:
            return {"type": "ask_knowledge", "topic_id": tid, "rule_id": "r_ask_unknown_prerequisite", "trace": trace}
        # Explicit request or unanswered question: offer explanation, but do not
        # infer that the user did not know the concept.
        return {"type": "explain", "topic_id": tid, "rule_id": "r_offer_uncertain_intro", "trace": trace}
    if force_explain:
        return {"type": "explain", "topic_id": goal, "rule_id": "r_explicit_explanation_request", "trace": trace}
    return {"type": "finish_topic", "topic_id": goal, "rule_id": "r_all_prerequisites_addressed", "trace": trace}
