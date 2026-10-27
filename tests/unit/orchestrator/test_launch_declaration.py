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
    LaunchDeclarationError,
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

    def test_empty_block_declares_nothing(self):
        assert parse_launch_block(None).is_empty
        assert parse_launch_block({}).is_empty
        assert parse_launch_block({"settings": None, "scratch": None}).is_empty

    def test_a_block_that_is_not_a_mapping_declares_nothing(self):
        # Step 2 (26 October 2026): advice, never a refusal.
        assert parse_launch_block(["GOCACHE"]).is_empty

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
        ],
    )
    def test_reserved_and_credential_shaped_names_are_refused(self, name, why):
        for key in ("settings", "scratch"):
            with pytest.raises(ValueError, match=why):
                parse_launch_block({key: [name]})

    @pytest.mark.parametrize("name", ["1CACHE", "BAD-NAME", "", 7])
    def test_a_malformed_name_is_left_out(self, name):
        for key in ("settings", "scratch"):
            block = parse_launch_block({key: [name, "GOOD_CACHE"]})
            assert getattr(block, key) == ("GOOD_CACHE",)

    def test_a_trailing_newline_is_folded_like_forge(self):
        # Forge strips names before checking; the pattern itself is matched
        # whole (fullmatch), so an unstripped newline could never pass.
        assert parse_launch_block({"scratch": ["GOCACHE\n"]}).scratch == ("GOCACHE",)
        from guardkit.orchestrator.launch_declaration import DECLARED_NAME_PATTERN

        assert DECLARED_NAME_PATTERN.fullmatch("GOCACHE\n") is None

    def test_duplicates_fold_as_forge_folds_them(self):
        block = parse_launch_block(
            {"settings": ["B", "A", "B"], "scratch": ["TOOL_CACHE", "TOOL_CACHE"]}
        )
        assert block.settings == ("B", "A")
        assert block.scratch == ("TOOL_CACHE",)

    def test_a_name_in_both_lists_is_a_scratch_folder(self):
        block = parse_launch_block({"settings": ["X_CACHE"], "scratch": ["X_CACHE"]})
        assert block.settings == () and block.scratch == ("X_CACHE",)

    def test_more_names_than_the_guide_are_kept(self):
        names = [f"NAME_{i}" for i in range(33)]
        assert len(parse_launch_block({"scratch": names}).scratch) == 33

    def test_a_string_is_not_a_list_and_is_ignored(self):
        assert parse_launch_block({"scratch": "TOOL_CACHE"}).is_empty


