"""
Run artifact archival for AutoBuild worktrees.

This module provides archival functionality for AutoBuild run artifacts before
worktree cleanup. All artifacts under `.guardkit/autobuild/` are archived to
a durable home outside the repository working tree.

Decision of Record: D-OBS-1 (OBS-2) + D-OBS-4 (NAS home) + L12 rider (baseline.json)

The archive root is:
- Default: ~/.guardkit/archive/<repo-name>/<feature-or-task-id>/
- Overridable via GUARDKIT_ARCHIVE_ROOT environment variable
- Always outside repo working tree (survives prune, git clean, repo deletion)

Example:
    >>> from pathlib import Path
    >>> from guardkit.worktrees.archive import RunArtifactArchiver
    >>>
    >>> archiver = RunArtifactArchiver(repo_root=Path.cwd())
    >>> archiver.archive_worktree_artifacts(
    ...     worktree_path=Path(".guardkit/worktrees/FEAT-ABC"),
    ...     feature_or_task_id="FEAT-ABC"
    ... )
"""

from __future__ import annotations

import logging
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class ArchiveResult:
    """
    Result of an archive operation.

    Attributes:
        success: Whether the archive completed successfully
        archive_path: Path where artifacts were archived (None if failed)
        error: Error message if archive failed (None if succeeded)
        files_archived: Number of files archived
    """
    success: bool
    archive_path: Optional[Path] = None
    error: Optional[str] = None
    files_archived: int = 0


