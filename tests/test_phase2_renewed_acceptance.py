"""Phase 2 renewed acceptance tests, targeting the edd554b integration contract.

Pure planner checks run without SWI-Prolog. The real end-to-end check runs only
when a working SWI-Prolog executable and the repository-generated facts exist.
Authored action expectations are regression fixtures, not human truth labels.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from museum_guide.knowledge_layer import KnowledgeState, TopicLibrary, next_knowledge_action

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "data" / "curated" / "education_topics.json"
SCENARIOS = ROOT / "evaluation" / "integrated_scenarios.jsonl"
FACTS = ROOT / "logic" / "clarification_generated_facts.pl"


def _cases() -> dict[str, dict]:
    from evaluation.evaluate_integrated_guide import load_jsonl

    return {case["id"]: case for case in load_jsonl(SCENARIOS)}


def test_revised_fixture_is_complete_and_unique() -> None:
    cases = _cases()
    assert len(cases) == 11
    assert sum(len(c["turns"]) for c in cases.values()) == 31
    assert sum("expected_action" in t for c in cases.values() for t in c["turns"]) == 29
    assert "portrait_prerequisite" not in cases
    assert {"portrait_familiar", "portrait_unfamiliar", "known_prerequisite", "skip"} <= cases.keys()


def test_fixture_respects_actual_curated_prerequisites() -> None:
    library = TopicLibrary.load(CATALOG)
    assert library.topics["c_portrait"].prerequisites == ()
    assert library.topics["c_expressionism"].prerequisites == ("c_art_style",)
    cases = _cases()
    assert [t["expected_action"] for t in cases["portrait_familiar"]["turns"]] == [
        "ask_knowledge", "finish_topic"
    ]
    assert [t["expected_action"] for t in cases["portrait_unfamiliar"]["turns"]] == [
        "ask_knowledge", "explain", "finish_topic"
    ]
    assert cases["known_prerequisite"]["turns"][1]["visitor"] == "topic c_expressionism"


def test_portrait_familiar_and_unfamiliar_planner_paths() -> None:
    library = TopicLibrary.load(CATALOG)
    familiar = KnowledgeState()
    assert next_knowledge_action(library, familiar, "c_portrait")["type"] == "ask_knowledge"
    familiar.apply("c_portrait", "known", source="visitor_confirmation")
    assert next_knowledge_action(library, familiar, "c_portrait")["type"] == "finish_topic"

    unfamiliar = KnowledgeState()
    unfamiliar.apply("c_portrait", "not_known", source="visitor_confirmation")
    assert next_knowledge_action(library, unfamiliar, "c_portrait")["type"] == "explain"
    unfamiliar.presented.add("c_portrait")
    assert next_knowledge_action(library, unfamiliar, "c_portrait")["type"] == "finish_topic"
    assert unfamiliar.status("c_portrait") == "not_known"


def test_known_prerequisite_and_skipped_topic_policy() -> None:
    library = TopicLibrary.load(CATALOG)
    state = KnowledgeState()
    state.apply("c_art_style", "known", source="visitor_confirmation")
    action = next_knowledge_action(library, state, "c_expressionism")
    assert action["type"] == "ask_knowledge"
    assert action["topic_id"] == "c_expressionism"

    skipped = KnowledgeState()
    skipped.skipped.add("c_portrait")
    assert next_knowledge_action(library, skipped, "c_portrait")["type"] == "finish_topic"


def test_real_prolog_updated_manual_acceptance() -> None:
    from museum_guide.prolog_bridge import find_swipl

    if find_swipl() is None or not FACTS.is_file():
        pytest.skip("Requires full checkout with SWI-Prolog and generated facts")
    from evaluation.evaluate_integrated_guide import evaluate, load_jsonl
    from museum_guide.dialogue import MuseumDialogue

    guide = MuseumDialogue.from_repository(ROOT)
    report = evaluate(guide, load_jsonl(SCENARIOS), mode="manual")
    summary = report["summary"]
    bad_rows = [
        row for row in report["turns"]
        if row["status"] == "error" or row["action_match_authored"] is False
    ]
    assert bad_rows == [], json.dumps(bad_rows, ensure_ascii=False, indent=2)
    assert summary["scenario_count"] == 11
    assert summary["executed_turns"] == 31
    assert summary["error_count"] == 0
    assert summary["complete_scenarios"] == 11
    assert summary["authored_action_match"] == 1.0
    assert summary["source_coverage_of_explain_or_recommend"] == 1.0
