---
id: TASK-CLQ-FIX-003
title: "Update integration tests to test real orchestrator paths"
status: completed
created: 2025-12-13T16:35:00Z
updated: 2025-12-13T20:30:00Z
completed: 2025-12-13T20:30:00Z
priority: medium
tags: [clarifying-questions, testing, integration-tests]
complexity: 4
parent_review: TASK-REV-0614
implementation_mode: task-work
dependencies: [TASK-CLQ-FIX-001]
completion_summary: |
  Updated all 3 integration test files to properly test real orchestrators:
  - test_task_review_clarification.py: 13 tests passing
  - test_feature_plan_clarification.py: 17 tests passing
  - test_task_work_clarification.py: 26 tests passing
  Total: 56/56 tests passing
---

# Task: Update integration tests to test real orchestrator

## Description

The current integration tests mock the workflow instead of testing the actual orchestrators. This means tests pass even though the real code path doesn't work.

## Problem

Current test pattern (problematic):
```python
def execute_feature_plan(feature_desc, flags=None):
    """Mock function representing feature-plan workflow."""
    # This is a mock, not the real orchestrator!
    if not flags.get("no_questions", False):
        questions = generate_review_questions(feature_desc, mode='decision')
        # ... mock implementation
```

This tests the clarification module in isolation but doesn't verify the orchestrator calls it.

## Solution

Update tests to call the real orchestrators with appropriate mocking only for I/O:

```python
import pytest
from unittest.mock import patch

from lib.task_review_orchestrator import execute_task_review
from lib.feature_plan_orchestrator import execute_feature_plan

class TestTaskReviewClarification:
    """Test clarification integration with real orchestrator."""

    @pytest.fixture
    def sample_task(self, tmp_path):
        """Create a sample task file for testing."""
        task_content = '''---
id: TASK-TEST-001
title: Test task
status: backlog
complexity: 6
---

# Test Task
'''
        task_file = tmp_path / "tasks" / "backlog" / "TASK-TEST-001.md"
        task_file.parent.mkdir(parents=True, exist_ok=True)
        task_file.write_text(task_content)
        return "TASK-TEST-001", tmp_path

    @patch('builtins.input', return_value='')  # Auto-accept defaults
    def test_clarification_triggers_for_decision_mode(self, mock_input, sample_task):
        """Clarification should trigger for decision mode with complexity >= 4."""
        task_id, base_dir = sample_task

        result = execute_task_review(
            task_id=task_id,
            mode="decision",
            depth="standard",
            base_dir=base_dir
        )

        # Verify clarification was called
        assert result['status'] == 'success'
        # Check that task frontmatter has clarification section
        # (This is the key verification - proves integration works)

    def test_no_questions_flag_skips_clarification(self, sample_task):
        """--no-questions should skip clarification entirely."""
        task_id, base_dir = sample_task

        result = execute_task_review(
            task_id=task_id,
            mode="decision",
            depth="standard",
            no_questions=True,
            base_dir=base_dir
        )

        assert result['status'] == 'success'
        # Verify no clarification in frontmatter


class TestFeaturePlanClarification:
    """Test clarification through feature-plan orchestrator."""

    @patch('builtins.input', return_value='')
    def test_feature_plan_triggers_context_a(self, mock_input, tmp_path):
        """Feature-plan should trigger Context A (review scope) clarification."""
        result = execute_feature_plan(
            feature_description="add user authentication",
            flags={},
            base_dir=tmp_path
        )

        assert result['status'] == 'success'
        assert result['review_task'] is not None

    def test_feature_plan_no_questions(self, tmp_path):
        """--no-questions should skip all clarification in feature-plan."""
        result = execute_feature_plan(
            feature_description="add dark mode",
            flags={'no_questions': True},
            base_dir=tmp_path
        )

        assert result['status'] == 'success'
```

## Files to Modify

1. `tests/integration/lib/clarification/test_task_review_clarification.py`
2. `tests/integration/lib/clarification/test_feature_plan_clarification.py`
3. `tests/integration/lib/clarification/test_task_work_clarification.py`

## Acceptance Criteria

- [ ] Tests import and call real orchestrators
- [ ] Only I/O (input, file system) is mocked
- [ ] Tests verify clarification appears in task frontmatter
- [ ] Tests cover:
  - Decision mode triggers clarification
  - Low complexity skips clarification
  - `--no-questions` flag works
  - `--with-questions` forces clarification
- [ ] All tests pass with new orchestrator code

## Dependencies

- TASK-CLQ-FIX-001 (orchestrator must be integrated first)

## Estimated Effort

1-2 hours
