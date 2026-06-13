"""Regression suite for the direct-mode false-green (TASK-FIX-DIRECTFG01).

In autobuild ``implementation_mode: direct``, the Player's quality gates are
written ``quality_gates_relaxed: True`` (coverage/arch relaxed). Before this
fix the Coach would approve without verifying that the acceptance criteria were
actually delivered, that authored wiring resolved, or that a registered CLI
producer the task authored actually runs. The concrete failure that motivated
this (FEAT-9DDE) was a registered ``bin-entries.txt`` producer that raised
``ModuleNotFoundError`` on plain ``python <path>`` yet sailed through the
relaxed Coach.

This suite pins the new deterministic gate
``AutoBuildOrchestrator._direct_mode_evidence_gate`` and its module-level helper
``_check_direct_mode_bin_entries``:

- AC4 (core): a broken authored bin-entry BLOCKS (decision != approve) and the
  block is PRE-LLM (the LLM Coach is never invoked).
- A working bin-entry does NOT block.
- A non-Python authored bin-entry is an advisory (``should_fix``), never a block
  on its own (stack-plugin-architecture.md: execution check degrades, never
  false-passes / crashes).
- Full-mode tasks (no ``quality_gates_relaxed``) skip the gate entirely (AC5 —
  full mode structurally untouched).
- A ``bin-entries.txt`` entry NOT in the authored set is never executed (the
  scoping invariant — never run arbitrary scripts).
- Unit coverage of ``_check_direct_mode_bin_entries`` classification across
  broken / working / timeout / non-Python cases.

Conventions follow ``tests/orchestrator/test_coach_wiring_bundle.py``
(``_init_git_worktree``, ``_passing_task_work_results``) and
``tests/unit/test_direct_mode_criteria_matching.py``.

Coverage Target: >=85%
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock

import pytest

from guardkit.orchestrator.autobuild import (
    AutoBuildOrchestrator,
    _check_direct_mode_bin_entries,
    _read_bin_entries,
)
from guardkit.orchestrator.quality_gates.coach_validator import CoachValidator


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _init_git_worktree(path: Path) -> None:
    """Minimal git init so CoachValidator / TaskStateBridge can construct."""
    subprocess.run(["git", "init", "-q"], cwd=path, check=True, capture_output=True)
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


def _direct_mode_results(
    *,
    files_created: List[str],
    files_modified: Optional[List[str]] = None,
    relaxed: bool = True,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build a direct-mode ``task_work_results`` dict.

    When ``relaxed`` is True the ``quality_gates.quality_gates_relaxed`` flag is
    set — the AC5 discriminator that the direct-mode results writer
    (``agent_invoker._write_direct_mode_results``) is the sole producer of. When
    False, the dict looks like a full task-work result (no relaxed flag) so the
    gate must no-op.
    """
    quality_gates: Dict[str, Any] = {
        "all_passed": True,
        "tests_passing": True,
        "tests_passed": 1,
        "tests_failed": 0,
        "coverage_met": True,
    }
    if relaxed:
        quality_gates["quality_gates_relaxed"] = True
    results: Dict[str, Any] = {
        "task_id": "TASK-X",
        "implementation_mode": "direct" if relaxed else "task-work",
        "completed": True,
        "success": True,
        "quality_gates": quality_gates,
        "files_created": list(files_created),
        "files_modified": list(files_modified or []),
        "tests_written": [],
        # AC delivery evidence so AC1 is satisfied and does not itself block in
        # the bin-entry-focused tests. completion_promises drive the matcher.
        "completion_promises": [{"criterion_id": "AC-001", "status": "complete"}],
        "requirements_met": ["AC-001"],
        "requirements_addressed": ["AC-001"],
    }
    if extra:
        results.update(extra)
    return results


