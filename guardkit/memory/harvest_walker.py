"""Harvest walker for GuardKit documentation.

Walks the curated allow-list directories (from HARVEST_MAP in harvest_taxonomy),
builds MemoryEpisodeV1 episodes for each markdown file, and returns both the
episodes and skip reports.

This module performs NO NATS work - it only constructs episode objects and
handles file system traversal. The publisher (harvest_publisher) handles
NATS publishing.
"""

from __future__ import annotations

import logging
import subprocess
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from nats_core.events import MAX_EPISODE_BODY_BYTES, MemoryEpisodeV1

from guardkit.memory.harvest_taxonomy import (
    HARVEST_MAP,
    derive_episode_id,
    episode_type_for,
    natural_key_for,
)

logger = logging.getLogger(__name__)


@dataclass
class HarvestResult:
    """Result of walking harvest directories.

    Attributes:
        episodes: List of MemoryEpisodeV1 episodes ready for publishing.
        skipped_oversized: List of (repo_relative_path, byte_size) tuples for
            docs that exceeded MAX_EPISODE_BODY_BYTES.
        skipped_empty: Count of empty/whitespace-only bodies filtered out.
        counts_per_type: Count of episodes by episode_type.
    """

    episodes: list[MemoryEpisodeV1]
    skipped_oversized: list[tuple[str, int]]
    skipped_empty: int
    counts_per_type: dict[str, int]


def _get_file_mtime(file_path: Path, repo_root: Path) -> datetime:
    """Get file modification time, preferring git last-commit time.

    Args:
        file_path: Absolute path to the file.
        repo_root: Repository root directory.

    Returns:
        Timezone-aware datetime of last modification.
        Falls back to filesystem mtime if git is unavailable.
    """
    try:
        # Try git log for last commit time (more accurate for versioned files)
        relative_path = file_path.relative_to(repo_root)
        result = subprocess.run(
            ["git", "log", "-1", "--format=%aI", "--", str(relative_path)],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode == 0 and result.stdout.strip():
            return datetime.fromisoformat(result.stdout.strip())

    except (subprocess.SubprocessError, ValueError, OSError):
        # Git not available or other error - fall back to filesystem
        pass

    # Fallback to filesystem mtime
    stat = file_path.stat()
    return datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)


def _is_empty_body(body: str) -> bool:
    """Check if body is empty or whitespace-only.

    Args:
        body: Document body text.

    Returns:
        True if body is empty after stripping whitespace.
    """
    return not body.strip()


def _build_episode(
    file_path: Path,
    repo_root: Path,
    episode_type: str,
) -> MemoryEpisodeV1 | None:
    """Build MemoryEpisodeV1 for a single file.

    Args:
        file_path: Absolute path to the markdown file.
        repo_root: Repository root directory.
        episode_type: Episode type from taxonomy mapping.

    Returns:
        MemoryEpisodeV1 instance, or None if body is empty.

    Raises:
        ValueError: If body size exceeds MAX_EPISODE_BODY_BYTES.
    """
    # Read file content
    body = file_path.read_text(encoding="utf-8")

    # Filter empty bodies
    if _is_empty_body(body):
        return None

    # Check size (UTF-8 encoded)
    body_bytes = body.encode("utf-8")
    if len(body_bytes) >= MAX_EPISODE_BODY_BYTES:
        raise ValueError(
            f"Body size {len(body_bytes)} bytes exceeds "
            f"MAX_EPISODE_BODY_BYTES ({MAX_EPISODE_BODY_BYTES})"
        )

    # Build repo-relative path
    relative_path = file_path.relative_to(repo_root)
    source_ref = str(relative_path).replace("\\", "/")

    # Derive episode_id from natural key
    natural_key = natural_key_for(source_ref, episode_type)
    episode_id = derive_episode_id(natural_key)

    # Extract name from file stem
    name = file_path.stem

    # Get file modification time
    occurred_at = _get_file_mtime(file_path, repo_root)

    # Build episode
    return MemoryEpisodeV1(
        episode_id=episode_id,
        project_id="guardkit",  # Literal - no hyphens (DLQ poison)
        episode_type=episode_type,
        content_format="markdown",
        body=body,
        source="guardkit-harvest",
        source_ref=source_ref,
        name=name,
        occurred_at=occurred_at,
    )


def walk_harvest_dirs(repo_root: Path | str) -> HarvestResult:
    """Walk harvest directories and build MemoryEpisodeV1 episodes.

    Enumerates all *.md files under HARVEST_MAP directories, maps each to its
    episode_type, builds MemoryEpisodeV1 with full provenance, filters empty
    bodies, and skips oversized docs (>= MAX_EPISODE_BODY_BYTES).

    Args:
        repo_root: Path to repository root directory. Can be Path or string.

    Returns:
        HarvestResult with episodes, skip reports, and statistics.

    Example:
        >>> result = walk_harvest_dirs(Path("/path/to/guardkit"))
        >>> print(f"Harvested {len(result.episodes)} episodes")
        >>> print(f"Skipped {result.skipped_empty} empty docs")
        >>> print(f"Counts: {result.counts_per_type}")
    """
    repo_root = Path(repo_root)

    episodes: list[MemoryEpisodeV1] = []
    skipped_oversized: list[tuple[str, int]] = []
    skipped_empty = 0
    type_counts: Counter[str] = Counter()

    # Collect all directories to scan from HARVEST_MAP
    dirs_to_scan: set[Path] = set()
    for entry in HARVEST_MAP.values():
        for directory in entry.directories:
            dir_path = repo_root / directory
            if dir_path.exists() and dir_path.is_dir():
                dirs_to_scan.add(dir_path)

    # Walk each directory
    for dir_path in dirs_to_scan:
        # Find all .md files recursively
        for md_file in dir_path.rglob("*.md"):
            # Get repo-relative path for taxonomy lookup
            relative_path = md_file.relative_to(repo_root)
            relative_path_str = str(relative_path).replace("\\", "/")

            # Map to episode_type
            episode_type = episode_type_for(relative_path_str)
            if episode_type is None:
                # Outside curated allow-list (shouldn't happen if dirs are correct)
                logger.debug(
                    "Skipping %s - no episode_type mapping",
                    relative_path_str,
                )
                continue

            # Build episode
            try:
                episode = _build_episode(md_file, repo_root, episode_type)

                if episode is None:
                    # Empty body - filtered out
                    skipped_empty += 1
                    logger.debug(
                        "Skipped empty body: %s",
                        relative_path_str,
                    )
                    continue

                # Successfully built episode
                episodes.append(episode)
                type_counts[episode_type] += 1
                logger.debug(
                    "Harvested %s (type=%s, size=%d bytes)",
                    relative_path_str,
                    episode_type,
                    len(episode.body.encode()),
                )

            except ValueError as e:
                # Oversized body - record in skip report
                if "exceeds MAX_EPISODE_BODY_BYTES" in str(e):
                    body_size = len(md_file.read_bytes())
                    skipped_oversized.append((relative_path_str, body_size))
                    logger.warning(
                        "Skipped oversized doc %s (%d bytes): %s",
                        relative_path_str,
                        body_size,
                        str(e),
                    )
                else:
                    # Other ValueError - re-raise
                    raise

    return HarvestResult(
        episodes=episodes,
        skipped_oversized=skipped_oversized,
        skipped_empty=skipped_empty,
        counts_per_type=dict(type_counts),
    )
