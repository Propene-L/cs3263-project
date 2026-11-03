"""ArtGraph interest-evidence audit and bounded development-set extraction.

This module performs RDF preprocessing and descriptive statistics only.  It
does not infer visitor interests or select recommendations; those operations
belong to SWI-Prolog in the Phase 0.75 proof-of-concept.
"""

from __future__ import annotations

import itertools
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from rdflib import Graph, URIRef
from rdflib.namespace import RDF

from .artgraph import (
    AG,
    LABEL_PREDICATES,
    RESOURCE_PREFIX,
    _node_label,
    stable_fact_id,
    stable_topic_id,
)


DIRECT_ATTRIBUTE_PREDICATES: dict[URIRef, str] = {
    AG.about: "tag",
    AG.hasStyle: "style",
    AG.hasGenre: "genre",
    AG.madeOf: "medium",
    AG.partOf: "series",
    AG.hasPeriod: "period",
}


@dataclass(slots=True)
class InterestIndex:
    graph: Graph
    artworks: tuple[URIRef, ...]
    labels: dict[URIRef, str]
    artwork_artist: dict[URIRef, URIRef]
    attributes: dict[URIRef, set[tuple[str, URIRef]]]
    attribute_artworks: dict[tuple[str, URIRef], set[URIRef]]
    attribute_fact_ids: dict[tuple[URIRef, str, URIRef], tuple[str, ...]]


def _resource_number(node: URIRef) -> int:
    return int(str(node).removeprefix(RESOURCE_PREFIX))


def _type_name(node: URIRef) -> str:
    return str(node).rsplit("#", 1)[-1]


def _label(index: InterestIndex, node: URIRef) -> str:
    if node not in index.labels:
        index.labels[node] = _node_label(index.graph, node)
    return index.labels[node]


def _summary(values: Iterable[int]) -> dict[str, float | int]:
    ordered = sorted(values)
    if not ordered:
        return {"count": 0, "min": 0, "median": 0, "mean": 0.0, "p90": 0, "p95": 0, "max": 0}

    def percentile(fraction: float) -> int:
        position = max(0, min(len(ordered) - 1, int(fraction * len(ordered) + 0.999999) - 1))
        return ordered[position]

    return {
        "count": len(ordered),
        "min": ordered[0],
        "median": statistics.median(ordered),
        "mean": round(statistics.fmean(ordered), 4),
        "p90": percentile(0.90),
        "p95": percentile(0.95),
        "max": ordered[-1],
    }


def build_interest_index(graph: Graph) -> InterestIndex:
    """Build typed artwork attributes and stable source-fact provenance."""

    artworks = tuple(sorted(set(graph.subjects(RDF.type, AG.Artwork)), key=_resource_number))
    artwork_set = set(artworks)
    labels: dict[URIRef, str] = {}
    artwork_artist: dict[URIRef, URIRef] = {}
    attributes: dict[URIRef, set[tuple[str, URIRef]]] = {artwork: set() for artwork in artworks}
    attribute_artworks: dict[tuple[str, URIRef], set[URIRef]] = defaultdict(set)
    attribute_fact_ids: dict[tuple[URIRef, str, URIRef], tuple[str, ...]] = {}

    for artwork, artist in graph.subject_objects(AG.createdBy):
        if artwork in artwork_set and isinstance(artist, URIRef):
            artwork_artist[artwork] = artist

    for predicate, attribute_type in DIRECT_ATTRIBUTE_PREDICATES.items():
        for artwork, value in graph.subject_objects(predicate):
            if artwork not in artwork_set or not isinstance(value, URIRef):
                continue
            key = (attribute_type, value)
            attributes[artwork].add(key)
            attribute_artworks[key].add(artwork)
            attribute_fact_ids[(artwork, attribute_type, value)] = (
                stable_fact_id(artwork, predicate, value),
            )

    artist_movements: dict[URIRef, list[tuple[URIRef, str]]] = defaultdict(list)
    for artist, movement in graph.subject_objects(AG.belongsToMovement):
        if isinstance(artist, URIRef) and isinstance(movement, URIRef):
            artist_movements[artist].append(
                (movement, stable_fact_id(artist, AG.belongsToMovement, movement))
            )
    for artwork, artist in artwork_artist.items():
        created_fact = stable_fact_id(artwork, AG.createdBy, artist)
        for movement, movement_fact in artist_movements.get(artist, []):
            key = ("movement", movement)
            attributes[artwork].add(key)
            attribute_artworks[key].add(artwork)
            attribute_fact_ids[(artwork, "movement", movement)] = (
                created_fact,
                movement_fact,
            )

    return InterestIndex(
        graph=graph,
        artworks=artworks,
        labels=labels,
        artwork_artist=artwork_artist,
        attributes=attributes,
        attribute_artworks=dict(attribute_artworks),
        attribute_fact_ids=attribute_fact_ids,
    )


