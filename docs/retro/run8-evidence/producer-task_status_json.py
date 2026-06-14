"""
Task status JSON producer script.

This script scans the project's tasks/ directories, parses task frontmatter,
and emits the task dashboard as stable, machine-readable JSON to stdout.
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import argparse

# Import task utilities
from installer.core.commands.lib.task_utils import parse_task_frontmatter, read_task_file


def get_all_task_files(base_path: Path) -> List[Path]:
    """
    Get all task files from all task directories.
    
    Args:
        base_path: Base project path
        
    Returns:
        List of task file paths
    """
    task_dirs = [
        base_path / "tasks" / "backlog",
        base_path / "tasks" / "in_progress", 
        base_path / "tasks" / "in_review",
        base_path / "tasks" / "blocked",
        base_path / "tasks" / "completed"
    ]
    
    # Also check for archive directories in completed
    archive_dirs = (base_path / "tasks" / "completed").glob("[0-9][0-9][0-9][0-9]-[0-9][0-9]")
    
    all_task_files = set()  # Use set to prevent duplicates
    
    # Add regular task directories
    for task_dir in task_dirs:
        if task_dir.exists():
            all_task_files.update(task_dir.rglob("*.md"))
    
    # Add archive directories
    for archive_dir in archive_dirs:
        if archive_dir.is_dir():
            all_task_files.update(archive_dir.rglob("*.md"))
    
    # Also check feature subdirectories
    feature_dirs = (base_path / "tasks").glob("*/")
    for feature_dir in feature_dirs:
        if feature_dir.is_dir() and feature_dir.name != "completed":
            all_task_files.update(feature_dir.rglob("*.md"))
    
    return sorted(list(all_task_files))


def parse_task_file(task_file: Path, base_path: Path) -> Optional[Dict[str, Any]]:
    """
    Parse a single task file and return its data.
    
    Args:
        task_file: Path to task file
        base_path: Base project path
        
    Returns:
        Dictionary with task data or None if parsing fails
    """
    try:
        # Read the task file
        content = task_file.read_text(encoding='utf-8')
        
        # Parse frontmatter
        frontmatter, body = read_task_file(task_file)
        
        # Extract file path relative to base path
        relative_path = task_file.relative_to(base_path)
        
        # Build task data with all required fields, ensuring null for missing values
        task_data = {
            "id": frontmatter.get("id"),
            "title": frontmatter.get("title"),
            "status": frontmatter.get("status"),
            "priority": frontmatter.get("priority"),
            "task_type": frontmatter.get("task_type"),
            "complexity": frontmatter.get("complexity"),
            "tags": frontmatter.get("tags", []),
            "created": frontmatter.get("created"),
            "updated": frontmatter.get("updated"),
            "epic": frontmatter.get("epic"),
            "feature": frontmatter.get("feature"),
            "parent_review": frontmatter.get("parent_review"),
            "feature_id": frontmatter.get("feature_id"),
            "file_path": str(relative_path),
            "external_ids": frontmatter.get("external_ids", {}),
            "legacy_id": frontmatter.get("legacy_id")
        }
        
        return task_data
    except Exception as e:
        # Log error but continue processing other files
        print(f"Warning: Could not parse task file {task_file}: {e}", file=sys.stderr)
        # Return minimal task data with parse error flag
        return {
            "id": task_file.stem,  # Use filename as ID if we can't parse it
            "title": None,
            "status": None,
            "priority": None,
            "task_type": None,
            "complexity": None,
            "tags": [],
            "created": None,
            "updated": None,
            "epic": None,
            "feature": None,
            "parent_review": None,
            "feature_id": None,
            "file_path": str(task_file.relative_to(base_path)),
            "external_ids": {},
            "legacy_id": None,
            "parse_error": True
        }


def generate_task_dashboard(base_path: Path = Path(".")) -> Dict[str, Any]:
    """
    Generate the complete task dashboard JSON.
    
    Args:
        base_path: Base project path
        
    Returns:
        Dictionary with complete dashboard data
    """
    # Get all task files
    task_files = get_all_task_files(base_path)
    
    # Parse all tasks
    tasks = []
    summary = {
        "backlog": 0,
        "in_progress": 0,
        "in_review": 0,
        "blocked": 0,
        "completed": 0,
        "total": 0
    }
    
    for task_file in task_files:
        task_data = parse_task_file(task_file, base_path)
        if task_data:
            tasks.append(task_data)
            # Update summary
            status = task_data.get("status", "backlog") or "backlog"
            summary[status] = summary.get(status, 0) + 1
            summary["total"] += 1
    
    # Sort tasks by (status, id) for deterministic output
    # Handle None values by converting to empty string for sorting
    def sort_key(task):
        status = task.get("status", "backlog") or ""
        task_id = task.get("id", "") or ""
        return (status, task_id)
    
    tasks.sort(key=sort_key)
    
    # Build final dashboard
    dashboard = {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "base_path": str(base_path),
        "summary": summary,
        "tasks": tasks
    }
    
    return dashboard


def get_single_task(task_id: str, base_path: Path = Path(".")) -> Dict[str, Any]:
    """
    Get a single task by ID.
    
    Args:
        task_id: Task ID to find
        base_path: Base project path
        
    Returns:
        Dictionary with single task data
        
    Raises:
        SystemExit: If task not found
    """
    task_files = get_all_task_files(base_path)
    
    for task_file in task_files:
        try:
            content = task_file.read_text(encoding='utf-8')
            frontmatter, _ = read_task_file(task_file)
            
            if frontmatter.get("id") == task_id:
                # Build task data with all required fields
                task_data = {
                    "id": frontmatter.get("id"),
                    "title": frontmatter.get("title"),
                    "status": frontmatter.get("status"),
                    "priority": frontmatter.get("priority"),
                    "task_type": frontmatter.get("task_type"),
                    "complexity": frontmatter.get("complexity"),
                    "tags": frontmatter.get("tags", []),
                    "created": frontmatter.get("created"),
                    "updated": frontmatter.get("updated"),
                    "epic": frontmatter.get("epic"),
                    "feature": frontmatter.get("feature"),
                    "parent_review": frontmatter.get("parent_review"),
                    "feature_id": frontmatter.get("feature_id"),
                    "file_path": str(task_file.relative_to(base_path)),
                    "external_ids": frontmatter.get("external_ids", {}),
                    "legacy_id": frontmatter.get("legacy_id")
                }
                return task_data
        except Exception as e:
            print(f"Warning: Could not parse task file {task_file}: {e}", file=sys.stderr)
            continue
    
    # Task not found
    print(f"Task {task_id} not found", file=sys.stderr)
    sys.exit(1)


def main():
    """Main entry point for the task status JSON producer."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Produce task status JSON",
        prog="task_status_json"
    )
    parser.add_argument("task_id", nargs="?", help="Optional task ID to get single task info")
    parser.add_argument("--base-path", default=".", help="Base path for the project (default: current directory)")
    
    args = parser.parse_args()
    
    base_path = Path(args.base_path).resolve()
    
    # Generate output
    if args.task_id:
        # Single task mode
        task_data = get_single_task(args.task_id, base_path)
        print(json.dumps(task_data, indent=2))
    else:
        # Full dashboard mode
        dashboard = generate_task_dashboard(base_path)
        print(json.dumps(dashboard, indent=2))


if __name__ == "__main__":
    main()