def _write_results(worktree: Path, task_id: str, results: Dict[str, Any]) -> None:
    results_dir = worktree / ".guardkit" / "autobuild" / task_id
    results_dir.mkdir(parents=True, exist_ok=True)
    (results_dir / "task_work_results.json").write_text(json.dumps(results))


def _write_bin_entry(worktree: Path, rel_path: str, body: str) -> None:
    target = worktree / rel_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body)


def _write_manifest(worktree: Path, entries: List[str]) -> None:
    manifest = worktree / "installer" / "core" / "commands" / "bin-entries.txt"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(
        "# GuardKit CLI manifest (test)\n" + "\n".join(entries) + "\n"
    )


class _FakeWorktree:
    """Minimal Worktree stand-in: the gate only reads ``.path``."""

    def __init__(self, path: Path) -> None:
        self.path = path


@pytest.fixture
def worktree(tmp_path: Path) -> Path:
    """A git-initialised worktree directory."""
    _init_git_worktree(tmp_path)
    return tmp_path


def _orchestrator(repo_root: Path, agent_invoker: Any = None) -> AutoBuildOrchestrator:
    """Construct an orchestrator without the pre-loop (DI for the agent invoker)."""
    return AutoBuildOrchestrator(
        repo_root=repo_root,
        enable_pre_loop=False,
        agent_invoker=agent_invoker,
    )


# ---------------------------------------------------------------------------
# AC4 (core): broken bin-entry blocks, and the block is pre-LLM
# ---------------------------------------------------------------------------


class TestBrokenBinEntryBlocks:
    """AC4: a broken registered producer must block the turn before the LLM."""

    def test_broken_bin_entry_blocks_via_gate(self, worktree: Path) -> None:
        """Driving the gate directly returns a non-None blocking feedback result.

        The broken wrapper raises ``ModuleNotFoundError`` on ``python <path>``
        (the FEAT-9DDE failure). The gate must return an ``AgentInvocationResult``
        with ``decision == "feedback"`` whose rationale names the
        ``direct_mode_bin_entry_broken`` category.
        """
        rel = "installer/core/commands/xyz.py"
        _write_bin_entry(
            worktree, rel, "import nonexistent_module_xyz123\nprint('hi')\n"
        )
        _write_manifest(worktree, [rel])
        _write_results(
            worktree, "TASK-X", _direct_mode_results(files_created=[rel])
        )

        orch = _orchestrator(worktree)
        validator = CoachValidator(str(worktree), task_id="TASK-X")

        result = orch._direct_mode_evidence_gate(
            validator,
            "TASK-X",
            1,
            _FakeWorktree(worktree),
            0.0,
            acceptance_criteria=["AC-001: deliver the producer"],
            task_type="feature",
        )

        assert result is not None, "broken producer must block"
        assert result.report.get("decision") == "feedback"
        assert result.report.get("decision") != "approve"
        assert "direct_mode_bin_entry_broken" in result.report.get("rationale", "")

    def test_broken_bin_entry_blocks_with_invoke_coach_not_called(
        self, worktree: Path
    ) -> None:
        """Through ``_invoke_coach_primary`` the LLM Coach is NEVER invoked.

        This is the load-bearing AC4 assertion: the deterministic gate must
        block BEFORE the LLM Coach so a red signal cannot be approved over by
        Coach leniency (the BDDW-002 lesson). We mock ``invoke_coach`` and
        assert it was not awaited.
        """
        rel = "installer/core/commands/xyz.py"
        _write_bin_entry(
            worktree, rel, "import nonexistent_module_xyz123\nprint('hi')\n"
        )
        _write_manifest(worktree, [rel])
        _write_results(
            worktree, "TASK-X", _direct_mode_results(files_created=[rel])
        )

        fake_invoker = MagicMock()
        fake_invoker.invoke_coach = AsyncMock()
        orch = _orchestrator(worktree, agent_invoker=fake_invoker)

        result = orch._invoke_coach_primary(
            task_id="TASK-X",
            turn=1,
            requirements="deliver the producer",
            player_report={"task_id": "TASK-X"},
            worktree=_FakeWorktree(worktree),
            acceptance_criteria=["AC-001: deliver the producer"],
            task_type="feature",
            skip_arch_review=False,
            requires_infrastructure=None,
            consumer_context=None,
            remaining_budget=None,
            wave_size=1,
            peer_changed_files=None,
            context_prompt="",
            start_time=0.0,
        )

        # Blocked deterministically, pre-LLM.
        assert result.report.get("decision") == "feedback"
        assert "direct_mode_bin_entry_broken" in result.report.get("rationale", "")
        fake_invoker.invoke_coach.assert_not_called()


