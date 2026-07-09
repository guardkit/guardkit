"""ST-05 mutation stage tests, incl. THE B6 GATE (auth-header survivor)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from guardkit.orchestrator.qa_stages import (
    MutationError,
    MutationSandbox,
    make_pytest_runner,
    revert_hunks_operator,
    run_mutation_campaign,
    split_diff_by_file,
    strip_auth_header_operator,
)
from guardkit.orchestrator.qa_stages.mutation import _MUTATED_AUTH_KEY

FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "qa_stages" / "auth_client"


def _pytest_runner():
    return make_pytest_runner(
        [sys.executable, "-m", "pytest", "-q", "test_authclient.py"], timeout=120
    )


# --------------------------------------------------------------------------- #
# Operator
# --------------------------------------------------------------------------- #
def test_strip_auth_header_emits_one_mutant_per_site():
    text = (FIXTURE / "authclient.py").read_text()
    mutants = strip_auth_header_operator("authclient.py", text)
    # Four verbs each carry an Authorization key.
    assert len(mutants) == 4
    assert all(m.operator == "strip-auth-header" for m in mutants)
    assert all(":" in m.site for m in mutants)


def test_strip_auth_header_is_fstring_safe(tmp_path):
    # A header value containing f-string braces must not corrupt the source.
    src = 'H = {"Authorization": f"Bearer {tok}"}\n'
    mutants = strip_auth_header_operator("m.py", src)
    assert len(mutants) == 1
    target = tmp_path / "m.py"
    target.write_text(src)
    mutants[0].apply(tmp_path)
    mutated = target.read_text()
    # The value/f-string is intact; only the KEY is renamed → still valid python.
    compile(mutated, "m.py", "exec")
    assert _MUTATED_AUTH_KEY in mutated
    assert '"Authorization"' not in mutated
    assert "f\"Bearer {tok}\"" in mutated


def test_strip_auth_header_matches_single_quotes_and_case():
    mutants = strip_auth_header_operator("m.py", "h = {'authorization': v}\n")
    assert len(mutants) == 1


# --------------------------------------------------------------------------- #
# THE GATE — a deliberately unpinned auth header is caught as a survivor
# --------------------------------------------------------------------------- #
def test_mutation_gate_catches_unpinned_auth_header():
    """B6 GATE: the delete verb's auth header is unpinned → surviving mutant."""
    text = (FIXTURE / "authclient.py").read_text()
    mutants = strip_auth_header_operator("authclient.py", text)
    sandbox = MutationSandbox(FIXTURE, prefer_git=False)

    result = run_mutation_campaign(sandbox, mutants, _pytest_runner())

    assert result.baseline_green is True
    # get/post/put pins kill their mutants; delete is the coverage hole.
    assert len(result.survivors) == 1
    survivor = result.survivors[0]
    assert survivor.operator == "strip-auth-header"
    assert survivor.site.startswith("authclient.py:")
    # Three verbs are pinned → three mutants killed.
    assert len(result.killed) == 3
    assert not result.errored


def test_mutation_campaign_raises_on_red_baseline(tmp_path):
    """Absence-of-failure: a red baseline cannot certify 'no coverage holes'."""
    (tmp_path / "src.py").write_text('AUTH = {"Authorization": "x"}\n')
    (tmp_path / "test_src.py").write_text("def test_fail():\n    assert False\n")
    text = (tmp_path / "src.py").read_text()
    mutants = strip_auth_header_operator("src.py", text)
    sandbox = MutationSandbox(tmp_path, prefer_git=False)
    runner = make_pytest_runner([sys.executable, "-m", "pytest", "-q", "test_src.py"], timeout=120)

    with pytest.raises(MutationError, match="baseline is RED"):
        run_mutation_campaign(sandbox, mutants, runner)


def test_no_mutants_yields_empty_campaign():
    text = "def f():\n    return 1\n"
    mutants = strip_auth_header_operator("m.py", text)
    assert mutants == []


# --------------------------------------------------------------------------- #
# revert-hunk operator (git-backed) — the second named operator
# --------------------------------------------------------------------------- #
def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, text=True, check=True
    ).stdout


def test_split_diff_by_file_and_revert_hunk(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "t@t")
    _git(root, "config", "user.name", "t")
    (root / "m.py").write_text("def add(a, b):\n    return a + b\n")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "base")
    base = _git(root, "rev-parse", "HEAD").strip()
    # A change that no test pins.
    (root / "m.py").write_text("def add(a, b):\n    return a + b + 0\n")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "change")

    diff = _git(root, "diff", base, "--", "m.py")
    by_file = split_diff_by_file(diff)
    assert "m.py" in by_file
    mutants = revert_hunks_operator("m.py", by_file["m.py"])
    assert len(mutants) >= 1
    assert mutants[0].operator == "revert-hunk"

    # Applying the revert in a git sandbox restores the base line.
    sandbox = MutationSandbox(root)
    with sandbox.materialize() as box:
        assert box.is_git  # git worktree isolation, not the task branch
        mutants[0].apply(box.path)
        reverted = (box.path / "m.py").read_text()
    assert "+ 0" not in reverted
