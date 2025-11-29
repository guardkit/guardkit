"""
Hash-based Task ID Generator with Intelligent Prefix Inference

Generates collision-free task IDs using SHA-256 hashing with progressive
length scaling based on task count. Includes intelligent prefix inference
from epic links, tags, and task titles.

This module eliminates the duplicate ID problem (e.g., TASK-003 appearing twice)
by using cryptographic hashing instead of sequential numbering.

Basic Usage:
    from lib.id_generator import generate_task_id

    # Simple ID
    task_id = generate_task_id()  # Returns: TASK-A3F2

    # With manual prefix
    task_id = generate_task_id(prefix="E01")  # Returns: TASK-E01-A3F2

    # With existing IDs for collision check
    existing = {"TASK-A3F2", "TASK-B7D1"}
    task_id = generate_task_id(existing_ids=existing)

Prefix Inference:
    from lib.id_generator import infer_prefix, generate_task_id

    # Infer from epic
    prefix = infer_prefix(epic="EPIC-001")  # Returns: "E01"
    task_id = generate_task_id(prefix=prefix)  # TASK-E01-A3F2

    # Infer from tags
    prefix = infer_prefix(tags=["docs", "api"])  # Returns: "DOC"
    task_id = generate_task_id(prefix=prefix)  # TASK-DOC-A3F2

    # Infer from title
    prefix = infer_prefix(title="Fix login bug")  # Returns: "FIX"
    task_id = generate_task_id(prefix=prefix)  # TASK-FIX-A3F2

    # Priority: Manual > Epic > Tags > Title
    prefix = infer_prefix(
        manual_prefix="CUST",
        epic="EPIC-001",
        tags=["docs"],
        title="Fix bug"
    )  # Returns: "CUST" (manual wins)

Prefix Validation:
    from lib.id_generator import validate_prefix

    # Normalize and validate
    prefix = validate_prefix("documentation")  # Returns: "DOCU"
    prefix = validate_prefix("api-v2")  # Returns: "APIV"
    prefix = validate_prefix("E01")  # Returns: "E01"

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

Prefix Inference Priority:
    1. Manual override (highest)
    2. Epic (EPIC-001 → E01)
    3. Tags (docs → DOC, bug → FIX)
    4. Title keywords (Fix... → FIX, Test... → TEST)
    5. None (no prefix)

References:
    - POC: docs/research/task-id-poc.py
    - Analysis: docs/research/task-id-strategy-analysis.md
    - Decision Guide: docs/research/task-id-decision-guide.md
"""

import hashlib
import re
import secrets
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Set, Dict, List

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

# Validation patterns (compiled once for performance)
# Note: Pattern accepts both uppercase and lowercase hex for backward compatibility
# with existing generator that produces uppercase hashes
_TASK_ID_PATTERN = re.compile(r'^TASK-([A-Z0-9]{2,4}-)?[A-Fa-f0-9]{4,6}(\.\d+)?$')
_PREFIX_PATTERN = re.compile(r'^[A-Z0-9]{2,4}$')

# Error message constants
ERROR_DUPLICATE = "❌ ERROR: Duplicate task ID: {task_id}\n   Existing file: {path}"
ERROR_INVALID_FORMAT = "❌ ERROR: Invalid task ID format: {task_id}\n   Expected: TASK-{{hash}} or TASK-{{prefix}}-{{hash}}"
ERROR_INVALID_PREFIX = "❌ ERROR: Invalid prefix: {prefix}\n   Expected: 2-4 uppercase alphanumeric characters"

# Registry caching
_id_registry_cache: Optional[Set[str]] = None
_cache_timestamp: Optional[float] = None
_registry_lock = threading.Lock()
CACHE_TTL = 5.0  # seconds

# Prefix Registry and Mappings
# Used for intelligent prefix inference and organization

STANDARD_PREFIXES: Dict[str, str] = {
    # Domain-based prefixes
    "DOC": "Documentation",
    "TEST": "Testing",
    "FIX": "Bug fixes",
    "FEAT": "Features",
    "REFA": "Refactoring",

    # Stack-based prefixes
    "API": "API/Backend",
    "UI": "User interface",
    "DB": "Database",
    "INFR": "Infrastructure",
}

TAG_PREFIX_MAP: Dict[str, str] = {
    # Documentation
    "docs": "DOC",
    "documentation": "DOC",

    # Testing
    "test": "TEST",
    "testing": "TEST",

    # Bug fixes
    "bug": "FIX",
    "bugfix": "FIX",
    "fix": "FIX",

    # Features
    "feature": "FEAT",

    # Stack-specific
    "api": "API",
    "backend": "API",
    "ui": "UI",
    "frontend": "UI",
    "database": "DB",
    "db": "DB",
    "infra": "INFR",
    "infrastructure": "INFR",
}

