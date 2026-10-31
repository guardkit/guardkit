"""TS-lane D.1b — THE DECLARATION: schema, loader, and the pre-turn-1 snapshot.

Three properties are pinned here:

1. **Parsing** — good / bad / absent. ``extra="forbid"`` makes a typo LOUD,
   because a silently-ignored declaration would fall through to the detection
   ladder and look like the tool ignoring the repo.
2. **The snapshot** (design §B.4, NOT optional) — the declaration lives inside
   the target repo, which means inside the worktree the builder is editing.
   The snapshot is taken pre-turn-1 from the declaration committed at the
   worktree's HEAD (the canonical tree when the worktree is not a git
   checkout) and written OUTSIDE the shared worktree, and it is the ONLY
   thing the verdict path reads.
3. **Absence is a no-op** — a repo with no ``toolchain:`` block gets nothing
   written and nothing changed.

Network-free and broker-free by construction: nothing here runs a subprocess
except the local ``git`` calls of ``TestSnapshotFromTheWorktreeCommit``.
"""

from __future__ import annotations

import json
import subprocess

import pytest
import yaml

from guardkit.orchestrator.toolchain_declaration import (
    ToolchainDeclaration,
    load_committed_toolchain_declaration,
    load_toolchain_declaration,
    load_toolchain_snapshot,
    parse_toolchain_block,
    snapshot_task_toolchain,
    toolchain_snapshot_paths,
)

_TASK_ID = "TASK-TS-001"


def _write_config(root, block):
    """Write a ``.guardkit/config.yaml`` carrying ``toolchain: <block>``."""
    cfg_dir = root / ".guardkit"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    payload = {"autobuild": {"coach": {"model": "coach-ft-v4"}}}
    if block is not None:
        payload["toolchain"] = block
    (cfg_dir / "config.yaml").write_text(yaml.safe_dump(payload), encoding="utf-8")
    return cfg_dir / "config.yaml"


@pytest.fixture
def repo(tmp_path):
    """A repo root with a worktree beneath it, laid out as autobuild does."""
    root = tmp_path / "ts-api-test"
    worktree = root / ".guardkit" / "worktrees" / _TASK_ID
    worktree.mkdir(parents=True)
    return root, worktree


# =========================================================================
# 1. Parsing — good
# =========================================================================


class TestParseGoodDeclaration:
    def test_full_block_from_the_design_shape_parses(self):
        block = parse_toolchain_block(
            {
                "test": "npm test",
                "install": "npm ci",
                "install_timeout": 900,
                "test_timeout": 600,
                "typecheck": "npm run typecheck",
                "lint": "npm run lint",
                "build": "npm run build",
                "absent_substrings": ["command not found", "missing script"],
                "ran_marker_regex": None,
                "requires_ran_marker": True,
                "runtime": {"node": "v24.15.0"},
            }
        )
        assert block.test == "npm test"
        assert block.install == "npm ci"
        assert block.install_timeout == 900
        assert block.test_timeout == 600
        assert block.typecheck == "npm run typecheck"
        assert block.lint == "npm run lint"
        assert block.build == "npm run build"
        assert block.requires_ran_marker is True
        assert block.runtime is not None and block.runtime.node == "v24.15.0"

    def test_test_only_block_keeps_todays_timeouts(self):
        """A repo declaring ONLY ``test:`` must not silently acquire a
        different timeout than it had before the declaration existed."""
        block = parse_toolchain_block({"test": "npm test"})
        assert block.test_timeout == 300
        assert block.install_timeout == 300
        assert block.install is None

    def test_null_ran_marker_means_inherit_not_override(self):
        block = parse_toolchain_block({"test": "npm test", "ran_marker_regex": None})
        assert block.ran_marker_regex is None
        # ``requires_ran_marker`` untouched ⇒ no classifier overlay at all.
        assert block.has_classifier_overlay is False

    def test_declaring_any_classifier_field_is_an_overlay(self):
        assert parse_toolchain_block(
            {"test": "x", "requires_ran_marker": False}
        ).has_classifier_overlay


# =========================================================================
# 2. Parsing — bad (LOUD, never silently ignored)
# =========================================================================


