#!/usr/bin/env python3
"""
Task Status JSON Producer

Scans the project's tasks/ directories, parses task frontmatter, and emits
the task dashboard as stable, machine-readable JSON to stdout.

Usage:
    python3 task_status_json.py [TASK-ID] [--base-path PATH]

- No args: full dashboard JSON (summary + all tasks)
- Positional TASK-ID: single-task JSON object (task shape only); exit 1 if not found
- --base-path: project root (default: cwd)
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure the project root is on sys.path so that package imports work
# when the script is executed directly or via bin-entries symlink.
_PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from installer.core.commands.lib.task_utils import parse_task_frontmatter

# Status buckets that the scanner traverses
STATUS_DIRS: List[str] = [
    "backlog",
    "in_progress",
    "in_review",
    "blocked",
    "completed",
]

# Fixed key order for task objects
TASK_KEYS: List[str] = [
    "id",
    "title",
    "status",
    "priority",
    "task_type",
    "complexity",
    "tags",
    "created",
    "updated",
    "epic",
    "feature",
    "parent_review",
    "feature_id",
    "file_path",
]

# Fixed key order for the top-level output
OUTPUT_KEYS: List[str] = [
    "schema_version",
    "generated_at",
    "base_path",
    "summary",
    "tasks",
]

# Fixed key order for summary
SUMMARY_KEYS: List[str] = [
    "backlog",
    "in_progress",
    "in_review",
    "blocked",
    "completed",
    "total",
]


def _ordered_dict(keys: List[str], **kwargs: Any) -> Dict[str, Any]:
    """Build an OrderedDict-style dict preserving insertion order."""
    result: Dict[str, Any] = {}
    for key in keys:
        result[key] = kwargs.get(key)
    return result


def scan_task_files(base_path: Path) -> List[Path]:
    """Recursively scan status directories for .md task files.

    Scans tasks/backlog/, tasks/in_progress/, tasks/in_review/,
    tasks/blocked/, tasks/completed/ recursively (including feature
    subfolders and archive folders like tasks/completed/YYYY-MM/).
    """
    task_files: List[Path] = []
    for status_dir in STATUS_DIRS:
        dir_path = base_path / "tasks" / status_dir
        if not dir_path.is_dir():
            continue
        for md_file in sorted(dir_path.rglob("*.md")):
            task_files.append(md_file)
    return task_files


def parse_task_record(file_path: Path, base_path: Path) -> Optional[Dict[str, Any]]:
    """Parse a single task file and return a normalized record dict.

    Returns None if the file cannot be parsed.
    """
    try:
        content = file_path.read_text(encoding="utf-8")
    except OSError:
        return None

    try:
        frontmatter = parse_task_frontmatter(content)
    except ValueError:
        return None

    # Derive relative file path from base_path
    try:
        rel_path = str(file_path.relative_to(base_path))
    except ValueError:
        rel_path = str(file_path)

    # Extract status from the directory the file lives under
    try:
        relative = file_path.relative_to(base_path / "tasks")
    except ValueError:
        relative = file_path.relative_to(base_path)
    status = str(relative.parts[0]) if relative.parts else "unknown"

    def _coerce_str(val: Any) -> Optional[str]:
        """Convert a value to string for JSON serialization; None stays None."""
        if val is None:
            return None
        if isinstance(val, (datetime,)):
            return val.isoformat()
        return str(val)

    # Build the task record with fixed key order; missing fields -> null
    record = _ordered_dict(
        TASK_KEYS,
        id=frontmatter.get("id"),
        title=frontmatter.get("title"),
        status=status,
        priority=frontmatter.get("priority"),
        task_type=frontmatter.get("task_type"),
        complexity=frontmatter.get("complexity"),
        tags=frontmatter.get("tags"),
        created=_coerce_str(frontmatter.get("created")),
        updated=_coerce_str(frontmatter.get("updated")),
        epic=_coerce_str(frontmatter.get("epic")),
        feature=_coerce_str(frontmatter.get("feature")),
        parent_review=_coerce_str(frontmatter.get("parent_review")),
        feature_id=_coerce_str(frontmatter.get("feature_id")),
        file_path=rel_path,
    )

    return record


def build_summary(tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Build the summary object counting tasks by status."""
    counts: Dict[str, int] = {
        "backlog": 0,
        "in_progress": 0,
        "in_review": 0,
        "blocked": 0,
        "completed": 0,
    }
    for task in tasks:
        status = task.get("status", "unknown")
        if status in counts:
            counts[status] += 1
    counts["total"] = len(tasks)
    return _ordered_dict(SUMMARY_KEYS, **counts)


def build_dashboard(base_path: Path) -> Dict[str, Any]:
    """Build the full dashboard JSON structure."""
    task_files = scan_task_files(base_path)
    tasks: List[Dict[str, Any]] = []
    for tf in task_files:
        record = parse_task_record(tf, base_path)
        if record is not None:
            tasks.append(record)

    # Sort by (status, id) for deterministic output; use empty string as fallback for None
    tasks.sort(key=lambda t: (t.get("status") or "", t.get("id") or ""))

    summary = build_summary(tasks)

    dashboard = _ordered_dict(
        OUTPUT_KEYS,
        schema_version="1.0",
        generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        base_path=str(base_path),
        summary=summary,
        tasks=tasks,
    )

    return dashboard


def build_single_task(task_id: str, base_path: Path) -> Optional[Dict[str, Any]]:
    """Find and return a single task record by ID.

    Returns None if not found.
    """
    task_files = scan_task_files(base_path)
    for tf in task_files:
        record = parse_task_record(tf, base_path)
        if record is not None and record.get("id") == task_id:
            return record
    return None


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Emit task dashboard as stable JSON to stdout."
    )
    parser.add_argument(
        "task_id",
        nargs="?",
        default=None,
        help="Optional single task ID to return (task shape only).",
    )
    parser.add_argument(
        "--base-path",
        type=Path,
        default=Path.cwd(),
        help="Project root directory (default: cwd).",
    )

    args = parser.parse_args()
    base_path = args.base_path.resolve()

    if args.task_id is not None:
        # Single-task mode
        record = build_single_task(args.task_id, base_path)
        if record is None:
            print(
                f"Error: task '{args.task_id}' not found in {base_path}/tasks/",
                file=sys.stderr,
            )
            sys.exit(1)
        output = record
    else:
        # Full dashboard mode
        output = build_dashboard(base_path)

    # Emit deterministic JSON with fixed key order
    print(json.dumps(output, indent=2, sort_keys=False, ensure_ascii=False))


if __name__ == "__main__":
    main()
