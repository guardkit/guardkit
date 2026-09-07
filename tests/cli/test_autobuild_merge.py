"""``guardkit autobuild merge --branch`` (2026-09-07, Part M of the
rewrite-on-refusal lane, rule 53): the merge word merges the branch the build
actually made.

Every build so far was a feature build on ``autobuild/<FEATURE_ID>``, so the
branch was implied. A repair's commits land on the journey's own branch
(``fix/<task id>-<build8>``), so the command now takes ``--branch``. Without
the flag the command is what it was: ``execute_merge`` is called with
``branch=None`` and every other argument exactly as before, and
``autobuild/<FEATURE_ID>`` is merged. The JSON report's ``branch`` field names
whichever branch was merged.

The contract with forge's half (fixed so both could be built at once): forge
passes ``--branch <merge_branch>`` only when the build row's ``merge_branch``
is set; otherwise its argv is byte-identical to today's. So the one thing this
file must prove about the default is that the flag's absence changes nothing.

Real git in ``tmp_path`` for the merges (the ``test_merge_executor`` pattern:
no mocks of git, no network, no seats). One test records the executor's
arguments to prove the flag changes exactly one of them.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Dict, List

import pytest
from click.testing import CliRunner

from guardkit.cli.main import cli
from guardkit.orchestrator import merge_executor
from guardkit.orchestrator.merge_executor import OUTCOME_MERGED, MergeReport

REPAIR_BRANCH = "fix/TASK-X-FIX1-1a2b3c4d"


# ---------------------------------------------------------------------------
# git fixture repo
# ---------------------------------------------------------------------------


def _git(repo: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=str(repo),
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout.strip()


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """main, autobuild/FEAT-X (feature.txt) and a repair branch (repair.txt).

    The two branches carry different files, so what lands on main says which
    branch was merged. HEAD is on main and the command runs from the root.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "t@t.t")
    _git(repo, "config", "user.name", "t")
    (repo / "app.py").write_text("x = 1\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "base")

    _git(repo, "checkout", "-q", "-b", "autobuild/FEAT-X")
    (repo / "feature.txt").write_text("the feature\n", encoding="utf-8")
    _git(repo, "add", "feature.txt")
    _git(repo, "commit", "-q", "-m", "feature work")

    _git(repo, "checkout", "-q", "-b", REPAIR_BRANCH, "main")
    (repo / "repair.txt").write_text("the repair\n", encoding="utf-8")
    _git(repo, "add", "repair.txt")
    _git(repo, "commit", "-q", "-m", "repair work")

    _git(repo, "checkout", "-q", "main")
    monkeypatch.chdir(repo)
    return repo


def _merge(*args: str):
    return CliRunner().invoke(cli, ["autobuild", "merge", *args])


# ---------------------------------------------------------------------------
# the flag on real git
# ---------------------------------------------------------------------------


def test_without_the_flag_the_feature_branch_is_merged(repo: Path) -> None:
    result = _merge("FEAT-X", "--no-verify", "--json")

    assert result.exit_code == 0, result.output
    report = json.loads(result.output)
    assert report["outcome"] == OUTCOME_MERGED
    assert report["branch"] == "autobuild/FEAT-X"
    assert (repo / "feature.txt").exists()
    assert not (repo / "repair.txt").exists()


def test_the_flag_merges_the_named_branch_and_the_report_names_it(
    repo: Path,
) -> None:
    pre = _git(repo, "rev-parse", "main")
    repair_sha = _git(repo, "rev-parse", REPAIR_BRANCH)

    result = _merge("FEAT-X", "--branch", REPAIR_BRANCH, "--no-verify", "--json")

    assert result.exit_code == 0, result.output
    report = json.loads(result.output)
    assert report["outcome"] == OUTCOME_MERGED
    assert report["branch"] == REPAIR_BRANCH
    assert report["pre_sha"] == pre
    # The named branch's commits landed; the feature branch's did not.
    assert (repo / "repair.txt").exists()
    assert not (repo / "feature.txt").exists()
    parents = _git(repo, "rev-list", "--parents", "-1", "main").split()
    assert parents[1:] == [pre, repair_sha]
    message = _git(repo, "log", "-1", "--format=%B", "main")
    assert f"branch {REPAIR_BRANCH} retained as the rollback path" in message
    # Both branches are kept: the merged one is the rollback path.
    assert _git(repo, "rev-parse", "--verify", f"refs/heads/{REPAIR_BRANCH}")
    assert _git(repo, "rev-parse", "--verify", "refs/heads/autobuild/FEAT-X")


def test_a_missing_named_branch_refuses_with_exit_2_and_names_it(
    repo: Path,
) -> None:
    pre = _git(repo, "rev-parse", "main")

    result = _merge("FEAT-X", "--branch", "fix/nowhere", "--no-verify", "--json")

    assert result.exit_code == 2, result.output
    report = json.loads(result.output)
    assert report["outcome"] == "refused"
    assert report["refusal_reason"] == "branch fix/nowhere does not exist"
    assert report["branch"] == "fix/nowhere"
    # The feature branch existing does not rescue a named branch that is
    # missing: nothing merged, nothing moved.
    assert _git(repo, "rev-parse", "main") == pre
    assert not (repo / "feature.txt").exists()
    assert _git(repo, "status", "--porcelain") == ""


def test_the_receipt_names_the_branch_when_not_json(repo: Path) -> None:
    result = _merge("FEAT-X", "--branch", REPAIR_BRANCH, "--no-verify")
    assert result.exit_code == 0, result.output
    assert f"Branch {REPAIR_BRANCH} is kept as the rollback path." in result.output


# ---------------------------------------------------------------------------
# the flag changes exactly one argument to the executor
# ---------------------------------------------------------------------------


def test_the_flag_changes_exactly_one_executor_argument(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Without --branch, ``execute_merge`` is called with ``branch=None`` and
    everything else exactly as before; with it, only ``branch`` differs."""
    calls: List[Dict[str, Any]] = []

    def fake_execute_merge(**kwargs: Any) -> MergeReport:
        calls.append(kwargs)
        return MergeReport(
            outcome=OUTCOME_MERGED,
            feature_id=kwargs["feature_id"],
            target_branch=kwargs["target_branch"],
            branch=merge_executor.branch_to_merge(
                kwargs["feature_id"], kwargs.get("branch")
            ),
        )

    monkeypatch.setattr(merge_executor, "execute_merge", fake_execute_merge)
    monkeypatch.chdir(tmp_path)

    common = [
        "FEAT-E613",
        "--target",
        "main",
        "--expect-main-sha",
        "3f2c1a9",
        "--no-verify",
        "--verify-timeout",
        "5",
        "--json",
    ]
    without = _merge(*common)
    with_flag = _merge(*common, "--branch", REPAIR_BRANCH)

    assert without.exit_code == 0, without.output
    assert with_flag.exit_code == 0, with_flag.output
    assert len(calls) == 2
    plain, named = calls

    assert plain["branch"] is None
    assert named["branch"] == REPAIR_BRANCH
    # Every other argument is identical: the flag touches nothing else.
    assert {k: v for k, v in plain.items() if k != "branch"} == {
        k: v for k, v in named.items() if k != "branch"
    }
    assert plain["expect_target_sha"] == "3f2c1a9"
    assert plain["verify_timeout"] == 5
    assert plain["verify"] is False

    assert json.loads(without.output)["branch"] == "autobuild/FEAT-E613"
    assert json.loads(with_flag.output)["branch"] == REPAIR_BRANCH


def test_help_names_the_flag_and_the_default() -> None:
    result = _merge("--help")
    assert result.exit_code == 0
    assert "--branch" in result.output
    assert "autobuild/FEATURE_ID" in result.output
