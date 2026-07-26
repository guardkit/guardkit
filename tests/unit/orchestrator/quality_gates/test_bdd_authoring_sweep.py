"""Regression suite for TASK-AB-BDDAUTHOR01 — the BDD authoring sweep.

Pins AC-002..AC-008: artefact activation on authored OWNED glue; unfiltered
run over the glue modules themselves (no ``-m`` tag filter, no
``GUARDKIT_BDD_TASK_ID``); the distinct blocking ``scenarios_undefined``
counter; parallel-wave isolation by authored-files scoping; feed-back (never
terminate) disposition; and the absence semantics (timeout/exit-5/exit-4
"not found" → absent; not-importable/runner-error → synthesised blocking).

The tag-scoped oracle's pinned semantics
(``test_pending_step_recorded_distinctly``,
``test_bdd_pending_approves_with_feedback``) are asserted unchanged by their
own suites; this file additionally pins that the tag-scoped result now
carries ``scenarios_undefined == 0`` structurally.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from guardkit.orchestrator.quality_gates import bdd_runner
from guardkit.orchestrator.quality_gates.bdd_runner import (
    BDDResult,
    SWEEP_RUNNER_ERROR_SENTINELS,
    _PytestInvocation,
    glue_owned_by_task,
    run_bdd_authoring_sweep,
)
from guardkit.orchestrator.quality_gates.coach_validator import CoachValidator


TASK_ID = "TASK-SMP2-07"

_UNDEFINED_JUNIT = """\
<?xml version="1.0" encoding="utf-8"?>
<testsuites>
  <testsuite name="pytest" tests="2" failures="1" errors="0">
    <testcase classname="features.smp.test_smp__TASK_SMP2_07" name="User exports data" />
    <testcase classname="features.smp.test_smp__TASK_SMP2_07" name="User imports data">
      <failure message="StepDefinitionNotFoundError: Step definition is not found: When the user imports">
StepDefinitionNotFoundError: Step definition is not found:
When the user imports
      </failure>
    </testcase>
  </testsuite>
</testsuites>
"""

_FAILED_JUNIT = """\
<?xml version="1.0" encoding="utf-8"?>
<testsuites>
  <testsuite name="pytest" tests="1" failures="1" errors="0">
    <testcase classname="features.smp.test_smp__TASK_SMP2_07" name="User exports data">
      <failure message="AssertionError: expected 3 rows, got 0">boom</failure>
    </testcase>
  </testsuite>
</testsuites>
"""

_PASSED_JUNIT = """\
<?xml version="1.0" encoding="utf-8"?>
<testsuites>
  <testsuite name="pytest" tests="1" failures="0" errors="0">
    <testcase classname="features.smp.test_smp__TASK_SMP2_07" name="User exports data" />
  </testsuite>
