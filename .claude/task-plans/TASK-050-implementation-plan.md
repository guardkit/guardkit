# TASK-050: Implementation Plan
## JSON Persistence for ID Mappings

**Created:** 2025-11-10T14:45:00Z
**Status:** In Progress
**Complexity:** 4/10 (Medium-Low)

---

## 1. Overview

Add persistent JSON storage for external ID mappings and counters from TASK-049, ensuring data survives across sessions with atomic operations and corruption protection.

### Goals
- Persistent storage for mappings and counters
- Atomic read-modify-write operations
- File locking for concurrent access
- Backup mechanism for recovery
- Corruption detection and recovery
- Seamless integration with ExternalIDMapper

---

## 2. Architecture Design

### 2.1 Module Structure
```
installer/core/lib/
├── external_id_mapper.py          (EXISTING - from TASK-049)
└── external_id_persistence.py     (NEW - persistence layer)

.claude/state/
├── external_id_mapping.json       (NEW - mapping data)
├── external_id_counters.json      (NEW - counter data)
├── external_id_mapping.json.bak   (NEW - backup)
└── external_id_counters.json.bak  (NEW - backup)

tests/lib/
├── test_external_id_mapper.py     (EXISTING - from TASK-049)
└── test_external_id_persistence.py (NEW - persistence tests)
```

### 2.2 Data Structures

**Mapping File Format** (aligns with TASK-049):
```json
{
  "version": "1.0",
  "updated": "2025-11-10T14:45:00Z",
  "mappings": {
    "TASK-E01-b2c4": {
      "jira": "PROJ-456",
      "azure_devops": "1234",
      "linear": "TEAM-789",
      "github": "234"
    }
  }
}
```

**Counter File Format** (aligns with TASK-049):
```json
{
  "version": "1.0",
  "updated": "2025-11-10T14:45:00Z",
  "counters": {
    "jira": {"PROJ": 457, "TEST": 12},
    "azure_devops": 1235,
    "linear": {"TEAM": 789, "DESIGN": 45},
    "github": 234
  }
}
```

**Note:** No `created` or `epic` fields per TASK-049 architectural review decisions.

### 2.3 Atomic Write Strategy
1. Create backup of existing file
2. Write to temporary file with `fsync()`
3. Atomic rename temp → target
4. Cleanup on failure

### 2.4 File Locking Strategy
Use `fcntl` (Unix) with .lock files for cross-process synchronization.

---

## 3. Implementation Steps

### Phase 3.1: Core Persistence Module (45 min)
**File:** `installer/core/lib/external_id_persistence.py`

**Components:**
1. `ExternalIDPersistence` class
2. Path management (`.claude/state/`)
3. File locking context manager
4. Atomic write implementation
5. Backup creation/restoration

**Functions:**
```python
class ExternalIDPersistence:
    def __init__(self, state_dir: Path = None)
    def save_mappings(self, mappings: Dict) -> None
    def load_mappings(self) -> Dict
    def save_counters(self, counters: Dict) -> None
    def load_counters(self) -> Dict
    def _atomic_write(self, path: Path, data: dict) -> None
    def _create_backup(self, path: Path) -> None
    def _restore_from_backup(self, path: Path) -> None
    def _validate_mapping_data(self, data: dict) -> bool
    def _validate_counter_data(self, data: dict) -> bool
```

### Phase 3.2: Atomic Write Implementation (30 min)

**Atomic Write with Backup:**
```python
def _atomic_write(self, path: Path, data: dict) -> None:
    """
    Write JSON atomically with backup.

    Steps:
    1. Create backup if file exists
    2. Write to temp file
    3. Flush and fsync
    4. Atomic rename
    5. Cleanup on failure
    """
    # Create backup
    if path.exists():
        self._create_backup(path)

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
            os.fsync(f.fileno())

        # Atomic rename
        os.replace(temp_path, path)
    except Exception:
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        raise
```

### Phase 3.3: File Locking (20 min)

**Lock Context Manager:**
```python
@contextmanager
def _file_lock(self, path: Path):
    """
    File locking for concurrent access protection.

    Uses fcntl for Unix systems.
    Creates .lock file alongside target file.
    """
    lock_path = path.with_suffix(path.suffix + '.lock')
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    with open(lock_path, 'w') as lock_file:
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            yield
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
```

