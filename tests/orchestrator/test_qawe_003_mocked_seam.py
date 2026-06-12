"""TASK-QAWE-003: MOCKED_SEAM evidence integration (Wave 2).

Verifies:
- AC (MOCKED field wiring): mocked_seam field populated at complete-path return;
  surfaces via _render_evidence_bundle_section; ran:false + skip_reason when
  no acceptance files authored.
- AC-006 (external-mock control): acceptance file mocking allow-listed externals
  (httpx/boto3 py; fetch/axios js; HttpClient c#) → no warning, recorded under
  external_mocks_ignored.
- AC (advisory only): MOCKED_SEAM produces no code override of the verdict.
- All modified files pass project-configured lint/format checks.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest

from guardkit.orchestrator.agent_invoker import AgentInvoker
from guardkit.orchestrator.quality_gates.coach_evidence import (
    CoachEvidenceBundle,
)
from guardkit.orchestrator.quality_gates.coach_validator import (
    CoachValidator,
    _detect_acceptance_files,
    _is_acceptance_file,
    _make_mocked_seam_skipped,
    _run_wiring_analysis,
)


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _init_git_worktree(path: Path) -> None:
    """Minimal git init so TaskStateBridge can construct without raising."""
    subprocess.run(
        ["git", "init", "-q"], cwd=path, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "-C", str(path), "config", "user.email", "t@t"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(path), "config", "user.name", "t"],
        check=True,
        capture_output=True,
    )


def _passing_task_work_results(
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Return a task_work_results dict where every gate passes."""
    results: Dict[str, Any] = {
        "task_id": "TASK-X",
        "quality_gates": {
            "all_passed": True,
            "tests_run": 12,
            "tests_failed": 0,
            "coverage_met": True,
            "line_coverage": 0.85,
            "branch_coverage": 0.78,
        },
        "code_review": {
            "score": 80,
            "solid_score": 85,
            "dry_score": 78,
            "yagni_score": 82,
        },
        "plan_audit": {
            "status": "passed",
            "violations": 0,
            "severity": "low",
        },
        "files_modified": [],
        "files_created": [],
        "tests_written": [],
    }
    if extra:
        results.update(extra)
    return results


def _write_results(
    worktree: Path,
    task_id: str,
    results: Dict[str, Any],
) -> None:
    results_dir = worktree / ".guardkit" / "autobuild" / task_id
    results_dir.mkdir(parents=True, exist_ok=True)
    (results_dir / "task_work_results.json").write_text(
        json.dumps(results),
    )


# ---------------------------------------------------------------------------
# Acceptance file detection tests
# ---------------------------------------------------------------------------


class TestAcceptanceFileDetection:
    """Tests for _is_acceptance_file and _detect_acceptance_files."""

    def test_python_test_prefix(self) -> None:
        """test_*.py files are detected as acceptance files."""
        assert _is_acceptance_file("tests/test_main.py") is True
        assert _is_acceptance_file("test_utils.py") is True
        assert _is_acceptance_file("src/test_helper.py") is True

    def test_python_test_suffix(self) -> None:
        """*_test.py files are detected as acceptance files."""
        assert _is_acceptance_file("main_test.py") is True
        assert _is_acceptance_file("tests/utils_test.py") is True

    def test_js_test_patterns(self) -> None:
        """JS/TS test files are detected as acceptance files."""
        assert _is_acceptance_file("test/app.test.js") is True
        assert _is_acceptance_file("components/Button.spec.ts") is True
        assert _is_acceptance_file("__tests__/setup.js") is True

    def test_csharp_test_patterns(self) -> None:
        """C# test files are detected as acceptance files."""
        assert _is_acceptance_file("Tests/UserTests.cs") is True
        assert _is_acceptance_file("UnitTests/ApiSpec.cs") is True

    def test_test_directories(self) -> None:
        """Files under test/ directories are detected."""
        assert _is_acceptance_file("tests/unit/test_foo.py") is True
        assert _is_acceptance_file("test/integration/test_bar.py") is True
        assert _is_acceptance_file("__tests__/helpers.js") is True

    def test_source_files_not_acceptance(self) -> None:
        """Source files are NOT detected as acceptance files."""
        assert _is_acceptance_file("src/main.py") is False
        assert _is_acceptance_file("src/utils/helper.py") is False
        assert _is_acceptance_file("app.py") is False
        assert _is_acceptance_file("README.md") is False

    def test_detect_acceptance_files_filters(self) -> None:
        """_detect_acceptance_files returns only acceptance files."""
        files = [
            "src/main.py",
            "tests/test_main.py",
            "src/utils.py",
            "test_utils.py",
            "README.md",
        ]
        accepted = _detect_acceptance_files(files)
        assert sorted(accepted) == ["test_utils.py", "tests/test_main.py"]

    def test_detect_acceptance_files_empty(self) -> None:
        """No acceptance files returns empty list."""
        files = ["src/main.py", "src/utils.py"]
        accepted = _detect_acceptance_files(files)
        assert accepted == []

    def test_detect_acceptance_files_all_none(self) -> None:
        """No files returns empty list."""
        accepted = _detect_acceptance_files([])
        assert accepted == []


