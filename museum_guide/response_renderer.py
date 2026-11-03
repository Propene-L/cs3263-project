"""Deterministic, source-bounded visitor responses."""

from __future__ import annotations

from typing import Any


ARTGRAPH_SOURCE = "https://zenodo.org/records/6337958"


def _interest(explanation: dict[str, Any], labels: dict[str, str]) -> str:
    components = explanation.get("components", [])
    if len(components) == 1 and components[0] in labels:
        return labels[components[0]]
    if len(components) == 2 and all(component in labels for component in components):
        return f"{labels[components[0]]} and {labels[components[1]]} specifically together"
    raise ValueError("Invalid preference explanation to render")


def render_action(
    action: dict[str, Any],
    evidence: dict[str, Any],
    library: Any,
    labels: dict[str, str],
) -> dict[str, Any]:
    """Render only catalog/evidence-backed content and return exact sources."""
    action_type = action["type"]
    sources: list[dict[str, Any]] = []
    if action_type == "clarify_interest":
        text = (
            f"Is your interest in {_interest(action['explanation'], labels)}? "
            "You can answer yes, no, or unsure."
        )
    elif action_type in {"ask_knowledge", "confirm_knowledge"}:
        topic = library.topics[action["topic_id"]]
        if action_type == "confirm_knowledge":
            text = (
                f"I have conflicting notes about your familiarity with {topic.label}. "
                "Are you familiar with it? (yes/no/unsure)"
            )
        else:
            text = f"Before continuing, are you already familiar with {topic.label}? (yes/no/unsure)"
    elif action_type == "explain":
        topic = library.topics[action["topic_id"]]
        text = f"About {topic.label}: {topic.explanation}"
        sources = [{
            "source_id": topic.source_id,
            "url": topic.source_url,
            "topic_id": topic.id,
            "provenance": "educational_guidance",
        }]
    elif action_type == "recommend":
        artwork_id = action["artwork_id"]
        if artwork_id not in evidence["artworks"]:
            raise ValueError("Unknown recommended artwork")
        artwork = evidence["artworks"][artwork_id]
        label_lookup = {
            (item["attribute_type"], item["value_id"]): item["label"]
            for item in evidence["hypotheses"]
        }
        matched: list[str] = []
        fact_ids: set[str] = set()
        for attribute in artwork["attributes"]:
            label = label_lookup.get((attribute["type"], attribute["value_id"]))
            if label and label not in matched:
                matched.append(label)
                fact_ids.update(attribute["fact_ids"])
        metadata = f" Its reviewed metadata includes: {', '.join(matched[:4])}." if matched else ""
        text = f"You might explore {artwork['label']} ({artwork_id}).{metadata}"
        sources = [{
            "source_id": "artgraph_v1",
            "url": ARTGRAPH_SOURCE,
            "artwork_id": artwork_id,
            "fact_ids": sorted(fact_ids),
            "provenance": "imported_artgraph_facts",
        }]
    elif action_type == "insufficient_evidence":
        text = (
            "I cannot confidently identify the next step from what is recorded. "
            "You can mention another artwork you like, ask for a topic, or skip this question."
        )
    elif action_type == "ask_open":
        text = (
            "Tell me which artwork interested you or which art topic you'd like to explore. "
            "I won't assume your prior knowledge."
        )
    elif action_type == "acknowledge_skip":
        text = "We can skip that. You can choose another artwork or topic whenever you like."
    elif action_type == "acknowledge_knowledge":
        text = (
            "I've updated your stated familiarity with the topic. "
            "You can choose a topic to explore or mention an artwork."
        )
    elif action_type == "finish_topic":
        text = "We've addressed the selected guidance topics. You can explore another topic or artwork."
    else:
        raise ValueError(f"Unsupported action type: {action_type}")
    return {"text": text, "sources": sources}
