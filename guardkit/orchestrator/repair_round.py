"""What a gate-driven repair round tells the plan audit and the Coach.

WHY THIS EXISTS (20 October 2026)
---------------------------------
A gate that runs after a wave (the whole-feature check, the smoke gate, the
wiring gate) can fail after every task in the wave was approved. The feature
orchestrator then re-opens those tasks with the gate's output as the Player's
feedback (``FeatureOrchestrator._execute_wave_parallel``). To make the gate
pass the Player may have to change files the task document never named: the
failing end-to-end test, the scripts and helpers beside it. The plan audit
knew nothing about the round, compared the whole task with the task document,
and refused every repair turn as high, so the task stalled although the
Player was doing what the round asked.

WHAT IT DOES
------------
At the re-open the feature orchestrator makes a :class:`RepairRound` - the
round's number, the commit the round starts from (HEAD at the re-open), the
gate's output, and the non-protected files the reviewer approved in this
task's earlier repair rounds - and hands it, in memory, down the call chain it controls:
``_execute_task`` -> ``AutoBuildOrchestrator`` -> its ``AgentInvoker``. Nothing
is written to disk for it and nothing on disk is read back, so there is
nothing a Player could write to make a turn look like a repair round.

In a repair round the plan audit does not refuse a turn for the number of
extra files the round made. The Coach's prompt for the turn lists every file
the round changed that the task document does not name - read from git since
the round's start, whatever the ordinary audit reports - marks the ones the
gate's output names (:func:`implicated_paths`), says it is a repair round for
the failing check and asks the reviewer to refuse the turn if any of them is
not needed to make that check pass. If that section cannot reach the model
whole, the Coach is not run. A protected file the round made (migration,
Dockerfile, lockfile, .env ...) is still refused by the audit itself. Ordinary turns have no repair round and are
audited exactly as before. A resumed build starts without one, so its turns
are audited as ordinary turns.

Nothing here knows a programming language: a path is a run of characters
with a slash in it, or a bare file name, that matches a file git tracks.
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, FrozenSet, Iterable, List, Optional, Set, Tuple

from guardkit.lib.project_git import run_git

logger = logging.getLogger(__name__)

#: How much of the gate's output the Coach's prompt carries (its end).
GATE_OUTPUT_PROMPT_LIMIT = 6000


@dataclass(frozen=True)
class RepairRound:
    """A round a gate opened again after the task was approved. In memory only.

    ``round_number`` is this round's number: 2 for the first repair round,
    whose approved predecessor's turn files went into ``round-1/`` (see
    ``turn_rounds``); it is for the record and the prompt only. ``start_commit`` is HEAD at the
    re-open: the candidate the gate failed. ``gate_output`` is the feedback the
    Player was given, the gate's own words. ``approved_by_earlier_repairs`` are
    the non-protected files this task's earlier repair rounds showed the
    reviewer on the turns it approved, carried in memory: a later gate's
    re-entry does not count them again. Never a protected file.
    """

    round_number: int
    start_commit: str
    gate_output: str
    approved_by_earlier_repairs: FrozenSet[str] = frozenset()
    #: Every protected path in the worktree as it stood at the re-open -
    #: tracked, untracked or ignored, file or symlink - as path and
    #: fingerprint only (``protected_fingerprints``). Never the contents.
    protected_fingerprints: Tuple[Tuple[str, str], ...] = ()
    #: Why the round's facts could not be established at the re-open, or
    #: ``None`` when they were. A round that is unavailable is still a repair
    #: round: every one of its turns is refused (the unreadable-record
    #: refusal), never audited as an ordinary turn.
    unavailable: Optional[str] = None


class RepairFactsUnavailable(Exception):
    """A repair round's facts could not be established. Every helper that
    establishes them raises this on any error, and the caller refuses the
    turn; no helper returns a stand-in value."""


#: The most implicated paths kept. A gate's output is cut to its last lines
#: already; this is only a bound on a pathological output.
MAX_IMPLICATED_PATHS = 200

# Characters that separate one path from the next in tool output: white
# space, quotes, brackets, commas, and the arrows and bars test runners print.
_SEPARATORS = re.compile(r"[\s\"'`()\[\]{}<>,;|›→»]+")
# A trailing ``:line`` or ``:line:column`` (``spec.ts:124:26``).
_LINE_SUFFIX = re.compile(r"(?::\d+)+$")


def _candidates(text: str) -> Iterable[str]:
    for token in _SEPARATORS.split(text or ""):
        token = token.strip().rstrip(".:")
        token = _LINE_SUFFIX.sub("", token).rstrip(".:")
        if token:
            yield token


def implicated_paths(text: str, tracked: Iterable[str]) -> List[str]:
    """The tracked files ``text`` names, sorted.

    A token with a slash names the tracked file that is its longest trailing
    run of path parts, so an absolute path printed from inside any checkout
    (``/somewhere/checkout/tests/e2e/login.spec.ts:12:3``) names
    ``tests/e2e/login.spec.ts``. A bare file name with an extension
    (``login.spec.ts``) names a file only when exactly one tracked file has
    that name. Anything else names nothing. Pure.
    """
    tracked_set: Set[str] = {str(path) for path in tracked if path}
    by_name: dict = {}
    for path in tracked_set:
        by_name.setdefault(path.rsplit("/", 1)[-1], []).append(path)

    found: Set[str] = set()
    for token in _candidates(text):
        if "/" in token:
            parts = [part for part in token.split("/") if part not in ("", ".")]
            for start in range(len(parts)):
                suffix = "/".join(parts[start:])
                if suffix in tracked_set:
                    found.add(suffix)
                    break
        elif "." in token.strip("."):
            matches = by_name.get(token, [])
            if len(matches) == 1:
                found.add(matches[0])
        if len(found) >= MAX_IMPLICATED_PATHS:
            break
    return sorted(found)


def begin_repair_round(
    worktree_path: Path,
    round_number: Optional[int],
    gate_output: str,
    approved_by_earlier_repairs: Iterable[str] = (),
) -> RepairRound:
    """The repair round a re-open starts. Always a round; never raises.

    Reads HEAD of the worktree, the round's start, and the fingerprint of
    every protected path in it. ``approved_by_earlier_repairs`` are the non-protected files this
    task's earlier repair rounds showed the reviewer on the turns it approved
    (``FeatureOrchestrator._remember_repair_approvals``); never another
    task's files, and never a protected file. If anything cannot be
    established the round is returned with ``unavailable`` set to the reason,
    and every one of its turns is refused.
    """
    number = round_number if isinstance(round_number, int) and round_number > 1 else 2
    approved = frozenset(str(path) for path in approved_by_earlier_repairs if path)
    try:
        head = git_head(worktree_path)
        fingerprints = protected_fingerprints(worktree_path)
    except Exception as exc:  # noqa: BLE001 — becomes an explicit unavailable round
        reason = str(exc) if isinstance(exc, RepairFactsUnavailable) else type(exc).__name__
        logger.warning(
            "The repair round's facts could not be established at the re-open "
            "(%s); every turn of the round will be refused.", reason,
        )
        return RepairRound(
            round_number=number,
            start_commit="",
            gate_output=str(gate_output or ""),
            approved_by_earlier_repairs=approved,
            unavailable=reason,
        )
    return RepairRound(
        round_number=number,
        start_commit=head,
        gate_output=str(gate_output or ""),
        approved_by_earlier_repairs=approved,
        protected_fingerprints=tuple(sorted(fingerprints.items())),
    )


def git_head(worktree_path: Path) -> str:
    """HEAD of the worktree. Raises ``RepairFactsUnavailable`` on any error."""
    try:
        done = run_git(["rev-parse", "HEAD"], cwd=Path(worktree_path), check=False, timeout=30)
    except Exception as exc:  # noqa: BLE001
        raise RepairFactsUnavailable(f"HEAD could not be read ({type(exc).__name__})") from exc
    head = (done.stdout or "").strip() if done.returncode == 0 else ""
    if not head:
        raise RepairFactsUnavailable("HEAD could not be read")
    return head


#: Files the factory itself writes at any depth of a worktree while a turn
#: runs (the checkpoint manager's git lock). Never the Player's work.
_FACTORY_OWNED_NAMES = frozenset({".guardkit-git.lock"})


#: Separates a fingerprint's hash from the protected names it carries.
_NAMES_SEPARATOR = "\x00"
#: The key prefix of a link's own fingerprint (its text and target).
LINK_KEY_PREFIX = "link:"


def fingerprint_names(fingerprint: str) -> List[str]:
    """The protected logical names a fingerprint carries (see
    :func:`protected_files`)."""
    return [name for name in str(fingerprint).split(_NAMES_SEPARATOR)[1:] if name]


def display_key(key: str) -> str:
    """How a fingerprint key is named to a person: its actual repository path."""
    return key[len(LINK_KEY_PREFIX):] if key.startswith(LINK_KEY_PREFIX) else key


def factory_owned_path(path: str, *, folder: bool = False) -> bool:
    """Genuine factory records by actual repository location, never packages.

    Callers supply a stable actual path; resolving a diagnostic alias here
    would make ownership depend on traversal order again.
    """
    parts = path.split("/")
    if parts[-1] in _FACTORY_OWNED_NAMES:
        return True
    if len(parts) >= 2 and parts[-2] == ".guardkit" and parts[-1].startswith(
        "memory-query-log.jsonl"
    ):
        return True
    location = path + "/" if folder else path
    return location.startswith((
        ".guardkit/", "docs/state/", "large_tool_results/",
        ".claude/task-plans/", "conversation_history/",
        "tasks/backlog/", "tasks/design_approved/", "tasks/in_progress/",
        "tasks/in_review/", "tasks/completed/",
    ))


def protected_fingerprints(worktree_path: Path) -> Dict[str, str]:
    """Every protected record in the worktree, as ``{key: fingerprint}``.
    See :func:`protected_files`."""
    return {key: fingerprint for key, (_, fingerprint) in protected_files(worktree_path).items()}


def protected_files(worktree_path: Path) -> Dict[str, Tuple[Tuple[str, ...], str]]:
    """Every protected record in the worktree, as ``{key: (names, fingerprint)}``.

    Files use real repository paths; links use their own entry paths with
    parent directories resolved, never the final link. The hash covers contents
    or type, or link text and resolved target. Logical names are diagnostic
    witnesses, carried after a separator but ignored when comparing records.

    Each real directory is visited once in the initial walk and once across
    all protected roots. Protection propagates through roots, including cycles,
    without enumerating aliases. Pruning depends only on entry names or actual
    locations: package entries are skipped, but an alias into a package can
    expose protected contents. Factory targets are always excluded; a protected
    link outside their namespace still has its own record.

    Outside targets are never walked or opened. Only regular files are opened,
    non-blocking with a type recheck. Unreadable paths and protected dangling
    links make facts unavailable. Contents are hashed, never retained or shown.
    """
    from installer.core.commands.lib.plan_audit import (
        _NEVER_COUNTED_DIRECTORY_NAMES,
        _NEVER_COUNTED_SUFFIXES,
        _is_protected,
    )

    root = Path(worktree_path)
    if not root.is_dir():
        raise RepairFactsUnavailable("the worktree could not be read")
    root_real = os.path.realpath(root)

    def _unreadable(path: str, exc: BaseException) -> RepairFactsUnavailable:
        return RepairFactsUnavailable(
            f"{os.path.basename(path)} could not be read ({type(exc).__name__})"
        )

    def _inside(real: str) -> bool:
        return real == root_real or real.startswith(root_real + os.sep)

    def _identity(path: str) -> Tuple[int, int]:
        try:
            st = os.stat(path)
        except OSError as exc:
            raise _unreadable(path, exc) from exc
        return (st.st_dev, st.st_ino)

    def _listing(real_dir: str) -> List[Tuple[str, str, bool, bool]]:
        """``(name, path, is a link, is a folder that is not a link)``, sorted;
        the two flags come from the folder listing itself."""
        try:
            with os.scandir(real_dir) as entries:
                return sorted(
                    (
                        entry.name,
                        entry.path,
                        entry.is_symlink(),
                        entry.is_dir(follow_symlinks=False),
                    )
                    for entry in entries
                )
        except OSError as exc:
            raise RepairFactsUnavailable(
                f"a folder of the worktree could not be read ({type(exc).__name__})"
            ) from exc

    def _kind(path: str, is_link: bool, plain_dir: bool) -> str:
        if not is_link:
            return "folder" if plain_dir else "file"
        try:
            if not os.path.exists(path):
                return "nowhere"  # a link that leads nowhere
            return "folder" if os.path.isdir(path) else "file"
        except OSError as exc:
            raise _unreadable(path, exc) from exc

    def _real(path: str, is_link: bool) -> str:
        # An entry that is not a link, in a real folder, is its own real path.
        return os.path.realpath(path) if is_link else path

    def _real_relative(path: str, is_link: bool = True) -> Optional[str]:
        real = _real(path, is_link)
        if not _inside(real) or real == root_real:
            return None
        return os.path.relpath(real, root_real).replace(os.sep, "/")

    def _factory_owned(path: str, is_link: bool, folder: bool) -> bool:
        relative = _real_relative(path, is_link)
        return relative is not None and factory_owned_path(relative, folder=folder)

    def _entry_excluded(name: str, folder: bool, path: str) -> bool:
        # The collector's original package/cache exclusions also exclude the
        # entry itself. Never consult a logical ancestor here.
        return (
            _factory_owned(path, False, folder)
            or path == os.path.join(root_real, ".git")
            or (folder and name in _NEVER_COUNTED_DIRECTORY_NAMES)
            or Path(name).suffix in _NEVER_COUNTED_SUFFIXES
        )

    def _package_contents(name: str, folder: bool, path: str) -> bool:
        # These exclusions used to live only in the caller and cover contents,
        # not protected symlink entries. Record such a link before pruning.
        return folder and (
            name in {"site-packages", ".tmp", ".npm"}
            or (os.path.dirname(path) == root_real and (
                name == ".local" or name.startswith(".venv")
            ))
        )

    files: Dict[str, Set[str]] = {}  # actual file path -> diagnostic witnesses
    found: Dict[str, Tuple[Tuple[str, ...], str]] = {}

    def _record_link(path: str, logical: str) -> None:
        """A link at a protected position: its text and resolved target."""
        try:
            link_text = os.readlink(path)
        except OSError as exc:
            raise _unreadable(path, exc) from exc
        digest = hashlib.sha256()
        digest.update(b"symlink:" + os.fsencode(link_text) + b"\0")
        digest.update(b"target:" + os.fsencode(os.path.realpath(path)))
        key = LINK_KEY_PREFIX + str(_real_relative(path, False))
        names = set(found.get(key, ((), ""))[0]) | {logical}
        ordered = tuple(sorted(names))
        found[key] = (
            ordered,
            digest.hexdigest() + _NAMES_SEPARATOR + _NAMES_SEPARATOR.join(ordered),
        )

    def _mark(path: str, logical: str) -> None:
        real = os.path.realpath(path)
        if not _inside(real):
            return  # outside: recorded as a link, never opened
        files.setdefault(real, set()).add(logical)

    # 1. Each real folder once; protected files by their path here; links at
    #    protected positions; roots.
    roots: List[Tuple[str, str]] = []
    seen: Set[Tuple[int, int]] = set()
    stack: List[Tuple[str, str]] = [("", root_real)]
    while stack:
        logical_dir, real_dir = stack.pop()
        identity = _identity(real_dir)
        if identity in seen:
            continue
        seen.add(identity)
        for name, path, is_link, plain_dir in _listing(real_dir):
            logical = f"{logical_dir}/{name}" if logical_dir else name
            kind = _kind(path, is_link, plain_dir)
            folder = kind == "folder"
            if _entry_excluded(name, folder, path):
                continue
            protected_here = _is_protected(logical) or (
                folder and _is_protected(f"{logical}/_")
            )
            if is_link and protected_here:
                _record_link(path, logical)
            if _package_contents(name, folder, path) or _factory_owned(path, is_link, folder):
                continue
            if kind == "nowhere":
                if protected_here:
                    raise RepairFactsUnavailable(f"{name} is a symlink that leads nowhere")
                continue
            if folder:
                if _is_protected(f"{logical}/_"):
                    roots.append((logical, path))
                real = _real(path, is_link)
                if _inside(real):
                    stack.append((logical, real))
                continue
            if _is_protected(logical):
                _mark(path, logical)

    # 2. Everything reachable from a protected folder is protected. One set of
    #    visited folders for all roots: a file reached from any of them is
    #    protected whichever reaches it first.
    reached: Set[Tuple[int, int]] = set()
    for root_logical, root_path in sorted(roots):
        stack = [(root_logical, os.path.realpath(root_path))]
        while stack:
            logical_dir, real_dir = stack.pop()
            if not _inside(real_dir):
                continue  # recorded as a link
            identity = _identity(real_dir)
            if identity in reached:
                continue
            reached.add(identity)
            for name, path, is_link, plain_dir in _listing(real_dir):
                logical = f"{logical_dir}/{name}"
                kind = _kind(path, is_link, plain_dir)
                folder = kind == "folder"
                if _entry_excluded(name, folder, path):
                    continue
                if is_link:
                    _record_link(path, logical)  # every link here is protected
                if _package_contents(name, folder, path) or _factory_owned(path, is_link, folder):
                    continue
                if kind == "nowhere":
                    raise RepairFactsUnavailable(f"{name} is a symlink that leads nowhere")
                if folder:
                    real = _real(path, is_link)
                    if _inside(real):
                        stack.append((logical, real))
                    continue
                _mark(path, logical)

    # 3. Distinct actual paths stay distinct, including hardlinks. Names are
    #    retained for diagnostics only, outside the compared digest.
    for real, names in files.items():
        try:
            contents = _bytes_sha256(Path(real))
        except OSError as exc:
            raise _unreadable(real, exc) from exc
        ordered = tuple(sorted(names))
        digest = hashlib.sha256()
        digest.update(b"real:" + os.fsencode(real) + b"\0")
        digest.update(b"contents:" + contents.encode())
        key = _real_relative(real, False) or real
        found[key] = (ordered, digest.hexdigest() + _NAMES_SEPARATOR + _NAMES_SEPARATOR.join(ordered))
    return found


def _sha256_of(path: Path) -> str:
    """The fingerprint of a file's contents, as a sha256 hex digest.

    For a regular file: the sha256 of its bytes. For a symlink: the link's own
    text, the path the whole chain resolves to, and the sha256 of that
    target's bytes, so a write THROUGH a symlinked ``.env`` (to a file that is
    not protected itself) changes the fingerprint, and so does retargeting
    the link. Raises ``RepairFactsUnavailable`` naming the file when it, or
    a link's target, cannot be read - a dangling link, a loop, a directory or
    a permission error; there is no stand-in value that could compare equal.
    Only hashes are returned; the contents are never kept.
    """
    try:
        if path.is_symlink():
            link_text = os.readlink(path)
            target = path.resolve(strict=True)  # follows the whole chain
            digest = hashlib.sha256()
            digest.update(b"symlink:" + os.fsencode(link_text) + b"\0")
            digest.update(b"target:" + os.fsencode(str(target)) + b"\0")
            digest.update(b"contents:" + _bytes_sha256(target).encode())
            return digest.hexdigest()
        return _bytes_sha256(path)
    except (OSError, RuntimeError) as exc:  # RuntimeError: a symlink loop (older Pythons)
        raise RepairFactsUnavailable(
            f"{path.name} could not be read to hash it ({type(exc).__name__})"
        ) from exc


def _bytes_sha256(path: Path) -> str:
    """The fingerprint of a file's contents without ever blocking.

    Only a regular file is opened and hashed (sha256 of its bytes). Anything
    else - a named pipe, a socket, a device - is fingerprinted by its type
    alone and never opened (``open()`` on a pipe blocks forever), so a change
    of type still counts as a change. The file is opened non-blocking and
    checked again once open, so swapping it for a pipe in between cannot
    block either. Raises ``OSError`` when it cannot be read.
    """
    kind = _special_kind(os.stat(path).st_mode)
    if kind:
        return f"type:{kind}"
    fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
    try:
        kind = _special_kind(os.fstat(fd).st_mode)
        if kind:
            return f"type:{kind}"
        digest = hashlib.sha256()
        with os.fdopen(fd, "rb", closefd=False) as handle:
            for chunk in iter(lambda: handle.read(1 << 20), b""):
                digest.update(chunk)
        return digest.hexdigest()
    finally:
        os.close(fd)


def _special_kind(mode: int) -> str:
    """"" for a regular file, else the kind of file it is."""
    if stat.S_ISREG(mode):
        return ""
    if stat.S_ISFIFO(mode):
        return "fifo"
    if stat.S_ISSOCK(mode):
        return "socket"
    if stat.S_ISCHR(mode):
        return "character-device"
    if stat.S_ISBLK(mode):
        return "block-device"
    if stat.S_ISDIR(mode):
        return "folder"
    return "other"


def protected_fingerprint_changes(
    before: Iterable[Tuple[str, str]], now: Dict[str, str]
) -> Set[str]:
    """The protected paths made, changed or deleted between two complete
    fingerprint listings. Pure."""
    then = dict(before)

    def digest(value: Optional[str]) -> Optional[str]:
        return value.split(_NAMES_SEPARATOR, 1)[0] if value is not None else None

    return {
        path for path in set(then) | set(now)
        if digest(then.get(path)) != digest(now.get(path))
    }