class TestLoad:
    def test_absent_file_or_block_is_none(self, tmp_path):
        assert load_launch_declaration(tmp_path) is None
        _write_config(tmp_path, None)
        assert load_launch_declaration(tmp_path) is None

    def test_block_with_only_other_keys_is_none(self, tmp_path):
        _write_config(tmp_path, {"something_else": 1})
        assert load_launch_declaration(tmp_path) is None

    def test_malformed_block_refuses_rather_than_degrading(self, tmp_path):
        config = _write_config(tmp_path, {"scratch": ["PATH"]})
        with pytest.raises(LaunchDeclarationError) as raised:
            load_launch_declaration(tmp_path)
        assert str(config) in str(raised.value)
        assert "PATH" in str(raised.value)
        # A task-load ValueError, and an OSError for "could not run" callers.
        assert isinstance(raised.value, ValueError)
        assert isinstance(raised.value, OSError)

    # The coach's reader-disagreement cases (probeB/div.py), with Forge's
    # answer for `settings` alongside.
    @pytest.mark.parametrize(
        "text, settings, scratch",
        [
            (
                "launch:\n  settings: [PLAYWRIGHT_BROWSERS_PATH, "
                "PLAYWRIGHT_BROWSERS_PATH]\n  scratch: [GOCACHE]\n",
                ("PLAYWRIGHT_BROWSERS_PATH",),  # Forge folds the repeat
                ("GOCACHE",),
            ),
            (
                "launch:\n  settings: ["
                + ", ".join(f"S{i}" for i in range(32))
                + "]\n  scratch: ["
                + ", ".join(f"C{i}" for i in range(32))
                + "]\n",
                tuple(f"S{i}" for i in range(32)),  # Forge accepts 32
                tuple(f"C{i}" for i in range(32)),
            ),
        ],
    )
    def test_accepted_like_forge(self, tmp_path, text, settings, scratch):
        (tmp_path / ".guardkit").mkdir()
        (tmp_path / ".guardkit" / "config.yaml").write_text(text)
        declaration = load_launch_declaration(tmp_path)
        assert declaration.settings == settings
        assert declaration.scratch == scratch

    @pytest.mark.parametrize(
        "text, reason",
        [
            (
                "launch:\n  settings: [PLAYWRIGHT_BROWSERS_PATH]\n  scratch: [TMPDIR]\n",
                "TMPDIR",
            ),
            (
                "launch:\n  settings: [GITHUB_TOKEN]\n",
                "credential-shaped",
            ),
        ],
    )
    def test_fenced_names_refuse_the_task(self, tmp_path, text, reason):
        (tmp_path / ".guardkit").mkdir()
        (tmp_path / ".guardkit" / "config.yaml").write_text(text)
        with pytest.raises(LaunchDeclarationError, match=reason):
            load_launch_declaration(tmp_path)


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

    def test_a_malformed_block_is_never_pinned(self, repo):
        root, worktree = repo
        _write_config(root, {"scratch": ["HOME"]})
        with pytest.raises(LaunchDeclarationError):
            snapshot_task_launch(_TASK_ID, worktree, root)
        assert not launch_snapshot_path(_TASK_ID, worktree).exists()

    def test_an_unreadable_pin_refuses_rather_than_reading_as_absent(self, repo):
        root, worktree = repo
        _write_config(root, {"scratch": ["TOOL_CACHE"]})
        path = snapshot_task_launch(_TASK_ID, worktree, root)
        path.write_text("{not json")
        with pytest.raises(LaunchDeclarationError, match="cannot be read"):
            load_launch_snapshot(_TASK_ID, worktree)


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

    def test_a_setting_never_replaces_a_value_the_caller_set(self, repo, monkeypatch):
        _, worktree = repo
        monkeypatch.setenv("BROWSERS_AT", "/opt/browsers")

        env = apply_launch_environment(
            {"BROWSERS_AT": "/caller/choice"},
            LaunchDeclaration(settings=("BROWSERS_AT",)),
            worktree,
        )

        assert env["BROWSERS_AT"] == "/caller/choice"

    def test_a_scratch_name_the_caller_chose_keeps_the_callers_value(
        self, repo, monkeypatch
    ):
        _, worktree = repo
        monkeypatch.delenv("TOOL_CACHE", raising=False)

        env = apply_launch_environment(
            {"TOOL_CACHE": "/caller/cache"},
            LaunchDeclaration(scratch=("TOOL_CACHE",)),
            worktree,
        )

        assert env["TOOL_CACHE"] == "/caller/cache"

    def test_an_inherited_value_is_replaced_by_the_scratch_folder(
        self, repo, monkeypatch
    ):
        _, worktree = repo
        monkeypatch.setenv("TOOL_CACHE", "/runner/default")

        env = apply_launch_environment(
            dict(os.environ), LaunchDeclaration(scratch=("TOOL_CACHE",)), worktree
        )

        assert env["TOOL_CACHE"].endswith("guardkit-scratch/toolchain/TOOL_CACHE")

    def test_none_env_means_this_process_environment(self, repo, monkeypatch):
        _, worktree = repo
        monkeypatch.setenv("INHERITED_ONE", "yes")
        env = apply_launch_environment(
            None, LaunchDeclaration(scratch=("TOOL_CACHE",)), worktree
        )
        assert env["INHERITED_ONE"] == "yes"
        assert "TOOL_CACHE" in env

    def test_no_scratch_folder_leaves_the_scratch_names_alone(
        self, tmp_path, monkeypatch
    ):
        worktree = tmp_path / "not-a-checkout"
        worktree.mkdir()
        monkeypatch.delenv("TOOL_CACHE", raising=False)

        env = apply_launch_environment(
            {}, LaunchDeclaration(scratch=("TOOL_CACHE",)), worktree
        )

        assert "TOOL_CACHE" not in env
        assert list(worktree.iterdir()) == []


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
            _checker_pytest_env,
        )

        worktree = _pinned(repo, {"settings": ["BROWSERS_AT"], "scratch": ["TOOL_CACHE"]})
        monkeypatch.setenv("BROWSERS_AT", "/opt/browsers")
        validator = CoachValidator(str(worktree), task_id=_TASK_ID)

        expected = str(
            Path(os.path.realpath(builder_scratch_dir(worktree)))
            / "toolchain"
            / "TOOL_CACHE"
        )
        for env in (validator._declared_command_env(), _checker_pytest_env(validator)):
            assert env["TOOL_CACHE"] == expected
            assert env["BROWSERS_AT"] == "/opt/browsers"
            # Since 13 October 2026 the Coach's commands get a private HOME
            # beside the scratch folders, never this process's own.
            assert env["HOME"] == str(Path(expected).parent / "HOME")

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

    def test_without_a_block_the_env_is_built_from_nothing(self, repo):
        """Since 13 October 2026 no block no longer means this process's
        environment: the Coach's command gets one built from nothing."""
        from guardkit.orchestrator.project_command_env import (
            project_command_environment,
        )
        from guardkit.orchestrator.quality_gates.coach_validator import (
            CoachValidator,
        )

        _, worktree = repo
        validator = CoachValidator(str(worktree), task_id=_TASK_ID)
        assert validator._declared_command_env() == project_command_environment(
            worktree, None
        )


