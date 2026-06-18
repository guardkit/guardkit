"""Unit tests for the post-wave wiring gate (TASK-AB-WIREGATE01).

Covers the four guardkit-side units of the gate:

1. ``_wave_authored_files`` — unions the authored set across a whole wave from
   each task's ``task_work_results.json``.
2. ``_collect_turn_rejecting_wiring_findings`` — only mocked-primary-seam +
   ctor-arity are turn-rejecting; UNWIRED stays advisory; absent signals
   (None / error / unsupported / skipped) are never turn-rejecting.
3. ``_build_wiring_feedback`` — frames per-task-green ≠ feature-green and names
   the seams + ctor mismatches.
4. ``_run_post_wave_wiring_gate`` — bounded feed-back retry, replace-not-append,
   never hard-terminates on findings, absence-of-failure-safe, stop_on_failure
   on a Coach-rejected re-run.

Coverage Target: >=85%
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from guardkit.orchestrator.feature_orchestrator import (
    FeatureOrchestrator,
    WaveExecutionResult,
)


def _has_guardkitfactory() -> bool:
    """True iff guardkitfactory is importable.

    Tests that ``patch("guardkitfactory.wiring.analyze_wiring")`` cannot run
    without it — the patch target import fails. They are skipped in CI's
    tests.yml (which deliberately does not install guardkitfactory) and run
    locally / in the seam suite. The gate SOURCE degrades gracefully when
    guardkitfactory is absent (lazy import + skip-log in
    ``_run_post_wave_wiring_gate``); that path is covered by
    ``test_guardkitfactory_unavailable_is_noop``, which does NOT need it.
    """
    try:
        import importlib.util

        return importlib.util.find_spec("guardkitfactory") is not None
    except Exception:
        return False


_requires_guardkitfactory = pytest.mark.skipif(
    not _has_guardkitfactory(),
    reason="patches guardkitfactory.wiring.analyze_wiring; requires guardkitfactory installed",
)


def _orchestrator(tmp_path: Path) -> FeatureOrchestrator:
    return FeatureOrchestrator(
        repo_root=tmp_path,
        max_turns=1,
        worktree_manager=MagicMock(),
        quiet=True,
    )


def _wave_result(task_ids, all_succeeded=True) -> WaveExecutionResult:
    return WaveExecutionResult(
        wave_number=1,
        task_ids=list(task_ids),
        results=[],
        all_succeeded=all_succeeded,
        smoke_gate_result=None,
    )


def _write_results(repo_root: Path, task_id: str, payload: dict) -> None:
    d = repo_root / ".guardkit" / "autobuild" / task_id
    d.mkdir(parents=True, exist_ok=True)
    (d / "task_work_results.json").write_text(json.dumps(payload))


def _wiring_dict(seam_findings=None, ctor_findings=None, status="complete"):
    """An analyze_wiring-shaped result dict."""
    return {
        "status": status,
        "mocked_seam": {
            "status": "ran" if seam_findings is not None else "skipped_no_acceptance_files",
            "findings": seam_findings or [],
            "external_mocks_ignored": [],
        },
        "ctor_arity": {
            "status": "ran" if ctor_findings is not None else "skipped_no_composition_root",
            "findings": ctor_findings or [],
        },
    }


_SEAM = {
    "file": "tests/integration/test_router.py",
    "lineno": 7,
    "symbol": "VoiceService",
    "pattern": "MOCKED_SEAM",
    "authored_this_turn": True,
}
_CTOR = {
    "file": "main.py",
    "lineno": 5,
    "symbol": "VoiceService",
    "pattern": "CTOR_ARITY",
    "why": "constructs 'VoiceService' with 1 arg but requires 2",
}


# ============================================================================
# 1. _wave_authored_files
# ============================================================================


class TestWaveAuthoredFiles:
    def test_unions_files_authored_across_tasks(self, tmp_path):
        orch = _orchestrator(tmp_path)
        _write_results(tmp_path, "TASK-A", {"files_authored": ["a.py", "shared.py"]})
        _write_results(tmp_path, "TASK-B", {"files_authored": ["b.py", "shared.py"]})
        got = orch._wave_authored_files(["TASK-A", "TASK-B"])
        assert sorted(got) == ["a.py", "b.py", "shared.py"]

    def test_falls_back_to_created_union_modified(self, tmp_path):
        orch = _orchestrator(tmp_path)
        _write_results(
            tmp_path, "TASK-A",
            {"files_created": ["new.py"], "files_modified": ["old.py", "new.py"]},
        )
        got = orch._wave_authored_files(["TASK-A"])
        assert sorted(got) == ["new.py", "old.py"]

    def test_missing_results_file_contributes_nothing(self, tmp_path):
        orch = _orchestrator(tmp_path)
        _write_results(tmp_path, "TASK-A", {"files_authored": ["a.py"]})
        # TASK-B has no results file.
        got = orch._wave_authored_files(["TASK-A", "TASK-B"])
        assert got == ["a.py"]

    def test_empty_authored_list_is_authoritative(self, tmp_path):
        orch = _orchestrator(tmp_path)
        _write_results(tmp_path, "TASK-A", {"files_authored": []})
        assert orch._wave_authored_files(["TASK-A"]) == []


# ============================================================================
# 2. _collect_turn_rejecting_wiring_findings
# ============================================================================


class TestCollectTurnRejecting:
    def test_authored_seam_and_ctor_are_turn_rejecting(self):
        result = _wiring_dict(seam_findings=[_SEAM], ctor_findings=[_CTOR])
        got = FeatureOrchestrator._collect_turn_rejecting_wiring_findings(result)
        assert {f["pattern"] for f in got} == {"MOCKED_SEAM", "CTOR_ARITY"}

    def test_non_authored_seam_excluded(self):
        external = dict(_SEAM, authored_this_turn=False, symbol="httpx")
        result = _wiring_dict(seam_findings=[external])
        assert FeatureOrchestrator._collect_turn_rejecting_wiring_findings(result) == []

    def test_unwired_findings_stay_advisory(self):
        result = _wiring_dict()
        result["findings"] = [{"pattern": "UNWIRED_PATH", "symbol": "foo"}]
        # UNWIRED_PATH lives at top level, not in mocked_seam/ctor_arity → never collected.
        assert FeatureOrchestrator._collect_turn_rejecting_wiring_findings(result) == []

    @pytest.mark.parametrize("absent", [None, {"status": "error"},
                                        {"status": "unsupported_stack"}])
    def test_absent_signal_never_turn_rejecting(self, absent):
        assert FeatureOrchestrator._collect_turn_rejecting_wiring_findings(absent) == []

    def test_skipped_subresults_not_turn_rejecting(self):
        # seam + ctor both skipped (no acceptance files / no composition root)
        assert FeatureOrchestrator._collect_turn_rejecting_wiring_findings(
            _wiring_dict()
        ) == []


# ============================================================================
# 3. _build_wiring_feedback
# ============================================================================


class TestBuildWiringFeedback:
    def test_feedback_names_seam_and_ctor(self, tmp_path):
        orch = _orchestrator(tmp_path)
        fb = orch._build_wiring_feedback([_SEAM, _CTOR])
        assert "FEATURE WIRING FAILURE" in fb
        assert "per-task-green is not feature-green" in fb.lower()
        assert "tests/integration/test_router.py:7" in fb
        assert "VoiceService" in fb
        assert "main.py:5" in fb
        assert "MOCKED PRIMARY SEAM" in fb
        assert "CONSTRUCTOR ARITY" in fb

    def test_feedback_seam_only(self, tmp_path):
        orch = _orchestrator(tmp_path)
        fb = orch._build_wiring_feedback([_SEAM])
        assert "MOCKED PRIMARY SEAM" in fb
        assert "CONSTRUCTOR ARITY" not in fb


# ============================================================================
# 4. _run_post_wave_wiring_gate
# ============================================================================


class TestRunPostWaveWiringGate:
    @_requires_guardkitfactory
    def test_no_findings_is_neutral_no_reentry(self, tmp_path):
        orch = _orchestrator(tmp_path)
        wr = _wave_result(["TASK-A"])
        with patch.object(orch, "_wave_authored_files", return_value=["a.py"]), \
             patch("guardkitfactory.wiring.analyze_wiring",
                   return_value=_wiring_dict()), \
             patch.object(orch, "_execute_wave") as exec_wave:
            outcome = orch._run_post_wave_wiring_gate(
                1, ["TASK-A"], MagicMock(), MagicMock(path=str(tmp_path)), wr
            )
        assert outcome.terminate is False
        assert outcome.findings_unresolved is False
        exec_wave.assert_not_called()

    @_requires_guardkitfactory
    def test_empty_authored_set_is_noop(self, tmp_path):
        orch = _orchestrator(tmp_path)
        wr = _wave_result(["TASK-A"])
        with patch.object(orch, "_wave_authored_files", return_value=[]), \
             patch("guardkitfactory.wiring.analyze_wiring") as az, \
             patch.object(orch, "_execute_wave") as exec_wave:
            outcome = orch._run_post_wave_wiring_gate(
                1, ["TASK-A"], MagicMock(), MagicMock(path=str(tmp_path)), wr
            )
        assert outcome.terminate is False
        az.assert_not_called()
        exec_wave.assert_not_called()

    @_requires_guardkitfactory
    def test_analyzer_error_is_absent_signal_no_reentry(self, tmp_path):
        orch = _orchestrator(tmp_path)
        wr = _wave_result(["TASK-A"])
        with patch.object(orch, "_wave_authored_files", return_value=["a.py"]), \
             patch("guardkitfactory.wiring.analyze_wiring",
                   side_effect=RuntimeError("boom")), \
             patch.object(orch, "_execute_wave") as exec_wave:
            outcome = orch._run_post_wave_wiring_gate(
                1, ["TASK-A"], MagicMock(), MagicMock(path=str(tmp_path)), wr
            )
        assert outcome.terminate is False
        exec_wave.assert_not_called()

    def test_guardkitfactory_unavailable_is_noop(self, tmp_path):
        orch = _orchestrator(tmp_path)
        wr = _wave_result(["TASK-A"])
        # Setting the module to None in sys.modules makes the local import raise.
        with patch.dict(sys.modules, {"guardkitfactory.wiring": None}), \
             patch.object(orch, "_execute_wave") as exec_wave:
            outcome = orch._run_post_wave_wiring_gate(
                1, ["TASK-A"], MagicMock(), MagicMock(path=str(tmp_path)), wr
            )
        assert outcome.terminate is False
        exec_wave.assert_not_called()

    @_requires_guardkitfactory
    def test_findings_feed_back_and_clear_on_retry(self, tmp_path):
        orch = _orchestrator(tmp_path)
        orch._wiring_gate_max_retries = 1
        wr = _wave_result(["TASK-A"])
        rerun = _wave_result(["TASK-A"], all_succeeded=True)
        # First analyze → findings; after the re-run → clean.
        results = [_wiring_dict(seam_findings=[_SEAM]), _wiring_dict()]
        with patch.object(orch, "_wave_authored_files", return_value=["a.py"]), \
             patch("guardkitfactory.wiring.analyze_wiring",
                   side_effect=results), \
             patch.object(orch, "_execute_wave", return_value=rerun) as exec_wave:
            outcome = orch._run_post_wave_wiring_gate(
                1, ["TASK-A"], MagicMock(), MagicMock(path=str(tmp_path)), wr
            )
        exec_wave.assert_called_once()
        # seed_feedback carries the wiring feedback to turn 1.
        _, kwargs = exec_wave.call_args
        assert "FEATURE WIRING FAILURE" in kwargs["seed_feedback"]
        assert outcome.terminate is False
        assert outcome.findings_unresolved is False
        # replace-not-append: the final result is the re-executed wave.
        assert outcome.final_wave_result is rerun

    @_requires_guardkitfactory
    def test_findings_persist_after_budget_advisory_not_terminate(self, tmp_path):
        orch = _orchestrator(tmp_path)
        orch._wiring_gate_max_retries = 1
        wr = _wave_result(["TASK-A"])
        rerun = _wave_result(["TASK-A"], all_succeeded=True)
        # Findings persist on both the first and the re-run analysis.
        with patch.object(orch, "_wave_authored_files", return_value=["a.py"]), \
             patch("guardkitfactory.wiring.analyze_wiring",
                   return_value=_wiring_dict(ctor_findings=[_CTOR])), \
             patch.object(orch, "_execute_wave", return_value=rerun) as exec_wave:
            outcome = orch._run_post_wave_wiring_gate(
                1, ["TASK-A"], MagicMock(), MagicMock(path=str(tmp_path)), wr
            )
        exec_wave.assert_called_once()  # exactly one retry (budget = 1)
        assert outcome.terminate is False      # NEVER hard-terminates on findings
        assert outcome.findings_unresolved is True

    @_requires_guardkitfactory
    def test_retries_disabled_runs_once_advisory(self, tmp_path):
        orch = _orchestrator(tmp_path)
        orch._wiring_gate_max_retries = 0
        wr = _wave_result(["TASK-A"])
        with patch.object(orch, "_wave_authored_files", return_value=["a.py"]), \
             patch("guardkitfactory.wiring.analyze_wiring",
                   return_value=_wiring_dict(seam_findings=[_SEAM])), \
             patch.object(orch, "_execute_wave") as exec_wave:
            outcome = orch._run_post_wave_wiring_gate(
                1, ["TASK-A"], MagicMock(), MagicMock(path=str(tmp_path)), wr
            )
        exec_wave.assert_not_called()  # budget 0 → no feed-back
        assert outcome.terminate is False
        assert outcome.findings_unresolved is True

    @_requires_guardkitfactory
    def test_stop_on_failure_terminates_on_rejected_rerun(self, tmp_path):
        orch = _orchestrator(tmp_path)
        orch._wiring_gate_max_retries = 1
        orch.stop_on_failure = True
        wr = _wave_result(["TASK-A"])
        rejected = _wave_result(["TASK-A"], all_succeeded=False)
        with patch.object(orch, "_wave_authored_files", return_value=["a.py"]), \
             patch("guardkitfactory.wiring.analyze_wiring",
                   return_value=_wiring_dict(seam_findings=[_SEAM])), \
             patch.object(orch, "_execute_wave", return_value=rejected):
            outcome = orch._run_post_wave_wiring_gate(
                1, ["TASK-A"], MagicMock(), MagicMock(path=str(tmp_path)), wr
            )
        assert outcome.terminate is True
        assert outcome.final_wave_result is rejected