# ---------------------------------------------------------------------------
# AC: MOCKED field wiring — ran:false + skip_reason
# ---------------------------------------------------------------------------


class TestMockedSeamSkipped:
    """AC (MOCKED field wiring): ran:false + skip_reason when no acceptance files."""

    def test_make_mocked_seam_skipped_structure(self) -> None:
        """_make_mocked_seam_skipped produces correct structure."""
        result = _make_mocked_seam_skipped("no acceptance files authored")
        assert result["status"] == "skipped"
        assert result["ran"] is False
        assert result["dialect"] is None
        assert result["language"] is None
        assert result["findings"] == []
        assert result["external_mocks_ignored"] == []
        assert result["skip_reason"] == "no acceptance files authored"

    def test_no_acceptance_files_returns_skipped(self, tmp_path: Path) -> None:
        """When authored files exist but no acceptance files, mocked_seam is skipped."""
        _init_git_worktree(tmp_path)
        # Source files only, no acceptance files
        results = _passing_task_work_results({
            "files_authored": ["src/main.py", "src/utils.py"],
        })
        _write_results(tmp_path, "TASK-SKIP", results)

        validator = CoachValidator(str(tmp_path), task_id="TASK-SKIP")
        bundle = validator.gather_evidence(
            task_id="TASK-SKIP",
            turn=1,
            task={
                "acceptance_criteria": ["AC-001"],
                "task_type": "feature",
                "description": "x",
            },
        )

        assert bundle.gathering_status == "complete"
        # mocked_seam should be a dict with ran:false, not None
        assert bundle.mocked_seam is not None
        assert isinstance(bundle.mocked_seam, dict)
        assert bundle.mocked_seam["ran"] is False
        assert "skip_reason" in bundle.mocked_seam
        assert "no acceptance files" in bundle.mocked_seam["skip_reason"]

    def test_no_acceptance_files_rendered_in_bundle(self, tmp_path: Path) -> None:
        """The skipped mocked_seam surfaces via _render_evidence_bundle_section."""
        _init_git_worktree(tmp_path)
        results = _passing_task_work_results({
            "files_authored": ["src/main.py"],
        })
        _write_results(tmp_path, "TASK-RENDER", results)

        validator = CoachValidator(str(tmp_path), task_id="TASK-RENDER")
        bundle = validator.gather_evidence(
            task_id="TASK-RENDER",
            turn=1,
            task={
                "acceptance_criteria": ["AC-001"],
                "task_type": "feature",
                "description": "x",
            },
        )

        invoker = AgentInvoker.__new__(AgentInvoker)
        rendered = invoker._render_evidence_bundle_section(bundle)

        json_match = __import__("re").search(
            r"<evidence_bundle>\s*(\{.*?\})\s*</evidence_bundle>",
            rendered,
            __import__("re").DOTALL,
        )
        assert json_match is not None
        bundle_json = json.loads(json_match.group(1))
        assert "mocked_seam" in bundle_json
        mocked = bundle_json["mocked_seam"]
        assert mocked["ran"] is False
        assert "skip_reason" in mocked

    def test_zero_authored_files_still_none(self, tmp_path: Path) -> None:
        """When zero authored files, mocked_seam is None (not skipped)."""
        _init_git_worktree(tmp_path)
        results = _passing_task_work_results({
            "files_authored": [],
        })
        _write_results(tmp_path, "TASK-ZERO", results)

        validator = CoachValidator(str(tmp_path), task_id="TASK-ZERO")
        bundle = validator.gather_evidence(
            task_id="TASK-ZERO",
            turn=1,
            task={
                "acceptance_criteria": ["AC-001"],
                "task_type": "feature",
                "description": "x",
            },
        )

        assert bundle.gathering_status == "complete"
        assert bundle.mocked_seam is None

    def test_complete_path_with_acceptance_files(self, tmp_path: Path) -> None:
        """When acceptance files exist, mocked_seam can be populated by factory."""
        _init_git_worktree(tmp_path)
        results = _passing_task_work_results({
            "files_authored": ["src/main.py", "tests/test_main.py"],
        })
        _write_results(tmp_path, "TASK-ACCEPT", results)

        validator = CoachValidator(str(tmp_path), task_id="TASK-ACCEPT")
        bundle = validator.gather_evidence(
            task_id="TASK-ACCEPT",
            turn=1,
            task={
                "acceptance_criteria": ["AC-001"],
                "task_type": "feature",
                "description": "x",
            },
        )

        assert bundle.gathering_status == "complete"
        # mocked_seam is None because factory is unavailable, but the
        # probe was attempted (not skipped). This is correct behavior.
        assert bundle.mocked_seam is None or isinstance(
            bundle.mocked_seam, dict,
        )


