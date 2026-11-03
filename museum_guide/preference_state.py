"""Safe Python orchestration for Phase 1.2 visitor-state reasoning."""

from __future__ import annotations

import json
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from .prolog_bridge import SAFE_ID, PrologError, find_swipl


PreferenceObservationKind = Literal[
    "likes", "dislikes", "explicit_interest", "explicit_rejection",
    "explicit_conjunction", "reject_conjunction", "reject_atomic_explanation", "reject_pair_explanation"
]
PreferenceStateMode = Literal["atomic", "compositional"]


@dataclass(frozen=True, slots=True)
class PreferenceObservation:
    id: str
    kind: PreferenceObservationKind
    object_id: str
    components: tuple[str, ...] = ()
    supersedes: str | None = None


@dataclass(frozen=True, slots=True)
class PreferenceState:
    session_id: str
    observations: tuple[PreferenceObservation, ...]
    allowed_action_artwork_ids: tuple[str, ...]
    mode: PreferenceStateMode = "compositional"
    hidden_fact_ids: tuple[str, ...] = ()
    evidence_incomplete: bool = False


def _validate_atom(value: str, field: str) -> str:
    if not SAFE_ID.fullmatch(value):
        raise PrologError(f"Unsafe {field}: {value!r}")
    return value


def _state_prolog(state: PreferenceState) -> str:
    visitor = _validate_atom(state.session_id, "session ID")
    mode = _validate_atom(state.mode, "preference-state mode")
    lines = [
        ":- dynamic preference_observation/4.",
        ":- dynamic allowed_action_artwork/1.",
        ":- dynamic preference_state_mode/2.",
        ":- dynamic observation_order/2.",
        ":- dynamic observation_components/2.",
        ":- dynamic superseded_observation/1.",
        ":- dynamic hidden_fact/1.",
        ":- dynamic incomplete_evidence/0.",
        ":- discontiguous preference_observation/4, observation_order/2, observation_components/2, superseded_observation/1.",
        f"preference_state_mode({visitor}, {mode}).",
    ]
    for artwork_id in sorted(set(state.allowed_action_artwork_ids)):
        lines.append(
            f"allowed_action_artwork({_validate_atom(artwork_id, 'action artwork ID')})."
        )
    for position, observation in enumerate(state.observations):
        lines.append(f"observation_order({observation.id}, {position}).")
        if observation.components:
            lines.append(
                f"observation_components({observation.id}, [{','.join(sorted(observation.components))}])."
            )
        if observation.supersedes:
            lines.append(f"superseded_observation({observation.supersedes}).")
        lines.append(
            "preference_observation("
            f"{_validate_atom(observation.id, 'observation ID')}, "
            f"{visitor}, {_validate_atom(observation.kind, 'observation kind')}, "
            f"{_validate_atom(observation.object_id, 'observation object')})."
        )
    lines.extend(f"hidden_fact({fact})." for fact in state.hidden_fact_ids)
    if state.evidence_incomplete or state.hidden_fact_ids:
        lines.append("incomplete_evidence.")
    return "\n".join(lines) + "\n"


def validate_state(state: PreferenceState, evidence: dict[str, Any]) -> None:
    """Validate identifiers and chronological corrections before serialization."""
    _validate_atom(state.session_id, "session ID")
    if state.mode not in {"atomic", "compositional"}:
        raise PrologError("Unsupported preference-state mode")
    hypotheses = {item["id"] for item in evidence["hypotheses"]}
    artworks = set(evidence["artworks"])
    known_facts = {f for a in evidence["artworks"].values() for x in a["attributes"] for f in x["fact_ids"]}
    if not set(state.allowed_action_artwork_ids) <= artworks:
        raise PrologError("Unknown action artwork ID")
    if not set(state.hidden_fact_ids) <= known_facts:
        raise PrologError("Unknown hidden fact ID")
    seen: set[str] = set()
    for observation in state.observations:
        _validate_atom(observation.id, "observation ID")
        if observation.id in seen:
            raise PrologError("Duplicate observation ID")
        if observation.supersedes and observation.supersedes not in seen:
            raise PrologError("Correction must supersede an earlier observation")
        seen.add(observation.id)
        if observation.kind in {"likes", "dislikes"}:
            valid = observation.object_id in artworks and not observation.components
        elif observation.kind in {"explicit_interest", "explicit_rejection", "reject_atomic_explanation"}:
            valid = observation.object_id in hypotheses and not observation.components
        elif observation.kind in {"explicit_conjunction", "reject_conjunction", "reject_pair_explanation"}:
            valid = (len(observation.components) == 2 and len(set(observation.components)) == 2
                     and set(observation.components) <= hypotheses
                     and observation.object_id == "preference_pair")
        else:
            valid = False
        if not valid:
            raise PrologError("Invalid observation kind, object, or components")


