"""Build the bounded real-ArtGraph universe for active clarification.

This module performs deterministic RDF selection and descriptive validation.
It does not decide clarification questions; that operation belongs to Prolog.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass
from typing import Any

from rdflib import URIRef

from .artgraph import RESOURCE_PREFIX, _node_label, stable_topic_id
from .interest_exploration import InterestIndex


@dataclass(frozen=True, slots=True)
class HypothesisDefinition:
    id: str
    attribute_type: str
    value_id: str
    label: str

    @property
    def value_uri(self) -> URIRef:
        return URIRef(f"{RESOURCE_PREFIX}{self.value_id.removeprefix('ag_')}")


HYPOTHESIS_DEFINITIONS: tuple[HypothesisDefinition, ...] = (
    HypothesisDefinition("h_musical_subject", "tag", "ag_3236", "musical subjects"),
    HypothesisDefinition("h_nature_subject", "tag", "ag_3679", "nature-reserve subjects"),
    HypothesisDefinition("h_water_subject", "tag", "ag_3579", "water-transport subjects"),
    HypothesisDefinition("h_feline_subject", "tag", "ag_3392", "feline subjects"),
    HypothesisDefinition("h_expressionist_style", "style", "ag_21", "expressionist style"),
    HypothesisDefinition("h_impressionist_style", "style", "ag_42", "impressionist style"),
    HypothesisDefinition("h_cubist_style", "style", "ag_25", "cubist style"),
    HypothesisDefinition("h_portrait_genre", "genre", "ag_9", "portrait genre"),
    HypothesisDefinition("h_oil_medium", "medium", "ag_2551", "oil medium"),
    HypothesisDefinition(
        "h_expressionist_movement", "movement", "ag_124670", "Expressionism movement"
    ),
)


def _numeric_topic_id(topic_id: str) -> int:
    return int(topic_id.removeprefix("ag_"))


def select_clarification_artworks(
    index: InterestIndex, *, per_hypothesis: int = 12
) -> tuple[list[str], dict[str, list[str]]]:
    """Select artist-diverse cohorts for each documented hypothesis."""

    selected_by_hypothesis: dict[str, list[str]] = {}
    for definition in HYPOTHESIS_DEFINITIONS:
        pool = sorted(
            index.attribute_artworks.get(
                (definition.attribute_type, definition.value_uri), set()
            ),
            key=lambda node: int(str(node).removeprefix(RESOURCE_PREFIX)),
        )
        chosen: list[URIRef] = []
        used_artists: set[URIRef] = set()

        # Keep the Phase 0.75 cello example when it belongs to the cohort.
        preferred = URIRef(f"{RESOURCE_PREFIX}10472")
        if preferred in pool:
            chosen.append(preferred)
            artist = index.artwork_artist.get(preferred)
            if artist is not None:
                used_artists.add(artist)

        for artwork in pool:
            if artwork in chosen:
                continue
            artist = index.artwork_artist.get(artwork)
            if artist is None or artist in used_artists:
                continue
            chosen.append(artwork)
            used_artists.add(artist)
            if len(chosen) == per_hypothesis:
                break
        for artwork in pool:
            if len(chosen) == per_hypothesis:
                break
            if artwork not in chosen:
                chosen.append(artwork)
        if len(chosen) < per_hypothesis:
            raise RuntimeError(
                f"Hypothesis {definition.id} has only {len(chosen)} selectable artworks"
            )
        selected_by_hypothesis[definition.id] = [stable_topic_id(node) for node in chosen]

    all_ids = sorted(
        {item for values in selected_by_hypothesis.values() for item in values},
        key=_numeric_topic_id,
    )
    return all_ids, selected_by_hypothesis


def analyze_contrasts(
    index: InterestIndex,
    artwork_ids: list[str],
) -> list[dict[str, Any]]:
    """Describe verified positive-evidence contrasts for every hypothesis pair."""

    uri_by_id = {
        stable_topic_id(artwork): artwork
        for artwork in index.artworks
        if stable_topic_id(artwork) in set(artwork_ids)
    }
    support: dict[str, set[str]] = {}
    for definition in HYPOTHESIS_DEFINITIONS:
        support[definition.id] = {
            topic_id
            for topic_id, artwork in uri_by_id.items()
            if (definition.attribute_type, definition.value_uri)
            in index.attributes[artwork]
        }

    rows: list[dict[str, Any]] = []
    for left_h, right_h in itertools.combinations(HYPOTHESIS_DEFINITIONS, 2):
        left_only = sorted(
            support[left_h.id] - support[right_h.id], key=_numeric_topic_id
        )
        right_only = sorted(
            support[right_h.id] - support[left_h.id], key=_numeric_topic_id
        )
        examples: list[dict[str, Any]] = []
        for left_id in left_only:
            for right_id in right_only:
                left_uri = uri_by_id[left_id]
                right_uri = uri_by_id[right_id]
                if index.artwork_artist.get(left_uri) == index.artwork_artist.get(right_uri):
                    continue
                left_facts = index.attribute_fact_ids[
                    (left_uri, left_h.attribute_type, left_h.value_uri)
                ]
                right_facts = index.attribute_fact_ids[
                    (right_uri, right_h.attribute_type, right_h.value_uri)
                ]
                examples.append(
                    {
                        "option_a": left_id,
                        "option_b": right_id,
                        "option_a_label": _node_label(index.graph, left_uri),
                        "option_b_label": _node_label(index.graph, right_uri),
                        "hypothesis_a_fact_ids": list(left_facts),
                        "hypothesis_b_fact_ids": list(right_facts),
                    }
                )
                if len(examples) == 2:
                    break
            if len(examples) == 2:
                break
        rows.append(
            {
                "hypothesis_a": left_h.id,
                "hypothesis_b": right_h.id,
                "option_a_only_count": len(left_only),
                "option_b_only_count": len(right_only),
                "potential_ordered_pair_count": len(left_only) * len(right_only),
                "examples": examples,
            }
        )
    return rows


def evidence_catalog(index: InterestIndex, artwork_ids: list[str]) -> dict[str, Any]:
    """Create baseline-visible positive evidence without Prolog conclusions."""

    selected = set(artwork_ids)
    artworks: dict[str, Any] = {}
    for artwork in index.artworks:
        artwork_id = stable_topic_id(artwork)
        if artwork_id not in selected:
            continue
        attributes = []
        for kind, value in sorted(index.attributes[artwork], key=lambda item: (item[0], str(item[1]))):
            attributes.append(
                {
                    "type": kind,
                    "value_id": stable_topic_id(value),
                    "fact_ids": list(index.attribute_fact_ids[(artwork, kind, value)]),
                }
            )
        artworks[artwork_id] = {
            "label": _node_label(index.graph, artwork),
            "artist_id": stable_topic_id(index.artwork_artist[artwork]),
            "attributes": attributes,
        }
    return {
        "schema_version": "1.0",
        "hypotheses": [
            {
                "id": definition.id,
                "attribute_type": definition.attribute_type,
                "value_id": definition.value_id,
                "label": definition.label,
            }
            for definition in HYPOTHESIS_DEFINITIONS
        ],
        "artworks": artworks,
    }
