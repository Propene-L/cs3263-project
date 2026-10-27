"""Create the controlled Phase 1 clarification benchmark.

The cases are declared independently of Prolog output. Expected availability
is based on the reviewed positive-evidence contrast report, not solver output.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def observation(identifier: str, hypothesis_id: str) -> dict[str, str]:
    return {
        "id": identifier,
        "kind": "explicit_interest",
        "object_id": hypothesis_id,
    }


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