class TestFeatureCheck:
    def test_the_check_command_sees_the_scratch_folder(self, repo):
        from guardkit.orchestrator.feature_check import run_feature_check_command

        root, worktree = repo
        _write_config(root, {"scratch": ["TOOL_CACHE"]})
        run = run_feature_check_command(
            'printf "%s" "$TOOL_CACHE"',
            cwd=worktree,
            timeout=30,
            launch_root=root,
        )

        assert run["exit_code"] == 0
        assert run["stdout"].endswith("/guardkit-scratch/toolchain/TOOL_CACHE")


    def test_a_malformed_block_means_the_check_could_not_start(self, repo):
        from guardkit.orchestrator.feature_check import run_feature_check_command

        root, worktree = repo
        _write_config(root, {"scratch": ["PATH"]})
        run = run_feature_check_command(
            "true", cwd=worktree, timeout=30, launch_root=root
        )

        assert run["exit_code"] is None
        assert "could not start" in run["stderr"]
        assert "PATH" in run["stderr"]

    def test_the_orchestrator_passes_the_main_checkout(self):
        from guardkit.orchestrator import feature_orchestrator

        source = inspect.getsource(feature_orchestrator)
        assert "launch_root=self.repo_root" in source


def _declared_manifest(eb, worktree):
    return eb.DetectedManifest(
        stack="custom",
        path=worktree / ".guardkit" / "config.yaml",
        is_lock_file=False,
        install_command=["tool", "install"],
        declared=True,
        install_cwd=worktree,
    )


