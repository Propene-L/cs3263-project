"""Phase 0.5 structural exploration of real ArtGraph subgraphs.

This module selects and summarizes RDF samples. It does not derive museum
conclusions or choose visitor recommendations; those remain Prolog concerns.
"""

from __future__ import annotations

import html
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from rdflib import Graph, URIRef
from rdflib.namespace import RDF

from .artgraph import (
    AG,
    ARTGRAPH_SCHEMA,
    RELATION_PREDICATES,
    RESOURCE_PREFIX,
    TYPE_MAP,
    _node_label,
    _node_type,
    stable_fact_id,
    stable_topic_id,
)
from .domain import Topic

ARTWORK_CONTEXT_PREDICATES = (
    AG.hasStyle,
    AG.hasGenre,
    AG.madeOf,
    AG.hasPeriod,
    AG.partOf,
)
ARTIST_CONTEXT_PREDICATES = (
    AG.belongsToMovement,
    AG.relatedToSchool,
    AG.hasSubject,
)
SHARED_PREDICATES = ARTWORK_CONTEXT_PREDICATES
EXPLORED_PREDICATES = (
    AG.hasSubject,
    AG.hasPeriod,
    AG.partOf,
    AG.relatedToSchool,
)

PREDICATE_SEMANTICS: dict[URIRef, dict[str, str]] = {
    AG.hasSubject: {
        "domain": "Artist",
        "range": "Subject",
        "potential": "Artist subject/category context; can join artwork→artist→subject.",
    },
    AG.hasPeriod: {
        "domain": "Artwork",
        "range": "Period",
        "potential": "Artwork period context and shared-period artwork relations.",
    },
    AG.partOf: {
        "domain": "Artwork",
        "range": "Serie",
        "potential": "Series membership and shared-series artwork relations.",
    },
    AG.relatedToSchool: {
        "domain": "Artist",
        "range": "Training",
        "potential": "Artist training-school context; can join artwork→artist→school.",
    },
}


def _resource_sort_key(node: URIRef) -> tuple[int, str]:
    local = str(node).removeprefix(RESOURCE_PREFIX)
    return (int(local), local) if local.isdigit() else (2**63 - 1, local)


def _limited_objects(
    graph: Graph, subject: URIRef, predicate: URIRef, limit: int
) -> list[URIRef]:
    return sorted(
        {
            obj
            for obj in graph.objects(subject, predicate)
            if isinstance(obj, URIRef) and _node_type(graph, obj) is not None
        },
        key=_resource_sort_key,
    )[:limit]


def predicate_inventory(graph: Graph) -> list[dict[str, Any]]:
    inventory: list[dict[str, Any]] = []
    for predicate in EXPLORED_PREDICATES:
        examples = []
        triples = sorted(
            graph.triples((None, predicate, None)),
            key=lambda triple: (_resource_sort_key(triple[0]), _resource_sort_key(triple[2])),
        )
        for subject, _, obj in triples[:3]:
            examples.append(
                {
                    "subject_id": stable_topic_id(subject),
                    "subject_label": _node_label(graph, subject),
                    "object_id": stable_topic_id(obj),
                    "object_label": _node_label(graph, obj),
                    "fact_id": stable_fact_id(subject, predicate, obj),
                    "triple": [str(subject), str(predicate), str(obj)],
                }
            )
        semantics = PREDICATE_SEMANTICS[predicate]
        inventory.append(
            {
                "predicate": RELATION_PREDICATES[predicate],
                "predicate_uri": str(predicate),
                "domain": semantics["domain"],
                "range": semantics["range"],
                "frequency": sum(1 for _ in graph.triples((None, predicate, None))),
                "potential": semantics["potential"],
                "importer_change": "Implemented in Phase 0.5 typed allowlist and Prolog export.",
                "examples": examples,
            }
        )
    return inventory


