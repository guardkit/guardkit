---
id: TASK-CLQ-FIX-004
title: "Add end-to-end smoke test for clarification flow"
status: backlog
created: 2025-12-13T16:35:00Z
updated: 2025-12-13T16:35:00Z
priority: medium
tags: [clarifying-questions, testing, smoke-test, e2e]
complexity: 3
parent_review: TASK-REV-0614
implementation_mode: direct
dependencies: [TASK-CLQ-FIX-001]
---

# Task: Add end-to-end smoke test for clarification

## Description

Create a simple end-to-end test that verifies clarification works in a real execution context. This serves as a regression guard to catch future integration breaks.

## Test Script

Create `tests/smoke/test_clarification_smoke.py`:

```python
#!/usr/bin/env python3
"""
Smoke test for clarification feature integration.

This test verifies that clarification questions are actually triggered
in a real execution context, not just in isolated unit tests.

Run with: python -m pytest tests/smoke/test_clarification_smoke.py -v
"""

import os
import sys
import tempfile
import subprocess
from pathlib import Path

import pytest


class TestClarificationSmoke:
    """End-to-end smoke tests for clarification."""

    @pytest.fixture
    def test_environment(self, tmp_path):
        """Set up a minimal test environment."""
        # Create task directory structure
        (tmp_path / "tasks" / "backlog").mkdir(parents=True)

        # Create a test task
        task_content = '''---
id: TASK-SMOKE-001
title: Smoke test task
status: backlog
complexity: 6
task_type: review
---

# Smoke Test Task

Test task for clarification smoke test.
'''
        task_file = tmp_path / "tasks" / "backlog" / "TASK-SMOKE-001.md"
        task_file.write_text(task_content)

        return tmp_path

    def test_clarification_appears_in_output(self, test_environment):
        """Verify clarification questions appear in task-review output."""
        # Run task-review orchestrator
        script = Path(__file__).parent.parent.parent / "installer" / "core" / "commands" / "lib" / "task_review_orchestrator.py"

        result = subprocess.run(
            [
                sys.executable,
                str(script),
                "TASK-SMOKE-001",
                "--mode=decision",
                "--depth=standard"
            ],
            capture_output=True,
            text=True,
            cwd=str(test_environment),
            env={**os.environ, "GUARDKIT_TEST_MODE": "1"},
            input="\n"  # Press enter to accept defaults
        )

        # Check for clarification indicators in output
        output = result.stdout + result.stderr

        # These strings should appear if clarification is working
        clarification_indicators = [
            "CLARIFICATION",  # Header
            "Phase 1.5",      # Phase indicator
            "question",       # Question prompt
        ]

        found_any = any(
            indicator.lower() in output.lower()
            for indicator in clarification_indicators
        )

        assert found_any, (
            f"No clarification indicators found in output.\n"
            f"Output was:\n{output}\n\n"
            f"This suggests clarification is not integrated with the orchestrator."
        )

    def test_clarification_persisted_to_frontmatter(self, test_environment):
        """Verify clarification decisions are saved to task frontmatter."""
        task_file = test_environment / "tasks" / "backlog" / "TASK-SMOKE-001.md"

        # Run task-review
        script = Path(__file__).parent.parent.parent / "installer" / "core" / "commands" / "lib" / "task_review_orchestrator.py"

        subprocess.run(
            [
                sys.executable,
                str(script),
                "TASK-SMOKE-001",
                "--mode=decision"
            ],
            cwd=str(test_environment),
            input="\n",
            capture_output=True,
            text=True
        )

        # Check task was moved to in_progress and has clarification
        moved_file = test_environment / "tasks" / "in_progress" / "TASK-SMOKE-001.md"
        if moved_file.exists():
            content = moved_file.read_text()
        elif task_file.exists():
            content = task_file.read_text()
        else:
            pytest.fail("Task file not found after review")

        # Clarification should be in frontmatter
        assert "clarification:" in content or "CLARIFICATION" in content, (
            "Clarification not found in task frontmatter.\n"
            "This suggests persist_to_frontmatter() is not being called."
        )

    def test_no_questions_skips_clarification(self, test_environment):
        """Verify --no-questions flag skips clarification."""
        script = Path(__file__).parent.parent.parent / "installer" / "core" / "commands" / "lib" / "task_review_orchestrator.py"

        result = subprocess.run(
            [
                sys.executable,
                str(script),
                "TASK-SMOKE-001",
                "--mode=decision",
                "--no-questions"
            ],
            capture_output=True,
            text=True,
            cwd=str(test_environment)
        )

        output = result.stdout + result.stderr

        # Should NOT see clarification prompts
        assert "CLARIFICATION QUESTIONS" not in output, (
            "Clarification appeared despite --no-questions flag"
        )

        # Should see skip indicator
        assert "skip" in output.lower() or "Phase 2:" in output, (
            "Expected skip message or Phase 2 to start directly"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

## Acceptance Criteria

- [ ] Test verifies clarification appears in output
- [ ] Test verifies persistence to frontmatter
- [ ] Test verifies --no-questions flag works
- [ ] Tests run in CI/CD pipeline
- [ ] Tests are fast (< 30 seconds total)

## Why This Matters

This smoke test would have caught the regression:
- Unit tests passed (clarification module works)
- Integration tests passed (mock worked)
- But real execution didn't work (no orchestrator integration)

The smoke test runs the actual orchestrator CLI and verifies output.

## Dependencies

- TASK-CLQ-FIX-001 (orchestrator must be integrated first)

## Estimated Effort

1 hour
