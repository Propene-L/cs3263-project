"""Create a method-blind, unscored textual human-review sheet."""

from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    results = json.loads(
        (ROOT / "evaluation" / "phase_1_1_results.json").read_text(encoding="utf-8")
    )
    evidence = json.loads(
        (ROOT / "data" / "curated" / "clarification_evidence.json").read_text(
            encoding="utf-8"
        )
    )
    selected = []
    for scenario in results["scenarios"]:
        if scenario["subset"] != "held_out":
            continue
        rounds = scenario["methods"]["compositional_prolog"]["rounds"]
        question = next((item for item in rounds if item.get("selected")), None)
        if question is not None:
            selected.append((scenario, question))
        if len(selected) == 12:
            break

    fields = [
        "review_item_id",
        "scenario_id",
        "option_a_id",
        "option_a_label",
        "option_b_id",
        "option_b_label",
        "active_hypotheses",
        "recorded_support_summary",
        "understandable_1_to_5",
        "attributes_accurate_1_to_5",
        "comparison_meaningful_1_to_5",
        "plausibly_clarifies_interest_1_to_5",
        "deductions_correct_1_to_5",
        "reviewer_notes",
    ]
    output = ROOT / "evaluation" / "clarification_human_review.csv"
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for index, (scenario, question) in enumerate(selected, start=1):
            option_a, option_b = question["selected_artwork_ids"]
            partition = question["predicted_response_partition"]
            writer.writerow(
                {
                    "review_item_id": f"review_{index:02d}",
                    "scenario_id": scenario["scenario_id"],
                    "option_a_id": option_a,
                    "option_a_label": evidence["artworks"][option_a]["label"],
                    "option_b_id": option_b,
                    "option_b_label": evidence["artworks"][option_b]["label"],
                    "active_hypotheses": " | ".join(
                        question["active_hypothesis_ids_before"]
                    ),
                    "recorded_support_summary": (
                        f"predict A: {', '.join(partition['prefer_a'])}; "
                        f"predict B: {', '.join(partition['prefer_b'])}; "
                        f"unknown: {', '.join(partition['unknown'])}"
                    ),
                    "understandable_1_to_5": "",
                    "attributes_accurate_1_to_5": "",
                    "comparison_meaningful_1_to_5": "",
                    "plausibly_clarifies_interest_1_to_5": "",
                    "deductions_correct_1_to_5": "",
                    "reviewer_notes": "",
                }
            )
    print(f"wrote {len(selected)} unscored items to {output}")


if __name__ == "__main__":
    main()
