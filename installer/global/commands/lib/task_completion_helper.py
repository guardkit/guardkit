"""
Task Completion Helper - Conductor-aware task completion with document archival.

This module provides utilities for completing tasks with proper handling of:
- Conductor worktree path resolution (uses git root)
- Implementation plan archival (.claude/task-plans/)
- Summary document archival (root directory cleanup)
- Completion report archival

Part of TASK-COND-FE76: Fix /task-complete Conductor workspace inconsistencies
Related to TASK-031: Git state helper for worktree support

Author: Claude (Anthropic)
Created: 2025-11-27
"""

import os
import shutil
from pathlib import Path
from typing import Optional, List, Tuple
from datetime import datetime
import logging

from git_state_helper import get_git_root

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def find_task_file(task_id_or_path: str) -> Optional[Path]:
    """
    Find task file by ID or path (Conductor-aware).

    Resolves paths relative to git repository root, ensuring correct behavior
    in both main repository and Conductor worktrees.

    Args:
        task_id_or_path: Either a task ID (e.g., "TASK-001") or full path

    Returns:
        Path to task file if found, None otherwise

    Raises:
        FileNotFoundError: If task not found (with helpful error message)

    Examples:
        >>> # Works in main repo
        >>> find_task_file("TASK-001")
        PosixPath('/path/to/repo/tasks/backlog/TASK-001.md')

        >>> # Works in Conductor worktree
        >>> find_task_file("TASK-001")  # Resolves to main repo tasks/
        PosixPath('/path/to/repo/tasks/backlog/TASK-001.md')

        >>> # Works with full path
        >>> find_task_file("/path/to/repo/tasks/backlog/TASK-001.md")
        PosixPath('/path/to/repo/tasks/backlog/TASK-001.md')
    """
    # If absolute path provided, use it directly
    if os.path.isabs(task_id_or_path):
        path = Path(task_id_or_path)
        if path.exists():
            return path
        else:
            raise FileNotFoundError(
                f"Task file not found at path: {task_id_or_path}\n"
                f"Check that the path is correct."
            )

    # Extract task ID from path-like inputs
    task_id = task_id_or_path
    if "/" in task_id or "\\" in task_id:
        # Extract filename without extension
        task_id = Path(task_id).stem

    # Get git root to search in main repo (Conductor-aware)
    try:
        git_root = get_git_root()
        base_dir = git_root / "tasks"
    except Exception as e:
        # Fallback to relative path if not in git repo
        logger.warning(f"Not in git repository, using relative paths: {e}")
        base_dir = Path("tasks")

    # Search in all task directories
    task_dirs = [
        "backlog",
        "in_progress",
        "in_review",
        "blocked",
        "completed",
        "review_complete",
        "design_approved"
    ]

    # Also search recursively in backlog for subdirectories
    search_paths = []
    for dir_name in task_dirs:
        dir_path = base_dir / dir_name
        if dir_path.exists():
            # Add top-level directory
            search_paths.append(dir_path)
            # Add subdirectories (e.g., backlog/agent-invocation-enforcement/)
            for subdir in dir_path.iterdir():
                if subdir.is_dir():
                    search_paths.append(subdir)

    # Search for task file
    for search_dir in search_paths:
        pattern = f"{task_id}*.md"
        matches = list(search_dir.glob(pattern))
        if matches:
            return matches[0]  # Return first match

    # Task not found - provide helpful error message
    raise FileNotFoundError(
        f"Task not found: {task_id}\n"
        f"Searched in: {base_dir}/\n"
        f"Directories checked: {', '.join(task_dirs)}\n"
        f"Tip: Use full path or ensure task exists in one of the task directories."
    )


def archive_task_documents(task_id: str, completed_dir: Path) -> int:
    """
    Archive all task-related documents when task completes.

    Moves the following files to the completed directory:
    1. Implementation plan from .claude/task-plans/
    2. Implementation summaries from root directory
    3. Completion reports from root directory

    Args:
        task_id: Task identifier (e.g., "TASK-001")
        completed_dir: Target directory for archived documents

    Returns:
        Number of documents archived

    Note:
        Does not fail if documents don't exist - logs info and continues.
        Failures during archival are logged as warnings but don't block completion.

    Examples:
        >>> completed_dir = Path("tasks/completed/2025-11/")
        >>> count = archive_task_documents("TASK-001", completed_dir)
        >>> print(f"Archived {count} documents")
        Archived 3 documents
    """
    archived_count = 0

    try:
        git_root = get_git_root()
    except Exception as e:
        logger.warning(f"Not in git repository, using relative paths for archival: {e}")
        git_root = Path.cwd()

    # 1. Archive implementation plan from .claude/task-plans/
    plan_path = git_root / ".claude" / "task-plans" / f"{task_id}-implementation-plan.md"
    if plan_path.exists():
        try:
            archive_path = completed_dir / f"{task_id}-implementation-plan.md"
            shutil.move(str(plan_path), str(archive_path))
            logger.info(f"✅ Archived implementation plan: {archive_path}")
            archived_count += 1
        except Exception as e:
            logger.warning(f"⚠️  Failed to archive implementation plan: {e}")

    # 2. Archive implementation summaries and reports from root directory
    # Pattern variations to check (case-insensitive handling)
    summary_patterns = [
        f"{task_id}-IMPLEMENTATION-SUMMARY.md",
        f"{task_id}-implementation-summary.md",
        f"{task_id}-COMPLETION-REPORT.md",
        f"{task_id}-completion-report.md",
        f"{task_id}-Implementation-Summary.md",
        f"{task_id}-Completion-Report.md",
    ]

    for pattern in summary_patterns:
        summary_path = git_root / pattern
        if summary_path.exists():
            try:
                # Preserve original filename in archive
                archive_path = completed_dir / pattern
                shutil.move(str(summary_path), str(archive_path))
                logger.info(f"✅ Archived summary document: {archive_path}")
                archived_count += 1
            except Exception as e:
                logger.warning(f"⚠️  Failed to archive summary {pattern}: {e}")

    if archived_count == 0:
        logger.debug(f"No task documents found for {task_id} to archive")
    else:
        logger.info(f"📦 Archived {archived_count} document(s) for {task_id}")

    return archived_count


