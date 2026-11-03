"""Create the controlled Phase 1 clarification benchmark.

The cases are declared independently of Prolog output. Expected availability
is based on the reviewed positive-evidence contrast report, not solver output.
"""

from __future__ import annotations

import json
import sys
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluation.shared_simulator import EvidenceModel


def observation(identifier: str, hypothesis_id: str) -> dict[str, str]:
    return {
        "id": identifier,
        "kind": "explicit_interest",
        "object_id": hypothesis_id,
    }


def scenario_eligible(scenario: dict[str, object]) -> list[str]:
    observations = scenario["observations"]
    excluded = {
        item["object_id"]
        for item in observations
        if item["kind"] in {"knows", "likes", "dislikes", "viewed", "rejected"}
    }
    for question in scenario.get("preloaded_questions", []):
        excluded.update((question["option_a_id"], question["option_b_id"]))
    return sorted(set(scenario["allowed_artwork_ids"]) - excluded)


def initial_active(scenario: dict[str, object], model: EvidenceModel) -> list[str]:
    active = [
        item
        for item in scenario["hypothesis_ids"]
        if item not in scenario["rejected_hypothesis_ids"]
    ]
    for question in scenario.get("preloaded_questions", []):
        response = question.get("response")
        if response:
            active = list(
                model.transition(
                    active,
                    question["option_a_id"],
                    question["option_b_id"],
                    response,
                ).after
            )
    return active


def add_independent_expectation(
    scenario: dict[str, object], model: EvidenceModel
) -> None:
    active = initial_active(scenario, model)
    eligible = scenario_eligible(scenario)
    if len(active) <= 1:
        status = "initially_resolved"
    elif model.has_discriminative_pair(active, eligible):
        status = "initially_solvable"
    else:
        status = "initially_unsolvable"
    scenario["expected_initial_status"] = status
    scenario["expected_has_question"] = status == "initially_solvable"
    scenario["independent_expectation"] = {
        "basis": "declared_positive_support_response_model",
        "initial_active_hypothesis_count": len(active),
        "eligible_artwork_count": len(eligible),
    }


