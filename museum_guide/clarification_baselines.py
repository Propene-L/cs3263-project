"""Independent baselines for active clarification.

These selectors consume the baseline evidence catalog and never read Prolog
proofs or symbolic scores.
"""

from __future__ import annotations

import json
import os
import random
import urllib.request
from dataclasses import dataclass
from typing import Any, Protocol

from .clarification import ClarificationState


@dataclass(frozen=True, slots=True)
class BaselineQuestion:
    method: str
    option_a_id: str
    option_b_id: str
    score: float | None
    metadata: dict[str, Any]


def eligible_artworks(state: ClarificationState) -> list[str]:
    excluded = {
        observation.object_id
        for observation in state.observations
        if observation.kind in {"knows", "likes", "dislikes", "viewed", "rejected"}
    }
    for question in state.asked_questions:
        excluded.update((question.option_a_id, question.option_b_id))
    return sorted(set(state.allowed_artwork_ids) - excluded)


class RandomPairSelector:
    def __init__(self, seed: int = 3263) -> None:
        self.seed = seed

    def select(self, state: ClarificationState) -> BaselineQuestion | None:
        eligible = eligible_artworks(state)
        if len(eligible) < 2:
            return None
        generator = random.Random(f"{self.seed}:{state.session_id}:{len(state.asked_questions)}")
        option_a, option_b = sorted(generator.sample(eligible, 2))
        return BaselineQuestion(
            "random_eligible",
            option_a,
            option_b,
            None,
            {"seed": self.seed},
        )


class AttributeContrastSelector:
    """Simple one-step baseline maximizing raw active-hypothesis contrast."""

    def __init__(self, evidence: dict[str, Any]) -> None:
        self.evidence = evidence
        self.hypotheses = {
            item["id"]: (item["attribute_type"], item["value_id"])
            for item in evidence["hypotheses"]
        }
        self.attributes = {
            artwork_id: {
                (attribute["type"], attribute["value_id"])
                for attribute in record["attributes"]
            }
            for artwork_id, record in evidence["artworks"].items()
        }

    def select(
        self, state: ClarificationState, active_hypothesis_ids: list[str]
    ) -> BaselineQuestion | None:
        eligible = eligible_artworks(state)
        best: tuple[int, str, str] | None = None
        for index, option_a in enumerate(eligible):
            for option_b in eligible[index + 1 :]:
                contrast = 0
                for hypothesis_id in active_hypothesis_ids:
                    attribute = self.hypotheses.get(hypothesis_id)
                    if attribute is None:
                        continue
                    support_a = attribute in self.attributes.get(option_a, set())
                    support_b = attribute in self.attributes.get(option_b, set())
                    contrast += int(support_a != support_b)
                candidate = (contrast, option_a, option_b)
                if contrast and (best is None or (-contrast, option_a, option_b) < (-best[0], best[1], best[2])):
                    best = candidate
        if best is None:
            return None
        return BaselineQuestion(
            "raw_attribute_contrast",
            best[1],
            best[2],
            float(best[0]),
            {"active_hypothesis_ids": active_hypothesis_ids},
        )


class LLMTransport(Protocol):
    def complete_json(self, payload: dict[str, Any]) -> dict[str, Any]: ...


