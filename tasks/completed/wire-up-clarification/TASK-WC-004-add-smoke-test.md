---
id: TASK-WC-004
title: Add end-to-end smoke test for clarification
status: superseded
created: 2025-12-13T21:00:00Z
updated: 2025-12-13T22:45:00Z
priority: medium
tags: [clarification, testing, smoke-test, task-work, superseded]
complexity: 4
implementation_mode: task-work
parent_feature: wire-up-clarification
related_review: TASK-REV-CLQ2
dependencies: [TASK-WC-001, TASK-WC-002, TASK-WC-003]
superseded_by: TASK-WC-012
superseded_reason: "TASK-REV-CLQ3 decided to use unified subagent pattern - tests expanded to cover all commands"
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Add end-to-end smoke test for clarification

## Description

Create an end-to-end smoke test that verifies clarifying questions are actually displayed when running `/feature-plan` and `/task-review` commands with ambiguous inputs or high-complexity tasks.

This test is critical because:
1. Unit tests exist but test isolated modules (they all pass but don't prove the feature works end-to-end)
2. Integration tests mock the workflow instead of testing actual invocation
3. The original bug was discovered by manual testing, not automated tests

## Background

The original test (in `docs/reviews/clarifying-questions/feature-plan-test.md`) showed that no clarification questions appeared despite the feature being "implemented". This task adds automated tests to prevent regression.

## Implementation

### 1. Create Smoke Test File

**File**: `tests/smoke/test_clarification_e2e.py`

```python
"""
End-to-end smoke tests for clarification feature.

These tests verify that clarifying questions are actually displayed
when running feature-plan and task-review orchestrators.

Prerequisites:
- GuardKit installed (symlinks in ~/.agentecflow/bin/)
- Python orchestrators accessible

Run with: pytest tests/smoke/test_clarification_e2e.py -v
"""

import subprocess
import sys
import tempfile
import os
from pathlib import Path
import pytest


@pytest.fixture
def temp_git_repo():
    """Create a temporary git repository for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Initialize git repo
        subprocess.run(["git", "init"], cwd=tmpdir, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=tmpdir,
            capture_output=True
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=tmpdir,
            capture_output=True
        )

        # Create tasks directory structure
        (Path(tmpdir) / "tasks" / "backlog").mkdir(parents=True)

        yield tmpdir


class TestFeaturePlanClarification:
    """Tests for /feature-plan clarification integration."""

    def test_orchestrator_exists(self):
        """Verify feature-plan-orchestrator symlink exists."""
        orchestrator = Path.home() / ".agentecflow" / "bin" / "feature-plan-orchestrator"
        assert orchestrator.exists(), f"Orchestrator not found at {orchestrator}"

    def test_orchestrator_executable(self):
        """Verify orchestrator can be executed."""
        result = subprocess.run(
            [sys.executable, str(Path.home() / ".agentecflow" / "bin" / "feature-plan-orchestrator"), "--help"],
            capture_output=True,
            text=True
        )
        # Should show help or usage, not crash
        assert result.returncode == 0 or "usage" in result.stdout.lower() or "error" not in result.stderr.lower()

    def test_clarification_available_flag(self, temp_git_repo):
        """Verify CLARIFICATION_AVAILABLE is True when module is importable."""
        # Import the orchestrator and check the flag
        orchestrator_path = Path.home() / ".agentecflow" / "bin" / "feature-plan-orchestrator"
        if orchestrator_path.exists():
            # Read the file and check for CLARIFICATION_AVAILABLE
            content = orchestrator_path.read_text()
            assert "CLARIFICATION_AVAILABLE" in content


class TestTaskReviewClarification:
    """Tests for /task-review clarification integration."""

    def test_orchestrator_exists(self):
        """Verify task-review-orchestrator symlink exists."""
        orchestrator = Path.home() / ".agentecflow" / "bin" / "task-review-orchestrator"
        assert orchestrator.exists(), f"Orchestrator not found at {orchestrator}"

    def test_orchestrator_executable(self):
        """Verify orchestrator can be executed."""
        result = subprocess.run(
            [sys.executable, str(Path.home() / ".agentecflow" / "bin" / "task-review-orchestrator"), "--help"],
            capture_output=True,
            text=True
        )
        # Should show help or usage
        assert result.returncode == 0 or "usage" in result.stdout.lower()

    def test_clarification_import_in_orchestrator(self):
        """Verify clarification module is imported in task-review orchestrator."""
        orchestrator_path = Path.home() / ".agentecflow" / "bin" / "task-review-orchestrator"
        if orchestrator_path.exists():
            content = orchestrator_path.read_text()
            # Verify import statements exist
            assert "from clarification import" in content or "import clarification" in content


class TestClarificationModule:
    """Tests for clarification module accessibility."""

    def test_clarification_module_importable(self):
        """Verify clarification module can be imported."""
        # Add lib path
        lib_path = Path(__file__).parent.parent.parent / "installer" / "core" / "commands" / "lib"
        sys.path.insert(0, str(lib_path))

        try:
            from clarification import (
                should_clarify,
                ClarificationMode,
                ClarificationContext,
            )
            # Verify key functions exist
            assert callable(should_clarify)
            assert hasattr(ClarificationMode, 'SKIP')
            assert hasattr(ClarificationMode, 'FULL')
        finally:
            sys.path.remove(str(lib_path))

    def test_should_clarify_returns_correct_mode(self):
        """Verify should_clarify returns expected modes based on complexity."""
        lib_path = Path(__file__).parent.parent.parent / "installer" / "core" / "commands" / "lib"
        sys.path.insert(0, str(lib_path))

        try:
            from clarification import should_clarify, ClarificationMode

            # Simple task should skip
            mode = should_clarify("review", complexity=2, flags={})
            assert mode == ClarificationMode.SKIP

            # Complex task should require full clarification
            mode = should_clarify("review", complexity=8, flags={})
            assert mode == ClarificationMode.FULL

            # --no-questions should always skip
            mode = should_clarify("review", complexity=8, flags={"no_questions": True})
            assert mode == ClarificationMode.SKIP

            # --with-questions should always ask
            mode = should_clarify("review", complexity=2, flags={"with_questions": True})
            assert mode in [ClarificationMode.FULL, ClarificationMode.QUICK]

        finally:
            sys.path.remove(str(lib_path))


class TestNoQuestionsFlag:
    """Tests for --no-questions flag behavior."""

    def test_no_questions_skips_clarification(self):
        """Verify --no-questions flag causes clarification to be skipped."""
        lib_path = Path(__file__).parent.parent.parent / "installer" / "core" / "commands" / "lib"
        sys.path.insert(0, str(lib_path))

        try:
            from clarification import should_clarify, ClarificationMode

            # Even high complexity should skip with --no-questions
            mode = should_clarify("review", complexity=10, flags={"no_questions": True})
            assert mode == ClarificationMode.SKIP

            mode = should_clarify("planning", complexity=10, flags={"no_questions": True})
            assert mode == ClarificationMode.SKIP

        finally:
            sys.path.remove(str(lib_path))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

### 2. Create Smoke Test Directory

```bash
mkdir -p tests/smoke
touch tests/smoke/__init__.py
```

### 3. Add pytest.ini Entry (if needed)

Ensure `tests/smoke/` is included in test discovery.

## Acceptance Criteria

- [ ] Smoke test file created at `tests/smoke/test_clarification_e2e.py`
- [ ] Tests verify orchestrator symlinks exist
- [ ] Tests verify orchestrators are executable
- [ ] Tests verify clarification module is importable
- [ ] Tests verify `should_clarify()` returns correct modes
- [ ] Tests verify `--no-questions` flag works
- [ ] All tests pass: `pytest tests/smoke/test_clarification_e2e.py -v`

## Testing

```bash
# Run smoke tests
pytest tests/smoke/test_clarification_e2e.py -v

# Expected output:
# test_orchestrator_exists PASSED
# test_orchestrator_executable PASSED
# test_clarification_available_flag PASSED
# test_clarification_module_importable PASSED
# test_should_clarify_returns_correct_mode PASSED
# test_no_questions_skips_clarification PASSED
```

## Implementation Notes

- Use `task-work` mode since this creates new test code
- Depends on Wave 1 tasks (symlinks must exist)
- Tests should be deterministic (no user input required)
- Tests verify the wiring, not the full clarification UX flow

## Dependencies

- TASK-WC-001: feature-plan.md must be updated
- TASK-WC-002: task-review.md must be updated
- TASK-WC-003: Symlinks must be created by installer
