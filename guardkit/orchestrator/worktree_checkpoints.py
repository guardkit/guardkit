"""Worktree checkpoint and rollback manager for context pollution mitigation.

This module implements a git-based checkpoint/rollback system for AutoBuild worktrees,
addressing the context pollution problem identified in Block AI Research findings.

Architecture:
    - Checkpoint Creation: git commits at turn boundaries
    - Rollback Mechanism: git reset --hard to previous checkpoints
    - Pollution Detection: Analyze test failure patterns across turns
    - Persistence: JSON checkpoint history for audit trail

Design Patterns:
    - CommandExecutor Protocol: Testable git operations (DRY + ISP)
    - Dataclass Pattern: Lightweight checkpoint state containers
    - State Management Pattern: JSON serialization for persistence

Problem:
    The current implementation uses the same worktree across all turns. If turn 1
    creates broken code, turn 2 inherits that state, potentially polluting subsequent
    attempts. Block research emphasizes isolated context windows.

Solution:
    Optional worktree checkpointing that creates git commits at turn boundaries,
    allowing rollback when accumulated state is causing problems.

Example:
    >>> from pathlib import Path
    >>> from guardkit.orchestrator.worktree_checkpoints import WorktreeCheckpointManager
    >>>
    >>> manager = WorktreeCheckpointManager(
    ...     worktree_path=Path(".guardkit/worktrees/TASK-001"),
    ...     task_id="TASK-001",
    ... )
    >>>
    >>> # Create checkpoint after turn completes
    >>> checkpoint = manager.create_checkpoint(turn=1, tests_passed=True)
    >>> print(f"Created checkpoint: {checkpoint.commit_hash[:8]}")
    >>>
    >>> # Detect pollution and rollback if needed
    >>> if manager.should_rollback():
    ...     target_turn = manager.find_last_passing_checkpoint()
    ...     if target_turn:
    ...         manager.rollback_to(target_turn)
"""

import fcntl
import hashlib
import json
import logging
import os
import re
import shutil
import stat
import subprocess
import threading
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import ClassVar, Dict, List, Optional, Protocol, Set, Tuple

from guardkit.lib.project_git import pattern_pathspec, run_git
from guardkit.orchestrator.evidence_repos import EvidenceRepo
from guardkit.orchestrator.head_identity import record_git_operation

logger = logging.getLogger(__name__)

# TASK-AB-XREPOEV01: bound sibling-repo git commits. The commit runs while
# holding a cross-process fcntl lock on the shared sibling repo, so an
# unbounded `git add -A`/`commit` (slow disk, network mount, git hang) would
# deadlock every other task that shares that repo. The worktree checkpoint
# itself keeps its legacy no-timeout behaviour.
_EVIDENCE_GIT_TIMEOUT_S: int = 120


# ============================================================================
# THE JUNK LAW (register 2a5 -> TS-lane D.1c)
# ============================================================================
#
# LAW: build junk is excluded from checkpoints BY PATHSPEC, never by the
# target repo's own ``.gitignore`` hygiene. Register 2a5 (2026-07-30) wrote
# that intent into the add sites' comment and enumerated only the Python
# classes; ``706589f7`` (2026-07-31) then fixed the pathspec MAGIC, not the
# coverage. TS-lane D.1c completes the enumeration for the JavaScript /
# TypeScript classes, and collapses what were two copy-pasted literals into
# ONE constant so the worktree site and the sibling-evidence site can never
# drift apart again (706589f7 had to fix both, separately).
#
# EVERY entry MUST be fully-wildcarded glob magic — ``:(exclude,glob)**/…``.
# This is the 706589f7 lesson and it cuts both ways:
#
#   * the wildcard-FREE form (``:(exclude).cache``) makes git 2.43 REFUSE the
#     whole ``add`` (exit 1, "The following paths are ignored…") the moment
#     the junk it names is ALSO in the repo's own .gitignore and exists on
#     disk — the checkpoint dies after a turn-1 coach approve (FEAT-153C);
#   * the un-magicked ``**`` form (no ``,glob``) excludes NOTHING at all in a
#     repo that does not gitignore the junk — a silent no-op.
#
# Only the fully-wildcarded glob form survives both repo shapes, and the
# regression tests prove each class in both shapes.
#
# ``dist/`` is DELIBERATELY ABSENT (design §B.6, explicitly): it is a real
# deliverable in some repos, and dropping shipped build output by pathspec
# would be silent. This enumeration is also known to rot (``.parcel-cache``,
# ``.svelte-kit``, whatever comes next) — accepted, because the alternative
# is an allowlist of what MAY be committed, which risks dropping real work.
#
# THE TRADE, stated honestly (JX lane). These excludes are GLOBAL: every
# entry is ``**/…``, so a repo that legitimately TRACKS one of these
# directories loses checkpointing for it — silently, until someone reads
# this comment. That is the node_modules precedent, taken deliberately:
# checkpoint excludes exist for MACHINE-MINTED junk, and the junk classes
# below are minted by npm at whatever depth npm feels like. A target repo
# with, say, ``src/fixtures/.tmp/`` fixtures will not see them checkpointed.
# The scope test each entry must pass is the ``dist/`` test: could this
# plausibly be a Player's DELIVERABLE? If yes, it does not go on this list.
CHECKPOINT_EXCLUDE_PATHSPECS: Tuple[str, ...] = (
    # --- register 2a5: machine-local Python/bootstrap junk ---
    ":(exclude,glob)**/.cache/**",
    ":(exclude,glob)**/.guardkit/bootstrap_state.json",
    # --- LI stage-2 (GA2 coach's real drive): the PYTHON junk classes ---
    # The JS/TS classes below were learned from the TypeScript builds; the
    # Python ones were never stated, and a single real work-leg drive of
    # 2026-08-02 committed 223 junk files — bytecode caches beside the Player's
    # edits, plus ``.local/`` where a pip ``--user`` install lands when the run
    # recipe points HOME at the worktree (the same mechanism that mints
    # ``.npm/`` below). All three pass the ``dist/`` test: no Player has ever
    # been asked to deliver a ``__pycache__`` directory or a ``.pyc``.
    ":(exclude,glob)**/__pycache__/**",
    ":(exclude,glob)**/*.pyc",
    ":(exclude,glob)**/.local/**",
    # --- FL lane (the FIRST FLUTTER BUILD's killer, 2026-08-02): the Dart
    # class. ``flutter pub get`` under a worktree-pointed HOME lands the whole
    # pub cache (76M, vendored third-party source) in the tree, and the
    # checkpoint SECRET-SCAN then refuses the commit — flutter_appauth's OAuth
    # sample code pattern-matches "a real secret". Excluding the junk from
    # staging also removes it from the scan's view: the scan judges the staged
    # set, and vendored packages are not the Player's deliverable.
    ":(exclude,glob)**/.pub-cache/**",
    ":(exclude,glob)**/.dart_tool/**",
    # The rest of the HOME-pointed Dart family, learned from the FIRST GREEN
    # Flutter build (FEAT-FLV1, 2026-08-02): its checkpoints carried 3,450
    # files of ``.dartServer/`` analysis cache, the ``.dart-tool/`` telemetry
    # dir (HYPHEN — a different directory from the underscore ``.dart_tool``
    # package cache above), ``.config/flutter/`` and the ``.flutter`` state
    # file — none of them the Player's deliverable; all swept out at the
    # selective merge. ``large_tool_results/`` is the harness's oversized
    # tool-output spool, ledgered on FEAT-STV1 (08-01) and seen AGAIN on
    # FEAT-FLV1 — two builds is a class, not a coincidence.
    ":(exclude,glob)**/.dartServer/**",
    ":(exclude,glob)**/.dart-tool/**",
    ":(exclude,glob)**/.config/flutter/**",
    ":(exclude,glob)**/.flutter",
    ":(exclude,glob)**/.flutter/**",
    ":(exclude,glob)**/large_tool_results/**",
    # The folder's own name too, so a symbolic link of that name (which the
    # ``/**`` form does not match) is not committed with its link text.
    ":(exclude,glob)**/large_tool_results",
    # The coding model's top-level transcript folder, ``conversation_history/``,
    # is deliberately NOT named here: naming it makes git refuse the whole add
    # in a project that ignores the folder while it exists. The unstaging step
    # (:func:`unstage_private_records`) keeps it out of every commit instead.
    # --- TS-lane D.1c: the JS/TS build-junk classes (design §B.6) ---
    ":(exclude,glob)**/node_modules/**",
    ":(exclude,glob)**/.next/**",
    ":(exclude,glob)**/.turbo/**",
    ":(exclude,glob)**/coverage/**",
    ":(exclude,glob)**/*.tsbuildinfo",
    # --- JX lane: npm's caches, minted INSIDE the worktree ---
    # Evidence = the two real TypeScript builds of 2026-07-31/08-01
    # (FEAT-TST1 on ts-api-test). Checkpoint ``ce4f43b`` carried 1365 paths
    # under ``.tmp/`` (node's compile cache), 8 under ``.npm/`` (npm's
    # ``_logs/`` + ``_update-notifier-last-checked``), the orchestrator's
    # own plan stub, and the harness's git lock — 1374 junk paths beside
    # ~10 of real Player work. npm mints these INSIDE the worktree because
    # the run recipe points its HOME/cache there; the target repo's
    # .gitignore (node_modules/dist/coverage/*.tsbuildinfo) knows nothing
    # about them, which is exactly the dependency the junk law removes.
    ":(exclude,glob)**/.tmp/**",
    ":(exclude,glob)**/.npm/**",
    # ``.claude/task-plans/`` ONLY — deliberately NOT ``**/.claude/**``.
    # The plan stub is orchestrator-minted (it is the one ``.claude/`` path
    # the real build actually checkpointed), but ``.claude/`` at large is
    # tracked Player-authorable content across this estate — guardkit's own
    # repo tracks 1606 files under it, and Players author ``.claude/rules/``
    # entries as task deliverables. A blanket exclude would silently drop
    # those edits from every checkpoint of a guardkit self-build: the exact
    # failure mode that keeps ``dist/`` off this list. This anchoring also
    # keeps the constant in step with ``agent_invoker``'s ratified AC-2
    # over-reach guard (``^\.claude/task-plans/``) — with one deliberate
    # depth asymmetry: this pathspec matches at ANY depth, the invoker
    # regex is root-anchored. HONEST RESIDUAL (JX coach, driven on real
    # git): a repo that TRACKS files under ``.claude/task-plans/`` (this
    # one tracks 275) loses checkpointing for edits to them — a
    # ``rollback_to``'s reset reverts such an edit to baseline. Consistent
    # with task-plans being orchestrator-owned; named here so nobody
    # rediscovers it as a surprise.
    ":(exclude,glob)**/.claude/task-plans/**",
    # The harness's own cross-process git lock (gitignored as ``/`` -rooted
    # in guardkit, ungitignored anywhere else — hence pathspec, not hygiene).
    # Carried in the fully-wildcarded form like ``bootstrap_state.json``:
    # a wildcard-free ``:(exclude).guardkit-git.lock`` is the 706589f7
    # refusal bug waiting to happen in the repo that DOES ignore it.
    ":(exclude,glob)**/.guardkit-git.lock",
    # GuardKit's own build records (14 October 2026). Nothing reads any of
    # them back from git; they reach the receipts folder from disk. Committed,
    # they ride into the candidate and a merge publishes them, private paths
    # and all. :func:`unstage_private_records` takes out anything already
    # staged under them, and :data:`FACTORY_RECORD_PATHS` is the one list
    # (Forge keeps a pinned copy: add any new record folder to both).
    #
    # Every per-task and per-feature record: turns, judge feedback, results,
    # the checkpoint list, the baseline, events, and the HEAD record
    # (``head-identity.jsonl``), which a rollback's reset must not rewind.
    ":(exclude,glob)**/.guardkit/autobuild/**",
    # Each record folder's own name as well, here and below: a symbolic link
    # of that name is not matched by the ``/**`` form, and its link text can
    # be a private path.
    ":(exclude,glob)**/.guardkit/autobuild",
    # The shadow judge's queue.
    ":(exclude,glob)**/.guardkit/qav-shadow/**",
    ":(exclude,glob)**/.guardkit/qav-shadow",
    # GuardKit's memory query log and its rotated copy, written relative to
    # the folder a command runs in.
    ":(exclude,glob)**/.guardkit/memory-query-log.jsonl*",
    # GuardKit's inner build folders: each is a git repository, which an add
    # would commit as an embedded-repository link (and the git helper refuses
    # an add that would take one in).
    ":(exclude,glob)**/.guardkit/worktrees/**",
    ":(exclude,glob)**/.guardkit/worktrees",
    # GuardKit's private records (13 October 2026). The final whole-feature
    # check record keeps the last 40 lines of the project's check output,
    # which can carry a credential; a project whose ignore file does not
    # cover this folder would otherwise have it
    # committed and carried towards a public history. This stops ``git add``
    # picking new files up there; :func:`unstage_private_records` is what
    # guarantees the commit, because anything ALREADY staged survives an
    # excluding ``git add``.
    ":(exclude,glob)**/.guardkit/autobuild-private/**",
    ":(exclude,glob)**/.guardkit/autobuild-private",
)
# Marked as patterns on purpose, so the factory's git helper runs the add
# without ``--literal-pathspecs`` (every other file name it treats literally).
CHECKPOINT_EXCLUDE_PATHSPECS = tuple(
    pattern_pathspec(spec) for spec in CHECKPOINT_EXCLUDE_PATHSPECS
)

