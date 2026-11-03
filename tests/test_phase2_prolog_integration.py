"""Opt-in real SWI-Prolog smoke test. Skips on machines without the repo/solver."""
from __future__ import annotations

import os
from pathlib import Path
import pytest

from museum_guide.dialogue import MuseumDialogue

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "data/curated/clarification_evidence.json"
FACTS = ROOT / "logic/clarification_generated_facts.pl"

@pytest.mark.skipif(not EVIDENCE.is_file() or not FACTS.is_file(),
                    reason="Requires complete cs3263-project checkout, not standalone patch")
def test_real_prolog_flagship_three_turn_preference_inference():
    try:
        guide = MuseumDialogue.from_repository(ROOT)
    except Exception as exc:
        if "SWI-Prolog executable not found" in str(exc):
            pytest.skip("SWI-Prolog is not installed or SWIPL_PATH was not configured")
        raise
    session = guide.new_session("visitor_live_test")
    for text in ["like ag_8416", "dislike ag_13231", "dislike ag_8296"]:
        session, result = guide.run_turn(session, text, mode="manual")
    assert result["action"] == "clarify_interest"
    assert result["audit"]["rule_id"] == "prolog_preference_clarification"
    assert result["state"]["pending"]["explanation"]["kind"] in {"atomic", "all_of"}
    session, answered = guide.run_turn(session, "yes", mode="manual")
    assert len(session.preferences) == 4
    assert session.preferences[-1]["kind"] in {"explicit_interest", "explicit_conjunction"}
    assert isinstance(answered["text"], str) and answered["text"]


def test_curated_topic_catalog_loads_and_has_sources():
    p = ROOT / "data/curated/education_topics.json"
    if not p.exists():
        pytest.skip("Curated topics not installed")
    from museum_guide.knowledge_layer import TopicLibrary
    library = TopicLibrary.load(p)
    assert {"c_art_style", "c_portrait", "c_expressionism"} <= set(library.topics)
    assert library.path("c_expressionist_portrait")[-1] == "c_expressionist_portrait"