### Phase 3.4: Load Operations with Validation (30 min)

**Load Mappings:**
```python
def load_mappings(self) -> Dict[str, Dict[str, str]]:
    """
    Load mappings from JSON, handle missing/corrupt files.

    Returns empty dict if file missing.
    Attempts backup restore if corrupted.
    """
    path = self.state_dir / "external_id_mapping.json"

    if not path.exists():
        return {}

    with self._file_lock(path):
        try:
            with open(path, 'r') as f:
                data = json.load(f)

            if not self._validate_mapping_data(data):
                raise ValueError("Invalid mapping data structure")

            return data.get('mappings', {})

        except (json.JSONDecodeError, ValueError) as e:
            # Try backup
            backup_path = path.with_suffix(path.suffix + '.bak')
            if backup_path.exists():
                self._restore_from_backup(path)
                return self.load_mappings()  # Recursive retry

            # No backup, return empty
            return {}
```

**Load Counters:**
```python
def load_counters(self) -> Dict:
    """
    Load counters from JSON, handle missing/corrupt files.

    Returns default structure if file missing.
    """
    path = self.state_dir / "external_id_counters.json"

    if not path.exists():
        return self._default_counter_structure()

    with self._file_lock(path):
        try:
            with open(path, 'r') as f:
                data = json.load(f)

            if not self._validate_counter_data(data):
                raise ValueError("Invalid counter data structure")

            return data.get('counters', self._default_counter_structure())

        except (json.JSONDecodeError, ValueError):
            backup_path = path.with_suffix(path.suffix + '.bak')
            if backup_path.exists():
                self._restore_from_backup(path)
                return self.load_counters()

            return self._default_counter_structure()
```

### Phase 3.5: Save Operations (25 min)

**Save Mappings:**
```python
def save_mappings(self, mappings: Dict[str, Dict[str, str]]) -> None:
    """
    Save mappings to JSON with atomic write.

    Args:
        mappings: Dictionary of internal_id -> {tool: external_id}
    """
    path = self.state_dir / "external_id_mapping.json"
    path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "version": "1.0",
        "updated": datetime.now(timezone.utc).isoformat(),
        "mappings": mappings
    }

    with self._file_lock(path):
        self._atomic_write(path, data)
```

**Save Counters:**
```python
def save_counters(self, counters: Dict) -> None:
    """
    Save counters to JSON with atomic write.

    Args:
        counters: Dictionary of tool -> counter value
    """
    path = self.state_dir / "external_id_counters.json"
    path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "version": "1.0",
        "updated": datetime.now(timezone.utc).isoformat(),
        "counters": counters
    }

    with self._file_lock(path):
        self._atomic_write(path, data)
```

### Phase 3.6: Integration with ExternalIDMapper (30 min)

**Modify ExternalIDMapper to use persistence:**
```python
class ExternalIDMapper:
    def __init__(self, persistence: ExternalIDPersistence = None):
        self.persistence = persistence or ExternalIDPersistence()

        # Load from disk
        self.mappings = self.persistence.load_mappings()
        self.counters = self.persistence.load_counters()

        self._counter_lock = threading.Lock()

    def map_to_external(self, internal_id, tool, project_key="PROJ"):
        # ... existing logic ...

        # After creating mapping, persist
        self.persistence.save_mappings(self.mappings)

        return external_id

    def increment_counter(self, tool, key=None):
        with self._counter_lock:
            # ... existing logic ...

            # After incrementing, persist
            self.persistence.save_counters(self.counters)

            return counter_value
```

---

## 4. Testing Strategy

### Phase 4.1: Unit Tests (90 min)
**File:** `tests/lib/test_external_id_persistence.py`

**Test Categories:**

**Atomic Write Tests (6 tests):**
- Test successful atomic write
- Test write creates backup
- Test write failure cleanup
- Test fsync called
- Test atomic rename
- Test directory auto-creation

**File Locking Tests (4 tests):**
- Test lock acquisition
- Test lock release
- Test concurrent access blocked
- Test lock timeout behavior

