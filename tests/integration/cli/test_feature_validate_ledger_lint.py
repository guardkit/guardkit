"""Integration tests for the B2 / DIM5-F3 plan-time ledger-authorship reject-lint
wired into ``guardkit feature validate``.

The lint refuses a planning session (``/feature-spec`` / ``/feature-plan``,
which run ``guardkit feature validate`` as their plan-output oracle) whose diff
authors ``qa/known-failures.yaml`` — the F2 ledger is human/Coach-at-triage-only
(K15 / LPA-09). It is flag-gated on ``qa.enforce_tier1``:

- flag OFF (the default) → the check is not invoked; validate is a byte-for-byte
  no-op relative to prior behaviour, even when the ledger IS edited;
- flag ON → validate fails (exit 1) with the reject-lint message.

Driven through the click CLI via ``CliRunner`` against a real git repo, so the
full ``git status --porcelain`` reader path is exercised.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from textwrap import dedent

import pytest
from click.testing import CliRunner

from guardkit.cli.feature import feature as feature_group


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@example.com",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@example.com",
    }
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        env=env,
        check=True,
    )


def _valid_feature_body() -> str:
    return dedent(
        """\
        id: FEAT-LEDGL
        name: Ledger-lint fixture
        description: valid feature so validate reaches the reject-lint step.
        created: "2026-07-09T10:00:00Z"
        complexity: 4
        estimated_tasks: 1
        tasks:
          - id: TASK-LEDGL-T1
            file_path: tasks/in_progress/TASK-LEDGL-T1.md
            name: Fixture task
            complexity: 3
            implementation_mode: task-work
            estimated_minutes: 30
        orchestration:
          parallel_groups:
            - [TASK-LEDGL-T1]
          estimated_duration_minutes: 30
          recommended_parallel: 1
        """
    )


def _write_task_file(repo_root: Path) -> None:
    target = repo_root / "tasks" / "in_progress" / "TASK-LEDGL-T1.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        dedent(
            """\
            ---
            id: TASK-LEDGL-T1
            title: Fixture task
            status: in_progress
            ---

            Fixture task body.
            """
        )
    )


@pytest.fixture
def planning_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A committed git repo with a valid feature YAML, chdir'd into.

    The committed ``qa/known-failures.yaml`` is the clean baseline; individual
    tests dirty it (or not) to simulate a planning session's diff.
    """
    repo = tmp_path / "repo"
    (repo / ".guardkit" / "features").mkdir(parents=True)
    (repo / "qa").mkdir(parents=True)
    _write_task_file(repo)
    (repo / ".guardkit" / "features" / "FEAT-LEDGL.yaml").write_text(_valid_feature_body())
    (repo / "qa" / "known-failures.yaml").write_text(
        'format_version: "1.0"\nsuite_id: s\nframework: pytest\n'
        "language: python\nexpected:\n  passed: 0\nknown_failures: []\n"
    )
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "seed")
    monkeypatch.delenv("GUARDKIT_QA_ENFORCE_TIER1", raising=False)
    monkeypatch.chdir(repo)
    return repo


def _edit_ledger(repo: Path) -> None:
    (repo / "qa" / "known-failures.yaml").write_text(
        'format_version: "1.0"\nsuite_id: s\nframework: pytest\n'
        "language: python\nexpected:\n  passed: 0\n"
        "known_failures:\n"
        "  - test_id: tests/a.py::test_x\n"
        "    reason: planner-invented (should be refused)\n"
        '    since: {date: "2026-07-09", sha: abcd}\n'
        "    owner: nobody\n    review_by: \"2026-08-01\"\n"
    )


def test_flag_off_is_noop_even_with_ledger_edit(planning_repo: Path):
    """Default (flag OFF): a ledger edit in the working tree does NOT change the
    validate verdict — a valid feature still passes (exit 0)."""
    _edit_ledger(planning_repo)
    result = CliRunner().invoke(feature_group, ["validate", "FEAT-LEDGL"])
    assert result.exit_code == 0, result.output
    assert "known-failure ledger" not in result.output


def test_flag_on_clean_plan_passes(planning_repo: Path, monkeypatch):
    """Flag ON but no ledger edit: valid feature passes (exit 0)."""
    monkeypatch.setenv("GUARDKIT_QA_ENFORCE_TIER1", "1")
    result = CliRunner().invoke(feature_group, ["validate", "FEAT-LEDGL"])
    assert result.exit_code == 0, result.output


def test_flag_on_ledger_edit_is_refused(planning_repo: Path, monkeypatch):
    """Flag ON with a ledger edit: validate FAILS (exit 1) with the reject-lint
    message — the planner-authorship channel is closed."""
    monkeypatch.setenv("GUARDKIT_QA_ENFORCE_TIER1", "1")
    _edit_ledger(planning_repo)
    result = CliRunner().invoke(feature_group, ["validate", "FEAT-LEDGL"])
    assert result.exit_code == 1, result.output
    assert "must not author the F2 known-failure ledger" in result.output
    assert "qa/known-failures.yaml" in result.output


def test_flag_on_untracked_ledger_is_refused(planning_repo: Path, monkeypatch):
    """A brand-new (untracked) ledger authored by the planner is also refused —
    ``git status --porcelain`` surfaces untracked adds."""
    monkeypatch.setenv("GUARDKIT_QA_ENFORCE_TIER1", "1")
    # Remove the committed ledger and re-add as untracked to simulate a planner
    # creating the file where none was tracked.
    _git(planning_repo, "rm", "-q", "qa/known-failures.yaml")
    _git(planning_repo, "commit", "-q", "-m", "drop ledger")
    (planning_repo / "qa").mkdir(exist_ok=True)
    _edit_ledger(planning_repo)  # now untracked
    result = CliRunner().invoke(feature_group, ["validate", "FEAT-LEDGL"])
    assert result.exit_code == 1, result.output
    assert "must not author the F2 known-failure ledger" in result.output
