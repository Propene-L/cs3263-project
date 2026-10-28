"""Independent baselines for active clarification.

These selectors consume the baseline evidence catalog and never read Prolog
proofs or symbolic scores.
"""

from __future__ import annotations

import json
import os
import random
import time
import urllib.error
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
    """Legacy generic JSON endpoint retained for deterministic compatibility tests.

    Real Phase 1.1 execution should use :class:`OpenAIResponsesTransport`, whose
    request and response shapes are provider-specific and validated.
    """

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


class OpenAIResponsesTransport:
    """OpenAI Responses API adapter with Structured Outputs and usage capture."""

    DEFAULT_ENDPOINT = "https://api.openai.com/v1/responses"

    def __init__(
        self,
        api_key: str,
        model: str,
        *,
        endpoint: str = DEFAULT_ENDPOINT,
        timeout_seconds: float = 90,
        max_retries: int = 2,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.endpoint = endpoint
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries

    @classmethod
    def from_environment(cls) -> "OpenAIResponsesTransport | None":
        provider = os.environ.get("CLARIFICATION_LLM_PROVIDER", "openai").lower()
        if provider != "openai":
            return None
        api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get(
            "CLARIFICATION_LLM_API_KEY"
        )
        model = os.environ.get("CLARIFICATION_LLM_MODEL")
        if not api_key or not model:
            return None
        endpoint = os.environ.get(
            "CLARIFICATION_LLM_ENDPOINT", cls.DEFAULT_ENDPOINT
        )
        return cls(api_key, model, endpoint=endpoint)

    @staticmethod
    def _schema() -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "decision": {
                    "type": "string",
                    "enum": ["select_question", "no_valid_question"],
                },
                "option_a_id": {"type": "string"},
                "option_b_id": {"type": "string"},
                "rationale": {"type": "string"},
            },
            "required": [
                "decision",
                "option_a_id",
                "option_b_id",
                "rationale",
            ],
            "additionalProperties": False,
        }

    @staticmethod
    def _output_text(response: dict[str, Any]) -> str:
        texts: list[str] = []
        for item in response.get("output", []):
            if not isinstance(item, dict) or item.get("type") != "message":
                continue
            for content in item.get("content", []):
                if isinstance(content, dict) and content.get("type") == "output_text":
                    text = content.get("text")
                    if isinstance(text, str):
                        texts.append(text)
                if isinstance(content, dict) and content.get("type") == "refusal":
                    raise ValueError(f"OpenAI model refused the request: {content.get('refusal', '')}")
        if not texts:
            raise ValueError("OpenAI response did not contain output_text")
        return "".join(texts)

    def complete_json(self, payload: dict[str, Any]) -> dict[str, Any]:
        body: dict[str, Any] = {
            "model": self.model,
            "store": False,
            "input": [
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "input_text",
                            "text": (
                                "You select a museum clarification question from only the "
                                "supplied evidence. Return the required JSON decision. Missing "
                                "attributes are unknown, not negative facts. Never infer or request "
                                "hidden evaluation information."
                            ),
                        }
                    ],
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": json.dumps(payload, ensure_ascii=False),
                        }
                    ],
                },
            ],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "clarification_decision",
                    "strict": True,
                    "schema": self._schema(),
                }
            },
        }
        request = urllib.request.Request(
            self.endpoint,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        last_error: Exception | None = None
        response: dict[str, Any] | None = None
        for attempt in range(self.max_retries + 1):
            try:
                with urllib.request.urlopen(
                    request, timeout=self.timeout_seconds
                ) as handle:
                    parsed = json.loads(handle.read().decode("utf-8"))
                if not isinstance(parsed, dict):
                    raise ValueError("OpenAI endpoint did not return a JSON object")
                response = parsed
                break
            except urllib.error.HTTPError as exc:
                last_error = exc
                if exc.code not in {408, 409, 429, 500, 502, 503, 504}:
                    raise
            except urllib.error.URLError as exc:
                last_error = exc
            if attempt < self.max_retries:
                time.sleep(2**attempt)
        if response is None:
            raise RuntimeError("OpenAI request failed after retries") from last_error
        if response.get("status") not in {None, "completed"}:
            raise ValueError(f"OpenAI response status was {response.get('status')!r}")
        decision = json.loads(self._output_text(response))
        if not isinstance(decision, dict):
            raise ValueError("OpenAI structured output was not a JSON object")
        decision["_transport_metadata"] = {
            "provider": "openai",
            "model_requested": self.model,
            "model_returned": response.get("model"),
            "response_id": response.get("id"),
            "usage": response.get("usage", {}),
        }
        decision["_raw_response"] = response
        return decision


class DirectLLMSelector:
    """Direct selector with strict post-validation and a mockable transport."""

    def __init__(self, transport: LLMTransport, evidence: dict[str, Any]) -> None:
        self.transport = transport
        self.evidence = evidence
        self.hypotheses = {item["id"]: item for item in evidence["hypotheses"]}
        self.last_record: dict[str, Any] | None = None

    def select(
        self,
        state: ClarificationState,
        active_hypothesis_ids: list[str],
        scenario_text: str = "",
        track: str = "structured",
    ) -> BaselineQuestion | None:
        if track not in {"structured", "natural_language"}:
            raise ValueError(f"Unsupported direct-LLM track: {track}")
        eligible = eligible_artworks(state)
        if len(eligible) < 2:
            self.last_record = {"decision": "no_valid_question", "reason": "fewer_than_two_eligible"}
            return None
        payload = {
            "task": (
                "Select two eligible artwork IDs whose pairwise preference response best "
                "distinguishes the active visitor-interest hypotheses, or return "
                "no_valid_question when no discriminative pair is supported."
            ),
            "evaluation_track": track,
            "visitor_scenario": scenario_text if track == "natural_language" else "",
            "validated_observations": (
                [
                    {"id": item.id, "kind": item.kind, "object_id": item.object_id}
                    for item in state.observations
                ]
                if track == "structured"
                else []
            ),
            "active_hypotheses": [
                self.hypotheses[item]
                for item in active_hypothesis_ids
                if item in self.hypotheses
            ],
            "allowed_responses": ["prefer_a", "prefer_b", "neither", "unsure"],
            "response_model": {
                "prefer_a": "A has recorded positive support and B does not.",
                "prefer_b": "B has recorded positive support and A does not.",
                "unknown": "Both or neither have recorded support; missing support is not absence.",
                "state_update": (
                    "Only a determinate opposite prediction is eliminated; unsure, neither, "
                    "and unknown predictions eliminate nothing."
                ),
            },
            "eligible_artwork_ids": eligible,
            "museum_evidence": {
                artwork_id: self.evidence["artworks"][artwork_id]
                for artwork_id in eligible
            },
            "session_constraints": {
                "allowed_artwork_ids": list(state.allowed_artwork_ids),
                "excluded_by_observation": sorted(
                    set(state.allowed_artwork_ids) - set(eligible)
                ),
                "previous_questions": [
                    {
                        "question_id": item.id,
                        "option_a_id": item.option_a_id,
                        "option_b_id": item.option_b_id,
                        "response": item.response,
                    }
                    for item in state.asked_questions
                ],
            },
            "selection_policy": (
                "Prefer more opposing determinate hypothesis predictions, then a balanced "
                "prefer_a/prefer_b split, fewer unknown predictions, and stable artwork IDs."
            ),
            "required_output": {
                "decision": "select_question | no_valid_question",
                "option_a_id": "eligible ag_* ID or empty string",
                "option_b_id": "eligible ag_* ID or empty string",
                "rationale": "brief evidence-based explanation",
            },
        }
        result = self.transport.complete_json(payload)
        self.last_record = {
            "request": payload,
            "validated_decision": {
                key: result.get(key)
                for key in ("decision", "option_a_id", "option_b_id", "rationale")
            },
            "transport_metadata": result.get("_transport_metadata", {}),
            "raw_response": result.get("_raw_response", result),
        }
        decision = result.get("decision", "select_question")
        if decision == "no_valid_question":
            return None
        if decision != "select_question":
            raise ValueError("Direct LLM returned an unsupported decision")
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
            {
                "rationale": result.get("rationale", ""),
                "executed": True,
                "transport": result.get("_transport_metadata", {}),
            },
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
