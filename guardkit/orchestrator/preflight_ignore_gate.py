"""Pre-turn-1 ``git check-ignore`` fail-fast gate (TASK-FIX-CAUD-PREFLIGHT-C3B0).

Closes deferred AC-005 of TASK-FIX-CAUD-J6F1. The J6F1 incident itself was
about claim-audit path normalisation and is fully closed by its
AC-001/002/003/006. AC-005 is hardening for a *different* scenario: the
class of failure where a planned target file genuinely IS git-ignored, so
the Player burns SDK turns writing a file that cannot subsequently be
tracked, observed by porcelain, or verified by the Coach.

The gate fires before turn 1 of any autobuild task. It:

1. Loads the task's planned target file list (implementation plan on disk
   if present; otherwise task frontmatter ``files_to_create`` /
   ``files_to_modify``).
2. Walks each planned target through ``git check-ignore -v --no-index``
   in the worktree.
3. If any target IS ignored, returns a ``BLOCKED`` result naming each
   matched rule in the canonical ``<source>:<line>:<pattern>`` format.
   The caller fail-fasts before the SDK is invoked.
4. If no plan / file list is available, returns ``SKIPPED`` (does NOT
   fail-open with a warning — the no-source path is intentionally a
   no-op, identical to the no-plan path in plan-audit).

The check-ignore subprocess wrapper duplicates the canonical idiom from
``coach_verification._classify_dropped_path`` / ``_git_check_ignore_rule``
deliberately (per the task brief: "refactor or duplicate at the
orchestrator-side as appropriate"). The Coach helpers are bound methods
on ``CoachVerifier`` and tied to its ``self.worktree_path``; lifting them
out adds risk during the active gate-stack freeze and is out of scope
for this hardening task.
"""

from __future__ import annotations

import logging
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---", re.DOTALL)
_CHECK_IGNORE_TIMEOUT_SECONDS = 30

# Status constants. Module-level so callers can compare without
# importing the dataclass.
STATUS_PASSED = "passed"
STATUS_SKIPPED = "skipped"
STATUS_BLOCKED = "blocked"


@dataclass
class IgnoreMatch:
    """A single planned target that the worktree's ignore rules match."""

    path: str
    rule: str  # ``<source>:<linenum>:<pattern>`` as emitted by check-ignore -v.


@dataclass
class PreflightResult:
    """Outcome of the pre-turn-1 ignore gate.

    ``status`` is one of ``STATUS_PASSED``, ``STATUS_SKIPPED``,
    ``STATUS_BLOCKED``. When ``blocked``, ``matches`` is non-empty and
    ``rebase_hint`` indicates whether at least one match came from the
    project-root ``.gitignore`` (the rebase-fixable case).
    """

    status: str
    matches: List[IgnoreMatch] = field(default_factory=list)
    skip_reason: Optional[str] = None
    rebase_hint: bool = False


def run_preflight_ignore_gate(
    task_id: str, worktree_path: Path
) -> PreflightResult:
    """Top-level entry point: run the pre-turn-1 ignore gate.

    Args:
        task_id: Task identifier (e.g. ``"TASK-XYZ"``).
        worktree_path: Path to the worktree the Player will execute in.

    Returns:
        A ``PreflightResult``. ``passed`` and ``skipped`` are both
        non-blocking; only ``blocked`` should cause the caller to
        fail-fast.
    """
    planned_targets = load_planned_targets(task_id, worktree_path)
    if planned_targets is None:
        return PreflightResult(
            status=STATUS_SKIPPED,
            skip_reason="no implementation plan and no frontmatter files_to_create / files_to_modify list",
        )
    if not planned_targets:
        return PreflightResult(
            status=STATUS_SKIPPED,
            skip_reason="plan / frontmatter present but empty file list",
        )

    matches: List[IgnoreMatch] = []
    for target in planned_targets:
        rule = check_ignore_one(worktree_path, target)
        if rule is not None:
            matches.append(IgnoreMatch(path=target, rule=rule))

    if not matches:
        return PreflightResult(status=STATUS_PASSED)

    rebase_hint = any(is_project_root_gitignore(m.rule) for m in matches)
    return PreflightResult(
        status=STATUS_BLOCKED, matches=matches, rebase_hint=rebase_hint
    )


def load_planned_targets(
    task_id: str, worktree_path: Path
) -> Optional[List[str]]:
    """Load the planned target file list for ``task_id``.

    Lookup order:

    1. ``docs/state/{task_id}/implementation_plan.md`` parsed via
       ``PlanMarkdownParser``.
    2. ``docs/state/{task_id}/implementation_plan.json`` parsed as JSON.
    3. Task frontmatter ``files_to_create`` and ``files_to_modify``
       lists.

    Returns ``None`` when none of the above are present or parseable.
    The caller treats ``None`` as "skip pre-flight" — identical to the
    no-plan branch in plan-audit, per the AC-005 brief.
    """
    plan_targets = _load_targets_from_plan(task_id, worktree_path)
    if plan_targets is not None:
        return plan_targets
    return _load_targets_from_task_frontmatter(task_id, worktree_path)