# The full ``git add`` argv prefix shared by both add sites.
_CHECKPOINT_ADD_ARGV: Tuple[str, ...] = (
    "git",
    "add",
    "-A",
    "--",
    ".",
) + CHECKPOINT_EXCLUDE_PATHSPECS


# ============================================================================
# GuardKit's records never enter a factory commit (13 and 14 October 2026)
# ============================================================================

#: The paths GuardKit and the coding model write records to inside a build's
#: folder, as git globs relative to the repository's top. None of them is
#: read back from git; the records reach the receipts folder from disk.
#: Forge keeps a literal copy of this list (it does not import GuardKit) and a
#: test in each repository pins it: a new record folder goes into both.
#: Paths 1 to 6 and 8 are also left out of ``git add``
#: (:data:`CHECKPOINT_EXCLUDE_PATHSPECS`); path 7 never is, because git
#: refuses the add in a project that ignores that folder while it exists.
FACTORY_RECORD_PATHS: Tuple[str, ...] = (
    "**/.guardkit/autobuild/**",
    "**/.guardkit/autobuild-private/**",
    "**/.guardkit/qav-shadow/**",
    "**/.guardkit/memory-query-log.jsonl*",
    "**/.guardkit/worktrees/**",
    "**/.guardkit/bootstrap_state.json",
    "conversation_history/**",
    "**/large_tool_results/**",
)

def _with_folder_names(paths: Tuple[str, ...]) -> Tuple[str, ...]:
    """Each path, then the bare name of each folder path (``x/**`` gives
    ``x``), which is what matches a symbolic link of that name."""
    return tuple(paths) + tuple(p[:-3] for p in paths if p.endswith("/**"))


#: GuardKit's own records (paths 1 to 6, and the record folders' own names),
#: as pathspecs for the git helper.
FACTORY_RECORD_PATHSPECS: Tuple[str, ...] = tuple(
    pattern_pathspec(f":(glob){path}")
    for path in _with_folder_names(FACTORY_RECORD_PATHS[:6])
)

#: The coding model's own working files (paths 7 and 8, 14 October 2026):
#: summarised conversation transcripts at the worktree root (where the
#: model's libraries write them; a product's own ``src/conversation_history/``
#: is left alone), and oversized tool output at any depth.
MODEL_ARTIFACT_PATHSPECS: Tuple[str, ...] = tuple(
    pattern_pathspec(f":(glob){path}")
    for path in _with_folder_names(FACTORY_RECORD_PATHS[6:])
)

#: Where record CONTENT is looked for, to catch an exact copy of a record
#: that was never committed: every record path except the inner build
#: folders, which hold copies of the product itself.
_RECORD_CONTENT_PATHSPECS: Tuple[str, ...] = tuple(
    pattern_pathspec(f":(glob){path}")
    for path in FACTORY_RECORD_PATHS
    if path != "**/.guardkit/worktrees/**"
)

_RECORD_FOLDERS = frozenset({"autobuild", "autobuild-private", "qav-shadow", "worktrees"})


def is_factory_record(path: str) -> bool:
    """Whether a path git printed is one of :data:`FACTORY_RECORD_PATHS`.

    The same answer as git's own glob matching of those paths and of the
    record folders' own names (a test pins the two together), for paths git
    has already printed, relative to the repository's top, separated by
    ``/``. A folder's own name counts, so a symbolic link of that name is a
    record too.
    """
    parts = path.split("/")
    if parts[0] == "conversation_history":
        return True
    for index, part in enumerate(parts):
        if part == "large_tool_results":
            return True
        if part != ".guardkit" or index + 1 >= len(parts):
            continue
        name, below = parts[index + 1], len(parts) - index - 2
        if name in _RECORD_FOLDERS:
            return True
        if below == 0 and (
            name == "bootstrap_state.json"
            or name.startswith("memory-query-log.jsonl")
        ):
            return True
    return False


#: ``(repository, path)`` pairs already warned about in this process, so an
#: older tracked copy is reported once rather than at every checkpoint.
_warned_tracked_private_records: Set[Tuple[str, str]] = set()
_warned_tracked_private_records_lock = threading.Lock()

#: The id of the empty blob, for SHA-1 and SHA-256 repositories.
_EMPTY_BLOB_IDS = frozenset({
    "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391",
    "473a0f4c3be8a93681a267e3b1e9a7dcda1185436fe141f7749120a303721813",
})

#: How many file names one ``git reset`` is given at a time.
_RESET_BATCH = 200


def _git_listing(
    git_executor: "GitCommandExecutor",
    argv: List[str],
    cwd: Path,
    timeout: Optional[int],
) -> List[str]:
    """Run a ``-z`` listing; raise ``CalledProcessError`` when git fails."""
    return [p for p in _git_fields(git_executor, argv, cwd, timeout) if p.strip()]


def _git_fields(
    git_executor: "GitCommandExecutor",
    argv: List[str],
    cwd: Path,
    timeout: Optional[int],
) -> List[str]:
    """Every NUL-separated field of a ``-z`` listing, empty names kept in
    place so status-and-path pairs stay aligned. Raises
    ``CalledProcessError`` when git fails."""
    done = git_executor.execute(
        # The executable is written here literally (the launch guard).
        ["git", *argv[1:]], cwd=cwd, check=False, timeout=timeout
    )
    if done.returncode != 0:
        raise subprocess.CalledProcessError(
            done.returncode, argv, done.stdout, done.stderr
        )
    fields = (done.stdout or "").split("\0")
    if fields and fields[-1] == "":
        fields.pop()
    return fields


