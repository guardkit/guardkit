"""A build's checks use main's settings for what main already declares.

18 November 2026 (FEAT-24BD). The copy of ``.guardkit/config.yaml`` pinned
before a task's first turn is read from the branch's HEAD, so a part an
earlier task added keeps its commands. The merge reads the settings from
main ("a branch never chooses the command that judges it"). FEAT-24BD's
builder raised a part's ``test_timeout`` to 3600 and committed it; the retry
of the task and the next task pinned 3600, passed in 1,037 s, and the merge
refused at main's 300. Since this change the pinned copy takes main's test
and install commands, their limits and named parts' folders for the root
and every folder main covers; everything else stays the branch's.

Every case runs on a real git repository with a real feature worktree made
from the base branch, as autobuild lays them out. All content is invented.
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

import pytest
import yaml

from guardkit.orchestrator.toolchain_declaration import (
    full_check_parts,
    load_committed_toolchain_declaration,
    load_toolchain_snapshot,
    parts_for_files,
    snapshot_task_toolchain,
)

_FEATURE = "FEAT-MS01"
_BRANCH = f"autobuild/{_FEATURE}"

# Main's settings, in the shape of the TypeScript project: a root check and a
# pattern for the packages, with no limit of its own (300 seconds).
_MAIN = {
    "test": "npm test",
    "install": "npm ci",
    "coverage": "npm run coverage",
    "parts": [{"under": "packages", "marker": "package.json", "test": "npm test"}],
}


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(cwd), "-c", "user.name=t",
         "-c", "user.email=t@example.invalid", *args],
        check=True, capture_output=True, text=True,
    ).stdout.strip()


def _write(tree: Path, rel: str, text: str) -> None:
    path = tree / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _declare(tree: Path, block, message: str = "settings") -> None:
    """Commit ``.guardkit/config.yaml`` with ``toolchain: block`` (no
    ``toolchain:`` key when ``block`` is None) in ``tree``."""
    payload = {"autobuild": {"coach": {"model": "coach-test"}}}
    if block is not None:
        payload["toolchain"] = block
    _write(tree, ".guardkit/config.yaml", yaml.safe_dump(payload))
    _git(tree, "add", "-A")
    _git(tree, "commit", "-q", "-m", message)


def _feature_build(tmp_path: Path, main_block, base: str = "main"):
    """A repository on ``base`` declaring ``main_block`` (no settings file when
    it is the string ``"no file"``), and a feature worktree made from it."""
    root = tmp_path / "project"
    root.mkdir()
    _git(root, "init", "-q", "-b", base)
    _write(root, ".gitignore", ".guardkit/worktrees/\n.guardkit/autobuild-private/\n")
    _write(root, "packages/career_agent/package.json", "{}\n")
    _write(root, "packages/web/package.json", "{}\n")
    _write(root, "services/api/go.mod", "module api\n")
    if main_block == "no file":
        _git(root, "add", "-A")
        _git(root, "commit", "-q", "-m", "start")
    else:
        _declare(root, main_block, "start")
    worktree = root / ".guardkit" / "worktrees" / _FEATURE
    _git(root, "worktree", "add", "-q", "-b", _BRANCH, str(worktree), base)
    return root, worktree


def _pinned(task_id: str, root: Path, worktree: Path, base: str = "main"):
    snapshot_task_toolchain(task_id, worktree, root, base_branch=base)
    return load_toolchain_snapshot(task_id, worktree)


def _part(declaration, worktree: Path, folder: str):
    """The part the check runs for a file changed in ``folder``."""
    (part,) = parts_for_files(declaration, worktree, [f"{folder}/src/a.ts"])
    assert part.cwd == folder
    return part


def _branch_settings(**changes) -> dict:
    block = yaml.safe_load(yaml.safe_dump(_MAIN))
    block.update(changes)
    return block


class TestMainJudgesWhatItDeclares:
    def test_a_raised_part_limit_is_main_s_on_the_retry_and_the_next_task(
        self, tmp_path: Path, caplog
    ):
        """FEAT-24BD: task 005's turn raises the packages part's limit to
        3600 and commits it. The retry of 005 and task 006 take fresh
        copies; both carry main's 300 (main inherits it through its pattern)."""
        root, worktree = _feature_build(tmp_path, _MAIN)
        first = _pinned("TASK-MS01-005", root, worktree)
        assert _part(first, worktree, "packages/career_agent").toolchain.test_timeout == 300

        raised = _branch_settings()
        raised["parts"][0]["test_timeout"] = 3600
        _declare(worktree, raised, "turn 1 checkpoint")
        assert load_committed_toolchain_declaration(worktree)[1].parts[0].test_timeout == 3600

        with caplog.at_level(logging.INFO):
            retry = _pinned("TASK-MS01-005", root, worktree)
            later = _pinned("TASK-MS01-006", root, worktree)
        for pinned in (retry, later):
            for folder in ("packages/career_agent", "packages/web"):
                assert _part(pinned, worktree, folder).toolchain.test_timeout == 300
        assert (
            "packages/* test_timeout: the branch says 3600, main says 300; "
            "main's is used, as at merge."
        ) in caplog.text

    def test_a_named_part_added_for_a_folder_main_covers_by_pattern(
        self, tmp_path: Path
    ):
        """FEAT-E673: the branch names the folder that main's pattern covers,
        with its own command and a higher limit. Main's are used."""
        root, worktree = _feature_build(tmp_path, _MAIN)
        _declare(worktree, _branch_settings(components={"career_agent": {
            "cwd": "packages/career_agent",
            "test": "npm run test:all",
            "test_timeout": 600,
        }}))

        pinned = _pinned("TASK-MS01-003", root, worktree)

        part = _part(pinned, worktree, "packages/career_agent")
        assert part.test == "npm test"
        assert part.toolchain.test_timeout == 300
        checked = {p.cwd: p for p in full_check_parts(pinned, worktree)}
        assert checked["packages/career_agent"].test == "npm test"

    def test_a_moved_named_part_goes_back_to_main_s_folder(self, tmp_path: Path):
        """FEAT-8FDA: the branch changed a named part's folder and command."""
        main = dict(_MAIN, components={"api": {
            "cwd": "services/api", "test": "go test ./...", "test_timeout": 120,
        }})
        root, worktree = _feature_build(tmp_path, main)
        _declare(worktree, dict(main, components={"api": {
            "cwd": "services", "test": "go test ./api/...", "test_timeout": 900,
        }}))

        api = _pinned("TASK-MS01-002", root, worktree).components["api"]

        assert (api.cwd, api.test, api.test_timeout) == ("services/api", "go test ./...", 120)

    def test_a_folder_main_covers_that_the_branch_dropped_is_still_checked(
        self, tmp_path: Path
    ):
        """The branch removes main's pattern; the merge would still test
        those folders with main's command, so the pinned copy names them."""
        root, worktree = _feature_build(tmp_path, _MAIN)
        branch = _branch_settings()
        del branch["parts"]
        _declare(worktree, branch)

        pinned = _pinned("TASK-MS01-002", root, worktree)

        for folder in ("packages/career_agent", "packages/web"):
            part = _part(pinned, worktree, folder)
            assert (part.test, part.toolchain.test_timeout) == ("npm test", 300)

    def test_a_part_main_does_not_cover_keeps_the_branch_s_commands(
        self, tmp_path: Path
    ):
        """Go C's case: an earlier task declares a new part; later tasks keep
        its commands and limit, because the merge does not test it alone."""
        root, worktree = _feature_build(tmp_path, _MAIN)
        _declare(worktree, _branch_settings(components={"api": {
            "cwd": "services/api",
            "test": "go test ./...",
            "test_timeout": 900,
            "install": "go mod download",
            "install_timeout": 1200,
        }}))

        api = _pinned("TASK-MS01-004", root, worktree).components["api"]

        assert (api.cwd, api.test, api.test_timeout) == ("services/api", "go test ./...", 900)
        assert (api.install, api.install_timeout) == ("go mod download", 1200)

    def test_the_root_command_is_main_s_coverage_and_feature_check_the_branch_s(
        self, tmp_path: Path
    ):
        root, worktree = _feature_build(tmp_path, _MAIN)
        _declare(worktree, _branch_settings(
            test="true",
            test_timeout=3600,
            install="npm install --force",
            coverage="npm run coverage -- --all",
            feature_check="bash qa/journey.sh",
            lint="npm run lint",
        ))

        pinned = _pinned("TASK-MS01-005", root, worktree)

        assert (pinned.test, pinned.test_timeout) == ("npm test", 300)
        assert pinned.install == "npm ci"
        assert pinned.coverage == "npm run coverage -- --all"
        assert pinned.feature_check == "bash qa/journey.sh"
        assert pinned.lint == "npm run lint"


