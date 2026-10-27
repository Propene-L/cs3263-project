"""Validated ArtGraph v1.0 RDF audit, sampling, and Prolog export."""

from __future__ import annotations

import hashlib
import io
import json
import re
import zipfile
from collections import Counter, deque
from contextlib import contextmanager
from dataclasses import asdict
from pathlib import Path
from typing import IO, Any, Iterator

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF

from .domain import Topic, TopicType

ARTGRAPH_SCHEMA = "https://www.gennarovessio.com/artgraph-schema#"
ARTGRAPH_RESOURCES = "https://www.gennarovessio.com/artgraph-resources#"
AG = Namespace(ARTGRAPH_SCHEMA)
RESOURCE_PREFIX = ARTGRAPH_RESOURCES
MALFORMED_APPEND_MARKER = ":POST http://localhost:7474/"

TYPE_MAP: dict[URIRef, TopicType] = {
    AG.Artwork: TopicType.ARTWORK,
    AG.Artist: TopicType.ARTIST,
    AG.Movement: TopicType.MOVEMENT,
    AG.Style: TopicType.STYLE,
    AG.Genre: TopicType.GENRE,
    AG.Media: TopicType.MEDIUM,
    AG.Subject: TopicType.SUBJECT,
    AG.Period: TopicType.PERIOD,
    AG.Serie: TopicType.SERIES,
    AG.Training: TopicType.TRAINING,
    AG.Tag: TopicType.TAG,
}

RELATION_PREDICATES: dict[URIRef, str] = {
    AG.createdBy: "created_by",
    AG.hasStyle: "has_style",
    AG.hasGenre: "has_genre",
    # The populated v1.0 facts use these spellings even though the bundled
    # ontology declares madeFrom and belongToMovement.
    AG.madeOf: "made_of",
    AG.belongsToMovement: "belongs_to_movement",
    AG.hasSubject: "has_subject",
    AG.hasPeriod: "has_period",
    AG.partOf: "part_of_series",
    AG.relatedToSchool: "related_to_school",
    AG.about: "about",
}

LABEL_PREDICATES: tuple[URIRef, ...] = (AG.title, AG.name)
INCOMING_EXPANSION_PREDICATES: frozenset[URIRef] = frozenset({AG.createdBy})
SAFE_ID = re.compile(r"^[a-z][a-z0-9_]*$")
ELIGIBLE_CANDIDATE_TYPES = frozenset(
    {
        TopicType.ARTIST,
        TopicType.MOVEMENT,
        TopicType.STYLE,
        TopicType.GENRE,
        TopicType.MEDIUM,
    }
)


class ArtGraphError(ValueError):
    """Raised when source RDF violates the Phase 0 import contract."""


@contextmanager
def open_artgraph_text(path: str | Path) -> Iterator[IO[str]]:
    source = Path(path)
    if source.suffix.lower() == ".zip":
        archive = zipfile.ZipFile(source)
        matches = [
            name
            for name in archive.namelist()
            if name.endswith("artgraph-facts.ttl")
        ]
        if len(matches) != 1:
            archive.close()
            raise ArtGraphError(
                f"Expected exactly one artgraph-facts.ttl in {source}, found {matches}"
            )
        binary = archive.open(matches[0])
        text = io.TextIOWrapper(binary, encoding="utf-8")
        try:
            yield text
        finally:
            text.close()
            archive.close()
    else:
        with source.open("r", encoding="utf-8") as stream:
            yield stream


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sanitize_artgraph(source: str | Path, output: str | Path) -> dict[str, Any]:
    """Remove the known appended Neo4j request/preview, preserving all prior lines."""

    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    kept = 0
    removed = 0
    marker_line: int | None = None
    in_removed_section = False
    with open_artgraph_text(source) as input_stream, destination.open(
        "w", encoding="utf-8", newline="\n"
    ) as output_stream:
        for line_number, line in enumerate(input_stream, start=1):
            if not in_removed_section and line.startswith(MALFORMED_APPEND_MARKER):
                marker_line = line_number
                in_removed_section = True
            if in_removed_section:
                removed += 1
            else:
                output_stream.write(line)
                kept += 1
    return {
        "source": str(source),
        "output": str(destination),
        "kept_lines": kept,
        "removed_lines": removed,
        "marker_line": marker_line,
        "sanitized_sha256": sha256_file(destination),
    }


def load_graph(path: str | Path) -> Graph:
    graph = Graph()
    try:
        graph.parse(Path(path), format="turtle")
    except Exception as exc:
        raise ArtGraphError(f"Could not parse RDF {path}: {exc}") from exc
    return graph


def graph_audit(graph: Graph) -> dict[str, Any]:
    predicate_counts = Counter(str(predicate) for predicate in graph.predicates())
    type_counts = Counter(str(obj) for obj in graph.objects(predicate=RDF.type))
    resource_nodes = {
        node
        for triple in graph
        for node in (triple[0], triple[2])
        if isinstance(node, URIRef) and str(node).startswith(RESOURCE_PREFIX)
    }
    return {
        "triple_count": len(graph),
        "resource_uri_count": len(resource_nodes),
        "predicate_counts": dict(sorted(predicate_counts.items())),
        "type_counts": dict(sorted(type_counts.items())),
        "validated_relation_predicates": [str(p) for p in RELATION_PREDICATES],
    }


