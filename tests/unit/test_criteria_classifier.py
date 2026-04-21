"""Tests for the acceptance criteria classifier.

Validates classification against real-world criteria from:
- FEAT-2AAA (failing run - TASK-VID-001 through TASK-VID-005)
- FEAT-SKEL-001 (successful run - TASK-SKEL-001 through TASK-SKEL-004)
"""

import inspect
import re
from pathlib import Path

import pytest

from guardkit.orchestrator.quality_gates import ac_linter
from guardkit.orchestrator.quality_gates.criteria_classifier import (
    UNVERIFIABLE_CONFIDENCE_THRESHOLD,
    ClassifiedCriterion,
    ClassificationResult,
    CriterionType,
    UnverifiableACWarning,
    classify_acceptance_criteria,
    classify_criterion,
    classify_with_warnings,
)


# --- FEAT-2AAA Criteria (Failing Run) ---


class TestTaskVid001Criteria:
    """TASK-VID-001: Add yt-dlp dependency to pyproject.toml.

    This task caused the UNRECOVERABLE_STALL because 2/3 criteria
    are command_execution type, unverifiable via synthetic report.
    """

    def test_file_content_criterion(self):
        """Criterion 1: file content check — should be verifiable."""
        result = classify_criterion(
            "- [ ] `yt-dlp>=2024.1.0` added to `dependencies` list in `pyproject.toml`"
        )
        assert result.criterion_type == CriterionType.FILE_CONTENT
        assert result.confidence >= 0.6

    def test_pip_install_criterion(self):
        """Criterion 2: command execution — was unverifiable."""
        result = classify_criterion(
            '- [ ] `pip install -e ".[dev]"` succeeds without errors'
        )
        assert result.criterion_type == CriterionType.COMMAND_EXECUTION
        assert result.extracted_command is not None
        assert "pip install" in result.extracted_command

    def test_python_import_criterion(self):
        """Criterion 3: command execution — was unverifiable."""
        result = classify_criterion(
            '- [ ] `python -c "import yt_dlp; print(yt_dlp.version.__version__)"` runs successfully'
        )
        assert result.criterion_type == CriterionType.COMMAND_EXECUTION
        assert result.extracted_command is not None
        assert "python" in result.extracted_command

    def test_full_task_classification(self):
        """All 3 criteria classified: expect 1 file_content, 2 command_execution."""
        criteria = [
            "- [ ] `yt-dlp>=2024.1.0` added to `dependencies` list in `pyproject.toml`",
            '- [ ] `pip install -e ".[dev]"` succeeds without errors',
            '- [ ] `python -c "import yt_dlp; print(yt_dlp.version.__version__)"` runs successfully',
        ]
        result = classify_acceptance_criteria(criteria)
        assert len(result.file_content_criteria) == 1
        assert len(result.command_criteria) == 2
        assert len(result.manual_criteria) == 0
        assert result.verifiable_count == 3


class TestTaskVid005Criteria:
    """TASK-VID-005: Add integration tests.

    5/6 criteria were unverifiable (commands + manual).
    """

    def test_pytest_command(self):
        result = classify_criterion(
            "- [ ] `pytest tests/test_video_info.py -v` passes all tests"
        )
        assert result.criterion_type == CriterionType.COMMAND_EXECUTION

    def test_coverage_command(self):
        result = classify_criterion(
            "- [ ] `pytest --cov=src --cov-report=term` shows >= 80% coverage"
        )
        assert result.criterion_type == CriterionType.COMMAND_EXECUTION


# --- FEAT-SKEL-001 Criteria (Successful Run) ---


class TestSuccessfulRunCriteria:
    """Criteria from the successful FEAT-SKEL-001 run.

    All criteria were file-content verifiable, which is why
    the synthetic report path worked.
    """

    def test_file_exists(self):
        result = classify_criterion(
            "- [ ] `pyproject.toml` exists with correct metadata"
        )
        assert result.criterion_type == CriterionType.FILE_CONTENT

    def test_file_contains(self):
        result = classify_criterion(
            '- [ ] `pyproject.toml` contains `name = "youtube-transcript-mcp"`'
        )
        assert result.criterion_type == CriterionType.FILE_CONTENT

    def test_module_defined(self):
        result = classify_criterion(
            "- [ ] Module `src/server.py` exists with FastMCP server"
        )
        assert result.criterion_type == CriterionType.FILE_CONTENT

    def test_function_defined(self):
        result = classify_criterion(
            "- [ ] Function `ping()` defined in `src/server.py`"
        )
        assert result.criterion_type == CriterionType.FILE_CONTENT


