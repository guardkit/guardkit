"""
Tests for TASK-AB-COACHVENV01: refresh Coach venv on intra-wave dep change.

FEAT-MEM-05 (fleet-memory) added ``tiktoken`` to ``pyproject.toml`` and consumed
it within the SAME wave. The worktree venv is bootstrapped once per feature and
re-bootstrapped only BETWEEN waves, so the Coach's independent pytest run
executed against the stale venv → ``ModuleNotFoundError`` → every AC rejected
even though the deliverable + manifest edit were correct (a false-red).

This suite covers:

* ``changed_dependency_manifests`` — the cheap diff gate (so unaffected turns
  pay nothing).
* ``refresh_environment_for_changes`` — no-op when no manifest changed; reinstall
  when one did; the FEAT-MEM-05 scenario (manifest gains a dep → reinstall runs
  with the editable command that picks it up).
* The ``AutoBuildOrchestrator._maybe_refresh_venv_for_manifest_change`` hook —
  no-op / success / absence-of-failure-safe feedback on reinstall failure.

Coverage Target: >=85%
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from guardkit.orchestrator.environment_bootstrap import (
    BootstrapFailureDetail,
    BootstrapResult,
    changed_dependency_manifests,
    refresh_environment_for_changes,
)


# ---------------------------------------------------------------------------
# changed_dependency_manifests — the diff gate
# ---------------------------------------------------------------------------


class TestChangedDependencyManifests:
    def test_detects_pyproject(self):
        assert changed_dependency_manifests(
            ["src/foo.py", "pyproject.toml"]
        ) == ["pyproject.toml"]

    def test_detects_requirements_variants(self):
        assert changed_dependency_manifests(["requirements.txt"]) == [
            "requirements.txt"
        ]
        assert changed_dependency_manifests(["requirements-dev.txt"]) == [
            "requirements-dev.txt"
        ]
        assert changed_dependency_manifests(["reqs/requirements.txt"]) == [
            "reqs/requirements.txt"
        ]

    def test_detects_lock_files(self):
        for name in ("uv.lock", "poetry.lock", "package.json", "go.mod"):
            assert changed_dependency_manifests([name]) == [name]

    def test_detects_nested_manifest_by_basename(self):
        assert changed_dependency_manifests(
            ["packages/backend/pyproject.toml"]
        ) == ["packages/backend/pyproject.toml"]

    def test_detects_repo_qualified_manifest(self):
        # Cross-repo evidence loop emits ``<repo>:<path>`` strings.
        assert changed_dependency_manifests(
            ["guardkitfactory:pyproject.toml"]
        ) == ["guardkitfactory:pyproject.toml"]

    def test_no_manifest_returns_empty(self):
        assert changed_dependency_manifests(["src/a.py", "tests/test_a.py"]) == []

    def test_empty_input_returns_empty(self):
        assert changed_dependency_manifests([]) == []

    def test_dedupes_preserving_order(self):
        assert changed_dependency_manifests(
            ["pyproject.toml", "pyproject.toml", "uv.lock"]
        ) == ["pyproject.toml", "uv.lock"]

    def test_ignores_falsy_entries(self):
        assert changed_dependency_manifests(["", None, "pyproject.toml"]) == [  # type: ignore[list-item]
            "pyproject.toml"
        ]

    def test_does_not_match_unrelated_toml(self):
        assert changed_dependency_manifests(["config.toml", "data.json"]) == []


# ---------------------------------------------------------------------------
# refresh_environment_for_changes
# ---------------------------------------------------------------------------


class TestRefreshEnvironmentForChanges:
    def test_no_manifest_change_is_noop(self, tmp_path: Path):
        # Even with a manifest present on disk, a turn that changed no manifest
        # must NOT trigger a reinstall.
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "x"\nversion = "0.1.0"\n', encoding="utf-8"
        )
        with patch.object(
            __import__(
                "guardkit.orchestrator.environment_bootstrap",
                fromlist=["EnvironmentBootstrapper"],
            ).EnvironmentBootstrapper,
            "bootstrap",
        ) as mock_bootstrap:
            result = refresh_environment_for_changes(
                tmp_path, ["src/only_code.py"]
            )
        assert result is None
        mock_bootstrap.assert_not_called()

    def test_manifest_change_with_no_detected_manifest_is_noop(
        self, tmp_path: Path
    ):
        # Player reports a manifest change but none exists in the worktree
        # (e.g. it was reverted). Detection yields nothing → no-op, no crash.
        result = refresh_environment_for_changes(tmp_path, ["pyproject.toml"])
        assert result is None

    def test_manifest_change_triggers_reinstall(self, tmp_path: Path):
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "x"\nversion = "0.1.0"\n'
            'dependencies = ["tiktoken"]\n',
            encoding="utf-8",
        )
        sentinel = BootstrapResult(
            success=True,
            skipped=False,
            stacks_detected=["python"],
            manifests_found=[str(tmp_path / "pyproject.toml")],
            venv_python=str(tmp_path / ".venv" / "bin" / "python"),
        )
        with patch.object(
            __import__(
                "guardkit.orchestrator.environment_bootstrap",
                fromlist=["EnvironmentBootstrapper"],
            ).EnvironmentBootstrapper,
            "bootstrap",
            return_value=sentinel,
        ) as mock_bootstrap:
            result = refresh_environment_for_changes(
                tmp_path, ["pyproject.toml", "src/uses_tiktoken.py"]
            )
        assert result is sentinel
        mock_bootstrap.assert_called_once()

    def test_feat_mem_05_scenario_install_command_picks_up_new_dep(
        self, tmp_path: Path
    ):
        """A dep added to a complete project reinstalls editable, which pulls it."""
        # Complete project: source dir matches the project name.
        (tmp_path / "x").mkdir()
        (tmp_path / "x" / "__init__.py").write_text("", encoding="utf-8")
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "x"\nversion = "0.1.0"\n'
            'dependencies = ["tiktoken"]\n',
            encoding="utf-8",
        )

        captured: dict = {}

        def _fake_bootstrap(self, manifests, relevant_stacks=None):  # noqa: ANN001
            captured["commands"] = [list(m.install_command) for m in manifests]
            return BootstrapResult(
                success=True,
                skipped=False,
                stacks_detected=["python"],
                manifests_found=[str(m.path) for m in manifests],
            )

        with patch.object(
            __import__(
                "guardkit.orchestrator.environment_bootstrap",
                fromlist=["EnvironmentBootstrapper"],
            ).EnvironmentBootstrapper,
            "bootstrap",
            _fake_bootstrap,
        ):
            result = refresh_environment_for_changes(tmp_path, ["pyproject.toml"])

        assert result is not None and result.success
        # The reinstall command is an editable install of the project, which
        # resolves the freshly declared ``tiktoken`` from the manifest.
        assert any(
            "-e" in cmd and cmd[-1].startswith(".") for cmd in captured["commands"]
        )


# ---------------------------------------------------------------------------
# AutoBuildOrchestrator._maybe_refresh_venv_for_manifest_change
# ---------------------------------------------------------------------------


def _orchestrator_with_refresh():
    """Bind the unbound method onto a lightweight stand-in object."""
    from guardkit.orchestrator.autobuild import AutoBuildOrchestrator

    obj = MagicMock()
    obj._venv_python = "/old/venv/bin/python"
    obj._maybe_refresh_venv_for_manifest_change = (
        AutoBuildOrchestrator._maybe_refresh_venv_for_manifest_change.__get__(obj)
    )
    return obj


def _player_result(files_modified=None, files_created=None):
    pr = MagicMock()
    pr.report = {
        "files_modified": files_modified or [],
        "files_created": files_created or [],
    }
    return pr


def _worktree(path: Path):
    wt = MagicMock()
    wt.path = path
    return wt


class TestMaybeRefreshVenvHook:
    def test_noop_when_no_manifest_changed(self, tmp_path: Path):
        obj = _orchestrator_with_refresh()
        with patch(
            "guardkit.orchestrator.environment_bootstrap.refresh_environment_for_changes"
        ) as mock_refresh:
            feedback = obj._maybe_refresh_venv_for_manifest_change(
                _player_result(files_modified=["src/a.py"]),
                _worktree(tmp_path),
                turn=1,
            )
        assert feedback is None
        mock_refresh.assert_not_called()

    def test_noop_when_worktree_or_player_none(self, tmp_path: Path):
        obj = _orchestrator_with_refresh()
        assert (
            obj._maybe_refresh_venv_for_manifest_change(None, _worktree(tmp_path), 1)
            is None
        )
        assert (
            obj._maybe_refresh_venv_for_manifest_change(_player_result(), None, 1)
            is None
        )

    def test_success_updates_venv_python_and_returns_none(self, tmp_path: Path):
        obj = _orchestrator_with_refresh()
        new_venv = str(tmp_path / ".venv" / "bin" / "python")
        ok = BootstrapResult(
            success=True,
            skipped=False,
            stacks_detected=["python"],
            manifests_found=["pyproject.toml"],
            venv_python=new_venv,
        )
        with patch(
            "guardkit.orchestrator.environment_bootstrap.refresh_environment_for_changes",
            return_value=ok,
        ):
            feedback = obj._maybe_refresh_venv_for_manifest_change(
                _player_result(files_modified=["pyproject.toml"]),
                _worktree(tmp_path),
                turn=2,
            )
        assert feedback is None
        assert obj._venv_python == new_venv

    def test_reinstall_failure_returns_actionable_feedback(self, tmp_path: Path):
        obj = _orchestrator_with_refresh()
        failed = BootstrapResult(
            success=False,
            skipped=False,
            stacks_detected=["python"],
            manifests_found=["pyproject.toml"],
            installs_attempted=1,
            installs_failed=1,
            error="1/1 install(s) failed",
            failure_details=[
                BootstrapFailureDetail(
                    stack="python",
                    manifest_path=str(tmp_path / "pyproject.toml"),
                    stderr_excerpt="No matching distribution found for nope",
                    essential=True,
                )
            ],
        )
        with patch(
            "guardkit.orchestrator.environment_bootstrap.refresh_environment_for_changes",
            return_value=failed,
        ):
            feedback = obj._maybe_refresh_venv_for_manifest_change(
                _player_result(files_modified=["pyproject.toml"]),
                _worktree(tmp_path),
                turn=3,
            )
        assert feedback is not None
        assert "reinstall failed" in feedback.lower()
        assert "No matching distribution found for nope" in feedback
        # A failed reinstall must NOT silently update the interpreter.
        assert obj._venv_python == "/old/venv/bin/python"

    def test_exception_is_surfaced_not_swallowed(self, tmp_path: Path):
        obj = _orchestrator_with_refresh()
        with patch(
            "guardkit.orchestrator.environment_bootstrap.refresh_environment_for_changes",
            side_effect=RuntimeError("uv exploded"),
        ):
            feedback = obj._maybe_refresh_venv_for_manifest_change(
                _player_result(files_created=["pyproject.toml"]),
                _worktree(tmp_path),
                turn=4,
            )
        assert feedback is not None
        assert "uv exploded" in feedback
