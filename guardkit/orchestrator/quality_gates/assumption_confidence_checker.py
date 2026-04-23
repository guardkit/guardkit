"""Assumption-confidence warn-mode gate (TASK-FIX-RWOP1.4a).

``installer/core/commands/feature-spec.md:337`` declares that the Coach
"is expected to verify all low-confidence assumptions before accepting
the specification." Before this module, no code enforced that claim —
the Coach validator had no producer writing a Coach-consumable verdict,
so `/feature-spec` runs with unconfirmed `confidence: low` rows would
proceed silently and the pipeline would look green.

This module provides the producer side of the TASK-FIX-RWOP1.3.1
"runner without producer" fix shape, adapted for Phase 5 assumptions:

    producer (this module)         -> task_work_results.json
                                       ["unconfirmed_low_confidence_assumptions"]
    consumer (coach_validator.py)  -> non-blocking warning in Coach's
                                       approval issues list

The consumer raises a **warning, not a failure** — the decision was
scoped in TASK-FIX-RWOP1.4 Part A. Escalation to block-mode is a
separate task driven by evidence that warn-mode is being ignored.

Shape contract
==============

``check_unconfirmed_low_confidence_assumptions(workspace_root)`` returns
a dict with the same invariants as the TASK-FIX-RWOP1.3.1 producers
(never raises; checker crashes become a soft ``checker_error`` status)::

    {
        "status": "ok" | "warning" | "checker_error",
        "unconfirmed": [
            {"file": str, "id": str, "scenario": str,
             "assumption": str, "human_response": str | None},
            ...
        ],
        "files_scanned": int,
        "files_skipped": int,
        "message": str | None,  # populated on checker_error
    }

Filter policy
=============

A row is **unconfirmed** when both:

- ``confidence == "low"`` (high/medium rows are out of scope per feature-spec.md)
- ``human_response`` is not exactly ``"confirmed"``

Non-confirmed values — missing key, ``"deferred"``, ``"overridden: …"`` —
all flag as unconfirmed. This matches the literal task spec wording
(`no matching human_response: confirmed entry`). A future policy
relaxation (e.g. treating `overridden:` as human-handled) would change
the single predicate below.

Discovery glob
==============

Scans ``{workspace_root}/features/**/_assumptions.yaml`` to match
feature-spec.md's declared output path. A missing ``features/``
directory yields ``status: "ok"`` with ``files_scanned: 0`` — the
expected shape for tasks that don't touch feature specs at all.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml

logger = logging.getLogger(__name__)


_CONFIRMED = "confirmed"
_LOW_CONFIDENCE = "low"


def check_unconfirmed_low_confidence_assumptions(
    workspace_root: Union[str, Path],
) -> Dict[str, Any]:
    """Scan ``features/**/_assumptions.yaml`` for unconfirmed low-confidence rows.

    Parameters
    ----------
    workspace_root : str | Path
        Directory under which to glob. Typically the AutoBuild
        worktree root (``.guardkit/worktrees/TASK-XXX/``) or the repo
        root for non-AutoBuild runs.

    Returns
    -------
    Dict[str, Any]
        Coach-consumable block (see module docstring for shape).
        Never raises — checker crashes become ``status: "checker_error"``.
    """
    root = Path(workspace_root)
    try:
        return _scan(root)
    except Exception as exc:  # noqa: BLE001 — producer invariant: never raise
        logger.warning(
            "assumption_confidence checker raised %s; recording checker_error.",
            exc.__class__.__name__,
        )
        return {
            "status": "checker_error",
            "unconfirmed": [],
            "files_scanned": 0,
            "files_skipped": 0,
            "message": f"{exc.__class__.__name__}: {exc}",
        }


def _scan(root: Path) -> Dict[str, Any]:
    """Inner scan — may raise; wrapped by the public entry point."""
    features_dir = root / "features"
    if not features_dir.is_dir():
        return {
            "status": "ok",
            "unconfirmed": [],
            "files_scanned": 0,
            "files_skipped": 0,
            "message": None,
        }

    unconfirmed: List[Dict[str, Any]] = []
    files_scanned = 0
    files_skipped = 0

    for yaml_path in sorted(features_dir.rglob("_assumptions.yaml")):
        files_scanned += 1
        rows = _read_assumption_rows(yaml_path)
        if rows is None:
            files_skipped += 1
            continue

        rel_path = _relative(yaml_path, root)
        for row in rows:
            if not _is_unconfirmed_low_confidence(row):
                continue
            unconfirmed.append({
                "file": rel_path,
                "id": _str_or_unknown(row.get("id")),
                "scenario": _str_or_unknown(row.get("scenario")),
                "assumption": _str_or_unknown(row.get("assumption")),
                "human_response": row.get("human_response"),
            })

    status = "warning" if unconfirmed else "ok"
    return {
        "status": status,
        "unconfirmed": unconfirmed,
        "files_scanned": files_scanned,
        "files_skipped": files_skipped,
        "message": None,
    }


def _read_assumption_rows(yaml_path: Path) -> Optional[List[Dict[str, Any]]]:
    """Parse an _assumptions.yaml file, returning its ``assumptions`` list.

    Returns ``None`` when the file is unparseable or structurally
    unexpected — the caller counts it as skipped rather than failing
    the whole gate.
    """
    try:
        raw = yaml.safe_load(yaml_path.read_text())
    except (yaml.YAMLError, OSError) as exc:
        logger.warning(
            "assumption_confidence: could not read %s (%s); skipping file.",
            yaml_path,
            exc.__class__.__name__,
        )
        return None

    if raw is None:
        return []
    if not isinstance(raw, dict):
        logger.warning(
            "assumption_confidence: %s is not a mapping; skipping.", yaml_path
        )
        return None

    rows = raw.get("assumptions")
    if rows is None:
        return []
    if not isinstance(rows, list):
        logger.warning(
            "assumption_confidence: %s has non-list 'assumptions'; skipping.",
            yaml_path,
        )
        return None

    # Filter out non-mapping entries defensively — a malformed row
    # shouldn't drop the whole file.
    return [r for r in rows if isinstance(r, dict)]


def _is_unconfirmed_low_confidence(row: Dict[str, Any]) -> bool:
    """True when the row is low-confidence AND not explicitly confirmed."""
    confidence = row.get("confidence")
    if not isinstance(confidence, str) or confidence.strip().lower() != _LOW_CONFIDENCE:
        return False

    human_response = row.get("human_response")
    if not isinstance(human_response, str):
        return True
    return human_response.strip().lower() != _CONFIRMED


def _str_or_unknown(value: Any) -> str:
    return str(value) if isinstance(value, str) and value.strip() else "unknown"


def _relative(path: Path, root: Path) -> str:
    """Return path relative to root when possible; absolute string otherwise."""
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)
