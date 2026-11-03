"""Measure candidate-count scaling for exact Python and compositional Prolog."""

from __future__ import annotations

import json
import statistics
import time
from pathlib import Path

from evaluation.exact_python_selector import ExactObjectivePythonSelector
from museum_guide.clarification import ClarificationObservation, ClarificationState, default_engine

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    evidence = json.loads(
        (ROOT / "data" / "curated" / "clarification_evidence.json").read_text(
            encoding="utf-8"
        )
    )
    catalog = json.loads(
        (ROOT / "data" / "curated" / "clarification_topic_catalog.json").read_text(
            encoding="utf-8"
        )
    )
    hypotheses = [
        "h_musical_subject",
        "h_nature_subject",
        "h_expressionist_style",
        "h_cubist_style",
        "h_oil_medium",
        "h_portrait_genre",
    ]
    observations = tuple(
        ClarificationObservation(f"obs_scale_{index}", "explicit_interest", hypothesis)
        for index, hypothesis in enumerate(hypotheses, start=1)
    )
    exact = ExactObjectivePythonSelector(evidence)
    engine = default_engine(ROOT)
    rows = []
    for candidate_count in (10, 20, 40, 80, 112):
        allowed = tuple(catalog["allowed_candidate_ids"][:candidate_count])
        state = ClarificationState(
            session_id=f"complexity_{candidate_count}",
            observations=observations,
            allowed_artwork_ids=allowed,
        )
        exact_times = []
        for _ in range(5):
            started = time.perf_counter()
            exact.select(state, hypotheses)
            exact_times.append((time.perf_counter() - started) * 1000)
        prolog_times = []
        for _ in range(3):
            started = time.perf_counter()
            engine.clarify(state)
            prolog_times.append((time.perf_counter() - started) * 1000)
        rows.append(
            {
                "eligible_artwork_count": candidate_count,
                "unordered_pair_count": candidate_count * (candidate_count - 1) // 2,
                "active_hypothesis_count": len(hypotheses),
                "exact_python_mean_ms": round(statistics.fmean(exact_times), 3),
                "exact_python_median_ms": round(statistics.median(exact_times), 3),
                "compositional_prolog_mean_ms": round(statistics.fmean(prolog_times), 3),
                "compositional_prolog_median_ms": round(statistics.median(prolog_times), 3),
                "repetitions": {"exact_python": 5, "compositional_prolog": 3},
            }
        )
    output = {
        "schema_version": "1.0",
        "notice": "Wall-clock measurements on the local Phase 1.1 environment; not cross-machine benchmarks.",
        "rows": rows,
    }
    path = ROOT / "evaluation" / "phase_1_1_complexity_results.json"
    path.write_text(
        json.dumps(output, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    print(json.dumps(rows, indent=2))


if __name__ == "__main__":
    main()