def expanded_scenarios(
    catalog: dict[str, object], evidence: dict[str, object]
) -> list[dict[str, object]]:
    """Build 45 non-Prolog-labeled cases over the fixed real ArtGraph snapshot."""

    model = EvidenceModel(evidence)
    all_artworks = list(catalog["allowed_candidate_ids"])
    hypothesis_rows = {item["id"]: item for item in evidence["hypotheses"]}
    hypothesis_ids = list(hypothesis_rows)
    required = [
        (
            "h_expressionist_movement",
            "h_expressionist_style",
            "h_oil_medium",
            "h_musical_subject",
        ),
        (
            "h_impressionist_style",
            "h_cubist_style",
            "h_portrait_genre",
            "h_oil_medium",
        ),
    ]
    pool = [
        combo
        for size in (3, 4, 5, 6)
        for combo in combinations(hypothesis_ids, size)
    ]
    # Stable interleaving avoids selecting only lexically adjacent/easy cases.
    pool = sorted(pool, key=lambda combo: (sum(map(len, combo)) % 7, "|".join(reversed(combo))))
    multi_sets: list[tuple[str, ...]] = []
    for combo in [*required, *pool]:
        normalized = tuple(dict.fromkeys(combo))
        if set(normalized) not in [set(item) for item in multi_sets]:
            multi_sets.append(normalized)
        if len(multi_sets) == 39:
            break

    scenarios: list[dict[str, object]] = []
    for index, hypotheses in enumerate(multi_sets, start=1):
        hidden = hypotheses[index % len(hypotheses)]
        allowed = all_artworks
        tags = ["controlled", "real_artgraph", "expanded", "multi_hypothesis"]
        observations = [
            observation(f"obs_p11_{index:03d}_{number}", hypothesis)
            for number, hypothesis in enumerate(hypotheses, start=1)
        ]
        rejected_hypotheses: list[str] = []

        if index % 6 == 0:
            limited = all_artworks[(index % 3) :: 2]
            if model.has_discriminative_pair(hypotheses, limited):
                allowed = limited
                tags.extend(["incomplete_evidence", "reduced_candidate_universe"])
        best = model.best_pair(hypotheses, allowed)
        if best and index % 7 == 0:
            observations.append(
                {
                    "id": f"obs_p11_{index:03d}_viewed",
                    "kind": "viewed",
                    "object_id": best[0],
                }
            )
            tags.append("previously_viewed_optimum")
        if best and index % 8 == 0:
            observations.append(
                {
                    "id": f"obs_p11_{index:03d}_rejected",
                    "kind": "rejected",
                    "object_id": best[1],
                }
            )
            tags.append("rejected_artwork_constraint")
        if index % 10 == 0 and len(hypotheses) > 3:
            rejected_hypotheses = [hypotheses[-1]]
            tags.append("rejected_hypothesis")

        scenario: dict[str, object] = {
            "scenario_id": f"phase_1_1_multi_{index:03d}",
            "description": (
                "Controlled multi-hypothesis clarification case with independently "
                "declared positive-support semantics."
            ),
            "natural_language_utterance": "I am interested in "
            + ", ".join(hypothesis_rows[item]["label"] for item in hypotheses)
            + ".",
            "intended_observation_ids": [item["id"] for item in observations if item["kind"] == "explicit_interest"],
            "observations": observations,
            "hypothesis_ids": list(hypotheses),
            "hidden_hypothesis_id": hidden,
            "rejected_hypothesis_ids": rejected_hypotheses,
            "allowed_artwork_ids": allowed,
            "independent_contrast_examples": [],
            "case_tags": tags,
            "attribute_families": sorted(
                {hypothesis_rows[item]["attribute_type"] for item in hypotheses}
            ),
            "correlation_group": (
                "correlated"
                if {
                    "h_expressionist_movement",
                    "h_expressionist_style",
                }.issubset(hypotheses)
                else "relatively_independent"
            ),
            "subset": "development" if index <= 26 else "held_out",
        }
        if index == 1:
            scenario["simulated_responses"] = ["unsure"]
            tags.append("early_answer_no_reduction")
        if index == 2:
            scenario["simulated_responses"] = ["neither"]
            tags.append("neither_no_reduction")
        if index == 3 and best:
            final_response = model.simulated_response(hidden, best[0], best[1])
            if final_response == "unsure":
                final_response = "prefer_a"
            scenario["preloaded_questions"] = [
                {
                    "id": f"q_{best[0]}_{best[1]}",
                    "option_a_id": best[0],
                    "option_b_id": best[1],
                    "response_observation_id": f"obs_p11_{index:03d}_corrected",
                    "response": final_response,
                    "correction_replaced_response": (
                        "prefer_b" if final_response == "prefer_a" else "prefer_a"
                    ),
                }
            ]
            tags.append("explicitly_corrected_response")
        if index in {4, 5}:
            scenario["hidden_hypothesis_id"] = next(
                item for item in hypothesis_ids if item not in hypotheses
            )
            tags.append("hidden_hypothesis_already_absent")

        add_independent_expectation(scenario, model)
        scenarios.append(scenario)

    # Four deliberately unsolvable cases with 3-5 hypotheses and only a pair
    # whose prediction vector has no opposing determinate answers.
    for offset, size in enumerate((3, 4, 5, 3), start=40):
        hypotheses = tuple(hypothesis_ids[offset % len(hypothesis_ids) :] + hypothesis_ids[: offset % len(hypothesis_ids)])[:size]
        non_discriminating: tuple[str, str] | None = None
        for option_a, option_b in combinations(all_artworks, 2):
            if model.statistics(hypotheses, option_a, option_b)[
                "distinguished_hypothesis_pair_count"
            ] == 0:
                non_discriminating = (option_a, option_b)
                break
        assert non_discriminating is not None
        scenario = {
            "scenario_id": f"phase_1_1_unsolvable_{offset:03d}",
            "description": "Real-ArtGraph candidates provide no opposing determinate predictions.",
            "natural_language_utterance": "I have several possible interests, but the available examples may not separate them.",
            "intended_observation_ids": [f"obs_p11_{offset:03d}_{number}" for number in range(1, size + 1)],
            "observations": [
                observation(f"obs_p11_{offset:03d}_{number}", hypothesis)
                for number, hypothesis in enumerate(hypotheses, start=1)
            ],
            "hypothesis_ids": list(hypotheses),
            "hidden_hypothesis_id": hypotheses[0],
            "rejected_hypothesis_ids": [],
            "allowed_artwork_ids": list(non_discriminating),
            "independent_contrast_examples": [],
            "case_tags": [
                "controlled",
                "real_artgraph",
                "expanded",
                "no_valid_question",
                "unknown_or_same_direction_predictions",
            ],
            "attribute_families": sorted(
                {hypothesis_rows[item]["attribute_type"] for item in hypotheses}
            ),
            "correlation_group": "mixed",
            "subset": "held_out",
        }
        add_independent_expectation(scenario, model)
        scenarios.append(scenario)

    # Two initially resolved cases are reported separately, never counted as
    # successful clarification requiring zero questions.
    for offset, hypothesis in enumerate(hypothesis_ids[:2], start=44):
        scenario = {
            "scenario_id": f"phase_1_1_resolved_{offset:03d}",
            "description": "One provisional hypothesis is already active before interaction.",
            "natural_language_utterance": f"I am interested in {hypothesis_rows[hypothesis]['label']}.",
            "intended_observation_ids": [f"obs_p11_{offset:03d}_1"],
            "observations": [observation(f"obs_p11_{offset:03d}_1", hypothesis)],
            "hypothesis_ids": [hypothesis],
            "hidden_hypothesis_id": hypothesis,
            "rejected_hypothesis_ids": [],
            "allowed_artwork_ids": all_artworks,
            "independent_contrast_examples": [],
            "case_tags": [
                "controlled",
                "real_artgraph",
                "expanded",
                "initially_resolved",
            ],
            "attribute_families": [hypothesis_rows[hypothesis]["attribute_type"]],
            "correlation_group": "not_applicable",
            "subset": "held_out",
        }
        add_independent_expectation(scenario, model)
        scenarios.append(scenario)

    assert len(scenarios) == 45
    assert sum(
        item["expected_initial_status"] == "initially_solvable"
        and item["independent_expectation"]["initial_active_hypothesis_count"] >= 3
        for item in scenarios
    ) >= 23
    return scenarios


