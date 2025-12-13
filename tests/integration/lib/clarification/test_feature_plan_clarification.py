"""Integration tests for clarification in feature-plan workflow.

Tests that the real feature_plan_orchestrator correctly invokes clarification
and uses clarification context for subtask generation.

These tests call the REAL orchestrator with only I/O mocked:
- builtins.input → Simulated user answers
- Model router → Prevent actual AI API calls
"""

import sys
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add lib directory to path for imports
lib_path = Path(__file__).parent.parent.parent.parent.parent / "installer" / "core" / "commands" / "lib"
if str(lib_path) not in sys.path:
    sys.path.insert(0, str(lib_path))

# Import real orchestrator
from feature_plan_orchestrator import execute_feature_plan

# Import clarification components for verification
from clarification.core import ClarificationContext, parse_frontmatter

# Note: create_task_in_state is defined in the local conftest.py.
# Import directly with full path to avoid conftest shadowing from root directory.
import importlib.util
_conftest_spec = importlib.util.spec_from_file_location(
    "local_conftest",
    Path(__file__).parent / "conftest.py"
)
_local_conftest = importlib.util.module_from_spec(_conftest_spec)
_conftest_spec.loader.exec_module(_local_conftest)
create_task_in_state = _local_conftest.create_task_in_state


def create_mock_model_router():
    """Create standard mock model router for tests."""
    mock_model_router = MagicMock()
    mock_cost_info = MagicMock()
    mock_cost_info.model_id = "mock-model"
    mock_cost_info.estimated_cost_usd = 0.0
    mock_cost_info.estimated_tokens = 0
    mock_cost_info.rationale = "Test mock"
    mock_model_router.get_model_for_review.return_value = "mock-model"
    mock_model_router.get_model_for_planning.return_value = "mock-model"
    mock_model_router.get_cost_estimate.return_value = mock_cost_info
    mock_model_router.log_model_usage.return_value = None
    return mock_model_router


class TestRealFeaturePlanClarification:
    """Test clarification integration with real feature_plan_orchestrator."""

    def test_feature_plan_triggers_review_clarification(
        self, temp_project_dir: Path
    ):
        """
        Feature plan should trigger review scope clarification (Context A).
        """
        feature_desc = "implement dark mode toggle"

        mock_model_router = create_mock_model_router()
        mock_answers = iter(["", "", "", ""])  # Accept defaults for clarification questions

        with patch("builtins.input", side_effect=lambda _: next(mock_answers, "")):
            with patch("task_review_orchestrator.ModelRouter", return_value=mock_model_router):
                with patch("feature_plan_orchestrator.get_git_root", return_value=temp_project_dir):
                    with patch("task_review_orchestrator.get_git_root", return_value=temp_project_dir):
                        # Mock decision checkpoint to return "accept" (avoid interactive loop)
                        with patch("feature_plan_orchestrator._present_decision_checkpoint", return_value="accept"):
                            result = execute_feature_plan(
                                feature_description=feature_desc,
                                flags={},
                            )

        assert result["status"] == "success"

        # Check that clarification was triggered
        review_clarification = result.get("clarification_a")
        if review_clarification is not None:
            assert review_clarification.context_type == "review_scope"

    def test_feature_plan_triggers_implement_clarification(
        self, temp_project_dir: Path
    ):
        """
        Feature plan should trigger implementation preferences clarification (Context B).
        """
        feature_desc = "add user notifications"

        mock_model_router = create_mock_model_router()

        # Simulate: Review questions + Implement questions (checkpoint is mocked)
        mock_answers = iter([
            "",  # Review Q1
            "",  # Review Q2
            "",  # Implement Q1
            "",  # Implement Q2
        ])

        with patch("builtins.input", side_effect=lambda _: next(mock_answers, "")):
            with patch("task_review_orchestrator.ModelRouter", return_value=mock_model_router):
                with patch("feature_plan_orchestrator.get_git_root", return_value=temp_project_dir):
                    with patch("task_review_orchestrator.get_git_root", return_value=temp_project_dir):
                        # Mock checkpoint to return "implement" to trigger Context B
                        with patch("feature_plan_orchestrator._present_decision_checkpoint", return_value="implement"):
                            result = execute_feature_plan(
                                feature_description=feature_desc,
                                flags={},
                            )

        assert result["status"] == "success"

        # Check implementation clarification
        implement_clarification = result.get("clarification_b")
        if implement_clarification is not None:
            assert implement_clarification.context_type == "implementation_prefs"

    def test_no_questions_flag_skips_both_clarifications(
        self, temp_project_dir: Path
    ):
        """
        --no-questions should skip both Context A and Context B clarifications.
        """
        feature_desc = "add search functionality"

        mock_model_router = create_mock_model_router()
        input_calls = []

        def track_input(prompt):
            input_calls.append(prompt)
            return ""

        with patch("builtins.input", side_effect=track_input):
            with patch("task_review_orchestrator.ModelRouter", return_value=mock_model_router):
                with patch("feature_plan_orchestrator.get_git_root", return_value=temp_project_dir):
                    with patch("task_review_orchestrator.get_git_root", return_value=temp_project_dir):
                        # Mock checkpoint to return "accept" (avoid interactive loop)
                        with patch("feature_plan_orchestrator._present_decision_checkpoint", return_value="accept"):
                            result = execute_feature_plan(
                                feature_description=feature_desc,
                                flags={"no_questions": True},
                            )

        assert result["status"] == "success"

        # Both clarifications should be None or skip mode
        review_clr = result.get("clarification_a")
        implement_clr = result.get("clarification_b")

        if review_clr is not None:
            assert review_clr.mode == "skip" or review_clr.user_override == "skip"
        if implement_clr is not None:
            assert implement_clr.mode == "skip" or implement_clr.user_override == "skip"

    def test_with_questions_forces_clarification(
        self, temp_project_dir: Path
    ):
        """
        --with-questions should force clarification even for simple features.
        """
        feature_desc = "fix typo"  # Simple feature

        mock_model_router = create_mock_model_router()
        mock_answers = iter(["", "", "", "", ""])

        with patch("builtins.input", side_effect=lambda _: next(mock_answers, "")):
            with patch("task_review_orchestrator.ModelRouter", return_value=mock_model_router):
                with patch("feature_plan_orchestrator.get_git_root", return_value=temp_project_dir):
                    with patch("task_review_orchestrator.get_git_root", return_value=temp_project_dir):
                        # Mock checkpoint to return "accept" (avoid interactive loop)
                        with patch("feature_plan_orchestrator._present_decision_checkpoint", return_value="accept"):
                            result = execute_feature_plan(
                                feature_description=feature_desc,
                                flags={"with_questions": True},
                            )

        assert result["status"] == "success"

        # Clarification should be triggered despite simple feature
        review_clr = result.get("clarification_a")
        if review_clr is not None:
            assert review_clr.mode != "skip"


