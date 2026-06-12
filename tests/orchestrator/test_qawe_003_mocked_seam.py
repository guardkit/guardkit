"""TASK-QAWE-003: MOCKED_SEAM evidence integration (Wave 2).

Verifies:
- AC (MOCKED field wiring): mocked_seam extracted from the FACTORY result
  shape (nested under "mocked_seam" in the flat wiring dict) and populated
  at the complete-path return; surfaces via _render_evidence_bundle_section.
- AC-006 (external-mock control): external_mocks_ignored always present on
  a populated mocked_seam dict.
- AC (advisory only): MOCKED_SEAM produces no code override of the verdict.
- The UNWIRED probe is NOT gated on acceptance files (the factory decides
  the mocked_seam skip internally; guardkit never pre-gates the call).

All analyze_wiring stubs in this module encode the REAL factory return
shape: the §5.1 wiring dict FLAT at top level with the MOCKED_SEAM result
nested under "mocked_seam" — see guardkitfactory.wiring.analyzer.
Real-factory (unmocked) end-to-end coverage lives in
tests/orchestrator/test_wiring_seam_real_factory.py.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional
from unittest.mock import MagicMock, patch

from guardkit.orchestrator.agent_invoker import AgentInvoker
from guardkit.orchestrator.quality_gates.coach_evidence import (
    CoachEvidenceBundle,
)
from guardkit.orchestrator.quality_gates.coach_validator import (
    CoachValidator,
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


def _factory_shape(
    *,
    mocked_seam: Optional[Dict[str, Any]],
    findings: Optional[list] = None,
    status: str = "complete",
) -> Dict[str, Any]:
    """The REAL analyze_wiring return shape: flat wiring dict with the
    MOCKED_SEAM result nested under "mocked_seam"."""
    shape: Dict[str, Any] = {
        "status": status,
        "dialect": "python",
        "language": "python",
        "dialects": ["python"],
        "languages": ["python"],
        "targets_scanned": 1,
        "symbols_examined": 1,
        "findings": findings if findings is not None else [],
        "degraded_files": [],
    }
    if mocked_seam is not None:
        shape["mocked_seam"] = mocked_seam
    return shape


_FACTORY_PATCH = "guardkit.orchestrator.quality_gates.coach_validator.analyze_wiring"
_AVAIL_PATCH = (
    "guardkit.orchestrator.quality_gates.coach_validator."
    "_is_wiring_factory_available"
)


# ---------------------------------------------------------------------------
# Envelope normalization: factory shape -> {wiring, mocked_seam, spec_gap}
# ---------------------------------------------------------------------------


class TestEnvelopeNormalization:
    """_run_wiring_analysis normalizes the factory shape into the
    three-field envelope gather_evidence consumes."""

    def test_mocked_seam_extracted_from_nested_key(self, tmp_path: Path) -> None:
        seam = {
            "status": "ran",
            "ran": True,
            "skip_reason": None,
            "dialect": "python",
            "language": "python",
            "findings": [{"symbol": "authored.seam", "severity": "warning"}],
            "external_mocks_ignored": [],
        }
        with patch(_AVAIL_PATCH, return_value=True), patch(
            _FACTORY_PATCH, return_value=_factory_shape(mocked_seam=seam),
        ):
            result = _run_wiring_analysis(
                worktree_path=tmp_path,
                authored_files=["src/main.py"],
                task_type="feature",
                stack_template="python",
            )

        assert result is not None
        assert result["mocked_seam"] == seam
        # The wiring dict is the FLAT factory dict, without the nested copy.
        assert result["wiring"]["status"] == "complete"
        assert "mocked_seam" not in result["wiring"]
        assert result["spec_gap"] is None  # Wave-3

    def test_factory_skip_result_passes_through(self, tmp_path: Path) -> None:
        """The factory's own skipped_no_acceptance_files result reaches the
        bundle untouched — guardkit does not synthesize skip dicts."""
        seam = {
            "status": "skipped_no_acceptance_files",
            "ran": False,
            "skip_reason": "no acceptance files found",
            "dialect": "python",
            "language": "python",
            "findings": [],
            "external_mocks_ignored": [],
        }
        with patch(_AVAIL_PATCH, return_value=True), patch(
            _FACTORY_PATCH, return_value=_factory_shape(mocked_seam=seam),
        ):
            result = _run_wiring_analysis(
                worktree_path=tmp_path,
                authored_files=["src/main.py"],
                task_type="feature",
                stack_template="python",
            )

        assert result is not None
        assert result["mocked_seam"]["status"] == "skipped_no_acceptance_files"
        assert result["mocked_seam"]["ran"] is False

    def test_unwired_probe_not_gated_on_acceptance_files(
        self, tmp_path: Path
    ) -> None:
        """Production-only authored sets still call the factory and surface
        UNWIRED findings — the pre-gate that skipped the call is gone."""
        finding = {
            "symbol": "dead_handler",
            "severity": "warning",
            "pattern": "UNWIRED_PATH",
        }
        with patch(_AVAIL_PATCH, return_value=True), patch(
            _FACTORY_PATCH,
            return_value=_factory_shape(mocked_seam=None, findings=[finding]),
        ) as mock_factory:
            result = _run_wiring_analysis(
                worktree_path=tmp_path,
                authored_files=["src/production_only.py"],  # no test files
                task_type="feature",
                stack_template="python",
            )

        mock_factory.assert_called_once()
        assert result is not None
        assert result["wiring"]["findings"] == [finding]

    def test_stack_hint_passed_as_object_with_language(
        self, tmp_path: Path
    ) -> None:
        """The factory reads stack.language — a bare string would be
        silently dropped, so the bridge wraps it."""
        with patch(_AVAIL_PATCH, return_value=True), patch(
            _FACTORY_PATCH, return_value=None,
        ) as mock_factory:
            _run_wiring_analysis(
                worktree_path=tmp_path,
                authored_files=["src/main.py"],
                task_type="feature",
                stack_template="python",
            )

        stack_arg = mock_factory.call_args.kwargs["stack"]
        assert getattr(stack_arg, "language", None) is not None

    def test_factory_none_returns_none(self, tmp_path: Path) -> None:
        with patch(_AVAIL_PATCH, return_value=True), patch(
            _FACTORY_PATCH, return_value=None,
        ):
            result = _run_wiring_analysis(
                worktree_path=tmp_path,
                authored_files=["src/main.py"],
                task_type="feature",
                stack_template="python",
            )
        assert result is None

    def test_factory_exception_returns_none(self, tmp_path: Path) -> None:
        with patch(_AVAIL_PATCH, return_value=True), patch(
            _FACTORY_PATCH, side_effect=RuntimeError("boom"),
        ):
            result = _run_wiring_analysis(
                worktree_path=tmp_path,
                authored_files=["src/main.py"],
                task_type="feature",
                stack_template="python",
            )
        assert result is None

    def test_zero_authored_files_returns_none(self, tmp_path: Path) -> None:
        result = _run_wiring_analysis(
            worktree_path=tmp_path,
            authored_files=[],
            task_type="feature",
            stack_template="python",
        )
        assert result is None

    def test_non_feature_task_types_return_none(self, tmp_path: Path) -> None:
        """Positive gate: only FEATURE/REFACTOR/INTEGRATION are analyzed —
        infrastructure and documentation are gated out (scope §4)."""
        for task_type in (
            "scaffolding", "documentation", "testing", "infrastructure",
        ):
            result = _run_wiring_analysis(
                worktree_path=tmp_path,
                authored_files=["src/main.py"],
                task_type=task_type,
                stack_template="python",
            )
            assert result is None, task_type

    def test_factory_unavailable_returns_none_regardless_of_files(
        self, tmp_path: Path
    ) -> None:
        """AC-017: factory absent → None for ALL THREE fields, uniformly —
        including authored sets with no test-looking files."""
        with patch(_AVAIL_PATCH, return_value=False):
            for authored in (
                ["src/main.py"],
                ["src/main.py", "tests/test_main.py"],
            ):
                assert _run_wiring_analysis(
                    worktree_path=tmp_path,
                    authored_files=authored,
                    task_type="feature",
                    stack_template="python",
                ) is None


# ---------------------------------------------------------------------------
# AC-006: external_mocks_ignored always present on populated mocked_seam
# ---------------------------------------------------------------------------


class TestExternalMockControl:
    """AC-006: external_mocks_ignored present (added when missing)."""

    def test_missing_external_mocks_ignored_is_added(self, tmp_path: Path) -> None:
        seam_without_field = {
            "status": "ran",
            "ran": True,
            "dialect": "python",
            "findings": [],
            # external_mocks_ignored intentionally absent
        }
        with patch(_AVAIL_PATCH, return_value=True), patch(
            _FACTORY_PATCH,
            return_value=_factory_shape(mocked_seam=seam_without_field),
        ):
            result = _run_wiring_analysis(
                worktree_path=tmp_path,
                authored_files=["src/main.py"],
                task_type="feature",
                stack_template="python",
            )

        assert result is not None
        assert result["mocked_seam"]["external_mocks_ignored"] == []

    def test_populated_external_mocks_ignored_preserved(
        self, tmp_path: Path
    ) -> None:
        ignored = [{"symbol": "httpx.Client", "severity": "info"}]
        seam = {
            "status": "ran",
            "ran": True,
            "dialect": "python",
            "findings": [],
            "external_mocks_ignored": ignored,
        }
        with patch(_AVAIL_PATCH, return_value=True), patch(
            _FACTORY_PATCH, return_value=_factory_shape(mocked_seam=seam),
        ):
            result = _run_wiring_analysis(
                worktree_path=tmp_path,
                authored_files=["src/main.py"],
                task_type="feature",
                stack_template="python",
            )

        assert result is not None
        assert result["mocked_seam"]["external_mocks_ignored"] == ignored


# ---------------------------------------------------------------------------
# Gather integration: complete-path population via the (mocked) factory
# ---------------------------------------------------------------------------


class TestGatherIntegration:
    """gather_evidence populates the bundle fields from the normalized
    envelope at the complete-path return."""

    def _gather(self, tmp_path: Path, task_id: str) -> CoachEvidenceBundle:
        validator = CoachValidator(str(tmp_path), task_id=task_id)
        return validator.gather_evidence(
            task_id=task_id,
            turn=1,
            task={
                "acceptance_criteria": ["AC-001"],
                "task_type": "feature",
                "description": "x",
            },
        )

    def test_bundle_fields_populated_from_factory_shape(
        self, tmp_path: Path
    ) -> None:
        _init_git_worktree(tmp_path)
        results = _passing_task_work_results(
            {"files_authored": ["src/main.py"]},
        )
        _write_results(tmp_path, "TASK-POP", results)

        seam = {
            "status": "ran",
            "ran": True,
            "dialect": "python",
            "findings": [{"symbol": "authored.seam", "severity": "warning"}],
            "external_mocks_ignored": [],
        }
        finding = {"symbol": "dead_code", "severity": "warning"}
        with patch(_AVAIL_PATCH, return_value=True), patch(
            _FACTORY_PATCH,
            return_value=_factory_shape(mocked_seam=seam, findings=[finding]),
        ):
            bundle = self._gather(tmp_path, "TASK-POP")

        assert bundle.gathering_status == "complete"
        assert bundle.wiring is not None
        assert bundle.wiring["findings"] == [finding]
        assert bundle.mocked_seam is not None
        assert bundle.mocked_seam["ran"] is True
        assert bundle.spec_gap is None

    def test_zero_authored_files_all_fields_none(self, tmp_path: Path) -> None:
        _init_git_worktree(tmp_path)
        results = _passing_task_work_results({"files_authored": []})
        _write_results(tmp_path, "TASK-ZERO", results)

        bundle = self._gather(tmp_path, "TASK-ZERO")

        assert bundle.gathering_status == "complete"
        assert bundle.wiring is None
        assert bundle.mocked_seam is None
        assert bundle.spec_gap is None

    def test_rendered_bundle_carries_mocked_seam(self, tmp_path: Path) -> None:
        _init_git_worktree(tmp_path)
        results = _passing_task_work_results(
            {"files_authored": ["src/main.py"]},
        )
        _write_results(tmp_path, "TASK-RENDER", results)

        seam = {
            "status": "ran",
            "ran": True,
            "dialect": "python",
            "findings": [{"symbol": "authored.seam", "severity": "warning"}],
            "external_mocks_ignored": [],
        }
        with patch(_AVAIL_PATCH, return_value=True), patch(
            _FACTORY_PATCH, return_value=_factory_shape(mocked_seam=seam),
        ):
            bundle = self._gather(tmp_path, "TASK-RENDER")

        invoker = AgentInvoker.__new__(AgentInvoker)
        rendered = invoker._render_evidence_bundle_section(bundle)
        json_match = re.search(
            r"<evidence_bundle>\s*(\{.*?\})\s*</evidence_bundle>",
            rendered,
            re.DOTALL,
        )
        assert json_match is not None
        bundle_json = json.loads(json_match.group(1))
        assert bundle_json["mocked_seam"]["ran"] is True
        assert len(bundle_json["mocked_seam"]["findings"]) == 1
        assert bundle_json["wiring"] is not None

    def test_bundle_json_roundtrip(self, tmp_path: Path) -> None:
        _init_git_worktree(tmp_path)
        results = _passing_task_work_results(
            {"files_authored": ["src/main.py"]},
        )
        _write_results(tmp_path, "TASK-RT", results)

        seam = {
            "status": "ran",
            "ran": True,
            "dialect": "python",
            "findings": [],
            "external_mocks_ignored": [],
        }
        with patch(_AVAIL_PATCH, return_value=True), patch(
            _FACTORY_PATCH, return_value=_factory_shape(mocked_seam=seam),
        ):
            bundle = self._gather(tmp_path, "TASK-RT")

        d = bundle.to_dict()
        parsed = json.loads(json.dumps(d, default=str))
        assert parsed["mocked_seam"]["ran"] is True
        assert "wiring" in parsed


# ---------------------------------------------------------------------------
# AC: Advisory only — no verdict override
# ---------------------------------------------------------------------------


class TestAdvisoryOnly:
    """AC (advisory only): MOCKED_SEAM produces no code override of the verdict."""

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
        assert d["mocked_seam"]["ran"] is True
        assert d["mocked_seam"]["external_mocks_ignored"] == ["httpx"]
        parsed = json.loads(json.dumps(d, default=str))
        assert parsed["mocked_seam"]["ran"] is True

    def test_guard_sentence_7_treats_mocked_seam_as_advisory(self) -> None:
        """Guard #7 treats mocked_seam findings as advisory candidates AND
        reminds the Coach that non-complete statuses are absent evidence."""
        invoker = AgentInvoker.__new__(AgentInvoker)
        guards = invoker._render_absence_of_failure_guards()

        assert "WIRING-EVIDENCE ADVISORY GUARD" in guards
        assert "mocked_seam" in guards
        assert "candidate dead code" in guards or "suspect acceptance" in guards
        # Advisory, not an override.
        assert "Advisory only" in guards
        # The absent-signal reminder: non-complete status + findings:[] is
        # NOT a clean verdict.
        assert "ABSENT" in guards

    def test_no_code_override_for_wiring_findings(self) -> None:
        """grep-level guard: no hard-gate override keyed on wiring or
        mocked_seam findings exists in the validator (advisory day one)."""
        import guardkit.orchestrator.quality_gates.coach_validator as cv

        src = Path(cv.__file__).read_text()
        # The spec_gap hard guard is Wave-3 (QAWE-004); nothing in Wave-1/2
        # may turn wiring/mocked_seam findings into a programmatic rejection.
        assert "_apply_wiring_override" not in src
        assert "_apply_mocked_seam_override" not in src
