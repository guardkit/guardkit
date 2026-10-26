"""Protected paths hold the build's committed content before every Coach run.

A project declares ``autobuild.player.protected_paths`` (acceptance tests, a
check script, a read-only copy of a prototype). The Player's file tools refuse
to change them, but its shell cannot be confined that way. So before every
Coach run (and so before the turn's checkpoint commit, which follows the
Coach) each declared path in the worktree is compared with the commit the
build started from, and put back exactly when anything differs.

Only files that existed at that commit are protected (step 2, 26 October
2026): a new file the builder creates inside a protected folder is its own
work, and stays. The same file list is what the builder's file tools refuse
to change (:func:`protected_files_at_start`), so both copies agree.

The declaration is read from that commit too, not from the worktree the
Player can edit. Git is asked only for committed objects (``ls-tree`` and
``cat-file`` by object id, with replacement objects switched off); nothing
here runs ``checkout``, ``diff`` or ``status``, which apply filters the
project can set. The worktree side is read without following links, and a
file is only read when its size already matches the committed one.

The committed bytes are the reference. A protected file whose checkout the
project changes through a ``filter`` or ``eol`` attribute (Git LFS, line-ending
conversion) would be found changed and put back as committed on every check;
such paths are not refused at build start (not done: 17 October 2026).

The git index and the branch are held to the same commit (review R1, 17
October 2026): a protected entry staged with other content, or flagged
assume-unchanged or skip-worktree, is replaced with the commit's blob id and
mode through ``update-index --index-info`` (no filters run), and a protected
path changed by a commit on the branch is put back by one corrective commit
built from a temporary index (``read-tree``, ``update-index``,
``write-tree``, ``commit-tree``) and moved in with ``update-ref`` only if the
branch has not moved meanwhile. A corrective commit, rather than stopping the
task, because it changes nothing but the protected paths and keeps the
turn's other work; the branch's net change under them is then nil.
"""

from __future__ import annotations

import hashlib
import logging
import os
import posixpath
import shutil
import stat
import tempfile
from dataclasses import dataclass
from pathlib import Path

from guardkit.lib.committed_content import git
from guardkit.lib.project_git import run_git

_NO_REPLACE = ("-c", "core.useReplaceRefs=false")
_MAX_LISTED = 10

logger = logging.getLogger(__name__)

# The protected files of each worktree as they were at its build's start
# commit, recorded when the reference is loaded (step 2, 26 October 2026).
_started_with: dict[str, tuple[str, ...]] = {}


def _run(repo: Path, *args: str, data: bytes | None = None, index: str | None = None) -> bytes:
    """Run a filter-free git command for this check, or raise with a plain sentence."""
    out = run_git(
        ["-C", str(repo), *_NO_REPLACE, *args], input=data, text=False, timeout=60,
        env={"GIT_INDEX_FILE": index} if index else None,
    )
    if out.returncode != 0:
        raise ProtectedPathsError(f"git {args[0]} failed in {repo} while checking protected paths.")
    return out.stdout


class ProtectedPathsError(Exception):
    """A protected path could not be read or put back; the message says which."""


@dataclass(frozen=True)
class ProtectedReference:
    """The build's commit, the protected paths it declares, and the build branch."""

    commit: str
    paths: tuple[str, ...]
    #: The build branch's full ref name (``refs/heads/...``), fixed at build start.
    ref: str


def _committed(repo: Path, commit: str, path: str) -> dict[str, tuple[str, str, int]]:
    """Every committed file at or under ``path``: ``{path: (mode, object id, size)}``."""
    out = git(repo, *_NO_REPLACE, "ls-tree", "-r", "-l", "-z", "--full-tree", commit, "--", path)
    if out.returncode != 0:
        raise ProtectedPathsError(f"Could not list {path} at {commit[:12]} in {repo}.")
    entries = {}
    for record in out.stdout.decode("utf-8").split("\0"):
        if record:
            meta, _, rel = record.partition("\t")
            mode, kind, oid, size = meta.split()
            if kind != "blob":
                raise ProtectedPathsError(f"Protected path {rel} is a {kind}, not a file.")
            entries[rel] = (mode, oid, int(size))
    return entries


