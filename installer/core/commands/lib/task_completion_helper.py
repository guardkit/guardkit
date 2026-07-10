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
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional, List, Tuple
from datetime import datetime
import logging

# Context-robust import: the CLI (`guardkit task complete`) runs in the installed
# guardkit context where the repo root is on sys.path, so the package path
# resolves; the legacy bin-script context puts commands/lib/ directly on sys.path,
# where the bare name resolves. Supporting BOTH makes this the genuinely shared
# routine (demotion scope §2) rather than one importable from a single context.
try:  # installed-guardkit / CLI context
    from installer.core.commands.lib.git_state_helper import get_git_root
except ImportError:  # bin-script context (commands/lib on sys.path)
    from git_state_helper import get_git_root

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CompletionRefused(Exception):
    """A pre-completion gate refused to finalize the task.

    Raised by :func:`complete_task` for a carve-out (autobuild / operator_handoff)
    or a fail-closed ``qa.enforce_tier1`` refusal. The task file is left UNTOUCHED
    (no flip, no move) — a refusal must never half-complete a task.
    """


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


def _repo_root() -> Path:
    """Git root, or cwd fallback (mirrors the module's other lookups)."""
    try:
        return get_git_root()
    except Exception:
        return Path.cwd()


def _apply_completion_frontmatter(
    content: str,
    *,
    completed_timestamp: str,
    completed_location: Optional[str] = None,
) -> str:
    """Return ``content`` with the completion frontmatter applied (PURE — no I/O).

    Flips ``status`` to ``completed`` and stamps ``completed`` / ``updated``
    (and ``completed_location`` when given). Operates on a string so the caller
    can write the flipped content to the *destination* and never to the source
    location — the load-bearing half of :func:`atomic_flip_and_move`'s invariant.
    """
    # Context-robust import (see module header rationale).
    try:
        from installer.core.commands.lib.task_utils import (
            parse_task_frontmatter,
            write_task_frontmatter,
        )
    except ImportError:
        from task_utils import parse_task_frontmatter, write_task_frontmatter

    frontmatter = parse_task_frontmatter(content)
    parts = content.split("---", 2)
    body = parts[2] if len(parts) >= 3 else ""

    frontmatter["status"] = "completed"
    frontmatter["completed"] = completed_timestamp
    if completed_location is not None:
        frontmatter["completed_location"] = completed_location
    frontmatter["updated"] = completed_timestamp
    return write_task_frontmatter(frontmatter, body)


