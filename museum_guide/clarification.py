"""Safe orchestration for the SWI-Prolog active-clarification engine."""

from __future__ import annotations

import json
import subprocess
import tempfile
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Literal

from .prolog_bridge import SAFE_ID, PrologError, find_swipl


ObservationKind = Literal[
    "knows", "likes", "dislikes", "viewed", "rejected", "explicit_interest"
]
PreferenceResponse = Literal["prefer_a", "prefer_b", "neither", "unsure"]


@dataclass(frozen=True, slots=True)
class ClarificationObservation:
    id: str
    kind: ObservationKind
    object_id: str


@dataclass(frozen=True, slots=True)
class AskedQuestion:
    id: str
    option_a_id: str
    option_b_id: str
    response_observation_id: str | None = None
    response: PreferenceResponse | None = None


@dataclass(frozen=True, slots=True)
class ClarificationState:
    session_id: str
    observations: tuple[ClarificationObservation, ...]
    allowed_artwork_ids: tuple[str, ...]
    asked_questions: tuple[AskedQuestion, ...] = ()
    rejected_hypothesis_ids: tuple[str, ...] = ()
    mode: Literal["single_rule", "compositional"] = "compositional"

    def apply_response(
        self,
        question: dict[str, Any],
        response: PreferenceResponse,
        observation_id: str,
    ) -> "ClarificationState":
        """Return corrected current state; a repeated question ID replaces its response."""

        if response not in {"prefer_a", "prefer_b", "neither", "unsure"}:
            raise ValueError(f"Unsupported response: {response}")
        asked = AskedQuestion(
            id=question["question_id"],
            option_a_id=question["option_a"]["artwork_id"],
            option_b_id=question["option_b"]["artwork_id"],
            response_observation_id=observation_id,
            response=response,
        )
        remaining = tuple(item for item in self.asked_questions if item.id != asked.id)
        return replace(self, asked_questions=remaining + (asked,))


def _validate_atom(value: str, field: str) -> str:
    if not SAFE_ID.fullmatch(value):
        raise PrologError(f"Unsafe {field}: {value!r}")
    return value


def _state_prolog(state: ClarificationState) -> str:
    session = _validate_atom(state.session_id, "session ID")
    lines = [
        ":- dynamic visitor_observation/4.",
        ":- dynamic allowed_artwork/1.",
        ":- dynamic asked_question/4.",
        ":- dynamic question_response/4.",
        ":- dynamic hypothesis_status/3.",
        ":- dynamic clarification_mode/2.",
        ":- discontiguous asked_question/4.",
        ":- discontiguous question_response/4.",
        f"clarification_mode({session}, {_validate_atom(state.mode, 'mode')}).",
    ]
    for artwork_id in sorted(set(state.allowed_artwork_ids)):
        lines.append(f"allowed_artwork({_validate_atom(artwork_id, 'artwork ID')}).")
    for observation in state.observations:
        lines.append(
            "visitor_observation("
            f"{_validate_atom(observation.id, 'observation ID')}, "
            f"{session}, {_validate_atom(observation.kind, 'observation kind')}, "
            f"{_validate_atom(observation.object_id, 'observation object')})."
        )
    for hypothesis_id in sorted(set(state.rejected_hypothesis_ids)):
        lines.append(
            f"hypothesis_status({session}, "
            f"{_validate_atom(hypothesis_id, 'hypothesis ID')}, rejected)."
        )
    for question in state.asked_questions:
        question_id = _validate_atom(question.id, "question ID")
        lines.append(
            f"asked_question({question_id}, {session}, "
            f"{_validate_atom(question.option_a_id, 'option A')}, "
            f"{_validate_atom(question.option_b_id, 'option B')})."
        )
        if question.response is not None and question.response_observation_id is not None:
            lines.append(
                "question_response("
                f"{_validate_atom(question.response_observation_id, 'response observation ID')}, "
                f"{session}, {question_id}, "
                f"{_validate_atom(question.response, 'response')})."
            )
    return "\n".join(lines) + "\n"


