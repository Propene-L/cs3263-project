"""Discover controlled Phase 1.2 scenarios from the frozen ArtGraph evidence."""

from __future__ import annotations

import json
from itertools import combinations
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_PATH = ROOT / "data" / "curated" / "clarification_evidence.json"
OUTPUT_PATH = ROOT / "evaluation" / "preference_state_scenarios.jsonl"
AUDIT_PATH = ROOT / "docs" / "preference_state_data_audit.json"


def build_index(evidence: dict[str, Any]) -> tuple[dict[str, set[str]], dict[str, dict[str, Any]]]:
    definitions = {
        (item["attribute_type"], item["value_id"]): item["id"]
        for item in evidence["hypotheses"]
    }
    supports: dict[str, set[str]] = {}
    for artwork_id, record in evidence["artworks"].items():
        supports[artwork_id] = {
            definitions[(attribute["type"], attribute["value_id"])]
            for attribute in record["attributes"]
            if (attribute["type"], attribute["value_id"]) in definitions
        }
    return supports, {item["id"]: item for item in evidence["hypotheses"]}


def relevant_ids(
    supports: dict[str, set[str]], latent_profile: dict[str, Any], candidates: list[str]
) -> list[str]:
    required = set(latent_profile["components"])
    if latent_profile["kind"] == "atomic":
        return sorted(item for item in candidates if required <= supports[item])
    return sorted(item for item in candidates if required <= supports[item])


def candidate_universe(
    artworks: list[str], observed: set[str], target: str, distractor: str
) -> list[str]:
    extras = [
        item
        for item in artworks
        if item not in observed and item not in {target, distractor}
    ][:3]
    return [target, distractor, *extras]


def flagship_scenarios(
    evidence: dict[str, Any], supports: dict[str, set[str]]
) -> list[dict[str, Any]]:
    interaction_candidates = ["ag_20804", "ag_8415"]
    interaction_profile = {
        "kind": "all_of",
        "components": ["h_expressionist_style", "h_portrait_genre"],
    }
    atomic_candidates = ["ag_14531", "ag_42361"]
    atomic_profile = {"kind": "atomic", "components": ["h_musical_subject"]}
    return [
        {
            "scenario_id": "flagship_interaction_albert_kollmann",
            "family": "compositional_interaction",
            "subset": "development",
            "natural_language_history": (
                "I liked Albert Kollmann. I did not like A Bird Passing through a "
                "Cloud, and I also did not like Profile Portrait of a Boy."
            ),
            "observations": [
                {"id": "obs_like_albert", "kind": "likes", "object_id": "ag_8416"},
                {"id": "obs_dislike_bird", "kind": "dislikes", "object_id": "ag_13231"},
                {"id": "obs_dislike_boy", "kind": "dislikes", "object_id": "ag_8296"},
            ],
            "latent_profile": interaction_profile,
            "candidate_artwork_ids": interaction_candidates,
            "relevant_artwork_ids": relevant_ids(
                supports, interaction_profile, interaction_candidates
            ),
            "clarification_useful_ids": [],
            "expected_action_type": "recommend",
            "construction": {
                "liked_artwork_id": "ag_8416",
                "disliked_artwork_ids": ["ag_13231", "ag_8296"],
                "target_artwork_id": "ag_20804",
                "distractor_artwork_id": "ag_8415",
                "interaction_schema": "style_plus_genre",
                "criteria": "exact_user_supplied_flagship",
            },
        },
        {
            "scenario_id": "flagship_contrastive_cellist",
            "family": "contrastive_atomic",
            "subset": "development",
            "natural_language_history": (
                "I liked Study for The Cellist, but I did not like Albert Kollmann."
            ),
            "observations": [
                {"id": "obs_like_cellist", "kind": "likes", "object_id": "ag_10472"},
                {"id": "obs_dislike_albert", "kind": "dislikes", "object_id": "ag_8416"},
            ],
            "latent_profile": atomic_profile,
            "candidate_artwork_ids": atomic_candidates,
            "relevant_artwork_ids": relevant_ids(
                supports, atomic_profile, atomic_candidates
            ),
            "clarification_useful_ids": ["ag_14531"],
            "expected_action_type": "clarify",
            "construction": {
                "liked_artwork_id": "ag_10472",
                "disliked_artwork_ids": ["ag_8416"],
                "target_artwork_id": "ag_14531",
                "distractor_artwork_id": "ag_42361",
                "differentiating_hypothesis": "h_musical_subject",
                "criteria": "exact_user_supplied_flagship",
            },
        },
    ]


