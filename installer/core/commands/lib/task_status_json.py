#!/usr/bin/env python3
"""
Task Status JSON Producer

This script scans the project's tasks/ directories, parses task frontmatter,
and emits the task dashboard as stable, machine-readable JSON to stdout.

Usage:
    python3 task_status_json.py [TASK-ID] [--base-path PATH]
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
import datetime

# Import task utilities
def read_task_file(file_path: Path) -> tuple[Dict[str, Any], str]:
    """
    Read task file and return frontmatter and body separately.
    """
    try:
        from installer.core.commands.lib.task_utils import parse_task_frontmatter
    except ImportError:
        # Fallback for when the module is not available in the current context
        import yaml
        
        def parse_task_frontmatter(content: str) -> Dict[str, Any]:
            """Parse task frontmatter from markdown content."""
            # Split frontmatter from body
            parts = content.split('---', 2)
            if len(parts) < 3:
                raise ValueError("Invalid task format: missing frontmatter delimiters")

            # Parse YAML frontmatter
            try:
                frontmatter = yaml.safe_load(parts[1])
            except yaml.YAMLError as e:
                raise ValueError(f"Invalid YAML in frontmatter: {e}")

            if not isinstance(frontmatter, dict):
                raise ValueError("Frontmatter must be a YAML dictionary")

            # Ensure external_ids exists (default to empty dict for backward compatibility)
            if 'external_ids' not in frontmatter:
                frontmatter['external_ids'] = {}

            # Ensure external_ids is a dict
            if not isinstance(frontmatter['external_ids'], dict):
                frontmatter['external_ids'] = {}

            # Ensure legacy_id is handled (for migrated tasks)
            if 'legacy_id' not in frontmatter:
                frontmatter['legacy_id'] = None

            return frontmatter

    content = file_path.read_text(encoding='utf-8')
    frontmatter = parse_task_frontmatter(content)

    # Extract body
    parts = content.split('---', 2)
    body = parts[2] if len(parts) >= 3 else ""
    
    return frontmatter, body


def get_task_directories(base_path: Path) -> List[Path]:
    """Get all task directories to scan."""
    task_dirs = [
        base_path / "tasks" / "backlog",
        base_path / "tasks" / "in_progress", 
        base_path / "tasks" / "in_review",
        base_path / "tasks" / "blocked",
        base_path / "tasks" / "completed"
    ]
    
    # Also scan feature subdirectories
    try:
        feature_dirs = (base_path / "tasks" / "backlog").glob("*")
        task_dirs.extend(feature_dirs)
    except Exception:
        # Skip if feature directories can't be accessed
        pass
    
    # Also scan archive directories in completed
    try:
        archive_dirs = (base_path / "tasks" / "completed").glob("????-??")
        task_dirs.extend(archive_dirs)
    except Exception:
        # Skip if archive directories can't be accessed
        pass
    
    return task_dirs


def scan_tasks(base_path: Path) -> List[Dict[str, Any]]:
    """Scan all tasks and return their parsed data."""
    tasks = []
    
    task_dirs = get_task_directories(base_path)
    
    for task_dir in task_dirs:
        if not task_dir.exists():
            continue
            
        # Find all .md files in the directory
        try:
            for task_file in task_dir.glob("*.md"):
                try:
                    frontmatter, body = read_task_file(task_file)
                    # Add file path to frontmatter
                    frontmatter["file_path"] = str(task_file.relative_to(base_path))
                    tasks.append(frontmatter)
                except Exception as e:
                    # Skip invalid task files
                    # print(f"Warning: Could not parse task file {task_file}: {e}", file=sys.stderr)
                    continue
        except Exception:
            # Skip if directory access fails
            continue
    
    return tasks


def get_task_summary(tasks: List[Dict[str, Any]]) -> Dict[str, int]:
    """Calculate task summary statistics."""
    summary = {
        "backlog": 0,
        "in_progress": 0,
        "in_review": 0,
        "blocked": 0,
        "completed": 0,
        "total": len(tasks)
    }
    
    for task in tasks:
        status = task.get("status", "backlog")
        if status in summary:
            summary[status] += 1
    
    return summary


def sort_tasks(tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Sort tasks by status and then by ID."""
    def sort_key(task):
        status_order = {
            "backlog": 0,
            "in_progress": 1,
            "in_review": 2,
            "blocked": 3,
            "completed": 4
        }
        status = task.get("status", "backlog")
        task_id = task.get("id", "")
        return (status_order.get(status, 999), task_id)
    
    return sorted(tasks, key=sort_key)


def main() -> None:
    """Main entry point for the task status JSON producer."""
    parser = argparse.ArgumentParser(
        description="Produce task status JSON",
        prog="task_status_json"
    )
    parser.add_argument(
        "task_id", 
        nargs="?", 
        help="Specific task ID to get JSON for (if omitted, returns full dashboard)"
    )
    parser.add_argument(
        "--base-path",
        default=".",
        help="Project root path (default: current directory)"
    )
    
    args = parser.parse_args()
    
    base_path = Path(args.base_path).resolve()
    
    if args.task_id:
        # Return single task JSON
        tasks = scan_tasks(base_path)
        task = next((t for t in tasks if t.get("id") == args.task_id), None)
        if task is None:
            print(f"Task {args.task_id} not found", file=sys.stderr)
            sys.exit(1)
        
        # Remove summary from single task output
        task.pop("summary", None)
        print(json.dumps(task, indent=2, ensure_ascii=False))
    else:
        # Return full dashboard JSON
        tasks = scan_tasks(base_path)
        sorted_tasks = sort_tasks(tasks)
        summary = get_task_summary(sorted_tasks)
        
        # Build the full JSON structure
        output = {
            "schema_version": "1.0",
            "generated_at": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "base_path": str(base_path),
            "summary": summary,
            "tasks": sorted_tasks
        }
        
        print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()