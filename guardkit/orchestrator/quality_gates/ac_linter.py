"""Assertable-AC linter — plan-level aggregator (warn-mode v1).

Runs after ``/feature-plan`` generates its tasks. For each task, delegates
to :func:`classify_with_warnings` and collects the resulting
:class:`UnverifiableACWarning` instances.

Architectural invariant — read before editing
---------------------------------------------
This module MUST NOT contain its own regexes, heuristics, pattern
constants, or confidence thresholds. It is a report-mode wrapper around
:mod:`criteria_classifier`, full stop.

Rationale: ``criteria_classifier`` is the single source of truth for "is
this AC verifiable?". A parallel classification path here would (a) drift
from the classifier over time, (b) make v1-warn → v2-block promotion a
multi-file rewrite instead of a one-line threshold change in
``criteria_classifier.UNVERIFIABLE_CONFIDENCE_THRESHOLD``.

The ``test_linter_has_no_independent_patterns`` test greps this module's
source and fails if that invariant is broken.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List

from guardkit.orchestrator.quality_gates.criteria_classifier import (
    UnverifiableACWarning,
    classify_with_warnings,
)


def lint_plan_warnings(tasks: Iterable[Dict[str, Any]]) -> List[UnverifiableACWarning]:
    """Aggregate unverifiable-AC warnings across a plan's tasks.

    Parameters
    ----------
    tasks : Iterable[Dict[str, Any]]
        Each task dict must contain at least ``id`` (str) and
        ``acceptance_criteria`` (List[str]). Extra keys are ignored.

    Returns
    -------
    List[UnverifiableACWarning]
        Warnings flattened across all tasks, in task-then-AC order.
    """
    warnings: List[UnverifiableACWarning] = []
    for task in tasks:
        task_id = task.get("id", "<unknown>")
        criteria = task.get("acceptance_criteria", []) or []
        _, task_warnings = classify_with_warnings(criteria, task_id=task_id)
        warnings.extend(task_warnings)
    return warnings


def format_warning_summary(warnings: List[UnverifiableACWarning]) -> str:
    """Render warnings as the human-readable block surfaced by /feature-plan.

    Intentionally plain-text — this is what the planner appends to its
    output. Callers (e.g. the LLM-refinement roundtrip) may render
    differently.
    """
    if not warnings:
        return "AC-quality review: 0 unverifiable acceptance criteria detected."

    lines: List[str] = [
        f"AC-quality review: {len(warnings)} unverifiable acceptance "
        f"criteria detected (warn-mode, non-blocking).",
        "",
    ]
    by_task: Dict[str, List[UnverifiableACWarning]] = {}
    for w in warnings:
        by_task.setdefault(w.task_id, []).append(w)

    for task_id, task_warnings in by_task.items():
        lines.append(f"  {task_id}:")
        for w in task_warnings:
            lines.append(f"    - {w.ac_text}")
            lines.append(f"      reason: {w.reason}")
            if w.suggested_rewrite_hint:
                lines.append(f"      suggested: {w.suggested_rewrite_hint}")
    return "\n".join(lines)
