from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from museum_guide.artgraph import load_graph
from museum_guide.prolog_bridge import find_swipl

ROOT = Path(__file__).resolve().parents[1]


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_real_candidate_inventory_satisfies_phase_0_5_filters():
    report = json.loads(
        (ROOT / "docs" / "phase_0_5_candidates.json").read_text(encoding="utf-8")
    )
    assert len(report["candidates"]) == 5
    assert report["recommended_candidate_id"] == "artist_ag_1210"
    for candidate in report["candidates"]:
        stats = candidate["stats"]
        assert candidate["movement_ids"]
        assert stats["artwork_count"] >= 3
        assert stats["entity_type_count"] >= 4
        assert stats["shared_relationship_count"] >= 1
        assert stats["independent_path_count"] >= 3
    recommended = report["candidates"][0]
    assert recommended["stats"]["relationship_count"] == 47
    assert recommended["stats"]["entity_type_count"] == 10
    assert "artwork_artist_movement" in recommended["independent_paths"]


def test_phase_0_5_manifest_hashes_and_viewer_are_reproducible():
    manifest = json.loads(
        (ROOT / "docs" / "dataset_manifest.json").read_text(encoding="utf-8")
    )["phase_0_5"]
    paths_and_hashes = {
        manifest["selection_artifact"]: manifest["selection_artifact_sha256"],
        manifest["recommended_sample"]: manifest["recommended_sample_sha256"],
        manifest["topic_catalog"]: manifest["topic_catalog_sha256"],
        manifest["prolog_facts"]: manifest["prolog_facts_sha256"],
        manifest["viewer"]: manifest["viewer_sha256"],
    }
    for relative_path, expected_hash in paths_and_hashes.items():
        assert file_sha256(ROOT / relative_path) == expected_hash
    viewer = (ROOT / manifest["viewer"]).read_text(encoding="utf-8")
    assert "ArtGraph Phase 0.5 Explorer" in viewer
    assert "predicate_uri" in viewer
    assert "source_uri" in viewer
    assert "morris-louis" in viewer
    assert len(load_graph(ROOT / manifest["recommended_sample"])) == 99


@pytest.mark.skipif(find_swipl() is None, reason="SWI-Prolog is not installed")
def test_phase_0_5_real_plunit_suite_passes():
    completed = subprocess.run(
        [
            str(find_swipl()),
            "-q",
            "-s",
            str(ROOT / "logic" / "tests" / "test_phase_0_5_pilot.pl"),
            "-g",
            "run_tests",
            "-t",
            "halt",
        ],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "Warning:" not in completed.stderr

