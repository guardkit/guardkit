"""Unit tests for the TASK-FIX-A7B4 seam-tests blocking gate.

Covers:
    * The module-level helper ``_extract_seam_tests_section`` — header
      detection, case-insensitivity, level-aware closing, and empty-body
      filtering.
    * The ``CoachValidator._count_seam_marker_tests`` reader — marker
      detection across files, tolerance for missing/unreadable files, and
      multi-marker support.
    * The ``CoachValidator._check_seam_tests_implemented`` gate — return
      shape and absence-of-trigger conditions.
    * End-to-end ``validate()`` behaviour, matching the task-file ACs:
        - AC-005: Player ignores ``## Seam Tests`` block → ``feedback``
        - AC-006: Task without ``## Seam Tests`` → no spurious failure
        - AC-007: ``## Seam Tests`` + marker-decorated tests → ``approve``

Coverage Target: >=85% of the gate plus its helper.
Test Count: 16
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest

from guardkit.orchestrator.quality_gates import CoachValidator
from guardkit.orchestrator.quality_gates.coach_validator import (
    _extract_seam_tests_section,
)


# ============================================================================
# Test Fixtures (mirror the layout used by test_coach_validator.py)
# ============================================================================


@pytest.fixture
def tmp_worktree(tmp_path: Path) -> Path:
    """Create a temporary worktree directory."""
    worktree = tmp_path / "worktrees" / "TASK-001"
    worktree.mkdir(parents=True)
    return worktree


@pytest.fixture
def task_work_results_dir(tmp_worktree: Path) -> Path:
    """Create the task-work results directory."""
    results_dir = tmp_worktree / ".guardkit" / "autobuild" / "TASK-001"
    results_dir.mkdir(parents=True)
    return results_dir


def _write_test_file(worktree: Path, rel_path: str, body: str) -> None:
    """Materialise a test file under the worktree at ``rel_path``."""
    target = worktree / rel_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body, encoding="utf-8")


def _passing_task_work_results(
    tests_written: List[str],
    requirements_met: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Build a results payload that would otherwise approve cleanly."""
    return {
        "quality_gates": {
            "tests_passing": True,
            "tests_passed": len(tests_written) or 1,
            "tests_failed": 0,
            "coverage": 88,
            "coverage_met": True,
            "all_passed": True,
        },
        "code_review": {"score": 85, "solid": 85, "dry": 80, "yagni": 82},
        "plan_audit": {"violations": 0, "file_count_match": True},
        "requirements_met": requirements_met if requirements_met is not None else [
            "Criterion A",
            "Criterion B",
        ],
        "tests_written": tests_written,
    }


def _write_results(results_dir: Path, payload: Dict[str, Any]) -> None:
    (results_dir / "task_work_results.json").write_text(
        json.dumps(payload, indent=2),
        encoding="utf-8",
    )


# ============================================================================
# Helper: _extract_seam_tests_section
# ============================================================================


class TestExtractSeamTestsSection:
    """Unit tests for the description-parsing helper."""

    def test_returns_none_for_empty_input(self) -> None:
        assert _extract_seam_tests_section("") is None
        assert _extract_seam_tests_section(None) is None

    def test_returns_none_when_header_absent(self) -> None:
        body = "# Task: Foo\n\n## Description\n\nDo something.\n"
        assert _extract_seam_tests_section(body) is None

    def test_returns_none_when_section_empty(self) -> None:
        # Header present, body whitespace-only — AC-001 says "an empty
        # ## Seam Tests section with no code stubs does not trigger".
        body = (
            "# Task: Foo\n\n"
            "## Seam Tests\n"
            "\n"
            "   \n"
            "## Out Of Scope\n"
            "\n"
            "Nothing.\n"
        )
        assert _extract_seam_tests_section(body) is None

    def test_returns_body_when_section_has_stub(self) -> None:
        body = (
            "## Seam Tests\n"
            "\n"
            "```python\n"
            "@pytest.mark.seam\n"
            "def test_widget_writes_then_reads():\n"
            "    ...\n"
            "```\n"
            "\n"
            "## Out Of Scope\n"
        )
        section = _extract_seam_tests_section(body)
        assert section is not None
        assert "@pytest.mark.seam" in section
        # Body must NOT include the next header.
        assert "Out Of Scope" not in section

    def test_header_match_is_case_insensitive(self) -> None:
        body = "## seam tests\n\nstub\n"
        assert _extract_seam_tests_section(body) is not None
        body_caps = "## SEAM TESTS\n\nstub\n"
        assert _extract_seam_tests_section(body_caps) is not None

    def test_subheader_level_is_respected(self) -> None:
        # `### Seam Tests` should still trigger — AC-001 just says
        # "markdown header parse, case-insensitive". The closing level
        # then needs to honour the matched depth so the section ends at the
        # next equal-or-shallower header.
        body = (
            "## Implementation Notes\n"
            "\n"
            "### Seam Tests\n"
            "\n"
            "stub line\n"
            "\n"
            "## Out Of Scope\n"
        )
        section = _extract_seam_tests_section(body)
        assert section is not None
        assert "stub line" in section
        assert "Out Of Scope" not in section

    def test_prose_mentioning_seam_tests_does_not_trigger(self) -> None:
        # The header regex is anchored — prose like "Seam Tests are useful"
        # should not be treated as a header.
        body = "## Description\n\nSeam Tests are useful in cross-boundary work.\n"
        assert _extract_seam_tests_section(body) is None