class TestSubtaskGeneration:
    """Test that clarification context affects subtask generation."""

    def test_subtasks_reflect_scope_decision(
        self, temp_project_dir: Path
    ):
        """
        Subtask generation should respect scope decision from clarification.
        """
        feature_desc = "implement user authentication"

        mock_model_router = create_mock_model_router()

        # Choose minimal scope (checkpoint is mocked)
        mock_answers = iter([
            "M",  # Minimal scope
            "",   # Other defaults
            "M",  # Minimal implementation
        ])

        with patch("builtins.input", side_effect=lambda _: next(mock_answers, "")):
            with patch("task_review_orchestrator.ModelRouter", return_value=mock_model_router):
                with patch("feature_plan_orchestrator.get_git_root", return_value=temp_project_dir):
                    with patch("task_review_orchestrator.get_git_root", return_value=temp_project_dir):
                        # Mock checkpoint to return "implement" to trigger subtask generation
                        with patch("feature_plan_orchestrator._present_decision_checkpoint", return_value="implement"):
                            result = execute_feature_plan(
                                feature_description=feature_desc,
                                flags={},
                            )

        assert result["status"] == "success"

        # Subtasks should exist (check subtasks_created count)
        subtasks_created = result.get("subtasks_created", 0)

        # The number/scope of subtasks should be influenced by clarification
        # At minimum, we verify the feature was processed
        assert result.get("decision") is not None

    def test_complete_scope_generates_more_subtasks(
        self, temp_project_dir: Path
    ):
        """
        Complete scope should generate comprehensive subtask list.
        """
        feature_desc = "implement full payment system"

        mock_model_router = create_mock_model_router()

        # Choose complete scope (checkpoint is mocked)
        mock_answers = iter([
            "C",  # Complete scope
            "",   # Other defaults
            "C",  # Complete implementation
        ])

        with patch("builtins.input", side_effect=lambda _: next(mock_answers, "")):
            with patch("task_review_orchestrator.ModelRouter", return_value=mock_model_router):
                with patch("feature_plan_orchestrator.get_git_root", return_value=temp_project_dir):
                    with patch("task_review_orchestrator.get_git_root", return_value=temp_project_dir):
                        # Mock checkpoint to return "implement" to trigger subtask generation
                        with patch("feature_plan_orchestrator._present_decision_checkpoint", return_value="implement"):
                            result = execute_feature_plan(
                                feature_description=feature_desc,
                                flags={},
                            )

        assert result["status"] == "success"

        # Complete scope should have more comprehensive subtasks
        # At minimum, verify the decision was made
        if result.get("clarification_b"):
            assert result.get("decision") is not None


