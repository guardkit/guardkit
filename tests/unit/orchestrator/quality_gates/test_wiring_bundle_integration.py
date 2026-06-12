"""Wave-1 wiring bundle integration tests (TASK-QAWE-002).

Verifies:
- AC-002: three new Optional[Dict] fields on CoachEvidenceBundle
- AC-008: SCAFFOLDING/DOCUMENTATION task types → all three fields None
- AC-015: absent-vs-empty discipline (findings:[] vs None)
- AC-016: truncation of >20 findings
- AC-017: graceful import absence (factory unavailable → all None)
- Guard sentence #7 in _render_absence_of_failure_guards
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from guardkit.orchestrator.agent_invoker import AgentInvoker
from guardkit.orchestrator.quality_gates.coach_evidence import (
    CoachEvidenceBundle,
    GatheringStatus,
)
from guardkit.orchestrator.quality_gates.coach_validator import (
    CoachValidator,
    _compute_authored_set,
    _run_wiring_analysis,
    _is_wiring_factory_available,
    _reset_wiring_factory_cache,
)


# ---------------------------------------------------------------------------
# AC-002: Bundle fields exist and serialise
# ---------------------------------------------------------------------------


class TestBundleFields:
    """AC-002: wiring, mocked_seam, spec_gap fields on CoachEvidenceBundle."""

    def test_fields_exist(self) -> None:
        """All three wiring fields are present on the dataclass."""
        bundle = CoachEvidenceBundle(honesty=MagicMock(verified=True))
        assert hasattr(bundle, "wiring")
        assert hasattr(bundle, "mocked_seam")
        assert hasattr(bundle, "spec_gap")

    def test_defaults_are_none(self) -> None:
        """By default all three fields are None."""
        bundle = CoachEvidenceBundle(honesty=MagicMock(verified=True))
        assert bundle.wiring is None
        assert bundle.mocked_seam is None
        assert bundle.spec_gap is None

    def test_serialisation_with_dict_values(self) -> None:
        """to_dict() serialises dict values via asdict."""
        bundle = CoachEvidenceBundle(
            honesty=MagicMock(verified=True),
            wiring={"status": "complete", "findings": []},
            mocked_seam={"status": "ran", "findings": []},
            spec_gap={"status": "complete", "findings": []},
        )
        d = bundle.to_dict()
        assert d["wiring"] == {"status": "complete", "findings": []}
        assert d["mocked_seam"] == {"status": "ran", "findings": []}
        assert d["spec_gap"] == {"status": "complete", "findings": []}

    def test_serialisation_with_none_values(self) -> None:
        """to_dict() serialises None values as null."""
        bundle = CoachEvidenceBundle(
            honesty=MagicMock(verified=True),
            wiring=None,
            mocked_seam=None,
            spec_gap=None,
        )
        d = bundle.to_dict()
        assert d["wiring"] is None
        assert d["mocked_seam"] is None
        assert d["spec_gap"] is None

    def test_json_roundtrip(self) -> None:
        """Bundle serialises to JSON and back."""
        bundle = CoachEvidenceBundle(
            honesty=MagicMock(verified=True),
            gathering_status="complete",
            wiring={"status": "complete", "findings": [{"symbol": "foo"}]},
            mocked_seam=None,
            spec_gap=None,
        )
        d = bundle.to_dict()
        raw = json.dumps(d, default=str)
        parsed = json.loads(raw)
        assert parsed["wiring"]["status"] == "complete"
        assert parsed["wiring"]["findings"] == [{"symbol": "foo"}]
        assert parsed["mocked_seam"] is None


# ---------------------------------------------------------------------------
# AC-015: absent-vs-empty discipline
# ---------------------------------------------------------------------------


class TestAbsentVsEmpty:
    """AC-015: findings:[] with positive status is distinct from None."""

    def test_empty_findings_vs_none(self) -> None:
        """Empty findings list is distinct from the field being None."""
        bundle = CoachEvidenceBundle(
            honesty=MagicMock(verified=True),
            wiring={"status": "complete", "findings": []},
            mocked_seam=None,
            spec_gap=None,
        )
        d = bundle.to_dict()
        # wiring is a dict with empty findings, not None
        assert d["wiring"] is not None
        assert d["wiring"]["findings"] == []
        # mocked_seam is None (probe did not run)
        assert d["mocked_seam"] is None


# ---------------------------------------------------------------------------
# AC-017: Graceful import absence
# ---------------------------------------------------------------------------


class TestGracefulImportAbsence:
    """AC-017: with guardkitfactory absent, gather_evidence does not crash."""

    def test_factory_unavailable_returns_none_fields(self) -> None:
        """When factory is unavailable, _run_wiring_analysis returns None."""
        with patch(
            "guardkit.orchestrator.quality_gates.coach_validator."
            "_is_wiring_factory_available",
            return_value=False,
        ):
            result = _run_wiring_analysis(
                worktree_path=Path("/tmp"),
                authored_files=["src/main.py"],
                task_type="feature",
                stack_template="python",
            )
        assert result is None

    def test_scaffolding_task_gates_out(self) -> None:
        """AC-008: SCAFFOLDING task → all three fields None."""
        with patch(
            "guardkit.orchestrator.quality_gates.coach_validator."
            "_is_wiring_factory_available",
            return_value=True,
        ):
            result = _run_wiring_analysis(
                worktree_path=Path("/tmp"),
                authored_files=["src/main.py"],
                task_type="scaffolding",
                stack_template="python",
            )
        assert result is None

    def test_documentation_task_gates_out(self) -> None:
        """AC-008: DOCUMENTATION task → all three fields None."""
        with patch(
            "guardkit.orchestrator.quality_gates.coach_validator."
            "_is_wiring_factory_available",
            return_value=True,
        ):
            result = _run_wiring_analysis(
                worktree_path=Path("/tmp"),
                authored_files=["docs/readme.md"],
                task_type="documentation",
                stack_template="python",
            )
        assert result is None

    def test_zero_authored_targets_gates_out(self) -> None:
        """Zero-authored-targets → all three fields None."""
        with patch(
            "guardkit.orchestrator.quality_gates.coach_validator."
            "_is_wiring_factory_available",
            return_value=True,
        ):
            result = _run_wiring_analysis(
                worktree_path=Path("/tmp"),
                authored_files=[],
                task_type="feature",
                stack_template="python",
            )
        assert result is None


# ---------------------------------------------------------------------------
# _compute_authored_set helper
# ---------------------------------------------------------------------------


class TestComputeAuthoredSet:
    """Verify the authored-set extraction logic."""

    def test_files_authored_takes_precedence(self) -> None:
        """files_authored key is used when present."""
        results = {
            "files_authored": ["src/a.py", "src/b.py"],
            "files_created": ["src/c.py"],
            "files_modified": ["src/d.py"],
        }
        authored = _compute_authored_set(results)
        assert authored == ["src/a.py", "src/b.py"]

    def test_fallback_to_created_modified(self) -> None:
        """Without files_authored, falls back to created ∪ modified."""
        results = {
            "files_created": ["src/a.py", "src/b.py"],
            "files_modified": ["src/c.py", "src/b.py"],  # b.py in both
        }
        authored = _compute_authored_set(results)
        # b.py should appear only once
        assert "src/a.py" in authored
        assert "src/b.py" in authored
        assert "src/c.py" in authored
        assert len(authored) == 3

    def test_empty_results(self) -> None:
        """Empty results → empty list."""
        authored = _compute_authored_set({})
        assert authored == []


# ---------------------------------------------------------------------------
# AC-016: Truncation of findings
# ---------------------------------------------------------------------------


class TestFindingsTruncation:
    """AC-016: >20 findings → first 20 + '... and N more'."""

    def test_truncate_findings_under_limit(self) -> None:
        """Findings under the limit pass through unchanged."""
        container = {"findings": [{"id": i} for i in range(10)]}
        AgentInvoker._truncate_findings(container, 20)
        assert len(container["findings"]) == 10

    def test_truncate_findings_over_limit(self) -> None:
        """Findings over the limit are truncated with marker."""
        container = {"findings": [{"id": i} for i in range(25)]}
        AgentInvoker._truncate_findings(container, 20)
        assert len(container["findings"]) == 21  # 20 + marker
        assert container["findings"][20] == "... and 5 more (truncated for token budget)"

    def test_truncate_findings_none_container(self) -> None:
        """None container is a no-op."""
        AgentInvoker._truncate_findings(None, 20)  # should not raise

    def test_truncate_findings_no_findings_key(self) -> None:
        """Container without 'findings' key is a no-op."""
        container = {"status": "complete"}
        AgentInvoker._truncate_findings(container, 20)
        assert "findings" not in container

    def test_truncate_findings_empty_findings(self) -> None:
        """Empty findings list passes through unchanged."""
        container = {"findings": []}
        AgentInvoker._truncate_findings(container, 20)
        assert container["findings"] == []


# ---------------------------------------------------------------------------
# Guard sentence #7
# ---------------------------------------------------------------------------


class TestGuardSentence7:
    """AC-016: advisory guard sentence #7 in _render_absence_of_failure_guards."""

    def test_guard_7_present(self) -> None:
        """Guard sentence #7 appears in the guards output."""
        invoker = AgentInvoker("/tmp")
        guards = invoker._render_absence_of_failure_guards()
        assert "7." in guards
        assert "WIRING-EVIDENCE ADVISORY GUARD" in guards
        assert "wiring" in guards
        assert "mocked_seam" in guards
        assert "spec_gap" in guards

    def test_six_existing_guards_still_present(self) -> None:
        """All six original guards are still present."""
        invoker = AgentInvoker("/tmp")
        guards = invoker._render_absence_of_failure_guards()
        for i in range(1, 7):
            assert f"{i}." in guards