# ============================================================================
# Helper: _count_seam_marker_tests
# ============================================================================


class TestCountSeamMarkerTests:
    """Unit tests for the marker-counting helper on the validator."""

    def test_counts_pytest_mark_seam(self, tmp_worktree: Path) -> None:
        _write_test_file(
            tmp_worktree,
            "tests/test_widget.py",
            "import pytest\n\n@pytest.mark.seam\ndef test_widget():\n    ...\n",
        )
        validator = CoachValidator(str(tmp_worktree))
        assert validator._count_seam_marker_tests(["tests/test_widget.py"]) == 1

    def test_counts_contract_and_boundary_markers(self, tmp_worktree: Path) -> None:
        _write_test_file(
            tmp_worktree,
            "tests/test_a.py",
            "@pytest.mark.contract\ndef test_a(): ...\n",
        )
        _write_test_file(
            tmp_worktree,
            "tests/test_b.py",
            "@pytest.mark.boundary\ndef test_b(): ...\n",
        )
        validator = CoachValidator(str(tmp_worktree))
        total = validator._count_seam_marker_tests(
            ["tests/test_a.py", "tests/test_b.py"]
        )
        assert total == 2

    def test_filename_without_marker_does_not_count(
        self, tmp_worktree: Path
    ) -> None:
        # `test_seam_widget.py` (filename suggestive) but no marker — must
        # NOT satisfy the contract gate. AC-002 demands marker presence.
        _write_test_file(
            tmp_worktree,
            "tests/test_seam_widget.py",
            "def test_widget():\n    assert True\n",
        )
        validator = CoachValidator(str(tmp_worktree))
        assert (
            validator._count_seam_marker_tests(["tests/test_seam_widget.py"]) == 0
        )

    def test_missing_file_is_silently_ignored(self, tmp_worktree: Path) -> None:
        validator = CoachValidator(str(tmp_worktree))
        # No file written — read should fail gracefully, return 0.
        assert validator._count_seam_marker_tests(["tests/missing.py"]) == 0

    def test_empty_list_returns_zero(self, tmp_worktree: Path) -> None:
        validator = CoachValidator(str(tmp_worktree))
        assert validator._count_seam_marker_tests([]) == 0


# ============================================================================
# Gate: _check_seam_tests_implemented (return-shape unit tests)
# ============================================================================


class TestSeamTestsGateReturnShape:
    """Unit tests for the validator method that emits the blocking issue."""

    def test_no_section_returns_empty(self, tmp_worktree: Path) -> None:
        validator = CoachValidator(str(tmp_worktree))
        issues = validator._check_seam_tests_implemented(
            task={"description": "Plain task with no seam stub."},
            task_work_results={"tests_written": []},
        )
        assert issues == []

    def test_section_with_marker_test_returns_empty(
        self, tmp_worktree: Path
    ) -> None:
        _write_test_file(
            tmp_worktree,
            "tests/test_widget.py",
            "@pytest.mark.seam\ndef test_widget(): ...\n",
        )
        validator = CoachValidator(str(tmp_worktree))
        issues = validator._check_seam_tests_implemented(
            task={
                "description": (
                    "## Seam Tests\n\n```python\n@pytest.mark.seam\n"
                    "def test_widget(): ...\n```\n"
                )
            },
            task_work_results={"tests_written": ["tests/test_widget.py"]},
        )
        assert issues == []

    def test_section_without_marker_test_returns_must_fix(
        self, tmp_worktree: Path
    ) -> None:
        _write_test_file(
            tmp_worktree,
            "tests/test_widget.py",
            "def test_widget(): assert True\n",  # no seam marker
        )
        validator = CoachValidator(str(tmp_worktree))
        issues = validator._check_seam_tests_implemented(
            task={
                "description": (
                    "## Seam Tests\n\n```python\n@pytest.mark.seam\n"
                    "def test_widget_seam():\n    ...\n```\n"
                )
            },
            task_work_results={"tests_written": ["tests/test_widget.py"]},
        )
        assert len(issues) == 1
        issue = issues[0]
        assert issue["severity"] == "must_fix"
        assert issue["category"] == "seam_tests_unimplemented"
        # AC-005: feedback should reference the stub.
        assert "test_widget_seam" in issue["description"]