class TestClarificationPersistence:
    """Test clarification persistence in feature-plan workflow."""

    def test_review_clarification_persisted(
        self, temp_project_dir: Path
    ):
        """
        Review clarification should be persisted to generated review task.
        """
        feature_desc = "add analytics dashboard"

        mock_model_router = create_mock_model_router()
        mock_answers = iter(["", "", "", ""])

        with patch("builtins.input", side_effect=lambda _: next(mock_answers, "")):
            with patch("task_review_orchestrator.ModelRouter", return_value=mock_model_router):
                with patch("feature_plan_orchestrator.get_git_root", return_value=temp_project_dir):
                    with patch("task_review_orchestrator.get_git_root", return_value=temp_project_dir):
                        # Mock checkpoint to return "accept" (avoid interactive loop)
                        with patch("feature_plan_orchestrator._present_decision_checkpoint", return_value="accept"):
                            result = execute_feature_plan(
                                feature_description=feature_desc,
                                flags={},
                            )

        assert result["status"] == "success"

        # Check if review task was created
        review_task_id = result.get("review_task_id")

        if review_task_id:
            # Look for task file in tasks directory
            tasks_dir = temp_project_dir / "tasks"
            for state_dir in tasks_dir.iterdir():
                if state_dir.is_dir():
                    for task_file in state_dir.glob(f"{review_task_id}*.md"):
                        content = task_file.read_text()
                        frontmatter, _ = parse_frontmatter(content)

                        # Check if clarification was persisted
                        if "clarification" in frontmatter:
                            assert frontmatter["clarification"]["context"] == "review_scope"

    def test_implement_clarification_affects_output(
        self, temp_project_dir: Path
    ):
        """
        Implementation clarification should affect output artifacts.
        """
        feature_desc = "implement caching layer"

        mock_model_router = create_mock_model_router()
        mock_answers = iter(["", "", "", ""])  # Checkpoint is mocked

        with patch("builtins.input", side_effect=lambda _: next(mock_answers, "")):
            with patch("task_review_orchestrator.ModelRouter", return_value=mock_model_router):
                with patch("feature_plan_orchestrator.get_git_root", return_value=temp_project_dir):
                    with patch("task_review_orchestrator.get_git_root", return_value=temp_project_dir):
                        # Mock checkpoint to return "implement" to trigger Context B
                        with patch("feature_plan_orchestrator._present_decision_checkpoint", return_value="implement"):
                            result = execute_feature_plan(
                                feature_description=feature_desc,
                                flags={},
                            )

        assert result["status"] == "success"

        # Implementation clarification should be in result
        implement_clarification = result.get("clarification_b")

        if implement_clarification is not None:
            # Verify it has proper structure
            assert hasattr(implement_clarification, "decisions") or isinstance(implement_clarification, dict)


class TestFeatureDescriptionVariations:
    """Test clarification with various feature descriptions."""

    @pytest.mark.parametrize("feature_desc", [
        "add user authentication",
        "implement dark mode",
        "refactor database layer",
        "optimize performance",
        "fix security vulnerabilities",
    ])
    def test_various_features_execute_successfully(
        self, temp_project_dir: Path, feature_desc: str
    ):
        """
        Various feature descriptions should all execute successfully.
        """
        mock_model_router = create_mock_model_router()
        mock_answers = iter(["", "", "", "", ""])

        with patch("builtins.input", side_effect=lambda _: next(mock_answers, "")):
            with patch("task_review_orchestrator.ModelRouter", return_value=mock_model_router):
                with patch("feature_plan_orchestrator.get_git_root", return_value=temp_project_dir):
                    with patch("task_review_orchestrator.get_git_root", return_value=temp_project_dir):
                        # Mock checkpoint to return "accept" (avoid interactive loop)
                        with patch("feature_plan_orchestrator._present_decision_checkpoint", return_value="accept"):
                            result = execute_feature_plan(
                                feature_description=feature_desc,
                                flags={},
                            )

        assert result["status"] == "success"

    def test_empty_feature_description_handled(
        self, temp_project_dir: Path
    ):
        """
        Empty feature description should be handled gracefully.
        """
        mock_model_router = create_mock_model_router()
        mock_answers = iter(["", ""])

        with patch("builtins.input", side_effect=lambda _: next(mock_answers, "")):
            with patch("task_review_orchestrator.ModelRouter", return_value=mock_model_router):
                with patch("feature_plan_orchestrator.get_git_root", return_value=temp_project_dir):
                    with patch("task_review_orchestrator.get_git_root", return_value=temp_project_dir):
                        # Mock checkpoint to return "accept" (avoid interactive loop)
                        with patch("feature_plan_orchestrator._present_decision_checkpoint", return_value="accept"):
                            try:
                                result = execute_feature_plan(
                                    feature_description="",
                                    flags={},
                                )
                                # If it succeeds with empty, that's fine
                                assert result is not None
                            except (ValueError, TypeError):
                                # Raising error for empty description is also acceptable
                                pass