class TestNothingOnMainIsTodaysBehaviour:
    @pytest.mark.parametrize("main_block", ["no file", None])
    def test_no_settings_on_main_pins_the_branch_s_copy_unchanged(
        self, tmp_path: Path, main_block
    ):
        """No settings file on main, or one without a ``toolchain:`` block:
        the pinned copy is exactly the branch's, as before this change."""
        root, worktree = _feature_build(tmp_path, main_block)
        raised = _branch_settings(test="true")
        raised["parts"][0]["test_timeout"] = 3600
        _declare(worktree, raised)

        pinned = _pinned("TASK-MS01-002", root, worktree)

        assert pinned == load_committed_toolchain_declaration(worktree)[1]
        assert pinned.test == "true"
        assert pinned.parts[0].test_timeout == 3600

    def test_a_base_branch_git_cannot_find_pins_the_branch_s_copy(
        self, tmp_path: Path
    ):
        root, worktree = _feature_build(tmp_path, _MAIN)
        _declare(worktree, _branch_settings(test="true"))

        pinned = _pinned("TASK-MS01-002", root, worktree, base="no-such-branch")

        assert pinned == load_committed_toolchain_declaration(worktree)[1]


class TestTheBuildersCheck:
    def test_the_coach_s_check_stops_at_main_s_limit_after_the_real_pin(
        self, tmp_path: Path
    ):
        """The toy reproduction through the real path a builder turn reaches,
        with no model: the orchestrator's pre-turn-1 pin, given the feature
        worktree (made from ``trunk``, so the base branch must be passed
        through), then the Coach's check of the changed part. The branch's
        committed 3600 would let ``sleep 3`` pass; main's 1 second stops it."""
        from guardkit.orchestrator.autobuild import AutoBuildOrchestrator
        from guardkit.orchestrator.quality_gates.coach_validator import (
            CoachValidator,
        )
        from guardkit.worktrees.manager import Worktree

        main = {"parts": [{"under": "packages", "marker": "package.json",
                           "test": "sleep 3", "test_timeout": 1}]}
        root, worktree = _feature_build(tmp_path, main, base="trunk")
        _declare(worktree, {"parts": [dict(main["parts"][0], test_timeout=3600)]})

        orchestrator = AutoBuildOrchestrator.__new__(AutoBuildOrchestrator)
        orchestrator.repo_root = root
        orchestrator._snapshot_toolchain_declaration(
            "TASK-MS01-006",
            Worktree(task_id=_FEATURE, branch_name=_BRANCH, path=worktree,
                     base_branch="trunk"),
        )
        validator = CoachValidator(
            str(worktree), task_id="TASK-MS01-006",
            baseline_commit=_git(worktree, "rev-parse", "HEAD"),
        )
        _write(worktree, "packages/career_agent/src/a.ts", "export {}\n")

        result = validator.run_changed_parts()

        assert result.tests_passed is False
        assert "packages/career_agent" in result.test_output_summary
        assert "1-second limit" in result.test_output_summary
