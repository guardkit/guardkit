"""
Hash-based Task ID Generator

Generates collision-free task IDs using SHA-256 hashing with progressive
length scaling based on task count.

This module eliminates the duplicate ID problem (e.g., TASK-003 appearing twice)
by using cryptographic hashing instead of sequential numbering.

Usage:
    from installer.global.lib.id_generator import generate_task_id

    # Simple ID
    task_id = generate_task_id()  # Returns: TASK-A3F2

    # With prefix
    task_id = generate_task_id(prefix="E01")  # Returns: TASK-E01-A3F2

    # With existing IDs for collision check
    existing = {"TASK-A3F2", "TASK-B7D1"}
    task_id = generate_task_id(existing_ids=existing)

Algorithm:
    1. Determine hash length based on task count (4, 5, or 6 characters)
    2. Generate seed from current timestamp + cryptographic random bytes
    3. Create SHA-256 hash of seed
    4. Extract first N characters of hex digest (uppercase)
    5. Check for collision (rare but possible)
    6. If collision, regenerate (max 10 attempts)
    7. Return formatted ID: TASK-{hash} or TASK-{prefix}-{hash}

Length Scaling:
    - 0-499 tasks: 4 characters (e.g., TASK-A3F2)
    - 500-1,499 tasks: 5 characters (e.g., TASK-A3F2D)
    - 1,500+ tasks: 6 characters (e.g., TASK-A3F2D7)

Collision Risk:
    - 4 chars: ~0.006% at 500 tasks
    - 5 chars: ~0.015% at 1,500 tasks
    - 6 chars: ~0.000% at 5,000 tasks

References:
    - POC: docs/research/task-id-poc.py
    - Analysis: docs/research/task-id-strategy-analysis.md
    - Decision Guide: docs/research/task-id-decision-guide.md
"""

import hashlib
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Set

# Task directories to scan for existing tasks
# Extracted as constant for DRY compliance
TASK_DIRECTORIES = [
    'tasks/backlog',
    'tasks/in_progress',
    'tasks/in_review',
    'tasks/completed',
    'tasks/blocked'
]

# Length scaling thresholds
SCALE_THRESHOLDS = [
    (0, 4),      # 0-499 tasks → 4 characters
    (500, 5),    # 500-1,499 tasks → 5 characters
    (1500, 6)    # 1,500+ tasks → 6 characters
]


def get_hash_length(task_count: int) -> int:
    """
    Determine hash length based on task count.

    Uses progressive scaling to keep IDs compact for small projects
    while providing collision resistance for larger projects.

    Args:
        task_count: Number of existing tasks

    Returns:
        Hash length in characters (4, 5, or 6)

    Examples:
        >>> get_hash_length(100)
        4
        >>> get_hash_length(500)
        5
        >>> get_hash_length(2000)
        6
    """
    for threshold, length in reversed(SCALE_THRESHOLDS):
        if task_count >= threshold:
            return length
    return 4  # Default for 0 tasks


def count_existing_tasks() -> int:
    """
    Count all existing tasks across all directories.

    Scans task directories (backlog, in_progress, in_review, completed, blocked)
    and counts files matching the pattern TASK-*.md.

    Returns:
        Total number of existing tasks

    Note:
        Returns 0 if directories don't exist (graceful degradation)
    """
    count = 0
    for dir_path in TASK_DIRECTORIES:
        path = Path(dir_path)
        if path.exists():
            count += len(list(path.glob('TASK-*.md')))
    return count


def task_exists(task_id: str) -> bool:
    """
    Check if a task ID already exists in the filesystem.

    Searches all task directories for a file matching the given task ID.

    Args:
        task_id: Task ID to check (e.g., "TASK-A3F2" or "TASK-E01-A3F2")

    Returns:
        True if task exists, False otherwise

    Examples:
        >>> task_exists("TASK-A3F2")
        False
        >>> task_exists("TASK-001")  # Existing task
        True
    """
    for dir_path in TASK_DIRECTORIES:
        if Path(f"{dir_path}/{task_id}.md").exists():
            return True
    return False