class PreferenceStateEngine:
    """Invoke a fresh SWI-Prolog process for each visitor-state solve."""

    def __init__(
        self,
        *,
        facts_path: str | Path,
        hypotheses_path: str | Path,
        rules_path: str | Path,
        swipl_path: str | Path | None = None,
        timeout_seconds: float = 20,
        entry_point: str = "write_preference_state_json",
    ) -> None:
        self.facts_path = Path(facts_path).resolve()
        self.hypotheses_path = Path(hypotheses_path).resolve()
        self.rules_path = Path(rules_path).resolve()
        executable = Path(swipl_path) if swipl_path else find_swipl()
        if executable is None:
            raise PrologError("SWI-Prolog executable not found; set SWIPL_PATH")
        self.swipl_path = executable
        self.timeout_seconds = timeout_seconds
        self.entry_point = entry_point
        self.runtime_directory = self.rules_path.parents[1] / ".runtime"

    def infer(self, state: PreferenceState) -> dict[str, Any]:
        evidence = json.loads(
            (self.rules_path.parents[1] / "data/curated/clarification_evidence.json")
            .read_text(encoding="utf-8")
        )
        validate_state(state, evidence)
        for path in (self.facts_path, self.hypotheses_path, self.rules_path):
            if not path.is_file():
                raise PrologError(f"Missing Prolog input: {path}")
        visitor = _validate_atom(state.session_id, "session ID")
        self.runtime_directory.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(
            prefix="museum-preference-state-", dir=self.runtime_directory
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
                f"{self.entry_point}({visitor})",
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
    def _validate_result(result: Any, state: PreferenceState) -> None:
        if not isinstance(result, dict) or result.get("status") != "ok":
            raise PrologError("Preference-state result must be an ok JSON object")
        explanations = result.get("preference_explanations")
        actions = result.get("ranked_actions")
        if not isinstance(explanations, list) or not isinstance(actions, list):
            raise PrologError("Preference-state output is missing explanations or actions")
        for explanation in explanations:
            if explanation.get("kind") not in {"atomic", "all_of"}:
                raise PrologError("Unsupported preference explanation kind")
            components = explanation.get("components")
            if not isinstance(components, list) or not components:
                raise PrologError("Preference explanation has no components")
            for component in components:
                _validate_atom(component, "preference component")
            proof = explanation.get("proof")
            if not isinstance(proof, dict) or not proof.get("rule_id"):
                raise PrologError("Preference explanation is missing proof provenance")
        allowed = set(state.allowed_action_artwork_ids)
        for action in actions:
            if action.get("artwork_id") not in allowed:
                raise PrologError("Prolog returned an action outside the allowlist")
            if not isinstance(action.get("proof"), dict):
                raise PrologError("Ranked action is missing proof provenance")


def default_preference_state_engine(
    root: str | Path | None = None,
    *, historical: bool = False,
) -> PreferenceStateEngine:
    project = Path(root) if root else Path(__file__).resolve().parents[1]
    return PreferenceStateEngine(
        facts_path=project / "logic" / "clarification_generated_facts.pl",
        hypotheses_path=project / "logic" / "clarification_hypotheses.pl",
        rules_path=project / "logic" / (
            "preference_state_rules.pl" if historical else "preference_state_corrected_rules.pl"
        ),
        entry_point=("write_preference_state_json" if historical else "write_corrected_preference_state_json"),
    )