def _unstage(
    git_executor: "GitCommandExecutor",
    cwd: Path,
    specs: List[str],
    timeout: Optional[int],
) -> None:
    """``git reset -q -- <specs>``; raise ``CalledProcessError`` on failure."""
    for start in range(0, len(specs), _RESET_BATCH):
        reset_argv = ["git", "reset", "-q", "--", *specs[start:start + _RESET_BATCH]]
        reset = git_executor.execute(
            # The executable is written here literally (the launch guard).
            ["git", *reset_argv[1:]], cwd=cwd, check=False, timeout=timeout
        )
        if reset.returncode != 0:
            raise subprocess.CalledProcessError(
                reset.returncode, reset_argv, reset.stdout, reset.stderr
            )


def _shown(paths: List[str]) -> str:
    shown = ", ".join(paths[:5])
    if len(paths) > 5:
        shown += f" and {len(paths) - 5} more"
    return shown


def _leave_out_record_moves(
    git_executor: "GitCommandExecutor",
    cwd: Path,
    *,
    timeout: Optional[int] = None,
) -> List[str]:
    """Unstage every staged move or copy of a record to an ordinary path.

    Runs before anything restores a record's index entry: once the source is
    put back to ``HEAD``'s copy, the outside file looks like a new file
    copied from an unchanged one. ``--find-copies-harder`` is what sees a
    plain move on disk (the add never stages the source's deletion, so git
    sees a copy), and ``-l0`` stops git skipping the comparison quietly on a
    large change. ``--raw`` gives the same pairs with their blob ids: git
    pairs empty files with each other, so a destination that is the empty
    blob (a new ``__init__.py`` beside an empty tracked record) is never
    taken for a copy. Files on disk are kept. Returns the paths it unstaged.
    """
    fields = _git_fields(
        git_executor,
        ["git", "diff", "--cached", "--raw", "-z", "--no-abbrev", "-M", "-C",
         "--find-copies-harder", "-l0"],
        cwd, timeout,
    )
    destinations: List[str] = []
    index = 0
    while index < len(fields):
        meta = fields[index].split()
        status = meta[-1] if meta else ""
        if status[:1] in ("R", "C") and index + 2 < len(fields):
            source, destination = fields[index + 1], fields[index + 2]
            if (
                is_factory_record(source)
                and not is_factory_record(destination)
                and meta[3] not in _EMPTY_BLOB_IDS
            ):
                destinations.append(destination)
            index += 3
        else:
            index += 2
    if not destinations:
        return []
    # Literal names: the git helper treats names literally unless marked.
    _unstage(git_executor, cwd, destinations, timeout)
    logger.warning(
        "Left %d file(s) out of the commit in %s: they are moves or copies of "
        "GuardKit's own records (first: %s), which can hold private paths. They "
        "stay on disk and are never committed.",
        len(destinations),
        Path(cwd).resolve(),
        destinations[0],
    )
    return destinations


def _staged_outside_records(
    git_executor: "GitCommandExecutor",
    cwd: Path,
    timeout: Optional[int],
) -> List[Tuple[str, str]]:
    """``(blob id, path)`` for every file content staged as added, changed or
    retyped outside the record paths (embedded-repository links left out)."""
    fields = _git_fields(
        git_executor,
        ["git", "diff", "--cached", "--raw", "-z", "--no-abbrev", "--no-renames",
         "--diff-filter=AMT"],
        cwd, timeout,
    )
    staged: List[Tuple[str, str]] = []
    for index in range(0, len(fields) - 1, 2):
        meta, path = fields[index].split(), fields[index + 1]
        if len(meta) < 4 or meta[1] == "160000" or is_factory_record(path):
            continue
        staged.append((meta[3], path))
    return staged


#: An inner build folder's own record folders, relative to that folder. Only
#: these are read inside it: its product files are never compared.
_INNER_RECORD_FOLDERS: Tuple[str, ...] = (
    ".guardkit/autobuild",
    ".guardkit/autobuild-private",
    ".guardkit/qav-shadow",
    "conversation_history",
    "large_tool_results",
)


def git_blob_id(data: bytes, object_format: str) -> str:
    """The id git gives a file holding exactly ``data``: the ``sha1`` or
    ``sha256`` digest of ``b"blob <length>\\0"`` followed by the bytes, as
    lower-case hex. No line-ending or filter conversion is applied."""
    digest = hashlib.new(object_format)
    digest.update(b"blob %d\0" % len(data))
    digest.update(data)
    return digest.hexdigest()


def _object_format(
    git_executor: "GitCommandExecutor", cwd: Path, timeout: Optional[int]
) -> str:
    """``sha1`` or ``sha256``, as the repository says."""
    argv = ["git", "rev-parse", "--show-object-format"]
    done = git_executor.execute(
        # The executable is written here literally (the launch guard).
        ["git", *argv[1:]], cwd=cwd, check=False, timeout=timeout
    )
    found = (done.stdout or "").strip()
    if done.returncode != 0 or found not in ("sha1", "sha256"):
        raise subprocess.CalledProcessError(
            done.returncode or 1, argv, done.stdout, done.stderr
        )
    return found


def _read_regular_file(path: Path) -> Optional[bytes]:
    """A regular file's bytes, or ``None`` when it is gone, unreadable, empty
    or not a regular file (a link is never followed). GuardKit replaces
    records by renaming a temporary file over them while other tasks run, so
    a file listed a moment ago may be gone: that is never an error."""
    flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
    try:
        handle = os.open(path, flags)
    except OSError:
        return None
    try:
        if not stat.S_ISREG(os.fstat(handle).st_mode):
            return None
        chunks: List[bytes] = []
        while True:
            chunk = os.read(handle, 1 << 20)
            if not chunk:
                break
            chunks.append(chunk)
    except OSError:
        return None
    finally:
        os.close(handle)
    return b"".join(chunks) or None


def _inner_build_record_files(root: Path) -> List[Path]:
    """The record files of each inner build folder under
    ``.guardkit/worktrees/``, found by walking the record folders only and
    never following a link. git's own listing stops at an inner build
    folder, because each is a repository of its own."""
    worktrees = root / ".guardkit" / "worktrees"
    if any(p.is_symlink() for p in (root / ".guardkit", worktrees)):
        return []
    try:
        inner_folders = [e for e in os.scandir(worktrees) if e.is_dir(follow_symlinks=False)]
    except OSError:
        return []
    found: List[Path] = []
    for entry in inner_folders:
        inner = Path(entry.path)
        guardkit = inner / ".guardkit"
        if guardkit.is_symlink():
            continue
        for relative in _INNER_RECORD_FOLDERS:
            top = inner / relative
            if top.is_symlink() or not top.is_dir():
                continue
            for folder, _subfolders, names in os.walk(top):
                found.extend(Path(folder) / name for name in names)
        try:
            names = [e.name for e in os.scandir(guardkit) if e.is_file(follow_symlinks=False)]
        except OSError:
            continue
        found.extend(
            guardkit / name for name in names
            if name == "bootstrap_state.json" or name.startswith("memory-query-log.jsonl")
        )
    return found


#: How long the checkpoint waits for record files to be read. A read on a
#: stalled filesystem (a hung network mount, a FIFO with no peer) cannot be
#: interrupted, and a turn must never block on evidence I/O.
_RECORD_READ_BOUND_S = 5.0


def _record_blob_ids(
    git_executor: "GitCommandExecutor",
    cwd: Path,
    timeout: Optional[int],
) -> Set[str]:
    """The blob id of every non-empty regular file on disk at a record path,
    tracked, untracked or ignored alike, and of each inner build folder's own
    records. Ids are computed here from the bytes (:func:`git_blob_id`), so a
    record replaced while this runs is skipped, never an error.

    The files are read in a worker thread that the checkpoint waits for at
    most :data:`_RECORD_READ_BOUND_S`. Files not read by then are left out of
    the comparison, with one warning; the thread is left behind.
    """
    listed = _git_listing(
        git_executor,
        ["git", "ls-files", "-z", "--cached", "--others", "--",
         *_RECORD_CONTENT_PATHSPECS],
        cwd, timeout,
    )
    object_format = _object_format(git_executor, cwd, timeout)
    root = Path(cwd)
    ids: Set[str] = set()
    progress = {"listed": 0, "read": 0, "finished": False}
    lock = threading.Lock()

    def _read_all() -> None:
        paths = {root / p for p in listed if not p.endswith("/")}
        paths.update(_inner_build_record_files(root))
        with lock:
            progress["listed"] = len(paths)
        for path in sorted(paths):
            data = _read_regular_file(path)
            with lock:
                if data is not None:
                    ids.add(git_blob_id(data, object_format))
                progress["read"] += 1
        with lock:
            progress["finished"] = True

    worker = threading.Thread(
        target=_read_all, name="guardkit-checkpoint: reading records", daemon=True
    )
    worker.start()
    worker.join(timeout=_RECORD_READ_BOUND_S)
    with lock:
        found = set(ids)
        finished = progress["finished"]
        unread = progress["listed"] - progress["read"]
    if not finished:
        logger.warning(
            "Reading GuardKit's record files in %s did not finish within %.0fs "
            "(%s not read); exact copies of those were not looked for in this "
            "commit.",
            root.resolve(),
            _RECORD_READ_BOUND_S,
            f"{unread} file(s)" if unread > 0 else "the folders could not be listed",
        )
    return found


