"""Harvest taxonomy configuration and episode ID derivation.

This module provides pure-Python config and helpers for GuardKit's memory harvest
publisher. No NATS dependencies, no file I/O - just deterministic functions that
map curated document paths to episode types and derive stable episode IDs.

The episode_id derivation is byte-identical to fleet-memory's reindex publisher
to ensure idempotent publishing when shared keys exist.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import NamedTuple


class HarvestEntry(NamedTuple):
    """Configuration entry for a harvested document type.

    Attributes:
        episode_type: NATS subject segment for this document class (e.g., "adr", "review_report")
        directories: List of repo-relative directory paths to harvest
        content_format: Content format identifier ("markdown" for all current entries)
    """

    episode_type: str
    directories: list[str]
    content_format: str


# Harvest taxonomy: curated allow-list of directory → episode_type mappings.
# Each entry maps an episode_type to the directories it covers and its content format.
# Transient directories (archive, checkpoints, state, history) are intentionally excluded.
HARVEST_MAP: dict[str, HarvestEntry] = {
    "adr": HarvestEntry(
        episode_type="adr",
        directories=["docs/adr", "docs/adrs", "docs/decisions"],
        content_format="markdown",
    ),
    "review_report": HarvestEntry(
        episode_type="review_report",
        # docs/reviews is EXCLUDED: it holds autobuild/seeding/profiling RUN CAPTURES
        # (run_N.md, vllm_run_*.md, *seed*.md, phase_N_build.md), not knowledge — 83%
        # noise and ~78% of the whole harvested corpus's noise (see
        # fleet-memory/docs/evals/FEAT-MEM-05-parity-eval-2026-06-27.md). The LLM-free
        # store ingests raw, so noisy logs out-rank real content in retrieval. Legitimate
        # hand-written reviews live in docs/code-review.
        directories=["docs/code-review"],
        content_format="markdown",
    ),
    "feature_outcome": HarvestEntry(
        episode_type="feature_outcome",
        directories=["docs/completion-reports", "docs/retro"],
        content_format="markdown",
    ),
    "document": HarvestEntry(
        episode_type="document",
        directories=["docs/design", "docs/guides", "docs/reference"],
        content_format="markdown",
    ),
}

# NATS subject segment validation pattern
_NATS_SUBJECT_SEGMENT_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9\-_]*$")


def derive_episode_id(natural_key: str) -> str:
    """Derive deterministic episode_id from natural key.

    Uses SHA-256 hash of natural key to ensure the same payload published twice
    yields the same episode_id for JetStream Msg-Id deduplication.

    This implementation is byte-identical to fleet-memory's _derive_episode_id
    to ensure consistent episode IDs across different publishers.

    Args:
        natural_key: Three-segment colon-separated key (e.g., "guardkit:path:type")

    Returns:
        Deterministic episode ID in format "ep-{16-char-hex-prefix}"

    Example:
        >>> derive_episode_id("guardkit:docs/adr/001.md:adr")
        'ep-a1b2c3d4e5f6g7h8'
    """
    hash_bytes = hashlib.sha256(natural_key.encode("utf-8")).digest()
    return f"ep-{hash_bytes.hex()[:16]}"


def natural_key_for(repo_relative_path: str, episode_type: str) -> str:
    """Construct natural key from repo-relative path and episode type.

    The natural key is a three-segment colon-separated identifier:
    "guardkit:{repo_relative_path}:{episode_type}"

    Args:
        repo_relative_path: Path relative to repository root
        episode_type: Episode type from HARVEST_MAP (e.g., "adr", "review_report")

    Returns:
        Three-segment natural key for episode_id derivation

    Example:
        >>> natural_key_for("docs/adr/001-decision.md", "adr")
        'guardkit:docs/adr/001-decision.md:adr'
    """
    return f"guardkit:{repo_relative_path}:{episode_type}"


def episode_type_for(repo_relative_path: str) -> str | None:
    """Resolve episode_type from repo-relative path via longest-prefix match.

    Searches HARVEST_MAP for the longest directory prefix that matches the given path.
    Returns None for paths outside the curated allow-list.

    Args:
        repo_relative_path: Path relative to repository root (forward slashes)

    Returns:
        Episode type if path matches a harvested directory, None otherwise

    Example:
        >>> episode_type_for("docs/adr/001-decision.md")
        'adr'
        >>> episode_type_for("docs/reviews/feature-x-review.md")
        'review_report'
        >>> episode_type_for("docs/archive/old-doc.md")
        None
    """
    # Normalize path separators and convert to Path for consistent matching
    path = Path(repo_relative_path)
    path_str = str(path).replace("\\", "/")

    # Find longest matching directory prefix
    longest_match: tuple[str, str] | None = None
    longest_length = 0

    for entry in HARVEST_MAP.values():
        for directory in entry.directories:
            # Normalize directory path
            dir_normalized = directory.replace("\\", "/")

            # Check if path is under this directory
            if path_str.startswith(dir_normalized + "/") or path_str == dir_normalized:
                dir_length = len(dir_normalized)
                if dir_length > longest_length:
                    longest_length = dir_length
                    longest_match = (entry.episode_type, dir_normalized)

    return longest_match[0] if longest_match else None


def validate_episode_types() -> None:
    """Validate that all episode_type values are valid NATS subject segments.

    A valid NATS subject segment matches: ^[a-zA-Z0-9][a-zA-Z0-9\\-_]*$
    (starts with alphanumeric, contains only alphanumeric, hyphens, and underscores)

    Raises:
        ValueError: If any episode_type is not a valid NATS subject segment
    """
    invalid_types = []
    for entry in HARVEST_MAP.values():
        if not _NATS_SUBJECT_SEGMENT_PATTERN.match(entry.episode_type):
            invalid_types.append(entry.episode_type)

    if invalid_types:
        raise ValueError(
            f"Invalid NATS subject segments in HARVEST_MAP: {invalid_types}"
        )


# Validate episode types on module import
validate_episode_types()