# --- Edge Cases ---


class TestEdgeCases:
    def test_empty_string(self):
        result = classify_acceptance_criteria([""])
        assert result.total_count == 0

    def test_whitespace_only(self):
        result = classify_acceptance_criteria(["   "])
        assert result.total_count == 0

    def test_no_backticks(self):
        """Plain text criterion with no code markers."""
        result = classify_criterion("The API responds with 200 OK")
        # Should default to file_content with low confidence
        assert result.confidence <= 0.5

    def test_manual_visual_check(self):
        result = classify_criterion(
            "- [ ] Visually verify the UI matches the design mockup"
        )
        assert result.criterion_type == CriterionType.MANUAL

    def test_manual_performance_check(self):
        result = classify_criterion(
            "- [ ] Response time stays under 200ms for 95th percentile"
        )
        assert result.criterion_type == CriterionType.MANUAL

    def test_npm_install_command(self):
        result = classify_criterion(
            "- [ ] `npm install` completes without errors"
        )
        assert result.criterion_type == CriterionType.COMMAND_EXECUTION
        assert "npm install" in result.extracted_command

    def test_docker_command(self):
        result = classify_criterion(
            "- [ ] `docker build -t myapp .` succeeds"
        )
        assert result.criterion_type == CriterionType.COMMAND_EXECUTION

    def test_cargo_test(self):
        result = classify_criterion(
            "- [ ] `cargo test` passes all tests"
        )
        assert result.criterion_type == CriterionType.COMMAND_EXECUTION

    def test_checkbox_stripped(self):
        """Markdown checkbox prefix should not affect classification."""
        with_checkbox = classify_criterion("- [x] `pip install` succeeds")
        without_checkbox = classify_criterion("`pip install` succeeds")
        assert with_checkbox.criterion_type == without_checkbox.criterion_type


# --- ClassificationResult Properties ---


class TestClassificationResult:
    def test_mixed_criteria(self):
        criteria = [
            "- [ ] `config.json` exists with correct settings",
            "- [ ] `npm test` passes all tests",
            "- [ ] Visually verify the layout matches mockup",
        ]
        result = classify_acceptance_criteria(criteria)
        assert result.total_count == 3
        assert len(result.file_content_criteria) == 1
        assert len(result.command_criteria) == 1
        assert len(result.manual_criteria) == 1
        assert result.verifiable_count == 2

    def test_empty_input(self):
        result = classify_acceptance_criteria([])
        assert result.total_count == 0
        assert result.verifiable_count == 0


# --- Assertable-AC Linter (warn-mode v1) ---
#
# NOTE: AC lines 67-68 of TASK-AC-53445 specify path
# tests/unit/orchestrator/test_criteria_classifier.py, but the existing
# classifier tests live here (tests/unit/test_criteria_classifier.py).
# Per that task's resolution, new linter tests are colocated with the
# existing suite rather than fragmenting into a parallel directory.


