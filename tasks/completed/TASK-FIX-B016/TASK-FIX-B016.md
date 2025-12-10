---
id: TASK-FIX-B016
title: Fix settings deserialization missing to_dict() method in checkpoint-resume
status: completed
created: 2025-12-09T05:00:00Z
updated: 2025-12-09T06:15:00Z
completed: 2025-12-09T06:15:00Z
priority: critical
task_type: implementation
tags: [template-create, deserialization, checkpoint-resume, bug-fix]
complexity: 3
estimated_hours: 2-3
actual_hours: 1
related_tasks: [TASK-REV-B016, TASK-FIX-P5RT, TASK-REV-D4A8]
parent_review: TASK-REV-B016
completed_location: tasks/completed/TASK-FIX-B016/
organized_files: [TASK-FIX-B016.md]
---

# Fix: Settings Deserialization Missing to_dict() Method

## Context

From review TASK-REV-B016: The `/template-create` command fails at Phase 9 when resuming from a checkpoint because the `_deserialize_settings()` method creates a bare dynamic class without the `to_dict()` method required for JSON serialization.

## Root Cause

**Location**: [template_create_orchestrator.py:2300-2305](installer/core/commands/lib/template_create_orchestrator.py#L2300-L2305)

```python
def _deserialize_settings(self, data: Optional[dict]) -> Any:
    """Deserialize dict back to settings."""
    if data is None:
        return None
    # Return as dict for now, actual class reconstruction happens in phases
    return type('Settings', (), data)()  # ← BUG: No to_dict() method!
```

This causes Phase 9 to fail when calling:
```python
settings_gen.save(settings, settings_path)  # Calls settings.to_dict()
```

## Error Trace

```
Phase 9: Package Assembly
  ✓ manifest.json (2.0 B)
  ❌ Package assembly failed: 'Settings' object has no attribute 'to_dict'
```

## Implementation Summary

### Changes Made

**File Modified**: [installer/core/commands/lib/template_create_orchestrator.py](installer/core/commands/lib/template_create_orchestrator.py)

#### 1. _deserialize_manifest() (lines 2276-2287)
- Added explicit `to_dict()` method to manifest object
- Enables checkpoint-resume serialization

#### 2. _deserialize_settings() (lines 2306-2322)
- Added Pydantic TemplateSettings model validation
- Falls back to dynamic object with `to_dict()` method
- Added warning logging for fallback scenarios

#### 3. _deserialize_templates() (lines 2358-2387)
- Added Pydantic TemplateCollection model validation
- Falls back to dynamic object with `to_dict()` method for collection and each template
- Uses proper closure semantics for lambda functions

### Tests Added

**File Modified**: [tests/unit/test_template_create_orchestrator.py](tests/unit/test_template_create_orchestrator.py)

4 new tests added:
1. `test_deserialize_settings_has_to_dict()` - Verifies settings deserialization
2. `test_deserialize_manifest_has_to_dict()` - Verifies manifest deserialization
3. `test_deserialize_templates_has_to_dict()` - Verifies templates deserialization
4. `test_settings_round_trip_serialization()` - Verifies serialize → deserialize → to_dict() cycle

## Acceptance Criteria

- [x] `_deserialize_settings()` returns object with working `to_dict()` method
- [x] Phase 9 succeeds after checkpoint-resume (verified via test)
- [x] Unit test added for deserialization round-trip
- [x] `_deserialize_manifest()` fixed (same pattern)
- [x] `_deserialize_templates()` fixed (same pattern)

## Test Results

```
tests/unit/test_template_create_orchestrator.py::test_deserialize_settings_has_to_dict PASSED
tests/unit/test_template_create_orchestrator.py::test_deserialize_manifest_has_to_dict PASSED
tests/unit/test_template_create_orchestrator.py::test_deserialize_templates_has_to_dict PASSED
tests/unit/test_template_create_orchestrator.py::test_settings_round_trip_serialization PASSED

4 tests passed, 0 failed
```

## Quality Gates

| Gate | Status | Notes |
|------|--------|-------|
| Compilation | ✅ PASS | No syntax errors |
| Tests | ✅ PASS | 4/4 new tests passing |
| Architectural Review | ✅ PASS | 88/100 score |
| Code Review | ✅ PASS | 85/100 score |

## Verification

```bash
# Run unit tests
python3 -m pytest tests/unit/test_template_create_orchestrator.py -v -k "deserialize"

# All 4 deserialization tests pass
```

---

*Created from TASK-REV-B016 review findings*
*Priority: Critical - Blocks /template-create completion*
*Implementation completed: 2025-12-09*
*Task completed: 2025-12-09*
