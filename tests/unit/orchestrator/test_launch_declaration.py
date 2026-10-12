"""The project's ``launch:`` block — settings and scratch folders for its shell.

12 October 2026 (web readiness W1/R4). Pinned here:

1. **Parsing** — Forge's name rules, mirrored: shape, reserved prefixes and
   names, credential-shaped names, count, duplicates; a name in both lists is
   refused. A block without the new key, or no block, declares nothing.
2. **The snapshot** — read from the canonical repo root, written outside the
   worktree, never falling back to the live file.
3. **The one helper** — :func:`apply_launch_environment` leaves an
   environment untouched without a declaration, copies settings only when set,
   puts scratch names under the worktree's scratch folder, and refuses to run
   with no scratch folder rather than falling back into the project.
4. **Every caller applies it** — the Coach's declared and pytest commands,
   the whole-feature check, the install bootstrap, and the harness callers.
"""

from __future__ import annotations

import ast
import inspect
import os
import stat
import textwrap
from pathlib import Path

import pytest
import yaml

from guardkit.orchestrator.launch_declaration import (
    LaunchDeclaration,
    LaunchEnvironmentError,
    apply_launch_environment,
    apply_task_launch_environment,
    launch_snapshot_path,
    load_launch_declaration,
    load_launch_snapshot,
    parse_launch_block,
    snapshot_task_launch,
)
from guardkit.orchestrator.paths import builder_scratch_dir

_TASK_ID = "TASK-LAUNCH-001"


def _write_config(root: Path, launch) -> Path:
    cfg_dir = root / ".guardkit"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    payload = {"memory": {"project": "neutral_fixture"}}
    if launch is not None:
        payload["launch"] = launch
    path = cfg_dir / "config.yaml"
    path.write_text(yaml.safe_dump(payload), encoding="utf-8")
    return path


@pytest.fixture
def repo(tmp_path):
    """A plain git checkout with a worktree beneath it, as autobuild lays out.

    The worktree's ``.git`` is a directory here, so its scratch folder is
    ``<worktree>/.git/guardkit-scratch`` — outside the project tree.
    """
    root = tmp_path / "fixture-repo"
    worktree = root / ".guardkit" / "worktrees" / _TASK_ID
    (worktree / ".git").mkdir(parents=True)
    return root, worktree


def _files(worktree: Path) -> list:
    return sorted(
        str(p.relative_to(worktree))
        for p in worktree.rglob("*")
        if ".git" not in p.relative_to(worktree).parts
    )


# =========================================================================
# 1. Parsing
# =========================================================================


class TestParse:
    def test_settings_and_scratch_parse(self):
        block = parse_launch_block(
            {
                "settings": ["BROWSERS_AT"],
                "scratch": ["TOOL_CACHE", "npm_config_cache"],
            }
        )
        assert block == LaunchDeclaration(
            settings=("BROWSERS_AT",), scratch=("TOOL_CACHE", "npm_config_cache")
        )

    def test_settings_only_block_is_forges_block_unchanged(self):
        block = parse_launch_block({"settings": ["SOME_TOOL_CACHE"]})
        assert block.settings == ("SOME_TOOL_CACHE",)
        assert block.scratch == ()

    def test_non_mapping_or_empty_block_declares_nothing(self):
        assert parse_launch_block("settings").is_empty
        assert parse_launch_block({}).is_empty
        assert parse_launch_block({"settings": None, "scratch": None}).is_empty

    @pytest.mark.parametrize(
        "name, why",
        [
            ("PATH", "sets itself"),
            ("HOME", "sets itself"),
            ("TMPDIR", "sets itself"),
            ("SSH_AUTH_SOCK", "sets itself"),
            ("GUARDKIT_ANYTHING", "keeps for itself"),
            ("FORGE_X", "keeps for itself"),
            ("FLEET_MEMORY_PG_DSN", "keeps for itself"),
            ("OPENAI_BASE_URL", "keeps for itself"),
            ("ANTHROPIC_X", "keeps for itself"),
            ("REGISTRY_TOKEN", "credential-shaped"),
            ("db_password", "credential-shaped"),
            ("1CACHE", "not the shape"),
            ("BAD-NAME", "not the shape"),
            ("", "empty"),
        ],
    )
    def test_reserved_and_malformed_names_are_refused(self, name, why):
        for key in ("settings", "scratch"):
            with pytest.raises(ValueError, match=why):
                parse_launch_block({key: [name]})

    def test_duplicates_are_refused(self):
        with pytest.raises(ValueError, match="more than once"):
            parse_launch_block({"scratch": ["TOOL_CACHE", "TOOL_CACHE"]})

    def test_a_name_in_both_lists_is_refused(self):
        with pytest.raises(ValueError, match="cannot be both"):
            parse_launch_block({"settings": ["X_CACHE"], "scratch": ["X_CACHE"]})

    def test_too_many_names_are_refused(self):
        names = [f"NAME_{i}" for i in range(33)]
        with pytest.raises(ValueError, match="at most 32"):
            parse_launch_block({"scratch": names})

    def test_a_string_is_not_a_list(self):
        with pytest.raises(ValueError, match="list of names"):
            parse_launch_block({"scratch": "TOOL_CACHE"})


