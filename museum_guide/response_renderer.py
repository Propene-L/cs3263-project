"""Deterministic, source-bounded responses: language model cannot add art facts."""
from __future__ import annotations

from typing import Any

ARTGRAPH_SOURCE = "https://zenodo.org/records/6337958"


def _interest(explanation: dict, labels: dict[str, str]) -> str:
    components = explanation.get("components", [])
    if len(components) == 1:
        return labels[components[0]]
    if len(components) == 2:
        return f"{labels[components[0]]} and {labels[components[1]]} specifically together"
    raise ValueError("Invalid preference explanation to render")


def render_action(action: dict, evidence: dict, library, labels: dict[str, str]) -> dict:
    """Return a visitor-facing message plus its exact source references."""
    typ = action["type"]
    sources: list[dict] = []
    if typ == "clarify_interest":
        text = f"Is your interest in {_interest(action['explanation'], labels)}? You can answer yes, no, or unsure."
    elif typ in {"ask_knowledge", "confirm_knowledge"}:
        topic = library.topics[action["topic_id"]]
        if typ == "confirm_knowledge":
            text = f"I have conflicting notes about your familiarity with {topic.label}. Are you familiar with it? (yes/no/unsure)"
        else:
            text = f"Before continuing, are you already familiar with {topic.label}? (yes/no/unsure)"
    elif typ == "explain":
        topic = library.topics[action["topic_id"]]
        text = f"About {topic.label}: {topic.explanation}"
        sources = [{"source_id": topic.source_id, "url": topic.source_url, "topic_id": topic.id}]
    elif typ == "recommend":
        artwork_id = action["artwork_id"]
        if artwork_id not in evidence["artworks"]:
            raise ValueError("Unknown recommended artwork")
        artwork = evidence["artworks"][artwork_id]
        lookup = {(h["attribute_type"], h["value_id"]): h["label"] for h in evidence["hypotheses"]}
        matched = []
        fact_ids = set()
        for attribute in artwork["attributes"]:
            label = lookup.get((attribute["type"], attribute["value_id"]))
            if label and label not in matched:
                matched.append(label)
                fact_ids.update(attribute["fact_ids"])
        extra = f" Its reviewed metadata includes: {', '.join(matched[:4])}." if matched else ""
        text = f"You might explore {artwork['label']} ({artwork_id}).{extra}"
        sources = [{"source_id": "artgraph_v1", "url": ARTGRAPH_SOURCE,
                    "artwork_id": artwork_id, "fact_ids": sorted(fact_ids)}]
        followup = action.get("follow_up_topic")
        if followup and followup in library.topics:
            text += f" Would you like to explore {library.topics[followup].label}? (yes/no/unsure)"
    elif typ == "insufficient_evidence":
        text = "I cannot confidently identify the next step from what is recorded. You can mention another artwork you like, ask for a topic, or skip this question."
    elif typ == "ask_open":
        text = "Tell me which artwork interested you or which art topic you'd like to explore. I won't assume your prior knowledge."
    elif typ == "acknowledge_skip":
        text = "We can skip that. You can choose another artwork or topic whenever you like."
    elif typ == "acknowledge_knowledge":
        text = "I've updated your stated familiarity with the topic. You can choose a topic to explore or mention an artwork."
    elif typ == "finish_topic":
        text = "We've covered the selected topic's prerequisites. You can explore another topic or artwork."
    else:
        raise ValueError(f"Unsupported action type: {typ}")
    return {"text": text, "sources": sources}
