"""Independent Phase 1.2 visitor-state construction baselines."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Protocol

from .clarification_baselines import OpenAIResponsesTransport
from .preference_state import PreferenceState


@dataclass(frozen=True, slots=True)
class PreferenceMethodResult:
    method: str
    preference_explanations: list[dict[str, Any]]
    ranked_actions: list[dict[str, Any]]
    metadata: dict[str, Any]


class PreferenceEvidenceIndex:
    def __init__(self, evidence: dict[str, Any]) -> None:
        self.evidence = evidence
        self.hypothesis_rows = {item["id"]: item for item in evidence["hypotheses"]}
        self.definitions = {
            (item["attribute_type"], item["value_id"]): item["id"]
            for item in evidence["hypotheses"]
        }
        self.supports: dict[str, set[str]] = {}
        self.fact_ids: dict[tuple[str, str], list[str]] = {}
        for artwork_id, record in evidence["artworks"].items():
            supported: set[str] = set()
            for attribute in record["attributes"]:
                hypothesis = self.definitions.get(
                    (attribute["type"], attribute["value_id"])
                )
                if hypothesis is None:
                    continue
                supported.add(hypothesis)
                self.fact_ids[(artwork_id, hypothesis)] = list(attribute["fact_ids"])
            self.supports[artwork_id] = supported

    def ranked_action(
        self, artwork_id: str, score: float, components: list[str]
    ) -> dict[str, Any]:
        return {
            "artwork_id": artwork_id,
            "label": self.evidence["artworks"][artwork_id]["label"],
            "score": score,
            "supported_components": components,
            "artgraph_fact_ids": sorted(
                {
                    fact
                    for hypothesis in components
                    for fact in self.fact_ids.get((artwork_id, hypothesis), [])
                }
            ),
        }


class PositiveAccumulationBaseline:
    """Naive content matching: union attributes from liked artworks only."""

    method = "positive_attribute_accumulation"

    def __init__(self, evidence: dict[str, Any]) -> None:
        self.index = PreferenceEvidenceIndex(evidence)

    def infer(self, state: PreferenceState) -> PreferenceMethodResult:
        liked = [item for item in state.observations if item.kind == "likes"]
        counts = {hypothesis: 0 for hypothesis in self.index.hypothesis_rows}
        observation_ids: dict[str, list[str]] = {
            hypothesis: [] for hypothesis in self.index.hypothesis_rows
        }
        for observation in liked:
            for hypothesis in self.index.supports.get(observation.object_id, set()):
                counts[hypothesis] += 1
                observation_ids[hypothesis].append(observation.id)
        active = sorted(item for item, count in counts.items() if count > 0)
        explanations = [
            {
                "kind": "atomic",
                "components": [hypothesis],
                "status": "reinforced" if counts[hypothesis] >= 2 else "candidate",
                "proof": {
                    "rule_id": "baseline_like_attribute_accumulation",
                    "observation_ids": sorted(observation_ids[hypothesis]),
                },
            }
            for hypothesis in active
        ]
        actions = []
        for artwork_id in state.allowed_action_artwork_ids:
            components = sorted(self.index.supports.get(artwork_id, set()) & set(active))
            actions.append(self.index.ranked_action(artwork_id, len(components), components))
        actions.sort(key=lambda item: (-item["score"], item["artwork_id"]))
        return PreferenceMethodResult(self.method, explanations, actions, {})


class SignedAdditiveAtomicBaseline:
    """Atomic liked-count minus disliked-count state and candidate score."""

    method = "signed_additive_atomic"

    def __init__(self, evidence: dict[str, Any]) -> None:
        self.index = PreferenceEvidenceIndex(evidence)

    def infer(self, state: PreferenceState) -> PreferenceMethodResult:
        weights = {hypothesis: 0 for hypothesis in self.index.hypothesis_rows}
        evidence_rows: dict[str, list[str]] = {
            hypothesis: [] for hypothesis in self.index.hypothesis_rows
        }
        for observation in state.observations:
            if observation.kind not in {"likes", "dislikes"}:
                continue
            delta = 1 if observation.kind == "likes" else -1
            for hypothesis in self.index.supports.get(observation.object_id, set()):
                weights[hypothesis] += delta
                evidence_rows[hypothesis].append(observation.id)
        explanations = [
            {
                "kind": "atomic",
                "components": [hypothesis],
                "status": "candidate",
                "weight": weight,
                "proof": {
                    "rule_id": "baseline_signed_atomic_weight",
                    "observation_ids": sorted(evidence_rows[hypothesis]),
                },
            }
            for hypothesis, weight in sorted(weights.items())
            if weight > 0
        ]
        actions = []
        for artwork_id in state.allowed_action_artwork_ids:
            supported = sorted(self.index.supports.get(artwork_id, set()))
            score = sum(weights[hypothesis] for hypothesis in supported)
            nonzero = [hypothesis for hypothesis in supported if weights[hypothesis] != 0]
            actions.append(self.index.ranked_action(artwork_id, score, nonzero))
        actions.sort(key=lambda item: (-item["score"], item["artwork_id"]))
        return PreferenceMethodResult(
            self.method,
            explanations,
            actions,
            {"atomic_weights": weights},
        )


class PreferenceLLMTransport(Protocol):
    def complete_json(self, payload: dict[str, Any]) -> dict[str, Any]: ...


class DirectPreferenceStateLLM:
    """Direct model infers visitor state and next action without symbolic output."""

    method = "direct_llm_state_reasoning"

    OUTPUT_SCHEMA = {
        "type": "object",
        "properties": {
            "inferred_preferences": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "kind": {"type": "string", "enum": ["atomic", "all_of"]},
                        "components": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["kind", "components"],
                    "additionalProperties": False,
                },
            },
            "next_action_type": {
                "type": "string",
                "enum": ["clarify", "recommend"],
            },
            "artwork_id": {"type": "string"},
            "rationale": {"type": "string"},
        },
        "required": [
            "inferred_preferences",
            "next_action_type",
            "artwork_id",
            "rationale",
        ],
        "additionalProperties": False,
    }

    def __init__(self, transport: PreferenceLLMTransport, evidence: dict[str, Any]) -> None:
        self.transport = transport
        self.index = PreferenceEvidenceIndex(evidence)
        self.last_record: dict[str, Any] | None = None

    @classmethod
    def from_environment(
        cls, evidence: dict[str, Any]
    ) -> "DirectPreferenceStateLLM | None":
        provider = os.environ.get("PREFERENCE_STATE_LLM_PROVIDER", "openai").lower()
        api_key = os.environ.get("OPENAI_API_KEY")
        model = os.environ.get("PREFERENCE_STATE_LLM_MODEL")
        if provider != "openai" or not api_key or not model:
            return None
        endpoint = os.environ.get(
            "PREFERENCE_STATE_LLM_ENDPOINT",
            OpenAIResponsesTransport.DEFAULT_ENDPOINT,
        )
        transport = OpenAIResponsesTransport(
            api_key,
            model,
            endpoint=endpoint,
            output_schema=cls.OUTPUT_SCHEMA,
            schema_name="preference_state_decision",
            system_prompt=(
                "Infer a provisional museum visitor preference explanation and choose "
                "one next action using only the supplied history and recorded facts. "
                "Missing attributes are unknown, not negative facts. Return JSON only."
            ),
        )
        return cls(transport, evidence)

    def infer(
        self, state: PreferenceState, *, natural_language_history: str
    ) -> PreferenceMethodResult:
        candidates = list(state.allowed_action_artwork_ids)
        observed_ids = [
            item.object_id
            for item in state.observations
            if item.kind in {"likes", "dislikes"}
        ]
        relevant_artworks = sorted(set(candidates + observed_ids))
        payload = {
            "task": (
                "Infer provisional atomic or conjunction preferences from the visitor "
                "history, then choose one clarification or recommendation action."
            ),
            "visitor_history": natural_language_history,
            "hypothesis_vocabulary": list(self.index.hypothesis_rows.values()),
            "candidate_artwork_ids": candidates,
            "artwork_evidence": {
                artwork_id: self.index.evidence["artworks"][artwork_id]
                for artwork_id in relevant_artworks
            },
            "missing_support_policy": "not_recorded, never factual absence",
            "required_output": {
                "inferred_preferences": [
                    {"kind": "atomic | all_of", "components": ["h_*"]}
                ],
                "next_action_type": "clarify | recommend",
                "artwork_id": "candidate ag_*",
                "rationale": "string",
            },
        }
        result = self.transport.complete_json(payload)
        explanations = result.get("inferred_preferences")
        artwork_id = result.get("artwork_id")
        if not isinstance(explanations, list):
            raise ValueError("Direct LLM did not return inferred_preferences")
        validated: list[dict[str, Any]] = []
        for explanation in explanations:
            if not isinstance(explanation, dict) or explanation.get("kind") not in {
                "atomic",
                "all_of",
            }:
                raise ValueError("Direct LLM returned an invalid preference explanation")
            components = explanation.get("components")
            if not isinstance(components, list) or not components:
                raise ValueError("Direct LLM explanation has no components")
            if any(item not in self.index.hypothesis_rows for item in components):
                raise ValueError("Direct LLM returned a hypothesis outside the allowlist")
            validated.append(
                {
                    "kind": explanation["kind"],
                    "components": components,
                    "status": "model_inferred",
                }
            )
        if artwork_id not in candidates:
            raise ValueError("Direct LLM returned an artwork outside the candidate allowlist")
        action = self.index.ranked_action(artwork_id, 1.0, [])
        action["next_action_type"] = result.get("next_action_type")
        action["rationale"] = result.get("rationale", "")
        self.last_record = {
            "request": payload,
            "raw_response": result.get("_raw_response", result),
            "transport_metadata": result.get("_transport_metadata", {}),
            "validated_result": {
                "inferred_preferences": validated,
                "next_action_type": result.get("next_action_type"),
                "artwork_id": artwork_id,
            },
        }
        return PreferenceMethodResult(
            self.method,
            validated,
            [action],
            {"llm_record": self.last_record},
        )
