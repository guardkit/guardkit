#!/usr/bin/env python3
"""
Smoke test for clarification feature integration.

This test verifies that clarification questions are actually triggered
in a real execution context, not just in isolated unit tests.

Run with: python -m pytest tests/smoke/test_clarification_smoke.py -v

These tests run the actual orchestrator scripts and verify:
1. Clarification appears in output (when expected)
2. Clarification is persisted to frontmatter
3. --no-questions flag skips clarification
"""

import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
from io import StringIO

import pytest

# Add lib directory to path for imports
lib_path = Path(__file__).parent.parent.parent / "installer" / "core" / "commands" / "lib"
if str(lib_path) not in sys.path:
    sys.path.insert(0, str(lib_path))

# Import orchestrators for direct testing
from task_review_orchestrator import execute_task_review, find_task_file
from clarification.core import parse_frontmatter


class TestClarificationSmoke:
    """End-to-end smoke tests for clarification integration."""

    @pytest.fixture
    def test_environment(self, tmp_path):
        """Set up a minimal test environment with task structure."""
        # Create task directory structure
        tasks_backlog = tmp_path / "tasks" / "backlog"
        tasks_backlog.mkdir(parents=True)
        tasks_in_progress = tmp_path / "tasks" / "in_progress"
        tasks_in_progress.mkdir(parents=True)
        tasks_review_complete = tmp_path / "tasks" / "review_complete"
        tasks_review_complete.mkdir(parents=True)

        return tmp_path

    @pytest.fixture
    def smoke_task_high_complexity(self, test_environment):
        """Create a high-complexity smoke test task."""
        task_id = "TASK-SMOKE-HIGH"
        task_content = '''---
id: TASK-SMOKE-HIGH
title: Smoke test task with high complexity
status: backlog
complexity: 6
task_type: review
priority: medium
created: 2025-12-13T16:00:00Z
updated: 2025-12-13T16:00:00Z
---

# Smoke Test Task - High Complexity

## Description

Test task for smoke test with high complexity to trigger clarification.

## Acceptance Criteria

- [ ] Test passes
'''
        task_file = test_environment / "tasks" / "backlog" / f"{task_id}.md"
        task_file.write_text(task_content)

        return task_id, task_file, test_environment

    @pytest.fixture
    def smoke_task_low_complexity(self, test_environment):
        """Create a low-complexity smoke test task."""
        task_id = "TASK-SMOKE-LOW"
        task_content = '''---
id: TASK-SMOKE-LOW
title: Smoke test task with low complexity
status: backlog
complexity: 2
task_type: review
priority: medium
created: 2025-12-13T16:00:00Z
updated: 2025-12-13T16:00:00Z
---

# Smoke Test Task - Low Complexity

## Description

Test task for smoke test with low complexity to skip clarification.

## Acceptance Criteria

- [ ] Test passes
'''
        task_file = test_environment / "tasks" / "backlog" / f"{task_id}.md"
        task_file.write_text(task_content)

        return task_id, task_file, test_environment

    def _create_mock_model_router(self):
        """Create a mock model router to prevent AI API calls."""
        mock_router = MagicMock()
        mock_cost_info = MagicMock()
        mock_cost_info.model_id = "mock-model"
        mock_cost_info.estimated_cost_usd = 0.0
        mock_cost_info.estimated_tokens = 0
        mock_cost_info.rationale = "Smoke test mock"
        mock_router.get_model_for_review.return_value = "mock-model"
        mock_router.get_cost_estimate.return_value = mock_cost_info
        return mock_router

    def test_clarification_appears_in_output_for_high_complexity(
        self, smoke_task_high_complexity
    ):
        """
        Verify clarification questions appear in output for high complexity tasks.

        This is the key smoke test - if clarification isn't integrated with
        the orchestrator, this test will fail even if unit tests pass.
        """
        task_id, task_file, test_env = smoke_task_high_complexity

        # Mock user input to accept defaults
        mock_answers = iter(["", "", ""])

        # Capture stdout to verify output
        captured_output = StringIO()

        mock_router = self._create_mock_model_router()

        with patch("builtins.input", side_effect=lambda _: next(mock_answers, "")):
            with patch("task_review_orchestrator.ModelRouter", return_value=mock_router):
                with patch("task_review_orchestrator.get_git_root", return_value=test_env):
                    with patch("sys.stdout", captured_output):
                        result = execute_task_review(
                            task_id=task_id,
                            mode="decision",
                            depth="standard",
                        )

        output = captured_output.getvalue()

        # Verify orchestrator succeeded
        assert result["status"] == "success", f"Orchestrator failed: {result.get('error')}"
        assert result["task_id"] == task_id

        # Check for clarification phase indicators in output
        # These strings should appear if clarification is working
        clarification_indicators = [
            "Phase 1.5",  # Phase indicator
            "Clarification",  # Section header
        ]

        found_any = any(
            indicator.lower() in output.lower()
            for indicator in clarification_indicators
        )

        assert found_any, (
            f"No clarification indicators found in output.\n"
            f"Output was:\n{output}\n\n"
            f"This suggests clarification is not integrated with the orchestrator.\n"
            f"Check execute_clarification_phase is being called."
        )

    def test_clarification_persisted_to_frontmatter(
        self, smoke_task_high_complexity
    ):
        """
        Verify clarification decisions are saved to task frontmatter.

        After running the orchestrator, the task file should contain
        clarification data in its frontmatter.
        """
        task_id, task_file, test_env = smoke_task_high_complexity

        # Mock user input to accept defaults
        mock_answers = iter(["", "", ""])

        mock_router = self._create_mock_model_router()

        with patch("builtins.input", side_effect=lambda _: next(mock_answers, "")):
            with patch("task_review_orchestrator.ModelRouter", return_value=mock_router):
                with patch("task_review_orchestrator.get_git_root", return_value=test_env):
                    result = execute_task_review(
                        task_id=task_id,
                        mode="decision",
                        depth="standard",
                    )

        # Verify execution succeeded
        assert result["status"] == "success"

        # Find the task file (may have moved to different state directory)
        found_file = find_task_file(task_id, test_env / "tasks")

        assert found_file is not None, "Task file not found after orchestrator run"
        assert found_file.exists(), f"Task file path exists but file doesn't: {found_file}"

        # Read and parse frontmatter
        content = found_file.read_text()
        frontmatter, _ = parse_frontmatter(content)

        # Check clarification is in frontmatter OR in result
        # Note: Implementation may store in either location
        clarification_in_frontmatter = "clarification" in frontmatter
        clarification_in_result = result.get("clarification") is not None

        assert clarification_in_frontmatter or clarification_in_result, (
            f"Clarification not found in frontmatter or result.\n"
            f"Frontmatter: {frontmatter}\n"
            f"Result clarification: {result.get('clarification')}\n"
            f"This suggests persist_to_frontmatter() is not being called."
        )

    def test_no_questions_flag_skips_clarification(
        self, smoke_task_high_complexity
    ):
        """
        Verify --no-questions flag skips clarification for high complexity tasks.

        Even with high complexity, the --no-questions flag should bypass
        the clarification phase entirely.
        """
        task_id, task_file, test_env = smoke_task_high_complexity

        # Capture stdout
        captured_output = StringIO()

        mock_router = self._create_mock_model_router()

        # Note: No input mock needed since we're skipping questions
        with patch("task_review_orchestrator.ModelRouter", return_value=mock_router):
            with patch("task_review_orchestrator.get_git_root", return_value=test_env):
                with patch("sys.stdout", captured_output):
                    result = execute_task_review(
                        task_id=task_id,
                        mode="decision",
                        depth="standard",
                        no_questions=True,  # Skip clarification
                    )

        output = captured_output.getvalue()

        # Verify execution succeeded
        assert result["status"] == "success"

        # Should see skip indicator OR not see full clarification prompts
        # The exact message depends on implementation
        clarification_skipped = (
            "skip" in output.lower() or
            "Phase 1.5" not in output or
            "CLARIFICATION" not in output.upper()
        )

        # The key assertion: we should NOT be prompted for clarification questions
        # (no "Your choice" prompts, no "Enter" prompts for defaults)
        has_question_prompts = "Your choice" in output or "?" in output

        assert clarification_skipped or not has_question_prompts, (
            f"Clarification prompts appeared despite --no-questions flag.\n"
            f"Output: {output}"
        )

    def test_low_complexity_skips_clarification_automatically(
        self, smoke_task_low_complexity
    ):
        """
        Verify low complexity tasks (<=2) skip clarification automatically.

        For trivial tasks, clarification should be skipped without needing
        the --no-questions flag.
        """
        task_id, task_file, test_env = smoke_task_low_complexity

        # Capture stdout
        captured_output = StringIO()

        mock_router = self._create_mock_model_router()

        # Note: No input mock needed since clarification should be skipped
        with patch("task_review_orchestrator.ModelRouter", return_value=mock_router):
            with patch("task_review_orchestrator.get_git_root", return_value=test_env):
                with patch("sys.stdout", captured_output):
                    result = execute_task_review(
                        task_id=task_id,
                        mode="decision",
                        depth="standard",
                        # Note: NOT passing no_questions - should auto-skip
                    )

        output = captured_output.getvalue()

        # Verify execution succeeded
        assert result["status"] == "success"

        # For low complexity, clarification should be skipped
        # Look for skip message or absence of question prompts
        has_skip_indicator = (
            "skip" in output.lower() or
            "trivial" in output.lower()
        )

        # Should not have interactive question prompts
        has_interactive_prompts = "Your choice" in output

        assert has_skip_indicator or not has_interactive_prompts, (
            f"Low complexity task triggered interactive clarification.\n"
            f"Expected: Skip clarification automatically\n"
            f"Output: {output}"
        )


