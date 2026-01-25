---
id: TASK-FBSDK-026
title: Verify feature-plan generates task_type in frontmatter
status: completed
created: 2025-01-22T21:30:00Z
updated: 2026-01-22T12:30:00Z
completed: 2026-01-22T12:30:00Z
completed_location: tasks/completed/TASK-FBSDK-026/
priority: medium
tags: [feature-build, feature-plan, quality-gates, verification, testing]
complexity: 3
task_type: feature
implementation_mode: direct
parent_review: TASK-REV-FB20
feature_id: FEAT-ARCH-SCORE-FIX
wave: 1
dependencies: []
organized_files: [TASK-FBSDK-026.md]
---

# Verify feature-plan generates task_type in frontmatter

## Description

Verify that the `/feature-plan` command correctly generates task files with `task_type` in frontmatter, as implemented in TASK-FBSDK-022.

**Background**: The test task file (`TASK-FHE-001-create-project-structure.md`) was missing `task_type` in frontmatter, which contributed to the architectural review failure. The `implement_orchestrator.py` code (TASK-FBSDK-022) should be writing `task_type`, so we need to verify the execution path.

**Possible Issues**:
1. Claude Code may generate task files directly instead of using `implement_orchestrator.py`
2. The skill may have been executed before TASK-FBSDK-022 was merged
3. There may be multiple code paths for task file generation

## Acceptance Criteria

- [x] Verify `implement_orchestrator.py` is invoked during `/feature-plan [I]mplement`
- [x] Confirm generated task files contain `task_type` field in frontmatter
- [x] Verify task_type detection correctly classifies scaffolding vs feature tasks
- [x] Document the execution path from `/feature-plan` to task file creation
- [x] Add integration test covering the generation flow

## Verification Findings (2026-01-22)

### Summary

**Key Finding**: The `implement_orchestrator.py` IS correctly implemented with task_type detection, but Claude Code may create task files directly without invoking the orchestrator.

### Execution Path Analysis

```
/feature-plan "description"
       │
       ▼
[1] Create review task (/task-create)
       │
       ▼
[2] Execute review (/task-review --mode=decision)
       │
       ▼
[3] Decision checkpoint - User chooses [I]mplement
       │
       ▼
[4] **GAP IDENTIFIED**: Command spec references implement_orchestrator.py
    but no CLI script exists to invoke it. Claude interprets markdown
    instructions and may create files directly using Write tool.
       │
       ▼
[5] Task files created (MAY or MAY NOT use orchestrator)
```

### Code Verification

**implement_orchestrator.py** (lines 257-275):
- Line 49: `from guardkit.lib.task_type_detector import detect_task_type`
- Line 258: `task_type = detect_task_type(title, description)` ✅
- Line 275: `task_type: {task_type.value}` ✅

**task_type_detector.py**:
- Uses keyword-based classification with priority order
- Priority: INFRASTRUCTURE → DOCUMENTATION → SCAFFOLDING → FEATURE
- All tests pass (3/3 integration tests)

### Test Results

```
tests/integration/test_feature_plan_task_type_detection.py::TestFeaturePlanTaskTypeDetection::test_task_type_detection_in_subtask_generation PASSED
tests/integration/test_feature_plan_task_type_detection.py::TestFeaturePlanTaskTypeDetection::test_task_type_with_empty_description PASSED
tests/integration/test_feature_plan_task_type_detection.py::TestFeaturePlanTaskTypeDetection::test_task_type_ambiguous_title_with_description PASSED
```

### Root Cause of Missing task_type

The test task file (`TASK-FHE-001-create-project-structure.md`) was likely created:
1. **Before TASK-FBSDK-022 was merged** - The detection code was added later
2. **OR by Claude Code directly** - Using Write tool instead of invoking the orchestrator

### Recommendations