def atomic_flip_and_move(
    task_path: Path,
    *,
    month_subfolder: bool = True,
) -> Tuple[Path, Path]:
    """Atomically flip ``status: completed`` AND move the file to ``tasks/completed/``.

    **This is the WS3-S8 deliverable** (one operation, so "completed but sitting
    in backlog" is unrepresentable — demotion scope §2 step 2).

    Mechanism — the flip is baked into the *destination* content, and a single
    ``os.replace`` of a temp file (written in the destination dir, same
    filesystem) is the commit point; the source is unlinked LAST:

    - crash BEFORE the ``os.replace`` → source untouched, still its original
      status in its original directory (task simply not completed — retryable);
    - crash AFTER the ``os.replace`` → the destination is the authoritative
      completed copy; at worst the source lingers as a stale duplicate whose
      status is still the ORIGINAL (never ``completed``).

    So at no observable instant does a file carrying ``status: completed`` sit
    under a non-completed directory. ``status: completed`` is never written to
    the source path — the invariant the atomicity test pins.

    Returns ``(new_task_path, completed_dir)``, matching
    :func:`move_task_to_completed`.
    """
    git_root = _repo_root()
    if month_subfolder:
        completed_dir = git_root / "tasks" / "completed" / datetime.now().strftime("%Y-%m")
    else:
        completed_dir = git_root / "tasks" / "completed"
    completed_dir.mkdir(parents=True, exist_ok=True)
    new_task_path = completed_dir / task_path.name

    try:
        completed_location = str(completed_dir.relative_to(git_root))
    except ValueError:
        completed_location = str(completed_dir)

    content = task_path.read_text(encoding="utf-8")
    completed_timestamp = datetime.utcnow().isoformat() + "Z"
    flipped = _apply_completion_frontmatter(
        content,
        completed_timestamp=completed_timestamp,
        completed_location=completed_location,
    )

    # Write the flipped content to a temp file IN THE DESTINATION DIR (same
    # filesystem as the final path → os.replace is a true atomic rename), fsync,
    # then atomically replace into place. On any failure the source is untouched.
    fd, tmp_name = tempfile.mkstemp(
        dir=str(completed_dir), prefix=f".{task_path.stem}.", suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(flipped)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, str(new_task_path))  # ← atomic commit point
    except BaseException:
        # Commit did not happen: remove the temp, leave the source untouched so
        # the task is simply "not completed" (never a half-state).
        try:
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)
        except OSError:
            pass
        raise

    # Commit succeeded — destination is authoritative. Remove the (original,
    # NOT-completed) source last. If this fails the completion still SUCCEEDED;
    # the leftover source's status is still the original, so the
    # "completed-but-in-backlog" invariant holds regardless.
    if task_path.resolve() != new_task_path.resolve():
        try:
            task_path.unlink()
        except FileNotFoundError:
            pass
        except OSError as exc:
            logger.warning(
                "⚠️  Completed copy written to %s but could not remove source %s "
                "(%s) — the completed copy is authoritative; source is a stale "
                "duplicate (its status is unchanged, so no completed-in-backlog state)",
                new_task_path,
                task_path,
                exc,
            )

    logger.info("✅ Atomic flip+move: %s → %s (status: completed)", task_path, new_task_path)
    return new_task_path, completed_dir


def _enforce_tier1_completion(
    repo_root: Path,
    task_id: str,
    *,
    test_output: Optional[str] = None,
) -> Optional[str]:
    """Fail-closed ``qa.enforce_tier1`` completion gate (demotion scope §3.3).

    Returns ``None`` when enforcement is OFF or passes; returns a refusal reason
    string when the flag is ON and a check fails. The single completion-time call
    site for WS2-B2 so BOTH entry points (task-work Phase 6 + the CLI) inherit it.

    When ON, runs the pinned-pass-bar precondition, and — if a completion-suite
    ``test_output`` is supplied — the known-failure ledger diff. An ABSENT test
    signal never blocks (``absence-of-failure-is-not-success``); a malformed
    ledger fails closed. Enforcement is opt-in, so a repo that turns it on always
    has ``guardkit`` importable; if the checker cannot be imported the gate is
    treated as OFF (there is nothing to enforce against).
    """
    try:
        from guardkit.qa.enforcement import (
            is_tier1_enforced,
            check_pass_bar_precondition,
            parse_pytest_outcome,
            diff_failures_against_ledger,
        )
    except ImportError:
        logger.debug("qa.enforcement not importable — tier-1 completion gate treated as OFF")
        return None

    if not is_tier1_enforced(repo_root):
        return None

    precondition = check_pass_bar_precondition(repo_root, task_id)
    if not precondition.passed:
        return f"qa.enforce_tier1 pass-bar precondition failed: {precondition.detail}"

    if test_output is not None:
        outcome = parse_pytest_outcome(test_output)
        sweep = diff_failures_against_ledger(
            outcome, repo_root / "qa" / "known-failures.yaml"
        )
        # "pass" and "unverified" (absent signal) proceed; "fail"/"error" refuse.
        if sweep.status in ("fail", "error"):
            return f"qa.enforce_tier1 known-failure ledger sweep failed: {sweep.detail}"

    return None