def _candidate_for_artist(
    graph: Graph,
    artist: URIRef,
    *,
    max_artworks: int,
    max_objects_per_predicate: int,
) -> tuple[dict[str, Any], Graph, list[Topic]] | None:
    artworks = sorted(
        {
            work
            for work in graph.subjects(AG.createdBy, artist)
            if isinstance(work, URIRef) and (work, RDF.type, AG.Artwork) in graph
        },
        key=_resource_sort_key,
    )
    movements = _limited_objects(graph, artist, AG.belongsToMovement, 3)
    if len(artworks) < 3 or not movements:
        return None
    artworks = artworks[:max_artworks]
    selected: set[URIRef] = {artist, *artworks, *movements}
    for predicate in ARTIST_CONTEXT_PREDICATES[1:]:
        selected.update(
            _limited_objects(graph, artist, predicate, max_objects_per_predicate)
        )
    for artwork in artworks:
        for predicate in ARTWORK_CONTEXT_PREDICATES:
            selected.update(
                _limited_objects(
                    graph, artwork, predicate, max_objects_per_predicate
                )
            )

    sample = Graph()
    for node in selected:
        for predicate, obj in graph.predicate_objects(node):
            if predicate == RDF.type or predicate in (AG.name, AG.title):
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

    shared_groups: list[dict[str, Any]] = []
    for predicate in SHARED_PREDICATES:
        object_to_works: dict[URIRef, list[URIRef]] = defaultdict(list)
        for artwork in artworks:
            for obj in graph.objects(artwork, predicate):
                if obj in selected:
                    object_to_works[obj].append(artwork)
        for obj, linked_works in sorted(
            object_to_works.items(), key=lambda item: _resource_sort_key(item[0])
        ):
            if len(linked_works) >= 2:
                shared_groups.append(
                    {
                        "predicate": RELATION_PREDICATES[predicate],
                        "topic_id": stable_topic_id(obj),
                        "topic_label": _node_label(graph, obj),
                        "artwork_ids": [stable_topic_id(work) for work in linked_works],
                    }
                )

    relation_edges = [
        (subject, predicate, obj)
        for subject, predicate, obj in sample
        if predicate in RELATION_PREDICATES
    ]
    type_counts: dict[str, int] = defaultdict(int)
    for topic in topics:
        type_counts[topic.type.value] += 1
    independent_paths = ["artwork_artist_movement"]
    independent_paths.extend(
        sorted({f"shared_{group['predicate']}" for group in shared_groups})
    )
    if any(sample.triples((artist, AG.relatedToSchool, None))):
        independent_paths.append("artwork_artist_school")
    if any(sample.triples((artist, AG.hasSubject, None))):
        independent_paths.append("artwork_artist_subject")
    score = (
        len(type_counts) * 12
        + len(set(predicate for _, predicate, _ in relation_edges)) * 5
        + len(shared_groups) * 4
        + len(independent_paths) * 8
        + len(artworks) * 2
    )

    nodes = [
        {
            "id": topic.id,
            "label": topic.label,
            "type": topic.type.value,
            "source_uri": topic.source_uri,
        }
        for topic in topics
    ]
    edges = [
        {
            "source": stable_topic_id(subject),
            "target": stable_topic_id(obj),
            "predicate": RELATION_PREDICATES[predicate],
            "predicate_uri": str(predicate),
            "fact_id": stable_fact_id(subject, predicate, obj),
            "triple": [str(subject), str(predicate), str(obj)],
        }
        for subject, predicate, obj in sorted(
            relation_edges,
            key=lambda triple: tuple(str(term) for term in triple),
        )
    ]
    summary = {
        "candidate_id": f"artist_{stable_topic_id(artist)}",
        "artist_id": stable_topic_id(artist),
        "artist_label": _node_label(graph, artist),
        "artwork_ids": [stable_topic_id(work) for work in artworks],
        "movement_ids": [stable_topic_id(movement) for movement in movements],
        "stats": {
            "entity_count": len(topics),
            "relationship_count": len(relation_edges),
            "artwork_count": len(artworks),
            "entity_type_count": len(type_counts),
            "entity_types": dict(sorted(type_counts.items())),
            "distinct_predicate_count": len(
                {predicate for _, predicate, _ in relation_edges}
            ),
            "shared_relationship_count": len(shared_groups),
            "independent_path_count": len(independent_paths),
            "inference_richness_score": score,
        },
        "shared_relationships": shared_groups,
        "independent_paths": independent_paths,
        "nodes": nodes,
        "edges": edges,
    }
    return summary, sample, topics


def discover_candidate_subgraphs(
    graph: Graph,
    *,
    limit: int = 5,
    max_artworks: int = 6,
    max_objects_per_predicate: int = 3,
) -> list[tuple[dict[str, Any], Graph, list[Topic]]]:
    artists = sorted(
        set(graph.subjects(AG.belongsToMovement, None)), key=_resource_sort_key
    )
    candidates = []
    for artist in artists:
        candidate = _candidate_for_artist(
            graph,
            artist,
            max_artworks=max_artworks,
            max_objects_per_predicate=max_objects_per_predicate,
        )
        if candidate is None:
            continue
        summary = candidate[0]
        stats = summary["stats"]
        if (
            stats["entity_type_count"] >= 4
            and stats["shared_relationship_count"] >= 1
            and stats["independent_path_count"] >= 3
        ):
            candidates.append(candidate)
    candidates.sort(
        key=lambda item: (
            -item[0]["stats"]["inference_richness_score"],
            item[0]["artist_id"],
        )
    )
    for rank, (summary, _, _) in enumerate(candidates[:limit], start=1):
        summary["rank"] = rank
    return candidates[:limit]