def _object(repo: Path, oid: str) -> bytes:
    out = git(repo, *_NO_REPLACE, "cat-file", "blob", oid)
    if out.returncode != 0:
        raise ProtectedPathsError(f"Could not read the committed object {oid[:12]} in {repo}.")
    return out.stdout


def load_protected_reference(
    repo: Path, commit: str, branch: str | None
) -> ProtectedReference | None:
    """The protected paths declared at ``commit``, each present there; None if none.

    ``branch`` is the build branch every check holds to the commit.
    """
    from guardkit.orchestrator.harness.selector import _parse_player_project_inputs

    config = _committed(repo, commit, ".guardkit/config.yaml").get(".guardkit/config.yaml")
    if config is None:
        return None
    inputs = _parse_player_project_inputs(
        _object(repo, config[1]).decode("utf-8", "replace"),
        config_path=f".guardkit/config.yaml at {commit[:12]}",
        has_file=lambda _rel: False,
    )
    declared = tuple(posixpath.normpath(p) for p in inputs["protected_paths"])
    # Step 2 (26 October 2026): only what exists is protected. A declared path
    # that is not in the start commit protects nothing; noted, never a stop.
    paths, files = [], []
    for path in declared:
        entries = _committed(repo, commit, path)
        if not entries:
            logger.warning(
                "The project declares the protected path %r, but it is not in the "
                "commit this build started from (%s); it protects nothing.",
                path, commit[:12],
            )
            continue
        paths.append(path)
        files.extend(entries)
    paths = tuple(paths)
    _started_with[str(Path(repo).resolve())] = tuple(sorted(set(files)))
    if paths and not branch:
        raise ProtectedPathsError(
            "The project declares protected paths, but no build branch is known "
            "to keep them on; the task was not started."
        )
    return ProtectedReference(commit, paths, f"refs/heads/{branch}") if paths else None


def protected_files_at_start(repo: Path, declared) -> tuple[str, ...]:
    """The protected files the builder's file tools refuse to change.

    The files under the declared paths at the build's start commit, once
    :func:`load_protected_reference` has read them for this worktree; until
    then, the declared paths themselves.
    """
    files = _started_with.get(str(Path(repo).resolve()))
    return tuple(declared) if files is None else files


def _real_folders(repo: Path, rel: str) -> bool:
    """True when every folder between the worktree and ``rel`` is a real folder."""
    current = repo
    for part in rel.split("/")[:-1]:
        current = current / part
        try:
            if not stat.S_ISDIR(os.lstat(current).st_mode):
                return False
        except OSError:
            return False
    return True


def _same_file(path: Path, info: os.stat_result, oid: str, size: int) -> bool:
    if info.st_size != size:  # never read an unbounded file
        return False
    digest = hashlib.new("sha1" if len(oid) == 40 else "sha256", b"blob %d\0" % size)
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest() == oid


def _differences(repo: Path, root: str, entries: dict) -> list[tuple[str, str]]:
    """What differs under ``root``: ``[(path, what)]``, empty when nothing does."""
    if not _real_folders(repo, root) or not os.path.lexists(repo / root):
        return [(root, "deleted or moved")]
    if root not in entries and not stat.S_ISDIR(os.lstat(repo / root).st_mode):
        return [(root, "replaced")]
    changes = []
    for rel, (mode, oid, size) in sorted(entries.items()):
        path = repo / rel
        try:
            info = os.lstat(path) if _real_folders(repo, rel) else None
            if info is None:
                changes.append((rel, "deleted or moved"))
            elif mode == "120000":
                if not stat.S_ISLNK(info.st_mode):
                    changes.append((rel, "replaced"))
                elif os.fsencode(os.readlink(path)) != _object(repo, oid):
                    changes.append((rel, "edited"))
            elif not stat.S_ISREG(info.st_mode):
                changes.append((rel, "replaced"))
            elif not _same_file(path, info, oid, size):
                changes.append((rel, "edited"))
            elif bool(info.st_mode & 0o111) != (mode == "100755"):
                changes.append((rel, "executable bit changed"))
        except FileNotFoundError:
            changes.append((rel, "deleted"))
        except OSError:
            changes.append((rel, "unreadable"))
    # A file added under a protected folder is the builder's own new work,
    # never a change to a protected file (step 2, 26 October 2026).
    return changes