# ============================================================================
# End-to-end validate() — matches the AC-005/006/007 contracts
# ============================================================================


def _make_task(description: str = "") -> Dict[str, Any]:
    return {
        "acceptance_criteria": ["Criterion A", "Criterion B"],
        "description": description,
    }


class TestSeamTestsBlockingGateE2E:
    """Drive validate() the same way autobuild does."""

    def test_ac_005_player_skipped_seam_block_yields_feedback(
        self,
        tmp_worktree: Path,
        task_work_results_dir: Path,
    ) -> None:
        """AC-005: skipping a non-empty `## Seam Tests` block must reject."""
        _write_test_file(
            tmp_worktree,
            "tests/test_widget.py",
            "def test_widget(): assert True\n",  # NO marker
        )
        _write_results(
            task_work_results_dir,
            _passing_task_work_results(["tests/test_widget.py"]),
        )

        description = (
            "# Task: Widget\n\n"
            "## Description\n\nWidget syncs.\n\n"
            "## Seam Tests\n\n"
            "```python\n"
            "@pytest.mark.seam\n"
            "def test_widget_write_then_read():\n"
            "    persist(make_widget())\n"
            "    assert load_widget() is not None\n"
            "```\n"
        )

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout="15 passed", stderr=""
            )
            validator = CoachValidator(str(tmp_worktree))
            result = validator.validate(
                "TASK-001", 1, _make_task(description)
            )

        assert result.decision == "feedback"
        seam_issues = [
            i for i in result.issues
            if i["category"] == "seam_tests_unimplemented"
        ]
        assert len(seam_issues) == 1
        assert seam_issues[0]["severity"] == "must_fix"
        # AC-005: feedback must cite the stub by name or reference.
        assert "test_widget_write_then_read" in seam_issues[0]["description"]

    def test_ac_006_no_seam_section_yields_no_spurious_failure(
        self,
        tmp_worktree: Path,
        task_work_results_dir: Path,
    ) -> None:
        """AC-006: tasks without a Seam Tests section approve normally."""
        _write_test_file(
            tmp_worktree,
            "tests/test_plain.py",
            "def test_plain(): assert True\n",
        )
        _write_results(
            task_work_results_dir,
            _passing_task_work_results(["tests/test_plain.py"]),
        )

        description = (
            "# Task: Trivial\n\n## Description\n\nA trivial task.\n"
        )

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout="15 passed", stderr=""
            )
            validator = CoachValidator(str(tmp_worktree))
            result = validator.validate(
                "TASK-001", 1, _make_task(description)
            )

        # AC-006: no seam section → gate must not fire.
        seam_issues = [
            i for i in result.issues
            if i["category"] == "seam_tests_unimplemented"
        ]
        assert seam_issues == []

    def test_ac_007_seam_section_plus_marker_test_yields_approve(
        self,
        tmp_worktree: Path,
        task_work_results_dir: Path,
    ) -> None:
        """AC-007: contract honoured → normal approval."""
        _write_test_file(
            tmp_worktree,
            "tests/test_widget.py",
            (
                "import pytest\n\n"
                "@pytest.mark.seam\n"
                "def test_widget_write_then_read():\n"
                "    assert True\n"
            ),
        )
        _write_results(
            task_work_results_dir,
            _passing_task_work_results(["tests/test_widget.py"]),
        )

        description = (
            "## Seam Tests\n\n"
            "```python\n"
            "@pytest.mark.seam\n"
            "def test_widget_write_then_read():\n"
            "    ...\n"
            "```\n"
        )

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout="15 passed", stderr=""
            )
            validator = CoachValidator(str(tmp_worktree))
            result = validator.validate(
                "TASK-001", 1, _make_task(description)
            )

        assert result.decision == "approve"
        seam_issues = [
            i for i in result.issues
            if i["category"] == "seam_tests_unimplemented"
        ]
        assert seam_issues == []

    def test_empty_seam_section_does_not_trigger(
        self,
        tmp_worktree: Path,
        task_work_results_dir: Path,
    ) -> None:
        """AC-001: empty Seam Tests section (no stubs) is not a trigger."""
        _write_test_file(
            tmp_worktree,
            "tests/test_plain.py",
            "def test_plain(): assert True\n",
        )
        _write_results(
            task_work_results_dir,
            _passing_task_work_results(["tests/test_plain.py"]),
        )

        description = (
            "## Seam Tests\n"
            "\n"
            "## Out Of Scope\n"
            "\n"
            "Nothing.\n"
        )

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout="15 passed", stderr=""
            )
            validator = CoachValidator(str(tmp_worktree))
            result = validator.validate(
                "TASK-001", 1, _make_task(description)
            )

        # Empty section → no trigger, decision is approve.
        assert result.decision == "approve"