def write_graph_viewer(report: dict[str, Any], path: str | Path) -> None:
    """Write a self-contained interactive SVG viewer with no external assets."""

    # JSON is embedded directly in a script element. Escape HTML-significant
    # characters and JavaScript line separators so labels cannot terminate the
    # script or make the generated source invalid.
    data = (
        json.dumps(report, ensure_ascii=False)
        .replace("&", "\\u0026")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )
    template = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ArtGraph Phase 0.5 Explorer</title>
<style>
body{font:14px system-ui;margin:0;background:#f7f7f8;color:#1f2937}
header{padding:16px 20px;background:#111827;color:white} main{display:grid;grid-template-columns:1fr 340px;gap:12px;padding:12px}
#graph{width:100%;height:680px;background:white;border:1px solid #d1d5db;border-radius:8px}.panel{background:white;padding:14px;border:1px solid #d1d5db;border-radius:8px;overflow:auto;max-height:650px}
.edge{stroke:#94a3b8;stroke-width:2}.edge:hover{stroke:#111827;stroke-width:4}.edge-label{font-size:10px;fill:#475569;cursor:pointer}.node{stroke:#fff;stroke-width:2;cursor:pointer}.node-label{font-size:11px;text-anchor:middle;pointer-events:none}.legend span{display:inline-block;margin:3px 8px 3px 0}.dot{width:10px;height:10px;border-radius:50%;display:inline-block;margin-right:4px}pre{white-space:pre-wrap;word-break:break-word;font-size:11px}select{padding:6px;min-width:280px}
</style></head><body><header><h1>ArtGraph Phase 0.5 Explorer</h1><label>Candidate: <select id="candidate"></select></label> <span id="stats"></span></header>
<main><svg id="graph" viewBox="0 0 1100 680"></svg><aside class="panel"><h2>Legend</h2><div id="legend" class="legend"></div><h2>Selection</h2><pre id="details">Select a node or edge. Hover also exposes the original RDF triple.</pre><h2>Candidate statistics</h2><pre id="candidateStats"></pre></aside></main>
<script>const DATA=__DATA__;
const colors={artwork:'#2563eb',artist:'#dc2626',movement:'#7c3aed',style:'#ea580c',genre:'#16a34a',medium:'#0891b2',subject:'#ca8a04',period:'#db2777',series:'#4f46e5',training:'#64748b'};
const sel=document.getElementById('candidate'),svg=document.getElementById('graph'),details=document.getElementById('details');
DATA.candidates.forEach((c,i)=>{let o=document.createElement('option');o.value=i;o.textContent=`#${c.rank} ${c.artist_label} (${c.artist_id})`;sel.appendChild(o)});
document.getElementById('legend').innerHTML=Object.entries(colors).map(([k,v])=>`<span><i class="dot" style="background:${v}"></i>${k}</span>`).join('');
function S(name,attrs={}){let e=document.createElementNS('http://www.w3.org/2000/svg',name);Object.entries(attrs).forEach(([k,v])=>e.setAttribute(k,v));return e}
function render(){svg.replaceChildren();let c=DATA.candidates[+sel.value],nodes=c.nodes,edges=c.edges;document.getElementById('stats').textContent=` ${c.stats.entity_count} entities · ${c.stats.relationship_count} relationships · score ${c.stats.inference_richness_score}`;document.getElementById('candidateStats').textContent=JSON.stringify(c.stats,null,2)+'\n\nPaths:\n'+c.independent_paths.join('\n');let pos={};nodes.forEach((n,i)=>{let a=2*Math.PI*i/nodes.length-Math.PI/2;pos[n.id]={x:550+260*Math.cos(a),y:330+250*Math.sin(a)}});edges.forEach(e=>{let a=pos[e.source],b=pos[e.target],line=S('line',{x1:a.x,y1:a.y,x2:b.x,y2:b.y,class:'edge'});line.onclick=()=>details.textContent=JSON.stringify(e,null,2);let t=S('title');t.textContent=e.triple.join(' ');line.appendChild(t);svg.appendChild(line);let label=S('text',{x:(a.x+b.x)/2,y:(a.y+b.y)/2,class:'edge-label'});label.textContent=e.predicate;label.onclick=()=>details.textContent=JSON.stringify(e,null,2);svg.appendChild(label)});nodes.forEach(n=>{let p=pos[n.id],g=S('g');let circle=S('circle',{cx:p.x,cy:p.y,r:n.type==='artwork'?28:23,fill:colors[n.type]||'#334155',class:'node'});circle.onclick=()=>details.textContent=JSON.stringify(n,null,2);let title=S('title');title.textContent=`${n.label} (${n.id})\n${n.source_uri}`;circle.appendChild(title);g.appendChild(circle);let l=S('text',{x:p.x,y:p.y+40,class:'node-label'});l.textContent=`${n.label} [${n.id}]`;g.appendChild(l);svg.appendChild(g)})}
sel.onchange=render;render();</script></body></html>"""
    Path(path).write_text(
        template.replace("__DATA__", data), encoding="utf-8", newline="\n"
    )

