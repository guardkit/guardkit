"""THE PER-COMPONENT SEAM on the VERDICT path (CoachValidator).

The defect, stated once: study-tutor is a Python backend at the root and a
Flutter app under ``app/``. One flat ``test:`` cannot be right for both — add
the backend's and every ``app/`` task silently gets the Python suite as its
verdict on Dart work; add the app's and every backend task gets ``flutter
test``. So the task says which component it is, and the declaration says what
that component's command is and WHERE it runs.

Four things are pinned here:

1. **The task's component is resolved FIRST** — its declared command is the
   oracle, and no rung of the ladder below may pre-empt it or follow it.
2. **``cwd`` is real** — proved by a REAL subprocess that records the
   directory it actually ran in, not by a mocked kwarg alone. ``flutter test``
   needs the package root; ``cd app && …`` inside a command string is
   invisible to the snapshot reader and to anyone auditing the receipt.
3. **An unresolvable component NEVER falls back to the root command** — it is
   a loud INSTRUMENT FAULT (ABSENT / UNKNOWN), never a pass and never a
   Player test failure.
4. **Everything else is byte-unchanged** — no component key, or no
   declaration at all, resolves exactly what it resolved before, at the same
   cwd, through the same branch.

Network-free and broker-free: the only subprocesses are ``pwd``/``true``/
``false`` against a temp directory.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import yaml

from guardkit.orchestrator.quality_gates.coach_validator import (
    CoachValidator,
    IndependentTestResult,
)
from guardkit.orchestrator.toolchain_declaration import snapshot_task_toolchain

_TASK_ID = "TASK-PC-042"

# The study-tutor SHAPE, with the commands stubbed: the resolution and the cwd
# are what is under test, not Flutter itself.
STUDY_TUTOR_SHAPE = {
    "test": "uv run --no-sync python -m pytest -q",
    "components": {
        "app": {
            "cwd": "app",
            "test": "flutter test",
            "install": "flutter pub get",
            "test_timeout": 900,
        },
    },
}


def _write_config(root, block):
    cfg = root / ".guardkit"
    cfg.mkdir(parents=True, exist_ok=True)
    (cfg / "config.yaml").write_text(
        yaml.safe_dump({"toolchain": block}), encoding="utf-8"
    )


@pytest.fixture
def repo(tmp_path):
    """Repo root + the worktree beneath it, with the ``app/`` component dir."""
    root = tmp_path / "study-tutor"
    worktree = root / ".guardkit" / "worktrees" / _TASK_ID
    worktree.mkdir(parents=True)
    (worktree / "app").mkdir()
    (worktree / "pyproject.toml").touch()
    return root, worktree


def _validator(root, worktree, block, **kwargs):
    """Declare, snapshot pre-turn-1, then build the validator — the real
    sequence, so these tests exercise the snapshot seam too."""
    _write_config(root, block)
    snapshot_task_toolchain(_TASK_ID, worktree, root)
    kwargs.setdefault("task_id", _TASK_ID)
    return CoachValidator(str(worktree), **kwargs)


# =========================================================================
# 1. Resolution — the component's command, or the root's
# =========================================================================


class TestComponentCommandResolution:
    def test_a_component_task_gets_the_components_command(self, repo):
        root, worktree = repo
        v = _validator(root, worktree, STUDY_TUTOR_SHAPE, component="app")
        assert v._detect_test_command(_TASK_ID) == "flutter test"

    def test_a_task_with_no_component_gets_the_root_command(self, repo):
        """Today's semantics, unchanged, in the SAME repo and the SAME
        declaration — the §E stage-3 exit receipt in one assertion pair."""
        root, worktree = repo
        v = _validator(root, worktree, STUDY_TUTOR_SHAPE)
        assert v._detect_test_command(None) == "uv run --no-sync python -m pytest -q"

    def test_both_oracles_come_out_of_one_declaration(self, repo):
        root, worktree = repo
        _write_config(root, STUDY_TUTOR_SHAPE)
        snapshot_task_toolchain(_TASK_ID, worktree, root)
        app = CoachValidator(str(worktree), task_id=_TASK_ID, component="app")
        backend = CoachValidator(str(worktree), task_id=_TASK_ID)
        assert app._detect_test_command(None) == "flutter test"
        assert backend._detect_test_command(None) != app._detect_test_command(None)

    def test_the_component_outranks_the_python_task_specific_rung(self, repo):
        """A component task must NOT be judged by whatever ``.py`` files
        happened to be touched — that rung is about the root component."""
        root, worktree = repo
        tests_dir = worktree / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_task_pc_042_thing.py").touch()
        v = _validator(root, worktree, STUDY_TUTOR_SHAPE, component="app")
        assert v._detect_test_command(_TASK_ID) == "flutter test"

    def test_the_control_without_a_component_still_takes_that_rung(self, repo):
        root, worktree = repo
        tests_dir = worktree / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_task_pc_042_thing.py").touch()
        v = _validator(root, worktree, STUDY_TUTOR_SHAPE)
        cmd = v._detect_test_command(_TASK_ID)
        assert cmd.startswith("pytest ")
        assert "test_task_pc_042_thing.py" in cmd

    def test_the_component_is_honoured_in_a_parallel_wave(self, repo):
        root, worktree = repo
        v = _validator(root, worktree, STUDY_TUTOR_SHAPE, component="app", wave_size=4)
        assert v.is_parallel is True
        assert v._detect_test_command(_TASK_ID) == "flutter test"

    def test_the_components_test_timeout_is_honoured(self, repo):
        root, worktree = repo
        v = _validator(root, worktree, STUDY_TUTOR_SHAPE, component="app")
        assert v.test_timeout == 900

    def test_the_root_timeout_applies_to_a_component_less_task(self, repo):
        root, worktree = repo
        v = _validator(root, worktree, STUDY_TUTOR_SHAPE)
        assert v.test_timeout == 300

    def test_an_explicit_caller_timeout_still_wins(self, repo):
        root, worktree = repo
        v = _validator(
            root, worktree, STUDY_TUTOR_SHAPE, component="app", test_timeout=120
        )
        assert v.test_timeout == 120

    def test_a_components_classifier_overlay_is_the_components_own(self, repo):
        root, worktree = repo
        (worktree / "app" / "package.json").touch()  # a node row in the SUBDIR
        v = _validator(
            root,
            worktree,
            {
                "test": "pytest -q",
                "components": {
                    "app": {
                        "cwd": "app",
                        "test": "npx vitest run",
                        "absent_substrings": ["no test files found"],
                    }
                },
            },
            component="app",
        )
        v._detect_test_command(_TASK_ID)
        profile = v._active_stack_profile
        assert profile is not None
        assert profile.stack == "node"  # matched in app/, not at the root
        assert profile.absent_substrings == ("no test files found",)


# =========================================================================
# 2. cwd — the field that makes it real
# =========================================================================


class TestComponentCwd:
    def test_the_declared_command_runs_in_the_components_directory(self, repo):
        root, worktree = repo
        v = _validator(root, worktree, STUDY_TUTOR_SHAPE, component="app")
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="All tests passed", stderr="")
            v.run_independent_tests()
        kwargs = mock_run.call_args.kwargs
        assert kwargs["shell"] is True
        assert kwargs["cwd"] == str(worktree / "app")
        assert kwargs["timeout"] == 900

    def test_a_real_subprocess_actually_runs_there(self, repo):
        """THE MARKER FLIP: no mock. The command records the directory it was
        really executed in, and the marker lands in the component's dir."""
        root, worktree = repo
        v = _validator(
            root,
            worktree,
            {
                "test": "pwd > ran_here.txt",
                "components": {
                    "app": {"cwd": "app", "test": "pwd > ran_here.txt"}
                },
            },
            component="app",
        )
        result = v.run_independent_tests()
        assert result.tests_passed is True
        marker = worktree / "app" / "ran_here.txt"
        assert marker.exists(), "the component's command did not run in app/"
        assert not (worktree / "ran_here.txt").exists()
        assert Path(marker.read_text().strip()).resolve() == (worktree / "app").resolve()

    def test_the_control_runs_at_the_worktree_root(self, repo):
        """Same command, no component: the marker lands at the root. This is
        the byte-unchanged half of the same experiment."""
        root, worktree = repo
        v = _validator(
            root,
            worktree,
            {
                "test": "pwd > ran_here.txt",
                "components": {"app": {"cwd": "app", "test": "pwd > ran_here.txt"}},
            },
        )
        result = v.run_independent_tests()
        assert result.tests_passed is True
        marker = worktree / "ran_here.txt"
        assert marker.exists()
        assert not (worktree / "app" / "ran_here.txt").exists()
        assert Path(marker.read_text().strip()).resolve() == worktree.resolve()

    def test_a_real_failing_component_command_is_a_real_red(self, repo):
        """The verdict is still the exit code, from the component's dir."""
        root, worktree = repo
        v = _validator(
            root,
            worktree,
            {"components": {"app": {"cwd": "app", "test": "false"}}},
            component="app",
        )
        result = v.run_independent_tests()
        assert result.tests_passed is False
        assert result.signal_absent is False

    def test_a_nested_component_cwd_resolves(self, repo):
        root, worktree = repo
        (worktree / "clients").mkdir()
        (worktree / "clients" / "web").mkdir()
        v = _validator(
            root,
            worktree,
            {"components": {"web": {"cwd": "clients/web", "test": "pwd > here.txt"}}},
            component="web",
        )
        v.run_independent_tests()
        assert (worktree / "clients" / "web" / "here.txt").exists()

    def test_a_declared_pytest_component_keeps_the_interpreter_pin(self, repo):
        """A component whose command IS pytest still takes the venv-pinned
        ``python -m pytest`` branch — with the component's cwd."""
        root, worktree = repo
        v = _validator(
            root,
            worktree,
            {
                "test": "pytest -q",
                "components": {
                    "backend": {"cwd": "app", "test": "pytest tests/ -v --tb=short"}
                },
            },
            component="backend",
        )
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="5 passed", stderr="")
            v.run_independent_tests()
        argv = mock_run.call_args.args[0]
        assert argv[1:3] == ["-m", "pytest"]
        assert mock_run.call_args.kwargs["cwd"] == str(worktree / "app")

    def test_the_parallel_isolated_copy_also_runs_in_the_component_dir(self, repo):
        """The isolated copy is a copy of the WHOLE worktree, so the component
        exists inside it at the same relative path."""
        root, worktree = repo
        v = _validator(
            root, worktree, STUDY_TUTOR_SHAPE, component="app", wave_size=4
        )
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")
            v.run_independent_tests()
        cwd = Path(mock_run.call_args.kwargs["cwd"])
        assert cwd.name == "app"
        assert cwd.parent != worktree  # the temp copy, not the live worktree
        assert "guardkit-coach-iso-" in str(cwd)

    def test_a_component_forces_the_deterministic_subprocess_path(self, repo):
        """The SDK path bakes ``cwd=worktree`` into the harness call, so a
        component task must not take it (and says so at WARNING)."""
        root, worktree = repo
        v = _validator(
            root,
            worktree,
            STUDY_TUTOR_SHAPE,
            component="app",
            coach_test_execution="sdk",
        )
        with patch.object(
            CoachValidator, "_is_custom_api_base", return_value=False
        ), patch.object(
            CoachValidator, "_is_langgraph_harness", return_value=False
        ), patch.object(
            CoachValidator, "_run_tests_via_sdk", new_callable=AsyncMock
        ) as mock_sdk, patch(
            "subprocess.run"
        ) as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")
            v.run_independent_tests()
        mock_sdk.assert_not_called()
        assert mock_run.call_args.kwargs["cwd"] == str(worktree / "app")

    def test_the_control_without_a_component_still_reaches_the_sdk_path(self, repo):
        """Proves the guard above is what redirected the run, not the env."""
        root, worktree = repo
        v = _validator(
            root, worktree, STUDY_TUTOR_SHAPE, coach_test_execution="sdk"
        )
        with patch.object(
            CoachValidator, "_is_custom_api_base", return_value=False
        ), patch.object(
            CoachValidator, "_is_langgraph_harness", return_value=False
        ), patch.object(
            CoachValidator, "_run_tests_via_sdk", new_callable=AsyncMock
        ) as mock_sdk:
            mock_sdk.return_value = IndependentTestResult.absent(
                test_command="x", test_output_summary="y", duration_seconds=0.0
            )
            v.run_independent_tests()
        mock_sdk.assert_called_once()