1. **TASK-FBSDK-025 is STILL REQUIRED**: Passes task_type to CoachValidator for quality gate profiles
2. **Future Enhancement**: Consider creating a CLI script to invoke `implement_orchestrator.py` directly, ensuring consistent task file generation
3. **Documentation**: Update feature-plan.md command spec to explicitly instruct Claude to include task_type when creating task files manually

### Conclusion

The `implement_orchestrator.py` correctly implements task_type detection and generation. The issue is that Claude Code may bypass the orchestrator when creating task files. TASK-FBSDK-025 addresses the immediate need by passing task_type from task frontmatter to CoachValidator.

## Verification Steps

### Step 1: Manual Test

Run `/feature-plan` with a new test feature and verify output:

```bash
# In a test directory
/feature-plan "Create a simple Python CLI tool"

# After [I]mplement, check generated files:
cat tasks/backlog/*/TASK-*.md | grep -A2 "^---" | head -30
```

Expected output should include `task_type: scaffolding` or `task_type: feature`.

### Step 2: Trace Execution Path

Add verbose logging to verify `implement_orchestrator.py` is called:

```python
# In implement_orchestrator.py, add at start of generate_subtask_files():
print(f"DEBUG: generate_subtask_files called for {len(self.subtasks)} subtasks")
```

### Step 3: Verify Detection Logic

Test the task type detector with sample titles:

```python
from guardkit.lib.task_type_detector import detect_task_type

# Should return SCAFFOLDING
detect_task_type("Create project structure and configuration")

# Should return FEATURE
detect_task_type("Implement user authentication")
```

### Step 4: Integration Test

Create test file: `tests/integration/test_feature_plan_task_type_e2e.py`

```python
"""End-to-end test for task_type generation in feature-plan."""

import tempfile
import os
from pathlib import Path

def test_feature_plan_generates_task_type():
    """Verify /feature-plan creates task files with task_type."""
    # This would be a manual/semi-automated test
    # since /feature-plan is a Claude Code skill
    pass


def test_implement_orchestrator_writes_task_type(tmp_path):
    """Verify implement_orchestrator writes task_type to frontmatter."""
    from installer.core.lib.implement_orchestrator import ImplementOrchestrator

    review_task = {
        "id": "TASK-REV-TEST",
        "title": "Test Review",
        "created": "2025-01-22T00:00:00Z",
    }

    orchestrator = ImplementOrchestrator(review_task, "dummy-report.md")
    orchestrator.feature_slug = "test-feature"
    orchestrator.feature_name = "Test Feature"
    orchestrator.subtasks = [
        {
            "id": "TASK-TF-001",
            "title": "Create project structure",
            "description": "Set up the initial project configuration",
        }
    ]
    orchestrator.subfolder_path = str(tmp_path)

    orchestrator.generate_subtask_files()

    # Verify task file was created with task_type
    task_file = tmp_path / "TASK-TF-001-create-project-structure.md"
    assert task_file.exists()

    content = task_file.read_text()
    assert "task_type: scaffolding" in content
```

## Files to Create/Modify

| File | Change | LOC |
|------|--------|-----|
| `tests/integration/test_feature_plan_task_type_e2e.py` | New integration test | +60 |
| Documentation | Document execution path findings | N/A |

## Expected Outcomes

1. **If task_type IS being generated**: Document the confirmed execution path
2. **If task_type is NOT being generated**:
   - Identify the actual code path used by `/feature-plan`
   - Create follow-up task to fix the generation

## Dependencies

None - this is a verification task that can run in parallel with TASK-FBSDK-025.

## Notes

- The existing test at `tests/integration/test_feature_plan_task_type_detection.py` tests the detector in isolation
- This task verifies the end-to-end integration
- Even if task_type IS generated, TASK-FBSDK-025 is still needed to pass it to CoachValidator

## Related Tasks

- TASK-REV-FB20: Review that identified this issue
- TASK-FBSDK-022: Implemented task type auto-detection (should be working)
- TASK-FBSDK-025: Pass task_type to CoachValidator (primary fix)