class TestParseBadDeclaration:
    def test_typod_key_is_loud(self):
        """``tests:`` instead of ``test:`` must name itself, not be dropped."""
        with pytest.raises(ValueError) as exc:
            parse_toolchain_block({"tests": "npm test"})
        assert "tests" in str(exc.value)
        assert "typos" in str(exc.value).lower()

    def test_empty_command_string_is_rejected(self):
        with pytest.raises(ValueError):
            parse_toolchain_block({"test": ""})

    def test_timeout_above_the_bound_is_rejected(self):
        with pytest.raises(ValueError):
            parse_toolchain_block({"test": "npm test", "test_timeout": 999999})

    def test_zero_timeout_is_rejected(self):
        with pytest.raises(ValueError):
            parse_toolchain_block({"test": "npm test", "install_timeout": 0})

    def test_non_compiling_ran_marker_regex_is_rejected(self):
        """A regex that never compiles would silently never match — which
        reads as a false ABSENT, not as a config error."""
        with pytest.raises(ValueError) as exc:
            parse_toolchain_block({"test": "npm test", "ran_marker_regex": "([a-z"})
        assert "regex" in str(exc.value).lower()

    def test_unknown_runtime_key_is_loud(self):
        with pytest.raises(ValueError):
            parse_toolchain_block({"test": "x", "runtime": {"nodejs": "v24"}})

    def test_non_mapping_block_is_loud(self):
        with pytest.raises(ValueError) as exc:
            parse_toolchain_block("npm test")
        assert "mapping" in str(exc.value)


# =========================================================================
# 3. The loader — absence, and loud-degrade
# =========================================================================


class TestLoadDeclaration:
    def test_no_config_file_is_absent(self, tmp_path):
        assert load_toolchain_declaration(tmp_path) is None

    def test_config_without_toolchain_block_is_absent(self, tmp_path):
        _write_config(tmp_path, None)
        assert load_toolchain_declaration(tmp_path) is None

    def test_declaration_is_read_from_the_repo_config(self, tmp_path):
        _write_config(tmp_path, {"test": "npm test", "install": "npm ci"})
        block = load_toolchain_declaration(tmp_path)
        assert block is not None
        assert block.test == "npm test"

    def test_malformed_block_degrades_to_absent_and_logs_error(self, tmp_path, caplog):
        """A schema typo in an opt-in feature must never crash an existing
        build — but it must be LOUD, so it is an ERROR, not a shrug."""
        _write_config(tmp_path, {"tests": "npm test"})
        with caplog.at_level("ERROR"):
            assert load_toolchain_declaration(tmp_path) is None
        assert any("MALFORMED" in r.message for r in caplog.records)

    def test_empty_block_is_absent(self, tmp_path, caplog):
        _write_config(tmp_path, {})
        with caplog.at_level("WARNING"):
            assert load_toolchain_declaration(tmp_path) is None

    def test_unreadable_yaml_degrades_to_absent(self, tmp_path):
        cfg = tmp_path / ".guardkit"
        cfg.mkdir(parents=True)
        (cfg / "config.yaml").write_text("toolchain: [unclosed\n", encoding="utf-8")
        assert load_toolchain_declaration(tmp_path) is None


# =========================================================================
# 4. THE SNAPSHOT (design §B.4) — the crux
# =========================================================================


def _git(cwd, *args):
    subprocess.run(["git", "-C", str(cwd), *args], check=True, capture_output=True)


@pytest.fixture
def git_worktree(repo):
    """The repo fixture, with the worktree made a git checkout whose first
    commit declares nothing (the feature's starting point)."""
    root, worktree = repo
    _git(worktree, "init", "-q")
    _git(worktree, "config", "user.email", "t@example.invalid")
    _git(worktree, "config", "user.name", "t")
    _write_config(worktree, None)
    _git(worktree, "add", "-A")
    _git(worktree, "commit", "-q", "-m", "start")
    return root, worktree


def _commit_config(worktree, block):
    _write_config(worktree, block)
    _git(worktree, "add", "-A")
    _git(worktree, "commit", "-q", "-m", "declare")