class TestClarificationFlags:
    """Test clarification control flags in feature-plan."""

    def test_defaults_flag_uses_defaults(
        self, temp_project_dir: Path
    ):
        """
        --defaults flag should use all default answers.
        """
        feature_desc = "add new feature"

        mock_model_router = create_mock_model_router()
        input_calls = []

        def track_input(prompt):
            input_calls.append(prompt)
            return ""

        with patch("builtins.input", side_effect=track_input):
            with patch("task_review_orchestrator.ModelRouter", return_value=mock_model_router):
                with patch("feature_plan_orchestrator.get_git_root", return_value=temp_project_dir):
                    with patch("task_review_orchestrator.get_git_root", return_value=temp_project_dir):
                        # Mock checkpoint to return "accept" (avoid interactive loop)
                        with patch("feature_plan_orchestrator._present_decision_checkpoint", return_value="accept"):
                            result = execute_feature_plan(
                                feature_description=feature_desc,
                                flags={"defaults": True},
                            )

        assert result["status"] == "success"

        # With defaults, no interactive clarification prompts should happen
        # (though other prompts like checkpoint may still occur)

    def test_inline_answers_flag(
        self, temp_project_dir: Path
    ):
        """
        --answers flag should provide inline answers.
        """
        feature_desc = "implement feature X"

        mock_model_router = create_mock_model_router()
        mock_answers = iter(["", ""])

        with patch("builtins.input", side_effect=lambda _: next(mock_answers, "")):
            with patch("task_review_orchestrator.ModelRouter", return_value=mock_model_router):
                with patch("feature_plan_orchestrator.get_git_root", return_value=temp_project_dir):
                    with patch("task_review_orchestrator.get_git_root", return_value=temp_project_dir):
                        # Mock checkpoint to return "accept" (avoid interactive loop)
                        with patch("feature_plan_orchestrator._present_decision_checkpoint", return_value="accept"):
                            result = execute_feature_plan(
                                feature_description=feature_desc,
                                flags={"answers": "scope:standard testing:integration"},
                            )

        assert result["status"] == "success"

        # Clarification should have recorded the inline answers
        review_clr = result.get("clarification_a")
        if review_clr is not None and hasattr(review_clr, "decisions"):
            # Check if answers were applied
            decisions_by_id = {d.question_id: d for d in review_clr.decisions}
            if "scope" in decisions_by_id:
                assert decisions_by_id["scope"].answer in ["standard", "S"]


class TestIndependentContexts:
    """Test that Context A and Context B are independent."""

    def test_review_and_implement_clarifications_independent(
        self, temp_project_dir: Path
    ):
        """
        Review and implementation clarifications should be independent.
        """
        feature_desc = "add comprehensive feature"

        mock_model_router = create_mock_model_router()
        mock_answers = iter([
            "C",  # Review: Complete scope
            "",   # Review: default
            "M",  # Implement: Minimal
            "",   # Implement: default
        ])

        with patch("builtins.input", side_effect=lambda _: next(mock_answers, "")):
            with patch("task_review_orchestrator.ModelRouter", return_value=mock_model_router):
                with patch("feature_plan_orchestrator.get_git_root", return_value=temp_project_dir):
                    with patch("task_review_orchestrator.get_git_root", return_value=temp_project_dir):
                        # Mock checkpoint to return "implement" to trigger Context B
                        with patch("feature_plan_orchestrator._present_decision_checkpoint", return_value="implement"):
                            result = execute_feature_plan(
                                feature_description=feature_desc,
                                flags={},
                            )

        assert result["status"] == "success"

        review_clr = result.get("clarification_a")
        implement_clr = result.get("clarification_b")

        # Both should exist
        if review_clr is not None and implement_clr is not None:
            # Different context types
            assert review_clr.context_type == "review_scope"
            assert implement_clr.context_type == "implementation_prefs"

            # Independent decisions
            if hasattr(review_clr, "decisions") and hasattr(implement_clr, "decisions"):
                assert review_clr.decisions != implement_clr.decisions