def resource_uri(value: str) -> URIRef:
    if value.startswith(RESOURCE_PREFIX):
        return URIRef(value)
    if not value.isdigit():
        raise ArtGraphError(
            "Seed must be a numeric ArtGraph resource ID or full ArtGraph resource URI"
        )
    return URIRef(f"{RESOURCE_PREFIX}{value}")


def stable_topic_id(uri: URIRef | str) -> str:
    value = str(uri)
    if not value.startswith(RESOURCE_PREFIX):
        raise ArtGraphError(f"Not an ArtGraph resource URI: {value}")
    local = value.removeprefix(RESOURCE_PREFIX)
    if not local.isdigit():
        raise ArtGraphError(f"ArtGraph resource local ID is not numeric: {local!r}")
    return f"ag_{local}"


def stable_fact_id(subject: Any, predicate: Any, obj: Any) -> str:
    canonical = "\x1f".join((str(subject), str(predicate), str(obj)))
    return "agf_" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:20]


def _node_type(graph: Graph, node: URIRef) -> TopicType | None:
    for rdf_type in sorted(graph.objects(node, RDF.type), key=str):
        if rdf_type in TYPE_MAP:
            return TYPE_MAP[rdf_type]
    return None


def _node_label(graph: Graph, node: URIRef) -> str:
    for predicate in LABEL_PREDICATES:
        labels = sorted(str(value) for value in graph.objects(node, predicate))
        if labels:
            return labels[0]
    return stable_topic_id(node)


def find_seed_candidates(graph: Graph, limit: int = 10) -> list[dict[str, str]]:
    required = (AG.createdBy, AG.hasStyle, AG.hasGenre, AG.madeOf)
    candidates: list[dict[str, str]] = []
    artworks = sorted(
        graph.subjects(RDF.type, AG.Artwork),
        key=lambda node: int(str(node).removeprefix(RESOURCE_PREFIX)),
    )
    for artwork in artworks:
        if all(any(graph.objects(artwork, predicate)) for predicate in required):
            candidates.append(
                {
                    "resource_id": str(artwork).removeprefix(RESOURCE_PREFIX),
                    "topic_id": stable_topic_id(artwork),
                    "source_uri": str(artwork),
                    "label": _node_label(graph, artwork),
                }
            )
            if len(candidates) >= limit:
                break
    return candidates


def extract_connected_subgraph(
    graph: Graph,
    seed: str,
    *,
    max_depth: int = 2,
    max_neighbors_per_predicate: int = 3,
) -> tuple[Graph, list[Topic]]:
    """Deterministically sample a bounded connected graph; this is not inference."""

    seed_uri = resource_uri(seed)
    if (seed_uri, RDF.type, AG.Artwork) not in graph:
        raise ArtGraphError(f"Seed is not an ArtGraph Artwork: {seed_uri}")
    selected: set[URIRef] = {seed_uri}
    queue: deque[tuple[URIRef, int]] = deque([(seed_uri, 0)])

    while queue:
        node, depth = queue.popleft()
        if depth >= max_depth:
            continue
        grouped: dict[tuple[str, URIRef], list[URIRef]] = {}
        for predicate in RELATION_PREDICATES:
            objects = [
                obj
                for obj in graph.objects(node, predicate)
                if isinstance(obj, URIRef) and _node_type(graph, obj) is not None
            ]
            grouped[("out", predicate)] = sorted(set(objects), key=str)
        for predicate in INCOMING_EXPANSION_PREDICATES:
            subjects = [
                subject
                for subject in graph.subjects(predicate, node)
                if isinstance(subject, URIRef) and _node_type(graph, subject) is not None
            ]
            grouped[("in", predicate)] = sorted(set(subjects), key=str)
        for key in sorted(grouped, key=lambda item: (item[0], str(item[1]))):
            for neighbor in grouped[key][:max_neighbors_per_predicate]:
                if neighbor not in selected:
                    selected.add(neighbor)
                    queue.append((neighbor, depth + 1))

    sample = Graph()
    sample.bind("artgraph", AG)
    sample.bind("artgraph-res", Namespace(RESOURCE_PREFIX))
    for node in sorted(selected, key=str):
        for predicate, obj in graph.predicate_objects(node):
            if predicate == RDF.type or predicate in LABEL_PREDICATES:
                sample.add((node, predicate, obj))
            elif predicate in RELATION_PREDICATES and obj in selected:
                sample.add((node, predicate, obj))

    topics = [
        Topic(
            id=stable_topic_id(node),
            type=node_type,
            label=_node_label(graph, node),
            source_uri=str(node),
            properties={},
        )
        for node in selected
        if (node_type := _node_type(graph, node)) is not None
    ]
    topics.sort(key=lambda topic: (topic.type.value, topic.id))
    return sample, topics