class TestInstallBootstrap:
    @staticmethod
    def _record(monkeypatch, eb):
        seen = {}

        def fake_run(cmd, **kwargs):
            seen["env"] = kwargs.get("env", "absent")
            return eb.subprocess.CompletedProcess(cmd, 0, "", "")

        monkeypatch.setattr(eb.subprocess, "run", fake_run)
        return seen

    def test_install_command_env_carries_the_main_checkouts_folders(
        self, repo, monkeypatch
    ):
        from guardkit.orchestrator import environment_bootstrap as eb

        root, worktree = repo
        _write_config(root, {"scratch": ["TOOL_CACHE"]})
        seen = self._record(monkeypatch, eb)
        bootstrapper = eb.EnvironmentBootstrapper(worktree)

        assert bootstrapper._run_install(_declared_manifest(eb, worktree)) is True
        assert seen["env"]["TOOL_CACHE"].endswith("guardkit-scratch/toolchain/TOOL_CACHE")
        assert bootstrapper._run_single_command(["tool", "add"], worktree) is True
        assert "TOOL_CACHE" in seen["env"]

    def test_a_player_edit_of_the_worktree_config_changes_nothing(
        self, repo, monkeypatch
    ):
        """B2: the block is the main checkout's, not the worktree's."""
        from guardkit.orchestrator import environment_bootstrap as eb

        root, worktree = repo
        _write_config(root, {"scratch": ["TOOL_CACHE"]})
        monkeypatch.setenv("SOME_PROXY", "http://proxy.invalid")
        # What a Player could write into its own worktree mid-build.
        _write_config(worktree, {"settings": ["SOME_PROXY"], "scratch": ["OTHER"]})
        seen = self._record(monkeypatch, eb)

        assert eb.EnvironmentBootstrapper(worktree)._run_single_command(
            ["tool", "add"], worktree
        )
        assert "TOOL_CACHE" in seen["env"]
        assert "OTHER" not in seen["env"]

    def test_without_a_block_install_envs_are_unchanged(self, repo, monkeypatch):
        """Reliability (1): no block means the helper's environment with no
        declared names (13 October 2026: built from nothing, never None)."""
        from guardkit.orchestrator import environment_bootstrap as eb
        from guardkit.orchestrator.project_command_env import (
            project_command_environment,
        )

        root, worktree = repo
        _write_config(root, None)
        seen = self._record(monkeypatch, eb)
        bootstrapper = eb.EnvironmentBootstrapper(worktree)
        plain = project_command_environment(worktree, None)

        assert bootstrapper._run_single_command(["tool", "add"], worktree) is True
        assert seen["env"] == plain
        assert bootstrapper._run_install(_declared_manifest(eb, worktree)) is True
        assert seen["env"] == plain
        # A Python install keeps its isolated env, byte for byte.
        venv = worktree / ".venv"
        bootstrapper._venv_python = venv / "bin" / "python"
        python = eb.DetectedManifest(
            stack="python",
            path=worktree / "pyproject.toml",
            is_lock_file=False,
            install_command=[eb.sys.executable, "-m", "pip", "install", "-e", "."],
        )
        assert bootstrapper._run_install(python) is True
        assert seen["env"] == bootstrapper._isolated_env(venv)


    def test_a_malformed_block_fails_the_install_plainly(self, repo, monkeypatch):
        from guardkit.orchestrator import environment_bootstrap as eb

        root, worktree = repo
        _write_config(root, {"scratch": ["PATH"]})
        monkeypatch.setattr(
            eb.subprocess, "run", lambda *a, **k: pytest.fail("must not run")
        )
        bootstrapper = eb.EnvironmentBootstrapper(worktree)

        assert bootstrapper._run_install(_declared_manifest(eb, worktree)) is False
        assert "`launch:` block" in bootstrapper._last_failure_stderr


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


# =========================================================================
# 5. What the reliability owner requires (12 October 2026)
# =========================================================================


def _git(cwd: Path, *args: str) -> str:
    import subprocess

    return subprocess.run(
        ["git", *args], cwd=str(cwd), check=True, capture_output=True, text=True
    ).stdout


@pytest.fixture
def clone(tmp_path):
    """A build clone with a real git feature worktree, as the runner lays out."""
    root = tmp_path / "build-clone"
    root.mkdir()
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "t@example.invalid")
    _git(root, "config", "user.name", "t")
    (root / "README").write_text("clone\n")
    _git(root, "add", "README")
    _git(root, "commit", "-q", "-m", "init")
    wt = root / ".guardkit" / "worktrees" / "FEAT-L"
    wt.parent.mkdir(parents=True)
    _git(root, "worktree", "add", "-q", "-b", "feat", str(wt))
    (wt / "src.txt").write_text("committed source\n")
    _git(wt, "add", "src.txt")
    _git(wt, "commit", "-q", "-m", "source")
    return root, wt


# Fills the declared cache when there is one, then passes or fails on purpose.
_CACHE_FILLING = (
    'if [ -n "$TOOL_CACHE" ]; then mkdir -p "$TOOL_CACHE/pkg" && '
    'echo c > "$TOOL_CACHE/pkg/c" && pwd > "$TOOL_CACHE/cwd"; fi; '
)


