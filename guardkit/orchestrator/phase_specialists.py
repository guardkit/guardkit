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
from typing import Dict, Iterable, List, Optional, Sequence, Set

logger = logging.getLogger(__name__)


# Filenames in `.claude/agents/` and `.claude/rules/guidance/` whose stems end
# in one of these suffixes are treated as installed specialist agents for the
# template. Other guidance files (e.g. `database.md`, `fastapi.md`,
# `agent-development.md`) are topic notes, not specialists, and are ignored.
SPECIALIST_NAME_SUFFIXES: tuple[str, ...] = (
    "-specialist",
    "-engineer",
    "-architect",
)


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


def discover_template_specialists(
    workspace_root: Optional[Path] = None,
) -> Set[str]:
    """Return the set of specialist names installed in the workspace.

    Scans the workspace's ``.claude/agents/*.md`` and
    ``.claude/rules/guidance/*.md`` directories and returns the stems of files
    whose names end in one of :data:`SPECIALIST_NAME_SUFFIXES`. Topic-style
    guidance (``database.md``, ``fastapi.md``, ``README.md``) is excluded.

    Companion ``-ext.md`` files emitted by `/agent-enhance` are de-duplicated
    against their canonical counterpart so the canonical specialist name wins.

    Parameters
    ----------
    workspace_root : Optional[Path]
        Directory to inspect. Defaults to the current working directory. The
        autobuild path passes the worktree root; the interactive path passes
        the project root.

    Returns
    -------
    Set[str]
        Set of specialist stems present in the workspace, e.g.
        ``{"langchain-tool-decorator-specialist",
           "pytest-agent-testing-specialist"}``. Empty when neither directory
        exists or when no files match the specialist-suffix convention.
    """
    root = Path(workspace_root) if workspace_root else Path.cwd()
    candidate_dirs = [
        root / ".claude" / "agents",
        root / ".claude" / "rules" / "guidance",
    ]
    found: Set[str] = set()
    for directory in candidate_dirs:
        if not directory.is_dir():
            continue
        for path in directory.glob("*.md"):
            stem = path.stem
            # `/agent-enhance` writes a companion `<name>-ext.md` next to the
            # canonical specialist. Strip the suffix so we count the agent
            # once, under its canonical name.
            if stem.endswith("-ext"):
                stem = stem[: -len("-ext")]
            if not stem.endswith(SPECIALIST_NAME_SUFFIXES):
                continue
            found.add(stem)
    return found


def _normalize_for_match(value: str) -> str:
    """Lowercase and strip common separators so tag/spec names match loosely."""
    return value.lower().replace("-", "").replace("_", "")


def _select_by_tag_affinity(
    available: Set[str],
    task_tags: Sequence[str],
) -> Optional[str]:
    """Return the first available specialist whose name matches any task tag.

    The match is intentionally minimal — substring-based on a normalised
    (lowercased, hyphen/underscore-stripped) form. A comprehensive
    tag→specialist taxonomy is explicitly out of scope (see TASK-GK-PROF-001
    "Scope discipline"); this only ensures that an obvious tag like
    ``"tool-decorator"`` lines up with ``"langchain-tool-decorator-specialist"``
    when the template happens to ship one.
    """
    if not task_tags or not available:
        return None
    sorted_available = sorted(available)
    for tag in task_tags:
        if not tag:
            continue
        norm_tag = _normalize_for_match(tag)
        if not norm_tag:
            continue
        for spec in sorted_available:
            if norm_tag in _normalize_for_match(spec):
                return spec
    return None