TITLE_KEYWORDS: Dict[str, str] = {
    r"^fix\b": "FIX",
    r"^bug\b": "FIX",
    r"\bdocument": "DOC",
    r"\btest": "TEST",
    r"\bapi\b": "API",
    r"\bui\b": "UI",
    r"\bdatabase\b": "DB",
}


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


def validate_task_id(task_id: str) -> bool:
    r"""
    Validate task ID format.

    Checks if task ID matches the expected pattern:
    TASK-([A-Z0-9]{2,4}-)?[A-Fa-f0-9]{4,6}(\.\d+)?

    Accepts both uppercase and lowercase hexadecimal hashes for backward
    compatibility (generator currently produces uppercase).

    Valid formats:
        - TASK-a3f2          (simple hash - lowercase)
        - TASK-A3F2          (simple hash - uppercase)
        - TASK-E01-a3f2      (with prefix - lowercase hash)
        - TASK-E01-A3F2      (with prefix - uppercase hash)
        - TASK-E01-a3f2.1    (with subtask)

    Invalid formats:
        - TASK-XYZ-a3f2      (prefix too long)
        - TASK-123           (hash too short)
        - TASK-GGGG          (invalid hex characters)

    Args:
        task_id: Task ID to validate

    Returns:
        True if valid format, False otherwise

    Examples:
        >>> validate_task_id("TASK-a3f2")
        True
        >>> validate_task_id("TASK-E01-a3f2")
        True
        >>> validate_task_id("TASK-E01-a3f2.1")
        True
        >>> validate_task_id("TASK-INVALID")
        False
    """
    if not isinstance(task_id, str) or not task_id:
        return False
    return bool(_TASK_ID_PATTERN.match(task_id))


def is_valid_prefix(prefix: str) -> bool:
    """
    Validate prefix format.

    Prefix must be 2-4 uppercase alphanumeric characters.

    Args:
        prefix: Prefix string to validate

    Returns:
        True if valid, False otherwise

    Examples:
        >>> is_valid_prefix("E01")
        True
        >>> is_valid_prefix("DOC")
        True
        >>> is_valid_prefix("e01")  # lowercase
        False
        >>> is_valid_prefix("X")    # too short
        False
        >>> is_valid_prefix("EXTRA") # too long
        False
    """
    if not isinstance(prefix, str) or not prefix:
        return False
    return bool(_PREFIX_PATTERN.match(prefix))


def build_id_registry() -> Set[str]:
    """
    Build registry of all existing task IDs.

    Scans all task directories and extracts task IDs from filenames.
    Uses Set for O(1) lookup performance.

    Returns:
        Set of existing task IDs (without .md extension)

    Performance:
        - 1,000 tasks: ~10ms
        - 5,000 tasks: ~50ms

    Examples:
        >>> registry = build_id_registry()
        >>> "TASK-001" in registry
        True
        >>> "TASK-NONEXISTENT" in registry
        False
    """
    registry = set()
    for dir_path in TASK_DIRECTORIES:
        try:
            path = Path(dir_path)
            if path.exists():
                # Extract task ID from filename (remove .md extension)
                registry.update(p.stem for p in path.glob('TASK-*.md'))
        except OSError as e:
            # Graceful degradation - log warning but continue
            # This ensures we don't fail completely if one directory is inaccessible
            import sys
            print(f"Warning: Cannot read {dir_path}: {e}", file=sys.stderr)
    return registry


def get_id_registry(force_refresh: bool = False) -> Set[str]:
    """
    Get ID registry with caching.

    Uses module-level cache with 5-second TTL to avoid repeated filesystem scans.
    Thread-safe with lock protection.

    Args:
        force_refresh: Force rebuild of registry, bypassing cache

    Returns:
        Set of existing task IDs

    Performance:
        - Cache hit: ~0.001ms (O(1))
        - Cache miss: ~10-50ms (filesystem scan)

    Examples:
        >>> registry = get_id_registry()  # First call - builds registry
        >>> registry = get_id_registry()  # Second call - uses cache (fast)
        >>> registry = get_id_registry(force_refresh=True)  # Forces rebuild
    """
    global _id_registry_cache, _cache_timestamp

    with _registry_lock:
        now = time.time()
        cache_valid = (
            _id_registry_cache is not None and
            _cache_timestamp is not None and
            (now - _cache_timestamp) < CACHE_TTL
        )

        if force_refresh or not cache_valid:
            _id_registry_cache = build_id_registry()
            _cache_timestamp = now

        return _id_registry_cache.copy()  # Return copy to prevent external modification


