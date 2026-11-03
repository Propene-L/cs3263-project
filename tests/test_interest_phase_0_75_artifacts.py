from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from museum_guide.artgraph import load_graph
from museum_guide.prolog_bridge import find_swipl

ROOT = Path(__file__).resolve().parents[1]


def test_real_interest_audit_and_candidate_universes():
    report = json.loads(
        (ROOT / "docs" / "interest_inference_audit.json").read_text(encoding="utf-8")
    )
    audit = report["audit"]
    assert audit["about_triple_count"] == 342982
    assert audit["tag_entity_count"] == 5424
    observed_pairs = audit["about_semantics"]["observed_type_pairs"]
    assert len(observed_pairs) == 1
    assert observed_pairs[0]["domain"] == "Artwork"
    assert observed_pairs[0]["range"] == "Tag"
    assert observed_pairs[0]["count"] == 342982
    assert len(report["candidate_subsets"]) == 5
    assert report["recommended_candidate_id"] == "tag_ag_3236"
    recommended = report["candidate_subsets"][0]
    assert recommended["stats"]["artwork_count"] == 188
    assert recommended["stats"]["artist_count"] == 138
    assert recommended["examples"][0]["supporting_fact_ids"]


def test_real_interest_snapshot_and_scenarios_are_bounded():
    assert len(load_graph(ROOT / "data" / "curated" / "artgraph_interest_dev.ttl")) == 3218
    catalog = json.loads(
        (ROOT / "data" / "curated" / "interest_topic_catalog.json").read_text(
            encoding="utf-8"
        )
    )
    scenarios = json.loads(
        (ROOT / "docs" / "interest_inference_scenarios.json").read_text(
            encoding="utf-8"
        )
    )
    assert len(catalog["allowed_candidate_ids"]) == 188
    assert len(scenarios["scenarios"]) == 5
    assert scenarios["scenarios"][4]["rejected_artwork_ids"] == ["ag_70351"]


@pytest.mark.skipif(find_swipl() is None, reason="SWI-Prolog is not installed")
def test_interest_poc_plunit_suite_passes():
    completed = subprocess.run(
        [
            str(find_swipl()),
            "-q",
            "-s",
            str(ROOT / "logic" / "tests" / "test_interest_poc.pl"),
            "-g",
            "run_tests",
            "-t",
            "halt",
        ],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "Warning:" not in completed.stderr

