"""Shared, method-independent data contracts frozen in V2 Phase 0."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Literal


class TopicType(str, Enum):
    ARTWORK = "artwork"
    ARTIST = "artist"
    MOVEMENT = "movement"
    STYLE = "style"
    GENRE = "genre"
    MEDIUM = "medium"


@dataclass(frozen=True, slots=True)
class Topic:
    id: str
    type: TopicType
    label: str
    source_uri: str
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Fact:
    predicate: str
    args: tuple[str, ...]
    source_triple_id: str
    source_uri: str
    provenance: dict[str, Any]


@dataclass(frozen=True, slots=True)
class VisitorState:
    session_id: str
    goal_id: str
    known_topic_ids: tuple[str, ...] = ()
    presented_topic_ids: tuple[str, ...] = ()
    skipped_topic_ids: tuple[str, ...] = ()
    recent_turns: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class StateDelta:
    add_known: tuple[str, ...] = ()
    remove_known: tuple[str, ...] = ()
    set_goal: str | None = None
    skip: tuple[str, ...] = ()
    confidence: float | None = None
    uncertainty: bool = False


@dataclass(frozen=True, slots=True)
class Candidate:
    topic_id: str
    action: Literal["RECOMMEND"]
    rank: int
    support: dict[str, Any]
    method: str


@dataclass(frozen=True, slots=True)
class RecommendInput:
    scenario_id: str
    goal_id: str
    known_topic_ids: tuple[str, ...]
    skipped_topic_ids: tuple[str, ...]
    allowed_candidate_ids: tuple[str, ...]
    context_snapshot_id: str


@dataclass(frozen=True, slots=True)
class RecommendOutput:
    method: str
    ranked_topic_ids: tuple[str, ...]
    candidate_details: tuple[Candidate, ...]
    runtime_ms: float
    metadata: dict[str, Any]
    errors: tuple[str, ...] = ()