class HTTPJSONLLMTransport:
    """Optional configured JSON endpoint; no credentials are stored in-repo."""

    def __init__(self, endpoint: str, api_key: str, model: str) -> None:
        self.endpoint = endpoint
        self.api_key = api_key
        self.model = model

    @classmethod
    def from_environment(cls) -> "HTTPJSONLLMTransport | None":
        endpoint = os.environ.get("CLARIFICATION_LLM_ENDPOINT")
        api_key = os.environ.get("CLARIFICATION_LLM_API_KEY")
        model = os.environ.get("CLARIFICATION_LLM_MODEL")
        if not endpoint or not api_key or not model:
            return None
        return cls(endpoint, api_key, model)

    def complete_json(self, payload: dict[str, Any]) -> dict[str, Any]:
        request = urllib.request.Request(
            self.endpoint,
            data=json.dumps({"model": self.model, "input": payload}).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            result = json.loads(response.read().decode("utf-8"))
        if not isinstance(result, dict):
            raise ValueError("LLM endpoint did not return a JSON object")
        return result


class DirectLLMSelector:
    """Direct selector with strict post-validation and a mockable transport."""

    def __init__(self, transport: LLMTransport, evidence: dict[str, Any]) -> None:
        self.transport = transport
        self.evidence = evidence

    def select(
        self,
        state: ClarificationState,
        active_hypothesis_ids: list[str],
        scenario_text: str = "",
    ) -> BaselineQuestion | None:
        eligible = eligible_artworks(state)
        if len(eligible) < 2:
            return None
        payload = {
            "task": "Select two artwork IDs for the next pairwise preference clarification question.",
            "visitor_scenario": scenario_text,
            "allowed_responses": ["prefer_a", "prefer_b", "neither", "unsure"],
            "active_hypothesis_ids": active_hypothesis_ids,
            "eligible_artwork_ids": eligible,
            "museum_evidence": {
                artwork_id: self.evidence["artworks"][artwork_id]
                for artwork_id in eligible
            },
            "required_output": {"option_a_id": "ag_*", "option_b_id": "ag_*", "rationale": "string"},
        }
        result = self.transport.complete_json(payload)
        option_a = result.get("option_a_id")
        option_b = result.get("option_b_id")
        if option_a == option_b or option_a not in eligible or option_b not in eligible:
            raise ValueError("Direct LLM returned invalid or non-allowlisted options")
        option_a, option_b = sorted((option_a, option_b))
        return BaselineQuestion(
            "direct_llm",
            option_a,
            option_b,
            None,
            {"rationale": result.get("rationale", ""), "executed": True},
        )


class ValidatedLLMObservationExtractor:
    """Optional LLM-to-Prolog adapter; it may propose state but never a pair."""

    def __init__(self, transport: LLMTransport) -> None:
        self.transport = transport

    def extract(
        self,
        visitor_text: str,
        *,
        allowed_artwork_ids: set[str],
        allowed_hypothesis_ids: set[str],
    ) -> tuple[dict[str, str], ...]:
        payload = {
            "task": "Extract validated museum visitor observations. Do not select a question or recommendation.",
            "visitor_text": visitor_text,
            "allowed_artwork_ids": sorted(allowed_artwork_ids),
            "allowed_hypothesis_ids": sorted(allowed_hypothesis_ids),
            "allowed_kinds": [
                "knows",
                "likes",
                "dislikes",
                "viewed",
                "rejected",
                "explicit_interest",
            ],
            "required_output": {
                "observations": [
                    {"id": "obs_*", "kind": "allowed kind", "object_id": "allowlisted ID"}
                ]
            },
        }
        result = self.transport.complete_json(payload)
        observations = result.get("observations")
        if not isinstance(observations, list):
            raise ValueError("LLM extractor did not return an observations list")
        validated: list[dict[str, str]] = []
        allowed_kinds = {
            "knows",
            "likes",
            "dislikes",
            "viewed",
            "rejected",
            "explicit_interest",
        }
        for item in observations:
            if not isinstance(item, dict):
                raise ValueError("LLM observation must be an object")
            identifier = item.get("id")
            kind = item.get("kind")
            object_id = item.get("object_id")
            if not isinstance(identifier, str) or not identifier.startswith("obs_"):
                raise ValueError("LLM observation has an invalid ID")
            if kind not in allowed_kinds:
                raise ValueError("LLM observation has an invalid kind")
            allowed_objects = (
                allowed_hypothesis_ids
                if kind == "explicit_interest"
                else allowed_artwork_ids
            )
            if object_id not in allowed_objects:
                raise ValueError("LLM observation object is outside the allowlist")
            validated.append({"id": identifier, "kind": kind, "object_id": object_id})
        return tuple(validated)
