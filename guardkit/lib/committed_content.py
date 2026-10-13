"""Read a repository's committed content: files and tree modes at one commit.

One small reader, shared by ``guardkit memory seed`` (the commit at ``HEAD``)
and the Coach's binding-documents capture (the build's source commit), so both
read committed text the same way: ``git ls-tree`` for paths and modes (a
symbolic link is mode ``120000``), ``git cat-file blob <rev>:<path>`` for the
bytes, never the working tree.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from guardkit.lib.project_git import run_git


class CommittedContentError(Exception):
    """Git could not answer; the message says what was asked and why it failed."""


def git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    """Run git in ``repo`` through the factory's git helper (literal file names,
    no project program, a fixed sentence instead of git's error text)."""
    return run_git(["-C", str(repo), *args], text=False, timeout=60)


def git_text(repo: Path, *args: str) -> str:
    """Run git in ``repo`` and return its output, or raise with the helper's sentence."""
    result = git(repo, *args)
    if result.returncode != 0:
        raise CommittedContentError(
            f"git {' '.join(args)} failed in {repo}: "
            f"{result.stderr.decode('utf-8', 'replace').strip()}"
        )
    return result.stdout.decode("utf-8")


def tree_entries(repo: Path, rev: str = "HEAD") -> dict[str, str]:
    """Every file at ``rev``, by path, with its tree mode (``100644``, ``120000``…)."""
    out = git(repo, "ls-tree", "-r", "-z", rev)
    if out.returncode != 0:
        raise CommittedContentError(
            f"Could not list the files at {rev} in {repo}: "
            f"{out.stderr.decode('utf-8', 'replace').strip()}"
        )
    entries: dict[str, str] = {}
    for record in out.stdout.decode("utf-8").split("\0"):
        if not record:
            continue
        meta, _, path = record.partition("\t")
        entries[path] = meta.split(" ", 1)[0]
    return entries


def changed_paths(repo: Path, paths: list[str]) -> set[str]:
    """Which of ``paths`` differ from HEAD in the index or the working tree."""
    if not paths:
        return set()
    out = git(repo, "status", "--porcelain=v1", "-z", "--untracked-files=no", "--", *paths)
    if out.returncode != 0:
        raise CommittedContentError(
            f"Could not check {repo} for uncommitted changes: "
            f"{out.stderr.decode('utf-8', 'replace').strip()}"
        )
    changed: set[str] = set()
    records = out.stdout.decode("utf-8").split("\0")
    index = 0
    while index < len(records):
        record = records[index]
        index += 1
        if len(record) < 4:
            continue
        changed.add(record[3:])
        if record[0] in "RC":  # a rename names its source next
            if index < len(records):
                changed.add(records[index])
            index += 1
    return changed


def blob(repo: Path, path: str, rev: str = "HEAD") -> bytes:
    """The committed bytes of ``path`` at ``rev`` (for a link: its target's name)."""
    out = git(repo, "cat-file", "blob", f"{rev}:{path}")
    if out.returncode != 0:
        raise CommittedContentError(f"Could not read {path} at {rev} in {repo}.")
    return out.stdout