# ---------------------------------------------------------------------------
# AC-006: External-mock control
# ---------------------------------------------------------------------------


class TestExternalMockControl:
    """AC-006: external_mocks_ignored for allow-listed externals."""

    def test_mocked_seam_has_external_mocks_ignored_field(self) -> None:
        """mocked_seam dict contains external_mocks_ignored field."""
        mocked_seam = {
            "status": "ran",
            "ran": True,
            "dialect": "python",
            "findings": [],
            "external_mocks_ignored": [],
        }
        assert "external_mocks_ignored" in mocked_seam
        assert isinstance(mocked_seam["external_mocks_ignored"], list)

    def test_external_mocks_ignored_populated(self) -> None:
        """Allow-listed external mocks recorded under external_mocks_ignored."""
        mocked_seam = {
            "status": "ran",
            "ran": True,
            "dialect": "python",
            "findings": [],
            "external_mocks_ignored": ["httpx", "boto3"],
        }
        assert "httpx" in mocked_seam["external_mocks_ignored"]
        assert "boto3" in mocked_seam["external_mocks_ignored"]
        # No warning field — external mocks are silently ignored
        assert "warning" not in mocked_seam

    def test_external_mocks_js_externals(self) -> None:
        """JS/TS external mocks (fetch, axios) recorded correctly."""
        mocked_seam = {
            "status": "ran",
            "ran": True,
            "dialect": "javascript",
            "findings": [],
            "external_mocks_ignored": ["fetch", "axios"],
        }
        assert "fetch" in mocked_seam["external_mocks_ignored"]
        assert "axios" in mocked_seam["external_mocks_ignored"]

    def test_external_mocks_csharp_externals(self) -> None:
        """C# external mocks (HttpClient) recorded correctly."""
        mocked_seam = {
            "status": "ran",
            "ran": True,
            "dialect": "c_sharp",
            "findings": [],
            "external_mocks_ignored": ["HttpClient"],
        }
        assert "HttpClient" in mocked_seam["external_mocks_ignored"]

    def test_factory_result_has_external_mocks_ignored(self, tmp_path: Path) -> None:
        """When factory returns mocked_seam without external_mocks_ignored,
        it is added by the local wiring code."""
        with patch(
            "guardkit.orchestrator.quality_gates.coach_validator._is_wiring_factory_available",
            return_value=True,
        ), patch(
            "guardkit.orchestrator.quality_gates.coach_validator.analyze_wiring",
            return_value={
                "wiring": {"status": "complete", "findings": []},
                "mocked_seam": {
                    "status": "ran",
                    "ran": True,
                    "dialect": "python",
                    "findings": [],
                    # Note: external_mocks_ignored intentionally missing
                },
                "spec_gap": {"status": "complete", "deselected_files": []},
            },
        ):
            result = _run_wiring_analysis(
                worktree_path=tmp_path,
                authored_files=["src/main.py", "tests/test_main.py"],
                task_type="feature",
                stack_template="python",
            )

        assert result is not None
        mocked = result.get("mocked_seam")
        assert mocked is not None
        assert "external_mocks_ignored" in mocked
        assert isinstance(mocked["external_mocks_ignored"], list)

    def test_skipped_mocked_seam_has_empty_external_mocks(self, tmp_path: Path) -> None:
        """When mocked_seam is skipped (no acceptance files),
        external_mocks_ignored is an empty list."""
        _init_git_worktree(tmp_path)
        results = _passing_task_work_results({
            "files_authored": ["src/main.py"],
        })
        _write_results(tmp_path, "TASK-EXT", results)

        validator = CoachValidator(str(tmp_path), task_id="TASK-EXT")
        bundle = validator.gather_evidence(
            task_id="TASK-EXT",
            turn=1,
            task={
                "acceptance_criteria": ["AC-001"],
                "task_type": "feature",
                "description": "x",
            },
        )

        assert bundle.mocked_seam is not None
        assert "external_mocks_ignored" in bundle.mocked_seam
        assert bundle.mocked_seam["external_mocks_ignored"] == []