# =========================================================================
# 3. An unresolvable component is ABSENT — never the root command
# =========================================================================


class TestComponentAbsence:
    def test_an_undeclared_component_never_runs_the_root_command(self, repo):
        root, worktree = repo
        v = _validator(root, worktree, STUDY_TUTOR_SHAPE, component="api")
        assert v._detect_test_command(_TASK_ID) is None
        assert "INSTRUMENT FAULT" in v._detection_absence
        assert "api" in v._detection_absence
        assert "NOT used as a fallback" in v._detection_absence

    def test_that_absence_is_unknown_never_a_pass_and_never_a_failure(self, repo):
        root, worktree = repo
        v = _validator(root, worktree, STUDY_TUTOR_SHAPE, component="api")
        with patch("subprocess.run") as mock_run:
            result = v.run_independent_tests()
        mock_run.assert_not_called()  # no substituted command was executed
        assert result.signal_absent is True
        assert result.tests_passed is False
        assert "INSTRUMENT FAULT" in result.test_output_summary

    def test_the_absence_is_loud(self, repo, caplog):
        root, worktree = repo
        with caplog.at_level("ERROR"):
            v = _validator(root, worktree, STUDY_TUTOR_SHAPE, component="api")
            v._detect_test_command(_TASK_ID)
        assert any(r.levelname == "ERROR" for r in caplog.records)

    def test_a_component_declaring_no_test_command_says_so(self, repo):
        root, worktree = repo
        v = _validator(
            root,
            worktree,
            {
                "test": "pytest -q",
                "components": {"app": {"cwd": "app", "install": "flutter pub get"}},
            },
            component="app",
        )
        assert v._detect_test_command(_TASK_ID) is None
        assert "declares no `test:` command" in v._detection_absence
        assert "component: app" in v._detection_absence

    def test_no_snapshot_means_a_component_task_cannot_be_served(self, repo):
        """THE §B.4 LAW at the executor: a config the Player wrote into the
        worktree with NO pre-turn-1 snapshot is invisible, components and
        all — and the absence is loud rather than a root-block fallback."""
        root, worktree = repo
        _write_config(worktree, STUDY_TUTOR_SHAPE)  # Player-side only
        v = CoachValidator(str(worktree), task_id=_TASK_ID, component="app")
        assert v._detect_test_command(None) is None
        assert "INSTRUMENT FAULT" in v._detection_absence

    def test_a_pinned_component_survives_a_mid_build_config_rewrite(self, repo):
        """THE ATTACK, end to end: the Player rewrites the component's command
        to ``true`` in both trees after the pin; the pinned command is what
        the validator resolves."""
        root, worktree = repo
        v = _validator(root, worktree, STUDY_TUTOR_SHAPE, component="app")
        self_green = {
            "test": "true",
            "components": {"app": {"cwd": "app", "test": "true"}},
        }
        _write_config(worktree, self_green)
        _write_config(root, self_green)
        assert v._detect_test_command(_TASK_ID) == "flutter test"