# ---------------------------------------------------------------------------
# CoachValidator.gather_evidence wiring integration
# ---------------------------------------------------------------------------


class TestGatherEvidenceWiring:
    """Verify wiring fields in gather_evidence output."""

    @pytest.fixture
    def mock_honesty(self) -> MagicMock:
        """A HonestyVerification mock that passes."""
        mock = MagicMock()
        mock.verified = True
        mock.discrepancies = []
        mock.resolved_paths = []
        mock.honesty_score = 1.0
        return mock

    def _passing_results(self) -> dict:
        """Task-work results where every gate passes."""
        return {
            "task_id": "TASK-W1",
            "quality_gates": {
                "all_passed": True,
                "tests_run": 5,
                "tests_failed": 0,
                "coverage_met": True,
            },
            "code_review": {"score": 80},
            "plan_audit": {"status": "passed"},
            "files_created": ["src/example.py"],
            "files_modified": [],
        }

    def _make_worktree(self, tmp_path: Path) -> Path:
        """Create a minimal git worktree with task_work_results."""
        import subprocess
        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True,
                       capture_output=True)
        subprocess.run(
            ["git", "-C", str(tmp_path), "config", "user.email", "t@t"],
            check=True, capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(tmp_path), "config", "user.name", "t"],
            check=True, capture_output=True,
        )
        results_dir = tmp_path / ".guardkit" / "autobuild" / "TASK-W1"
        results_dir.mkdir(parents=True, exist_ok=True)
        import json
        (results_dir / "task_work_results.json").write_text(
            json.dumps(self._passing_results())
        )
        return tmp_path

    def test_wiring_fields_none_when_factory_unavailable(
        self, tmp_path: Path, mock_honesty: MagicMock,
    ) -> None:
        """When factory unavailable, gather_evidence returns None for wiring fields."""
        worktree = self._make_worktree(tmp_path)
        validator = CoachValidator(str(worktree))
        task = {
            "acceptance_criteria": ["AC-1"],
            "task_type": "feature",
        }
        with patch.object(
            CoachValidator, "_verify_honesty", return_value=mock_honesty,
        ), patch(
            "guardkit.orchestrator.quality_gates.coach_validator."
            "_is_wiring_factory_available",
            return_value=False,
        ), patch(
            "guardkit.orchestrator.quality_gates.coach_validator."
            "_compute_authored_set",
            return_value=["src/example.py"],
        ):
            bundle = validator.gather_evidence(
                task_id="TASK-W1", turn=1, task=task,
            )
        assert bundle.wiring is None
        assert bundle.mocked_seam is None
        assert bundle.spec_gap is None

    def test_scaffolding_task_returns_none_wiring_fields(
        self, tmp_path: Path, mock_honesty: MagicMock,
    ) -> None:
        """AC-008: SCAFFOLDING task → wiring fields are None."""
        worktree = self._make_worktree(tmp_path)
        validator = CoachValidator(str(worktree))
        task = {
            "acceptance_criteria": ["AC-1"],
            "task_type": "scaffolding",
        }
        with patch.object(
            CoachValidator, "_verify_honesty", return_value=mock_honesty,
        ), patch(
            "guardkit.orchestrator.quality_gates.coach_validator."
            "_is_wiring_factory_available",
            return_value=True,
        ), patch(
            "guardkit.orchestrator.quality_gates.coach_validator."
            "_compute_authored_set",
            return_value=["src/example.py"],
        ):
            bundle = validator.gather_evidence(
                task_id="TASK-W1", turn=1, task=task,
            )
        assert bundle.wiring is None
        assert bundle.mocked_seam is None
        assert bundle.spec_gap is None