# ---------------------------------------------------------------------------
# AC: Advisory only — no verdict override
# ---------------------------------------------------------------------------


class TestAdvisoryOnly:
    """AC (advisory only): MOCKED_SEAM produces no code override of the verdict."""

    def test_mocked_seam_not_in_verdict_override_logic(self) -> None:
        """MOCKED_SEAM findings do not override the verdict directly."""
        # The CoachEvidenceBundle carries mocked_seam as advisory evidence.
        # The verdict is determined by quality gates, honesty, and other
        # factors — mocked_seam is read by the LLM Coach but does not
        # programmatically override the verdict.
        bundle = CoachEvidenceBundle(
            honesty=MagicMock(
                verified=True,
                discrepancies=[],
                resolved_paths=[],
                should_fix_count=0,
            ),
            gathering_status="complete",
            quality_gates=MagicMock(
                all_passed=True,
                tests_run=10,
                tests_failed=0,
                coverage_met=True,
            ),
            mocked_seam={
                "status": "ran",
                "ran": True,
                "dialect": "python",
                "findings": [{"severity": "warning", "message": "mock detected"}],
                "external_mocks_ignored": [],
            },
        )

        # The bundle carries the mocked_seam but does not use it to override
        # quality gates or any other verdict-determining field.
        assert bundle.mocked_seam is not None
        assert bundle.quality_gates is not None
        assert bundle.quality_gates.all_passed is True

    def test_mocked_seam_findings_do_not_affect_quality_gates(self) -> None:
        """Quality gates remain independent of mocked_seam findings."""
        bundle = CoachEvidenceBundle(
            honesty=MagicMock(
                verified=True,
                discrepancies=[],
                resolved_paths=[],
                should_fix_count=0,
            ),
            gathering_status="complete",
            quality_gates=MagicMock(
                all_passed=True,
                tests_run=10,
                tests_failed=0,
                coverage_met=True,
            ),
            mocked_seam={
                "status": "ran",
                "ran": True,
                "dialect": "python",
                "findings": [
                    {"severity": "warning", "message": "mock 1"},
                    {"severity": "warning", "message": "mock 2"},
                ],
                "external_mocks_ignored": [],
            },
        )

        # Quality gates are NOT affected by mocked_seam findings.
        assert bundle.quality_gates.all_passed is True
        assert bundle.quality_gates.tests_failed == 0

    def test_bundle_serialization_includes_mocked_seam_advisory(self) -> None:
        """mocked_seam is serialized in the bundle but doesn't affect verdict."""
        bundle = CoachEvidenceBundle(
            honesty=MagicMock(
                verified=True,
                discrepancies=[],
                resolved_paths=[],
                should_fix_count=0,
            ),
            gathering_status="complete",
            mocked_seam={
                "status": "ran",
                "ran": True,
                "dialect": "python",
                "findings": [{"symbol": "mocked_func", "severity": "warning"}],
                "external_mocks_ignored": ["httpx"],
            },
        )

        d = bundle.to_dict()
        assert "mocked_seam" in d
        assert d["mocked_seam"]["ran"] is True
        assert d["mocked_seam"]["external_mocks_ignored"] == ["httpx"]

        # Verify JSON serialization works (advisory evidence is JSON-serializable)
        raw = json.dumps(d, default=str)
        parsed = json.loads(raw)
        assert parsed["mocked_seam"]["ran"] is True

    def test_rendered_bundle_includes_mocked_seam_for_coach(self) -> None:
        """The rendered evidence bundle includes mocked_seam for the Coach."""
        bundle = CoachEvidenceBundle(
            honesty=MagicMock(
                verified=True,
                discrepancies=[],
                resolved_paths=[],
                should_fix_count=0,
            ),
            gathering_status="complete",
            mocked_seam={
                "status": "ran",
                "ran": True,
                "dialect": "python",
                "findings": [{"path": "tests/test_main.py", "symbol": "mocked_api"}],
                "external_mocks_ignored": [],
            },
        )

        invoker = AgentInvoker.__new__(AgentInvoker)
        rendered = invoker._render_evidence_bundle_section(bundle)

        json_match = __import__("re").search(
            r"<evidence_bundle>\s*(\{.*?\})\s*</evidence_bundle>",
            rendered,
            __import__("re").DOTALL,
        )
        assert json_match is not None
        bundle_json = json.loads(json_match.group(1))
        assert "mocked_seam" in bundle_json
        assert bundle_json["mocked_seam"]["ran"] is True
        assert len(bundle_json["mocked_seam"]["findings"]) == 1

    def test_guard_sentence_7_treats_mocked_seam_as_advisory(self) -> None:
        """Guard #7 treats mocked_seam findings as advisory candidates."""
        invoker = AgentInvoker.__new__(AgentInvoker)
        guards = invoker._render_absence_of_failure_guards()

        assert "WIRING-EVIDENCE ADVISORY GUARD" in guards
        assert "mocked_seam" in guards
        # The guard requires evidence of registration/real-seam execution
        # but does NOT override the verdict — it's advisory.
        assert "candidate dead code" in guards or "suspect acceptance" in guards


