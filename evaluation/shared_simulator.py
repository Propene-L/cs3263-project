"""Method-independent clarification response and state-transition semantics.

This module is an evaluation oracle over the declared positive-support model.
It does not read Prolog output, proof trees, rankings, or gold selections.
Missing RDF support always maps to ``unknown``; it is never treated as a
negative museum fact.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Literal, Sequence


Prediction = Literal["prefer_a", "prefer_b", "unknown"]
Response = Literal["prefer_a", "prefer_b", "neither", "unsure"]


@dataclass(frozen=True, slots=True)
class Transition:
    before: tuple[str, ...]
    response: Response
    eliminated: tuple[str, ...]
    after: tuple[str, ...]


class EvidenceModel:
    """Independent view of the exported, provenance-bearing evidence catalog."""

    def __init__(self, evidence: dict[str, Any]) -> None:
        self.evidence = evidence
        self.hypotheses = {
            item["id"]: item for item in evidence["hypotheses"]
        }
        self.definitions = {
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

    def prediction(self, hypothesis_id: str, option_a: str, option_b: str) -> Prediction:
        attribute = self.definitions[hypothesis_id]
        support_a = attribute in self.attributes.get(option_a, set())
        support_b = attribute in self.attributes.get(option_b, set())
        if support_a and not support_b:
            return "prefer_a"
        if support_b and not support_a:
            return "prefer_b"
        return "unknown"

    def partition(
        self, hypothesis_ids: Sequence[str], option_a: str, option_b: str
    ) -> dict[str, list[str]]:
        partition = {"prefer_a": [], "prefer_b": [], "unknown": []}
        for hypothesis_id in hypothesis_ids:
            partition[self.prediction(hypothesis_id, option_a, option_b)].append(
                hypothesis_id
            )
        return partition

    def statistics(
        self, hypothesis_ids: Sequence[str], option_a: str, option_b: str
    ) -> dict[str, Any]:
        partition = self.partition(hypothesis_ids, option_a, option_b)
        prefer_a = len(partition["prefer_a"])
        prefer_b = len(partition["prefer_b"])
        unknown = len(partition["unknown"])
        distinguished = prefer_a * prefer_b
        imbalance = abs(prefer_a - prefer_b)
        return {
            "predicted_response_partition": partition,
            "predicted_prefer_a_count": prefer_a,
            "predicted_prefer_b_count": prefer_b,
            "unknown_prediction_count": unknown,
            "distinguished_hypothesis_pair_count": distinguished,
            "response_split_imbalance": imbalance,
            "deterministic_score": distinguished * 1000 - imbalance * 10 - unknown,
        }

    def transition(
        self,
        active_hypothesis_ids: Sequence[str],
        option_a: str,
        option_b: str,
        response: Response,
    ) -> Transition:
        if response not in {"prefer_a", "prefer_b", "neither", "unsure"}:
            raise ValueError(f"Unsupported response: {response}")
        opposite = {"prefer_a": "prefer_b", "prefer_b": "prefer_a"}.get(response)
        eliminated = tuple(
            hypothesis_id
            for hypothesis_id in active_hypothesis_ids
            if opposite is not None
            and self.prediction(hypothesis_id, option_a, option_b) == opposite
        )
        eliminated_set = set(eliminated)
        after = tuple(
            item for item in active_hypothesis_ids if item not in eliminated_set
        )
        return Transition(tuple(active_hypothesis_ids), response, eliminated, after)

    def simulated_response(
        self, hidden_hypothesis_id: str, option_a: str, option_b: str
    ) -> Response:
        prediction = self.prediction(hidden_hypothesis_id, option_a, option_b)
        return prediction if prediction != "unknown" else "unsure"

    def has_discriminative_pair(
        self, hypothesis_ids: Sequence[str], eligible_artwork_ids: Sequence[str]
    ) -> bool:
        for index, option_a in enumerate(eligible_artwork_ids):
            for option_b in eligible_artwork_ids[index + 1 :]:
                if self.statistics(hypothesis_ids, option_a, option_b)[
                    "distinguished_hypothesis_pair_count"
                ]:
                    return True
        return False

    def best_pair(
        self, hypothesis_ids: Sequence[str], eligible_artwork_ids: Iterable[str]
    ) -> tuple[str, str, dict[str, Any]] | None:
        """Return the declared objective optimum with stable-ID tie-breaking."""

        eligible = sorted(set(eligible_artwork_ids))
        best: tuple[tuple[int, str, str], str, str, dict[str, Any]] | None = None
        for index, option_a in enumerate(eligible):
            for option_b in eligible[index + 1 :]:
                statistics = self.statistics(hypothesis_ids, option_a, option_b)
                if not statistics["distinguished_hypothesis_pair_count"]:
                    continue
                key = (-statistics["deterministic_score"], option_a, option_b)
                candidate = (key, option_a, option_b, statistics)
                if best is None or candidate[0] < best[0]:
                    best = candidate
        if best is None:
            return None
        return best[1], best[2], best[3]


def replay_responses(
    model: EvidenceModel,
    initial_hypothesis_ids: Sequence[str],
    questions: Iterable[Any],
) -> tuple[str, ...]:
    """Recompute active hypotheses from the corrected current question history."""

    active = tuple(initial_hypothesis_ids)
    for question in questions:
        response = getattr(question, "response", None)
        if response is None:
            continue
        active = model.transition(
            active,
            getattr(question, "option_a_id"),
            getattr(question, "option_b_id"),
            response,
        ).after
    return active