class TestUnverifiableACWarning:
    """Warn-mode v1 behaviour: emit warnings without blocking."""

    def test_unverifiable_ac_warning_emitted(self):
        """Prose AC produces exactly one warning at 0.3-confidence fallback.

        Directly validates AC line 68 of TASK-AC-53445.
        """
        _result, warnings = classify_with_warnings(
            ["- [ ] handles edge cases correctly"],
            task_id="TASK-TEST-0001",
        )
        assert len(warnings) == 1
        w = warnings[0]
        assert isinstance(w, UnverifiableACWarning)
        assert "handles edge cases correctly" in w.ac_text
        assert w.task_id == "TASK-TEST-0001"
        assert w.reason  # non-empty, sourced verbatim from classifier

    def test_verifiable_acs_produce_no_warnings(self):
        """Well-formed ACs (file-content or command) must not warn."""
        _result, warnings = classify_with_warnings(
            [
                "- [ ] `pyproject.toml` contains `name = \"ac-linter\"`",
                "- [ ] `pytest tests/` passes all tests",
            ],
            task_id="TASK-TEST-0002",
        )
        assert warnings == []

    def test_mixed_plan_warnings_are_task_scoped(self):
        """Warnings carry the supplied task_id verbatim."""
        _result, warnings = classify_with_warnings(
            [
                "- [ ] `pyproject.toml` exists with correct metadata",
                "- [ ] backward-compatible defaults ensure no breakage",
            ],
            task_id="TASK-AC-53445",
        )
        assert len(warnings) == 1
        assert warnings[0].task_id == "TASK-AC-53445"

    def test_threshold_is_exclusive_upper_bound(self):
        """Exactly-at-threshold confidence does NOT warn.

        Guards against accidentally upgrading 0.6 file-path fallbacks
        (criteria_classifier.py:170-177) into warnings.
        """
        assert UNVERIFIABLE_CONFIDENCE_THRESHOLD == 0.6
        # A bare-file-path AC classifies at 0.6 via the fallback branch.
        _result, warnings = classify_with_warnings(
            ["- [ ] something-or-other in `config.py`"],
            task_id="TASK-TEST-0003",
        )
        # The file-path fallback scores exactly 0.6 and must remain quiet.
        # If this starts warning, the threshold has drifted.
        assert warnings == []


class TestLinterHasNoIndependentPatterns:
    """Architectural guardrail from TASK-AC-53445.

    The linter module must be a report-mode wrapper around the
    classifier. If this test fails, the linter has grown a parallel
    classification path — delete it, don't reconcile.

    Directly validates AC line 67 of TASK-AC-53445.
    """

    @pytest.fixture
    def linter_source(self) -> str:
        """Raw source of ac_linter module — the thing we're asserting about."""
        return inspect.getsource(ac_linter)

    def test_linter_has_no_independent_patterns(self, linter_source):
        """Grep the linter module for regex / heuristic patterns.

        Allowed: delegation to classify_with_warnings / classify_criterion.
        Forbidden: re.compile, pattern constants, confidence thresholds,
        or a standalone `import re`.
        """
        # No regex compilation.
        assert "re.compile" not in linter_source, (
            "ac_linter must not compile regexes — delegate to criteria_classifier"
        )

        # No standalone re import (matches `import re` at start of line or
        # after a newline; does not match `from re import ...` either).
        assert not re.search(r"(?:^|\n)\s*import re(?:\s|$)", linter_source), (
            "ac_linter must not import re — it has no business matching patterns"
        )
        assert not re.search(r"(?:^|\n)\s*from re\s", linter_source), (
            "ac_linter must not import from re — it has no business matching patterns"
        )

        # No pattern-list constants.
        assert "_PATTERNS" not in linter_source, (
            "ac_linter must not define _PATTERNS constants — "
            "classification lives in criteria_classifier"
        )

        # No locally-defined confidence threshold. The sole knob is
        # UNVERIFIABLE_CONFIDENCE_THRESHOLD in criteria_classifier; any
        # float comparison here would indicate a parallel heuristic.
        assert not re.search(r"confidence\s*[<>]=?\s*0\.\d", linter_source), (
            "ac_linter must not compare confidence directly — "
            "that threshold belongs to criteria_classifier"
        )
        # No assignment of a local threshold constant. (Distinct from
        # merely mentioning the classifier's constant in a docstring.)
        assert not re.search(
            r"^[A-Z_]*THRESHOLD[A-Z_]*\s*=", linter_source, re.MULTILINE
        ), "ac_linter must not declare its own threshold constant"

    def test_linter_delegates_to_classifier(self, linter_source):
        """Positive assertion: the linter *does* call through to the classifier."""
        assert "classify_with_warnings" in linter_source, (
            "ac_linter must delegate to classify_with_warnings"
        )
