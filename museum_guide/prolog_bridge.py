"""Narrow Phase 0 subprocess interface for the pilot Prolog proof."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

SAFE_ID = re.compile(r"^[a-z][a-z0-9_]*$")


class PrologError(RuntimeError):
    pass


def find_swipl() -> Path | None:
    configured = os.environ.get("SWIPL_PATH")
    found = shutil.which("swipl")
    candidates = [
        Path(configured) if configured else None,
        Path(found) if found else None,
        Path(__file__).resolve().parents[1] / ".tools" / "swipl" / "bin" / "swipl.exe",
    ]
    return next((path for path in candidates if path and path.is_file()), None)


def run_pilot_query(
    facts_path: str | Path,
    rules_path: str | Path,
    artwork_id: str,
    *,
    timeout_seconds: float = 10,
    swipl_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    """Query only an allowlisted atom; raw visitor text never enters Prolog."""

    if not SAFE_ID.fullmatch(artwork_id):
        raise PrologError(f"Unsafe Prolog topic ID: {artwork_id!r}")
    executable = Path(swipl_path) if swipl_path else find_swipl()
    if executable is None:
        raise PrologError("SWI-Prolog executable not found; set SWIPL_PATH")
    facts = Path(facts_path).resolve()
    rules = Path(rules_path).resolve()
    if not facts.is_file() or not rules.is_file():
        raise PrologError(f"Missing Prolog input: facts={facts}, rules={rules}")
    goal = (
        "findall(_{topic:T,kind:K,rule_id:R,fact_ids:F},"
        f"artwork_context({artwork_id},T,K,R,F),Rows),"
        "json_write_dict(current_output,Rows),nl"
    )
    command = [
        str(executable),
        "-q",
        "-g",
        "use_module(library(http/json))",
        "-s",
        str(facts),
        "-s",
        str(rules),
        "-g",
        goal,
        "-t",
        "halt",
    ]
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise PrologError(f"SWI-Prolog timed out after {timeout_seconds}s") from exc
    if completed.returncode != 0:
        raise PrologError(
            f"SWI-Prolog exited {completed.returncode}: {completed.stderr.strip()}"
        )
    if completed.stderr.strip():
        raise PrologError(f"SWI-Prolog wrote to stderr: {completed.stderr.strip()}")
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise PrologError(f"Invalid JSON from SWI-Prolog: {completed.stdout!r}") from exc
    if not isinstance(result, list):
        raise PrologError(f"Expected a JSON list from SWI-Prolog, got {type(result).__name__}")
    return result