def _actual_about_types(graph: Graph) -> dict[str, Any]:
    pair_counts: Counter[tuple[str, str]] = Counter()
    examples: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for subject, obj in graph.subject_objects(AG.about):
        subject_types = sorted(_type_name(value) for value in graph.objects(subject, RDF.type)) or ["untyped"]
        object_types = sorted(_type_name(value) for value in graph.objects(obj, RDF.type)) or ["untyped"]
        for domain in subject_types:
            for range_type in object_types:
                key = (domain, range_type)
                pair_counts[key] += 1
                if len(examples[key]) < 3:
                    examples[key].append(
                        {
                            "subject_id": stable_topic_id(subject),
                            "subject_label": _node_label(graph, subject),
                            "object_id": stable_topic_id(obj),
                            "object_label": _node_label(graph, obj),
                            "fact_id": stable_fact_id(subject, AG.about, obj),
                            "triple": [str(subject), str(AG.about), str(obj)],
                        }
                    )
    return {
        "declared_domain": "Artwork",
        "declared_range": "Tag",
        "observed_type_pairs": [
            {
                "domain": domain,
                "range": range_type,
                "count": count,
                "examples": examples[(domain, range_type)],
            }
            for (domain, range_type), count in sorted(pair_counts.items())
        ],
    }


def _multi_tag_overlap(index: InterestIndex) -> dict[str, Any]:
    tag_pairs: dict[tuple[URIRef, URIRef], list[URIRef]] = defaultdict(list)
    for artwork in index.artworks:
        tags = sorted(value for kind, value in index.attributes[artwork] if kind == "tag")
        for pair in itertools.combinations(tags, 2):
            tag_pairs[pair].append(artwork)

    with_peer: set[URIRef] = set()
    with_cross_artist_peer: set[URIRef] = set()
    repeated_pair_groups = 0
    cross_artist_pair_groups = 0
    for group in tag_pairs.values():
        if len(group) < 2:
            continue
        repeated_pair_groups += 1
        with_peer.update(group)
        artists = {index.artwork_artist.get(artwork) for artwork in group}
        artists.discard(None)
        if len(artists) >= 2:
            cross_artist_pair_groups += 1
            with_cross_artist_peer.update(group)
    tagged = {
        artwork
        for artwork in index.artworks
        if any(kind == "tag" for kind, _ in index.attributes[artwork])
    }
    denominator = len(tagged) or 1
    return {
        "metric_definition": "Artwork-centric exact counts: an artwork is counted once if at least one peer shares two or more distinct tags.",
        "repeated_tag_pair_groups": repeated_pair_groups,
        "cross_artist_repeated_tag_pair_groups": cross_artist_pair_groups,
        "artworks_with_two_tag_peer": len(with_peer),
        "percent_tagged_artworks_with_two_tag_peer": round(100 * len(with_peer) / denominator, 4),
        "artworks_with_two_tag_cross_artist_peer": len(with_cross_artist_peer),
        "percent_tagged_artworks_with_two_tag_cross_artist_peer": round(
            100 * len(with_cross_artist_peer) / denominator, 4
        ),
    }