def phase_3_specialist_for_stack(
    stack_template: Optional[str],
    workspace_root: Optional[Path] = None,
    task_tags: Optional[Sequence[str]] = None,
) -> str:
    """Return the Phase-3 specialist agent name for a stack template.

    When ``workspace_root`` points at a workspace whose ``.claude/agents`` or
    ``.claude/rules/guidance`` directory carries an installed specialist set,
    the resolution prefers a name actually present in that set. The fallback
    chain is:

    1. **template-discovered + tag-matched**: a specialist whose name aligns
       with one of ``task_tags`` and is installed in the workspace.
    2. **profile-default-if-installed**: the entry from
       :data:`STACK_TO_PHASE_3_SPECIALIST` for ``stack_template`` *iff* it is
       installed in the workspace.
    3. **legacy fallback**: ``"python-api-specialist"`` *iff* it is installed
       in the workspace (back-compat for templates that ship it).
    4. **informational fallback**: :data:`GENERIC_PHASE_3_FALLBACK` when the
       workspace has specialists installed but none of the above match — this
       prevents the advisory from naming a specialist the operator does not
       have.

    When ``workspace_root`` is ``None`` (or its discovery yields nothing), the
    function preserves the historical behavior: profile-default if known,
    otherwise the generic fallback. This keeps callers that have no workspace
    handle (e.g. unit tests, ad-hoc tooling) backward-compatible.

    Parameters
    ----------
    stack_template : Optional[str]
        Template identifier (from ``.claude/settings.json -> project.template``).
    workspace_root : Optional[Path]
        Workspace whose installed specialist set should drive resolution.
    task_tags : Optional[Sequence[str]]
        Task tags used for minimal tag→specialist affinity matching.
    """
    profile_default = (
        STACK_TO_PHASE_3_SPECIALIST.get(stack_template)
        if stack_template
        else None
    )

    available = discover_template_specialists(workspace_root) if workspace_root else set()

    if available:
        tag_match = _select_by_tag_affinity(available, task_tags or ())
        if tag_match is not None:
            return tag_match
        if profile_default and profile_default in available:
            return profile_default
        if "python-api-specialist" in available:
            return "python-api-specialist"
        # Workspace ships specialists but none match this template's expected
        # shape. Returning the generic label (rather than a hardcoded literal
        # the operator does not have) downgrades the advisory to
        # informational, satisfying AC-3.
        return GENERIC_PHASE_3_FALLBACK

    # No workspace discovery (or no installed specialists) — fall back to the
    # historical map so isolated callers keep getting a useful label.
    if profile_default:
        return profile_default
    return GENERIC_PHASE_3_FALLBACK


def specialist_for_phase(
    phase: str,
    stack_template: Optional[str] = None,
    workspace_root: Optional[Path] = None,
    task_tags: Optional[Sequence[str]] = None,
) -> str:
    """Return the specialist agent name for a single phase identifier.

    Parameters
    ----------
    phase : str
        Phase identifier, e.g. ``"3"``, ``"4"``, ``"5"``, ``"2.5B"``.
    stack_template : Optional[str]
        Used only to resolve Phase 3. Ignored for other phases.
    workspace_root : Optional[Path]
        Used only to resolve Phase 3. Ignored for other phases.
    task_tags : Optional[Sequence[str]]
        Used only to resolve Phase 3. Ignored for other phases.
    """
    if phase in STATIC_PHASE_SPECIALISTS:
        return STATIC_PHASE_SPECIALISTS[phase]
    if phase == "3":
        return phase_3_specialist_for_stack(
            stack_template,
            workspace_root=workspace_root,
            task_tags=task_tags,
        )
    # Unknown phase — return the phase descriptor as-is rather than guessing.
    return PHASE_DESCRIPTIONS.get(phase, f"Phase {phase} specialist")


def render_missing_phase_list(
    missing_phases: Iterable[str],
    stack_template: Optional[str] = None,
    workspace_root: Optional[Path] = None,
    task_tags: Optional[Sequence[str]] = None,
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
    workspace_root : Optional[Path]
        Workspace whose installed specialist set should drive Phase-3
        resolution. Other phases are stack-independent.
    task_tags : Optional[Sequence[str]]
        Task tags used for minimal tag→specialist affinity matching when
        resolving Phase 3.

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
        specialist = specialist_for_phase(
            phase,
            stack_template=stack_template,
            workspace_root=workspace_root,
            task_tags=task_tags,
        )
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
    "SPECIALIST_NAME_SUFFIXES",
    "detect_stack_template",
    "discover_template_specialists",
    "phase_3_specialist_for_stack",
    "specialist_for_phase",
    "render_missing_phase_list",
]