def _coach(wt: Path, cmd: str, wave_size: int):
    from guardkit.orchestrator.quality_gates.coach_validator import CoachValidator

    validator = CoachValidator(
        worktree_path=str(wt), task_id=_TASK_ID, test_command=cmd, wave_size=wave_size
    )
    validator._coach_test_execution = "subprocess"
    return validator


def _comparable(record: dict) -> dict:
    """The run_evidence fields a launch block must not change."""
    source = record["source"]
    return {
        "keys": sorted(record),
        "source_keys": sorted(source),
        "command": record["command"],
        "execution_root_is": record["execution_root_is"],
        "verdict": source["verdict"],
        "changed_paths": source["changed_paths"],
        "created": source["files_created_during_the_command"],
        "entries": source["manifest"]["entries"] if source["manifest"] else None,
        "capture_errors": record.get("capture_errors"),
    }


class TestReliabilityRequirements:
    def test_1_no_block_leaves_the_coach_envs_byte_identical(self, repo):
        from guardkit.orchestrator.quality_gates.command_models import venv_path_first
        from guardkit.orchestrator.quality_gates.coach_validator import (
            CoachValidator,
            _checker_pytest_env,
        )

        root, worktree = repo
        _write_config(root, None)
        snapshot_task_launch(_TASK_ID, worktree, root)
        validator = CoachValidator(str(worktree), task_id=_TASK_ID)
        validator._fixture_env = {"DATABASE_URL": "postgresql://fixture.invalid/db"}

        # 13 October 2026: built from nothing, with only the fixture URLs
        # added, never a copy of this process's environment.
        from guardkit.orchestrator.project_command_env import (
            project_command_environment,
        )

        declared_today = project_command_environment(
            worktree, None, additions=validator._fixture_env
        )
        path_first = venv_path_first(worktree)
        pytest_today = (
            project_command_environment(worktree, None, path_first=path_first)
            if path_first
            else project_command_environment(worktree, None)
        )
        pytest_today.update(validator._fixture_env)
        assert validator._declared_command_env() == declared_today
        assert _checker_pytest_env(validator) == pytest_today

    def test_1_no_block_leaves_the_feature_check_env_byte_identical(self, repo):
        from guardkit.orchestrator.feature_check import run_feature_check_command

        root, worktree = repo
        _write_config(root, None)
        # Each command carries its own marker (process_group, 19 October
        # 2026), a fresh value every time, so it is left out of the compare.
        from guardkit.orchestrator.process_group import COMMAND_MARKER_NAME

        cmd = f"env | grep -v '^{COMMAND_MARKER_NAME}=' | LC_ALL=C sort"

        today = run_feature_check_command(cmd, cwd=worktree, timeout=30)
        with_root = run_feature_check_command(
            cmd, cwd=worktree, timeout=30, launch_root=root
        )

        assert today["exit_code"] == with_root["exit_code"] == 0
        assert with_root["stdout"] == today["stdout"]

    @pytest.mark.parametrize("wave_size", [1, 2], ids=["worktree", "isolated-copy"])
    @pytest.mark.parametrize("ending", ["test -f src.txt", "false"], ids=["pass", "fail"])
    def test_2_and_3_the_block_changes_no_verdict_or_record_field(
        self, clone, wave_size, ending
    ):
        root, wt = clone
        cmd = _CACHE_FILLING + ending

        without = _coach(wt, cmd, wave_size).run_independent_tests(turn=1)
        _write_config(root, {"scratch": ["TOOL_CACHE"]})
        snapshot_task_launch(_TASK_ID, wt, root)
        declared = _coach(wt, cmd, wave_size).run_independent_tests(turn=1)

        # (2) the same verdict and the same record fields.
        assert declared.tests_passed == without.tests_passed == (ending != "false")
        assert declared.signal_absent == without.signal_absent
        runs_without = without.run_evidence["runs"]
        runs_declared = declared.run_evidence["runs"]
        assert [_comparable(r) for r in runs_declared] == [
            _comparable(r) for r in runs_without
        ]

        # (3) the cache was really written, outside every execution root, and
        # no record names it as a file the command created or as source.
        cache = Path(os.path.realpath(builder_scratch_dir(wt))) / "toolchain" / "TOOL_CACHE"
        assert (cache / "pkg" / "c").read_text() == "c\n"
        for record in runs_declared:
            root_dir = Path(record["execution_root"]).resolve()
            assert not cache.is_relative_to(root_dir)
            source = record["source"]
            assert not source["files_created_during_the_command"]
            text = repr(source)
            assert "guardkit-scratch" not in text and "TOOL_CACHE" not in text

    def test_4_isolated_copy_uses_the_originating_worktrees_scratch(self, clone):
        root, wt = clone
        _write_config(root, {"scratch": ["TOOL_CACHE"]})
        snapshot_task_launch(_TASK_ID, wt, root)

        result = _coach(wt, _CACHE_FILLING + "test -f src.txt", 2).run_independent_tests(
            turn=1
        )

        assert result.tests_passed, result.test_output_summary
        record = result.run_evidence["runs"][0]
        copy_root = Path(record["execution_root"]).resolve()
        assert copy_root != wt.resolve()
        assert "without Git metadata" in record["execution_root_is"]
        cache = Path(os.path.realpath(builder_scratch_dir(wt))) / "toolchain" / "TOOL_CACHE"
        # The command ran in the copy, and its cache was the original's.
        ran_in = Path((cache / "cwd").read_text().strip()).resolve()
        assert ran_in == copy_root
        assert not cache.is_relative_to(copy_root)
        assert cache.is_relative_to(Path(os.path.realpath(root / ".git")))