class TestSnapshotFromTheWorktreeCommit:
    """The pin reads what is COMMITTED at the worktree's HEAD, so a feature's
    later tasks run the tests an earlier task declared (a recorded Go feature
    build, 29 October 2026), and an uncommitted edit still cannot change it."""

    def test_an_earlier_tasks_declaration_reaches_the_next_task(self, git_worktree):
        root, worktree = git_worktree
        _write_config(root, None)  # the main checkout has not seen the feature
        _commit_config(worktree, {"test": "go test ./..."})  # task 002's turn
        snapshot_task_toolchain(_TASK_ID, worktree, root)
        assert load_toolchain_snapshot(_TASK_ID, worktree).test == "go test ./..."

    def test_the_commit_wins_over_the_main_checkout(self, git_worktree):
        root, worktree = git_worktree
        _write_config(root, {"test": "npm test"})
        _commit_config(worktree, {"test": "npm test && npm run e2e"})
        snapshot_task_toolchain(_TASK_ID, worktree, root)
        assert load_toolchain_snapshot(_TASK_ID, worktree).test == "npm test && npm run e2e"

    def test_an_uncommitted_edit_is_not_pinned(self, git_worktree):
        root, worktree = git_worktree
        _commit_config(worktree, {"test": "go test ./..."})
        _write_config(worktree, {"test": "true"})  # the Player's version, not committed
        snapshot_task_toolchain(_TASK_ID, worktree, root)
        assert load_toolchain_snapshot(_TASK_ID, worktree).test == "go test ./..."

    def test_a_commit_that_declares_nothing_pins_nothing(self, git_worktree):
        root, worktree = git_worktree
        _write_config(root, {"test": "npm test"})
        assert snapshot_task_toolchain(_TASK_ID, worktree, root) is None
        assert load_toolchain_snapshot(_TASK_ID, worktree) is None

    def test_a_commit_without_the_config_file_pins_nothing(self, repo):
        root, worktree = repo
        _git(worktree, "init", "-q")
        _git(worktree, "config", "user.email", "t@example.invalid")
        _git(worktree, "config", "user.name", "t")
        (worktree / "README.md").write_text("x", encoding="utf-8")
        _git(worktree, "add", "-A")
        _git(worktree, "commit", "-q", "-m", "start")
        _write_config(root, {"test": "npm test"})
        assert snapshot_task_toolchain(_TASK_ID, worktree, root) is None

    def test_committed_reader_reports_a_non_checkout(self, repo):
        _, worktree = repo
        assert load_committed_toolchain_declaration(worktree) == (False, None)


class TestSnapshot:
    def test_snapshot_writes_outside_the_shared_worktree(self, repo):
        root, worktree = repo
        _write_config(root, {"test": "npm test"})
        path = snapshot_task_toolchain(_TASK_ID, worktree, root)
        assert path is not None
        assert path.exists()
        # Player-unreachable: the private dir resolves to the MAIN checkout,
        # not into the worktree the Player edits.
        assert not str(path).startswith(str(worktree))
        assert str(path).startswith(str(root / ".guardkit" / "autobuild-private"))

    def test_snapshot_round_trips_the_declaration(self, repo):
        root, worktree = repo
        _write_config(root, {"test": "npm test", "install": "npm ci", "lint": "eslint ."})
        snapshot_task_toolchain(_TASK_ID, worktree, root)
        loaded = load_toolchain_snapshot(_TASK_ID, worktree)
        assert loaded == ToolchainDeclaration(
            test="npm test", install="npm ci", lint="eslint ."
        )

    def test_no_declaration_writes_nothing(self, repo):
        """Byte-equivalent no-op for every repo that has not opted in."""
        root, worktree = repo
        _write_config(root, None)
        assert snapshot_task_toolchain(_TASK_ID, worktree, root) is None
        assert not toolchain_snapshot_paths(_TASK_ID, worktree)["dir"].exists()
        assert load_toolchain_snapshot(_TASK_ID, worktree) is None

    def test_snapshot_reads_the_canonical_repo_not_the_worktree(self, repo):
        """When the worktree is not a git checkout the snapshot's source is
        the repo_root tree, so a worktree file that differs cannot poison the
        pin."""
        root, worktree = repo
        _write_config(root, {"test": "npm test"})
        _write_config(worktree, {"test": "true"})  # the Player's version
        snapshot_task_toolchain(_TASK_ID, worktree, root)
        assert load_toolchain_snapshot(_TASK_ID, worktree).test == "npm test"

    def test_a_mid_build_config_edit_cannot_change_the_pinned_command(self, repo):
        """THE IMMUTABILITY PROOF. Snapshot, then rewrite the config in BOTH
        trees the way a Player turn would (``toolchain.test: "true"`` greens
        anything), and the pinned command is still what executes."""
        root, worktree = repo
        _write_config(root, {"test": "npm test"})
        snapshot_task_toolchain(_TASK_ID, worktree, root)

        _write_config(worktree, {"test": "true"})
        _write_config(root, {"test": "true"})

        assert load_toolchain_snapshot(_TASK_ID, worktree).test == "npm test"
        # ...and the live file really does say otherwise, so the assertion
        # above is about the snapshot and not about a stale write.
        assert load_toolchain_declaration(worktree).test == "true"

    def test_corrupt_snapshot_degrades_to_absent(self, repo):
        root, worktree = repo
        _write_config(root, {"test": "npm test"})
        snapshot_task_toolchain(_TASK_ID, worktree, root)
        toolchain_snapshot_paths(_TASK_ID, worktree)["file"].write_text(
            "{not json", encoding="utf-8"
        )
        assert load_toolchain_snapshot(_TASK_ID, worktree) is None

    def test_snapshot_file_is_readable_json(self, repo):
        root, worktree = repo
        _write_config(root, {"test": "npm test", "test_timeout": 600})
        path = snapshot_task_toolchain(_TASK_ID, worktree, root)
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["test"] == "npm test"
        assert data["test_timeout"] == 600