# ---------------------------------------------------------------------------
# Working producer does not block
# ---------------------------------------------------------------------------


class TestWorkingBinEntryDoesNotBlock:
    def test_working_bin_entry_does_not_block(self, worktree: Path) -> None:
        """A producer that loads cleanly (exit 0) must not raise a block.

        Driven through the gate: with AC evidence present and no broken
        producer, the gate returns ``None`` (nothing to block on).
        """
        rel = "installer/core/commands/ok.py"
        _write_bin_entry(worktree, rel, "print('{}')\n")
        _write_manifest(worktree, [rel])
        _write_results(
            worktree, "TASK-X", _direct_mode_results(files_created=[rel])
        )

        orch = _orchestrator(worktree)
        validator = CoachValidator(str(worktree), task_id="TASK-X")

        result = orch._direct_mode_evidence_gate(
            validator,
            "TASK-X",
            1,
            _FakeWorktree(worktree),
            0.0,
            acceptance_criteria=["AC-001: deliver the producer"],
            task_type="feature",
        )

        assert result is None, "a clean producer must not block"

    def test_working_bin_entry_exit_zero_empty_stdout_is_present(
        self, worktree: Path
    ) -> None:
        """A module that loads silently (exit 0, empty stdout) is PRESENT.

        Unit-level: ``_check_direct_mode_bin_entries`` must NOT penalise exit-0
        with empty stdout — a module that imports cleanly and prints nothing is
        a valid producer signal.
        """
        rel = "installer/core/commands/silent.py"
        _write_bin_entry(worktree, rel, "x = 1\n")  # exit 0, no stdout
        _write_manifest(worktree, [rel])

        issues = _check_direct_mode_bin_entries(worktree, [rel], sys.executable)
        assert issues == []


# ---------------------------------------------------------------------------
# Non-Python bin-entry is advisory, not blocking
# ---------------------------------------------------------------------------


class TestNonPythonBinEntryIsAdvisory:
    def test_non_python_bin_entry_is_advisory_not_blocking(
        self, worktree: Path
    ) -> None:
        """A non-.py authored bin-entry yields a ``should_fix`` advisory only.

        On its own (no other ``must_fix`` issue) it must NOT block the turn —
        per stack-plugin-architecture.md the execution check degrades to an
        absent signal for non-Python entries rather than crashing or
        false-passing.
        """
        rel = "installer/core/commands/run.sh"
        _write_bin_entry(worktree, rel, "echo hi\n")
        _write_manifest(worktree, [rel])
        _write_results(
            worktree, "TASK-X", _direct_mode_results(files_created=[rel])
        )

        orch = _orchestrator(worktree)
        validator = CoachValidator(str(worktree), task_id="TASK-X")

        result = orch._direct_mode_evidence_gate(
            validator,
            "TASK-X",
            1,
            _FakeWorktree(worktree),
            0.0,
            acceptance_criteria=["AC-001: deliver the producer"],
            task_type="feature",
        )

        # Advisory rides alongside but does not block on its own.
        assert result is None, "a non-Python advisory must not block the turn"

    def test_non_python_classified_as_should_fix(self, worktree: Path) -> None:
        """Unit-level: the non-Python entry produces a ``should_fix`` advisory."""
        rel = "installer/core/commands/run.sh"
        _write_bin_entry(worktree, rel, "echo hi\n")
        _write_manifest(worktree, [rel])

        issues = _check_direct_mode_bin_entries(worktree, [rel], sys.executable)
        assert len(issues) == 1
        assert issues[0]["severity"] == "should_fix"
        assert issues[0]["category"] == "direct_mode_bin_entry_unverifiable"


