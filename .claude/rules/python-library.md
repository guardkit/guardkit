---
paths: installer/core/lib/**/*.py, installer/core/commands/lib/**/*.py
---

# Python Library Development Patterns

These patterns are extracted from GuardKit's actual codebase for consistency.

## Module Documentation (NumPy-Style)

Use comprehensive docstrings with examples:

```python
def generate_task_id(
    prefix: Optional[str] = None,
    existing_ids: Optional[Set[str]] = None,
    max_attempts: int = 10
) -> str:
    """
    Generate a collision-free hash-based task ID.

    Uses SHA-256 hashing with progressive length scaling.

    Args:
        prefix: Optional prefix for categorization (e.g., "E01", "DOC")
        existing_ids: Optional set for collision checking
        max_attempts: Maximum collision resolution attempts (default: 10)

    Returns:
        Task ID in format "TASK-{hash}" or "TASK-{prefix}-{hash}"

    Raises:
        RuntimeError: If unable to generate unique ID after max_attempts

    Examples:
        >>> generate_task_id()
        'TASK-A3F2'
        >>> generate_task_id(prefix="E01")
        'TASK-E01-A3F2'
    """
```

## Public API Exports

Always define `__all__` for module exports:

```python
__all__ = [
    # Core ID generation
    'generate_task_id',
    'generate_simple_id',

    # Validation
    'validate_task_id',
    'is_valid_prefix',

    # Constants
    'TASK_DIRECTORIES',
    'SCALE_THRESHOLDS',
]
```

## Module-Level Constants

Use UPPER_SNAKE_CASE for module constants:

```python
# Task directories to scan for existing tasks
TASK_DIRECTORIES = [
    'tasks/backlog',
    'tasks/in_progress',
    'tasks/in_review',
    'tasks/completed',
    'tasks/blocked'
]

# Length scaling thresholds
SCALE_THRESHOLDS = [
    (0, 4),      # 0-499 tasks -> 4 characters
    (500, 5),    # 500-1,499 tasks -> 5 characters
    (1500, 6)    # 1,500+ tasks -> 6 characters
]

# Error message constants
ERROR_DUPLICATE = "Duplicate task ID: {task_id}\n   Existing file: {path}"
ERROR_INVALID_FORMAT = "Invalid task ID format: {task_id}"
```

## Compiled Regex Patterns

Pre-compile regex for performance:

```python
import re

# Compiled once at module load
_TASK_ID_PATTERN = re.compile(r'^TASK-([A-Z0-9]{2,4}-)?[A-Fa-f0-9]{4,6}(\.\d+)?$')
_PREFIX_PATTERN = re.compile(r'^[A-Z0-9]{2,4}$')

def validate_task_id(task_id: str) -> bool:
    """Validate task ID format."""
    if not isinstance(task_id, str) or not task_id:
        return False
    return bool(_TASK_ID_PATTERN.match(task_id))
```

## Type Hints

Use comprehensive typing:

```python
from typing import Optional, Dict, List, Set, Tuple
from pathlib import Path
from datetime import datetime

def process_files(
    source_dir: Path,
    patterns: List[str],
    options: Optional[Dict[str, str]] = None
) -> Tuple[int, List[Path]]:
    """Process files matching patterns."""
    ...
```

## Error Handling

Use specific exception types:

```python
class ManifestValidationError(Exception):
    """Exception raised when manifest validation fails."""
    pass

def validate_manifest(data: dict) -> None:
    if not data.get('name'):
        raise ManifestValidationError("Missing required field: name")
```

## Path Operations

Use pathlib consistently:

```python
from pathlib import Path

def count_existing_tasks() -> int:
    """Count all existing tasks across directories."""
    count = 0
    for dir_path in TASK_DIRECTORIES:
        path = Path(dir_path)
        if path.exists():
            count += len(list(path.glob('TASK-*.md')))
    return count
```

## Relative Imports

Use relative imports within packages:

```python
# From installer/core/lib/agent_enhancement/orchestrator.py
from ..state_paths import get_state_file, AGENT_ENHANCE_STATE
```