def _capture_outcome_best_effort(new_task_path: Path, *, success: bool = True) -> str:
    """Best-effort fleet-memory capture-outcome (the flywheel's ONLY write path).

    Shells the SAME acquisition path the ``guardkit memory capture-outcome`` CLI
    uses (cli-wrapper-shares-client-acquisition rule) as a subprocess so the CLI
    completion path — which has no AI orchestrator to run the markdown's capture
    step — still enriches fleet-memory. Silent-fail class → LOUD log line
    (demotion scope §2.5). Returns a short status string for the banner.
    """
    cmd = [
        sys.executable,
        "-m",
        "guardkit.cli.main",
        "memory",
        "capture-outcome",
        "--from-task-file",
        str(new_task_path),
        "--success" if success else "--failure",
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    except (OSError, subprocess.SubprocessError) as exc:
        logger.warning("⚠️  fleet-memory capture-outcome could not run (%s) — outcome NOT captured", exc)
        return f"skipped ({exc})"
    if proc.returncode != 0:
        logger.warning(
            "⚠️  fleet-memory capture-outcome exited %s — outcome NOT captured; stderr: %s",
            proc.returncode,
            (proc.stderr or "").strip()[:400],
        )
        return f"failed (exit {proc.returncode})"
    logger.info("✅ fleet-memory capture-outcome recorded for %s", new_task_path.name)
    return "recorded"


def _commit_git_state_best_effort(task_id: str) -> str:
    """Best-effort conductor git-state commit (never blocks completion)."""
    try:
        from installer.core.commands.lib.git_state_helper import commit_state_files
    except ImportError:
        from git_state_helper import commit_state_files
    try:
        commit_state_files(task_id=task_id, message=f"Complete {task_id} and update state")
        logger.info("✅ Conductor git-state committed for %s", task_id)
        return "committed"
    except Exception as exc:  # not in a git repo / git unavailable / nothing to commit
        logger.warning("⚠️  Could not commit conductor git-state for %s (%s) — non-critical", task_id, exc)
        return f"skipped ({exc})"


def complete_task(
    task_id_or_path: str,
    update_metadata: bool = True,
    archive_documents: bool = True,
    *,
    refuse_autobuild: bool = False,
    refuse_operator_handoff: bool = False,
    enforce_tier1: bool = True,
    test_output: Optional[str] = None,
    capture_outcome: bool = False,
    commit_git_state: bool = False,
    repo_root: Optional[Path] = None,
) -> dict:
    """
    Complete task with the full shared workflow (Conductor-aware).

    THE shared atomic completion routine (demotion scope §2), called from both
    entry points: task-work Phase 6 Finalize and the ``guardkit task complete``
    CLI. Carries, in order:

    1. Find task file (Conductor-aware, location-agnostic);
    2. Pre-completion carve-out gates + fail-closed ``qa.enforce_tier1``;
    3. ATOMIC status-flip + file-move (:func:`atomic_flip_and_move`) — one
       operation, so "completed but sitting in backlog" is unrepresentable;
    4. Related-file archival;
    5. fleet-memory ``capture-outcome`` (best-effort, loud on failure);
    6. Conductor git-state commit (best-effort).

    Args:
        task_id_or_path: Task ID or full path.
        update_metadata: Flip ``status`` to ``completed`` during the move
            (default True). When True the move is atomic (flip+move as one
            commit); when False the file is moved with its status unchanged.
        archive_documents: Archive plans and summaries (default True).
        refuse_autobuild: Raise :class:`CompletionRefused` — the guard-metric
            carve-out (never auto-complete an unmerged autobuild branch; the
            autobuild lane finalizes via feature-complete post-merge).
        refuse_operator_handoff: Raise :class:`CompletionRefused` when the task
            is ``task_type: operator_handoff`` (Phase-6 carve-out; the CLI/manual
            lane leaves this False so it CAN complete deferred operator_handoff).
        enforce_tier1: Run the fail-closed ``qa.enforce_tier1`` completion gate
            when the repo flag is on (default True; a no-op when the flag is off).
        test_output: Optional completion-suite pytest text, fed to the tier-1
            known-failure ledger diff. Absent → the ledger check is skipped.
        capture_outcome: Run the fleet-memory ``capture-outcome`` write
            (default False; the CLI/Phase-6 path passes True — it has no AI
            orchestrator to run the markdown's capture step).
        commit_git_state: Commit conductor state files (default False).
        repo_root: Repo root for the enforcement gate (default: git root / cwd).

    Returns:
        Dict with: task_id, old_path, new_path, completed_dir,
        documents_archived, completed_at, status_flipped, task_type,
        capture_status, git_state_status.

    Raises:
        FileNotFoundError: If task not found.
        CompletionRefused: If a carve-out or the tier-1 gate refuses (the task
            file is left UNTOUCHED — no flip, no move).
    """
    repo_root = repo_root or _repo_root()

    # 1. Find task file (Conductor-aware, location-agnostic — see find_task_file).
    logger.info(f"🔍 Finding task: {task_id_or_path}")
    task_path = find_task_file(task_id_or_path)

    # Extract task ID from filename (handles both TASK-001 and TASK-TEST-001 formats)
    task_id = task_path.stem  # Use full stem (filename without extension)
    logger.info(f"📋 Task ID: {task_id}")
    logger.info(f"📁 Current path: {task_path}")

    # Read task_type for the operator_handoff carve-out (before any mutation).
    try:
        from installer.core.commands.lib.task_utils import read_task_file
    except ImportError:
        from task_utils import read_task_file
    try:
        frontmatter, _ = read_task_file(task_path)
        task_type = str(frontmatter.get("task_type", "") or "").strip().lower()
    except Exception:
        task_type = ""

    # 2. Pre-completion gates — REFUSE before touching the file (no half-state).
    if refuse_autobuild:
        raise CompletionRefused(
            f"refusing to complete {task_id} in autobuild mode: feature-build merges "
            f"BEFORE completion; the autobuild lane finalizes via feature-complete "
            f"calling this routine post-merge (guard metric: no completion for an "
            f"unmerged autobuild branch)"
        )
    if refuse_operator_handoff and task_type == "operator_handoff":
        raise CompletionRefused(
            f"refusing to auto-complete {task_id}: task_type is operator_handoff — "
            f"those tasks never run task-work; their completion path is feature-complete"
        )
    if enforce_tier1:
        refusal = _enforce_tier1_completion(repo_root, task_id, test_output=test_output)
        if refusal:
            raise CompletionRefused(f"refusing to complete {task_id}: {refusal}")

    # 3. Atomic status-flip + move (the WS3-S8 deliverable).
    if update_metadata:
        logger.info(f"🏁 Atomic flip+move → tasks/completed/")
        new_task_path, completed_dir = atomic_flip_and_move(task_path)
        status_flipped = True
    else:
        logger.info(f"🏁 Moving task to completed directory (status unchanged)")
        new_task_path, completed_dir = move_task_to_completed(task_path)
        status_flipped = False

    # 4. Archive documents
    documents_archived = 0
    if archive_documents:
        logger.info(f"📦 Archiving related documents")
        documents_archived = archive_task_documents(task_id, completed_dir)

    # 5. fleet-memory capture-outcome (best-effort, loud on failure).
    capture_status = "not_requested"
    if capture_outcome:
        capture_status = _capture_outcome_best_effort(new_task_path, success=True)

    # 6. Conductor git-state commit (best-effort).
    git_state_status = "not_requested"
    if commit_git_state:
        git_state_status = _commit_git_state_best_effort(task_id)

    # 7. Return summary
    result = {
        'task_id': task_id,
        'old_path': str(task_path),
        'new_path': str(new_task_path),
        'completed_dir': str(completed_dir),
        'documents_archived': documents_archived,
        'completed_at': datetime.utcnow().isoformat() + 'Z',
        'status_flipped': status_flipped,
        'task_type': task_type,
        'capture_status': capture_status,
        'git_state_status': git_state_status,
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