def _remove(path: Path) -> None:
    if os.path.islink(path) or not path.is_dir():
        os.unlink(path)
        return
    os.chmod(path, 0o700)
    for folder, names, _files in os.walk(path):
        for name in names:
            child = os.path.join(folder, name)
            if not os.path.islink(child):
                os.chmod(child, 0o700)
    shutil.rmtree(path)


def _real_parents(repo: Path, rel: str) -> None:
    """Make every folder above ``rel`` a real folder."""
    current = repo
    for part in rel.split("/")[:-1]:
        current = current / part
        if os.path.lexists(current) and not stat.S_ISDIR(os.lstat(current).st_mode):
            os.unlink(current)
        if not os.path.lexists(current):
            current.mkdir()


def _put_back(repo: Path, root: str, entries: dict) -> None:
    """Put back each file that existed at the start commit; leave new files."""
    if root in entries or (
        os.path.lexists(repo / root) and not stat.S_ISDIR(os.lstat(repo / root).st_mode)
    ):
        _real_parents(repo, root)
        if os.path.lexists(repo / root):
            _remove(repo / root)
    for rel, (mode, oid, _size) in sorted(entries.items()):
        path = repo / rel
        _real_parents(repo, rel)
        if os.path.lexists(path):
            _remove(path)
        data = _object(repo, oid)
        if mode == "120000":
            os.symlink(os.fsdecode(data), path)
            continue
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
        with os.fdopen(os.open(path, flags, 0o600), "wb") as handle:
            handle.write(data)
        os.chmod(path, 0o755 if mode == "100755" else 0o644)


def _index(repo: Path, root: str) -> list[tuple[str, str, str, str, str]]:
    """The index entries under ``root``: ``(path, tag, mode, object id, stage)``."""
    entries = []
    for record in _run(repo, "ls-files", "-s", "-v", "-z", "--", root).decode().split("\0"):
        if record:
            meta, _, path = record.partition("\t")
            tag, mode, oid, stage = meta.split()
            entries.append((path, tag, mode, oid, stage))
    return sorted(entries)


def _wanted_index(entries: dict) -> list[tuple[str, str, str, str, str]]:
    return sorted((p, "H", mode, oid, "0") for p, (mode, oid, _size) in entries.items())


def _index_info(remove: set[str], entries: dict, zero: str) -> bytes:
    """``update-index -z --index-info`` input: drop ``remove``, then add ``entries``."""
    lines = [f"0 {zero}\t{p}" for p in sorted(remove)]
    lines += [f"{mode} {oid}\t{p}" for p, (mode, oid, _size) in sorted(entries.items())]
    return "\0".join(lines).encode() + b"\0"


def _correct_branch(repo: Path, commit: str, roots: list[str], ref: str) -> None:
    """One commit on ``ref`` putting ``roots`` back as they are at ``commit``."""
    old = _run(repo, "rev-parse", "--verify", f"{ref}^{{commit}}").decode().strip()
    zero = "0" * len(old)
    with tempfile.TemporaryDirectory() as folder:
        index = os.path.join(folder, "index")
        _run(repo, "read-tree", old, index=index)
        for root in roots:
            start = _committed(repo, commit, root)
            # Only files that existed at the start; new files stay committed.
            remove = set(_committed(repo, old, root)) & set(start)
            _run(repo, "update-index", "-z", "--index-info", index=index,
                 data=_index_info(remove, start, zero))
        tree = _run(repo, "write-tree", index=index).decode().strip()
    message = "[guardkit] put protected paths back as committed: " + ", ".join(roots)
    new = _run(repo, "commit-tree", tree, "-p", old, "-m", message).decode().strip()
    _run(repo, "update-ref", "-m", message, ref, new, old)  # only if it has not moved


