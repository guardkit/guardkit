"""Part N of the rewrite-on-refusal spec (2026-09-07, rules 58-60): a repair's
work leg has an interpreter.

Journey one's second attempt: the review leg passed and wrote three fix tasks;
all three work legs failed at once with "Autobuild interpreter-resolution
FAILED ... no worktree venv interpreter resolved". The work leg runs the
orchestrator on an existing worktree with the pre-loop off and never
bootstrapped, so on a Python repository it could resolve no interpreter.

What runs for real here: the task loader, the requirements threading, the
receipt writer, ``probe_worktree_venv`` (the Coach verifier's own probe),
``ProjectEnvironmentDetector`` and ``EnvironmentBootstrapper`` — including the
real ``uv venv --seed`` that creates ``<worktree>/.venv`` and the real state
file that makes a second bootstrap a skip. The orchestrator is a recording
double at the leg's factory seam (a Player-Coach run is not this suite's job).
The one thing faked, and only where the real one would have to fetch a build
backend from the network, is the bootstrapper's install subprocess
(``EnvironmentBootstrapper._run_install``) — the venv creation and the
interpreter path are proven for real in every test.
"""

from __future__ import annotations

import json
import shlex
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any, Dict, List

import pytest

from guardkit.orchestrator import work_runner
from guardkit.orchestrator.environment_bootstrap import (
    EnvironmentBootstrapper,
    UvSourcesRequireUvError,
)
from guardkit.orchestrator.work_runner import (
    BOOTSTRAP_STATE_RELPATH,
    INTERPRETER_SOURCES,
    InterpreterProvision,
    bootstrap_worktree,
    provision_interpreter,
    run_work_leg,
    write_receipt,
)

pytestmark = pytest.mark.skipif(
    sys.platform == "win32", reason="the bootstrap's venv layout is POSIX bin/python"
)

# ===========================================================================
# The temp projects
# ===========================================================================

FIX_TASK_ID = "TASK-TINY-001-make-the-tiny-project-count"

FIX_TASK_BODY = f"""---
id: {FIX_TASK_ID}
title: Make the tiny project count
status: backlog
priority: medium
complexity: 2
task_type: fix
---

# Make the tiny project count

## Description

The tiny project should count. Make its one test pass.

## Acceptance Criteria

- [ ] AC-1: tests/test_tiny.py passes under the worktree's own interpreter
"""

# No third-party dependencies, no requires-python (a pin would make ``uv venv``
# ask for a specific interpreter, which could mean a download). No build
# backend either: the project is deliberately "incomplete" for the
# bootstrapper (no ``tinyproj/`` source directory), so its real path creates
# the venv and finds no install to run — the fully-real, network-free leg.
PYPROJECT = """[project]
name = "tinyproj"
version = "0.0.1"
description = "a tiny project with no third-party dependencies"
"""

TEST_FILE = """def test_tiny_counts():
    assert 1 + 1 == 2
"""

APPROVED_STDERR = "ERROR: No matching distribution found for nothing==9.9"


