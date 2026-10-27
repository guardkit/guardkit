"""Read a task's planned target files (its plan on disk, else its front matter).

``load_planned_targets`` is used by the parallel-wave planner. (27 October 2026:
the pre-turn ``git check-ignore`` advice that also lived here was removed with
the other checks.)
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---", re.DOTALL)



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


__all__ = [
    "load_planned_targets",
]