def discover_atomic(
    artworks: list[str], supports: dict[str, set[str]]
) -> tuple[list[dict[str, Any]], int]:
    clean_probe = {
        hypothesis: [
            artwork
            for artwork in artworks
            if supports[artwork] == {hypothesis}
        ]
        for hypothesis in sorted({item for values in supports.values() for item in values})
    }
    matches: list[dict[str, Any]] = []
    viable_count = 0
    seen: set[tuple[str, str, str]] = set()
    for liked in artworks:
        for disliked in artworks:
            if liked == disliked:
                continue
            shared = supports[liked] & supports[disliked]
            differentiating = supports[liked] - supports[disliked]
            if len(shared) < 2 or len(differentiating) != 1:
                continue
            for hypothesis in sorted(differentiating):
                probes = [
                    item
                    for item in clean_probe.get(hypothesis, [])
                    if item not in {liked, disliked}
                ]
                distractors = [
                    item
                    for item in artworks
                    if item not in {liked, disliked}
                    and hypothesis not in supports[item]
                    and len(supports[item] & shared) >= 2
                ]
                if not probes or not distractors:
                    continue
                viable_count += 1
                key = (liked, disliked, hypothesis)
                if key in seen:
                    continue
                seen.add(key)
                target = probes[0]
                distractor = sorted(
                    distractors,
                    key=lambda item: (-len(supports[item] & shared), item),
                )[0]
                candidates = candidate_universe(
                    artworks, {liked, disliked}, target, distractor
                )
                latent = {"kind": "atomic", "components": [hypothesis]}
                matches.append(
                    {
                        "family": "contrastive_atomic",
                        "natural_language_history": (
                            f"I liked artwork {liked}, but I did not like artwork {disliked}."
                        ),
                        "observations": [
                            {"id": "obs_like", "kind": "likes", "object_id": liked},
                            {"id": "obs_dislike", "kind": "dislikes", "object_id": disliked},
                        ],
                        "latent_profile": latent,
                        "candidate_artwork_ids": candidates,
                        "relevant_artwork_ids": relevant_ids(supports, latent, candidates),
                        "clarification_useful_ids": sorted(
                            item for item in candidates if supports[item] == {hypothesis}
                        ),
                        "expected_action_type": "clarify",
                        "construction": {
                            "liked_artwork_id": liked,
                            "disliked_artwork_ids": [disliked],
                            "shared_hypotheses": sorted(shared),
                            "differentiating_hypothesis": hypothesis,
                            "target_artwork_id": target,
                            "distractor_artwork_id": distractor,
                            "criteria": {
                                "minimum_shared_hypotheses": 2,
                                "clean_probe_support_set": [hypothesis],
                                "distractor_excludes_differentiating_hypothesis": True,
                            },
                        },
                    }
                )
    return matches, viable_count


def discover_interactions(
    artworks: list[str],
    supports: dict[str, set[str]],
    hypothesis_rows: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], int]:
    allowed_type_pairs = {("tag", "style"), ("tag", "genre"), ("style", "genre")}
    hypotheses = sorted(hypothesis_rows)

    def derived_pairs(liked: str, disliked_a: str, disliked_b: str) -> set[frozenset[str]]:
        derived: set[frozenset[str]] = set()
        for candidate_a, candidate_b in combinations(hypotheses, 2):
            types = {
                hypothesis_rows[candidate_a]["attribute_type"],
                hypothesis_rows[candidate_b]["attribute_type"],
            }
            if types not in ({"tag", "style"}, {"tag", "genre"}, {"style", "genre"}):
                continue
            if {candidate_a, candidate_b} <= supports[liked] and (
                (
                    candidate_a in supports[disliked_a]
                    and candidate_b not in supports[disliked_a]
                    and candidate_b in supports[disliked_b]
                    and candidate_a not in supports[disliked_b]
                )
                or (
                    candidate_b in supports[disliked_a]
                    and candidate_a not in supports[disliked_a]
                    and candidate_a in supports[disliked_b]
                    and candidate_b not in supports[disliked_b]
                )
            ):
                derived.add(frozenset((candidate_a, candidate_b)))
        return derived

    matches: list[dict[str, Any]] = []
    viable_count = 0
    for first, second in combinations(hypotheses, 2):
        type_first = hypothesis_rows[first]["attribute_type"]
        type_second = hypothesis_rows[second]["attribute_type"]
        if (type_first, type_second) not in allowed_type_pairs and (
            type_second,
            type_first,
        ) not in allowed_type_pairs:
            continue
        components = {first, second}
        liked_options = [item for item in artworks if components <= supports[item]]
        first_only = [
            item for item in artworks if first in supports[item] and second not in supports[item]
        ]
        second_only = [
            item for item in artworks if second in supports[item] and first not in supports[item]
        ]
        targets = list(liked_options)
        if not liked_options or not first_only or not second_only or len(targets) < 2:
            continue
        for liked in liked_options:
            d1 = next((item for item in first_only if item != liked), None)
            d2 = next((item for item in second_only if item not in {liked, d1}), None)
            target = next(
                (item for item in targets if item not in {liked, d1, d2}), None
            )
            if d1 is None or d2 is None or target is None:
                continue
            if derived_pairs(liked, d1, d2) != {frozenset(components)}:
                continue
            distractors = [
                item
                for item in artworks
                if item not in {liked, d1, d2, target}
                and not components <= supports[item]
                and bool(components & supports[item])
            ]
            if not distractors:
                continue
            viable_count += 1
            distractor = sorted(
                distractors,
                key=lambda item: (-len(supports[item] & supports[liked]), item),
            )[0]
            candidates = candidate_universe(
                artworks, {liked, d1, d2}, target, distractor
            )
            latent = {"kind": "all_of", "components": [first, second]}
            matches.append(
                {
                    "family": "compositional_interaction",
                    "natural_language_history": (
                        f"I liked artwork {liked}. I did not like artworks {d1} and {d2}."
                    ),
                    "observations": [
                        {"id": "obs_like", "kind": "likes", "object_id": liked},
                        {"id": "obs_dislike_component_a", "kind": "dislikes", "object_id": d1},
                        {"id": "obs_dislike_component_b", "kind": "dislikes", "object_id": d2},
                    ],
                    "latent_profile": latent,
                    "candidate_artwork_ids": candidates,
                    "relevant_artwork_ids": relevant_ids(supports, latent, candidates),
                    "clarification_useful_ids": [],
                    "expected_action_type": "recommend",
                    "construction": {
                        "liked_artwork_id": liked,
                        "disliked_artwork_ids": [d1, d2],
                        "interaction_components": [first, second],
                        "interaction_schema": f"{type_first}_plus_{type_second}",
                        "target_artwork_id": target,
                        "distractor_artwork_id": distractor,
                        "criteria": {
                            "liked_supports_both": True,
                            "disliked_examples_support_separate_components": True,
                            "missing_component_status": "not_recorded",
                        },
                    },
                }
            )
    return matches, viable_count