# =========================================================================
# 5. THE PIN — the snapshot fires pre-turn-1, at the conformance call site
# =========================================================================


class TestAutobuildSnapshotPin:
    """§B.4: "if the snapshot is cut from scope, the declaration must be cut
    with it". These pin the seam so a future refactor cannot quietly move the
    capture to somewhere the Player has already run."""

    def test_orchestrator_helper_writes_the_snapshot_from_repo_root(self, repo):
        from types import SimpleNamespace

        from guardkit.orchestrator.autobuild import AutoBuildOrchestrator

        root, worktree = repo
        _write_config(root, {"test": "npm test"})
        orchestrator = AutoBuildOrchestrator.__new__(AutoBuildOrchestrator)
        orchestrator.repo_root = root

        orchestrator._snapshot_toolchain_declaration(
            _TASK_ID, SimpleNamespace(path=worktree)
        )
        assert load_toolchain_snapshot(_TASK_ID, worktree).test == "npm test"

    def test_helper_never_raises_on_a_broken_worktree(self):
        from types import SimpleNamespace

        from guardkit.orchestrator.autobuild import AutoBuildOrchestrator

        orchestrator = AutoBuildOrchestrator.__new__(AutoBuildOrchestrator)
        orchestrator.repo_root = None  # deliberately broken
        orchestrator._snapshot_toolchain_declaration(
            _TASK_ID, SimpleNamespace(path=None)
        )  # must not raise

    def test_the_call_sits_right_after_setup_before_turn_1(self):
        """Structural pin: the toolchain snapshot is invoked in the
        fresh-start branch immediately after ``_setup_phase`` creates the
        worktree, and BEFORE any Player activity."""
        import inspect

        from guardkit.orchestrator.autobuild import AutoBuildOrchestrator

        source = inspect.getsource(AutoBuildOrchestrator._orchestrate_owned)
        setup = source.index("self._setup_phase(task_id, base_branch)")
        toolchain = source.index(
            "self._snapshot_toolchain_declaration(task_id, worktree)"
        )
        loop = source.index("self._loop_phase(")
        assert setup < toolchain < loop
        # nothing that could run the Player sits between setup and the pin
        between = source[setup:toolchain]
        for forbidden in ("_loop_phase", "invoke_", "_execute_turn", "await "):
            assert forbidden not in between


# =========================================================================
# Language servers (28 October 2026): accepted, never run by GuardKit
# =========================================================================


class TestLanguageServers:
    _GO = {"command": ["gopls"], "files": ["**/*.go"], "root": "packages/career_agent",
           "env": {"GOFLAGS": "-tags=live"}}

    def test_a_declared_server_keeps_the_rest_of_the_toolchain(self):
        decl = parse_toolchain_block({"test": "go test ./...", "language_servers": [self._GO]})
        assert decl.test == "go test ./..."
        assert decl.language_servers is not None
        assert decl.language_servers[0].command == ["gopls"]
        assert decl.language_servers[0].env == {"GOFLAGS": "-tags=live"}

    def test_optional_fields_default(self):
        decl = parse_toolchain_block(
            {"test": "pytest", "language_servers": [{"command": ["pyright-langserver", "--stdio"],
                                                      "files": ["**/*.py"]}]})
        server = decl.language_servers[0]
        assert server.root == "." and server.env is None and server.language_id is None

    def test_no_servers_is_todays_declaration(self):
        assert parse_toolchain_block({"test": "pytest"}).language_servers is None

    @pytest.mark.parametrize("bad", [
        {"command": ["gopls"], "files": ["**/*.go"], "rot": "."},   # typo'd key
        {"command": [], "files": ["**/*.go"]},                      # no program
        {"command": ["gopls"], "files": []},                        # no files
    ])
    def test_a_malformed_server_is_loud(self, bad):
        with pytest.raises(ValueError):
            parse_toolchain_block({"test": "pytest", "language_servers": [bad]})
