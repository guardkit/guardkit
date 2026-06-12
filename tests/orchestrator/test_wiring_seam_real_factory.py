"""Cross-repo seam tests: the wiring bridge against the REAL guardkitfactory.

The QAWE-002 run-1 implementation shipped green over a broken seam because
every test mocked ``analyze_wiring`` with an invented envelope shape — the
exact "green over un-wired code" failure mode the wiring evidence exists to
catch. These tests exercise the REAL installed ``guardkitfactory.wiring``
(no mocks), mirroring the xrepo-contract pattern of
``tests/orchestrator/harness/test_xrepo_contract_seam.py``: a factory-side
shape change fails here in seconds, not after a full autobuild run.

Skipped cleanly when guardkitfactory (or its tree-sitter stack) is absent.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional

import pytest

pytest.importorskip("guardkitfactory.wiring")

from guardkit.orchestrator.quality_gates.coach_validator import (  # noqa: E402
    CoachValidator,
    _run_wiring_analysis,
)

pytestmark = pytest.mark.seam


def _init_git_worktree(path: Path) -> None:
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


def _write(worktree: Path, rel: str, content: str) -> str:
    p = worktree / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)
    return rel


def _passing_task_work_results(
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
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
        "code_review": {"score": 80},
        "plan_audit": {"status": "passed", "violations": 0, "severity": "low"},
        "files_modified": [],
        "files_created": [],
        "tests_written": [],
    }
    if extra:
        results.update(extra)
    return results


class TestRealFactorySeam:
    """_run_wiring_analysis against the real analyzer — no mocks."""

    def test_unwired_symbol_reaches_wiring_findings(self, tmp_path: Path) -> None:
        """A genuinely dead authored symbol produces a non-empty
        wiring.findings through the real seam — the run-1 regression
        (envelope mismatch → bundle.wiring always None) fails this test."""
        _write(
            tmp_path,
            "src/orphan_module.py",
            "def totally_unwired_zzqx_handler():\n    pass\n",
        )

        result = _run_wiring_analysis(
            worktree_path=tmp_path,
            authored_files=["src/orphan_module.py"],
            task_type="feature",
            stack_template=None,
        )

        assert result is not None
        wiring = result["wiring"]
        assert wiring is not None
        assert wiring["status"] == "complete"
        symbols = {f["symbol"] for f in wiring["findings"]}
        assert "totally_unwired_zzqx_handler" in symbols
        # The wiring dict must NOT carry the nested mocked_seam copy.
        assert "mocked_seam" not in wiring
        # The factory's own skip result for mocked_seam passes through.
        assert result["mocked_seam"] is not None
        assert result["mocked_seam"]["ran"] is False
        assert result["mocked_seam"]["status"] == "skipped_no_acceptance_files"
        assert result["mocked_seam"]["external_mocks_ignored"] == []

    def test_wired_symbol_yields_empty_findings_complete(
        self, tmp_path: Path
    ) -> None:
        """Absent-vs-empty (AC-015): a wired fixture returns a REAL positive
        verdict — status complete with findings:[] — distinct from None."""
        _write(tmp_path, "src/wired.py", "def wired_service():\n    pass\n")
        _write(
            tmp_path,
            "src/consumer.py",
            "from wired import wired_service\nwired_service()\n",
        )

        result = _run_wiring_analysis(
            worktree_path=tmp_path,
            authored_files=["src/wired.py"],
            task_type="feature",
            stack_template=None,
        )

        assert result is not None
        assert result["wiring"]["status"] == "complete"
        assert result["wiring"]["findings"] == []

    def test_mocked_authored_seam_reaches_mocked_seam_findings(
        self, tmp_path: Path
    ) -> None:
        """An acceptance file patching an authored seam produces a warning
        finding through the real seam."""
        _write(tmp_path, "authored.py", "def my_authored_seam():\n    pass\n")
        _write(tmp_path, "main.py", "from authored import my_authored_seam\n")
        _write(
            tmp_path,
            "features/steps.py",
            "from unittest.mock import patch\n"
            "@patch('authored.my_authored_seam')\n"
            "def step_impl(mock_seam):\n    pass\n",
        )

        result = _run_wiring_analysis(
            worktree_path=tmp_path,
            authored_files=["authored.py"],
            task_type="feature",
            stack_template=None,
        )

        assert result is not None
        seam = result["mocked_seam"]
        assert seam is not None and seam["ran"] is True
        warnings = [f for f in seam["findings"] if f["severity"] == "warning"]
        assert len(warnings) == 1
        assert "my_authored_seam" in warnings[0]["symbol"]
        assert warnings[0]["authored_this_turn"] is True

    def test_result_is_json_serializable(self, tmp_path: Path) -> None:
        _write(tmp_path, "src/x.py", "def lonely_zz():\n    pass\n")
        result = _run_wiring_analysis(
            worktree_path=tmp_path,
            authored_files=["src/x.py"],
            task_type="feature",
            stack_template=None,
        )
        json.dumps(result)


class TestRealFactoryGatherEndToEnd:
    """gather_evidence end-to-end with the real factory: the dead symbol
    must reach bundle.wiring at the complete-path return."""

    def test_bundle_wiring_populated_for_dead_symbol(self, tmp_path: Path) -> None:
        _init_git_worktree(tmp_path)
        rel = _write(
            tmp_path,
            "src/orphan_module.py",
            "def totally_unwired_zzqx_handler():\n    pass\n",
        )
        results = _passing_task_work_results({"files_authored": [rel]})
        results_dir = tmp_path / ".guardkit" / "autobuild" / "TASK-SEAM"
        results_dir.mkdir(parents=True, exist_ok=True)
        (results_dir / "task_work_results.json").write_text(json.dumps(results))

        validator = CoachValidator(str(tmp_path), task_id="TASK-SEAM")
        bundle = validator.gather_evidence(
            task_id="TASK-SEAM",
            turn=1,
            task={
                "acceptance_criteria": ["AC-001"],
                "task_type": "feature",
                "description": "x",
            },
        )

        assert bundle.gathering_status == "complete"
        assert bundle.wiring is not None, (
            "bundle.wiring is None for a fixture with a genuinely dead "
            "authored symbol — the factory seam is broken again"
        )
        symbols = {f["symbol"] for f in bundle.wiring["findings"]}
        assert "totally_unwired_zzqx_handler" in symbols
        assert bundle.mocked_seam is not None
        # Wave-3 populates spec_gap; no BDD evidence here -> absent-signal,
        # hard gate not armed.
        assert bundle.spec_gap is not None
        assert bundle.spec_gap["whole_file_deselection"] is False
