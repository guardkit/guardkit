"""Unit tests for the post-wave wiring gate (TASK-AB-WIREGATE01).

Covers the four guardkit-side units of the gate:

1. ``_wave_authored_files`` — unions the authored set across a whole wave from
   each task's ``task_work_results.json``.
2. ``_collect_turn_rejecting_wiring_findings`` — only mocked-primary-seam +
   ctor-arity are turn-rejecting; UNWIRED stays advisory; absent signals
   (None / error / unsupported / skipped) are never turn-rejecting.
3. ``_run_post_wave_wiring_gate`` — one pass, advice only (step 2, 26 October
   2026): findings are printed and recorded, the wave is never re-run, and
   absent signals are never findings.

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


def _checkout(tmp_path: Path) -> MagicMock:
    """A stand-in worktree whose path is a real git checkout.

    The gate runs the analyser as the checkout's one writer, which reads the
    checkout with git; an empty folder made the gate take its "stopped on an
    error of its own" path before any finding was looked at.
    """
    import subprocess

    root = tmp_path / "checkout"
    root.mkdir(exist_ok=True)
    (root / "a.py").write_text("x = 1\n", encoding="utf-8")
    git = ["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid"]
    subprocess.run(git + ["init", "-q", "-b", "main"], cwd=root, check=True)
    subprocess.run(git + ["add", "-A"], cwd=root, check=True)
    subprocess.run(git + ["commit", "-q", "-m", "start"], cwd=root, check=True)
    return MagicMock(path=str(root))


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
        got, not_recorded = orch._wave_authored_files(["TASK-A", "TASK-B"])
        assert sorted(got) == ["a.py", "b.py", "shared.py"]
        assert not_recorded == []

    def test_falls_back_to_created_union_modified(self, tmp_path):
        orch = _orchestrator(tmp_path)
        _write_results(
            tmp_path, "TASK-A",
            {"files_created": ["new.py"], "files_modified": ["old.py", "new.py"]},
        )
        got, not_recorded = orch._wave_authored_files(["TASK-A"])
        assert sorted(got) == ["new.py", "old.py"]
        assert not_recorded == []

    def test_missing_results_file_contributes_nothing(self, tmp_path):
        orch = _orchestrator(tmp_path)
        _write_results(tmp_path, "TASK-A", {"files_authored": ["a.py"]})
        # TASK-B has no results file.
        got, not_recorded = orch._wave_authored_files(["TASK-A", "TASK-B"])
        assert got == ["a.py"]
        assert not_recorded == []

    def test_empty_tracked_list_is_authoritative(self, tmp_path):
        orch = _orchestrator(tmp_path)
        _write_results(
            tmp_path, "TASK-A",
            {"files_authored": [], "files_authored_tracking": "tracked"},
        )
        assert orch._wave_authored_files(["TASK-A"]) == ([], [])

    def test_unmarked_empty_list_is_reported_not_recorded(self, tmp_path):
        """2026-09-21: an unmarked empty list is not 'this task wrote
        nothing'; it is 'nobody recorded what this task wrote'."""
        orch = _orchestrator(tmp_path)
        _write_results(
            tmp_path, "TASK-A",
            {
                "files_authored": [],
                "files_created": ["new.py"],
                "files_modified": ["old.py"],
            },
        )
        got, not_recorded = orch._wave_authored_files(["TASK-A"])
        assert got == []
        assert not_recorded == ["TASK-A"]


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
# 3. _run_post_wave_wiring_gate — advice only
# ============================================================================