# =========================================================================
# 4. Back-compat: no component anywhere ⇒ byte-unchanged
# =========================================================================


class TestBackCompat:
    def test_a_flat_declaration_is_resolved_and_run_exactly_as_before(self, tmp_path):
        root = tmp_path / "flat"
        worktree = root / ".guardkit" / "worktrees" / _TASK_ID
        worktree.mkdir(parents=True)
        (worktree / "package.json").touch()
        v = _validator(root, worktree, {"test": "npm test"})
        assert v._detect_test_command(None) == "npm test"
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")
            v.run_independent_tests()
        assert mock_run.call_args.kwargs["cwd"] == str(worktree)

    def test_a_repo_with_no_declaration_is_untouched(self, tmp_path):
        (tmp_path / "pyproject.toml").touch()
        v = CoachValidator(str(tmp_path))
        assert v._detect_test_command(None) == "pytest tests/ -v --tb=short"
        assert v._component is None
        assert v._component_toolchain is None

    def test_the_run_cwd_helper_is_identity_without_a_component(self, tmp_path):
        """The one-line guarantee behind 'every other path byte-unchanged'."""
        v = CoachValidator(str(tmp_path))
        assert v._component_run_cwd(tmp_path) == tmp_path
        other = tmp_path / "elsewhere"
        assert v._component_run_cwd(other) == other

    def test_a_symlinked_component_cwd_is_refused_as_absent(self, repo, tmp_path):
        """The runtime containment re-check (a symlink no schema can see):
        the run is REFUSED, and the refusal surfaces as ABSENT — never a run
        relocated to the worktree root, and never a pass."""
        root, worktree = repo
        outside = tmp_path / "outside"
        outside.mkdir()
        (worktree / "app").rmdir()
        (worktree / "app").symlink_to(outside, target_is_directory=True)
        v = _validator(root, worktree, STUDY_TUTOR_SHAPE, component="app")
        with patch("subprocess.run") as mock_run:
            result = v.run_independent_tests()
        mock_run.assert_not_called()
        assert result.signal_absent is True
        assert result.tests_passed is False


def test_declared_test_command_second_belt_never_falls_to_root():
    """Coordinator pin (the PC coach's surviving mutant): the belt INSIDE
    _declared_test_command must hold on its own — a named-but-undeclared
    component returns None, NEVER the root command, even if the earlier
    absence-return is ever reordered away."""
    from types import SimpleNamespace

    from guardkit.orchestrator.quality_gates.coach_validator import CoachValidator

    v = object.__new__(CoachValidator)
    v._component_toolchain = None
    v._component = "app"
    v._toolchain = SimpleNamespace(test="pytest -q")
    assert v._declared_test_command() is None