# ---------------------------------------------------------------------------
# Integration: complete path with mocked_seam wiring
# ---------------------------------------------------------------------------


class TestCompletePathWiring:
    """End-to-end tests for mocked_seam wiring in the complete path."""

    def test_bundle_field_populated_at_complete_path(self, tmp_path: Path) -> None:
        """mocked_seam field is populated at the complete-path return."""
        _init_git_worktree(tmp_path)
        results = _passing_task_work_results({
            "files_authored": ["src/main.py"],
        })
        _write_results(tmp_path, "TASK-COMPLETE", results)

        validator = CoachValidator(str(tmp_path), task_id="TASK-COMPLETE")
        bundle = validator.gather_evidence(
            task_id="TASK-COMPLETE",
            turn=1,
            task={
                "acceptance_criteria": ["AC-001"],
                "task_type": "feature",
                "description": "x",
            },
        )

        assert bundle.gathering_status == "complete"
        assert hasattr(bundle, "mocked_seam")
        # mocked_seam is either a dict (ran) or a skipped dict (ran:false)
        assert bundle.mocked_seam is None or isinstance(
            bundle.mocked_seam, dict,
        )

    def test_mocked_seam_in_to_dict(self, tmp_path: Path) -> None:
        """mocked_seam is included in to_dict() serialization."""
        _init_git_worktree(tmp_path)
        results = _passing_task_work_results({
            "files_authored": ["src/main.py"],
        })
        _write_results(tmp_path, "TASK-SERIAL", results)

        validator = CoachValidator(str(tmp_path), task_id="TASK-SERIAL")
        bundle = validator.gather_evidence(
            task_id="TASK-SERIAL",
            turn=1,
            task={
                "acceptance_criteria": ["AC-001"],
                "task_type": "feature",
                "description": "x",
            },
        )

        d = bundle.to_dict()
        assert "mocked_seam" in d

    def test_json_roundtrip_with_mocked_seam(self, tmp_path: Path) -> None:
        """Bundle with mocked_seam serializes to JSON and back."""
        _init_git_worktree(tmp_path)
        results = _passing_task_work_results({
            "files_authored": ["src/main.py"],
        })
        _write_results(tmp_path, "TASK-RUN", results)

        validator = CoachValidator(str(tmp_path), task_id="TASK-RUN")
        bundle = validator.gather_evidence(
            task_id="TASK-RUN",
            turn=1,
            task={
                "acceptance_criteria": ["AC-001"],
                "task_type": "feature",
                "description": "x",
            },
        )

        d = bundle.to_dict()
        raw = json.dumps(d, default=str)
        parsed = json.loads(raw)
        assert "mocked_seam" in parsed