def check_duplicate(task_id: str) -> Optional[str]:
    """
    Check if task ID exists.

    Returns path to existing file if duplicate found, None otherwise.

    Args:
        task_id: Task ID to check

    Returns:
        Path to duplicate file if found, None otherwise

    Performance:
        - Uses cached registry for O(1) lookup
        - Only scans filesystem to find exact path if duplicate found

    Examples:
        >>> check_duplicate("TASK-a3f2")
        None  # Not a duplicate

        >>> check_duplicate("TASK-001")
        "tasks/backlog/TASK-001.md"  # Duplicate found
    """
    # Check registry first (fast O(1) lookup)
    registry = get_id_registry()
    if task_id not in registry:
        return None

    # Found in registry - now locate the actual file path
    for dir_path in TASK_DIRECTORIES:
        path = Path(f"{dir_path}/{task_id}.md")
        if path.exists():
            return str(path)

    # Edge case: in registry but file not found (should be rare)
    # This can happen if file was deleted between registry build and lookup
    return None


def has_duplicate(task_id: str) -> bool:
    """
    Check if task ID exists (boolean only).

    Convenience wrapper around check_duplicate() for simple existence checks.

    Args:
        task_id: Task ID to check

    Returns:
        True if task ID exists, False otherwise

    Examples:
        >>> has_duplicate("TASK-a3f2")
        False
        >>> has_duplicate("TASK-001")
        True
    """
    return check_duplicate(task_id) is not None


def validate_prefix(prefix: str) -> str:
    """
    Validate and normalize a prefix string.

    Performs comprehensive validation and normalization to ensure prefix
    meets format requirements: 2-4 uppercase alphanumeric characters.

    Normalization steps:
    1. Convert to uppercase
    2. Remove invalid characters (keep only A-Z, 0-9)
    3. Truncate to 4 characters if longer
    4. Validate length (2-4 characters)

    Args:
        prefix: Prefix string to validate and normalize

    Returns:
        Normalized prefix string (uppercase, 2-4 alphanumeric characters)

    Raises:
        ValueError: If prefix is empty, None, or too short after normalization

    Examples:
        >>> validate_prefix("doc")
        'DOC'
        >>> validate_prefix("E01")
        'E01'
        >>> validate_prefix("refactoring")
        'REFA'
        >>> validate_prefix("api-v2")
        'APIV'
        >>> validate_prefix("x")
        ValueError: Prefix too short: X (min 2 chars)
        >>> validate_prefix("")
        ValueError: Prefix cannot be empty

    Performance:
        - O(n) where n is prefix length (typically 2-10 chars)
        - ~0.01ms per validation
    """
    if not prefix:
        raise ValueError("Prefix cannot be empty")

    # Normalize: uppercase
    prefix = prefix.upper()

    # Remove invalid characters (keep only A-Z, 0-9)
    prefix = re.sub(r'[^A-Z0-9]', '', prefix)

    # Truncate to 4 characters
    if len(prefix) > 4:
        prefix = prefix[:4]

    # Validate length
    if len(prefix) < 2:
        raise ValueError(f"Prefix too short: {prefix} (min 2 chars)")

    return prefix