def _leave_out_record_copies(
    git_executor: "GitCommandExecutor",
    cwd: Path,
    *,
    timeout: Optional[int] = None,
) -> List[str]:
    """Unstage every staged file outside the record paths whose content is
    byte for byte that of a record file on disk.

    Records are never committed, so git's copy detection, which only looks at
    files ``HEAD`` or the index holds, cannot see an exact copy of one. Empty
    files are never compared. Files on disk are kept. Returns the paths it
    unstaged.
    """
    staged = _staged_outside_records(git_executor, cwd, timeout)
    if not staged:
        return []
    record_ids = _record_blob_ids(git_executor, cwd, timeout)
    copies = [path for blob, path in staged if blob in record_ids]
    if not copies:
        return []
    # Literal names: the git helper treats names literally unless marked.
    _unstage(git_executor, cwd, copies, timeout)
    logger.warning(
        "Left %d file(s) out of the commit in %s: they are moves or copies of "
        "GuardKit's own records (first: %s), which can hold private paths. They "
        "stay on disk and are never committed.",
        len(copies),
        Path(cwd).resolve(),
        copies[0],
    )
    return copies


def _leave_out_model_artifacts(
    git_executor: "GitCommandExecutor",
    cwd: Path,
    *,
    timeout: Optional[int] = None,
) -> List[str]:
    """Keep the coding model's working files out of the next commit.

    ``git add`` already excludes ``large_tool_results/``; the top-level
    ``conversation_history/`` is staged by the add and taken out here. This
    unstages both, and warns when any such file is in the working tree at
    all, staged or not (unless the repository ignores it). Files on disk are
    kept. Returns the paths it unstaged.
    """
    staged = _git_listing(
        git_executor,
        ["git", "diff", "--cached", "--name-only", "-z", "--",
         *MODEL_ARTIFACT_PATHSPECS],
        cwd, timeout,
    )
    if staged:
        _unstage(git_executor, cwd, list(MODEL_ARTIFACT_PATHSPECS), timeout)
    present = sorted(set(staged) | set(_git_listing(
        git_executor,
        ["git", "ls-files", "-z", "--others", "--modified", "--exclude-standard",
         "--", *MODEL_ARTIFACT_PATHSPECS],
        cwd, timeout,
    )))
    if present:
        logger.warning(
            "Left %d file(s) out of the commit in %s: the coding model's own "
            "conversation transcripts or large tool output, which can quote "
            "private paths. They stay on disk and are never committed: %s",
            len(present),
            Path(cwd).resolve(),
            _shown(present),
        )
    return staged


def unstage_private_records(
    git_executor: "GitCommandExecutor",
    cwd: Path,
    *,
    timeout: Optional[int] = None,
) -> List[str]:
    """Take every one of the factory's records out of the index before a commit.

    Called at each of GuardKit's three commit sites, after their ``git add``
    and before ``git commit``. Excluding the folders from ``git add`` is not
    enough: an entry that is already staged (by a Player, a tool or an earlier
    run) still goes into the next commit. So this, in order:

    1. finds every staged move or copy whose source is a record path and whose
       destination is not, and unstages the destination
       (:func:`_leave_out_record_moves`). It runs first, before any step
       below puts a record's index entry back to ``HEAD``. Then any staged
       file outside the record paths whose content is exactly that of a
       record file on disk, committed or not, is unstaged too
       (:func:`_leave_out_record_copies`);
    2. keeps the coding model's own working files (``conversation_history/``
       at the root, ``large_tool_results/`` at any depth) out of the commit,
       and warns when any are present (:func:`_leave_out_model_artifacts`);
    3. lists what is staged under :data:`FACTORY_RECORD_PATHSPECS` and
       unstages it with ``git reset -q -- <pathspecs>``. Files on disk are
       kept. A new file leaves the index, with a warning; a tracked file's
       index entry goes back to ``HEAD``'s copy, so its change is not
       committed;
    4. for each record ``HEAD`` already tracks that was staged or is changed
       on disk, warns once per process that an older copy is tracked here,
       that its committed content is left as it is, and that new content is
       not committed.

    It does not remove records a repository already tracks, and it does not
    rewrite history.

    Returns the paths it unstaged.

    Raises ``subprocess.CalledProcessError`` when a listing or the unstaging
    fails, so the caller's commit does not go ahead with a record still
    staged: each caller already treats a failed git step as a failed commit.
    """
    moved = _leave_out_record_moves(git_executor, cwd, timeout=timeout)
    moved += _leave_out_record_copies(git_executor, cwd, timeout=timeout)
    model_artifacts = _leave_out_model_artifacts(git_executor, cwd, timeout=timeout)
    fields = _git_fields(
        git_executor,
        ["git", "diff", "--cached", "--name-status", "--no-renames", "-z", "--",
         *FACTORY_RECORD_PATHSPECS],
        cwd, timeout,
    )
    staged = [(fields[i], fields[i + 1]) for i in range(0, len(fields) - 1, 2)]
    paths = [path for _, path in staged]
    if paths:
        _unstage(git_executor, cwd, list(FACTORY_RECORD_PATHSPECS), timeout)

    repository = str(Path(cwd).resolve())
    added = [path for status, path in staged if status.startswith("A")]
    if added:
        logger.warning(
            "Left %d file(s) out of the commit in %s: GuardKit's own build "
            "records, which can hold private paths, had been staged. They stay "
            "on disk and are never committed: %s",
            len(added),
            repository,
            _shown(added),
        )

    # Every record HEAD tracks that was staged or is changed on disk. After
    # the reset above the index holds HEAD's copy of each, so ``--modified``
    # lists only records HEAD tracks.
    tracked = [path for status, path in staged if not status.startswith("A")]
    tracked += _git_listing(
        git_executor,
        ["git", "ls-files", "-z", "--modified", "--", *FACTORY_RECORD_PATHSPECS],
        cwd, timeout,
    )
    for path in sorted(set(tracked)):
        key = (repository, path)
        with _warned_tracked_private_records_lock:
            if key in _warned_tracked_private_records:
                continue
            _warned_tracked_private_records.add(key)
        logger.warning(
            "An older copy of GuardKit's record %s is tracked in the "
            "repository at %s. Its committed content is left as it is; new "
            "content in it is not committed.",
            path,
            repository,
        )
    return moved + model_artifacts + paths


# ============================================================================
# Protocols & ABC
# ============================================================================


class GitCommandExecutor(Protocol):
    """Protocol for git command execution (DRY + ISP from architectural review).

    This protocol enables dependency injection and testability by abstracting
    git operations behind an interface.

    Methods:
        execute: Execute a git command and return output
    """

    def execute(
        self,
        command: List[str],
        cwd: Path,
        check: bool = True,
        timeout: Optional[int] = None,
    ) -> subprocess.CompletedProcess:
        """Execute git command with error handling.

        Args:
            command: Git command as list (e.g., ["git", "add", "-A"])
            cwd: Working directory for command execution
            check: Whether to raise on non-zero exit code
            timeout: Optional seconds before the subprocess is killed. None
                means no timeout (legacy worktree behaviour). Set for
                sibling-repo commits, which hold a cross-process fcntl lock
                and must not be able to deadlock the turn (TASK-AB-XREPOEV01).

        Returns:
            CompletedProcess with stdout/stderr

        Raises:
            subprocess.CalledProcessError: If check=True and command fails
            subprocess.TimeoutExpired: If timeout is set and exceeded
        """
        ...


# ============================================================================
# Data Models
# ============================================================================


def format_test_status(tests_passed: Optional[bool]) -> str:
    """Render a tri-state checkpoint test signal for logs and commit messages.

    ``True`` → ``"pass"`` (a test oracle ran and passed), ``False`` →
    ``"fail"`` (ran and failed), ``None`` → ``"unknown"`` (no test oracle
    produced a verdict for this turn).

    Rendering ``None`` as ``"unknown"`` rather than ``"fail"`` is the
    checkpoint-layer instance of the absence-of-failure rule
    (TASK-FIX-CKPTTESTRED01): an *absent* self-reported / gate test signal
    must not read as a *negative* one. See
    ``.claude/rules/absence-of-failure-is-not-success.md``.
    """
    if tests_passed is None:
        return "unknown"
    return "pass" if tests_passed else "fail"


