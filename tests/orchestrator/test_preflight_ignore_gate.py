"""Tests for the pre-turn-1 ``git check-ignore`` fail-fast gate
(TASK-FIX-CAUD-PREFLIGHT-C3B0).

Closes deferred AC-005 of TASK-FIX-CAUD-J6F1. Uses real ``git init``
worktrees rather than mocking subprocess so the tests exercise the
actual ``git check-ignore`` semantics — the gate's correctness is
entirely about agreeing with git, and a mock that diverges from git
would mask the very bug class the gate is supposed to prevent.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from guardkit.orchestrator.preflight_ignore_gate import (
    STATUS_BLOCKED,
    STATUS_PASSED,
    STATUS_SKIPPED,
    check_ignore_one,
    format_blocked_message,
    is_project_root_gitignore,
    load_planned_targets,
    run_preflight_ignore_gate,
)


# ---------- fixtures ----------------------------------------------------


@pytest.fixture
def worktree(tmp_path: Path) -> Path:
    """A fresh ``git init`` worktree with no .gitignore yet."""
    subprocess.run(
        ["git", "init", "-q"], cwd=str(tmp_path), check=True
    )
    # Quiet "please tell me who you are" warnings on minimal CI envs.
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=str(tmp_path),
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=str(tmp_path),
        check=True,
    )
    return tmp_path


def _write_gitignore(worktree: Path, content: str) -> None:
    (worktree / ".gitignore").write_text(content + "\n", encoding="utf-8")


def _write_plan_json(worktree: Path, task_id: str, plan: dict) -> Path:
    state_dir = worktree / "docs" / "state" / task_id
    state_dir.mkdir(parents=True)
    json_path = state_dir / "implementation_plan.json"
    json_path.write_text(json.dumps(plan), encoding="utf-8")
    return json_path


def _write_task_file(
    worktree: Path,
    task_id: str,
    *,
    files_to_create: list[str] | None = None,
    files_to_modify: list[str] | None = None,
) -> Path:
    """Drop a minimal task markdown into ``tasks/in_progress/``."""
    task_dir = worktree / "tasks" / "in_progress"
    task_dir.mkdir(parents=True)
    frontmatter_lines = [
        "---",
        f"id: {task_id}",
        f'title: "test task for {task_id}"',
        "status: in_progress",
    ]
    if files_to_create is not None:
        frontmatter_lines.append("files_to_create:")
        for path in files_to_create:
            frontmatter_lines.append(f"  - {path}")
    if files_to_modify is not None:
        frontmatter_lines.append("files_to_modify:")
        for path in files_to_modify:
            frontmatter_lines.append(f"  - {path}")
    frontmatter_lines.append("---")
    body = "\n".join(frontmatter_lines) + "\n\n# body\n"
    task_path = task_dir / f"{task_id}-stub.md"
    task_path.write_text(body, encoding="utf-8")
    return task_path


# ---------- unit tests: helpers ----------------------------------------


class TestCheckIgnoreOne:
    """Coverage for the subprocess wrapper used by the gate."""

    def test_returns_rule_string_for_ignored_path(self, worktree: Path) -> None:
        _write_gitignore(worktree, "secrets/*.key")
        rule = check_ignore_one(worktree, "secrets/api.key")
        assert rule is not None
        assert rule.startswith(".gitignore:")
        assert "secrets/*.key" in rule

    def test_returns_none_for_non_ignored_path(self, worktree: Path) -> None:
        _write_gitignore(worktree, "secrets/*.key")
        rule = check_ignore_one(worktree, "src/handler.py")
        assert rule is None

    def test_handles_path_that_does_not_exist_on_disk(
        self, worktree: Path
    ) -> None:
        """--no-index lets check-ignore match against the rule set even
        when the path is not yet on disk — the common case for planned
        (about-to-be-created) targets."""
        _write_gitignore(worktree, "build/")
        rule = check_ignore_one(worktree, "build/output.txt")
        assert rule is not None
        assert "build/" in rule

    def test_nested_gitignore_source_in_rule(self, worktree: Path) -> None:
        """Rule source should reflect which .gitignore matched."""
        nested = worktree / "src"
        nested.mkdir()
        (nested / ".gitignore").write_text("*.pyc\n", encoding="utf-8")
        rule = check_ignore_one(worktree, "src/compiled.pyc")
        assert rule is not None
        assert rule.startswith("src/.gitignore:")


class TestIsProjectRootGitignore:
    """Coverage for the rebase-hint heuristic."""

    def test_root_gitignore_matches(self) -> None:
        assert is_project_root_gitignore(".gitignore:5:*.log") is True

    def test_nested_gitignore_does_not_match(self) -> None:
        assert is_project_root_gitignore("src/.gitignore:2:*.pyc") is False

    def test_empty_rule_is_false(self) -> None:
        assert is_project_root_gitignore("") is False


# ---------- integration tests: full gate ------------------------------


class TestPreflightGateFromPlanJson:
    """End-to-end with a JSON implementation plan on disk."""

    def test_plan_with_gitignored_target_blocks(self, worktree: Path) -> None:
        _write_gitignore(worktree, "secrets/*.key")
        _write_plan_json(
            worktree,
            "TASK-T1",
            {
                "plan": {
                    "files_to_create": ["secrets/api.key", "src/handler.py"],
                    "files_to_modify": [],
                }
            },
        )

        result = run_preflight_ignore_gate("TASK-T1", worktree)

        assert result.status == STATUS_BLOCKED
        assert len(result.matches) == 1
        assert result.matches[0].path == "secrets/api.key"
        assert ".gitignore:" in result.matches[0].rule
        assert result.rebase_hint is True

    def test_plan_with_no_ignored_targets_passes(self, worktree: Path) -> None:
        _write_gitignore(worktree, "*.log\nbuild/\n")
        _write_plan_json(
            worktree,
            "TASK-T2",
            {
                "plan": {
                    "files_to_create": ["src/handler.py", "src/utils.py"],
                    "files_to_modify": ["README.md"],
                }
            },
        )

        result = run_preflight_ignore_gate("TASK-T2", worktree)

        assert result.status == STATUS_PASSED
        assert result.matches == []
        assert result.rebase_hint is False

    def test_multiple_ignored_targets_all_reported(
        self, worktree: Path
    ) -> None:
        _write_gitignore(worktree, "*.log\nbuild/\n")
        _write_plan_json(
            worktree,
            "TASK-T3",
            {
                "plan": {
                    "files_to_create": [
                        "src/handler.py",
                        "build/output.txt",
                        "app.log",
                    ],
                    "files_to_modify": [],
                }
            },
        )

        result = run_preflight_ignore_gate("TASK-T3", worktree)

        assert result.status == STATUS_BLOCKED
        paths = {m.path for m in result.matches}
        assert paths == {"build/output.txt", "app.log"}
        assert result.rebase_hint is True

    def test_files_to_modify_also_checked(self, worktree: Path) -> None:
        _write_gitignore(worktree, "config/local.yaml")
        _write_plan_json(
            worktree,
            "TASK-T4",
            {
                "plan": {
                    "files_to_create": [],
                    "files_to_modify": ["config/local.yaml"],
                }
            },
        )

        result = run_preflight_ignore_gate("TASK-T4", worktree)

        assert result.status == STATUS_BLOCKED
        assert result.matches[0].path == "config/local.yaml"

    def test_nested_gitignore_does_not_trigger_rebase_hint(
        self, worktree: Path
    ) -> None:
        nested = worktree / "src"
        nested.mkdir()
        (nested / ".gitignore").write_text("generated/\n", encoding="utf-8")
        _write_plan_json(
            worktree,
            "TASK-T5",
            {
                "plan": {
                    "files_to_create": ["src/generated/output.py"],
                    "files_to_modify": [],
                }
            },
        )

        result = run_preflight_ignore_gate("TASK-T5", worktree)

        assert result.status == STATUS_BLOCKED
        assert len(result.matches) == 1
        assert result.rebase_hint is False, (
            "rebase hint should only fire when the matched rule is from "
            "the project-root .gitignore"
        )

    def test_plan_with_dict_shaped_file_entries(self, worktree: Path) -> None:
        """Some legacy plan schemas use ``{path: ..., rationale: ...}``."""
        _write_gitignore(worktree, "secrets/*.key")
        _write_plan_json(
            worktree,
            "TASK-T6",
            {
                "plan": {
                    "files_to_create": [
                        {"path": "secrets/api.key", "rationale": "config"},
                        {"path": "src/handler.py", "rationale": "logic"},
                    ],
                    "files_to_modify": [],
                }
            },
        )

        result = run_preflight_ignore_gate("TASK-T6", worktree)

        assert result.status == STATUS_BLOCKED
        assert result.matches[0].path == "secrets/api.key"


class TestPreflightGateFromFrontmatter:
    """End-to-end falling back to task frontmatter when no plan on disk."""

    def test_frontmatter_files_to_create_used_when_no_plan(
        self, worktree: Path
    ) -> None:
        _write_gitignore(worktree, "secrets/*.key")
        _write_task_file(
            worktree,
            "TASK-T7",
            files_to_create=["secrets/api.key", "src/handler.py"],
        )

        result = run_preflight_ignore_gate("TASK-T7", worktree)

        assert result.status == STATUS_BLOCKED
        assert result.matches[0].path == "secrets/api.key"

    def test_frontmatter_files_to_modify_used_when_no_plan(
        self, worktree: Path
    ) -> None:
        _write_gitignore(worktree, "*.log")
        _write_task_file(
            worktree,
            "TASK-T8",
            files_to_modify=["app.log", "src/main.py"],
        )

        result = run_preflight_ignore_gate("TASK-T8", worktree)

        assert result.status == STATUS_BLOCKED
        assert result.matches[0].path == "app.log"

    def test_frontmatter_with_no_ignored_targets_passes(
        self, worktree: Path
    ) -> None:
        _write_gitignore(worktree, "*.log\nbuild/\n")
        _write_task_file(
            worktree, "TASK-T9", files_to_create=["src/handler.py"]
        )

        result = run_preflight_ignore_gate("TASK-T9", worktree)

        assert result.status == STATUS_PASSED


class TestPreflightGateSkips:
    """The no-source path is a no-op, not a fail-open warning."""

    def test_no_plan_no_frontmatter_skips(self, worktree: Path) -> None:
        result = run_preflight_ignore_gate("TASK-NO-SOURCE", worktree)

        assert result.status == STATUS_SKIPPED
        assert result.skip_reason is not None

    def test_plan_with_empty_lists_falls_through_to_frontmatter(
        self, worktree: Path
    ) -> None:
        """An empty plan should not short-circuit the frontmatter
        fallback; otherwise a stub plan would silently bypass the gate."""
        _write_gitignore(worktree, "secrets/*.key")
        _write_plan_json(
            worktree,
            "TASK-T10",
            {"plan": {"files_to_create": [], "files_to_modify": []}},
        )
        _write_task_file(
            worktree, "TASK-T10", files_to_create=["secrets/api.key"]
        )

        result = run_preflight_ignore_gate("TASK-T10", worktree)

        assert result.status == STATUS_BLOCKED
        assert result.matches[0].path == "secrets/api.key"

    def test_frontmatter_present_but_empty_skips(
        self, worktree: Path
    ) -> None:
        _write_task_file(worktree, "TASK-T11", files_to_create=[])

        result = run_preflight_ignore_gate("TASK-T11", worktree)

        assert result.status == STATUS_SKIPPED

    def test_task_file_with_no_frontmatter_skips(
        self, worktree: Path
    ) -> None:
        task_dir = worktree / "tasks" / "in_progress"
        task_dir.mkdir(parents=True)
        (task_dir / "TASK-T12-bare.md").write_text(
            "# bare task with no frontmatter\n", encoding="utf-8"
        )

        result = run_preflight_ignore_gate("TASK-T12", worktree)

        assert result.status == STATUS_SKIPPED


class TestLoadPlannedTargets:
    """Direct coverage of the source-resolver."""

    def test_prefers_plan_over_frontmatter(self, worktree: Path) -> None:
        _write_plan_json(
            worktree,
            "TASK-T13",
            {"plan": {"files_to_create": ["from_plan.py"], "files_to_modify": []}},
        )
        _write_task_file(
            worktree, "TASK-T13", files_to_create=["from_frontmatter.py"]
        )

        targets = load_planned_targets("TASK-T13", worktree)

        assert targets == ["from_plan.py"]

    def test_falls_back_to_frontmatter_when_no_plan(
        self, worktree: Path
    ) -> None:
        _write_task_file(
            worktree, "TASK-T14", files_to_create=["from_frontmatter.py"]
        )

        targets = load_planned_targets("TASK-T14", worktree)

        assert targets == ["from_frontmatter.py"]

    def test_returns_none_when_no_source(self, worktree: Path) -> None:
        assert load_planned_targets("TASK-T15", worktree) is None


# ---------- message formatting ----------------------------------------


class TestFormatBlockedMessage:
    def test_contains_path_and_rule(self, worktree: Path) -> None:
        _write_gitignore(worktree, "secrets/*.key")
        _write_plan_json(
            worktree,
            "TASK-MSG",
            {
                "plan": {
                    "files_to_create": ["secrets/api.key"],
                    "files_to_modify": [],
                }
            },
        )

        result = run_preflight_ignore_gate("TASK-MSG", worktree)
        msg = format_blocked_message("TASK-MSG", result)

        assert "TASK-MSG" in msg
        assert "secrets/api.key" in msg
        assert ".gitignore:" in msg
        assert "secrets/*.key" in msg
        # Rebase hint should be present for project-root .gitignore match.
        assert "rebas" in msg.lower()

    def test_no_rebase_hint_for_nested_gitignore_match(
        self, worktree: Path
    ) -> None:
        nested = worktree / "src"
        nested.mkdir()
        (nested / ".gitignore").write_text("generated/\n", encoding="utf-8")
        _write_plan_json(
            worktree,
            "TASK-MSG2",
            {
                "plan": {
                    "files_to_create": ["src/generated/output.py"],
                    "files_to_modify": [],
                }
            },
        )

        result = run_preflight_ignore_gate("TASK-MSG2", worktree)
        msg = format_blocked_message("TASK-MSG2", result)

        assert "rebas" not in msg.lower()

    def test_singular_vs_plural_count_phrasing(self, worktree: Path) -> None:
        _write_gitignore(worktree, "*.log\n*.tmp\n")
        _write_plan_json(
            worktree,
            "TASK-MSG3",
            {
                "plan": {
                    "files_to_create": ["a.log", "b.tmp"],
                    "files_to_modify": [],
                }
            },
        )

        result = run_preflight_ignore_gate("TASK-MSG3", worktree)
        msg = format_blocked_message("TASK-MSG3", result)

        assert "2 planned targets are git-ignored" in msg

    def test_raises_on_non_blocked_result(self) -> None:
        from guardkit.orchestrator.preflight_ignore_gate import (
            PreflightResult,
        )

        passed = PreflightResult(status=STATUS_PASSED)
        with pytest.raises(ValueError):
            format_blocked_message("TASK-X", passed)


# ---------- subprocess-error resilience -------------------------------


class TestSubprocessErrorResilience:
    """An infra failure on the check-ignore subprocess should degrade
    to ``not-ignored`` (no false-fail). The Coach still runs the
    existence floor at turn end, so the detection floor is preserved."""

    def test_treats_path_as_not_ignored_when_git_unavailable(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Force subprocess.run to raise FileNotFoundError (mimics git
        # not on PATH).
        def _raise(*args: object, **kwargs: object) -> object:
            raise FileNotFoundError("git not on PATH")

        monkeypatch.setattr(
            "guardkit.orchestrator.preflight_ignore_gate.subprocess.run",
            _raise,
        )

        rule = check_ignore_one(tmp_path, "src/handler.py")

        assert rule is None
