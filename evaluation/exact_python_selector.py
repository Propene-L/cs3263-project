"""Conventional exact optimizer for the Phase 1 clarification objective.

This is intentionally independent of SWI-Prolog and consumes only the shared
exported evidence catalog. It is an experimental baseline, not a replacement
for the project's symbolic inference engine.
"""

from __future__ import annotations

from typing import Sequence

from evaluation.shared_simulator import EvidenceModel
from museum_guide.clarification import ClarificationState
from museum_guide.clarification_baselines import BaselineQuestion, eligible_artworks


class ExactObjectivePythonSelector:
    def __init__(self, evidence: dict) -> None:
        self.model = EvidenceModel(evidence)

    def select(
        self, state: ClarificationState, active_hypothesis_ids: Sequence[str]
    ) -> BaselineQuestion | None:
        best = self.model.best_pair(
            active_hypothesis_ids, eligible_artworks(state)
        )
        if best is None:
            return None
        option_a, option_b, statistics = best
        return BaselineQuestion(
            method="exact_objective_python",
            option_a_id=option_a,
            option_b_id=option_b,
            score=float(statistics["deterministic_score"]),
            metadata={"statistics": statistics},
        )
