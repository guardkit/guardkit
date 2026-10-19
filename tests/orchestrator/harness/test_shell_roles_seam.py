"""Seam: the builder's and the checker's shells do not share a home folder.

19 October 2026. GuardKit's selector names the role it builds a shell for
(``shell_role_for``: the Player is the builder, the Coach and its test run the
checker) and the installed guardkitfactory gives each role its own private
``HOME`` and ``TMPDIR``. Built here exactly as the selector builds them, with
the real factory, for a real linked worktree: what the builder's shell leaves
in its home folder (a ``~/.npmrc``, a ``~/.gitconfig``, a marker) is not seen
by the checker's shell, which still runs the project's tests normally.

Skips, like the other seam modules, when guardkitfactory is not installed.
It fails (it does not skip) against a factory that cannot take the role.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

guardkitfactory_harness = pytest.importorskip(
    "guardkitfactory.harness",
    reason="guardkitfactory + langchain stack not installed; seam test only",
)

from guardkit.orchestrator.harness.selector import (  # noqa: E402
    _build_backend_with_optional_cap,
    shell_role_for,
)
from guardkit.orchestrator.paths import prepare_builder_scratch_dir  # noqa: E402

pytestmark = pytest.mark.seam

_GIT_ENV = {
    "PATH": "/usr/bin:/bin",
    "HOME": "/nonexistent",
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_AUTHOR_NAME": "t",
    "GIT_AUTHOR_EMAIL": "t@example.invalid",
    "GIT_COMMITTER_NAME": "t",
    "GIT_COMMITTER_EMAIL": "t@example.invalid",
}


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, env=_GIT_ENV, check=True, capture_output=True,
        text=True,
    ).stdout


def _factory_worktree(tmp_path: Path) -> Path:
    host = tmp_path / "host"
    host.mkdir()
    _git(host, "init", "-q")
    (host / "test_sample.py").write_text(
        "import unittest\n\n\n"
        "class Sample(unittest.TestCase):\n"
        "    def test_adds(self):\n"
        "        self.assertEqual(1 + 1, 2)\n",
        encoding="utf-8",
    )
    _git(host, "add", "-A")
    _git(host, "commit", "-q", "-m", "start")
    worktree = host / ".guardkit" / "worktrees" / "FEAT-X"
    _git(host, "worktree", "add", "-q", "-b", "autobuild/FEAT-X", str(worktree))
    return worktree


def test_the_builder_cannot_change_what_the_checker_sees(tmp_path: Path) -> None:
    worktree = _factory_worktree(tmp_path)
    factory = guardkitfactory_harness.build_autobuild_backend
    builder = _build_backend_with_optional_cap(
        factory, worktree, None, (), prepare_builder_scratch_dir(worktree),
        shell_role=shell_role_for("player"),
    )
    checker = _build_backend_with_optional_cap(
        factory, worktree, None, shell_role=shell_role_for("coach"),
    )
    assert builder.default._env["HOME"] != checker.default._env["HOME"]
    assert builder.default._env["TMPDIR"] != checker.default._env["TMPDIR"]

    planted = builder.execute(
        'set -e; echo builder > "$HOME/left-by-builder"; '
        'echo builder > "$TMPDIR/left-by-builder"; '
        'printf "[user]\\n\\tname = planted-by-builder\\n" > "$HOME/.gitconfig"; '
        'echo "registry=https://example.invalid/" > "$HOME/.npmrc"; '
        "git config --get user.name"
    )
    assert planted.exit_code == 0, planted.output
    assert "planted-by-builder" in planted.output  # control: it is read there

    looked = checker.execute(
        'ls -A "$HOME"; echo ---; ls -A "$TMPDIR"; echo ---; '
        'git config --get user.name || echo no-user-name'
    )
    assert looked.exit_code == 0, looked.output
    assert "left-by-builder" not in looked.output
    assert ".gitconfig" not in looked.output and ".npmrc" not in looked.output
    assert "no-user-name" in looked.output

    tests = checker.execute("python3 -m unittest -v test_sample")
    assert tests.exit_code == 0, tests.output
    assert "OK" in tests.output and "test_adds" in tests.output
    assert _git(worktree, "status", "--porcelain", "--untracked-files=all") == ""
