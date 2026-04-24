"""Phase → specialist-agent name resolution for enriched error messages.

TASK-FIX-7A07: Coach feedback on agent_invocations_violation and the
post-loop summary hint both need to name the specific sub-agent the Player
should invoke via the Task tool (not just a phase number). Phase 4 is always
``test-orchestrator`` and Phase 5 is always ``code-reviewer``; Phase 3's
specialist is stack-dependent (``python-api-specialist``, ``react-typescript-specialist``,
``dotnet-specialist``, etc.).

This module is intentionally a thin best-effort lookup:

* Phase 4 and Phase 5 names are hard-coded because they are genuinely stack-
  agnostic across GuardKit (single specialist per phase, not a discovery
  surface).
* Phase 3's specialist is derived from ``.claude/settings.json`` ->
  ``project.template`` when available. When unavailable, callers get a generic
  "stack-specific Phase-3 specialist" label and should NOT hardcode.

No imports from the agent_invoker / agent_discovery subsystems — those carry
heavyweight dependencies (SDK, etc.) and are not needed for a name lookup.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, Iterable, List, Optional

logger = logging.getLogger(__name__)


# Phase descriptions for human-readable error messages. Mirror the
# descriptions in installer/core/commands/lib/agent_invocation_validator.py.
PHASE_DESCRIPTIONS: Dict[str, str] = {
    "2": "Planning",
    "2.5B": "Architectural Review",
    "2.7": "Complexity Evaluation",
    "3": "Implementation",
    "4": "Testing",
    "5": "Code Review",
}

# Phases whose specialist is stack-independent — one canonical agent per phase.
STATIC_PHASE_SPECIALISTS: Dict[str, str] = {
    "4": "test-orchestrator",
    "5": "code-reviewer",
    "2.5B": "architectural-reviewer",
}

# Stack-template identifiers (matching ``.claude/settings.json`` ->
# ``project.template``) to their canonical Phase-3 specialist. If a template
# is not in this map, the caller receives the generic fallback label.
STACK_TO_PHASE_3_SPECIALIST: Dict[str, str] = {
    "fastapi-python": "python-api-specialist",
    "python-library": "python-api-specialist",
    "nats-asyncio-service": "python-api-specialist",
    "langchain-deepagents": "python-api-specialist",
    "langchain-deepagents-orchestrator": "python-api-specialist",
    "langchain-deepagents-weighted-evaluation": "python-api-specialist",
    "react-typescript": "react-typescript-specialist",
    "nextjs-fullstack": "react-typescript-specialist",
    "react-fastapi-monorepo": "react-typescript-specialist",
    "dotnet-railway-fastendpoints": "dotnet-specialist",
}

GENERIC_PHASE_3_FALLBACK = "the stack-specific Phase-3 specialist"
"""Fallback label when stack detection is unavailable; do NOT hardcode a name."""


def detect_stack_template(workspace_root: Optional[Path] = None) -> Optional[str]:
    """Return the ``project.template`` string from ``.claude/settings.json``, or None.

    Parameters
    ----------
    workspace_root : Optional[Path]
        Directory to search for ``.claude/settings.json``. Defaults to the
        current working directory. The autobuild path passes the worktree
        root; the interactive path passes the project root.

    Returns
    -------
    Optional[str]
        The template identifier (e.g. ``"fastapi-python"``) if present and
        parseable, else ``None``.
    """
    root = Path(workspace_root) if workspace_root else Path.cwd()
    settings_path = root / ".claude" / "settings.json"
    if not settings_path.exists():
        return None
    try:
        data = json.loads(settings_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.debug("Failed to read %s: %s", settings_path, exc)
        return None
    if not isinstance(data, dict):
        return None
    project = data.get("project")
    if not isinstance(project, dict):
        return None
    template = project.get("template")
    if isinstance(template, str) and template:
        return template
    return None


def phase_3_specialist_for_stack(
    stack_template: Optional[str],
) -> str:
    """Return the Phase-3 specialist agent name for a stack template.

    Falls back to ``GENERIC_PHASE_3_FALLBACK`` when the template is unknown or
    None — callers should render the fallback verbatim rather than guessing.

    Parameters
    ----------
    stack_template : Optional[str]
        Template identifier (from ``.claude/settings.json -> project.template``).
    """
    if stack_template and stack_template in STACK_TO_PHASE_3_SPECIALIST:
        return STACK_TO_PHASE_3_SPECIALIST[stack_template]
    return GENERIC_PHASE_3_FALLBACK


def specialist_for_phase(
    phase: str,
    stack_template: Optional[str] = None,
) -> str:
    """Return the specialist agent name for a single phase identifier.

    Parameters
    ----------
    phase : str
        Phase identifier, e.g. ``"3"``, ``"4"``, ``"5"``, ``"2.5B"``.
    stack_template : Optional[str]
        Used only to resolve Phase 3. Ignored for other phases.
    """
    if phase in STATIC_PHASE_SPECIALISTS:
        return STATIC_PHASE_SPECIALISTS[phase]
    if phase == "3":
        return phase_3_specialist_for_stack(stack_template)
    # Unknown phase — return the phase descriptor as-is rather than guessing.
    return PHASE_DESCRIPTIONS.get(phase, f"Phase {phase} specialist")


def render_missing_phase_list(
    missing_phases: Iterable[str],
    stack_template: Optional[str] = None,
) -> List[str]:
    """Render a list of 'Phase N: `agent-name` (description)' lines.

    Used by both the Coach feedback issue-construction (AC-3) and the
    post-loop summary hint renderer (AC-2).

    Parameters
    ----------
    missing_phases : Iterable[str]
        Phase identifiers that are missing (e.g. ``["4", "5"]``).
    stack_template : Optional[str]
        Stack template for Phase-3 specialist resolution.

    Returns
    -------
    List[str]
        One formatted line per missing phase, e.g.::

            ["Phase 3: `python-api-specialist` (Implementation)",
             "Phase 4: `test-orchestrator` (Testing)",
             "Phase 5: `code-reviewer` (Code Review)"]
    """
    lines: List[str] = []
    for phase in missing_phases:
        specialist = specialist_for_phase(phase, stack_template)
        description = PHASE_DESCRIPTIONS.get(phase, "")
        if description:
            lines.append(f"Phase {phase}: `{specialist}` ({description})")
        else:
            lines.append(f"Phase {phase}: `{specialist}`")
    return lines


__all__ = [
    "PHASE_DESCRIPTIONS",
    "STATIC_PHASE_SPECIALISTS",
    "STACK_TO_PHASE_3_SPECIALIST",
    "GENERIC_PHASE_3_FALLBACK",
    "detect_stack_template",
    "phase_3_specialist_for_stack",
    "specialist_for_phase",
    "render_missing_phase_list",
]