def audit_interest_data(graph: Graph, index: InterestIndex) -> dict[str, Any]:
    """Return quantitative Tag/about and typed-attribute diagnostics."""

    tag_key_counts = {
        value: len(artworks)
        for (kind, value), artworks in index.attribute_artworks.items()
        if kind == "tag"
    }
    tag_counts_by_artwork = [
        sum(1 for kind, _ in index.attributes[artwork] if kind == "tag")
        for artwork in index.artworks
    ]
    tagged_artworks = sum(count > 0 for count in tag_counts_by_artwork)
    per_tag_artist_counts = {
        tag: len(
            {
                index.artwork_artist.get(artwork)
                for artwork in index.attribute_artworks[("tag", tag)]
                if index.artwork_artist.get(artwork) is not None
            }
        )
        for tag in tag_key_counts
    }
    cross_artist_tags = sum(count >= 2 for count in per_tag_artist_counts.values())
    cross_artist_artworks: set[URIRef] = set()
    for tag, artist_count in per_tag_artist_counts.items():
        if artist_count >= 2:
            cross_artist_artworks.update(index.attribute_artworks[("tag", tag)])

    predicate_counts = {
        str(predicate): sum(1 for _ in graph.triples((None, predicate, None)))
        for predicate in (
            AG.about,
            AG.hasStyle,
            AG.hasGenre,
            AG.createdBy,
            AG.belongsToMovement,
            AG.madeOf,
            AG.partOf,
            AG.hasPeriod,
        )
    }
    return {
        "about_semantics": _actual_about_types(graph),
        "artwork_count": len(index.artworks),
        "tag_entity_count": sum(1 for _ in graph.subjects(RDF.type, AG.Tag)),
        "about_triple_count": sum(tag_key_counts.values()),
        "tagged_artwork_count": tagged_artworks,
        "tagged_artwork_percent": round(100 * tagged_artworks / len(index.artworks), 4),
        "tags_per_all_artwork": _summary(tag_counts_by_artwork),
        "tags_per_tagged_artwork": _summary(value for value in tag_counts_by_artwork if value),
        "tags_per_artwork_histogram": dict(sorted(Counter(tag_counts_by_artwork).items())),
        "artworks_per_tag": _summary(tag_key_counts.values()),
        "artists_per_tag": _summary(per_tag_artist_counts.values()),
        "tags_used_by_multiple_artists": cross_artist_tags,
        "artworks_with_any_cross_artist_tag_peer": len(cross_artist_artworks),
        "percent_tagged_artworks_with_any_cross_artist_tag_peer": round(
            100 * len(cross_artist_artworks) / (tagged_artworks or 1), 4
        ),
        "multi_tag_overlap": _multi_tag_overlap(index),
        "top_tags": [
            {
                "id": stable_topic_id(tag),
                "label": _label(index, tag),
                "artwork_count": count,
                "artist_count": per_tag_artist_counts[tag],
                "source_uri": str(tag),
            }
            for tag, count in sorted(
                tag_key_counts.items(), key=lambda item: (-item[1], _resource_number(item[0]))
            )[:30]
        ],
        "typed_predicate_counts": predicate_counts,
    }


def _cross_artist_multi_attribute_artworks(
    index: InterestIndex, artworks: set[URIRef]
) -> tuple[set[URIRef], list[dict[str, Any]]]:
    signature_groups: dict[
        tuple[tuple[str, URIRef], tuple[str, URIRef]], list[URIRef]
    ] = defaultdict(list)
    for artwork in sorted(artworks, key=_resource_number):
        for pair in itertools.combinations(sorted(index.attributes[artwork], key=lambda item: (item[0], str(item[1]))), 2):
            signature_groups[pair].append(artwork)

    qualifying: set[URIRef] = set()
    example_pairs: dict[tuple[URIRef, URIRef], set[tuple[str, URIRef]]] = defaultdict(set)
    for signature, group in signature_groups.items():
        if len(group) < 2:
            continue
        for left, right in itertools.combinations(group, 2):
            if index.artwork_artist.get(left) == index.artwork_artist.get(right):
                continue
            qualifying.update((left, right))
            pair = (left, right) if _resource_number(left) < _resource_number(right) else (right, left)
            example_pairs[pair].update(signature)

    examples = []
    for (left, right), shared in sorted(
        example_pairs.items(), key=lambda item: (-len(item[1]), _resource_number(item[0][0]), _resource_number(item[0][1]))
    )[:3]:
        shared_items = []
        fact_ids: list[str] = []
        for kind, value in sorted(shared, key=lambda item: (item[0], str(item[1]))):
            left_facts = index.attribute_fact_ids[(left, kind, value)]
            right_facts = index.attribute_fact_ids[(right, kind, value)]
            fact_ids.extend((*left_facts, *right_facts))
            shared_items.append(
                {"type": kind, "value_id": stable_topic_id(value), "value_label": _label(index, value)}
            )
        examples.append(
            {
                "left": {"id": stable_topic_id(left), "label": _label(index, left)},
                "right": {"id": stable_topic_id(right), "label": _label(index, right)},
                "left_artist_id": stable_topic_id(index.artwork_artist[left]),
                "right_artist_id": stable_topic_id(index.artwork_artist[right]),
                "shared_attributes": shared_items,
                "supporting_fact_ids": sorted(set(fact_ids)),
            }
        )
    return qualifying, examples