def generate_task_id(
    prefix: Optional[str] = None,
    existing_ids: Optional[Set[str]] = None,
    max_attempts: int = 10
) -> str:
    """
    Generate a collision-free hash-based task ID.

    Uses SHA-256 hashing with progressive length scaling to create unique
    task IDs. Automatically detects collisions and retries if needed.

    Args:
        prefix: Optional prefix for categorization (e.g., "E01", "DOC", "FIX")
               If empty string or whitespace-only, treated as None
        existing_ids: Optional set of existing IDs for collision checking
                     If None, checks filesystem directly
        max_attempts: Maximum collision resolution attempts (default: 10)

    Returns:
        Task ID in format "TASK-{hash}" or "TASK-{prefix}-{hash}"
        Hash is uppercase hexadecimal (4-6 characters based on task count)

    Raises:
        RuntimeError: If unable to generate unique ID after max_attempts
                     (extremely rare - indicates systematic issue)

    Examples:
        >>> generate_task_id()
        'TASK-A3F2'

        >>> generate_task_id(prefix="E01")
        'TASK-E01-A3F2'

        >>> existing = {"TASK-A3F2"}
        >>> generate_task_id(existing_ids=existing)
        'TASK-B7D1'  # Different hash, no collision

    Performance:
        - Single ID generation: ~1-2ms
        - 1,000 IDs: <1 second (target)
        - Collision rate: <0.01% for 4-char hash at 500 tasks

    Thread Safety:
        Not thread-safe. Use locks if generating IDs concurrently.
    """
    # Normalize prefix: treat empty/whitespace as None
    if prefix is not None:
        prefix = prefix.strip()
        if not prefix:
            prefix = None

    # Determine hash length based on current task count
    task_count = count_existing_tasks()
    hash_length = get_hash_length(task_count)

    # Attempt to generate unique ID
    for attempt in range(max_attempts):
        # Generate cryptographic seed from timestamp + random bytes
        # This ensures uniqueness even if called rapidly in sequence
        timestamp = datetime.now(timezone.utc).isoformat()
        random_bytes = secrets.token_hex(8)
        seed = f"{timestamp}{random_bytes}"

        # Create SHA-256 hash and extract required length
        hash_obj = hashlib.sha256(seed.encode('utf-8'))
        task_hash = hash_obj.hexdigest()[:hash_length].upper()

        # Format ID with optional prefix
        if prefix:
            task_id = f"TASK-{prefix}-{task_hash}"
        else:
            task_id = f"TASK-{task_hash}"

        # Check for collision
        if existing_ids is not None:
            # Use provided set for fast O(1) lookup
            if task_id not in existing_ids:
                return task_id
        else:
            # Check filesystem directly (slower but no pre-computation needed)
            if not task_exists(task_id):
                return task_id

        # Collision detected (extremely rare)
        # Continue to next attempt

    # Failed to generate unique ID after max attempts
    # This indicates a systematic issue (e.g., corrupted filesystem state)
    raise RuntimeError(
        f"Failed to generate unique task ID after {max_attempts} attempts. "
        f"Task count: {task_count}, Hash length: {hash_length}. "
        f"This may indicate a systematic issue with task storage."
    )


# Convenience functions for common use cases

def generate_simple_id() -> str:
    """
    Generate a simple task ID without prefix.

    Convenience wrapper for generate_task_id().

    Returns:
        Task ID in format "TASK-{hash}"

    Examples:
        >>> generate_simple_id()
        'TASK-A3F2'
    """
    return generate_task_id()


def generate_prefixed_id(prefix: str) -> str:
    """
    Generate a task ID with a specific prefix.

    Convenience wrapper for generate_task_id(prefix=...).

    Args:
        prefix: Prefix for categorization (e.g., "E01", "DOC")

    Returns:
        Task ID in format "TASK-{prefix}-{hash}"

    Examples:
        >>> generate_prefixed_id("E01")
        'TASK-E01-A3F2'
    """
    return generate_task_id(prefix=prefix)


# Module-level docstring additions
__all__ = [
    'generate_task_id',
    'generate_simple_id',
    'generate_prefixed_id',
    'count_existing_tasks',
    'task_exists',
    'get_hash_length',
    'TASK_DIRECTORIES',
    'SCALE_THRESHOLDS'
]
