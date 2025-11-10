---
id: TASK-050
title: Add JSON persistence for ID mappings
status: in_progress
created: 2025-01-08T00:00:00Z
updated: 2025-11-10T14:45:00Z
priority: high
tags: [infrastructure, hash-ids, persistence]
complexity: 4
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Add JSON persistence for ID mappings

## Description

Implement persistent storage for internal ↔ external ID mappings and PM tool counters using JSON files. This ensures mappings survive across sessions and provides a reliable registry for bidirectional lookups.

## Acceptance Criteria

- [ ] Store mappings in `.claude/state/external_id_mapping.json`
- [ ] Store counters in `.claude/state/external_id_counters.json`
- [ ] Atomic read-modify-write operations (prevent corruption)
- [ ] File locking for concurrent access
- [ ] Auto-create directories if missing
- [ ] Pretty-printed JSON for human readability
- [ ] Backup previous version before write
- [ ] Validation on load (detect corruption)
- [ ] Migration support for schema changes

## Test Requirements

- [ ] Unit tests for save/load operations
- [ ] Unit tests for atomic writes
- [ ] Unit tests for file locking
- [ ] Unit tests for corruption detection
- [ ] Integration tests with ExternalIDMapper
- [ ] Concurrent access tests (10 simultaneous reads/writes)
- [ ] Test coverage ≥90%

## Implementation Notes

### File Locations
```
.claude/state/
├── external_id_mapping.json       # Internal ↔ External mappings
├── external_id_counters.json      # Next available numbers per tool
├── external_id_mapping.json.bak   # Backup before last write
└── external_id_counters.json.bak  # Backup before last write
```

### Mapping File Format
```json
{
  "version": "1.0",
  "updated": "2025-01-08T10:30:00Z",
  "mappings": {
    "TASK-E01-b2c4": {
      "jira": "PROJ-456",
      "azure_devops": "1234",
      "linear": "TEAM-789",
      "github": "234",
      "created": "2025-01-08T10:00:00Z",
      "epic": "EPIC-001"
    }
  }
}
```

### Counter File Format
```json
{
  "version": "1.0",
  "updated": "2025-01-08T10:30:00Z",
  "counters": {
    "jira": {
      "PROJ": 457,
      "TEST": 12
    },
    "azure_devops": 1235,
    "linear": {
      "TEAM": 789
    },
    "github": 234
  }
}
```

### Key Functions
```python
def save_mappings(mappings: Dict[str, Dict[str, str]]) -> None:
    """Save mappings to JSON with atomic write."""

def load_mappings() -> Dict[str, Dict[str, str]]:
    """Load mappings from JSON, handle missing/corrupt file."""

def save_counters(counters: Dict[str, Any]) -> None:
    """Save counters to JSON with atomic write."""

def load_counters() -> Dict[str, Any]:
    """Load counters from JSON, handle missing/corrupt file."""

def atomic_write(path: Path, data: dict) -> None:
    """Write JSON atomically: temp file → rename."""

def create_backup(path: Path) -> None:
    """Create .bak file before overwrite."""
```

### Atomic Write Pattern
```python
import json
import tempfile
from pathlib import Path

def atomic_write(path: Path, data: dict) -> None:
    """Write JSON atomically to prevent corruption."""
    # Create backup
    if path.exists():
        backup_path = path.with_suffix(path.suffix + '.bak')
        shutil.copy2(path, backup_path)

    # Write to temp file
    temp_fd, temp_path = tempfile.mkstemp(
        dir=path.parent,
        prefix='.tmp_',
        suffix='.json'
    )

    try:
        with os.fdopen(temp_fd, 'w') as f:
            json.dump(data, f, indent=2, sort_keys=True)
            f.flush()
            os.fsync(f.fileno())  # Force disk write

        # Atomic rename
        os.rename(temp_path, path)
    except Exception:
        # Cleanup on failure
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        raise
```

### File Locking
```python
import fcntl

def with_file_lock(path: Path):
    """Context manager for file locking."""
    lock_path = path.with_suffix('.lock')

    with open(lock_path, 'w') as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
```

### Validation
```python
def validate_mapping_file(data: dict) -> bool:
    """Validate mapping file structure."""
    required_keys = ['version', 'updated', 'mappings']
    if not all(k in data for k in required_keys):
        return False

    # Validate each mapping
    for internal_id, external_ids in data['mappings'].items():
        if not isinstance(external_ids, dict):
            return False

    return True
```

### Error Handling
- **Missing file**: Create with empty structure
- **Corrupt file**: Restore from .bak if available, otherwise start fresh
- **Lock timeout**: Retry 3 times with exponential backoff
- **Write failure**: Preserve backup, raise clear error

## Dependencies

- TASK-049: External ID mapper (defines data structure)

## Related Tasks

- TASK-049: External ID mapper
- TASK-051: Update task frontmatter
- TASK-052: Migration script

## Test Execution Log

[Automatically populated by /task-work]