def main() -> None:
    report = json.loads(
        (ROOT / "docs" / "clarification_dataset_report.json").read_text(
            encoding="utf-8"
        )
    )
    catalog = json.loads(
        (ROOT / "data" / "curated" / "clarification_topic_catalog.json").read_text(
            encoding="utf-8"
        )
    )
    evidence = json.loads(
        (ROOT / "data" / "curated" / "clarification_evidence.json").read_text(
            encoding="utf-8"
        )
    )
    valid_pairs = [
        row
        for row in report["contrast_analysis"]
        if len(row["examples"]) >= 2
    ]
    scenarios: list[dict[str, object]] = []
    for index, row in enumerate(valid_pairs[:14], start=1):
        hypotheses = [row["hypothesis_a"], row["hypothesis_b"]]
        observations = [
            observation(f"obs_s{index}_h1", hypotheses[0]),
            observation(f"obs_s{index}_h2", hypotheses[1]),
        ]
        if index == 5:
            observations.append(
                {"id": "obs_s5_viewed", "kind": "viewed", "object_id": "ag_8966"}
            )
        if index == 6:
            observations.append(
                {"id": "obs_s6_rejected", "kind": "rejected", "object_id": "ag_8793"}
            )
        scenarios.append(
            {
                "scenario_id": f"controlled_pair_{index:02d}",
                "description": "Two explicit provisional hypotheses with verified real-ArtGraph contrasts.",
                "observations": observations,
                "hypothesis_ids": hypotheses,
                "hidden_hypothesis_id": hypotheses[(index + 1) % 2],
                "rejected_hypothesis_ids": [],
                "allowed_artwork_ids": catalog["allowed_candidate_ids"],
                "expected_has_question": True,
                "independent_contrast_examples": row["examples"],
                "case_tags": ["controlled", "real_artgraph", "two_hypothesis"],
            }
        )

    multi_sets = [
        ["h_musical_subject", "h_expressionist_style", "h_nature_subject", "h_oil_medium"],
        ["h_water_subject", "h_cubist_style", "h_portrait_genre", "h_oil_medium"],
        ["h_feline_subject", "h_impressionist_style", "h_nature_subject", "h_portrait_genre"],
        ["h_expressionist_movement", "h_expressionist_style", "h_musical_subject", "h_oil_medium"],
    ]
    for offset, hypotheses in enumerate(multi_sets, start=15):
        rejected = [hypotheses[-1]] if offset == 18 else []
        scenarios.append(
            {
                "scenario_id": f"controlled_multi_{offset:02d}",
                "description": "Compositional clarification across four provisional hypotheses.",
                "observations": [
                    observation(f"obs_s{offset}_h{number}", hypothesis)
                    for number, hypothesis in enumerate(hypotheses, start=1)
                ],
                "hypothesis_ids": hypotheses,
                "hidden_hypothesis_id": hypotheses[0],
                "rejected_hypothesis_ids": rejected,
                "allowed_artwork_ids": catalog["allowed_candidate_ids"],
                "expected_has_question": True,
                "independent_contrast_examples": [],
                "case_tags": [
                    "controlled",
                    "real_artgraph",
                    "multi_hypothesis",
                    *( ["corrected_state"] if rejected else [] ),
                ],
            }
        )

    scenarios.append(
        {
            "scenario_id": "ambiguous_single_hypothesis_19",
            "description": "Only one hypothesis remains, so no pair can distinguish hypotheses.",
            "observations": [observation("obs_s19_h1", "h_musical_subject")],
            "hypothesis_ids": ["h_musical_subject"],
            "hidden_hypothesis_id": "h_musical_subject",
            "rejected_hypothesis_ids": [],
            "allowed_artwork_ids": catalog["allowed_candidate_ids"],
            "expected_has_question": False,
            "independent_contrast_examples": [],
            "case_tags": ["controlled", "ambiguous", "no_valid_question"],
        }
    )

    scenarios.append(
        {
            "scenario_id": "missing_support_universe_20",
            "description": "Allowed artworks carry no recorded support contrast for the two hypotheses.",
            "observations": [
                observation("obs_s20_h1", "h_musical_subject"),
                observation("obs_s20_h2", "h_feline_subject"),
            ],
            "hypothesis_ids": ["h_musical_subject", "h_feline_subject"],
            "hidden_hypothesis_id": "h_musical_subject",
            "rejected_hypothesis_ids": [],
            "allowed_artwork_ids": ["ag_8142", "ag_8148"],
            "expected_has_question": False,
            "independent_contrast_examples": [],
            "case_tags": [
                "controlled",
                "missing_attributes",
                "no_valid_question",
            ],
        }
    )

    phase_1_output = ROOT / "evaluation" / "clarification_scenarios_phase_1.jsonl"
    phase_1_output.write_text(
        "".join(json.dumps(item, ensure_ascii=False) + "\n" for item in scenarios),
        encoding="utf-8",
        newline="\n",
    )

    for scenario in scenarios:
        scenario.setdefault("subset", "phase_1_regression")
        scenario.setdefault("attribute_families", [])
        add_independent_expectation(scenario, EvidenceModel(evidence))

    scenarios.extend(expanded_scenarios(catalog, evidence))

    output = ROOT / "evaluation" / "clarification_scenarios.jsonl"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        "".join(json.dumps(item, ensure_ascii=False) + "\n" for item in scenarios),
        encoding="utf-8",
        newline="\n",
    )
    print(f"wrote {len(scenarios)} scenarios to {output}")


if __name__ == "__main__":
    main()
