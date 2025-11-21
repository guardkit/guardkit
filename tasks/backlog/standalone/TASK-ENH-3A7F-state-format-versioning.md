---
task_id: TASK-ENH-3A7F
title: Add state format versioning to checkpoint system
status: BACKLOG
priority: MEDIUM
complexity: 2
created: 2025-11-20T21:20:00Z
updated: 2025-11-20T21:20:00Z
assignee: null
tags: [enhancement, phase-8, state-management, future-proofing]
related_tasks: [TASK-PHASE-8-INCREMENTAL]
estimated_duration: 1 hour
technologies: [python, versioning]
review_source: docs/reviews/phase-8-implementation-review.md
---

# Add State Format Versioning to Checkpoint System

## Problem Statement

Checkpoint state files have no version identifier. Future format changes will break checkpoint resume functionality with no migration path for old state files.

**Review Finding** (Section 2, High Priority Issue #3):
> **Location**: Lines 1688-1694
> **Problem**: Checkpoint state has no version identifier
> **Impact**: Future format changes will break checkpoint resume, no migration path for old state files

## Current State

**Location**: `installer/global/commands/lib/template_create_orchestrator.py:1688-1694`

```python
state = {
    "checkpoint_phase": self.current_phase,
    "config": {...},
    "metadata": {...},
    # ... other fields
}
```

**Problems**:
- No `version` or `schema_version` field
- Cannot detect old vs new format
- Cannot implement format migrations
- Breaking changes require deleting all checkpoint files

## Acceptance Criteria

### 1. Version Field Added
- [ ] State dict includes `checkpoint_version` field
- [ ] Version follows semantic versioning (e.g., "1.0", "1.1", "2.0")
- [ ] Version documented in code and comments
- [ ] Version incremented when format changes

### 2. Version Validation
- [ ] Load checkpoint validates version compatibility
- [ ] Clear error if version too old
- [ ] Clear error if version too new (future compatibility)
- [ ] Graceful degradation possible

### 3. Migration Support
- [ ] Architecture supports version migrations
- [ ] Can migrate v1.0 → v1.1 automatically
- [ ] Migration failures handled gracefully
- [ ] Migration logged for debugging

### 4. Documentation
- [ ] Version changelog documented in code
- [ ] Migration guide for developers
- [ ] User-facing error messages helpful

## Technical Details

### Files to Modify

**1. `installer/global/commands/lib/template_create_orchestrator.py`**
- Lines 1688-1694: Add version to state dict
- Checkpoint load method: Add version validation
- Add migration logic (future-proofing)

### Recommended Implementation

#### Step 1: Add Version to State
```python
CHECKPOINT_VERSION = "1.0"  # Module-level constant

def _save_checkpoint(self, phase: str):
    """Save checkpoint with version information."""
    state = {
        "checkpoint_version": CHECKPOINT_VERSION,  # Add version
        "checkpoint_phase": self.current_phase,
        "config": self._serialize_config(),
        "metadata": {...},
        # ... rest of state
    }

    checkpoint_file = Path(".template-create-checkpoint.json")
    checkpoint_file.write_text(json.dumps(state, indent=2))
    logger.info(f"Checkpoint saved (version {CHECKPOINT_VERSION})")
```

#### Step 2: Validate Version on Load
```python
def _load_checkpoint(self) -> Optional[dict]:
    """Load checkpoint with version validation."""
    checkpoint_file = Path(".template-create-checkpoint.json")

    if not checkpoint_file.exists():
        return None

    try:
        state = json.loads(checkpoint_file.read_text())

        # Validate version
        state_version = state.get("checkpoint_version")

        if not state_version:
            logger.warning("Checkpoint has no version - assuming legacy format")
            return self._migrate_legacy_checkpoint(state)

        if not self._is_version_compatible(state_version):
            logger.error(f"Checkpoint version {state_version} is not compatible with {CHECKPOINT_VERSION}")
            logger.error("Please delete .template-create-checkpoint.json and restart")
            return None

        # Migrate if needed
        if state_version != CHECKPOINT_VERSION:
            state = self._migrate_checkpoint(state, state_version)

        return state

    except json.JSONDecodeError as e:
        logger.error(f"Invalid checkpoint file: {e}")
        return None
```

#### Step 3: Version Compatibility Check
```python
def _is_version_compatible(self, state_version: str) -> bool:
    """Check if checkpoint version is compatible.

    Compatible versions:
    - Same major version (1.x compatible with 1.y)
    - Can migrate from older minor versions

    Args:
        state_version: Version string from checkpoint (e.g., "1.0")

    Returns:
        bool: True if compatible, False otherwise
    """
    current_major, current_minor = map(int, CHECKPOINT_VERSION.split("."))
    try:
        state_major, state_minor = map(int, state_version.split("."))
    except (ValueError, AttributeError):
        return False

    # Same major version is compatible
    if state_major == current_major:
        return True

    # Future version (state is newer than code)
    if state_major > current_major:
        logger.warning(f"Checkpoint from newer version {state_version}")
        return False

    # Very old version (pre-1.0)
    return False
```

#### Step 4: Migration Framework
```python
def _migrate_checkpoint(self, state: dict, from_version: str) -> dict:
    """Migrate checkpoint from old version to current.

    Args:
        state: Checkpoint state dict
        from_version: Version to migrate from

    Returns:
        dict: Migrated state
    """
    logger.info(f"Migrating checkpoint from {from_version} to {CHECKPOINT_VERSION}")

    # Migration chain
    migrations = {
        "1.0": self._migrate_1_0_to_1_1,
        "1.1": self._migrate_1_1_to_1_2,
        # Add new migrations as needed
    }

    current_version = from_version
    while current_version != CHECKPOINT_VERSION:
        if current_version not in migrations:
            logger.error(f"No migration path from {current_version}")
            return None

        state = migrations[current_version](state)
        current_version = state["checkpoint_version"]

    return state

def _migrate_1_0_to_1_1(self, state: dict) -> dict:
    """Migrate checkpoint from version 1.0 to 1.1.

    Example migration (add new field):
    """
    state["checkpoint_version"] = "1.1"
    state["new_field"] = "default_value"  # Example
    logger.info("Migrated to version 1.1")
    return state

def _migrate_legacy_checkpoint(self, state: dict) -> Optional[dict]:
    """Migrate checkpoint with no version (legacy format).

    Args:
        state: Checkpoint state with no version field

    Returns:
        Optional[dict]: Migrated state, or None if migration fails
    """
    logger.info("Migrating legacy checkpoint to version 1.0")

    # Add version field
    state["checkpoint_version"] = "1.0"

    # Any other legacy format conversions
    # ...

    return state
```

### Version Changelog

```python
"""
Checkpoint Version Changelog:

v1.0 (2025-11-20):
- Initial version with checkpoint_version field
- Fields: checkpoint_phase, config, metadata, agents, templates

v1.1 (future):
- Example: Add "enhancement_strategy" field
- Example: Rename "templates" to "template_files"

v2.0 (future):
- Breaking change: Complete state structure redesign
"""
```

## Success Metrics

### Functional Tests
- [ ] New checkpoint has version field
- [ ] Loading checkpoint validates version
- [ ] Incompatible version rejected with clear error
- [ ] Future version (e.g., 2.0) rejected gracefully
- [ ] Migration from 1.0 → 1.1 works (when implemented)

### Edge Cases
- [ ] Checkpoint with no version field (legacy) handled
- [ ] Checkpoint with invalid version string (e.g., "abc") handled
- [ ] Checkpoint with missing fields after migration

### User Experience
- [ ] Error messages actionable ("delete checkpoint and restart")
- [ ] Migration logged clearly
- [ ] No silent failures

## Dependencies

**Related To**:
- TASK-PHASE-8-INCREMENTAL (main implementation)

**Enables**:
- Future state format changes without breaking existing checkpoints

## Related Review Findings

**From**: `docs/reviews/phase-8-implementation-review.md`

- **Section 2**: Code Quality Review - High Priority Issue #3
- **Lines 1688-1694**: State format versioning missing
- **Section 6.1**: Should Fix #8 (30 minutes estimate)

## Estimated Effort

**Duration**: 1 hour

**Breakdown**:
- Add version field (15 min)
- Add validation (15 min)
- Add migration framework (20 min)
- Testing (10 min)

## Test Plan

### Unit Tests

```python
def test_checkpoint_includes_version():
    """Test that saved checkpoint has version field."""
    orchestrator = TemplateCreateOrchestrator()
    orchestrator._save_checkpoint("phase_3")

    state = json.loads(Path(".template-create-checkpoint.json").read_text())
    assert "checkpoint_version" in state
    assert state["checkpoint_version"] == "1.0"

def test_load_checkpoint_with_version():
    """Test loading checkpoint with matching version."""
    # Create checkpoint with version
    checkpoint = {
        "checkpoint_version": "1.0",
        "checkpoint_phase": "phase_3",
        # ... other fields
    }
    Path(".template-create-checkpoint.json").write_text(json.dumps(checkpoint))

    orchestrator = TemplateCreateOrchestrator()
    state = orchestrator._load_checkpoint()

    assert state is not None
    assert state["checkpoint_version"] == "1.0"

def test_load_checkpoint_incompatible_version():
    """Test loading checkpoint with incompatible version."""
    checkpoint = {
        "checkpoint_version": "2.0",  # Future version
        "checkpoint_phase": "phase_3",
    }
    Path(".template-create-checkpoint.json").write_text(json.dumps(checkpoint))

    orchestrator = TemplateCreateOrchestrator()
    state = orchestrator._load_checkpoint()

    assert state is None  # Rejected
    assert "not compatible" in caplog.text

def test_load_legacy_checkpoint():
    """Test loading checkpoint with no version (legacy)."""
    checkpoint = {
        # No version field
        "checkpoint_phase": "phase_3",
        "config": {},
    }
    Path(".template-create-checkpoint.json").write_text(json.dumps(checkpoint))

    orchestrator = TemplateCreateOrchestrator()
    state = orchestrator._load_checkpoint()

    assert state is not None
    assert state["checkpoint_version"] == "1.0"  # Migrated

def test_migration_1_0_to_1_1():
    """Test migration from version 1.0 to 1.1 (when implemented)."""
    # Create 1.0 checkpoint
    checkpoint = {
        "checkpoint_version": "1.0",
        "checkpoint_phase": "phase_3",
    }
    Path(".template-create-checkpoint.json").write_text(json.dumps(checkpoint))

    # Mock current version as 1.1
    with patch("module.CHECKPOINT_VERSION", "1.1"):
        orchestrator = TemplateCreateOrchestrator()
        state = orchestrator._load_checkpoint()

    assert state is not None
    assert state["checkpoint_version"] == "1.1"
```

## Notes

- **Priority**: MEDIUM - not blocking production but good practice
- **Effort**: 30 minutes per review, but 1 hour for comprehensive solution
- **Impact**: Future-proofing, prevents breaking changes
- **Risk**: LOW - purely additive

## Future Considerations

### When to Bump Version

**Minor version (1.0 → 1.1)**:
- Add new optional field
- Add new phase
- Non-breaking changes

**Major version (1.x → 2.0)**:
- Remove fields
- Rename fields
- Change field types
- Restructure state format

### Cleanup Strategy

Consider adding checkpoint cleanup:
```python
def _cleanup_old_checkpoints(self):
    """Remove checkpoint files older than 7 days."""
    # Prevent accumulation of stale checkpoints
```

This could be a future enhancement.