def _git(args: List[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=str(cwd), capture_output=True, text=True, check=True
    )


def _seed_repo(root: Path, files: Dict[str, str]) -> Path:
    for rel, content in files.items():
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    task_dir = root / "tasks" / "backlog" / "repair"
    task_dir.mkdir(parents=True, exist_ok=True)
    (task_dir / f"{FIX_TASK_ID}.md").write_text(FIX_TASK_BODY, encoding="utf-8")
    _git(["init", "-b", "main"], root)
    _git(["config", "user.email", "leg@example.test"], root)
    _git(["config", "user.name", "Work Leg"], root)
    _git(["add", "-A", "."], root)
    _git(["commit", "-m", "seed"], root)
    return root


@pytest.fixture
def python_repo(tmp_path: Path) -> Path:
    """A tiny Python project (pyproject, one pytest file) with no ``.venv``."""
    return _seed_repo(
        tmp_path / "worktree",
        {"pyproject.toml": PYPROJECT, "tests/test_tiny.py": TEST_FILE},
    )


@pytest.fixture
def complete_python_repo(tmp_path: Path) -> Path:
    """The same project with its source directory present, so the bootstrap
    has a real install command to run (``<venv>/bin/python -m pip install -e .``).
    That command needs a build backend from the network, so tests on this
    fixture fake the install subprocess and nothing else."""
    return _seed_repo(
        tmp_path / "worktree",
        {
            "pyproject.toml": PYPROJECT,
            "tinyproj/__init__.py": "COUNT = 1\n",
            "tests/test_tiny.py": TEST_FILE,
        },
    )


@pytest.fixture
def plain_repo(tmp_path: Path) -> Path:
    """Not a Python project: a README and the fix task, nothing else."""
    return _seed_repo(tmp_path / "worktree", {"README.md": "seed\n"})


# ===========================================================================
# The orchestrator double at the factory seam
# ===========================================================================


class FakeResult:
    def __init__(self, success: bool = True, final_decision: str = "approved") -> None:
        self.success = success
        self.final_decision = final_decision
        self.total_turns = 1
        self.turn_history: List[Any] = []
        self.error = None


class RecordingOrchestrator:
    def __init__(self) -> None:
        self.orchestrate_kwargs: Dict[str, Any] = {}

    def orchestrate(self, **kwargs: Any) -> FakeResult:
        self.orchestrate_kwargs = kwargs
        return FakeResult()


@pytest.fixture
def factory(monkeypatch):
    """Install a recording double at ``work_runner._build_orchestrator``.

    ``holder.calls`` is every kwargs dict the factory was built with — empty
    when the leg refused before constructing an orchestrator."""

    class Holder:
        calls: List[Dict[str, Any]] = []

    holder = Holder()
    holder.calls = []

    def build(**kwargs: Any) -> RecordingOrchestrator:
        holder.calls.append(kwargs)
        return RecordingOrchestrator()

    monkeypatch.setattr(work_runner, "_build_orchestrator", build)
    return holder


@pytest.fixture
def install_spy(monkeypatch):
    """Count the bootstrapper's two subprocess steps without changing them:
    venv creation stays real; the install is replaced by a recorder that
    returns the outcome the test asks for (default: success)."""

    class Spy:
        venv_creations = 0
        installs: List[str] = []
        install_ok = True
        install_stderr = ""

    spy = Spy()
    spy.installs = []
    real_ensure = EnvironmentBootstrapper._ensure_worktree_venv

    def counting_ensure(self, worktree, requires_python=None):
        spy.venv_creations += 1
        return real_ensure(self, worktree, requires_python)

    def fake_install(self, manifest) -> bool:
        cmd = list(manifest.install_command)
        if self._venv_python and cmd and cmd[0] == sys.executable:
            cmd[0] = str(self._venv_python)
        spy.installs.append(shlex.join(cmd))
        self._last_failure_stderr = spy.install_stderr if not spy.install_ok else ""
        self._last_failure_is_pep668 = False
        return spy.install_ok

    monkeypatch.setattr(EnvironmentBootstrapper, "_ensure_worktree_venv", counting_ensure)
    monkeypatch.setattr(EnvironmentBootstrapper, "_run_install", fake_install)
    return spy


def _run_leg(repo: Path, **kwargs: Any):
    return run_work_leg(task_id=FIX_TASK_ID, repo_root=repo, **kwargs)


def _receipt(repo: Path, outcome) -> Dict[str, Any]:
    path = write_receipt(outcome, repo_root=repo, build_id="build-test", correlation_id="cid")
    assert path is not None
    return json.loads(path.read_text(encoding="utf-8"))


def _venv_python(repo: Path) -> Path:
    return repo / ".venv" / "bin" / "python"


def _state_file(repo: Path) -> Path:
    return repo / BOOTSTRAP_STATE_RELPATH


def _interpreter_prefix(python: str) -> Path:
    out = subprocess.run(
        [python, "-c", "import sys; print(sys.prefix)"],
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    )
    return Path(out.stdout.strip()).resolve()


# ===========================================================================
# Rule 58 — a Python worktree with no interpreter is bootstrapped, once
# ===========================================================================


class TestPythonWorktreeWithoutVenv:
    def test_the_leg_bootstraps_for_real_and_the_orchestrator_gets_the_venv(
        self, python_repo, factory
    ):
        """No fakes below the factory seam: the real detector, the real
        bootstrapper, a real ``uv venv``. The orchestrator is constructed with
        the interpreter the bootstrap produced, and that interpreter runs."""
        assert not _venv_python(python_repo).exists()

        outcome = _run_leg(python_repo)

        assert outcome.status == "approved", outcome.error
        assert _venv_python(python_repo).exists()
        assert len(factory.calls) == 1
        assert factory.calls[0]["venv_python"] == str(_venv_python(python_repo))
        assert outcome.interpreter == {
            "path": str(_venv_python(python_repo)),
            "source": "bootstrapped",
        }
        assert outcome.bootstrap["ran"] is True
        assert outcome.bootstrap["skipped"] is False
        assert outcome.bootstrap["success"] is True
        assert outcome.bootstrap["stacks_detected"] == ["python"]
        # The bootstrapper's own record is on disk and says it succeeded.
        state = json.loads(_state_file(python_repo).read_text(encoding="utf-8"))
        assert state["success"] is True
        assert state["venv_python"] == str(_venv_python(python_repo))
        # The interpreter is real: it runs, and it is the worktree's own venv.
        assert _interpreter_prefix(outcome.interpreter["path"]) == (
            python_repo / ".venv"
        ).resolve()

    def test_the_receipt_names_the_interpreter_and_its_source(
        self, python_repo, factory
    ):
        outcome = _run_leg(python_repo)
        receipt = _receipt(python_repo, outcome)
        assert receipt["interpreter"] == {
            "path": str(_venv_python(python_repo)),
            "source": "bootstrapped",
        }
        assert receipt["interpreter"]["source"] in INTERPRETER_SOURCES
        assert receipt["bootstrap"]["ran"] is True
        assert receipt["bootstrap"]["state_file"] == str(_state_file(python_repo))
        assert receipt["status"] == "approved"

    def test_a_second_leg_in_the_same_worktree_does_not_bootstrap_again(
        self, python_repo, factory, install_spy
    ):
        """Legs two and three of a cycle reuse leg one's environment: the
        worktree now has an interpreter, so it is never touched."""
        first = _run_leg(python_repo)
        assert first.interpreter["source"] == "bootstrapped"
        assert install_spy.venv_creations == 1
        state_before = _state_file(python_repo).read_bytes()

        second = _run_leg(python_repo)

        assert second.status == "approved", second.error
        assert second.interpreter == {
            "path": first.interpreter["path"],
            "source": "worktree",
        }
        assert second.bootstrap is None
        assert install_spy.venv_creations == 1
        assert install_spy.installs == []
        assert _state_file(python_repo).read_bytes() == state_before
        assert [c["venv_python"] for c in factory.calls] == [
            first.interpreter["path"],
            first.interpreter["path"],
        ]

    def test_the_bootstraps_own_saved_state_makes_a_second_bootstrap_a_skip(
        self, python_repo, install_spy
    ):
        """The idempotence the leg relies on, proven at the bootstrap itself:
        the same call twice, the second is a hash-match skip that still hands
        back the same interpreter, and the venv is created once."""
        first = bootstrap_worktree(python_repo)
        second = bootstrap_worktree(python_repo)

        assert first.error is None and second.error is None
        assert first.bootstrap["skipped"] is False
        assert second.bootstrap["skipped"] is True
        assert first.path == second.path == str(_venv_python(python_repo))
        assert first.source == second.source == "bootstrapped"
        assert install_spy.venv_creations == 1

    def test_a_complete_project_runs_the_install_through_the_worktree_venv(
        self, complete_python_repo, factory, install_spy
    ):
        """With a source directory present the bootstrap has an install to run;
        the command it runs is the venv's own python (the bootstrapper's remap),
        and the receipt names it."""
        outcome = _run_leg(complete_python_repo)

        expected = shlex.join(
            [str(_venv_python(complete_python_repo)), "-m", "pip", "install", "-e", "."]
        )
        assert outcome.status == "approved", outcome.error
        assert install_spy.venv_creations == 1
        assert install_spy.installs == [expected]
        assert outcome.bootstrap["commands"] == [expected]
        assert outcome.bootstrap["installs_attempted"] == 1
        assert outcome.bootstrap["installs_failed"] == 0
        assert factory.calls[0]["venv_python"] == str(_venv_python(complete_python_repo))


# ===========================================================================
# Rule 58 — a worktree that already has an interpreter is never touched
# ===========================================================================


class TestWorktreeWithVenvPresent:
    def test_a_present_venv_is_used_as_is(self, python_repo, factory, install_spy):
        python = _venv_python(python_repo)
        python.parent.mkdir(parents=True)
        python.write_text("#!/bin/sh\n", encoding="utf-8")

        outcome = _run_leg(python_repo)

        assert outcome.status == "approved", outcome.error
        assert factory.calls[0]["venv_python"] == str(python)
        assert outcome.interpreter == {"path": str(python), "source": "worktree"}
        assert outcome.bootstrap is None
        assert install_spy.venv_creations == 0
        assert install_spy.installs == []
        assert not _state_file(python_repo).exists()

    def test_the_legacy_location_is_the_second_probe(
        self, python_repo, factory, install_spy
    ):
        """The Coach verifier's second location, ``.guardkit/venv/bin/python``."""
        legacy = python_repo / ".guardkit" / "venv" / "bin" / "python"
        legacy.parent.mkdir(parents=True)
        legacy.write_text("#!/bin/sh\n", encoding="utf-8")

        outcome = _run_leg(python_repo)

        assert outcome.interpreter == {"path": str(legacy), "source": "worktree"}
        assert factory.calls[0]["venv_python"] == str(legacy)
        assert install_spy.venv_creations == 0


# ===========================================================================
# Rule 58 — a non-Python worktree is unchanged
# ===========================================================================


class TestNonPythonWorktree:
    def test_a_non_python_worktree_is_unchanged(self, plain_repo, factory, install_spy):
        outcome = _run_leg(plain_repo)

        assert outcome.status == "approved", outcome.error
        assert factory.calls[0]["venv_python"] is None
        assert outcome.interpreter is None
        assert outcome.bootstrap is None
        assert install_spy.venv_creations == 0
        assert not (plain_repo / ".venv").exists()
        assert not _state_file(plain_repo).exists()
        receipt = _receipt(plain_repo, outcome)
        assert receipt["interpreter"] is None
        assert receipt["bootstrap"] is None


# ===========================================================================
# Rule 59 — a bootstrap failure is the leg's own sentence, naming the command
# ===========================================================================


class TestBootstrapFailure:
    def test_a_failed_install_fails_the_leg_naming_the_command(
        self, complete_python_repo, factory, install_spy
    ):
        install_spy.install_ok = False
        install_spy.install_stderr = APPROVED_STDERR

        outcome = _run_leg(complete_python_repo)

        expected = shlex.join(
            [str(_venv_python(complete_python_repo)), "-m", "pip", "install", "-e", "."]
        )
        assert outcome.status == "failed"
        assert outcome.exit_code == 2
        assert factory.calls == [], "the orchestrator must never be built without an interpreter"
        assert expected in outcome.error
        assert str(complete_python_repo) in outcome.error
        assert APPROVED_STDERR in outcome.error
        assert "no worktree venv interpreter resolved" not in outcome.error
        assert "interpreter-resolution FAILED" not in outcome.error
        # The venv creation half ran for real before the install failed.
        assert _venv_python(complete_python_repo).exists()
        assert install_spy.venv_creations == 1
        assert outcome.interpreter is None
        assert outcome.bootstrap["success"] is False
        assert outcome.bootstrap["installs_failed"] == 1
        assert outcome.bootstrap["failures"][0]["commands"] == [expected]
        assert outcome.bootstrap["failures"][0]["stderr_excerpt"] == APPROVED_STDERR
        # The residual channel carries the sentence, anchored like every residual.
        assert outcome.findings and outcome.findings[0]["severity"] == "must_fix"
        assert expected in outcome.findings[0]["detail"]
        receipt = _receipt(complete_python_repo, outcome)
        assert receipt["exit_code"] == 2
        assert receipt["interpreter"] is None
        assert expected in receipt["error"]

    def test_a_failed_bootstrap_inside_its_cooldown_still_fails_the_next_leg(
        self, complete_python_repo, factory, install_spy
    ):
        """After a failed install the bootstrap leaves ``.venv`` behind and
        its record says it failed. The next leg must not take that venv on
        trust (the Coach would approve "with environment flag" on it): it runs
        the bootstrap again, which is inside its own retry cooldown and skips,
        and the leg says so and stops."""
        install_spy.install_ok = False
        install_spy.install_stderr = APPROVED_STDERR
        first = _run_leg(complete_python_repo)
        assert first.status == "failed"
        assert _venv_python(complete_python_repo).exists()
        state = json.loads(_state_file(complete_python_repo).read_text(encoding="utf-8"))
        assert state["success"] is False

        install_spy.install_ok = True  # a retry WOULD succeed — but the cooldown holds
        second = _run_leg(complete_python_repo)

        expected = shlex.join(
            [str(_venv_python(complete_python_repo)), "-m", "pip", "install", "-e", "."]
        )
        assert second.status == "failed"
        assert second.exit_code == 2
        assert factory.calls == []
        assert "last attempt" in second.error
        assert state["timestamp"] in second.error
        assert "retry cooldown" in second.error
        assert expected in second.error
        assert second.bootstrap["skipped"] is True
        assert install_spy.installs == [expected], "the cooldown skip ran no install"

    def test_a_bootstrap_that_raises_names_the_failure(
        self, complete_python_repo, factory, monkeypatch
    ):
        message = (
            f"{complete_python_repo / 'pyproject.toml'} declares [tool.uv.sources] "
            "but `uv` is not on PATH."
        )

        def raising(self, manifests, relevant_stacks=None):
            raise UvSourcesRequireUvError(message)

        monkeypatch.setattr(EnvironmentBootstrapper, "bootstrap", raising)

        outcome = _run_leg(complete_python_repo)

        assert outcome.status == "failed" and outcome.exit_code == 2
        assert factory.calls == []
        assert message in outcome.error
        assert "the environment bootstrap failed" in outcome.error
        assert "pip install -e ." in outcome.error
        assert "no worktree venv interpreter resolved" not in outcome.error

    def test_a_python_marker_the_bootstrap_cannot_install_from_is_named(
        self, tmp_path, factory, install_spy
    ):
        """``setup.py`` makes the Coach call this a Python project, but the
        bootstrap reads only pyproject.toml, poetry.lock and requirements.txt.
        Proceeding would burn a Player turn and then hit the Coach's abort;
        the leg says what is missing instead."""
        repo = _seed_repo(tmp_path / "worktree", {"setup.py": "from setuptools import setup\nsetup(name='old')\n"})

        outcome = _run_leg(repo)

        assert outcome.status == "failed" and outcome.exit_code == 2
        assert factory.calls == []
        assert "setup.py" in outcome.error
        assert "found no manifest it can install from" in outcome.error
        assert install_spy.venv_creations == 0

    def test_a_bootstrap_that_leaves_no_interpreter_is_named(
        self, python_repo, factory, monkeypatch
    ):
        """Success without an interpreter is not success: the sentence names
        the two locations the leg looked in."""
        from guardkit.orchestrator.environment_bootstrap import BootstrapResult

        def hollow(self, manifests, relevant_stacks=None):
            return BootstrapResult(
                success=True,
                skipped=False,
                stacks_detected=["python"],
                manifests_found=[str(m.path) for m in manifests],
                venv_python=None,
            )

        monkeypatch.setattr(EnvironmentBootstrapper, "bootstrap", hollow)

        outcome = _run_leg(python_repo)

        assert outcome.status == "failed" and outcome.exit_code == 2
        assert factory.calls == []
        assert "left no interpreter at" in outcome.error
        assert str(_venv_python(python_repo)) in outcome.error
        assert str(python_repo / ".guardkit" / "venv" / "bin" / "python") in outcome.error


# ===========================================================================
# Rule 59 — the third source: an explicit interpreter
# ===========================================================================


class TestExplicitInterpreter:
    def test_an_explicit_interpreter_wins_and_is_named_explicit(
        self, python_repo, factory, install_spy, tmp_path
    ):
        explicit = tmp_path / "elsewhere" / "bin" / "python"
        explicit.parent.mkdir(parents=True)
        explicit.write_text("#!/bin/sh\n", encoding="utf-8")

        outcome = _run_leg(python_repo, venv_python=str(explicit))

        assert outcome.interpreter == {"path": str(explicit), "source": "explicit"}
        assert factory.calls[0]["venv_python"] == str(explicit)
        assert outcome.bootstrap is None
        assert install_spy.venv_creations == 0

    def test_an_explicit_path_that_does_not_exist_falls_through(
        self, python_repo, factory, install_spy
    ):
        """Like the Coach verifier: a missing explicit path is not an error,
        the probe and then the bootstrap take over."""
        outcome = _run_leg(python_repo, venv_python=str(python_repo / "missing" / "python"))

        assert outcome.status == "approved", outcome.error
        assert outcome.interpreter["source"] == "bootstrapped"
        assert install_spy.venv_creations == 1


# ===========================================================================
# The seam into the real orchestrator, and the resolver on its own
# ===========================================================================


class TestRealFactory:
    def test_the_real_factory_threads_venv_python_to_the_orchestrator(
        self, python_repo, monkeypatch
    ):
        captured: Dict[str, Any] = {}

        class FakeOrchestrator:
            def __init__(self, **kwargs: Any) -> None:
                captured.update(kwargs)

        import guardkit.orchestrator.autobuild as autobuild_mod

        monkeypatch.setattr(autobuild_mod, "AutoBuildOrchestrator", FakeOrchestrator)
        work_runner._build_orchestrator(
            repo_root=python_repo,
            worktree=work_runner.build_outer_worktree(FIX_TASK_ID, python_repo, "main"),
            max_turns=2,
            sdk_timeout=420,
            leg_budget=1620,
            timeout_event=threading.Event(),
            model=None,
            venv_python="/somewhere/.venv/bin/python",
        )
        assert captured["venv_python"] == "/somewhere/.venv/bin/python"
        # The five §2c switches are untouched by Part N.
        assert captured["enable_pre_loop"] is False
        assert captured["enable_checkpoints"] is False
        assert captured["rollback_on_pollution"] is False
        assert captured["skip_arch_review"] is True
        assert captured["existing_worktree"].path == python_repo

    def test_the_real_orchestrator_accepts_the_keyword(self):
        """``AutoBuildOrchestrator(venv_python=...)`` is the feature
        orchestrator's own handoff; the leg uses the same keyword."""
        import inspect

        from guardkit.orchestrator.autobuild import AutoBuildOrchestrator

        assert "venv_python" in inspect.signature(AutoBuildOrchestrator.__init__).parameters


class TestProvisionInterpreterOnItsOwn:
    def test_a_non_python_directory_yields_nothing(self, tmp_path):
        assert provision_interpreter(tmp_path) == InterpreterProvision()

    def test_the_probe_order_is_the_coach_verifiers(self, tmp_path):
        """``.venv`` first, then the legacy ``.guardkit/venv``."""
        (tmp_path / "pyproject.toml").write_text(PYPROJECT, encoding="utf-8")
        legacy = tmp_path / ".guardkit" / "venv" / "bin" / "python"
        current = tmp_path / ".venv" / "bin" / "python"
        for p in (legacy, current):
            p.parent.mkdir(parents=True)
            p.write_text("", encoding="utf-8")
        assert provision_interpreter(tmp_path).path == str(current)
        current.unlink()
        assert provision_interpreter(tmp_path).path == str(legacy)

    def test_provisioning_never_raises(self, tmp_path, monkeypatch):
        (tmp_path / "pyproject.toml").write_text(PYPROJECT, encoding="utf-8")

        def explode(root):
            raise RuntimeError("the probe blew up")

        import guardkit.orchestrator.environment_bootstrap as eb

        monkeypatch.setattr(eb, "probe_worktree_venv", explode)
        result = provision_interpreter(tmp_path)
        assert result.error and "the probe blew up" in result.error
        assert result.path is None