class ClarificationEngine:
    """Stateless SWI-Prolog bridge. Every call uses a fresh process."""

    def __init__(
        self,
        *,
        facts_path: str | Path,
        hypotheses_path: str | Path,
        rules_path: str | Path,
        swipl_path: str | Path | None = None,
        timeout_seconds: float = 20,
    ) -> None:
        self.facts_path = Path(facts_path).resolve()
        self.hypotheses_path = Path(hypotheses_path).resolve()
        self.rules_path = Path(rules_path).resolve()
        executable = Path(swipl_path) if swipl_path else find_swipl()
        if executable is None:
            raise PrologError("SWI-Prolog executable not found; set SWIPL_PATH")
        self.swipl_path = executable
        self.timeout_seconds = timeout_seconds
        self.runtime_directory = self.rules_path.parents[1] / ".runtime"

    def clarify(self, state: ClarificationState) -> dict[str, Any]:
        for path in (self.facts_path, self.hypotheses_path, self.rules_path):
            if not path.is_file():
                raise PrologError(f"Missing Prolog input: {path}")
        session = _validate_atom(state.session_id, "session ID")
        self.runtime_directory.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(
            prefix="museum-clarification-", dir=self.runtime_directory
        ) as directory:
            state_path = Path(directory) / "validated_state.pl"
            state_path.write_text(_state_prolog(state), encoding="utf-8")
            command = [
                str(self.swipl_path),
                "-q",
                "-s",
                str(self.facts_path),
                "-s",
                str(self.hypotheses_path),
                "-s",
                str(state_path),
                "-s",
                str(self.rules_path),
                "-g",
                f"write_clarification_json({session})",
                "-t",
                "halt",
            ]
            try:
                completed = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout_seconds,
                    check=False,
                )
            except subprocess.TimeoutExpired as exc:
                raise PrologError(
                    f"SWI-Prolog timed out after {self.timeout_seconds}s"
                ) from exc
        if completed.returncode != 0:
            raise PrologError(
                f"SWI-Prolog exited {completed.returncode}: {completed.stderr.strip()}"
            )
        if completed.stderr.strip():
            raise PrologError(f"SWI-Prolog wrote to stderr: {completed.stderr.strip()}")
        try:
            result = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise PrologError(
                f"Invalid JSON from SWI-Prolog: {completed.stdout!r}"
            ) from exc
        self._validate_result(result, state)
        return result

    @staticmethod
    def _validate_result(result: Any, state: ClarificationState) -> None:
        if not isinstance(result, dict):
            raise PrologError("Clarification result must be a JSON object")
        if result.get("status") not in {"selected", "no_discriminative_question"}:
            raise PrologError(f"Unexpected clarification status: {result.get('status')!r}")
        question = result.get("question")
        if result["status"] == "selected":
            if not isinstance(question, dict):
                raise PrologError("Selected result is missing a question")
            allowed = set(state.allowed_artwork_ids)
            option_ids = {
                question.get("option_a", {}).get("artwork_id"),
                question.get("option_b", {}).get("artwork_id"),
            }
            if None in option_ids or not option_ids <= allowed:
                raise PrologError("Prolog returned an artwork outside the allowlist")
            proof = question.get("proof")
            if not isinstance(proof, dict) or not proof.get("children"):
                raise PrologError("Selected question is missing its proof tree")


def default_engine(root: str | Path | None = None) -> ClarificationEngine:
    project = Path(root) if root else Path(__file__).resolve().parents[1]
    return ClarificationEngine(
        facts_path=project / "logic" / "clarification_generated_facts.pl",
        hypotheses_path=project / "logic" / "clarification_hypotheses.pl",
        rules_path=project / "logic" / "clarification_rules.pl",
    )
