"""Typed educational state and a stateless SWI-Prolog guidance bridge.

Python validates and serializes the bounded topic catalog and visitor state.
All prerequisite traversal and next-action selection occurs in
``logic/knowledge_guidance_rules.pl``.
"""

from __future__ import annotations

import json
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

from .prolog_bridge import PrologError, SAFE_ID, find_swipl


@dataclass(frozen=True, slots=True)
class Topic:
    id: str
    label: str
    prerequisites: tuple[str, ...]
    hypotheses: tuple[str, ...]
    explanation: str
    source_id: str
    source_url: str


class TopicLibrary:
    def __init__(self, topics: list[Topic]) -> None:
        self.topics = {topic.id: topic for topic in topics}
        if len(self.topics) != len(topics):
            raise ValueError("Duplicate educational topic ID")
        for topic in topics:
            _safe_id(topic.id, "topic ID")
            if not topic.label.strip() or not topic.explanation.strip():
                raise ValueError("Topic label and explanation are required")
            if not topic.source_id.strip() or not topic.source_url.startswith("https://"):
                raise ValueError("Topic source ID and HTTPS URL are required")
            if len(set(topic.prerequisites)) != len(topic.prerequisites):
                raise ValueError("Duplicate prerequisite")
            if not set(topic.prerequisites) <= set(self.topics):
                raise ValueError(f"Unknown prerequisite for {topic.id}")
            for value in (*topic.prerequisites, *topic.hypotheses):
                _safe_id(value, "catalog ID")

    @classmethod
    def load(cls, path: str | Path) -> "TopicLibrary":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if data.get("schema_version") != "1.0" or not isinstance(data.get("topics"), list):
            raise ValueError("Unsupported educational topic catalog")
        return cls([
            Topic(
                id=row["id"],
                label=row["label"],
                prerequisites=tuple(row["prerequisites"]),
                hypotheses=tuple(row["hypotheses"]),
                explanation=row["explanation"],
                source_id=row["source_id"],
                source_url=row["source_url"],
            )
            for row in data["topics"]
        ])


@dataclass
class KnowledgeState:
    statuses: dict[str, str] = field(default_factory=dict)
    presented: set[str] = field(default_factory=set)
    skipped: set[str] = field(default_factory=set)
    asked: set[str] = field(default_factory=set)

    def status(self, topic_id: str) -> str:
        return self.statuses.get(topic_id, "unknown")

    def apply(self, topic_id: str, status: str, *, confirmed: bool = False) -> None:
        if status not in {"known", "not_known", "unknown", "conflicted"}:
            raise ValueError("Invalid knowledge status")
        previous = self.status(topic_id)
        if confirmed or previous in {"unknown", status}:
            if status == "unknown":
                self.statuses.pop(topic_id, None)
            else:
                self.statuses[topic_id] = status
        elif previous != status:
            self.statuses[topic_id] = "conflicted"