class RunArtifactArchiver:
    """
    Archives AutoBuild run artifacts before worktree cleanup.

    This class handles copying all run artifacts from worktree `.guardkit/autobuild/`
    directories to a durable archive location outside the repository.

    Attributes:
        repo_root: Root directory of the git repository
        archive_root: Root directory for all archives (overridable)
    """

    def __init__(
        self,
        repo_root: Path,
        archive_root: Optional[Path] = None
    ):
        """
        Initialize the archiver.

        Args:
            repo_root: Root directory of the git repository
            archive_root: Custom archive root (defaults to ~/.guardkit/archive/)
        """
        self.repo_root = repo_root.resolve()

        if archive_root is None:
            # Default: ~/.guardkit/archive/<repo-name>/
            archive_root = Path.home() / ".guardkit" / "archive" / self.repo_root.name

        self.archive_root = archive_root.resolve()

        # Ensure archive root is outside repo working tree
        if self._is_inside_repo(self.archive_root):
            logger.warning(
                f"Archive root {self.archive_root} is inside repository tree. "
                f"Using fallback: {Path.home() / '.guardkit' / 'archive' / self.repo_root.name}"
            )
            self.archive_root = Path.home() / ".guardkit" / "archive" / self.repo_root.name

    def _is_inside_repo(self, path: Path) -> bool:
        """
        Check if a path is inside the repository working tree.

        Args:
            path: Path to check

        Returns:
            True if path is inside repo, False otherwise
        """
        try:
            path.resolve().relative_to(self.repo_root)
            return True
        except ValueError:
            return False

    def _get_repo_name(self) -> str:
        """
        Get the repository name from the repo root path.

        Returns:
            Repository name (last component of repo_root)
        """
        return self.repo_root.name

    def _copy_with_structure(
        self,
        src: Path,
        dest: Path,
        description: str = "artifacts"
    ) -> int:
        """
        Copy a directory tree preserving structure.

        Args:
            src: Source directory
            dest: Destination directory
            description: Description for logging

        Returns:
            Number of files copied
        """
        if not src.exists():
            logger.debug(f"Source {description} directory does not exist: {src}")
            return 0

        files_copied = 0

        try:
            # Create destination parent if it doesn't exist
            dest.parent.mkdir(parents=True, exist_ok=True)

            # Copy directory tree
            if src.is_dir():
                shutil.copytree(src, dest, dirs_exist_ok=True)
                # Count files recursively
                files_copied = sum(1 for _ in dest.rglob('*') if _.is_file())
                logger.debug(f"Copied {files_copied} {description} files from {src} to {dest}")
            else:
                # Single file
                shutil.copy2(src, dest)
                files_copied = 1
                logger.debug(f"Copied {description} file from {src} to {dest}")

        except Exception as e:
            logger.warning(
                f"Failed to copy {description} from {src} to {dest}: {e}",
                exc_info=True
            )

        return files_copied

    def archive_worktree_artifacts(
        self,
        worktree_path: Path,
        feature_or_task_id: str,
    ) -> ArchiveResult:
        """
        Archive all run artifacts from a worktree before cleanup.

        This archives:
        - All task directories under .guardkit/autobuild/<task_id>/
        - Feature-level baseline.json
        - Any events.jsonl files

        Args:
            worktree_path: Path to the worktree directory
            feature_or_task_id: Feature or task ID (e.g., FEAT-ABC, TASK-XYZ)

        Returns:
            ArchiveResult indicating success/failure and archive location
        """
        try:
            # Resolve worktree path
            worktree_path = worktree_path.resolve()

            # Source: worktree .guardkit/autobuild/
            autobuild_source = worktree_path / ".guardkit" / "autobuild"

            # Destination: archive_root/<feature-or-task-id>/
            archive_dest = self.archive_root / feature_or_task_id

            if not autobuild_source.exists():
                logger.warning(
                    f"No autobuild directory found in worktree: {autobuild_source}"
                )
                return ArchiveResult(
                    success=True,
                    archive_path=archive_dest,
                    files_archived=0
                )

            # Create archive destination
            archive_dest.mkdir(parents=True, exist_ok=True)

            total_files = 0

            # Archive all contents of autobuild directory
            # This includes task dirs AND feature-level files like baseline.json
            for item in autobuild_source.iterdir():
                dest_item = archive_dest / item.name
                files_copied = self._copy_with_structure(
                    item,
                    dest_item,
                    description=f"{item.name}"
                )
                total_files += files_copied

            logger.info(
                f"Archived {total_files} artifact files from {autobuild_source} "
                f"to {archive_dest}"
            )

            return ArchiveResult(
                success=True,
                archive_path=archive_dest,
                files_archived=total_files
            )

        except Exception as e:
            error_msg = f"Failed to archive worktree artifacts: {e}"
            logger.warning(error_msg, exc_info=True)
            return ArchiveResult(
                success=False,
                error=error_msg
            )

    def archive_main_repo_events(
        self,
        feature_or_task_id: str,
        events_file: Optional[Path] = None
    ) -> ArchiveResult:
        """
        Archive events.jsonl from the main repo.

        This archives both:
        - Feature-level: <cwd>/.guardkit/autobuild/<FEAT>/events.jsonl
        - Task-mode: <cwd>/.guardkit/autobuild/<task_id>/events.jsonl

        Args:
            feature_or_task_id: Feature or task ID
            events_file: Optional explicit path to events.jsonl
                        (defaults to .guardkit/autobuild/<id>/events.jsonl)

        Returns:
            ArchiveResult indicating success/failure
        """
        try:
            # Default events file location
            if events_file is None:
                events_file = (
                    self.repo_root / ".guardkit" / "autobuild"
                    / feature_or_task_id / "events.jsonl"
                )
            else:
                events_file = events_file.resolve()

            if not events_file.exists():
                logger.debug(f"No events file found at {events_file}")
                return ArchiveResult(success=True, files_archived=0)

            # Destination in archive
            archive_dest = self.archive_root / feature_or_task_id
            archive_dest.mkdir(parents=True, exist_ok=True)

            dest_file = archive_dest / "events.jsonl"

            # Copy events file
            shutil.copy2(events_file, dest_file)

            logger.info(f"Archived events file from {events_file} to {dest_file}")

            return ArchiveResult(
                success=True,
                archive_path=dest_file,
                files_archived=1
            )

        except Exception as e:
            error_msg = f"Failed to archive events file: {e}"
            logger.warning(error_msg, exc_info=True)
            return ArchiveResult(
                success=False,
                error=error_msg
            )

    def archive_task_artifacts(
        self,
        worktree_path: Path,
        task_id: str,
        feature_id: Optional[str] = None
    ) -> ArchiveResult:
        """
        Archive artifacts for a single task (incremental archival).

        This is the "belt" to the cleanup hook's "braces" - archives after
        each task's loop phase completes so a crash loses at most the in-flight task.

        Args:
            worktree_path: Path to the worktree
            task_id: Task ID to archive
            feature_id: Optional feature ID (uses task_id if not provided)

        Returns:
            ArchiveResult indicating success/failure
        """
        try:
            worktree_path = worktree_path.resolve()

            # Source: worktree .guardkit/autobuild/<task_id>/
            task_source = worktree_path / ".guardkit" / "autobuild" / task_id

            if not task_source.exists():
                logger.debug(f"No task artifacts found at {task_source}")
                return ArchiveResult(success=True, files_archived=0)

            # Use feature_id if provided, otherwise task_id
            archive_id = feature_id if feature_id else task_id

            # Destination: archive_root/<feature-or-task>/<task_id>/
            archive_dest = self.archive_root / archive_id / task_id

            # Copy task directory
            files_copied = self._copy_with_structure(
                task_source,
                archive_dest,
                description=f"task {task_id} artifacts"
            )

            logger.info(
                f"Incrementally archived {files_copied} files for task {task_id} "
                f"to {archive_dest}"
            )

            return ArchiveResult(
                success=True,
                archive_path=archive_dest,
                files_archived=files_copied
            )

        except Exception as e:
            error_msg = f"Failed to archive task {task_id} artifacts: {e}"
            logger.warning(error_msg, exc_info=True)
            return ArchiveResult(
                success=False,
                error=error_msg
            )


def get_archive_root_from_env() -> Optional[Path]:
    """
    Get custom archive root from GUARDKIT_ARCHIVE_ROOT environment variable.

    Returns:
        Path if set, None otherwise
    """
    env_root = os.getenv("GUARDKIT_ARCHIVE_ROOT")
    if env_root:
        return Path(env_root).resolve()
    return None