# ---------------------------------------------------------------------------
# Full-mode task skips the gate (AC5)
# ---------------------------------------------------------------------------


class TestFullModeTaskSkipsGate:
    def test_full_mode_task_skips_gate(self, worktree: Path) -> None:
        """Without ``quality_gates_relaxed`` the gate returns None immediately.

        AC5: full task-work tasks lack the relaxed flag, so the gate is a
        structural no-op — even with a broken registered producer in the tree.
        """
        rel = "installer/core/commands/xyz.py"
        _write_bin_entry(
            worktree, rel, "import nonexistent_module_xyz123\nprint('hi')\n"
        )
        _write_manifest(worktree, [rel])
        # relaxed=False => no quality_gates_relaxed flag.
        _write_results(
            worktree,
            "TASK-X",
            _direct_mode_results(files_created=[rel], relaxed=False),
        )

        orch = _orchestrator(worktree)
        validator = CoachValidator(str(worktree), task_id="TASK-X")

        result = orch._direct_mode_evidence_gate(
            validator,
            "TASK-X",
            1,
            _FakeWorktree(worktree),
            0.0,
            acceptance_criteria=["AC-001: deliver the producer"],
            task_type="feature",
        )

        assert result is None, "full-mode task must not be gated (AC5)"

    def test_missing_results_skips_gate(self, worktree: Path) -> None:
        """No ``task_work_results.json`` at all => gate no-ops (returns None)."""
        orch = _orchestrator(worktree)
        validator = CoachValidator(str(worktree), task_id="TASK-X")

        result = orch._direct_mode_evidence_gate(
            validator,
            "TASK-X",
            1,
            _FakeWorktree(worktree),
            0.0,
            acceptance_criteria=["AC-001"],
            task_type="feature",
        )

        assert result is None


# ---------------------------------------------------------------------------
# Scoping invariant: un-authored entries are never executed
# ---------------------------------------------------------------------------


class TestBinEntryOutsideAuthoredSetNotExecuted:
    def test_bin_entry_outside_authored_set_not_executed(
        self, worktree: Path
    ) -> None:
        """A broken manifest entry NOT authored this turn is NOT flagged.

        The scoping invariant: only authored, registered entries are executed.
        Here the broken script is registered but absent from the authored set,
        so it must not be run and must not produce a block. The authored file is
        an unrelated (non-bin-entry) path.
        """
        broken_rel = "installer/core/commands/broken.py"
        _write_bin_entry(
            worktree, broken_rel, "import nonexistent_module_xyz123\nprint('x')\n"
        )
        _write_manifest(worktree, [broken_rel])
        # Authored set contains a different, unrelated file (not the bin-entry).
        authored = "src/feature/widget.py"
        _write_bin_entry(worktree, authored, "VALUE = 1\n")
        _write_results(
            worktree, "TASK-X", _direct_mode_results(files_created=[authored])
        )

        orch = _orchestrator(worktree)
        validator = CoachValidator(str(worktree), task_id="TASK-X")

        result = orch._direct_mode_evidence_gate(
            validator,
            "TASK-X",
            1,
            _FakeWorktree(worktree),
            0.0,
            acceptance_criteria=["AC-001: deliver the widget"],
            task_type="feature",
        )

        assert result is None, "un-authored broken entry must not be executed"

    def test_unit_scoping_unauthored_entry_not_executed(
        self, worktree: Path
    ) -> None:
        """Unit-level scoping check on ``_check_direct_mode_bin_entries``."""
        broken_rel = "installer/core/commands/broken.py"
        _write_bin_entry(
            worktree, broken_rel, "import nonexistent_module_xyz123\n"
        )
        _write_manifest(worktree, [broken_rel])

        # authored_files does not include the registered broken entry.
        issues = _check_direct_mode_bin_entries(
            worktree, ["installer/core/commands/other.py"], sys.executable
        )
        assert issues == []