class TestRunPostWaveWiringGate:
    @_requires_guardkitfactory
    def test_no_findings_is_neutral_no_reentry(self, tmp_path):
        orch = _orchestrator(tmp_path)
        with patch.object(orch, "_wave_authored_files", return_value=(["a.py"], [])), \
             patch("guardkitfactory.wiring.analyze_wiring",
                   return_value=_wiring_dict()), \
             patch.object(orch, "_execute_wave") as exec_wave:
            outcome = orch._run_post_wave_wiring_gate(
                1, ["TASK-A"], MagicMock(), _checkout(tmp_path)
            )
        assert outcome.findings_unresolved is False
        exec_wave.assert_not_called()

    @_requires_guardkitfactory
    def test_empty_authored_set_is_noop(self, tmp_path):
        orch = _orchestrator(tmp_path)
        with patch.object(orch, "_wave_authored_files", return_value=([], [])), \
             patch("guardkitfactory.wiring.analyze_wiring") as az, \
             patch.object(orch, "_execute_wave") as exec_wave:
            outcome = orch._run_post_wave_wiring_gate(
                1, ["TASK-A"], MagicMock(), _checkout(tmp_path)
            )
        assert outcome.findings_unresolved is False
        az.assert_not_called()
        exec_wave.assert_not_called()

    @_requires_guardkitfactory
    def test_analyzer_error_is_absent_signal_no_reentry(self, tmp_path):
        orch = _orchestrator(tmp_path)
        with patch.object(orch, "_wave_authored_files", return_value=(["a.py"], [])), \
             patch("guardkitfactory.wiring.analyze_wiring",
                   side_effect=RuntimeError("boom")), \
             patch.object(orch, "_execute_wave") as exec_wave:
            outcome = orch._run_post_wave_wiring_gate(
                1, ["TASK-A"], MagicMock(), _checkout(tmp_path)
            )
        assert outcome.findings_unresolved is False
        exec_wave.assert_not_called()

    def test_guardkitfactory_unavailable_is_noop(self, tmp_path):
        orch = _orchestrator(tmp_path)
        # Setting the module to None in sys.modules makes the local import raise.
        with patch.dict(sys.modules, {"guardkitfactory.wiring": None}), \
             patch.object(orch, "_execute_wave") as exec_wave:
            outcome = orch._run_post_wave_wiring_gate(
                1, ["TASK-A"], MagicMock(), _checkout(tmp_path)
            )
        assert outcome.findings_unresolved is False
        exec_wave.assert_not_called()

    @_requires_guardkitfactory
    @pytest.mark.parametrize("found", [
        {"seam_findings": [_SEAM]}, {"ctor_findings": [_CTOR]},
    ], ids=["mocked-seam", "ctor-arity"])
    def test_findings_are_advice_and_the_wave_is_not_rerun(self, tmp_path, found):
        """Step 2 (26 October 2026): a finding is printed and recorded as
        advice; the wave is analysed once and never re-run."""
        orch = _orchestrator(tmp_path)
        with patch.object(orch, "_wave_authored_files", return_value=(["a.py"], [])), \
             patch("guardkitfactory.wiring.analyze_wiring",
                   return_value=_wiring_dict(**found)) as az, \
             patch.object(orch, "_execute_wave") as exec_wave:
            outcome = orch._run_post_wave_wiring_gate(
                1, ["TASK-A"], MagicMock(), _checkout(tmp_path)
            )
        exec_wave.assert_not_called()
        az.assert_called_once()
        assert outcome.findings_unresolved is True
        assert outcome.record["state"] == "found_something"
        assert outcome.record["reason"].startswith("advice")
        assert outcome.record["finding_count"] >= 1


# ============================================================================
# 4. _wiring_gate_record — unread input is never "ran and found nothing"
#    (12 October 2026, web readiness W4)
# ============================================================================


class TestWiringGateRecord:
    @staticmethod
    def _record(result, advisory=()):
        return FeatureOrchestrator._wiring_gate_record(3, result, list(advisory))

    def test_parse_degraded_is_not_checked(self):
        row = self._record(
            {"status": "parse_degraded", "findings": [],
             "degraded_files": ["web/src/Broken.tsx"]}
        )
        assert row["state"] == "not_checked"
        assert row["inputs_not_read"] == 1

    def test_partly_unsupported_lists_go_files_as_not_checked(self):
        row = self._record(
            {"status": "partly_unsupported", "findings": [],
             "degraded_files": [],
             "undialected_files": ["api/main.go", "api/handler.go"]}
        )
        assert row["state"] == "not_checked"
        assert row["inputs_not_read"] == 2

    def test_unread_files_under_a_complete_word_are_still_not_checked(self):
        row = self._record(
            {"status": "complete", "findings": [], "degraded_files": [],
             "undialected_files": ["api/main.go"]}
        )
        assert row["state"] == "not_checked"
        assert row["inputs_not_read"] == 1

    def test_older_result_without_the_new_field_still_reads(self):
        row = self._record({"status": "complete", "findings": [],
                            "degraded_files": []})
        assert row["state"] == "ran_and_found_nothing"
        assert row["inputs_not_read"] is None

    def test_a_finding_in_a_partly_read_check_keeps_both(self):
        row = self._record(
            {"status": "partly_unsupported", "degraded_files": [],
             "undialected_files": ["api/main.go"]},
            advisory=[{"file": "web/a.tsx", "symbol": "X",
                       "pattern": "UNWIRED_PATH"}],
        )
        assert row["state"] == "found_something"
        assert row["inputs_not_read"] == 1

    def test_unsupported_stack_is_kind_not_supported(self):
        row = self._record(
            {"status": "unsupported_stack", "undialected_files": ["main.go"]}
        )
        assert row["state"] == "kind_of_project_not_supported"


def test_task_and_group_records_agree_on_partly_read_checks():
    """The per-task summary and the per-group record give the same state and
    the same count for the same wiring result (12 October 2026)."""
    from guardkit.orchestrator.code_checks import summarise_check

    finding = {"file": "web/a.tsx", "symbol": "X", "pattern": "UNWIRED_PATH"}
    cases = [
        {"status": "complete", "findings": [], "degraded_files": [],
         "undialected_files": []},
        {"status": "parse_degraded", "findings": [],
         "degraded_files": ["web/a.tsx"]},
        {"status": "partly_unsupported", "findings": [], "degraded_files": [],
         "undialected_files": ["api/main.go"]},
        {"status": "partly_unsupported", "findings": [finding],
         "degraded_files": ["web/b.tsx"], "undialected_files": ["api/main.go"]},
    ]
    for block in cases:
        group = FeatureOrchestrator._wiring_gate_record(
            1, block, list(block["findings"])
        )
        task = summarise_check(block)
        assert (group["state"], group["inputs_not_read"]) == (
            task["state"], task["inputs_not_read"]
        ), block