def _config_pipe_holding_a_launch_block(root: Path) -> tuple:
    """A named pipe at the config path whose buffer already holds a valid
    ``launch:`` block, with a writer kept open: a read that ignored the
    file type would return that declaration instead of ``None``."""
    (root / ".guardkit").mkdir()
    pipe = root / ".guardkit" / "config.yaml"
    os.mkfifo(pipe)
    holder = os.open(pipe, os.O_RDWR | os.O_NONBLOCK)
    os.write(holder, yaml.safe_dump(
        {"launch": {"settings": ["NEUTRAL_SETTING"]}}).encode())
    return pipe, holder


@pytest.mark.timeout(30)
def test_a_pipe_at_the_config_path_is_never_read(tmp_path, caplog):
    """``open()`` on a named pipe can wait for a writer forever; the config
    is read only when it is a regular file (20 October 2026)."""
    pipe, holder = _config_pipe_holding_a_launch_block(tmp_path)
    try:
        assert load_launch_declaration(tmp_path) is None
    finally:
        os.close(holder)
    assert "is not a regular file" in caplog.text


@pytest.mark.timeout(30)
@pytest.mark.parametrize("with_writer", [True, False],
                         ids=["a-writer-holds-it", "no-writer"])
def test_a_pipe_swapped_in_after_the_type_check_is_caught_once_open(
    tmp_path, monkeypatch, with_writer
):
    """The type is checked again on the open descriptor: a path that looked
    like a regular file a moment earlier is still not read as one, and with
    no writer the open itself does not wait (it is non-blocking)."""
    import guardkit.orchestrator.launch_declaration as module

    pipe, holder = _config_pipe_holding_a_launch_block(tmp_path)
    if not with_writer:
        os.close(holder)
        holder = None
    real_stat = os.stat

    def stat_says_regular(path, *args, **kwargs):
        result = real_stat(path, *args, **kwargs)
        if Path(path) == pipe:
            return os.stat_result(
                (stat.S_IFREG | 0o644,) + tuple(result)[1:])
        return result

    monkeypatch.setattr(module.os, "stat", stat_says_regular)
    try:
        assert load_launch_declaration(tmp_path) is None
    finally:
        monkeypatch.undo()
        if holder is not None:
            os.close(holder)


def test_a_regular_config_is_still_read(tmp_path):
    _write_config(tmp_path, {"settings": ["NEUTRAL_SETTING"]})
    declaration = load_launch_declaration(tmp_path)
    assert declaration is not None and "NEUTRAL_SETTING" in declaration.settings