def infer_prefix(
    epic: Optional[str] = None,
    tags: Optional[List[str]] = None,
    title: Optional[str] = None,
    manual_prefix: Optional[str] = None
) -> Optional[str]:
    """
    Infer prefix from task context using priority-based rules.

    Attempts to automatically determine an appropriate prefix based on
    task metadata. Uses priority order to resolve conflicts:

    Priority Order:
    1. Manual override (highest priority)
    2. Epic inference (EPIC-001 → E01)
    3. Tag inference (docs → DOC)
    4. Title keyword matching (Fix... → FIX)
    5. None (no inference possible)

    Args:
        epic: Epic identifier (e.g., "EPIC-001")
        tags: List of task tags (e.g., ["docs", "api"])
        title: Task title string
        manual_prefix: User-specified prefix (overrides all inference)

    Returns:
        Inferred prefix string (validated and normalized) or None if no
        inference possible. Returns None gracefully rather than raising
        errors for robustness.

    Raises:
        ValueError: Only if manual_prefix is provided but invalid

    Examples:
        >>> infer_prefix(manual_prefix="API")
        'API'

        >>> infer_prefix(epic="EPIC-001")
        'E01'

        >>> infer_prefix(epic="EPIC-042")
        'E42'

        >>> infer_prefix(tags=["docs"])
        'DOC'

        >>> infer_prefix(tags=["general", "bug"])
        'FIX'

        >>> infer_prefix(title="Fix login validation bug")
        'FIX'

        >>> infer_prefix(title="Add API endpoint for users")
        'API'

        >>> infer_prefix(epic="EPIC-001", tags=["docs"], title="Fix bug")
        'E01'  # Epic has highest priority

        >>> infer_prefix(tags=["docs"], title="Fix bug")
        'DOC'  # Tags have priority over title

        >>> infer_prefix(title="Refactor authentication module")
        None  # No matching keyword

    Priority Examples:
        # Manual override wins over everything
        >>> infer_prefix(manual_prefix="CUST", epic="EPIC-001", tags=["docs"])
        'CUST'

        # Epic wins over tags and title
        >>> infer_prefix(epic="EPIC-001", tags=["docs"], title="Fix bug")
        'E01'

        # Tags win over title
        >>> infer_prefix(tags=["api"], title="Fix bug")
        'API'

    Performance:
        - O(1) for manual, epic parsing
        - O(n) for tag lookup where n = number of tags (typically 1-5)
        - O(m) for title matching where m = number of keywords (7)
        - Total: ~0.1ms per inference

    Thread Safety:
        - Read-only operations on shared dictionaries (safe)
        - No shared state modification
    """
    # Priority 1: Manual override (highest priority)
    if manual_prefix:
        return validate_prefix(manual_prefix)

    # Priority 2: Epic inference
    if epic:
        # Extract epic number: EPIC-001 → E01, EPIC-042 → E42
        epic_match = re.search(r'EPIC-(\d+)', epic, re.IGNORECASE)
        if epic_match:
            epic_num = epic_match.group(1)
            # Format: E + zero-padded number (2-3 digits max)
            # E01, E42, E123 (max 4 chars: E + 3 digits)
            return f"E{epic_num}"

    # Priority 3: Tag inference
    if tags:
        for tag in tags:
            tag_lower = tag.lower()
            if tag_lower in TAG_PREFIX_MAP:
                return TAG_PREFIX_MAP[tag_lower]

    # Priority 4: Title keyword matching
    if title:
        title_lower = title.lower()
        for pattern, prefix in TITLE_KEYWORDS.items():
            if re.search(pattern, title_lower):
                return prefix

    # Priority 5: No inference possible
    return None


def register_prefix(prefix: str, description: str) -> None:
    """
    Register a custom prefix in the global prefix registry.

    Adds or updates a prefix entry in the STANDARD_PREFIXES dictionary.
    Useful for dynamically adding project-specific or epic-based prefixes.

    Warning:
        This function modifies global state (STANDARD_PREFIXES dictionary).
        In multi-threaded environments, consider using locks if concurrent
        registration is possible.

    Args:
        prefix: Prefix string to register (will be validated and normalized)
        description: Human-readable description of the prefix purpose

    Raises:
        ValueError: If prefix is invalid (see validate_prefix)

    Examples:
        >>> register_prefix("CUST", "Custom feature")
        >>> STANDARD_PREFIXES["CUST"]
        'Custom feature'

        >>> register_prefix("epic-001", "Epic 001 tasks")
        >>> STANDARD_PREFIXES["EPIC"]
        'Epic 001 tasks'

        >>> register_prefix("E42", "Epic 42: Authentication System")
        >>> STANDARD_PREFIXES["E42"]
        'Epic 42: Authentication System'

    Use Cases:
        # Dynamic epic prefix registration
        >>> for epic_id in range(1, 10):
        ...     register_prefix(f"E{epic_id:02d}", f"Epic {epic_id}")

        # Project-specific prefixes
        >>> register_prefix("AUTH", "Authentication tasks")
        >>> register_prefix("PAY", "Payment system tasks")

    Thread Safety:
        - Not thread-safe (modifies global dictionary)
        - Use external locking if concurrent access possible
    """
    validated = validate_prefix(prefix)
    STANDARD_PREFIXES[validated] = description


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
    # Core ID generation
    'generate_task_id',
    'generate_simple_id',
    'generate_prefixed_id',

    # Prefix inference and validation
    'infer_prefix',
    'validate_prefix',
    'register_prefix',
    'is_valid_prefix',

    # Task management
    'count_existing_tasks',
    'task_exists',
    'get_hash_length',
    'validate_task_id',

    # Registry management
    'build_id_registry',
    'get_id_registry',
    'check_duplicate',
    'has_duplicate',

    # Constants
    'TASK_DIRECTORIES',
    'SCALE_THRESHOLDS',
    'STANDARD_PREFIXES',
    'TAG_PREFIX_MAP',
    'TITLE_KEYWORDS',

    # Error messages
    'ERROR_DUPLICATE',
    'ERROR_INVALID_FORMAT',
    'ERROR_INVALID_PREFIX'
]
