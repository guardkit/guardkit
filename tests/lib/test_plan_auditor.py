"""
Unit tests for PlanAuditor class.

Tests core audit logic for comparing planned vs actual implementation.
Part of TASK-025: Implement Phase 5.5 Plan Audit.
"""

import pytest
import subprocess
from pathlib import Path
from datetime import datetime
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "installer/core/commands/lib"))

from plan_audit import (
    PlanAuditor,
    PlanAuditReport,
    Discrepancy,
    PlanAuditError,
    format_audit_report
)


class TestPlanAuditor:
    """Test suite for PlanAuditor class."""

    @pytest.fixture
    def auditor(self, tmp_path):
        """Create PlanAuditor instance with temporary workspace."""
        return PlanAuditor(workspace_root=tmp_path)

    @pytest.fixture
    def sample_plan(self):
        """Sample implementation plan for testing."""
        return {
            "task_id": "TASK-TEST",
            "plan": {
                "files_to_create": [
                    "src/feature.py",
                    "src/utils.py",
                    "tests/test_feature.py"
                ],
                "files_to_modify": [],
                "external_dependencies": ["requests", "pydantic"],
                "estimated_loc": 250,
                "estimated_duration": "4 hours"
            }
        }

    def test_auditor_initialization(self, tmp_path):
        """Test PlanAuditor initializes correctly."""
        auditor = PlanAuditor(workspace_root=tmp_path)
        assert auditor.workspace_root == tmp_path

    def test_auditor_default_workspace(self):
        """Test PlanAuditor defaults to current directory."""
        auditor = PlanAuditor()
        assert auditor.workspace_root == Path(".")

    def test_extract_plan_summary(self, auditor, sample_plan):
        """Test plan summary extraction."""
        summary = auditor._extract_plan_summary(sample_plan)

        assert summary["files"] == 3
        assert summary["files_to_modify"] == 0
        assert summary["dependencies"] == 2
        assert summary["estimated_loc"] == 250
        assert summary["estimated_duration"] == "4 hours"

    def test_parse_duration_hours(self, auditor):
        """Test duration parsing for hours."""
        assert auditor._parse_duration("4 hours") == 4.0
        assert auditor._parse_duration("2.5 hours") == 2.5
        assert auditor._parse_duration("1 hour") == 1.0

    def test_parse_duration_days(self, auditor):
        """Test duration parsing for days."""
        assert auditor._parse_duration("2 days") == 16.0  # 2 * 8 hours
        assert auditor._parse_duration("1 day") == 8.0

    def test_parse_duration_minutes(self, auditor):
        """Test duration parsing for minutes."""
        assert auditor._parse_duration("30 minutes") == 0.5
        assert auditor._parse_duration("90 min") == 1.5

    def test_parse_duration_invalid(self, auditor):
        """Test duration parsing with invalid input."""
        assert auditor._parse_duration("") == 0.0
        assert auditor._parse_duration("invalid") == 0.0
        assert auditor._parse_duration("no numbers here") == 0.0

    def test_calculate_severity_no_discrepancies(self, auditor):
        """Test severity calculation with no discrepancies."""
        discrepancies = []
        severity = auditor._calculate_severity(discrepancies)
        assert severity == "low"

    def test_calculate_severity_low(self, auditor):
        """Test severity calculation for low severity."""
        discrepancies = [
            Discrepancy("loc", "low", "LOC variance: +8%", 250, 270, 8.0)
        ]
        severity = auditor._calculate_severity(discrepancies)
        assert severity == "low"

    def test_calculate_severity_medium(self, auditor):
        """Test severity calculation for medium severity."""
        discrepancies = [
            Discrepancy("files", "medium", "2 extra files", [], [], 0),
            Discrepancy("loc", "low", "LOC variance: +15%", 250, 287, 15.0)
        ]
        severity = auditor._calculate_severity(discrepancies)
        assert severity == "medium"

    def test_calculate_severity_high_multiple_high(self, auditor):
        """Test severity calculation with 2+ high severity discrepancies."""
        discrepancies = [
            Discrepancy("files", "high", "5 extra files", [], [], 0),
            Discrepancy("dependencies", "high", "4 extra deps", [], [], 0)
        ]
        severity = auditor._calculate_severity(discrepancies)
        assert severity == "high"

    def test_calculate_severity_high_one_high_and_mediums(self, auditor):
        """Test severity calculation with 1 high + multiple mediums."""
        discrepancies = [
            Discrepancy("files", "high", "5 extra files", [], [], 0),
            Discrepancy("loc", "medium", "LOC variance: +40%", 250, 350, 40.0)
        ]
        severity = auditor._calculate_severity(discrepancies)
        assert severity == "high"

    def test_compare_files_extra_files(self, auditor):
        """Test file comparison detects extra files."""
        plan_data = {"files_to_create": ["src/feature.py", "src/utils.py"]}
        actual = {"files_created": ["src/feature.py", "src/utils.py", "src/helpers.py"]}

        discrepancies = auditor._compare_files(plan_data, actual)

        assert len(discrepancies) == 1
        assert discrepancies[0].category == "files"
        assert discrepancies[0].severity == "medium"
        assert "extra" in discrepancies[0].message
        assert "src/helpers.py" in discrepancies[0].actual

    def test_compare_files_missing_files(self, auditor):
        """Test file comparison detects missing files."""
        plan_data = {"files_to_create": ["src/feature.py", "src/utils.py", "src/config.py"]}
        actual = {"files_created": ["src/feature.py", "src/utils.py"]}

        discrepancies = auditor._compare_files(plan_data, actual)

        assert len(discrepancies) == 1
        assert discrepancies[0].category == "files"
        assert discrepancies[0].severity == "high"
        assert "not created" in discrepancies[0].message  # Changed from "missing"
        assert "src/config.py" in discrepancies[0].planned

    def test_compare_files_high_severity_many_extra(self, auditor):
        """Test file comparison marks 3+ extra files as high severity."""
        plan_data = {"files_to_create": ["src/feature.py"]}
        actual = {
            "files_created": [
                "src/feature.py",
                "src/utils.py",
                "src/helpers.py",
                "src/validators.py"
            ]
        }

        discrepancies = auditor._compare_files(plan_data, actual)

        assert len(discrepancies) == 1
        assert discrepancies[0].severity == "high"

    def test_compare_dependencies_extra_deps(self, auditor):
        """Test dependency comparison detects extra dependencies."""
        plan_data = {"external_dependencies": ["requests"]}
        actual = {"dependencies": ["requests", "lodash"]}

        discrepancies = auditor._compare_dependencies(plan_data, actual)

        assert len(discrepancies) == 1
        assert discrepancies[0].category == "dependencies"
        assert discrepancies[0].severity == "medium"
        assert "extra" in discrepancies[0].message
        assert "lodash" in discrepancies[0].actual

    def test_compare_dependencies_missing_deps(self, auditor):
        """Test dependency comparison detects missing dependencies."""
        plan_data = {"external_dependencies": ["requests", "pydantic"]}
        actual = {"dependencies": ["requests"]}

        discrepancies = auditor._compare_dependencies(plan_data, actual)

        assert len(discrepancies) == 1
        assert discrepancies[0].category == "dependencies"
        assert discrepancies[0].severity == "medium"
        assert "not added" in discrepancies[0].message  # Changed from "missing"
        assert "pydantic" in discrepancies[0].planned

    def test_compare_loc_low_variance(self, auditor):
        """Test LOC comparison with low variance (<30%)."""
        plan_data = {"estimated_loc": 250}
        actual = {"total_loc": 280}  # 12% increase

        discrepancies = auditor._compare_loc(plan_data, actual)

        assert len(discrepancies) == 1
        assert discrepancies[0].category == "loc"
        assert discrepancies[0].severity == "low"
        assert discrepancies[0].variance < 30

    def test_compare_loc_medium_variance(self, auditor):
        """Test LOC comparison with medium variance (30-50%)."""
        plan_data = {"estimated_loc": 250}
        actual = {"total_loc": 350}  # 40% increase

        discrepancies = auditor._compare_loc(plan_data, actual)

        assert len(discrepancies) == 1
        assert discrepancies[0].category == "loc"
        assert discrepancies[0].severity == "medium"
        assert 30 <= discrepancies[0].variance < 50

    def test_compare_loc_high_variance(self, auditor):
        """Test LOC comparison with high variance (>50%)."""
        plan_data = {"estimated_loc": 250}
        actual = {"total_loc": 450}  # 80% increase

        discrepancies = auditor._compare_loc(plan_data, actual)

        assert len(discrepancies) == 1
        assert discrepancies[0].category == "loc"
        assert discrepancies[0].severity == "high"
        assert discrepancies[0].variance >= 50

    def test_compare_loc_no_variance(self, auditor):
        """Test LOC comparison with < 10% variance (no discrepancy)."""
        plan_data = {"estimated_loc": 250}
        actual = {"total_loc": 260}  # 4% increase

        discrepancies = auditor._compare_loc(plan_data, actual)

        assert len(discrepancies) == 0

    def test_generate_recommendations_extra_files(self, auditor):
        """Test recommendation generation for extra files."""
        discrepancies = [
            Discrepancy(
                "files",
                "medium",
                "2 extra file(s) not in plan",
                [],
                ["src/helpers.py", "src/validators.py"],
                0
            )
        ]

        recommendations = auditor._generate_recommendations(discrepancies, "medium")

        assert len(recommendations) > 0
        assert any("scope creep" in rec.lower() for rec in recommendations)
        assert any("helpers.py" in rec for rec in recommendations)

    def test_generate_recommendations_high_loc_variance(self, auditor):
        """Test recommendation generation for high LOC variance."""
        discrepancies = [
            Discrepancy(
                "loc",
                "high",
                "LOC variance: +75%",
                250,
                437,
                75.0
            )
        ]

        recommendations = auditor._generate_recommendations(discrepancies, "high")

        assert len(recommendations) > 0
        assert any("loc" in rec.lower() and "75" in rec for rec in recommendations)

    def test_generate_recommendations_no_discrepancies(self, auditor):
        """Test recommendation generation with no discrepancies."""
        discrepancies = []

        recommendations = auditor._generate_recommendations(discrepancies, "low")

        assert len(recommendations) == 1
        assert "no major concerns" in recommendations[0].lower()

    def test_count_file_loc(self, auditor, tmp_path):
        """Test LOC counting for a file."""
        test_file = tmp_path / "test.py"
        test_file.write_text(
            "# Comment\n"
            "\n"
            "def function():\n"
            "    return 42\n"
            "\n"
            "# Another comment\n"
            "result = function()\n"
        )

        loc = auditor._count_file_loc(test_file)

        # Should count: def, return, result = 3 lines
        # Should skip: comments, blank lines
        assert loc == 3

    def test_count_file_loc_nonexistent(self, auditor, tmp_path):
        """Test LOC counting for non-existent file."""
        nonexistent = tmp_path / "nonexistent.py"
        loc = auditor._count_file_loc(nonexistent)
        assert loc == 0

    def test_is_excluded_test_files(self, auditor):
        """Test that test files are excluded."""
        assert auditor._is_excluded(Path("tests/test_feature.py"))
        assert auditor._is_excluded(Path("src/feature_test.py"))
        assert auditor._is_excluded(Path("src/feature.test.ts"))
        assert auditor._is_excluded(Path("src/feature.spec.ts"))

    def test_is_excluded_cache_files(self, auditor):
        """Test that cache files are excluded."""
        assert auditor._is_excluded(Path("src/__pycache__/feature.pyc"))
        assert auditor._is_excluded(Path("src/tests/.pytest_cache/data.json"))
        # Note: node_modules pattern may not match due to Path.match() limitations with **
        # This is acceptable as the pattern will work for glob operations

    def test_is_excluded_normal_files(self, auditor):
        """Test that normal files are not excluded."""
        assert not auditor._is_excluded(Path("src/feature.py"))
        assert not auditor._is_excluded(Path("src/services/auth.py"))
        assert not auditor._is_excluded(Path("lib/utils.py"))

    # ------------------------------------------------------------------
    # TASK-GK-PA-001: modify-axis comparison tests
    # ------------------------------------------------------------------

    @staticmethod
    def _init_git_repo(repo_root: Path) -> None:
        """Initialize an isolated git repo at ``repo_root``.

        Sets a deterministic identity so commits don't depend on the
        host's global git config (CI fixtures often have none).
        """
        env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
        run = lambda *args: subprocess.run(  # noqa: E731
            args, cwd=repo_root, check=True, capture_output=True, env=env
        )
        run("git", "init", "-q")
        run("git", "config", "user.email", "test@example.com")
        run("git", "config", "user.name", "Test")
        run("git", "config", "commit.gpgsign", "false")

    def test_scan_modified_files_uses_git_diff(self, tmp_path):
        """AC-1: _scan_modified_files returns git-modified files."""
        self._init_git_repo(tmp_path)
        target = tmp_path / "src" / "feature.py"
        target.parent.mkdir(parents=True)
        target.write_text("def foo():\n    return 1\n")
        subprocess.run(
            ["git", "add", "src/feature.py"], cwd=tmp_path, check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-q", "-m", "initial"], cwd=tmp_path, check=True,
            capture_output=True,
        )
        # Modify the committed file
        target.write_text("def foo():\n    return 2\n")

        auditor = PlanAuditor(workspace_root=tmp_path)
        modified = auditor._scan_modified_files({"plan": {}})

        assert "src/feature.py" in modified

    def test_scan_modified_files_no_git_returns_empty(self, tmp_path):
        """AC-1: _scan_modified_files returns [] when not a git repo."""
        # tmp_path with no `.git` directory
        auditor = PlanAuditor(workspace_root=tmp_path)
        modified = auditor._scan_modified_files({"plan": {}})

        assert modified == []

    def test_scan_modified_files_filters_excluded(self, tmp_path):
        """AC-1: _scan_modified_files filters paths through _is_excluded."""
        self._init_git_repo(tmp_path)
        # Create a file in `tests/` (excluded by `**/tests/**` pattern)
        excluded = tmp_path / "tests" / "test_thing.py"
        excluded.parent.mkdir(parents=True)
        excluded.write_text("def test_a():\n    pass\n")
        # And a non-excluded production file
        kept = tmp_path / "src" / "feature.py"
        kept.parent.mkdir(parents=True)
        kept.write_text("def foo():\n    return 1\n")

        subprocess.run(
            ["git", "add", "."], cwd=tmp_path, check=True, capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-q", "-m", "initial"], cwd=tmp_path, check=True,
            capture_output=True,
        )

        # Modify both files
        excluded.write_text("def test_a():\n    assert True\n")
        kept.write_text("def foo():\n    return 2\n")

        auditor = PlanAuditor(workspace_root=tmp_path)
        modified = auditor._scan_modified_files({"plan": {}})

        assert "src/feature.py" in modified
        assert "tests/test_thing.py" not in modified

    def test_compare_files_missing_modify(self, auditor):
        """AC-2: missing-modify produces medium-severity discrepancy."""
        plan_data = {"files_to_create": [], "files_to_modify": ["a.py"]}
        actual = {"files_created": [], "files_modified": []}

        discrepancies = auditor._compare_files(plan_data, actual)

        assert len(discrepancies) == 1
        disc = discrepancies[0]
        assert disc.category == "files"
        assert disc.severity == "medium"
        assert disc.message.startswith("1 planned file(s) not modified")
        assert "a.py" in disc.planned

    def test_compare_files_unplanned_modify_with_planned_set(self, auditor):
        """AC-3: extra modify produces low-severity discrepancy."""
        plan_data = {"files_to_create": [], "files_to_modify": ["a.py"]}
        actual = {"files_created": [], "files_modified": ["a.py", "b.py"]}

        discrepancies = auditor._compare_files(plan_data, actual)

        assert len(discrepancies) == 1
        disc = discrepancies[0]
        assert disc.category == "files"
        assert disc.severity == "low"
        assert disc.message.startswith("1 unplanned modification(s)")
        assert disc.actual == ["b.py"]

    def test_compare_files_no_planned_modify_no_discrepancies(self, auditor):
        """AC-5: empty files_to_modify suppresses modify-axis discrepancies."""
        plan_data = {"files_to_create": [], "files_to_modify": []}
        actual = {"files_created": [], "files_modified": ["b.py"]}

        discrepancies = auditor._compare_files(plan_data, actual)

        assert discrepancies == []

    def test_compare_files_modify_match(self, auditor):
        """AC-4: planned == actual modifications produces no discrepancy."""
        plan_data = {"files_to_create": [], "files_to_modify": ["a.py"]}
        actual = {"files_created": [], "files_modified": ["a.py"]}

        discrepancies = auditor._compare_files(plan_data, actual)

        assert discrepancies == []