class TestLoad:
    def test_absent_file_or_block_is_none(self, tmp_path):
        assert load_launch_declaration(tmp_path) is None
        _write_config(tmp_path, None)
        assert load_launch_declaration(tmp_path) is None

    def test_block_with_only_other_keys_is_none(self, tmp_path):
        _write_config(tmp_path, {"something_else": 1})
        assert load_launch_declaration(tmp_path) is None

    def test_malformed_block_degrades_to_none_loudly(self, tmp_path, caplog):
        _write_config(tmp_path, {"scratch": ["PATH"]})
        assert load_launch_declaration(tmp_path) is None
        assert "MALFORMED `launch:` block" in caplog.text

    def test_declared_block_is_read(self, tmp_path):
        _write_config(tmp_path, {"scratch": ["TOOL_CACHE"]})
        assert load_launch_declaration(tmp_path).scratch == ("TOOL_CACHE",)


# =========================================================================
# 2. The snapshot
# =========================================================================


class TestSnapshot:
    def test_snapshot_is_written_outside_the_worktree_and_round_trips(self, repo):
        root, worktree = repo
        _write_config(root, {"settings": ["B"], "scratch": ["TOOL_CACHE"]})

        path = snapshot_task_launch(_TASK_ID, worktree, root)

        assert path == launch_snapshot_path(_TASK_ID, worktree)
        assert worktree not in path.parents
        assert load_launch_snapshot(_TASK_ID, worktree) == LaunchDeclaration(
            settings=("B",), scratch=("TOOL_CACHE",)
        )

    def test_no_block_writes_nothing(self, repo):
        root, worktree = repo
        _write_config(root, None)
        assert snapshot_task_launch(_TASK_ID, worktree, root) is None
        assert load_launch_snapshot(_TASK_ID, worktree) is None

    def test_a_mid_build_edit_of_the_worktree_file_changes_nothing(self, repo):
        root, worktree = repo
        _write_config(root, {"scratch": ["TOOL_CACHE"]})
        snapshot_task_launch(_TASK_ID, worktree, root)
        _write_config(worktree, {"settings": ["AWS_PROFILE"]})

        assert load_launch_snapshot(_TASK_ID, worktree).settings == ()

    def test_no_task_id_is_none(self, repo):
        _, worktree = repo
        assert load_launch_snapshot(None, worktree) is None

    def test_autobuild_pins_it_with_the_toolchain(self, repo):
        """The pre-turn-1 pin writes the launch snapshot too."""
        from types import SimpleNamespace

        from guardkit.orchestrator.autobuild import AutoBuildOrchestrator

        root, worktree = repo
        _write_config(root, {"scratch": ["TOOL_CACHE"]})
        orch = object.__new__(AutoBuildOrchestrator)
        orch.repo_root = root

        orch._snapshot_toolchain_declaration(
            _TASK_ID, SimpleNamespace(path=worktree)
        )

        assert load_launch_snapshot(_TASK_ID, worktree).scratch == ("TOOL_CACHE",)


# =========================================================================
# 3. The one helper
# =========================================================================