</testsuites>
"""


def _make_glue(tmp_path: Path, name: str, binding: bool = True) -> Path:
    features = tmp_path / "features" / "smp"
    features.mkdir(parents=True, exist_ok=True)
    glue = features / name
    body = "from pytest_bdd import given, scenario\n"
    if binding:
        body += (
            '@scenario("smp.feature", "User exports data")\n'
            "def test_export():\n    pass\n"
        )
    glue.write_text(body)
    return glue


def _invocation(returncode: int, junit: str = "", stdout: str = "", stderr: str = ""):
    return _PytestInvocation(
        returncode=returncode, stdout=stdout, stderr=stderr, junit_xml=junit
    )


@pytest.fixture
def owned_glue(tmp_path: Path) -> Path:
    return _make_glue(tmp_path, "test_smp__TASK_SMP2_07.py")


def _run(tmp_path, glue_files, invocation, importable=True):
    with patch.object(bdd_runner, "has_pytest_bdd", return_value=importable), \
         patch.object(bdd_runner, "_invoke_pytest_sweep", return_value=invocation) as invoke:
        result = run_bdd_authoring_sweep(TASK_ID, tmp_path, glue_files)
    return result, invoke


# ---------------------------------------------------------------------------
# Sweep runner semantics
# ---------------------------------------------------------------------------


class TestRunBddAuthoringSweep:
    def test_undefined_step_counted_under_scenarios_undefined(
        self, tmp_path, owned_glue
    ):
        result, _ = _run(tmp_path, [owned_glue], _invocation(1, _UNDEFINED_JUNIT))
        assert result is not None
        assert result.scenarios_undefined == 1
        assert result.undefined[0].scenario_name == "User imports data"
        # Sweep semantics: never reported as pending (that word's
        # non-blocking meaning belongs to the tag-scoped oracle).
        assert result.scenarios_pending == 0
        assert result.pending == []
        assert result.scenarios_passed == 1

    def test_passing_glue_yields_clean_result(self, tmp_path, owned_glue):
        result, _ = _run(tmp_path, [owned_glue], _invocation(0, _PASSED_JUNIT))
        assert result is not None
        assert result.scenarios_undefined == 0
        assert result.scenarios_failed == 0
        assert result.scenarios_passed == 1

    def test_ordinary_failure_stays_in_scenarios_failed(
        self, tmp_path, owned_glue
    ):
        result, _ = _run(tmp_path, [owned_glue], _invocation(1, _FAILED_JUNIT))
        assert result is not None
        assert result.scenarios_failed == 1
        assert result.scenarios_undefined == 0

    def test_timeout_is_absent_never_synthesised_failure(
        self, tmp_path, owned_glue
    ):
        # ABFIX-010: a verification timeout is an ABSENT signal.
        result, _ = _run(
            tmp_path, [owned_glue],
            _invocation(bdd_runner._PYTEST_EXIT_TIMEOUT),
        )
        assert result is None

    def test_exit5_with_binding_constructs_is_advisory_all_zero(
        self, tmp_path, owned_glue
    ):
        result, _ = _run(tmp_path, [owned_glue], _invocation(5))
        assert result is not None
        assert result.scenarios_passed == 0
        assert result.scenarios_failed == 0
        assert result.scenarios_undefined == 0

    def test_exit5_helpers_only_glue_is_absent(self, tmp_path):
        helpers = _make_glue(tmp_path, "_steps_smp.py", binding=False)
        result, _ = _run(tmp_path, [helpers], _invocation(5))
        assert result is None

    def test_exit4_not_found_signature_is_absent(self, tmp_path, owned_glue):
        result, _ = _run(
            tmp_path, [owned_glue],
            _invocation(4, stderr="ERROR: file or directory not found: x"),
        )
        assert result is None

    def test_exit4_conftest_import_error_is_blocking_runner_error(
        self, tmp_path, owned_glue
    ):
        result, _ = _run(
            tmp_path, [owned_glue],
            _invocation(
                4, stderr="ImportError while loading conftest 'features/conftest.py'"
            ),
        )
        assert result is not None
        assert result.scenarios_failed == 1
        assert result.failures[0].scenario_name == "pytest_runner_error"

    def test_runner_error_synthesised_blocking(self, tmp_path, owned_glue):
        result, _ = _run(
            tmp_path, [owned_glue], _invocation(3, stderr="INTERNALERROR>")
        )
        assert result is not None
        assert result.failures[0].scenario_name == "pytest_runner_error"
        assert result.failures[0].scenario_name in SWEEP_RUNNER_ERROR_SENTINELS

    def test_pytest_bdd_not_importable_is_blocking_synthetic(
        self, tmp_path, owned_glue
    ):
        result, _ = _run(
            tmp_path, [owned_glue], _invocation(0), importable=False
        )
        assert result is not None
        assert result.failures[0].scenario_name == "pytest_bdd_not_importable"

    def test_no_existing_glue_is_absent(self, tmp_path):
        result, invoke = _run(
            tmp_path, [tmp_path / "features" / "missing.py"], _invocation(0)
        )
        assert result is None
        assert not invoke.called

    def test_argv_has_no_tag_filter_and_no_task_env(self, tmp_path, owned_glue):
        """The sweep is unfiltered: no ``-m`` and no GUARDKIT_BDD_TASK_ID —
        collection targets are the glue modules themselves."""
        captured = {}

        def fake_run(*args, **kwargs):
            captured["argv"] = args[0]
            captured["env"] = kwargs.get("env")
            proc = Mock()
            proc.returncode = 0
            proc.stdout = ""
            proc.stderr = ""
            return proc

        with patch.object(bdd_runner, "has_pytest_bdd", return_value=True), \
             patch.object(bdd_runner.subprocess, "run", side_effect=fake_run):
            run_bdd_authoring_sweep(TASK_ID, tmp_path, [owned_glue])

        argv = captured["argv"]
        assert "-m" not in argv
        assert captured["env"] is None  # inherited env; no task-id injection
        assert any(str(owned_glue) == a for a in argv)
        assert any("_authoring_junit.xml" in a for a in argv)

    def test_junit_written_to_authoring_name(self, tmp_path, owned_glue):
        _, invoke = _run(tmp_path, [owned_glue], _invocation(0, _PASSED_JUNIT))
        junit_path = invoke.call_args.kwargs["junit_xml_path"]
        assert junit_path.name == f"{TASK_ID}_authoring_junit.xml"


# ---------------------------------------------------------------------------
# Ownership predicate (parallel-wave / FEAT-39E1 guard)
# ---------------------------------------------------------------------------


class TestGlueOwnership:
    def test_per_task_named_glue_is_owned(self):
        assert glue_owned_by_task(
            "features/smp/test_smp__TASK_SMP2_07.py", TASK_ID, []
        )

    def test_created_this_turn_is_owned(self):
        assert glue_owned_by_task(
            "features/smp/test_smp.py", TASK_ID,
            ["features/smp/test_smp.py"],
        )

    def test_modified_legacy_glue_is_not_owned(self):
        # Editing a pre-existing shared module must not put its whole
        # binding set into this task's blocking scope (FEAT-39E1).
        assert not glue_owned_by_task(
            "features/smp/test_smp.py", TASK_ID, []
        )

    def test_sibling_task_named_glue_is_not_owned(self):
        assert not glue_owned_by_task(
            "features/smp/test_smp__TASK_SMP2_03.py", TASK_ID, []
        )


# ---------------------------------------------------------------------------
# Producer wiring (agent_invoker seam)
# ---------------------------------------------------------------------------


class TestProducerActivation:
    def _invoker(self, worktree: Path):
        from guardkit.orchestrator.agent_invoker import AgentInvoker

        invoker = AgentInvoker.__new__(AgentInvoker)
        invoker.worktree_path = worktree
        invoker._resolve_worktree_python_executable = lambda: None
        return invoker

    def test_no_glue_authored_no_sweep_no_key(self, tmp_path):
        invoker = self._invoker(tmp_path)
        results = {
            "files_authored": ["src/module.py"],
            "files_created": ["src/module.py"],
            "files_modified": [],
        }
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "module.py").write_text("x = 1\n")
        assert invoker._run_bdd_authoring_sweep(TASK_ID, results) is None

    def test_owned_glue_triggers_sweep(self, tmp_path):
        glue = _make_glue(tmp_path, "test_smp__TASK_SMP2_07.py")
        rel = str(glue.relative_to(tmp_path))
        invoker = self._invoker(tmp_path)
        results = {
            "files_authored": [rel],
            "files_created": [rel],
            "files_modified": [],
        }
        sentinel = BDDResult(scenarios_undefined=1)
        with patch(
            "guardkit.orchestrator.quality_gates.bdd_runner."
            "run_bdd_authoring_sweep",
            return_value=sentinel,
        ) as sweep:
            out = invoker._run_bdd_authoring_sweep(TASK_ID, results)
        assert sweep.called
        assert out is not None and out["scenarios_undefined"] == 1

    def test_unowned_modified_glue_is_not_swept(self, tmp_path):
        glue = _make_glue(tmp_path, "test_smp.py")  # legacy shared name
        rel = str(glue.relative_to(tmp_path))
        invoker = self._invoker(tmp_path)
        results = {
            "files_authored": [rel],
            "files_created": [],  # modified, not created
            "files_modified": [rel],
        }
        assert invoker._run_bdd_authoring_sweep(TASK_ID, results) is None

    def test_empty_files_authored_falls_back_to_created_union_modified(
        self, tmp_path
    ):
        # A Player writing glue via Bash yields files_authored=[] — the
        # sweep must not silently skip (evidence-boundary shape).
        glue = _make_glue(tmp_path, "test_smp__TASK_SMP2_07.py")
        rel = str(glue.relative_to(tmp_path))
        invoker = self._invoker(tmp_path)
        results = {
            "files_authored": [],
            "files_created": [rel],
            "files_modified": [],
        }
        sentinel = BDDResult()
        with patch(
            "guardkit.orchestrator.quality_gates.bdd_runner."
            "run_bdd_authoring_sweep",
            return_value=sentinel,
        ) as sweep:
            invoker._run_bdd_authoring_sweep(TASK_ID, results)
        assert sweep.called

    def test_sibling_glue_on_disk_never_in_targets(self, tmp_path):
        mine = _make_glue(tmp_path, "test_smp__TASK_SMP2_07.py")
        _make_glue(tmp_path, "test_smp__TASK_SMP2_03.py")  # sibling's, on disk
        rel = str(mine.relative_to(tmp_path))
        invoker = self._invoker(tmp_path)
        results = {
            "files_authored": [rel],
            "files_created": [rel],
            "files_modified": [],
        }
        with patch(
            "guardkit.orchestrator.quality_gates.bdd_runner."
            "run_bdd_authoring_sweep",
            return_value=None,
        ) as sweep:
            invoker._run_bdd_authoring_sweep(TASK_ID, results)
        targets = sweep.call_args.args[2]
        assert [p.name for p in targets] == ["test_smp__TASK_SMP2_07.py"]

    def test_per_task_glue_on_disk_rearms_sweep_without_authored_files(
        self, tmp_path
    ):
        """Review finding 2: a Player blocked on undefined steps must not be
        able to clear the deterministic gate next turn by simply not
        touching its glue — per-task-named glue on disk re-arms the sweep
        every turn."""
        _make_glue(tmp_path, "test_smp__TASK_SMP2_07.py")
        invoker = self._invoker(tmp_path)
        results = {
            "files_authored": ["src/other.py"],
            "files_created": [],
            "files_modified": ["src/other.py"],
        }
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "other.py").write_text("x = 1\n")
        sentinel = BDDResult(scenarios_undefined=1)
        with patch(
            "guardkit.orchestrator.quality_gates.bdd_runner."
            "run_bdd_authoring_sweep",
            return_value=sentinel,
        ) as sweep:
            out = invoker._run_bdd_authoring_sweep(TASK_ID, results)
        assert sweep.called
        targets = sweep.call_args.args[2]
        assert [p.name for p in targets] == ["test_smp__TASK_SMP2_07.py"]
        assert out is not None and out["scenarios_undefined"] == 1

    def test_rearm_never_picks_up_sibling_glue(self, tmp_path):
        _make_glue(tmp_path, "test_smp__TASK_SMP2_03.py")  # sibling's only
        invoker = self._invoker(tmp_path)
        results = {
            "files_authored": [],
            "files_created": [],
            "files_modified": [],
        }
        assert invoker._run_bdd_authoring_sweep(TASK_ID, results) is None

    def test_sweep_exception_is_swallowed(self, tmp_path):
        glue = _make_glue(tmp_path, "test_smp__TASK_SMP2_07.py")
        rel = str(glue.relative_to(tmp_path))
        invoker = self._invoker(tmp_path)
        results = {
            "files_authored": [rel],
            "files_created": [rel],
            "files_modified": [],
        }
        with patch(
            "guardkit.orchestrator.quality_gates.bdd_runner."
            "run_bdd_authoring_sweep",
            side_effect=RuntimeError("boom"),
        ):
            assert invoker._run_bdd_authoring_sweep(TASK_ID, results) is None


# ---------------------------------------------------------------------------
# Coach gate (_check_bdd_authoring_sweep)
# ---------------------------------------------------------------------------


def _validator() -> CoachValidator:
    return CoachValidator.__new__(CoachValidator)


class TestCheckBddAuthoringSweep:
    def test_absent_key_is_inert(self):
        blocking, non_blocking = _validator()._check_bdd_authoring_sweep({})
        assert blocking == [] and non_blocking == []

    def test_undefined_steps_block_with_both_remediations(self):
        sweep = BDDResult(
            scenarios_undefined=2,
            undefined=[
                bdd_runner.PendingDetail("m", "S1", "When the user imports"),
                bdd_runner.PendingDetail("m", "S2", "Then rows exist"),
            ],
        ).to_dict()
        blocking, _ = _validator()._check_bdd_authoring_sweep(
            {"bdd_authoring_sweep": sweep}
        )
        assert len(blocking) == 1
        issue = blocking[0]
        assert issue["severity"] == "must_fix"
        assert issue["category"] == "bdd_undefined_steps"
        # Both remediations named (review Finding 3a): implement the step OR
        # narrow the binding per bdd-per-task-glue.
        assert "implement each" in issue["description"]
        assert "bdd-per-task-glue" in issue["description"]
        assert any("When the user imports" in e for e in issue["undefined_examples"])

    def test_runner_error_sentinel_blocks(self):
        sweep = BDDResult(
            scenarios_failed=1,
            failures=[
                bdd_runner.FailureDetail(
                    "m", "pytest_runner_error", "", "pytest_runner_error: exit=3"
                )
            ],
        ).to_dict()
        blocking, _ = _validator()._check_bdd_authoring_sweep(
            {"bdd_authoring_sweep": sweep}
        )
        assert [b["category"] for b in blocking] == ["bdd_sweep_error"]

    def test_ordinary_failures_are_advisory_only(self):
        sweep = BDDResult(
            scenarios_passed=1,
            scenarios_failed=1,
            failures=[
                bdd_runner.FailureDetail("m", "S1", "step", "AssertionError")
            ],
        ).to_dict()
        blocking, non_blocking = _validator()._check_bdd_authoring_sweep(
            {"bdd_authoring_sweep": sweep}
        )
        assert blocking == []
        assert [i["category"] for i in non_blocking] == ["bdd_sweep_failure"]
        assert all(i["severity"] == "should_fix" for i in non_blocking)

    def test_all_zero_sweep_is_zero_collected_advisory(self):
        sweep = BDDResult().to_dict()
        blocking, non_blocking = _validator()._check_bdd_authoring_sweep(
            {"bdd_authoring_sweep": sweep}
        )
        assert blocking == []
        assert [i["category"] for i in non_blocking] == [
            "bdd_sweep_zero_collected"
        ]


# ---------------------------------------------------------------------------
# Deterministic both-paths gate (autobuild._bdd_authoring_sweep_gate)
# ---------------------------------------------------------------------------


class TestAutobuildSweepGate:
    def _orchestrator(self):
        from guardkit.orchestrator.autobuild import AutoBuildOrchestrator

        display = Mock()
        display.__enter__ = Mock(return_value=display)
        display.__exit__ = Mock(return_value=False)
        return AutoBuildOrchestrator(
            repo_root=Path("/tmp/test"),
            max_turns=5,
            worktree_manager=Mock(worktrees_dir=Path("/tmp/worktrees")),
            agent_invoker=Mock(),
            progress_display=display,
        )

    def _worktree(self, tmp_path):
        worktree = Mock()
        worktree.path = tmp_path
        return worktree

    def test_no_sweep_key_is_noop(self, tmp_path):
        orchestrator = self._orchestrator()
        validator = Mock()
        validator.read_quality_gate_results.return_value = {"quality_gates": {}}
        result = orchestrator._bdd_authoring_sweep_gate(
            validator, TASK_ID, 1, self._worktree(tmp_path), 0.0
        )
        assert result is None
        assert not validator._check_bdd_authoring_sweep.called

    def test_blocking_sweep_emits_synthetic_feedback(self, tmp_path):
        orchestrator = self._orchestrator()
        validator = Mock()
        validator.read_quality_gate_results.return_value = {
            "bdd_authoring_sweep": {"scenarios_undefined": 1}
        }
        validator._check_bdd_authoring_sweep.return_value = (
            [{
                "severity": "must_fix",
                "category": "bdd_undefined_steps",
                "description": "1 undefined step",
                "undefined_examples": ["S — undefined step: When x"],
            }],
            [],
        )
        result = orchestrator._bdd_authoring_sweep_gate(
            validator, TASK_ID, 1, self._worktree(tmp_path), 0.0
        )
        assert result is not None
        assert result.report["decision"] == "feedback"
        assert "undefined" in result.report["rationale"]
        # The synthetic verdict is persisted for Layer-4 consistency.
        decision_file = (
            tmp_path / ".guardkit" / "autobuild-private" / TASK_ID / "coach_turn_1.json"
        )
        assert decision_file.exists()

    def test_advisory_only_sweep_does_not_block(self, tmp_path):
        orchestrator = self._orchestrator()
        validator = Mock()
        validator.read_quality_gate_results.return_value = {
            "bdd_authoring_sweep": {"scenarios_failed": 1}
        }
        validator._check_bdd_authoring_sweep.return_value = (
            [], [{"severity": "should_fix", "category": "bdd_sweep_failure"}]
        )
        result = orchestrator._bdd_authoring_sweep_gate(
            validator, TASK_ID, 1, self._worktree(tmp_path), 0.0
        )
        assert result is None

    def test_gate_exception_fails_open(self, tmp_path):
        orchestrator = self._orchestrator()
        validator = Mock()
        validator.read_quality_gate_results.return_value = {
            "bdd_authoring_sweep": {}
        }
        validator._check_bdd_authoring_sweep.side_effect = RuntimeError("boom")
        result = orchestrator._bdd_authoring_sweep_gate(
            validator, TASK_ID, 1, self._worktree(tmp_path), 0.0
        )
        assert result is None


# ---------------------------------------------------------------------------
# Serialization journey (absence-must-survive)
# ---------------------------------------------------------------------------


class TestSerializationJourney:
    def test_to_dict_always_carries_undefined_fields(self):
        d = BDDResult().to_dict()
        assert d["scenarios_undefined"] == 0
        assert d["undefined"] == []

    def test_evidence_bundle_has_sweep_field(self):
        import dataclasses

        from guardkit.orchestrator.quality_gates.coach_evidence import (
            CoachEvidenceBundle,
        )

        names = {f.name for f in dataclasses.fields(CoachEvidenceBundle)}
        assert "bdd_authoring_sweep" in names