**Load Operations Tests (8 tests):**
- Test load existing mappings
- Test load missing file returns empty
- Test load corrupted file uses backup
- Test load corrupted file no backup
- Test load existing counters
- Test load missing counters returns defaults
- Test validation catches invalid data
- Test recursive retry after backup restore

**Save Operations Tests (6 tests):**
- Test save mappings creates file
- Test save updates timestamp
- Test save preserves existing data
- Test save counters
- Test save with locking
- Test save creates parent directories

**Backup/Restore Tests (5 tests):**
- Test backup creation
- Test backup preservation on write failure
- Test restore from backup
- Test restore when no backup exists
- Test backup overwrite behavior

**Integration Tests (5 tests):**
- Test round-trip: save → load → verify
- Test persistence with ExternalIDMapper
- Test counter increment persists
- Test mapping creation persists
- Test concurrent mapper instances share state

**Concurrent Access Tests (3 tests):**
- Test 10 simultaneous writes (no corruption)
- Test concurrent read/write operations
- Test lock prevents race conditions

### Phase 4.2: Test Coverage Target
- Goal: ≥90%
- Critical paths: 100% (atomic write, locking)
- Error handling: 100% (corruption, missing files)

---

## 5. Quality Gates

### Phase 5.1: Architectural Review
- SOLID compliance
- DRY principle (no duplication with TASK-049)
- YAGNI (no speculative features)
- Integration design

### Phase 5.2: Code Review
- Error handling comprehensive
- File operations safe
- Lock management correct
- Documentation complete

### Phase 5.3: Test Quality
- Coverage ≥90%
- Concurrent tests validate locking
- Corruption scenarios tested
- Integration with TASK-049 validated

---

## 6. Integration Points

### Current Dependencies
- ✅ TASK-049: ExternalIDMapper (completed)

### Integration Changes Needed
**File:** `installer/core/lib/external_id_mapper.py`
- Add `persistence` parameter to `__init__()`
- Call `persistence.save_mappings()` after mapping creation
- Call `persistence.save_counters()` after counter increment
- Load initial state in `__init__()`

### Singleton Pattern Update
```python
def get_mapper(persistence: ExternalIDPersistence = None) -> ExternalIDMapper:
    """Get singleton mapper with persistence."""
    global _mapper_instance

    if _mapper_instance is None:
        with _instance_lock:
            if _mapper_instance is None:
                _mapper_instance = ExternalIDMapper(persistence)

    return _mapper_instance
```

---

## 7. Implementation Timeline

| Phase | Task | Duration | Status |
|-------|------|----------|--------|
| 3.1 | Core persistence module | 45 min | Pending |
| 3.2 | Atomic write | 30 min | Pending |
| 3.3 | File locking | 20 min | Pending |
| 3.4 | Load operations | 30 min | Pending |
| 3.5 | Save operations | 25 min | Pending |
| 3.6 | ExternalIDMapper integration | 30 min | Pending |
| 4.1 | Unit tests | 90 min | Pending |
| 4.2 | Test execution | 10 min | Pending |
| 5.1 | Architectural review | 15 min | Pending |
| 5.2 | Code review | 15 min | Pending |

**Total Estimated Time:** 5 hours

---

## 8. Success Criteria

- [ ] Mappings persist across process restarts
- [ ] Counters persist across process restarts
- [ ] Atomic writes prevent corruption
- [ ] File locking prevents race conditions
- [ ] Backup/restore handles corruption
- [ ] Test coverage ≥90%
- [ ] All tests pass
- [ ] Integration with TASK-049 seamless
- [ ] No performance degradation

---

## 9. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| File corruption | High | Atomic writes + backups |
| Concurrent access | High | File locking with fcntl |
| Disk full | Medium | Catch IOError, clear messaging |
| Permission errors | Medium | Validate directory writable |
| Lock contention | Low | Fast operations, brief locks |

---

## 10. Notes

- File locking uses `fcntl` (Unix/Linux/macOS standard)
- Atomic rename is OS-level atomic operation
- Backup strategy: always keep last known good state
- Performance: persist on every change (acceptable for counter frequency)
- Future: Consider write-behind caching if performance issue

---

**Plan Status:** Ready for Phase 2.5 Architectural Review