class TestApply:
    def test_no_declaration_returns_the_same_environment(self, repo):
        _, worktree = repo
        env = {"A": "1"}
        assert apply_launch_environment(env, None, worktree) is env
        assert apply_launch_environment(None, None, worktree) is None
        assert apply_launch_environment(env, LaunchDeclaration(), worktree) is env
        assert apply_task_launch_environment(env, None, worktree) is env
        assert apply_task_launch_environment(env, _TASK_ID, worktree) is env
        assert not (worktree / ".git" / "guardkit-scratch").exists()

    def test_settings_copied_only_when_set(self, repo, monkeypatch):
        _, worktree = repo
        monkeypatch.setenv("BROWSERS_AT", "/opt/browsers")
        monkeypatch.delenv("NOT_SET_HERE", raising=False)
        declaration = LaunchDeclaration(settings=("BROWSERS_AT", "NOT_SET_HERE"))

        env = apply_launch_environment({"A": "1"}, declaration, worktree)

        assert env == {"A": "1", "BROWSERS_AT": "/opt/browsers"}

    def test_scratch_names_live_under_the_worktrees_scratch_folder(self, repo):
        _, worktree = repo
        declaration = LaunchDeclaration(scratch=("TOOL_CACHE", "TOOL_HOME"))

        env = apply_launch_environment({"A": "1"}, declaration, worktree)

        base = Path(os.path.realpath(builder_scratch_dir(worktree))) / "toolchain"
        for name in ("TOOL_CACHE", "TOOL_HOME"):
            assert env[name] == str(base / name)
            assert stat.S_IMODE((base / name).stat().st_mode) == 0o700
        assert _files(worktree) == []

    def test_none_env_means_this_process_environment(self, repo, monkeypatch):
        _, worktree = repo
        monkeypatch.setenv("INHERITED_ONE", "yes")
        env = apply_launch_environment(
            None, LaunchDeclaration(scratch=("TOOL_CACHE",)), worktree
        )
        assert env["INHERITED_ONE"] == "yes"
        assert "TOOL_CACHE" in env

    def test_no_scratch_folder_refuses_rather_than_using_the_project(
        self, tmp_path
    ):
        worktree = tmp_path / "not-a-checkout"
        worktree.mkdir()

        with pytest.raises(LaunchEnvironmentError, match="no scratch folder"):
            apply_launch_environment(
                {}, LaunchDeclaration(scratch=("TOOL_CACHE",)), worktree
            )
        assert list(worktree.iterdir()) == []
        # An OSError, so callers report "could not run".
        assert issubclass(LaunchEnvironmentError, OSError)

    def test_symlinked_scratch_entry_is_refused(self, repo, tmp_path):
        _, worktree = repo
        elsewhere = tmp_path / "elsewhere"
        elsewhere.mkdir()
        base = builder_scratch_dir(worktree) / "toolchain"
        base.mkdir(parents=True)
        (base / "TOOL_CACHE").symlink_to(elsewhere)

        with pytest.raises(LaunchEnvironmentError, match="not a real folder"):
            apply_launch_environment(
                {}, LaunchDeclaration(scratch=("TOOL_CACHE",)), worktree
            )


# =========================================================================
# 4. Every caller applies it
# =========================================================================


def _pinned(repo, launch):
    root, worktree = repo
    _write_config(root, launch)
    snapshot_task_launch(_TASK_ID, worktree, root)
    return worktree


class TestCoachCommands:
    def test_declared_and_pytest_envs_carry_the_scratch_folders(
        self, repo, monkeypatch
    ):
        from guardkit.orchestrator.quality_gates.coach_validator import (
            CoachValidator,
        )

        worktree = _pinned(repo, {"settings": ["BROWSERS_AT"], "scratch": ["TOOL_CACHE"]})
        monkeypatch.setenv("BROWSERS_AT", "/opt/browsers")
        validator = CoachValidator(str(worktree), task_id=_TASK_ID)

        expected = str(
            Path(os.path.realpath(builder_scratch_dir(worktree)))
            / "toolchain"
            / "TOOL_CACHE"
        )
        for env in (validator._declared_command_env(), validator._pytest_env()):
            assert env["TOOL_CACHE"] == expected
            assert env["BROWSERS_AT"] == "/opt/browsers"
            # The Coach's commands keep inheriting this process's HOME.
            assert env["HOME"] == os.environ["HOME"]

    def test_real_go_sees_the_scratch_folders_through_the_coach_env(
        self, repo, monkeypatch
    ):
        """The Coach's own command path with the host's go (skipped if absent)."""
        import shutil
        import subprocess

        from guardkit.orchestrator.quality_gates.coach_validator import (
            CoachValidator,
        )

        go = shutil.which("go")
        if go is None:
            pytest.skip("go is not on this machine's PATH")
        monkeypatch.setenv("GOTOOLCHAIN", "local")
        worktree = _pinned(
            repo, {"scratch": ["GOPATH", "GOCACHE", "XDG_CONFIG_HOME"]}
        )
        validator = CoachValidator(str(worktree), task_id=_TASK_ID)

        proc = subprocess.run(
            [go, "env", "GOCACHE", "GOPATH"],
            cwd=worktree,
            env=validator._declared_command_env(),
            capture_output=True,
            text=True,
            timeout=60,
        )

        base = Path(os.path.realpath(builder_scratch_dir(worktree))) / "toolchain"
        assert proc.returncode == 0, proc.stderr
        assert proc.stdout.split() == [str(base / "GOCACHE"), str(base / "GOPATH")]
        assert _files(worktree) == []

    def test_without_a_block_the_env_is_this_process_environment(self, repo):
        from guardkit.orchestrator.quality_gates.coach_validator import (
            CoachValidator,
        )

        _, worktree = repo
        validator = CoachValidator(str(worktree), task_id=_TASK_ID)
        assert validator._declared_command_env() == dict(os.environ)