def main() -> None:
    evidence = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))
    supports, hypothesis_rows = build_index(evidence)
    artworks = sorted(evidence["artworks"])
    atomic_matches, atomic_discovery_count = discover_atomic(artworks, supports)
    interaction_matches, interaction_discovery_count = discover_interactions(
        artworks, supports, hypothesis_rows
    )
    selected_atomic = [
        item
        for item in atomic_matches
        if not (
            item["construction"]["liked_artwork_id"] == "ag_10472"
            and item["construction"]["disliked_artwork_ids"] == ["ag_8416"]
        )
    ][:11]
    selected_interaction = [
        item
        for item in interaction_matches
        if not (
            item["construction"]["liked_artwork_id"] == "ag_8416"
            and set(item["construction"]["interaction_components"])
            == {"h_expressionist_style", "h_portrait_genre"}
        )
    ][:11]
    scenarios = flagship_scenarios(evidence, supports)
    scenarios.extend(selected_atomic)
    scenarios.extend(selected_interaction)
    for index, scenario in enumerate(scenarios, start=1):
        if "scenario_id" not in scenario:
            family_slug = "atomic" if scenario["family"] == "contrastive_atomic" else "interaction"
            scenario["scenario_id"] = f"preference_{family_slug}_{index:03d}"
            scenario["subset"] = "development" if index % 2 else "held_out"
        scenario["benchmark_label_notice"] = (
            "Controlled latent profile over recorded support; not human preference truth."
        )
    audit = {
        "schema_version": "1.0",
        "source": "data/curated/clarification_evidence.json",
        "artwork_count": len(artworks),
        "hypothesis_count": len(hypothesis_rows),
        "allowed_interaction_type_schemas": [
            "tag_plus_style",
            "tag_plus_genre",
            "style_plus_genre",
        ],
        "discovery": {
            "contrastive_atomic_viable_constructions": atomic_discovery_count,
            "compositional_interaction_viable_constructions": interaction_discovery_count,
        },
        "selected": {
            "scenario_count": len(scenarios),
            "contrastive_atomic_count": sum(
                item["family"] == "contrastive_atomic" for item in scenarios
            ),
            "compositional_interaction_count": sum(
                item["family"] == "compositional_interaction" for item in scenarios
            ),
            "development_count": sum(item["subset"] == "development" for item in scenarios),
            "held_out_count": sum(item["subset"] == "held_out" for item in scenarios),
        },
        "limitations": [
            "Search uses only ten reviewed hypotheses and 112 frozen ArtGraph artworks.",
            "not_recorded means absent from the bounded snapshot, never a negative museum fact.",
            "Controlled latent profiles are constructed labels, not observed human preferences.",
        ],
    }
    OUTPUT_PATH.write_text(
        "".join(json.dumps(item, ensure_ascii=False) + "\n" for item in scenarios),
        encoding="utf-8",
        newline="\n",
    )
    AUDIT_PATH.write_text(
        json.dumps(audit, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    print(json.dumps(audit, indent=2))


if __name__ == "__main__":
    main()