def write_sorted_rdf(graph: Graph, path: str | Path) -> None:
    """Write deterministic N-Triples syntax, which is also valid Turtle."""

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    lines = sorted(
        f"{subject.n3()} {predicate.n3()} {obj.n3()} .\n"
        for subject, predicate, obj in graph
    )
    destination.write_text("".join(lines), encoding="utf-8", newline="\n")


def write_topic_catalog(topics: list[Topic], path: str | Path) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "1.0",
        "candidate_policy": (
            "Artwork may be a goal; eligible recommendation types are artist, "
            "movement, style, genre, and medium."
        ),
        "topics": [{**asdict(topic), "type": topic.type.value} for topic in topics],
        "allowed_candidate_ids": [
            topic.id for topic in topics if topic.type in ELIGIBLE_CANDIDATE_TYPES
        ],
    }
    destination.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def _prolog_atom(value: str) -> str:
    if SAFE_ID.fullmatch(value):
        return value
    escaped = value.replace("\\", "\\\\").replace("'", "''").replace("\n", " ")
    return f"'{escaped}'"


def export_prolog_facts(
    graph: Graph,
    topics: list[Topic],
    path: str | Path,
    *,
    snapshot_id: str,
    source_dataset_uri: str | None = None,
) -> dict[str, Any]:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    topic_by_uri = {URIRef(topic.source_uri): topic for topic in topics}
    lines = [
        "% Generated from validated ArtGraph v1.0 RDF. Do not edit.\n",
        ":- dynamic source_fact/5.\n",
        ":- dynamic fact_snapshot/2.\n",
        ":- dynamic rdf_type/3.\n",
        ":- dynamic rdf_label/3.\n",
        ":- dynamic created_by/3.\n",
        ":- dynamic has_style/3.\n",
        ":- dynamic has_genre/3.\n",
        ":- dynamic made_of/3.\n",
        ":- dynamic belongs_to_movement/3.\n",
        ":- dynamic has_subject/3.\n",
        ":- dynamic has_period/3.\n",
        ":- dynamic part_of_series/3.\n",
        ":- dynamic related_to_school/3.\n",
        ":- dynamic about/3.\n",
        ":- discontiguous source_fact/5.\n",
        ":- discontiguous fact_snapshot/2.\n",
        ":- discontiguous rdf_type/3.\n",
        ":- discontiguous rdf_label/3.\n",
        ":- discontiguous created_by/3.\n",
        ":- discontiguous has_style/3.\n",
        ":- discontiguous has_genre/3.\n",
        ":- discontiguous made_of/3.\n",
        ":- discontiguous belongs_to_movement/3.\n",
        ":- discontiguous has_subject/3.\n",
        ":- discontiguous has_period/3.\n",
        ":- discontiguous part_of_series/3.\n",
        ":- discontiguous related_to_school/3.\n",
        ":- discontiguous about/3.\n",
        f"snapshot({_prolog_atom(snapshot_id)}).\n",
    ]
    if source_dataset_uri is not None:
        lines.append(
            f"source_dataset({_prolog_atom(snapshot_id)}, "
            f"{_prolog_atom(source_dataset_uri)}).\n"
        )
    fact_count = 0
    for topic in sorted(topics, key=lambda item: item.id):
        lines.append(
            "topic({id}, {type}, {label}, {uri}).\n".format(
                id=topic.id,
                type=topic.type.value,
                label=_prolog_atom(topic.label),
                uri=_prolog_atom(topic.source_uri),
            )
        )

    triples = sorted(graph, key=lambda item: tuple(str(term) for term in item))
    for subject, predicate, obj in triples:
        if subject not in topic_by_uri:
            continue
        subject_id = topic_by_uri[subject].id
        fact_id = stable_fact_id(subject, predicate, obj)
        if predicate == RDF.type and obj in TYPE_MAP:
            predicate_name = "rdf_type"
            object_atom = TYPE_MAP[obj].value
            lines.append(f"rdf_type({subject_id}, {object_atom}, {fact_id}).\n")
        elif predicate in LABEL_PREDICATES and isinstance(obj, Literal):
            predicate_name = "rdf_label"
            object_atom = _prolog_atom(str(obj))
            lines.append(f"rdf_label({subject_id}, {object_atom}, {fact_id}).\n")
        elif predicate in RELATION_PREDICATES and obj in topic_by_uri:
            predicate_name = RELATION_PREDICATES[predicate]
            object_atom = topic_by_uri[obj].id
            lines.append(
                f"{predicate_name}({subject_id}, {object_atom}, {fact_id}).\n"
            )
        else:
            continue
        lines.append(
            "source_fact({fid}, {pred}, {subject}, {object}, {predicate_uri}).\n".format(
                fid=fact_id,
                pred=predicate_name,
                subject=subject_id,
                object=object_atom,
                predicate_uri=_prolog_atom(str(predicate)),
            )
        )
        lines.append(f"fact_snapshot({fact_id}, {_prolog_atom(snapshot_id)}).\n")
        fact_count += 1
    destination.write_text("".join(lines), encoding="utf-8", newline="\n")
    return {
        "topic_count": len(topics),
        "fact_count": fact_count,
        "output": str(destination),
        "sha256": sha256_file(destination),
    }