def move_task_to_completed(
    task_path: Path,
    month_subfolder: bool = True
) -> Tuple[Path, Path]:
    """
    Move task file to completed directory with optional month-based organization.

    Args:
        task_path: Current path to task file
        month_subfolder: If True, organize by YYYY-MM/ (default: True)

    Returns:
        Tuple of (new_task_path, completed_dir)

    Examples:
        >>> task_path = Path("tasks/backlog/TASK-001.md")
        >>> new_path, completed_dir = move_task_to_completed(task_path)
        >>> print(new_path)
        tasks/completed/2025-11/TASK-001.md
    """
    try:
        git_root = get_git_root()
    except Exception:
        git_root = Path.cwd()

    # Determine target directory
    if month_subfolder:
        # Organize by month: tasks/completed/YYYY-MM/
        year_month = datetime.now().strftime("%Y-%m")
        completed_dir = git_root / "tasks" / "completed" / year_month
    else:
        # Flat structure: tasks/completed/
        completed_dir = git_root / "tasks" / "completed"

    # Create directory if needed
    completed_dir.mkdir(parents=True, exist_ok=True)

    # Move task file
    filename = task_path.name
    new_task_path = completed_dir / filename

    # Use shutil.move for cross-filesystem support
    shutil.move(str(task_path), str(new_task_path))
    logger.info(f"✅ Moved task file: {task_path} → {new_task_path}")

    return new_task_path, completed_dir


def complete_task(
    task_id_or_path: str,
    update_metadata: bool = True,
    archive_documents: bool = True
) -> dict:
    """
    Complete task with full workflow (Conductor-aware).

    Performs the following steps:
    1. Find task file (using Conductor-aware lookup)
    2. Move task to completed directory
    3. Update task metadata (status, completed timestamp)
    4. Archive related documents (plans, summaries)
    5. Return completion summary

    Args:
        task_id_or_path: Task ID or full path
        update_metadata: Update task frontmatter (default: True)
        archive_documents: Archive plans and summaries (default: True)

    Returns:
        Dictionary with completion details:
        - task_id: Task identifier
        - old_path: Original task path
        - new_path: New task path in completed/
        - documents_archived: Number of documents archived
        - completed_at: ISO timestamp

    Raises:
        FileNotFoundError: If task not found

    Examples:
        >>> result = complete_task("TASK-001")
        >>> print(result['new_path'])
        /path/to/repo/tasks/completed/2025-11/TASK-001.md

        >>> # Works with full path
        >>> result = complete_task("/path/to/tasks/backlog/TASK-001.md")

        >>> # Works in Conductor worktree
        >>> result = complete_task("TASK-001")  # Resolves to main repo
    """
    from task_utils import update_task_frontmatter

    # 1. Find task file (Conductor-aware)
    logger.info(f"🔍 Finding task: {task_id_or_path}")
    task_path = find_task_file(task_id_or_path)

    # Extract task ID from filename (handles both TASK-001 and TASK-TEST-001 formats)
    task_id = task_path.stem  # Use full stem (filename without extension)
    logger.info(f"📋 Task ID: {task_id}")
    logger.info(f"📁 Current path: {task_path}")

    # 2. Move to completed directory
    logger.info(f"🏁 Moving task to completed directory")
    new_task_path, completed_dir = move_task_to_completed(task_path)

    # 3. Update metadata
    documents_archived = 0
    if update_metadata:
        logger.info(f"📝 Updating task metadata")
        try:
            completed_timestamp = datetime.utcnow().isoformat() + 'Z'
            update_task_frontmatter(
                new_task_path,
                {
                    'status': 'completed',
                    'completed': completed_timestamp
                }
            )
            logger.info(f"✅ Updated status to 'completed'")
        except Exception as e:
            logger.warning(f"⚠️  Failed to update metadata: {e}")

    # 4. Archive documents
    if archive_documents:
        logger.info(f"📦 Archiving related documents")
        documents_archived = archive_task_documents(task_id, completed_dir)

    # 5. Return summary
    result = {
        'task_id': task_id,
        'old_path': str(task_path),
        'new_path': str(new_task_path),
        'completed_dir': str(completed_dir),
        'documents_archived': documents_archived,
        'completed_at': datetime.utcnow().isoformat() + 'Z'
    }

    logger.info(f"")
    logger.info(f"{'='*60}")
    logger.info(f"✅ Task {task_id} completed successfully")
    logger.info(f"{'='*60}")
    logger.info(f"📁 New location: {new_task_path}")
    logger.info(f"📦 Documents archived: {documents_archived}")
    logger.info(f"⏰ Completed at: {result['completed_at']}")
    logger.info(f"{'='*60}")

    return result