def _load_targets_from_plan(
    task_id: str, worktree_path: Path
) -> Optional[List[str]]:
    """Return ``files_to_create + files_to_modify`` from the saved plan.

    Returns ``None`` when no plan is on disk. Returns an empty list when
    a plan exists but neither list is populated — the caller will then
    fall through to the frontmatter source.
    """
    state_dir = worktree_path / "docs" / "state" / task_id
    md_path = state_dir / "implementation_plan.md"
    json_path = state_dir / "implementation_plan.json"

    plan_data: Optional[Dict[str, Any]] = None

    if md_path.exists():
        try:
            from installer.core.commands.lib.plan_markdown_parser import (
                PlanMarkdownParser,
                PlanMarkdownParserError,
            )
        except ImportError as exc:
            logger.warning(
                "preflight_ignore_gate: PlanMarkdownParser unavailable (%s); "
                "falling back to JSON for %s",
                exc,
                task_id,
            )
        else:
            try:
                parser = PlanMarkdownParser()
                plan_data = parser.parse_file(md_path)
            except (PlanMarkdownParserError, FileNotFoundError, OSError) as exc:
                logger.warning(
                    "preflight_ignore_gate: markdown plan parse failed (%s) for %s; "
                    "falling back to JSON.",
                    exc,
                    task_id,
                )

    if plan_data is None and json_path.exists():
        import json

        try:
            plan_data = json.loads(json_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            logger.warning(
                "preflight_ignore_gate: JSON plan parse failed (%s) for %s.",
                exc,
                task_id,
            )

    if plan_data is None:
        return None

    inner = plan_data.get("plan") if isinstance(plan_data, dict) else None
    if not isinstance(inner, dict):
        # Some legacy callers store the lists at the top level.
        inner = plan_data if isinstance(plan_data, dict) else {}

    files_to_create = _coerce_string_list(inner.get("files_to_create"))
    files_to_modify = _coerce_string_list(inner.get("files_to_modify"))
    combined = files_to_create + files_to_modify
    # Falling through to frontmatter when both lists are empty matches
    # the AC-005 spirit: an empty plan is "no usable list", not "no
    # ignored targets".
    if not combined:
        return None
    return combined


def _load_targets_from_task_frontmatter(
    task_id: str, worktree_path: Path
) -> Optional[List[str]]:
    """Return ``files_to_create + files_to_modify`` from task frontmatter.

    Searches the standard task directories (backlog, design_approved,
    in_progress, in_review, completed, blocked) for a file matching
    ``{task_id}*.md``. Returns ``None`` when no file is found or the
    frontmatter has neither list populated.
    """
    task_file = _find_task_file(task_id, worktree_path)
    if task_file is None:
        return None

    try:
        content = task_file.read_text(encoding="utf-8")
    except OSError as exc:
        logger.warning(
            "preflight_ignore_gate: failed to read task file %s: %s",
            task_file,
            exc,
        )
        return None

    match = _FRONTMATTER_RE.match(content)
    if not match:
        return None

    try:
        import yaml
    except ImportError:
        logger.warning(
            "preflight_ignore_gate: PyYAML unavailable; cannot parse task "
            "frontmatter for %s.",
            task_id,
        )
        return None

    try:
        frontmatter = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError as exc:
        logger.warning(
            "preflight_ignore_gate: YAML parse failed for %s: %s", task_file, exc
        )
        return None

    if not isinstance(frontmatter, dict):
        return None

    files_to_create = _coerce_string_list(frontmatter.get("files_to_create"))
    files_to_modify = _coerce_string_list(frontmatter.get("files_to_modify"))
    combined = files_to_create + files_to_modify
    if not combined:
        return None
    return combined


def _find_task_file(task_id: str, worktree_path: Path) -> Optional[Path]:
    """Locate the markdown task file for ``task_id`` under ``worktree_path``.

    Mirrors ``AgentInvoker._find_task_file`` (kept local to avoid a
    cross-module dependency from a gate that fires before AgentInvoker
    is fully active).
    """
    task_dirs = (
        worktree_path / "tasks" / "backlog",
        worktree_path / "tasks" / "design_approved",
        worktree_path / "tasks" / "in_progress",
        worktree_path / "tasks" / "in_review",
        worktree_path / "tasks" / "completed",
        worktree_path / "tasks" / "blocked",
    )
    for task_dir in task_dirs:
        if not task_dir.exists():
            continue
        for candidate in task_dir.rglob(f"{task_id}*.md"):
            return candidate
    return None


def _coerce_string_list(value: Any) -> List[str]:
    """Coerce a frontmatter / plan list field into ``List[str]``.

    Plans and frontmatter may carry either bare path strings (the
    expected shape) or dicts like ``{"path": "...", "rationale": "..."}``
    (older TASK-69DC-shaped schemas). We accept both, drop anything we
    cannot interpret, and silently ignore non-string ``path`` values.
    """
    if not isinstance(value, list):
        return []
    out: List[str] = []
    for item in value:
        if isinstance(item, str) and item.strip():
            out.append(item.strip())
        elif isinstance(item, dict):
            path = item.get("path")
            if isinstance(path, str) and path.strip():
                out.append(path.strip())
    return out


def check_ignore_one(worktree_path: Path, path: str) -> Optional[str]:
    """Return the matched rule for ``path`` or ``None`` if not ignored.

    Wraps ``git check-ignore -v --no-index -- <path>`` in the worktree.
    ``--no-index`` makes the check evaluate the path string against
    ignore rules even when the path does not yet exist on disk — which
    is the common case for planned (not-yet-created) targets.

    Returns the canonical ``<source>:<linenum>:<pattern>`` prefix from
    the first output line. Returns ``None`` on:

    * exit 1 (path is not ignored) — the expected pass-case;
    * subprocess / git-not-found / timeout errors — degrades to
      "not ignored" so an unhealthy infra environment does not
      false-fail the gate (the existence-floor remains the Coach's job
      at turn end);
    * any non-{0,1} exit, with a warning logged so the operator can
      diagnose.

    The matching logic mirrors ``CoachVerifier._git_check_ignore_rule``
    but is intentionally duplicated to keep the gate self-contained.
    """
    try:
        result = subprocess.run(
            ["git", "check-ignore", "-v", "--no-index", "--", path],
            cwd=str(worktree_path),
            capture_output=True,
            text=True,
            check=False,
            timeout=_CHECK_IGNORE_TIMEOUT_SECONDS,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as exc:
        logger.warning(
            "preflight_ignore_gate: 'git check-ignore' failed for %s in %s: %s. "
            "Treating path as not-ignored (Coach still verifies on turn end).",
            path,
            worktree_path,
            exc,
        )
        return None

    if result.returncode == 1:
        return None
    if result.returncode == 0 and result.stdout:
        first_line = result.stdout.splitlines()[0]
        if "\t" in first_line:
            return first_line.split("\t", 1)[0]
        return first_line
    if result.returncode == 0:
        # Exit 0 with no stdout shouldn't happen; treat as not-ignored.
        return None

    logger.warning(
        "preflight_ignore_gate: 'git check-ignore' returned %d for %s in %s; "
        "stderr=%s. Treating path as not-ignored.",
        result.returncode,
        path,
        worktree_path,
        result.stderr.strip(),
    )
    return None


def is_project_root_gitignore(rule: str) -> bool:
    """Return True when ``rule``'s source is the project-root ``.gitignore``.

    Mirrors ``CoachValidator._ignore_rule_is_project_root`` (TASK-FIX-IGNR
    AC-6). ``git check-ignore -v --no-index`` formats matched rules as
    ``<source>:<linenum>:<pattern>``. A rule from the project-root
    ``.gitignore`` therefore has source ``.gitignore`` exactly (no
    directory prefix). Nested ``.gitignore`` files (e.g.
    ``src/.gitignore``) have a directory in the source — those are NOT
    the rebase-fixable case the hint targets, so the helper returns False.
    """
    if not rule:
        return False
    source = rule.split(":", 1)[0]
    return source == ".gitignore"


def format_blocked_message(task_id: str, result: PreflightResult) -> str:
    """Render a ``BLOCKED`` result as a human-readable, fail-fast message.

    Used by the caller (AgentInvoker) when raising ``AgentInvocationError``
    before turn 1 begins. The format is deliberately verbose so the
    operator sees both the matched rule and (when applicable) the
    rebase hint without further digging.
    """
    if result.status != STATUS_BLOCKED:
        raise ValueError(
            f"format_blocked_message called with non-blocked result: "
            f"{result.status!r}"
        )

    count = len(result.matches)
    plural = "target is" if count == 1 else "targets are"
    lines = [
        f"pre-flight ignore gate: {count} planned {plural} git-ignored "
        f"in the worktree. The Player would burn SDK turns creating "
        f"files that cannot subsequently be tracked or verified.",
        "",
        f"Task: {task_id}",
        "",
        "Matched rules:",
    ]
    for match in result.matches:
        lines.append(f"  - {match.path}: {match.rule}")

    if result.rebase_hint:
        lines.extend(
            [
                "",
                "Hint: at least one rule is from the project-root .gitignore. "
                "If the worktree was branched before .gitignore was updated, "
                "rebasing on the latest main may resolve the conflict. "
                "Otherwise, either pick a non-ignored target path or "
                "update the ignore rules to permit this path.",
            ]
        )

    return "\n".join(lines)


__all__ = [
    "IgnoreMatch",
    "PreflightResult",
    "STATUS_PASSED",
    "STATUS_SKIPPED",
    "STATUS_BLOCKED",
    "run_preflight_ignore_gate",
    "load_planned_targets",
    "check_ignore_one",
    "is_project_root_gitignore",
    "format_blocked_message",
]