def candidate_tag_subsets(
    index: InterestIndex,
    *,
    minimum_artworks: int = 50,
    maximum_artworks: int = 200,
    minimum_artists: int = 10,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Rank reproducible tag-anchored multi-artist candidate universes."""

    shortlist: list[tuple[int, URIRef, set[URIRef], set[URIRef], dict[str, set[URIRef]], int]] = []
    for (kind, tag), artworks in index.attribute_artworks.items():
        if kind != "tag" or not minimum_artworks <= len(artworks) <= maximum_artworks:
            continue
        artists = {index.artwork_artist.get(artwork) for artwork in artworks}
        artists.discard(None)
        if len(artists) < minimum_artists:
            continue
        type_values: dict[str, set[URIRef]] = defaultdict(set)
        relation_count = 0
        for artwork in artworks:
            relation_count += len(index.attributes[artwork])
            for attribute_type, value in index.attributes[artwork]:
                type_values[attribute_type].add(value)
        # Pairwise multi-attribute analysis is substantially more expensive
        # than these exact coverage counts.  Shortlist deterministically first
        # rather than recomputing combinations for every one of 5,424 tags.
        preliminary_score = (
            len(artists) * 3
            + len(type_values) * 20
            + min(200, sum(len(values) for values in type_values.values()))
            + min(200, relation_count // len(artworks))
        )
        shortlist.append(
            (
                preliminary_score,
                tag,
                set(artworks),
                set(artists),
                dict(type_values),
                relation_count,
            )
        )

    shortlist.sort(key=lambda item: (-item[0], stable_topic_id(item[1])))
    candidates: list[tuple[dict[str, Any], set[URIRef]]] = []
    for _, tag, artworks, artists, type_values, relation_count in shortlist[:75]:
        cross_multi, examples = _cross_artist_multi_attribute_artworks(index, artworks)
        stats = {
            "artwork_count": len(artworks),
            "artist_count": len(artists),
            "attribute_type_count": len(type_values),
            "attribute_value_count": sum(len(values) for values in type_values.values()),
            "attribute_values_by_type": {
                key: len(values) for key, values in sorted(type_values.items())
            },
            "attribute_relationship_count": relation_count,
            "attribute_relationships_per_artwork": round(relation_count / len(artworks), 4),
            "cross_artist_multi_attribute_artwork_count": len(cross_multi),
            "cross_artist_multi_attribute_percent": round(100 * len(cross_multi) / len(artworks), 4),
        }
        score = (
            len(cross_multi) * 10
            + len(artists) * 3
            + len(type_values) * 20
            + min(200, sum(len(values) for values in type_values.values()))
        )
        candidates.append(
            (
                {
                    "candidate_id": f"tag_{stable_topic_id(tag)}",
                    "anchor_tag": {
                        "id": stable_topic_id(tag),
                        "label": _label(index, tag),
                        "source_uri": str(tag),
                    },
                    "stats": stats,
                    "inference_opportunity_score": score,
                    "artwork_ids": [stable_topic_id(value) for value in sorted(artworks, key=_resource_number)],
                    "examples": examples,
                },
                set(artworks),
            )
        )
    candidates.sort(
        key=lambda item: (-item[0]["inference_opportunity_score"], item[0]["anchor_tag"]["id"])
    )

    selected: list[dict[str, Any]] = []
    selected_sets: list[set[URIRef]] = []
    for candidate, artworks in candidates:
        if any(len(artworks & prior) / len(artworks | prior) > 0.35 for prior in selected_sets):
            continue
        candidate["rank"] = len(selected) + 1
        selected.append(candidate)
        selected_sets.append(artworks)
        if len(selected) == limit:
            break
    return selected


def overlap_profile(
    index: InterestIndex,
    seed_artworks: list[URIRef],
    candidate_artworks: set[URIRef],
) -> dict[str, Any]:
    """Descriptive overlap only; Prolog remains responsible for eligibility."""

    seed_sets = [index.attributes[seed] for seed in seed_artworks]
    union = set().union(*seed_sets)
    intersection = set.intersection(*seed_sets) if seed_sets else set()
    repeated = {
        attribute
        for attribute in union
        if sum(attribute in attributes for attributes in seed_sets) >= 2
    }
    rows = []
    for candidate in sorted(candidate_artworks - set(seed_artworks), key=_resource_number):
        shared_union = union & index.attributes[candidate]
        shared_intersection = intersection & index.attributes[candidate]
        shared_repeated = repeated & index.attributes[candidate]
        rows.append(
            {
                "id": stable_topic_id(candidate),
                "label": _label(index, candidate),
                "artist_id": stable_topic_id(index.artwork_artist[candidate]),
                "shared_union_count": len(shared_union),
                "shared_intersection_count": len(shared_intersection),
                "shared_repeated_count": len(shared_repeated),
            }
        )
    rows.sort(
        key=lambda row: (
            -row["shared_repeated_count"],
            -row["shared_intersection_count"],
            -row["shared_union_count"],
            row["id"],
        )
    )
    return {
        "seed_ids": [stable_topic_id(seed) for seed in seed_artworks],
        "union_attribute_count": len(union),
        "intersection_attribute_count": len(intersection),
        "repeated_attribute_count": len(repeated),
        "candidate_counts_at_least": {
            str(threshold): sum(row["shared_union_count"] >= threshold for row in rows)
            for threshold in range(1, 6)
        },
        "cross_artist_candidate_counts_at_least": {
            str(threshold): sum(
                row["shared_union_count"] >= threshold
                and index.artwork_artist[URIRef(f"{RESOURCE_PREFIX}{row['id'].removeprefix('ag_')}")]
                not in {index.artwork_artist[seed] for seed in seed_artworks}
                for row in rows
            )
            for threshold in range(1, 6)
        },
        "top_candidates": rows[:20],
    }


def extract_interest_subgraph(
    graph: Graph, artwork_ids: Iterable[str]
) -> tuple[Graph, list[URIRef]]:
    """Extract real artwork attributes plus artist-to-movement intermediates."""

    artworks = {
        URIRef(f"{RESOURCE_PREFIX}{value.removeprefix('ag_')}") for value in artwork_ids
    }
    selected = set(artworks)
    relation_predicates = set(DIRECT_ATTRIBUTE_PREDICATES) | {AG.createdBy}
    for artwork in artworks:
        for predicate in relation_predicates:
            selected.update(obj for obj in graph.objects(artwork, predicate) if isinstance(obj, URIRef))
    artists = {obj for artwork in artworks for obj in graph.objects(artwork, AG.createdBy) if isinstance(obj, URIRef)}
    for artist in artists:
        selected.update(obj for obj in graph.objects(artist, AG.belongsToMovement) if isinstance(obj, URIRef))

    sample = Graph()
    for node in sorted(selected, key=str):
        for predicate, obj in graph.predicate_objects(node):
            if predicate == RDF.type or predicate in LABEL_PREDICATES:
                sample.add((node, predicate, obj))
            elif node in artworks and predicate in relation_predicates and obj in selected:
                sample.add((node, predicate, obj))
            elif node in artists and predicate == AG.belongsToMovement and obj in selected:
                sample.add((node, predicate, obj))
    return sample, sorted(selected, key=str)