class TestFeatureCheck:
    def test_the_check_command_sees_the_scratch_folder(self, repo):
        from guardkit.orchestrator.feature_check import run_feature_check_command

        _, worktree = repo
        run = run_feature_check_command(
            'printf "%s" "$TOOL_CACHE"',
            cwd=worktree,
            timeout=30,
            launch=LaunchDeclaration(scratch=("TOOL_CACHE",)),
        )

        assert run["exit_code"] == 0
        assert run["stdout"].endswith("/guardkit-scratch/toolchain/TOOL_CACHE")

    def test_no_scratch_folder_means_the_check_could_not_start(self, tmp_path):
        from guardkit.orchestrator.feature_check import run_feature_check_command

        run = run_feature_check_command(
            "true",
            cwd=tmp_path,
            timeout=30,
            launch=LaunchDeclaration(scratch=("TOOL_CACHE",)),
        )

        assert run["exit_code"] is None
        assert "could not start" in run["stderr"]
        assert "no scratch folder" in run["stderr"]

    def test_the_orchestrator_passes_the_main_checkouts_block(self):
        from guardkit.orchestrator import feature_orchestrator

        source = inspect.getsource(feature_orchestrator)
        assert "launch=load_launch_declaration(self.repo_root)" in source


class TestInstallBootstrap:
    def test_install_command_env_carries_the_scratch_folder(
        self, repo, monkeypatch
    ):
        from guardkit.orchestrator import environment_bootstrap as eb

        _, worktree = repo
        _write_config(worktree, {"scratch": ["TOOL_CACHE"]})
        seen = {}

        def fake_run(cmd, **kwargs):
            seen["env"] = kwargs.get("env")
            return eb.subprocess.CompletedProcess(cmd, 0, "", "")

        monkeypatch.setattr(eb.subprocess, "run", fake_run)
        bootstrapper = eb.EnvironmentBootstrapper(worktree)
        manifest = eb.DetectedManifest(
            stack="custom",
            path=worktree / ".guardkit" / "config.yaml",
            is_lock_file=False,
            install_command=["tool", "install"],
            declared=True,
            install_cwd=worktree,
        )

        assert bootstrapper._run_install(manifest) is True
        assert seen["env"]["TOOL_CACHE"].endswith("guardkit-scratch/toolchain/TOOL_CACHE")
        assert bootstrapper._run_single_command(["tool", "add"], worktree) is True
        assert "TOOL_CACHE" in seen["env"]

    def test_without_a_block_install_inherits_as_before(self, repo, monkeypatch):
        from guardkit.orchestrator import environment_bootstrap as eb

        _, worktree = repo
        seen = {}

        def fake_run(cmd, **kwargs):
            seen["env"] = kwargs.get("env", "absent")
            return eb.subprocess.CompletedProcess(cmd, 0, "", "")

        monkeypatch.setattr(eb.subprocess, "run", fake_run)
        bootstrapper = eb.EnvironmentBootstrapper(worktree)

        assert bootstrapper._run_single_command(["tool", "add"], worktree) is True
        assert seen["env"] is None

    def test_no_scratch_folder_fails_the_install_plainly(self, tmp_path, monkeypatch):
        from guardkit.orchestrator import environment_bootstrap as eb

        _write_config(tmp_path, {"scratch": ["TOOL_CACHE"]})
        monkeypatch.setattr(
            eb.subprocess, "run", lambda *a, **k: pytest.fail("must not run")
        )
        bootstrapper = eb.EnvironmentBootstrapper(tmp_path)

        assert bootstrapper._run_single_command(["tool", "add"], tmp_path) is False
        assert "no scratch folder" in bootstrapper._last_failure_stderr


class TestHarnessCallers:
    """Each ``select_harness`` caller hands over the task's pinned block."""

    @staticmethod
    def _select_harness_calls(function) -> list:
        tree = ast.parse(textwrap.dedent(inspect.getsource(function)))
        return [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "select_harness"
        ]

    @pytest.mark.parametrize(
        "owner, name",
        [
            ("guardkit.orchestrator.agent_invoker:AgentInvoker", "_invoke_with_role"),
            (
                "guardkit.orchestrator.agent_invoker:AgentInvoker",
                "_invoke_task_work_implement",
            ),
            (
                "guardkit.orchestrator.quality_gates.task_work_interface:TaskWorkInterface",
                "_execute_via_sdk",
            ),
        ],
    )
    def test_call_passes_the_pinned_block(self, owner, name):
        import importlib

        module_name, class_name = owner.split(":")
        cls = getattr(importlib.import_module(module_name), class_name)
        calls = self._select_harness_calls(getattr(cls, name))

        assert len(calls) == 1
        keywords = {kw.arg: kw.value for kw in calls[0].keywords}
        value = keywords["launch_declaration"]
        assert isinstance(value, ast.Call)
        assert value.func.id == "load_launch_snapshot"