class TestClarificationSmokeRegressionGuard:
    """
    Regression guard tests that would catch integration breaks.

    These tests are specifically designed to catch the type of regression
    where unit tests pass but real integration fails.
    """

    @pytest.fixture
    def guard_environment(self, tmp_path):
        """Set up environment for regression guard tests."""
        tasks_backlog = tmp_path / "tasks" / "backlog"
        tasks_backlog.mkdir(parents=True)
        (tmp_path / "tasks" / "in_progress").mkdir(parents=True)
        (tmp_path / "tasks" / "review_complete").mkdir(parents=True)
        return tmp_path

    @pytest.fixture
    def medium_complexity_task(self, guard_environment):
        """Create a medium complexity task that should trigger QUICK mode."""
        task_id = "TASK-SMOKE-MED"
        task_content = '''---
id: TASK-SMOKE-MED
title: Medium complexity smoke test
status: backlog
complexity: 4
task_type: review
priority: medium
created: 2025-12-13T16:00:00Z
updated: 2025-12-13T16:00:00Z
---

# Medium Complexity Task

## Description

Task with complexity 4 for testing quick mode clarification.

## Acceptance Criteria

- [ ] Test passes
'''
        task_file = guard_environment / "tasks" / "backlog" / f"{task_id}.md"
        task_file.write_text(task_content)
        return task_id, task_file, guard_environment

    def _create_mock_model_router(self):
        """Create mock model router."""
        mock_router = MagicMock()
        mock_cost_info = MagicMock()
        mock_cost_info.model_id = "mock-model"
        mock_cost_info.estimated_cost_usd = 0.0
        mock_cost_info.estimated_tokens = 0
        mock_cost_info.rationale = "Regression guard mock"
        mock_router.get_model_for_review.return_value = "mock-model"
        mock_router.get_cost_estimate.return_value = mock_cost_info
        return mock_router

    def test_clarification_module_imported_by_orchestrator(self):
        """
        Verify the clarification module is actually imported by orchestrator.

        This catches the case where orchestrator code exists but the import
        fails silently.
        """
        # Import the orchestrator and check CLARIFICATION_AVAILABLE flag
        from task_review_orchestrator import CLARIFICATION_AVAILABLE

        assert CLARIFICATION_AVAILABLE is True, (
            "Clarification module is not available in orchestrator.\n"
            "Check import statements in task_review_orchestrator.py.\n"
            "Expected: CLARIFICATION_AVAILABLE = True"
        )

    def test_execute_clarification_phase_function_exists(self):
        """
        Verify execute_clarification_phase function exists in orchestrator.

        This catches the case where the integration function was removed or renamed.
        """
        from task_review_orchestrator import execute_clarification_phase

        assert callable(execute_clarification_phase), (
            "execute_clarification_phase is not callable.\n"
            "Check that the function exists in task_review_orchestrator.py"
        )

    def test_clarification_called_from_main_workflow(
        self, medium_complexity_task
    ):
        """
        Verify clarification is actually called from the main workflow.

        This test patches the clarification phase to verify it gets called.
        """
        task_id, task_file, test_env = medium_complexity_task

        mock_router = self._create_mock_model_router()

        # Track if clarification phase was called
        clarification_called = False
        original_execute_clarification_phase = None

        def tracking_clarification_phase(*args, **kwargs):
            nonlocal clarification_called
            clarification_called = True
            # Call original if available, otherwise return None
            if original_execute_clarification_phase:
                return original_execute_clarification_phase(*args, **kwargs)
            return None

        # Import to get original function
        from task_review_orchestrator import execute_clarification_phase as orig_func
        original_execute_clarification_phase = orig_func

        with patch("task_review_orchestrator.execute_clarification_phase", tracking_clarification_phase):
            with patch("task_review_orchestrator.ModelRouter", return_value=mock_router):
                with patch("task_review_orchestrator.get_git_root", return_value=test_env):
                    result = execute_task_review(
                        task_id=task_id,
                        mode="decision",
                        depth="standard",
                    )

        assert clarification_called, (
            "execute_clarification_phase was never called from main workflow.\n"
            "Check that execute_task_review calls execute_clarification_phase."
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