# ---------------------------------------------------------------------------
# Unit: classification across broken / working / timeout / non-python
# ---------------------------------------------------------------------------


class TestCheckBinEntriesClassification:
    def test_unit_check_bin_entries_classifies_traceback_absent(
        self, worktree: Path
    ) -> None:
        """A Python traceback (ModuleNotFoundError) => ``must_fix`` broken.

        Includes the stderr head in ``details`` so a false-positive is
        diagnosable in one turn.
        """
        rel = "installer/core/commands/broken.py"
        _write_bin_entry(worktree, rel, "import nonexistent_module_xyz123\n")
        _write_manifest(worktree, [rel])

        issues = _check_direct_mode_bin_entries(worktree, [rel], sys.executable)
        assert len(issues) == 1
        issue = issues[0]
        assert issue["severity"] == "must_fix"
        assert issue["category"] == "direct_mode_bin_entry_broken"
        assert rel in issue["description"]
        assert "stderr_head" in issue["details"]
        assert "ModuleNotFoundError" in issue["details"]["stderr_head"]

    def test_unit_nonzero_exit_empty_stdout_is_broken(
        self, worktree: Path
    ) -> None:
        """Non-zero exit with empty stdout (no traceback) => broken."""
        rel = "installer/core/commands/exit2.py"
        # sys.exit(2) with no stdout and no traceback.
        _write_bin_entry(worktree, rel, "import sys\nsys.exit(2)\n")
        _write_manifest(worktree, [rel])

        issues = _check_direct_mode_bin_entries(worktree, [rel], sys.executable)
        assert len(issues) == 1
        assert issues[0]["category"] == "direct_mode_bin_entry_broken"
        assert issues[0]["details"]["returncode"] == 2

    def test_unit_nonzero_exit_with_stdout_is_present(
        self, worktree: Path
    ) -> None:
        """Non-zero exit but with stdout (and no traceback) is NOT flagged.

        A producer that emitted output before a non-zero exit gave a present
        signal; only the absent-signal cases (traceback, or non-zero+empty) are
        broken.
        """
        rel = "installer/core/commands/loud_exit.py"
        _write_bin_entry(
            worktree, rel, "print('ran')\nimport sys\nsys.exit(3)\n"
        )
        _write_manifest(worktree, [rel])

        issues = _check_direct_mode_bin_entries(worktree, [rel], sys.executable)
        assert issues == []

    def test_unit_check_bin_entries_classifies_timeout_absent(
        self, worktree: Path
    ) -> None:
        """A producer that hangs past the timeout => ``must_fix`` broken."""
        rel = "installer/core/commands/slow.py"
        _write_bin_entry(worktree, rel, "import time\ntime.sleep(5)\n")
        _write_manifest(worktree, [rel])

        issues = _check_direct_mode_bin_entries(
            worktree, [rel], sys.executable, timeout_s=1
        )
        assert len(issues) == 1
        assert issues[0]["severity"] == "must_fix"
        assert issues[0]["category"] == "direct_mode_bin_entry_broken"
        assert "timed out" in issues[0]["description"]
        assert issues[0]["details"].get("timed_out") is True

    def test_unit_clean_pythonpath_overwrites_ambient(
        self, worktree: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The probe's PYTHONPATH is the worktree ONLY (overwrite, not append).

        A producer importing a module that exists ONLY on the *ambient*
        PYTHONPATH must still be flagged broken — the probe overwrites
        PYTHONPATH with the worktree, so a sibling path injected into the host's
        PYTHONPATH cannot satisfy the import and mask the failure. This is the
        crux of the false-green the gate closes (guardkit's own ``src`` on
        PYTHONPATH must not rescue a broken producer).
        """
        # A module that exists ONLY under an ambient-PYTHONPATH dir, never in
        # the worktree.
        ambient_dir = tmp_path / "ambient_libs"
        ambient_dir.mkdir()
        (ambient_dir / "ambient_only_mod_xyz.py").write_text("VALUE = 1\n")
        monkeypatch.setenv("PYTHONPATH", str(ambient_dir))

        rel = "installer/core/commands/needs_ambient.py"
        _write_bin_entry(
            worktree, rel, "import ambient_only_mod_xyz\nprint('loaded')\n"
        )
        _write_manifest(worktree, [rel])

        issues = _check_direct_mode_bin_entries(worktree, [rel], sys.executable)
        # Overwrite (not append) => the ambient dir is dropped => import fails.
        assert len(issues) == 1
        assert issues[0]["category"] == "direct_mode_bin_entry_broken"

    def test_unit_worktree_pythonpath_allows_worktree_import(
        self, worktree: Path
    ) -> None:
        """A producer importing a sibling module IN the worktree loads cleanly.

        The flip side of the overwrite: a worktree-local module IS importable
        because the worktree root is on PYTHONPATH. Confirms the overwrite does
        not over-rotate and break legitimate same-repo imports.
        """
        # Sibling package importable from the worktree root.
        (worktree / "worktree_pkg").mkdir()
        (worktree / "worktree_pkg" / "__init__.py").write_text("OK = True\n")

        rel = "installer/core/commands/uses_worktree.py"
        _write_bin_entry(
            worktree, rel, "import worktree_pkg\nprint('ok')\n"
        )
        _write_manifest(worktree, [rel])

        issues = _check_direct_mode_bin_entries(worktree, [rel], sys.executable)
        assert issues == []

    def test_unit_no_manifest_returns_empty(self, worktree: Path) -> None:
        """No ``bin-entries.txt`` => empty list (absent signal, no crash)."""
        issues = _check_direct_mode_bin_entries(
            worktree, ["installer/core/commands/whatever.py"], sys.executable
        )
        assert issues == []


# ---------------------------------------------------------------------------
# Unit: manifest parsing
# ---------------------------------------------------------------------------


class TestReadBinEntries:
    def test_read_bin_entries_ignores_comments_and_blanks(
        self, worktree: Path
    ) -> None:
        manifest = worktree / "installer" / "core" / "commands" / "bin-entries.txt"
        manifest.parent.mkdir(parents=True, exist_ok=True)
        manifest.write_text(
            "# a comment\n"
            "\n"
            "installer/core/commands/a.py\n"
            "   \n"
            "# another\n"
            "installer/core/commands/lib/b.py\n"
        )
        entries = _read_bin_entries(worktree)
        assert entries == [
            "installer/core/commands/a.py",
            "installer/core/commands/lib/b.py",
        ]

    def test_read_bin_entries_missing_manifest(self, worktree: Path) -> None:
        assert _read_bin_entries(worktree) == []


# ---------------------------------------------------------------------------
# AC2: wiring consultation on the direct-mode path
# ---------------------------------------------------------------------------

_WIRING_PATCH = (
    "guardkit.orchestrator.quality_gates.coach_validator._run_wiring_analysis"
)


def _unwired_finding(file_path: str) -> Dict[str, Any]:
    """A factory-shaped UNWIRED_PATH finding.

    Mirrors guardkitfactory wiring/analyzer.py serialisation
    (``{file, symbol, kind, severity, pattern}``): the discriminator is
    ``pattern`` (``kind`` is the *symbol* kind, e.g. "function"), NOT ``kind``.
    A gate that filtered on ``kind == "UNWIRED_PATH"`` would never fire — this
    is the dead-code regression these tests pin.
    """
    return {
        "file": file_path,
        "symbol": "main",
        "kind": "function",
        "severity": "warning",
        "pattern": "UNWIRED_PATH",
    }


class TestWiringGapBlocks:
    """AC2: an UNWIRED authored bin-entry is surfaced as feedback, not approved.

    AC1 and AC3 are arranged to PASS (AC evidence present; the producer loads
    cleanly), so the ONLY thing that can block the turn is the wiring gap —
    isolating AC2.
    """

    def test_unwired_registered_bin_entry_blocks(
        self, worktree: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        rel = "installer/core/commands/widget.py"
        _write_bin_entry(worktree, rel, "print('ok')\n")  # clean => AC3 passes
        _write_manifest(worktree, [rel])
        _write_results(
            worktree, "TASK-X", _direct_mode_results(files_created=[rel])
        )
        monkeypatch.setattr(
            _WIRING_PATCH,
            lambda **kw: {
                "wiring": {"findings": [_unwired_finding(rel)]},
                "mocked_seam": None,
                "spec_gap": None,
            },
        )

        orch = _orchestrator(worktree)
        validator = CoachValidator(str(worktree), task_id="TASK-X")
        result = orch._direct_mode_evidence_gate(
            validator,
            "TASK-X",
            1,
            _FakeWorktree(worktree),
            0.0,
            acceptance_criteria=["AC-001: deliver the producer"],
            task_type="feature",
        )

        assert result is not None, "an UNWIRED registered producer must block"
        assert result.report.get("decision") == "feedback"
        assert "direct_mode_wiring_gap" in result.report.get("rationale", "")

    def test_unwired_unregistered_path_does_not_block(
        self, worktree: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """An UNWIRED finding on an authored-but-NOT-registered file must NOT
        block (scoping / fail-open — only registered bin-entries are gated)."""
        rel = "installer/core/commands/widget.py"
        _write_bin_entry(worktree, rel, "print('ok')\n")
        _write_manifest(worktree, [rel])
        _write_results(
            worktree,
            "TASK-X",
            _direct_mode_results(files_created=[rel, "src/helper.py"]),
        )
        # UNWIRED finding points at src/helper.py — authored but not a
        # registered bin-entry, so it must not block.
        monkeypatch.setattr(
            _WIRING_PATCH,
            lambda **kw: {
                "wiring": {"findings": [_unwired_finding("src/helper.py")]},
                "mocked_seam": None,
                "spec_gap": None,
            },
        )

        orch = _orchestrator(worktree)
        validator = CoachValidator(str(worktree), task_id="TASK-X")
        result = orch._direct_mode_evidence_gate(
            validator,
            "TASK-X",
            1,
            _FakeWorktree(worktree),
            0.0,
            acceptance_criteria=["AC-001: deliver the producer"],
            task_type="feature",
        )

        assert result is None, "non-registered UNWIRED path must not block"

    def test_wiring_unavailable_does_not_block(
        self, worktree: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Factory unavailable / no findings (returns None) => absent signal,
        non-blocking (per absence-of-failure: absent != fail, but also != pass —
        the other gates still ran)."""
        rel = "installer/core/commands/widget.py"
        _write_bin_entry(worktree, rel, "print('ok')\n")
        _write_manifest(worktree, [rel])
        _write_results(
            worktree, "TASK-X", _direct_mode_results(files_created=[rel])
        )
        monkeypatch.setattr(_WIRING_PATCH, lambda **kw: None)

        orch = _orchestrator(worktree)
        validator = CoachValidator(str(worktree), task_id="TASK-X")
        result = orch._direct_mode_evidence_gate(
            validator,
            "TASK-X",
            1,
            _FakeWorktree(worktree),
            0.0,
            acceptance_criteria=["AC-001: deliver the producer"],
            task_type="feature",
        )

        assert result is None, "absent wiring signal must not block"