def _safe_id(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not SAFE_ID.fullmatch(value):
        raise PrologError(f"Unsafe {field_name}: {value!r}")
    return value


class KnowledgeGuidanceEngine:
    """Invoke a fresh SWI-Prolog process for each educational action."""

    def __init__(
        self,
        rules_path: str | Path,
        *,
        swipl_path: str | Path | None = None,
        timeout_seconds: float = 10,
    ) -> None:
        self.rules_path = Path(rules_path).resolve()
        executable = Path(swipl_path) if swipl_path else find_swipl()
        if executable is None:
            raise PrologError("SWI-Prolog executable not found; set SWIPL_PATH")
        self.swipl_path = executable
        self.timeout_seconds = timeout_seconds
        self.runtime_directory = self.rules_path.parents[1] / ".runtime"

    def infer(
        self,
        library: TopicLibrary,
        state: KnowledgeState,
        goal_topic: str,
        *,
        force_explain: bool = False,
    ) -> dict[str, Any]:
        if goal_topic not in library.topics:
            raise PrologError("Unknown educational goal")
        catalog_ids = set(library.topics)
        if not (set(state.statuses) | state.presented | state.skipped | state.asked) <= catalog_ids:
            raise PrologError("Knowledge state contains an unknown topic")
        lines = [
            ":- dynamic topic/1, topic_order/2, prerequisite/2, goal_topic/1.",
            ":- dynamic knowledge_status/2, asked_topic/1, presented_topic/1, skipped_topic/1, force_explain/0.",
            ":- discontiguous topic/1, topic_order/2, prerequisite/2.",
            f"goal_topic({_safe_id(goal_topic, 'goal topic')}).",
        ]
        for order, topic in enumerate(library.topics.values()):
            lines.append(f"topic({_safe_id(topic.id, 'topic ID')}).")
            lines.append(f"topic_order({topic.id}, {order}).")
            lines.extend(f"prerequisite({topic.id}, {_safe_id(item, 'prerequisite ID')})." for item in topic.prerequisites)
        for topic_id, status in sorted(state.statuses.items()):
            if status not in {"known", "not_known", "unknown", "conflicted"}:
                raise PrologError("Invalid knowledge status")
            lines.append(f"knowledge_status({_safe_id(topic_id, 'topic ID')}, {status}).")
        lines.extend(f"asked_topic({_safe_id(item, 'topic ID')})." for item in sorted(state.asked))
        lines.extend(f"presented_topic({_safe_id(item, 'topic ID')})." for item in sorted(state.presented))
        lines.extend(f"skipped_topic({_safe_id(item, 'topic ID')})." for item in sorted(state.skipped))
        if force_explain:
            lines.append("force_explain.")
        self.runtime_directory = self.runtime_directory.resolve()
        self.runtime_directory.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="museum-knowledge-", dir=self.runtime_directory) as directory:
            state_path = Path(directory) / "validated_state.pl"
            state_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            command = [
                str(self.swipl_path), "-q", "-s", str(state_path), "-s", str(self.rules_path),
                "-g", "write_knowledge_action_json", "-t", "halt",
            ]
            try:
                completed = subprocess.run(
                    command, capture_output=True, text=True,
                    timeout=self.timeout_seconds, check=False,
                )
            except subprocess.TimeoutExpired as exc:
                raise PrologError(f"SWI-Prolog timed out after {self.timeout_seconds}s") from exc
        if completed.returncode != 0:
            raise PrologError(f"SWI-Prolog exited {completed.returncode}: {completed.stderr.strip()}")
        if completed.stderr.strip():
            raise PrologError(f"SWI-Prolog wrote to stderr: {completed.stderr.strip()}")
        try:
            result = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise PrologError(f"Invalid JSON from SWI-Prolog: {completed.stdout!r}") from exc
        self._validate_result(result, catalog_ids)
        return result

    @staticmethod
    def _validate_result(result: Any, catalog_ids: set[str]) -> None:
        if not isinstance(result, dict) or result.get("status") != "ok":
            raise PrologError("Knowledge result must be an ok JSON object")
        decision = result.get("decision")
        if not isinstance(decision, dict):
            raise PrologError("Knowledge result is missing a decision")
        if decision.get("action_type") not in {
            "ask_knowledge", "confirm_knowledge", "explain", "finish_topic"
        }:
            raise PrologError("Unsupported knowledge action")
        if decision.get("topic_id") not in catalog_ids:
            raise PrologError("Knowledge result contains an unknown topic")
        proof = decision.get("proof")
        if not isinstance(proof, dict) or proof.get("rule_id") != decision.get("rule_id"):
            raise PrologError("Knowledge result is missing rule provenance")


def default_knowledge_engine(root: str | Path | None = None) -> KnowledgeGuidanceEngine:
    project = Path(root) if root else Path(__file__).resolve().parents[1]
    return KnowledgeGuidanceEngine(project / "logic" / "knowledge_guidance_rules.pl")