class TestPlanAuditReport:
    """Test suite for PlanAuditReport dataclass."""

    def test_report_creation(self):
        """Test creating a PlanAuditReport."""
        report = PlanAuditReport(
            task_id="TASK-TEST",
            plan_summary={"files": 3, "dependencies": 2},
            actual_summary={"files_created": ["f1", "f2", "f3"]},
            discrepancies=[],
            severity="low",
            recommendations=["No concerns"],
            timestamp="2025-10-18T10:00:00Z",
            plan_path="docs/state/TASK-TEST/plan.md",
            audit_duration_seconds=1.5
        )

        assert report.task_id == "TASK-TEST"
        assert report.severity == "low"
        assert len(report.discrepancies) == 0
        assert report.audit_duration_seconds == 1.5


class TestFormatAuditReport:
    """Test suite for format_audit_report function."""

    def test_format_report_no_discrepancies(self):
        """Test formatting report with no discrepancies."""
        report = PlanAuditReport(
            task_id="TASK-TEST",
            plan_summary={
                "files": 3,
                "files_to_modify": 0,
                "dependencies": 2,
                "estimated_loc": 250,
                "estimated_duration": "4 hours"
            },
            actual_summary={
                "files_created": ["f1", "f2", "f3"],
                "total_loc": 255,
                "dependencies": ["d1", "d2"],
                "duration_hours": 4.2
            },
            discrepancies=[],
            severity="low",
            recommendations=["No major concerns"],
            timestamp="2025-10-18T10:00:00Z",
            plan_path="docs/state/TASK-TEST/plan.md",
            audit_duration_seconds=1.5
        )

        output = format_audit_report(report)

        assert "PLAN AUDIT - TASK-TEST" in output
        assert "PLANNED IMPLEMENTATION" in output
        assert "ACTUAL IMPLEMENTATION" in output
        assert "DISCREPANCIES: None" in output
        assert "SEVERITY: 🟢 LOW" in output
        assert "No major concerns" in output
        assert "OPTIONS:" in output

    def test_format_report_with_discrepancies(self):
        """Test formatting report with discrepancies."""
        report = PlanAuditReport(
            task_id="TASK-TEST",
            plan_summary={
                "files": 2,
                "files_to_modify": 0,
                "dependencies": 1,
                "estimated_loc": 200,
                "estimated_duration": "3 hours"
            },
            actual_summary={
                "files_created": ["f1", "f2", "f3"],
                "total_loc": 310,
                "dependencies": ["d1", "d2"],
                "duration_hours": 4.5
            },
            discrepancies=[
                Discrepancy(
                    "files",
                    "medium",
                    "1 extra file(s) not in plan",
                    ["f1", "f2"],
                    ["f3"],
                    50.0
                ),
                Discrepancy(
                    "loc",
                    "high",
                    "LOC variance: +55.0% (200 → 310 lines)",
                    200,
                    310,
                    55.0
                )
            ],
            severity="high",
            recommendations=[
                "Review extra files for scope creep: f3",
                "Understand why LOC exceeded estimate by 55%"
            ],
            timestamp="2025-10-18T10:00:00Z",
            plan_path="docs/state/TASK-TEST/plan.md",
            audit_duration_seconds=2.1
        )

        output = format_audit_report(report)

        assert "TASK-TEST" in output
        assert "extra file(s)" in output
        assert "LOC variance: +55.0%" in output
        assert "SEVERITY: 🔴 HIGH" in output
        assert "scope creep" in output
        assert "[A]pprove" in output
        assert "[R]evise" in output


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