@dataclass
class Checkpoint:
    """Immutable checkpoint record for a worktree state.

    This dataclass captures a snapshot of worktree state at turn completion,
    including git commit hash for rollback and test status for pollution detection.

    Attributes:
        turn: Turn number (1-indexed)
        commit_hash: Git commit SHA for rollback
        timestamp: ISO 8601 timestamp when checkpoint created
        tests_passed: Tri-state test signal for this checkpoint —
            ``True`` (a test oracle ran and passed), ``False`` (ran and
            failed), or ``None`` (UNKNOWN: no test oracle produced a verdict
            this turn, e.g. the LLM Coach report carried no quality-gate
            result). ``None`` is excluded from the consecutive-failure
            pollution tally in ``should_rollback`` — it is *absent* evidence,
            not a failure (TASK-FIX-CKPTTESTRED01). See
            ``.claude/rules/absence-of-failure-is-not-success.md``.
        test_count: Number of tests run (0 if no tests)
        message: Checkpoint commit message
        from_prior_run: True if this checkpoint was loaded from a prior
            orchestration session's ``checkpoints.json`` (e.g. on ``[R]esume``).
            Such checkpoints are preserved for forensic inspection but do not
            count toward the consecutive-failures threshold in
            ``should_rollback()``. Always False for checkpoints written by the
            current run. Defaults to False so old JSON files without this
            field deserialise correctly (TASK-FIX-F4A3).
    """

    turn: int
    commit_hash: str
    timestamp: str
    tests_passed: Optional[bool]
    test_count: int = 0
    message: str = ""
    from_prior_run: bool = False
    # TASK-AB-XREPOEV01: per-declared-sibling-repo checkpoint commit hashes,
    # keyed by repo name (e.g. {"guardkitfactory": "<sha>"}). Empty for
    # worktree-only checkpoints and for checkpoints written before evidence
    # support existed -- the default keeps old checkpoints.json deserialising
    # via ``Checkpoint(**data)``.
    evidence_commits: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization.

        Returns:
            JSON-serializable dictionary
        """
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> "Checkpoint":
        """Create Checkpoint from dictionary.

        Args:
            data: Dictionary with checkpoint fields

        Returns:
            Checkpoint instance
        """
        return cls(**data)


class CheckpointRefused(RuntimeError):
    """The worktree's HEAD is not on the feature branch, so no checkpoint.

    Raised by :meth:`WorktreeCheckpointManager.create_checkpoint` when HEAD is
    detached somewhere other than the branch's tip, or attached to another
    branch. A commit there would never reach the candidate branch (build
    0D7C, 12 October 2026). The message names the expected branch, the actual
    HEAD and the branch tip; the task stops with it.
    """

    def __init__(
        self,
        reason: str,
        *,
        expected_branch: str,
        actual_ref: Optional[str],
        head: str,
        branch_tip: Optional[str],
    ) -> None:
        super().__init__(reason)
        self.expected_branch = expected_branch
        self.actual_ref = actual_ref
        self.head = head
        self.branch_tip = branch_tip


# ============================================================================
# Git Command Executor
# ============================================================================


class SubprocessGitExecutor:
    """Production git command executor using subprocess.

    This implementation provides the real git execution for production use,
    while the Protocol enables test mocking.
    """

    def execute(
        self,
        command: List[str],
        cwd: Path,
        check: bool = True,
        timeout: Optional[int] = None,
    ) -> subprocess.CompletedProcess:
        """Execute git command with subprocess.

        Args:
            command: Git command as list
            cwd: Working directory
            check: Raise on non-zero exit
            timeout: Optional seconds before the subprocess is killed
                (None = no timeout, legacy behaviour).

        Returns:
            CompletedProcess with stdout/stderr

        Raises:
            subprocess.CalledProcessError: If check=True and command fails
            subprocess.TimeoutExpired: If timeout is set and exceeded
        """
        try:
            return run_git(command, cwd=cwd, check=check, timeout=timeout)
        except subprocess.CalledProcessError as e:
            # The helper's own sentence; git's text and output are not logged.
            logger.error(
                f"Git command failed: {' '.join(str(c) for c in command)}\n"
                f"Exit code: {e.returncode}\n"
                f"Stderr: {e.stderr}"
            )
            raise


# ============================================================================
# Checkpoint Manager
# ============================================================================


class WorktreeCheckpointManager:
    """Manages git-based checkpoints for worktree rollback.

    This class implements the checkpoint/rollback mechanism for AutoBuild worktrees,
    providing context pollution mitigation through git state snapshots.

    Architecture:
        - Checkpoints: Git commits at turn boundaries
        - Rollback: git reset --hard to previous commit
        - Detection: Analyze test failure patterns
        - Persistence: JSON file for checkpoint history
        - Concurrency: File-based locking for shared worktrees

    When multiple tasks share a worktree (feature mode), git operations in
    create_checkpoint() are serialized using a file-based lock to prevent
    index.lock conflicts.

    Attributes:
        worktree_path: Path to git worktree
        task_id: Task identifier
        checkpoints: List of checkpoint records
        git_executor: Git command executor (injectable for testing)

    Example:
        >>> manager = WorktreeCheckpointManager(
        ...     worktree_path=Path(".guardkit/worktrees/TASK-001"),
        ...     task_id="TASK-001",
        ... )
        >>>
        >>> # After each turn:
        >>> checkpoint = manager.create_checkpoint(
        ...     turn=1,
        ...     tests_passed=True,
        ...     test_count=15,
        ... )
        >>>
        >>> # Check for pollution and rollback if needed:
        >>> if manager.should_rollback():
        ...     target = manager.find_last_passing_checkpoint()
        ...     if target:
        ...         manager.rollback_to(target)
    """

    # Class-level thread locks keyed by resolved worktree path.
    # Ensures threads coordinate before acquiring the file lock.
    _thread_locks: ClassVar[Dict[str, threading.Lock]] = {}
    _thread_locks_guard: ClassVar[threading.Lock] = threading.Lock()

    def __init__(
        self,
        worktree_path: Path,
        task_id: str,
        git_executor: Optional[GitCommandExecutor] = None,
        evidence_repos: Optional[List[EvidenceRepo]] = None,
        expected_branch: Optional[str] = None,
        refuse_without_branch: bool = False,
    ):
        """Initialize WorktreeCheckpointManager.

        Args:
            worktree_path: Path to git worktree
            task_id: Task identifier
            git_executor: Optional git executor (default: SubprocessGitExecutor)
            evidence_repos: Optional declared sibling repos
                (TASK-AB-XREPOEV01). When provided, every checkpoint also
                commits each repo's working tree so approved sibling-repo work
                is versioned (closes the BDDW-002 hazard: approved factory
                work that was never committed anywhere, one ``git clean`` from
                breaking merged main). Default None -> worktree-only
                checkpoints, unchanged behaviour.
            expected_branch: The feature branch every checkpoint must land
                on (short name, e.g. ``autobuild/FEAT-X``). When given, each
                checkpoint first checks HEAD is on it (see
                :meth:`_keep_head_on_expected_branch`). Default None -> no
                check, unchanged behaviour.
            refuse_without_branch: With no ``expected_branch``, refuse every
                checkpoint instead of committing unchecked. The orchestrator
                sets it: a build whose branch could not be determined at its
                start must not commit wherever HEAD happens to be.
        """
        self.worktree_path = Path(worktree_path)
        self.task_id = task_id
        self.expected_branch = expected_branch
        self.refuse_without_branch = refuse_without_branch
        self.git_executor = git_executor or SubprocessGitExecutor()
        self.evidence_repos: List[EvidenceRepo] = list(evidence_repos or [])
        self.checkpoints: List[Checkpoint] = []

        # Checkpoint persistence path
        self._autobuild_dir = (
            self.worktree_path / ".guardkit" / "autobuild" / task_id
        )
        self._checkpoints_file = self._autobuild_dir / "checkpoints.json"

        # Git lock file path for serializing git operations across tasks
        self._git_lock_path = self.worktree_path / ".guardkit-git.lock"

        # Load existing checkpoints if available
        self._load_checkpoints()

    def create_checkpoint(
        self,
        turn: int,
        tests_passed: Optional[bool],
        test_count: int = 0,
    ) -> Checkpoint:
        """Create a checkpoint commit at current worktree state.

        This method stages all changes and creates a git commit with a
        standardized checkpoint message. The commit serves as a rollback point.

        Git operations (add, commit, rev-parse) are serialized using a
        file-based lock to prevent index.lock conflicts when multiple tasks
        share the same worktree in feature mode.

        Args:
            turn: Turn number (1-indexed)
            tests_passed: Tri-state test signal — ``True`` (ran and passed),
                ``False`` (ran and failed), or ``None`` (UNKNOWN: no test
                oracle verdict for this turn). ``None`` is NOT a failure for
                pollution-detection purposes (TASK-FIX-CKPTTESTRED01).
            test_count: Number of tests run (0 if no tests)

        Returns:
            Checkpoint record with commit hash

        Raises:
            subprocess.CalledProcessError: If git commands fail
            CheckpointRefused: If ``expected_branch`` was given and HEAD is
                neither on it nor detached exactly at its tip. Nothing is
                committed; the caller stops the task with the reason.
        """
        logger.info(
            f"Creating checkpoint for {self.task_id} turn {turn} "
            f"(tests: {format_test_status(tests_passed)}, count: {test_count})"
        )

        # Serialize git operations to prevent index.lock conflicts
        # when multiple tasks share the same worktree.
        checkpoint = self._create_checkpoint_locked(turn, tests_passed, test_count)

        self.checkpoints.append(checkpoint)
        self._save_checkpoints()

        logger.info(
            f"Created checkpoint: {checkpoint.commit_hash[:8]} for turn {turn} "
            f"({len(self.checkpoints)} total)"
        )

        return checkpoint

    def _get_thread_lock(self) -> threading.Lock:
        """Get or create a thread lock for this worktree path.

        Returns a threading.Lock shared by all managers with the same
        resolved worktree path, ensuring threads coordinate before
        acquiring the file lock.

        Returns:
            threading.Lock for this worktree path
        """
        key = str(self.worktree_path.resolve())
        with self._thread_locks_guard:
            if key not in self._thread_locks:
                self._thread_locks[key] = threading.Lock()
            return self._thread_locks[key]

    def _create_checkpoint_locked(
        self,
        turn: int,
        tests_passed: Optional[bool],
        test_count: int,
    ) -> Checkpoint:
        """Execute git checkpoint operations under a file-based lock.

        Uses a two-level locking strategy:
        1. threading.Lock - coordinates threads in the same process
        2. fcntl.flock - coordinates across processes (if needed)

        Args:
            turn: Turn number (1-indexed)
            tests_passed: Tri-state test signal (True/False/None=unknown)
            test_count: Number of tests run

        Returns:
            Checkpoint record with commit hash

        Raises:
            subprocess.CalledProcessError: If git commands fail
        """
        thread_lock = self._get_thread_lock()

        with thread_lock:
            # Ensure lock file parent directory exists
            self._git_lock_path.parent.mkdir(parents=True, exist_ok=True)

            with open(self._git_lock_path, "w") as lock_file:
                fcntl.flock(lock_file, fcntl.LOCK_EX)
                try:
                    return self._execute_git_checkpoint(
                        turn, tests_passed, test_count
                    )
                finally:
                    fcntl.flock(lock_file, fcntl.LOCK_UN)

    def _execute_git_checkpoint(
        self,
        turn: int,
        tests_passed: Optional[bool],
        test_count: int,
    ) -> Checkpoint:
        """Execute the git add/commit/rev-parse sequence.

        This method contains the actual git operations, extracted for clarity.
        It must only be called while holding the worktree git lock.

        Args:
            turn: Turn number (1-indexed)
            tests_passed: Tri-state test signal (True/False/None=unknown)
            test_count: Number of tests run

        Returns:
            Checkpoint record with commit hash
        """
        # KEEP THE CANDIDATE ON ITS BRANCH (12 October 2026, build 0D7C).
        # Checked here, under the same lock as the commit, so no other task's
        # checkpoint can move HEAD between the check and the commit.
        if self.expected_branch:
            self._keep_head_on_expected_branch(turn)
        elif self.refuse_without_branch:
            reason = (
                f"Checkpoint refused for {self.task_id} turn {turn}: no "
                f"feature branch was determined when the build started (HEAD "
                f"was not on a branch and none was declared), so there is no "
                f"branch to keep the work on. Nothing was committed."
            )
            logger.error(reason)
            raise CheckpointRefused(
                reason, expected_branch="", actual_ref=None,
                head="unknown", branch_tip=None,
            )

        # Stage all changes (including untracked files) EXCEPT build junk
        # (register 2a5, 2026-07-30; extended to the JS/TS classes by TS-lane
        # D.1c): checkpoint commits were baking pip http caches and
        # .guardkit/bootstrap_state.json into TARGET repos — 25 junk files on
        # the FEAT-UDBE branch, and a committed bootstrap_state whose dead
        # venv_python poisons later reads. The exclusions are pathspec magic,
        # so builds never depend on the target repo's own .gitignore hygiene.
        # See CHECKPOINT_EXCLUDE_PATHSPECS for the law and the glob-magic
        # rule; the SAME constant is used by the sibling-evidence add site.
        self.git_executor.execute(
            # The executable is written here literally (the launch guard).
            ["git", *_CHECKPOINT_ADD_ARGV[1:]],
            cwd=self.worktree_path,
        )
        # None of the factory's records enters the commit, even if it was
        # staged before the add above or moved out of its folder (13 and 14
        # October 2026).
        unstage_private_records(self.git_executor, self.worktree_path)

        # Create checkpoint commit message
        status = format_test_status(tests_passed)
        message = f"[guardkit-checkpoint] Turn {turn} complete (tests: {status})"

        # Create commit (allow empty for turns with no changes)
        self.git_executor.execute(
            ["git", "commit", "-m", message, "--allow-empty"],
            cwd=self.worktree_path,
        )

        # Get commit hash
        result = self.git_executor.execute(
            ["git", "rev-parse", "HEAD"],
            cwd=self.worktree_path,
        )
        commit_hash = result.stdout.strip()
        if self.expected_branch:
            # Recorded beside the agents' own before/after lines: another
            # task's checkpoint advancing the branch is the commonest
            # legitimate reason HEAD moves during an invocation.
            record_git_operation(
                self.worktree_path,
                actor="guardkit checkpoint",
                operation=(
                    f"commit turn {turn} checkpoint {commit_hash[:12]} "
                    f"on {self.expected_branch}"
                ),
                task_id=self.task_id,
            )

        # TASK-AB-XREPOEV01 (AC-004): also commit each declared sibling repo so
        # approved sibling-repo work is versioned, not left as uncommitted
        # working-tree edits. Best-effort and per-repo isolated: a failure in
        # one repo must never abort the worktree checkpoint that already
        # landed.
        evidence_commits = self._checkpoint_evidence_repos(turn, tests_passed)

        return Checkpoint(
            turn=turn,
            commit_hash=commit_hash,
            timestamp=datetime.now().isoformat(),
            tests_passed=tests_passed,
            test_count=test_count,
            message=message,
            evidence_commits=evidence_commits,
        )

    def _keep_head_on_expected_branch(self, turn: int) -> None:
        """Make sure the checkpoint commit lands on the feature branch.

        Build 0D7C (12 October 2026) finished with its checkout detached at a
        later checkpoint while its branch still named an older commit: a
        checkpoint had committed on a detached HEAD, so the work never reached
        the branch, and the merge guard rightly refused the candidate. Who
        detached it is not known; this is where the damage would be done, so
        this is where it is stopped.

        * HEAD attached to the expected branch: proceed as always, whether or
          not the branch has advanced (parallel tasks share one worktree and
          each one's checkpoint legitimately moves the branch).
        * HEAD detached at exactly the branch's current tip: re-attach the
          branch first. Nothing in the tree or the index changes. A warning
          is logged.
        * Anything else (detached elsewhere, or on another branch): refuse,
          naming the expected branch, the actual HEAD and the branch tip. No
          commit is ever made on a detached HEAD.

        Must only be called while holding the worktree git lock.
        """
        expected = self.expected_branch
        expected_ref = f"refs/heads/{expected}"
        symbolic = self.git_executor.execute(
            ["git", "symbolic-ref", "-q", "HEAD"],
            cwd=self.worktree_path,
            check=False,
        )
        attached = (
            (symbolic.stdout or "").strip() or None
            if symbolic.returncode == 0
            else None
        )
        if attached == expected_ref:
            return

        head_proc = self.git_executor.execute(
            ["git", "rev-parse", "HEAD"],
            cwd=self.worktree_path,
            check=False,
        )
        head = (
            (head_proc.stdout or "").strip() or "unreadable"
            if head_proc.returncode == 0
            else "unreadable"
        )
        tip_proc = self.git_executor.execute(
            ["git", "rev-parse", "--verify", "-q", f"{expected_ref}^{{commit}}"],
            cwd=self.worktree_path,
            check=False,
        )
        tip = (
            (tip_proc.stdout or "").strip() or None
            if tip_proc.returncode == 0
            else None
        )
        detached = symbolic.returncode == 1

        if detached and tip is not None and head == tip:
            # Same commit, so pointing HEAD back at the branch changes no
            # file and no index entry. The reflog message says who did it.
            self.git_executor.execute(
                [
                    "git", "symbolic-ref",
                    "-m", f"guardkit: re-attach {expected} at its tip "
                    f"before {self.task_id} turn {turn} checkpoint",
                    "HEAD", expected_ref,
                ],
                cwd=self.worktree_path,
            )
            logger.warning(
                f"[{self.task_id}] HEAD was detached at {head[:12]}, which is "
                f"exactly the tip of {expected}; re-attached {expected} before "
                f"the turn {turn} checkpoint. No file changed. Something "
                f"detached HEAD during this task — see "
                f".guardkit/autobuild/head-identity.jsonl for the invocations "
                f"that overlapped."
            )
            record_git_operation(
                self.worktree_path,
                actor="guardkit checkpoint",
                operation=(
                    f"re-attach {expected} at its tip {head[:12]} before "
                    f"turn {turn} checkpoint"
                ),
                task_id=self.task_id,
            )
            return

        if detached:
            actual = f"detached at {head}"
        elif attached is not None:
            actual = f"{attached} at {head}"
        else:
            actual = f"unreadable (git symbolic-ref exited {symbolic.returncode})"
        reason = (
            f"Checkpoint refused for {self.task_id} turn {turn}: the "
            f"worktree's HEAD is not on the feature branch, so a commit here "
            f"would not reach the candidate. Expected branch: {expected}. "
            f"Actual HEAD: {actual}. Branch tip: "
            f"{tip if tip is not None else 'the branch does not exist'}. "
            f"Nothing was committed. See "
            f".guardkit/autobuild/head-identity.jsonl for the agent "
            f"invocations and factory git operations that ran meanwhile."
        )
        logger.error(reason)
        record_git_operation(
            self.worktree_path,
            actor="guardkit checkpoint",
            operation=f"refused turn {turn} checkpoint: HEAD {actual}",
            task_id=self.task_id,
        )
        raise CheckpointRefused(
            reason,
            expected_branch=expected,
            actual_ref=attached,
            head=head,
            branch_tip=tip,
        )

    def _checkpoint_evidence_repos(
        self, turn: int, tests_passed: Optional[bool]
    ) -> Dict[str, str]:
        """Commit each declared sibling repo's working tree at this turn.

        Returns a ``{repo_name: commit_hash}`` map for the repos that were
        successfully committed. Each repo is committed under its own
        ``.guardkit-git.lock`` so parallel features writing to the same
        sibling repo cannot collide on ``index.lock``. Best-effort: any
        per-repo failure is logged and skipped, never raised -- AC-004's
        explicit-disclaim fallback is honoured by logging the gap.
        """
        evidence_commits: Dict[str, str] = {}
        if not self.evidence_repos:
            return evidence_commits

        status = format_test_status(tests_passed)
        message = (
            f"[guardkit-checkpoint] {self.task_id} turn {turn} "
            f"(sibling evidence, tests: {status})"
        )
        for repo in self.evidence_repos:
            try:
                commit = self._commit_one_evidence_repo(repo, message)
                if commit is not None:
                    evidence_commits[repo.name] = commit
                    logger.info(
                        "Checkpointed sibling repo %s at %s (turn %d)",
                        repo.name,
                        commit[:8],
                        turn,
                    )
                else:
                    logger.warning(
                        "Sibling repo %s NOT checkpointed at turn %d "
                        "(no git HEAD / commit failed); its state is "
                        "UNVERSIONED for this turn.",
                        repo.name,
                        turn,
                    )
            except Exception as exc:  # noqa: BLE001 -- never abort the checkpoint
                logger.warning(
                    "Sibling repo %s checkpoint failed at turn %d: %s "
                    "(state UNVERSIONED for this turn).",
                    repo.name,
                    turn,
                    exc,
                )
        return evidence_commits

    def _commit_one_evidence_repo(
        self, repo: EvidenceRepo, message: str
    ) -> Optional[str]:
        """``git add -A && git commit`` one sibling repo under its own lock.

        Returns the new commit hash, or None when the repo is not a usable git
        repository. The commit lands on the repo's CURRENT branch (no branch
        switch -- switching the operator's shared sibling repo is the riskier
        option the task flagged; an additive commit is recoverable, a branch
        switch is disruptive).
        """
        if not repo.root.exists():
            return None

        repo_lock_path = repo.root / ".guardkit-git.lock"
        try:
            repo_lock_path.parent.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass

        with open(repo_lock_path, "w") as lock_file:
            fcntl.flock(lock_file, fcntl.LOCK_EX)
            try:
                # Bounded so a hung git cannot hold the cross-process lock
                # indefinitely and stall every task sharing this repo.
                self.git_executor.execute(
                    # THE SAME constant as the worktree checkpoint above
                    # (register 2a5 + TS-lane D.1c) — a sibling-evidence
                    # commit must not bake pip caches, bootstrap state or
                    # node_modules either. Shared, not copy-pasted: 706589f7
                    # had to fix two divergent literals. The executable is
                    # written here literally (the launch guard).
                    ["git", *_CHECKPOINT_ADD_ARGV[1:]],
                    cwd=repo.root,
                    check=False,
                    timeout=_EVIDENCE_GIT_TIMEOUT_S,
                )
                # As at the worktree checkpoint. A failure here raises, and
                # the caller records this repo as unversioned for the turn
                # rather than committing a private record.
                unstage_private_records(
                    self.git_executor, repo.root,
                    timeout=_EVIDENCE_GIT_TIMEOUT_S,
                )
                self.git_executor.execute(
                    ["git", "commit", "-m", message, "--allow-empty"],
                    cwd=repo.root,
                    check=False,
                    timeout=_EVIDENCE_GIT_TIMEOUT_S,
                )
                result = self.git_executor.execute(
                    ["git", "rev-parse", "HEAD"],
                    cwd=repo.root,
                    check=False,
                    timeout=_EVIDENCE_GIT_TIMEOUT_S,
                )
            except subprocess.TimeoutExpired:
                logger.warning(
                    "Sibling repo %s git commit timed out after %ds; state "
                    "UNVERSIONED for this turn.",
                    repo.name,
                    _EVIDENCE_GIT_TIMEOUT_S,
                )
                return None
            finally:
                fcntl.flock(lock_file, fcntl.LOCK_UN)

        commit = (result.stdout or "").strip()
        return commit or None

    def rollback_to(self, turn: int) -> bool:
        """Rollback worktree to checkpoint at specified turn.

        This method performs a hard reset to the git commit at the specified
        turn, discarding all changes made in subsequent turns. Before the
        reset it snapshots per-turn audit JSONs (``coach_turn_*.json``,
        ``player_turn_*.json``, ``turn_state_turn_*.json``) for turns
        ``> turn`` to ``_rollback_archive/`` so the forensic audit trail of
        the polluted turns survives the reset (TASK-FIX-RBSS AC-3).

        Note:
            This method is **filesystem-only by design**. Resetting the
            Player SDK resume session is the *caller*'s responsibility —
            see ``autobuild.py`` rollback branch which calls
            ``AgentInvoker.set_player_resume_session(None)`` immediately
            after this method returns (TASK-FIX-RBSS AC-1, AC-7). Without
            that caller-side reset the next turn resumes the polluted
            cumulative-authoring memory and re-emits the file claims the
            rollback just deleted, defeating the rollback's purpose.

        Args:
            turn: Turn number to rollback to (1-indexed)

        Returns:
            True if rollback succeeded, False if checkpoint not found

        Raises:
            subprocess.CalledProcessError: If git reset fails
        """
        checkpoint = self._find_checkpoint(turn)
        if not checkpoint:
            logger.warning(f"No checkpoint found for turn {turn}")
            return False

        logger.info(
            f"Rolling back {self.task_id} to turn {turn} "
            f"(commit: {checkpoint.commit_hash[:8]})"
        )

        try:
            # TASK-FIX-RBSS AC-3: snapshot per-turn audit JSONs for turns
            # > target_turn before `git reset --hard` discards them. Audit
            # archival is best-effort: a snapshot failure must not block
            # the rollback itself (the SDK-session reset that follows is
            # load-bearing for recovery; archival is forensic hygiene).
            try:
                self._archive_post_target_audit_files(turn)
            except Exception as archive_error:  # noqa: BLE001
                logger.warning(
                    f"[rollback] Audit-trail archive failed (continuing "
                    f"with reset): {archive_error}"
                )

            # Hard reset to checkpoint commit
            self.git_executor.execute(
                ["git", "reset", "--hard", checkpoint.commit_hash],
                cwd=self.worktree_path,
            )
            if self.expected_branch:
                record_git_operation(
                    self.worktree_path,
                    actor="guardkit rollback",
                    operation=(
                        f"reset --hard to turn {turn} checkpoint "
                        f"{checkpoint.commit_hash[:12]}"
                    ),
                    task_id=self.task_id,
                )

            # TASK-AB-XREPOEV01 (AC-004): reset declared sibling repos to the
            # hash they were committed at in THIS target checkpoint. Guarded:
            # only repos with a recorded hash in the target are reset (we never
            # hard-reset a sibling repo to an unknown state); best-effort so a
            # sibling reset failure cannot break the worktree rollback that
            # already succeeded.
            self._rollback_evidence_repos(checkpoint)

            # Remove checkpoints after rollback point
            self.checkpoints = [cp for cp in self.checkpoints if cp.turn <= turn]
            self._save_checkpoints()

            logger.info(
                f"Rollback successful to turn {turn}, "
                f"{len(self.checkpoints)} checkpoints remaining"
            )
            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"Rollback failed: {e}")
            raise

    def should_rollback(self, consecutive_failures: int = 3) -> bool:
        """Detect if rollback is needed based on test failure patterns.

        This method analyzes recent checkpoint history to detect context pollution.
        The primary indicator is consecutive test failures, suggesting accumulated
        broken state.

        Checkpoints loaded from a prior orchestration session (``from_prior_run``)
        are excluded — they cannot be evidence of pollution accumulating in the
        current run, and counting them would trigger a spurious context-pollution
        short-circuit on turn 1 of any ``[R]esume`` (TASK-FIX-F4A3).

        A checkpoint counts as a "failure" ONLY when its test signal is
        explicitly ``tests_passed is False`` (a test oracle ran and failed).
        A checkpoint with an UNKNOWN signal (``tests_passed is None`` — no
        oracle produced a verdict that turn, e.g. the LLM Coach report carried
        no quality-gate result) is NOT a failure: it is absent evidence, and
        treating it as a failure is a false-red generator (TASK-FIX-CKPTTESTRED01,
        the checkpoint-layer instance of
        ``.claude/rules/absence-of-failure-is-not-success.md``). An unknown
        checkpoint in the recent window therefore breaks the consecutive-failure
        run and suppresses the spurious stall — while genuine consecutive
        ran-and-failed turns still stall as designed.

        Args:
            consecutive_failures: Number of consecutive failures to trigger rollback
                                 (default: 3, allows recovery from incomplete sessions)

        Returns:
            True if rollback should be triggered, False otherwise
        """
        current_run = [cp for cp in self.checkpoints if not cp.from_prior_run]

        if len(current_run) < consecutive_failures:
            return False

        # Check last N current-run checkpoints for consecutive failures.
        # Only an explicit ``tests_passed is False`` counts as a failure;
        # ``None`` (unknown) and ``True`` (pass) both break the run.
        recent = current_run[-consecutive_failures:]
        all_failing = all(cp.tests_passed is False for cp in recent)

        if all_failing:
            logger.warning(
                f"Context pollution detected: {consecutive_failures} consecutive "
                f"test failures in turns {[cp.turn for cp in recent]}"
            )
            return True

        return False

    def find_last_passing_checkpoint(self) -> Optional[int]:
        """Find the most recent checkpoint with passing tests.

        This method scans checkpoints in reverse order to find the last clean
        state for rollback.

        Returns:
            Turn number of last passing checkpoint, or None if none found
        """
        for checkpoint in reversed(self.checkpoints):
            # Only an explicit pass is a rollback target. ``None`` (unknown)
            # is not a known-good state (TASK-FIX-CKPTTESTRED01).
            if checkpoint.tests_passed is True:
                logger.info(
                    f"Found last passing checkpoint at turn {checkpoint.turn} "
                    f"(commit: {checkpoint.commit_hash[:8]})"
                )
                return checkpoint.turn

        logger.warning("No passing checkpoints found in history")
        return None

    def get_checkpoint(self, turn: int) -> Optional[Checkpoint]:
        """Get checkpoint for specific turn.

        Args:
            turn: Turn number

        Returns:
            Checkpoint if found, None otherwise
        """
        return self._find_checkpoint(turn)

    def get_checkpoint_count(self) -> int:
        """Get total number of checkpoints.

        Returns:
            Checkpoint count
        """
        return len(self.checkpoints)

    def clear_checkpoints(self) -> None:
        """Clear all checkpoints (use with caution).

        This method removes all checkpoint history. Use only for testing or
        when starting fresh.
        """
        logger.warning(f"Clearing all checkpoints for {self.task_id}")
        self.checkpoints = []
        self._save_checkpoints()

    # ========================================================================
    # Private Helper Methods
    # ========================================================================

    def _find_checkpoint(self, turn: int) -> Optional[Checkpoint]:
        """Find checkpoint by turn number.

        Args:
            turn: Turn number

        Returns:
            Checkpoint if found, None otherwise
        """
        for checkpoint in self.checkpoints:
            if checkpoint.turn == turn:
                return checkpoint
        return None

    def _rollback_evidence_repos(self, checkpoint: Checkpoint) -> None:
        """Hard-reset declared sibling repos to their hash in ``checkpoint``.

        Only repos with a recorded ``evidence_commits[name]`` in the target
        checkpoint are reset -- we never hard-reset a shared sibling repo to a
        state we did not record. Best-effort: a sibling reset failure is logged
        and skipped so the (already-completed) worktree rollback stands.

        Repos declared now but absent from the target checkpoint (e.g. the
        checkpoint predates a config change) are surfaced as a WARNING: their
        sibling state is NOT rolled back, which the operator must know.
        """
        if not self.evidence_repos:
            return

        rolled_back: List[str] = []
        not_rolled_back: List[str] = []
        for repo in self.evidence_repos:
            target = checkpoint.evidence_commits.get(repo.name)
            if not target:
                not_rolled_back.append(repo.name)
                logger.warning(
                    "Rollback: sibling repo %s has no recorded commit in the "
                    "target checkpoint (turn %d); its state is NOT rolled back.",
                    repo.name,
                    checkpoint.turn,
                )
                continue
            try:
                self.git_executor.execute(
                    ["git", "reset", "--hard", target],
                    cwd=repo.root,
                    check=False,
                    timeout=_EVIDENCE_GIT_TIMEOUT_S,
                )
                rolled_back.append(repo.name)
                logger.info(
                    "Rollback: reset sibling repo %s to %s (turn %d)",
                    repo.name,
                    target[:8],
                    checkpoint.turn,
                )
            except Exception as exc:  # noqa: BLE001 -- never break the rollback
                not_rolled_back.append(repo.name)
                logger.warning(
                    "Rollback: failed to reset sibling repo %s to %s: %s",
                    repo.name,
                    target[:8],
                    exc,
                )

        # Summary line so an operator diagnosing a worktree/sibling mismatch can
        # see at a glance which repos diverged from the rolled-back worktree.
        if not_rolled_back:
            logger.warning(
                "Rollback turn %d: sibling repos rolled back=%s; NOT rolled "
                "back=%s (worktree and these repos may be inconsistent).",
                checkpoint.turn,
                rolled_back or "[]",
                not_rolled_back,
            )

    # Audit JSONs the rollback wipes when their committing turn is rolled
    # away by ``git reset --hard``. Pattern groups: 1=turn number.
    _AUDIT_FILE_PATTERNS: ClassVar[Tuple[Tuple[str, "re.Pattern[str]"], ...]] = (
        ("coach", re.compile(r"^coach_turn_(\d+)\.json$")),
        ("player", re.compile(r"^player_turn_(\d+)\.json$")),
        ("turn_state", re.compile(r"^turn_state_turn_(\d+)\.json$")),
        ("qav_shadow", re.compile(r"^qav_shadow_turn_(\d+)\.json$")),
    )

    def _archive_post_target_audit_files(self, target_turn: int) -> int:
        """Snapshot per-turn audit JSONs for turns > ``target_turn``.

        Copies every ``coach_turn_<N>.json``, ``player_turn_<N>.json`` and
        ``turn_state_turn_<N>.json`` under ``.guardkit/autobuild/<task>/``
        whose turn number is strictly greater than ``target_turn`` into
        ``.guardkit/autobuild/<task>/_rollback_archive/turn_<target>_<ts>/``
        before the caller's ``git reset --hard`` would otherwise destroy
        them. Also writes a defensive ``.gitignore`` inside
        ``_rollback_archive/`` so the archived files self-exclude from any
        future ``git add -A`` checkpoint commit — that prevents subsequent
        rollbacks from recursively wiping prior archives even when the
        consumer project's root ``.gitignore`` does not list the archive
        path (TASK-FIX-RBSS AC-5).

        Audit-trail archival is best-effort. The caller is expected to
        catch any exception and continue with the reset — the SDK-session
        reset that follows is load-bearing; this is forensic hygiene.

        Args:
            target_turn: Rollback target. Files for turns ``> target_turn``
                are archived; the target turn itself is preserved by the
                git reset and does not need archival.

        Returns:
            Number of files archived. Zero is a valid no-op (e.g. test
            fixtures with no per-turn JSONs on disk).
        """
        if not self._autobuild_dir.exists():
            return 0

        rollback_archive_dir = self._autobuild_dir / "_rollback_archive"
        rollback_archive_dir.mkdir(parents=True, exist_ok=True)

        # Defensive in-directory .gitignore so the snapshots are never
        # picked up by `git add -A` in the next checkpoint, regardless of
        # what the project's root .gitignore says. ``!.gitignore`` keeps
        # the marker file itself committable so the directory's intent is
        # discoverable in git history.
        archive_gitignore = rollback_archive_dir / ".gitignore"
        if not archive_gitignore.exists():
            archive_gitignore.write_text("*\n!.gitignore\n", encoding="utf-8")

        timestamp = datetime.now().strftime("%Y%m%dT%H%M%SZ")
        snapshot_dir = rollback_archive_dir / f"turn_{target_turn}_{timestamp}"
        snapshot_dir.mkdir(parents=True, exist_ok=True)

        archived_count = 0
        # Iterate only top-level files in the autobuild dir; we explicitly
        # do NOT descend into _rollback_archive/ so we cannot pick up
        # prior snapshots.
        # TASK-SBHO-002: also scan the private dir for coach_turn files.
        private_dir = self._autobuild_dir.parent / "autobuild-private" / self.task_id
        scan_dirs = [self._autobuild_dir]
        if private_dir.exists():
            scan_dirs.append(private_dir)
        for scan_dir in scan_dirs:
            for entry in scan_dir.iterdir():
                if not entry.is_file():
                    continue
                for _kind, pattern in self._AUDIT_FILE_PATTERNS:
                    match = pattern.match(entry.name)
                    if not match:
                        continue
                    try:
                        file_turn = int(match.group(1))
                    except ValueError:
                        break
                    if file_turn <= target_turn:
                        break
                    try:
                        shutil.copy2(entry, snapshot_dir / entry.name)
                        archived_count += 1
                    except OSError as copy_error:
                        logger.warning(
                            f"[rollback] Failed to archive {entry.name}: "
                            f"{copy_error}"
                        )
                    break

        logger.info(
            f"[rollback] Archived {archived_count} audit file(s) to "
            f"_rollback_archive/{snapshot_dir.name}/"
        )
        return archived_count

    def _save_checkpoints(self) -> None:
        """Save checkpoint history to JSON file.

        Persists checkpoints to .guardkit/autobuild/{task_id}/checkpoints.json
        for resume capability and audit trail.
        """
        try:
            self._autobuild_dir.mkdir(parents=True, exist_ok=True)

            data = {
                "task_id": self.task_id,
                "checkpoints": [cp.to_dict() for cp in self.checkpoints],
                "last_updated": datetime.now().isoformat(),
            }

            with open(self._checkpoints_file, "w") as f:
                json.dump(data, f, indent=2)

            logger.debug(
                f"Saved {len(self.checkpoints)} checkpoints to {self._checkpoints_file}"
            )

        except Exception as e:
            logger.warning(f"Failed to save checkpoints: {e}")
            # Don't raise - persistence is best-effort

    def _load_checkpoints(self) -> None:
        """Load checkpoint history from JSON file.

        Loads existing checkpoints from .guardkit/autobuild/{task_id}/checkpoints.json
        if available. Used during initialization and resume.
        """
        if not self._checkpoints_file.exists():
            logger.debug(f"No checkpoint file found at {self._checkpoints_file}")
            return

        try:
            with open(self._checkpoints_file, "r") as f:
                data = json.load(f)

            checkpoints_data = data.get("checkpoints", [])
            self.checkpoints = [Checkpoint.from_dict(cp) for cp in checkpoints_data]

            # Anything loaded from disk at session-start is by definition from a
            # prior orchestration session — tag accordingly so the pollution
            # detector excludes them (TASK-FIX-F4A3). The persisted value is
            # ignored: a checkpoint that was "current" in the previous session
            # is "prior" in this one.
            for cp in self.checkpoints:
                cp.from_prior_run = True

            prior_run_count = len(self.checkpoints)
            if prior_run_count > 0:
                logger.info(
                    f"Loaded {prior_run_count} checkpoints from "
                    f"{self._checkpoints_file} "
                    f"(tagged from_prior_run; excluded from pollution detection)"
                )
            else:
                logger.info(
                    f"Loaded 0 checkpoints from {self._checkpoints_file}"
                )

        except json.JSONDecodeError as e:
            logger.warning(f"Invalid JSON in checkpoint file: {e}")
            self.checkpoints = []
        except Exception as e:
            logger.warning(f"Failed to load checkpoints: {e}")
            self.checkpoints = []


# ============================================================================
# Public API
# ============================================================================

__all__ = [
    "Checkpoint",
    "WorktreeCheckpointManager",
    "GitCommandExecutor",
    "SubprocessGitExecutor",
]
