"""Create method-blind Phase 1.2 pairwise relevance review items."""

from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def recorded_hypothesis_evidence(
    artwork_id: str, evidence: dict[str, object]
) -> str:
    """Render only reviewed hypothesis facts, with provenance, for blind review."""

    hypotheses = {
        (item["attribute_type"], item["value_id"]): item
        for item in evidence["hypotheses"]
    }
    artwork = evidence["artworks"][artwork_id]
    rows = []
    for attribute in artwork["attributes"]:
        hypothesis = hypotheses.get((attribute["type"], attribute["value_id"]))
        if hypothesis is not None:
            rows.append(
                f"{hypothesis['label']} [{', '.join(attribute['fact_ids'])}]"
            )
    return "; ".join(rows) if rows else "no reviewed hypothesis support recorded"


def main() -> None:
    results = json.loads(
        (ROOT / "evaluation" / "preference_state_results.json").read_text(
            encoding="utf-8"
        )
    )
    scenarios = {
        item["scenario_id"]: item
        for item in (
            json.loads(line)
            for line in (
                ROOT / "evaluation" / "preference_state_scenarios.jsonl"
            ).read_text(encoding="utf-8").splitlines()
        )
    }
    evidence = json.loads(
        (ROOT / "data" / "curated" / "clarification_evidence.json").read_text(
            encoding="utf-8"
        )
    )
    rows = [item for item in results["scenarios"] if item["subset"] == "held_out"]
    rows.append(
        next(
            item
            for item in results["scenarios"]
            if item["scenario_id"] == "flagship_interaction_albert_kollmann"
        )
    )
    fields = [
        "review_item_id",
        "scenario_id",
        "visitor_history",
        "recorded_observation_evidence",
        "action_a_artwork_id",
        "action_a_label",
        "action_a_recorded_attributes",
        "action_b_artwork_id",
        "action_b_label",
        "action_b_recorded_attributes",
        "reviewer_choice_a_b_equal_neither",
        "reviewer_notes",
    ]
    output = ROOT / "evaluation" / "preference_state_human_review.csv"
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for index, result_row in enumerate(rows, start=1):
            scenario = scenarios[result_row["scenario_id"]]
            compositional = result_row["methods"]["compositional_prolog"][
                "ranked_actions"
            ][0]["artwork_id"]
            baseline = result_row["methods"]["signed_additive_atomic"][
                "ranked_actions"
            ][0]["artwork_id"]
            if index % 2:
                action_a, action_b = compositional, baseline
            else:
                action_a, action_b = baseline, compositional
            observation_text = " | ".join(
                f"{item['kind']} {item['object_id']} "
                f"({evidence['artworks'][item['object_id']]['label']}): "
                f"{recorded_hypothesis_evidence(item['object_id'], evidence)}"
                for item in scenario["observations"]
            )
            writer.writerow(
                {
                    "review_item_id": f"state_review_{index:02d}",
                    "scenario_id": result_row["scenario_id"],
                    "visitor_history": scenario["natural_language_history"],
                    "recorded_observation_evidence": observation_text,
                    "action_a_artwork_id": action_a,
                    "action_a_label": evidence["artworks"][action_a]["label"],
                    "action_a_recorded_attributes": recorded_hypothesis_evidence(
                        action_a, evidence
                    ),
                    "action_b_artwork_id": action_b,
                    "action_b_label": evidence["artworks"][action_b]["label"],
                    "action_b_recorded_attributes": recorded_hypothesis_evidence(
                        action_b, evidence
                    ),
                    "reviewer_choice_a_b_equal_neither": "",
                    "reviewer_notes": "",
                }
            )
    print(f"wrote {len(rows)} unscored blinded items to {output}")


if __name__ == "__main__":
    main()