def _hold_index(repo: Path, root: str, entries: dict) -> bool:
    """Put ``root``'s index entries back as committed; True if they differed.

    Staged content, an assume-unchanged / skip-worktree flag, or bytes that
    ``git add`` converted (``text``, ``eol``, ``ident``, an encoding set in an
    attributes file): every entry is dropped and the commit's own blob ids
    and modes go back in, filter-free. Raises when they still differ.
    """
    def existing():
        # A new file staged under a protected folder is the builder's own.
        return [e for e in _index(repo, root) if e[0] in entries]

    index = existing()
    if index == _wanted_index(entries):
        return False
    zero = "0" * len(next(iter(entries.values()))[1])
    _run(repo, "update-index", "-z", "--index-info",
         data=_index_info({e[0] for e in index}, entries, zero))
    if existing() != _wanted_index(entries):
        raise ProtectedPathsError(
            f"Protected path {root} is still different in the git index after "
            "putting it back."
        )
    return True


def _existing(found: dict, start: dict) -> dict:
    """The part of ``found`` that names files existing at the start commit."""
    return {path: value for path, value in found.items() if path in start}


def hold_protected_index(repo: Path, reference: ProtectedReference) -> list[str]:
    """After a checkpoint's ``git add``, before its commit: the index part alone.

    Returns the protected paths whose staged entries had to be put back.
    """
    return [
        root for root in reference.paths
        if _hold_index(Path(repo), root, _committed(Path(repo), reference.commit, root))
    ]


def restore_protected_paths(repo: Path, reference: ProtectedReference) -> str | None:
    """Put every changed protected path back; return a note for the Player and Coach.

    Returns None when nothing changed. Raises ProtectedPathsError when a
    changed path cannot be read or put back exactly.
    """
    repo = Path(repo)
    changes: list[tuple[str, str]] = []
    committed_roots: list[str] = []
    for root in reference.paths:
        entries = _committed(repo, reference.commit, root)
        try:
            found = _differences(repo, root, entries)
            if found:
                _put_back(repo, root, entries)
            still = _differences(repo, root, entries) if found else []
        except OSError as exc:
            raise ProtectedPathsError(
                f"Protected path {root} was changed and could not be put back: {exc}"
            ) from exc
        if _hold_index(repo, root, entries):
            found += [(root, "changed in the git index")]
        if still:
            raise ProtectedPathsError(
                f"Protected path {root} is still different after putting it back: "
                + ", ".join(f"{p} ({w})" for p, w in still[:_MAX_LISTED])
            )
        if _existing(_committed(repo, reference.ref, root), entries) != entries:
            committed_roots.append(root)
            found += [(root, "committed on the branch")]
        changes.extend(found)
    if committed_roots:
        # The build branch itself, whatever HEAD points at now.
        _correct_branch(repo, reference.commit, committed_roots, reference.ref)
        if any(
            _existing(_committed(repo, reference.ref, r), start) != start
            for r in committed_roots
            for start in [_committed(repo, reference.commit, r)]
        ):
            raise ProtectedPathsError(
                "Protected paths committed on the branch are still different after "
                "a corrective commit: " + ", ".join(committed_roots)
            )
    attached = run_git(["-C", str(repo), "symbolic-ref", "-q", "HEAD"], text=False, timeout=60)
    if attached.returncode != 0 or attached.stdout.decode().strip() != reference.ref:
        where = attached.stdout.decode().strip() if attached.returncode == 0 else "detached"
        raise ProtectedPathsError(
            f"The worktree is not on the build branch {reference.ref[len('refs/heads/'):]} "
            f"(HEAD is {where}); protected paths were put back on that branch, and "
            "the task stops because its work is no longer on it."
        )
    if not changes:
        return None
    shown = [f"{p} ({w})" for p, w in changes]
    listed = shown[:_MAX_LISTED]
    if len(shown) > _MAX_LISTED:
        listed.append(f"{len(shown) - _MAX_LISTED} more")
    text = listed[0] if len(listed) == 1 else f"{', '.join(listed[:-1])} and {listed[-1]}"
    return f"Protected paths are read-only; these were found changed: {text}; they were put back."
