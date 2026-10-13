"""Real-git repositories whose own settings name marker programs.

Shared by the factory-git tests (``tests/unit/test_project_git.py`` and
``tests/integration/test_factory_git_runs_no_project_programs.py``).

Every marker program appends one line to a marker file: its own name and
whether it could see :data:`SECRET_NAME` in its environment. A test runs a git
command and then reads :meth:`Lab.fired` to learn which project programs ran.

Edits are deliberately the SAME SIZE as the original content: git skips
reading a file (and so never runs its clean filter) when the size alone says
it changed.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Sequence

SECRET_NAME = "FACTORY_TEST_SECRET"
SECRET_VALUE = "s3cret-value"

#: Hooks planted in the project's ``.git/hooks``.
HOOKS = (
    "pre-commit",
    "prepare-commit-msg",
    "commit-msg",
    "post-commit",
    "post-checkout",
    "post-merge",
    "pre-merge-commit",
    "reference-transaction",
    "post-index-change",
    "post-rewrite",
    "pre-rebase",
)

GIT = shutil.which("git") or "git"

#: Filter names the fixtures plant; set-up git switches them all off.
SETUP_SILENCED_FILTERS = ("mark", "proc", "late", "subf", "racer", "liar")


def git_version() -> str:
    return subprocess.run(
        [GIT, "--version"], capture_output=True, text=True, check=False
    ).stdout.strip()


class Lab:
    """Marker programs, a marker file and plain-git helpers in one folder."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.bin = root / "bin"
        self.bin.mkdir(parents=True, exist_ok=True)
        self.marks = root / "marks.txt"
        self.home = root / "home"
        self.home.mkdir(exist_ok=True)
        self._edits = 0
        for name, body in (
            ("clean", "cat\n"),
            ("smudge", "cat\n"),
            ("process", "exit 1\n"),
            ("textconv", 'cat "$1"\n'),
            ("extdiff", "exit 0\n"),
            ("mergedrv", "exit 1\n"),
            ("fsmonitor", "exit 1\n"),
            ("gpg", "exit 1\n"),
            ("sshcmd", "exit 1\n"),
            ("credhelper", "exit 0\n"),
            ("credhelper_url", "exit 0\n"),
            ("askpass", "exit 1\n"),
            ("uploadpack", 'exec git-upload-pack "$@"\n'),
            ("extmark", "exit 1\n"),
            ("gitproxy", "exit 1\n"),
            ("smudge_wt", "cat\n"),
            ("smudge_br", "cat\n"),
            ("smudge_co", "cat\n"),
            ("subclean", "cat\n"),
            ("subextdiff", "exit 0\n"),
            ("subtextconv", 'cat "$1"\n'),
            ("execmark", "exit 0\n"),
            ("late", "cat\n"),
            ("racer", "cat\n"),
        ):
            self.program(name, body)
        for hook in HOOKS:
            self.program("hook-" + hook, "exit 0\n")

    # -- programs and markers ------------------------------------------------

    def program(self, name: str, body: str = "exit 0\n") -> str:
        path = self.bin / name
        path.write_text(
            "#!/bin/sh\n"
            f'echo "{name} secret=${{{SECRET_NAME}:-absent}}" >> "{self.marks}"\n'
            + body
        )
        path.chmod(0o755)
        return str(path)

    def path(self, name: str) -> str:
        return str(self.bin / name)

    def fired(self) -> List[str]:
        """The marker lines written since the last call, then forget them."""
        if not self.marks.exists():
            return []
        lines = sorted({line for line in self.marks.read_text().splitlines() if line})
        self.marks.unlink()
        return lines

    @staticmethod
    def names(lines: Sequence[str]) -> List[str]:
        return sorted({line.split()[0] for line in lines})

    @staticmethod
    def saw_secret(lines: Sequence[str]) -> bool:
        return any(f"secret={SECRET_VALUE}" in line for line in lines)

    # -- plain git -----------------------------------------------------------

    def plain_env(self) -> Dict[str, str]:
        """The inherited environment, as the factory's git saw it before the fix."""
        return {**os.environ, SECRET_NAME: SECRET_VALUE, "GIT_TERMINAL_PROMPT": "0"}

    def plain(
        self, repo: Path, *args: str, input: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
    ) -> subprocess.CompletedProcess:
        return subprocess.run(
            [GIT, *args], cwd=repo, capture_output=True, text=True, input=input,
            env=env or self.plain_env(), check=False,
        )

    def setup_git(self, repo: Path, *args: str) -> str:
        """Fixture set-up git: no project programs, no hooks, must succeed."""
        argv = [GIT, "-c", "core.hooksPath=/dev/null", "-c", "core.fsmonitor=false",
                "-c", "protocol.file.allow=always"]
        for name in SETUP_SILENCED_FILTERS:
            for key in ("clean", "smudge", "process"):
                argv += ["-c", f"filter.{name}.{key}="]
        argv += list(args)
        done = subprocess.run(
            argv, cwd=repo, capture_output=True, text=True, check=False,
            env={k: v for k, v in os.environ.items() if k != SECRET_NAME},
        )
        assert done.returncode == 0, (args, done.stderr)
        return done.stdout

    # -- edits ---------------------------------------------------------------

    def same_size_edit(self, path: Path) -> None:
        """Change the content but not the size, so git must read the file."""
        self._edits += 1
        old = path.read_text()
        letter = chr(ord("a") + self._edits % 26)
        if old[:1] == letter:
            letter = chr(ord("a") + (self._edits + 1) % 26)
        path.write_text(letter + old[1:])

    # -- repositories --------------------------------------------------------

    def base_repo(self, name: str, attributes: str = "") -> Path:
        """A committed repository on ``main`` with ``a.txt``; nothing planted."""
        repo = self.root / name
        repo.mkdir(parents=True)
        g = lambda *a: self.setup_git(repo, *a)  # noqa: E731
        g("init", "-q", "-b", "main")
        g("config", "user.name", "Lab")
        g("config", "user.email", "lab@example.invalid")
        if attributes:
            (repo / ".gitattributes").write_text(attributes)
        (repo / "a.txt").write_text("one\n")
        g("add", "-A")
        g("commit", "-qm", "base")
        return repo

    def marked_repo(self, name: str, edits: bool = True, process: bool = False) -> Path:
        """The shared fixture: every program-running setting planted.

        ``main`` and ``side`` both change ``a.txt`` (so a merge needs the
        merge program). With ``edits``, the working tree then has same-size
        edits to the filtered ``.txt`` and ``.dat`` files. With ``process``,
        ``.dat`` files also name a long-running "process" filter, which fails
        and so stops most commands early: that one has its own cases.
        """
        repo = self.root / name
        repo.mkdir(parents=True)
        g = lambda *a: self.setup_git(repo, *a)  # noqa: E731
        g("init", "-q", "-b", "main")
        g("config", "user.name", "Lab")
        g("config", "user.email", "lab@example.invalid")
        (repo / ".gitattributes").write_text(
            "*.txt filter=mark diff=mark merge=mark\n*.dat filter=proc\n"
        )
        (repo / "a.txt").write_text("1\n2\n3\n4\n5\n6\n")
        (repo / "b.txt").write_text("two\n")
        (repo / "c.dat").write_text("three\n")
        g("add", "-A")
        g("commit", "-qm", "base")
        g("branch", "side")
        g("checkout", "-q", "side")
        (repo / "a.txt").write_text("1\n2\n3\n4\n5\nsix\n")
        g("commit", "-qam", "side")
        g("checkout", "-q", "main")
        (repo / "a.txt").write_text("one\n2\n3\n4\n5\n6\n")
        g("commit", "-qam", "main")
        self.plant(repo, process=process)
        if edits:
            self.same_size_edit(repo / "a.txt")
            self.same_size_edit(repo / "b.txt")
            self.same_size_edit(repo / "c.dat")
        return repo

    def plant(self, repo: Path, process: bool = False) -> None:
        """Write the program-running settings and hooks into the project."""
        g = lambda *a: self.setup_git(repo, *a)  # noqa: E731
        if process:
            g("config", "filter.proc.process", self.path("process"))
        for key, value in (
            ("filter.mark.clean", self.path("clean")),
            ("filter.mark.smudge", self.path("smudge")),
            ("diff.mark.textconv", self.path("textconv")),
            ("diff.external", self.path("extdiff")),
            ("merge.mark.driver", self.path("mergedrv") + " %O %A %B"),
            ("core.fsmonitor", self.path("fsmonitor")),
            ("commit.gpgSign", "true"),
            ("gpg.program", self.path("gpg")),
        ):
            g("config", key, value)
        hooks = Path(g("rev-parse", "--absolute-git-dir").strip()) / "hooks"
        hooks.mkdir(exist_ok=True)
        for hook in HOOKS:
            shutil.copy(self.bin / ("hook-" + hook), hooks / hook)

    def merge_repo(self, name: str) -> Path:
        """``side`` carries a commit with a (fake) signature; ``gpg.program``
        names the marker. Nothing else is planted."""
        repo = self.base_repo(name)
        g = lambda *a: self.setup_git(repo, *a)  # noqa: E731
        g("branch", "side")
        g("checkout", "-q", "side")
        (repo / "b.md").write_text("b\n")
        g("add", "-A")
        tree = g("write-tree").strip()
        parent = g("rev-parse", "HEAD").strip()
        body = (
            f"tree {tree}\nparent {parent}\n"
            "author Lab <lab@example.invalid> 1 +0000\n"
            "committer Lab <lab@example.invalid> 1 +0000\n"
            "gpgsig -----BEGIN PGP SIGNATURE-----\n \n fake\n -----END PGP SIGNATURE-----\n"
            "\nsigned side\n"
        )
        commit = subprocess.run(
            [GIT, "hash-object", "-t", "commit", "-w", "--stdin"], cwd=repo,
            input=body, capture_output=True, text=True, check=True,
        ).stdout.strip()
        g("update-ref", "refs/heads/side", commit)
        g("checkout", "-qf", "main")
        g("reset", "-q", "--hard")
        g("config", "gpg.program", self.path("gpg"))
        return repo

    def include(self, repo: Path, condition: Optional[str], text: str, file_name: str) -> None:
        """Write ``text`` to a settings file in ``.git`` and include it."""
        git_dir = Path(self.setup_git(repo, "rev-parse", "--git-common-dir").strip())
        if not git_dir.is_absolute():
            git_dir = repo / git_dir
        (git_dir / file_name).write_text(text)
        key = "include.path" if condition is None else f"includeIf.{condition}.path"
        self.setup_git(repo, "config", key, file_name)

    def submodule_repo(self, name: str) -> Path:
        """A project with a registered submodule ``sub`` whose own settings
        name a clean filter (``subclean``). The submodule's tracked file has
        a same-size edit."""
        source = self.base_repo(name + "-src", attributes="*.txt filter=subf\n")
        repo = self.base_repo(name)
        self.setup_git(repo, "submodule", "add", "-q", str(source), "sub")
        self.setup_git(repo, "commit", "-qm", "add sub")
        self.setup_git(repo / "sub", "config", "filter.subf.clean", self.path("subclean"))
        self.same_size_edit(repo / "sub" / "a.txt")
        return repo

    def moved_submodule_repo(self, name: str, external: bool) -> Path:
        """A project whose submodule's recorded commit moved (not committed in
        the outer project), whose submodule names an external diff or a text
        converter, and whose own settings send reads into submodules."""
        source = self.base_repo(name + "-src", attributes="*.txt diff=tc\n")
        repo = self.base_repo(name)
        self.setup_git(repo, "submodule", "add", "-q", str(source), "sub")
        self.setup_git(repo, "commit", "-qm", "add sub")
        sub = repo / "sub"
        if external:
            self.setup_git(sub, "config", "diff.external", self.path("subextdiff"))
        else:
            self.setup_git(sub, "config", "diff.tc.textconv", self.path("subtextconv"))
        (sub / "a.txt").write_text("moved\n")
        self.setup_git(sub, "-c", "user.name=Lab", "-c", "user.email=lab@example.invalid",
                       "commit", "-qam", "moved in sub")
        for key, value in (
            ("diff.submodule", "diff"),
            ("status.submoduleSummary", "true"),
            ("submodule.recurse", "true"),
            ("diff.ignoreSubmodules", "none"),
            ("submodule.sub.ignore", "none"),
        ):
            self.setup_git(repo, "config", key, value)
        return repo

    def partial_clone(self, name: str) -> Path:
        """A blob-less partial clone with nothing checked out, so a checkout
        must fetch the missing file lazily from the promisor remote."""
        origin = self.root / (name + "-origin")
        origin.mkdir()
        g = lambda *a: self.setup_git(origin, *a)  # noqa: E731
        g("init", "-q", "-b", "main")
        (origin / "x.md").write_text("x\n")
        g("add", "-A")
        g("-c", "user.name=Lab", "-c", "user.email=lab@example.invalid", "commit", "-qm", "x")
        g("config", "uploadpack.allowFilter", "true")
        repo = self.root / name
        self.setup_git(
            self.root, "clone", "-q", "--no-checkout", "--filter=blob:none",
            f"file://{origin}", str(repo),
        )
        return repo
