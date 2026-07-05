"""Cross-repo evidence support for autobuild (TASK-AB-XREPOEV01).

Central contract for the guardkit <-> sibling-repo (e.g. ``guardkitfactory``)
evidence boundary. The orchestrator's evidence loop (post-turn ``git diff``,
Coach file-existence verification, turn checkpoints, independent tests) is
scoped to the guardkit worktree by default. When a feature or task declares
``evidence_repos``, this module lets the orchestrator widen that boundary to
the declared sibling repos **without** implicitly scanning arbitrary parent
directories (AC-003).

Problem this closes (FEAT-C332 run 1, 2026-06-12): a task whose deliverable
lands in ``guardkitfactory`` (reached from the feature worktree via a symlink)
produced a Player report with ``0 files modified`` because the post-turn diff
only ran in the guardkit worktree. The Coach honestly rejected every turn as
"No implementation provided" while 2,100+ lines of on-spec work sat in the
factory repo. A sibling instance (FEAT-E2CB / BDDW-002) approved factory work
that was then never versioned anywhere.

This module is the **single source of truth** for the repo-qualified path
scheme ``<repo-name>:<rel-path>`` (e.g. ``guardkitfactory:src/foo.py``). The
producer (``AgentInvoker``, which writes the Player report) and the consumers
(``CoachVerifier`` file-existence checks, ``WorktreeCheckpointManager``,
``CoachValidator`` independent tests) MUST all route through
:func:`qualify` / :func:`split_qualified` so the two halves cannot drift.
That is the namespace-hygiene lesson (``.claude/rules/namespace-hygiene.md``):
a cross-repo contract scattered across files silently rots.

Sibling rules honoured here:

- ``.claude/rules/absence-of-failure-is-not-success.md`` -- an undeclared or
  un-runnable evidence repo is **absent** signal, never a silent pass. A
  declared test command that cannot run surfaces as feedback, not approval
  (see :class:`EvidenceTestResult.ran`).
- ``.claude/rules/path-string-mismatch-is-not-dishonesty.md`` -- an
  unresolvable repo-qualified path (unknown repo name) is fail-open, never a
  new false-red. Consumers resolve only declared repos and skip the rest.
- ``.claude/rules/harness-cancellation-contract.md`` /
  ``.claude/rules/namespace-hygiene.md`` -- this is the same guardkit <->
  guardkitfactory seam those rules govern; a feature declaring
  ``evidence_repos`` against an orchestrator that does not support them must
  fail **loudly** (the seam test), not absently.
"""

from __future__ import annotations

import logging
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Stdlib-only module; no import cycle back into evidence consumers
# (TASK-FIX-SIBTESTENV01 reuses the single source of truth for on-disk
# venv layouts rather than re-inventing the probe).
from guardkit.orchestrator.environment_bootstrap import probe_worktree_venv

logger = logging.getLogger(__name__)

# The separator between a repo name and its in-repo relative path in a
# repo-qualified evidence path. ``guardkitfactory:src/foo.py``.
QUALIFIER_SEP: str = ":"

# A repo NAME (the qualifier prefix) is a restricted token: no path
# separators, no colon. This keeps ``split_qualified`` from misfiring on
# genuine worktree-relative paths and prevents the qualifier from carrying a
# traversal payload.
_REPO_NAME_RE = re.compile(r"^[A-Za-z0-9_.\-]+$")

# Git command timeout (seconds). Mirrors AgentInvoker._detect_git_changes.
_GIT_TIMEOUT_S: int = 30


# ============================================================================
# Data models
# ============================================================================


@dataclass(frozen=True)
class EvidenceRepo:
    """A declared sibling repository whose writes count as task evidence.

    Attributes:
        name: Qualifier prefix used in repo-qualified paths
            (e.g. ``"guardkitfactory"``). Derived from the resolved
            directory name; never carries a path separator.
        root: Absolute path to the sibling repo's working tree. The
            orchestrator runs ``git`` and the declared ``test_command`` here.
        test_command: Optional per-repo command the Coach runs independently
            to verify sibling-repo work (AC-002). ``None`` means "no
            independent test for this repo" -- which is absent signal, NOT a
            pass (see :class:`EvidenceTestResult`).
        interpreter: Optional explicit Python interpreter path the
            ``test_command`` is pinned to (TASK-FIX-SIBTESTENV01). Relative
            paths resolve against ``root``. Takes precedence over the
            sibling's probed ``.venv`` -- see :func:`_resolve_repo_interpreter`.
    """

    name: str
    root: Path
    test_command: Optional[str] = None
    interpreter: Optional[str] = None


@dataclass
class EvidenceRepoChanges:
    """Per-repo git changes, expressed as repo-qualified paths.

    Attributes:
        repo: The evidence repo these changes belong to.
        modified: Repo-qualified paths of tracked files changed since baseline.
        created: Repo-qualified paths of untracked files.
    """

    repo: EvidenceRepo
    modified: List[str] = field(default_factory=list)
    created: List[str] = field(default_factory=list)

    @property
    def all_qualified(self) -> List[str]:
        """Every qualified path (modified + created), de-duplicated and sorted."""
        return sorted(set(self.modified) | set(self.created))


@dataclass
class EvidenceTestResult:
    """Result of the Coach independently running a sibling repo's tests (AC-002).

    The ``ran`` / ``passed`` split is load-bearing: a declared test command
    that could not run (``ran=False``) is **absent** signal and must surface
    as feedback, never be read as a pass. Only ``ran=True and passed=False``
    is a genuine failure, and ``ran=True and passed=True`` a genuine pass.
    See ``.claude/rules/absence-of-failure-is-not-success.md``.

    Attributes:
        repo_name: The evidence repo's qualifier name.
        command: The test command that was (or would have been) executed.
        ran: True only if the command actually executed to completion.
        passed: True only if it ran AND exited 0.
        returncode: Process exit code, or None if it never ran.
        output_summary: Truncated combined stdout/stderr for the evidence bundle.
    """

    repo_name: str
    command: Optional[str]
    ran: bool
    passed: bool
    returncode: Optional[int] = None
    output_summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """JSON-serialisable form for the evidence bundle (coach/player turn)."""
        return {
            "repo_name": self.repo_name,
            "command": self.command,
            "ran": self.ran,
            "passed": self.passed,
            "returncode": self.returncode,
            "output_summary": self.output_summary,
        }


# ============================================================================
# Repo-qualified path scheme (the cross-repo contract)
# ============================================================================


def qualify(repo_name: str, rel_path: str) -> str:
    """Build a repo-qualified evidence path ``<repo_name>:<rel_path>``.

    Args:
        repo_name: Evidence repo qualifier (no path separator, no colon).
        rel_path: Path relative to the repo root, POSIX-style.

    Returns:
        The qualified path string.

    Raises:
        ValueError: If ``repo_name`` is not a valid repo token.
    """
    if not _REPO_NAME_RE.match(repo_name):
        raise ValueError(
            f"Invalid evidence-repo name {repo_name!r}: must match "
            f"{_REPO_NAME_RE.pattern}"
        )
    # Normalise leading "./" and backslashes so the qualified form is stable.
    normalised = rel_path.replace("\\", "/")
    if normalised.startswith("./"):
        normalised = normalised[2:]
    return f"{repo_name}{QUALIFIER_SEP}{normalised}"


def is_qualified(path: str) -> bool:
    """True if ``path`` is a syntactically repo-qualified evidence path.

    Purely syntactic: the prefix before the first ``:`` must be a valid repo
    token (no ``/`` or ``\\``) and the remainder non-empty. Resolution against
    the *declared* repo set is the caller's responsibility -- an unknown repo
    name is fail-open, not an error.
    """
    return split_qualified(path) is not None


def split_qualified(path: str) -> Optional[Tuple[str, str]]:
    """Split a repo-qualified path into ``(repo_name, rel_path)``.

    Returns None when ``path`` is an ordinary (worktree-relative) path. A path
    is treated as qualified only when the segment before the first ``:`` is a
    bare repo token -- this prevents misfiring on genuine paths that contain a
    colon further along (e.g. ``dir/weird:name.py``).

    Args:
        path: Candidate path string.

    Returns:
        ``(repo_name, rel_path)`` or None.
    """
    if not isinstance(path, str) or QUALIFIER_SEP not in path:
        return None
    prefix, _, remainder = path.partition(QUALIFIER_SEP)
    if not prefix or not remainder:
        return None
    if "/" in prefix or "\\" in prefix:
        return None
    if not _REPO_NAME_RE.match(prefix):
        return None
    return prefix, remainder


def resolve_qualified_path(
    path: str, repos: Optional[List[EvidenceRepo]]
) -> Optional[Path]:
    """Resolve a repo-qualified path to an absolute on-disk path.

    Args:
        path: Candidate path (qualified or not).
        repos: The DECLARED evidence repos. Only these are resolved.

    Returns:
        The absolute ``repo.root / rel_path`` when ``path`` is qualified and
        names a declared repo; otherwise None (ordinary path, or unknown repo
        name -- the latter is fail-open per the path-string-mismatch rule).
    """
    split = split_qualified(path)
    if split is None or not repos:
        return None
    repo_name, rel_path = split
    for repo in repos:
        if repo.name == repo_name:
            return repo.root / rel_path
    return None


# ============================================================================
# Declaration parsing & resolution
# ============================================================================


def resolve_evidence_repos(
    declared: Optional[List[Any]], base: Path
) -> List[EvidenceRepo]:
    """Resolve declared ``evidence_repos`` entries to concrete repos.

    Each declared entry is either:

    - a bare string path (``"../guardkitfactory"``), or
    - a mapping ``{"path": "../guardkitfactory", "test_command": "pytest -q"}``.

    Relative paths resolve against ``base`` (the source repo root the worktree
    was created from), then ``Path.resolve()`` follows symlinks to the
    canonical sibling repo. Entries whose path does not exist on disk are
    dropped with a loud WARNING -- the orchestrator cannot baseline a repo
    that is not there, and silently inventing one would violate AC-003. The
    seam test guards the orthogonal failure (orchestrator lacking the feature
    entirely).

    Args:
        declared: Raw ``evidence_repos`` list from feature YAML / frontmatter.
        base: Directory that relative entries resolve against.

    Returns:
        Resolved, de-duplicated :class:`EvidenceRepo` list (possibly empty).
    """
    if not declared:
        return []

    base = Path(base)
    resolved: List[EvidenceRepo] = []
    seen_roots: set[str] = set()

    for entry in declared:
        raw_path, test_command, interpreter = _parse_entry(entry)
        if raw_path is None:
            logger.warning(
                "evidence_repos: ignoring malformed entry %r (expected str or "
                "mapping with 'path')",
                entry,
            )
            continue

        candidate = Path(raw_path)
        if not candidate.is_absolute():
            candidate = base / candidate
        try:
            root = candidate.resolve()
        except OSError as exc:  # broken symlink, permission denied
            logger.warning(
                "evidence_repos: cannot resolve %r (base=%s): %s -- skipping",
                raw_path,
                base,
                exc,
            )
            continue

        if not root.is_dir():
            logger.warning(
                "evidence_repos: declared path %s does not exist on disk "
                "(resolved from %r) -- skipping. Sibling-repo evidence for "
                "this entry will be ABSENT.",
                root,
                raw_path,
            )
            continue

        key = str(root)
        if key in seen_roots:
            continue
        seen_roots.add(key)

        name = root.name
        if not _REPO_NAME_RE.match(name):
            logger.warning(
                "evidence_repos: resolved repo dir name %r is not a valid "
                "qualifier token -- skipping %s",
                name,
                root,
            )
            continue

        resolved.append(
            EvidenceRepo(
                name=name,
                root=root,
                test_command=test_command,
                interpreter=interpreter,
            )
        )
        logger.info(
            "evidence_repos: declared sibling repo %s -> %s%s%s",
            name,
            root,
            f" (test_command={test_command!r})" if test_command else "",
            f" (interpreter={interpreter!r})" if interpreter else "",
        )

    return resolved


def _parse_entry(entry: Any) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Extract ``(path, test_command, interpreter)`` from one declared entry."""
    if isinstance(entry, str):
        return (entry.strip() or None), None, None
    if isinstance(entry, dict):
        raw_path = entry.get("path") or entry.get("repo")
        test_command = entry.get("test_command") or entry.get("tests")
        interpreter = entry.get("interpreter")
        if isinstance(raw_path, str) and raw_path.strip():
            tc = test_command.strip() if isinstance(test_command, str) and test_command.strip() else None
            interp = interpreter.strip() if isinstance(interpreter, str) and interpreter.strip() else None
            return raw_path.strip(), tc, interp
    return None, None, None


# ============================================================================
# Per-repo git evidence (baseline + diff)
# ============================================================================


def record_repo_baseline(repo: EvidenceRepo) -> Optional[str]:
    """Record the sibling repo's HEAD commit before task execution.

    Mirrors ``AgentInvoker._record_baseline`` for the worktree: a per-task
    baseline lets the post-turn diff attribute only this task's writes, even
    when sibling-repo HEAD moves under parallel waves.

    Returns:
        The 40-char commit hash, or None when the repo is not a usable git
        repository (fail-safe -- the diff then falls back to ``HEAD``).
    """
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(repo.root),
            capture_output=True,
            text=True,
            timeout=_GIT_TIMEOUT_S,
        )
        if proc.returncode == 0:
            return proc.stdout.strip()
        logger.debug(
            "evidence_repos: git rev-parse HEAD failed in %s (%s)",
            repo.root,
            proc.stderr.strip(),
        )
    except subprocess.TimeoutExpired:
        logger.warning("evidence_repos: git rev-parse timed out in %s", repo.root)
    except Exception as exc:  # noqa: BLE001 -- never block the turn
        logger.warning(
            "evidence_repos: failed to record baseline for %s: %s", repo.root, exc
        )
    return None


def record_repo_baselines(
    repos: Optional[List[EvidenceRepo]],
) -> Dict[str, Optional[str]]:
    """Record baselines for every declared repo, keyed by absolute root path."""
    if not repos:
        return {}
    return {str(repo.root): record_repo_baseline(repo) for repo in repos}


def detect_repo_changes(
    repo: EvidenceRepo, baseline: Optional[str]
) -> EvidenceRepoChanges:
    """Detect git changes in one evidence repo since ``baseline``.

    Returns repo-qualified paths so the Player report and Coach speak the same
    scheme. Mirrors ``AgentInvoker._detect_git_changes`` but scoped to the
    sibling repo root and qualified by repo name.

    Failure (non-git dir, git error, timeout) yields empty changes -- absent
    signal, never a fabricated result.
    """
    changes = EvidenceRepoChanges(repo=repo)
    diff_ref = baseline or "HEAD"

    try:
        proc = subprocess.run(
            ["git", "diff", "--name-only", diff_ref],
            cwd=str(repo.root),
            capture_output=True,
            text=True,
            timeout=_GIT_TIMEOUT_S,
        )
        if proc.returncode == 0:
            changes.modified = [
                qualify(repo.name, f.strip())
                for f in proc.stdout.strip().split("\n")
                if f.strip()
            ]

        proc = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard"],
            cwd=str(repo.root),
            capture_output=True,
            text=True,
            timeout=_GIT_TIMEOUT_S,
        )
        if proc.returncode == 0:
            changes.created = [
                qualify(repo.name, f.strip())
                for f in proc.stdout.strip().split("\n")
                if f.strip()
            ]
    except subprocess.TimeoutExpired:
        logger.warning("evidence_repos: git change detection timed out in %s", repo.root)
    except Exception as exc:  # noqa: BLE001 -- never block the turn
        logger.warning(
            "evidence_repos: git change detection failed in %s: %s", repo.root, exc
        )

    return changes


def detect_all_repo_changes(
    repos: Optional[List[EvidenceRepo]],
    baselines: Optional[Dict[str, Optional[str]]],
) -> List[EvidenceRepoChanges]:
    """Detect changes across every declared repo."""
    if not repos:
        return []
    baselines = baselines or {}
    return [
        detect_repo_changes(repo, baselines.get(str(repo.root)))
        for repo in repos
    ]


def qualified_paths_for_changes(
    changes: List[EvidenceRepoChanges],
) -> Tuple[List[str], List[str]]:
    """Flatten per-repo changes into ``(modified, created)`` qualified lists."""
    modified: List[str] = []
    created: List[str] = []
    for change in changes:
        modified.extend(change.modified)
        created.extend(change.created)
    return sorted(set(modified)), sorted(set(created))


# ============================================================================
# Independent per-repo tests (AC-002)
# ============================================================================

# Pytest exit codes that indicate the run died before/inside collection
# (2 = interrupted, 3 = internal error, 4 = usage/collection error). Exit 1
# is a genuine ran-and-failed verdict and is NEVER reclassified
# (TASK-FIX-SIBTESTENV01 AC-3).
_COLLECTION_ERROR_EXITS: Tuple[int, ...] = (2, 3, 4)

# Import-failure signatures pytest emits when a test module cannot even be
# imported during collection -- the fingerprint of a mis-resolved
# interpreter (the FEAT-10AC run-2 shape), not of failing tests.
_COLLECTION_IMPORT_ERROR_MARKERS: Tuple[str, ...] = (
    "ImportError while importing test module",
    "ModuleNotFoundError: No module named",
    "ImportError: cannot import name",
)

# Veto: if ANY tests actually ran ("3 passed", "1 failed"), the suite
# executed and a late import error must stay ran-and-failed -- bias to
# failure on ambiguity (the bdd_runner precedent).
_TESTS_ACTUALLY_RAN_RE = re.compile(r"\b\d+ (?:passed|failed)\b")


def _is_collection_import_error(returncode: Optional[int], output: str) -> bool:
    """True when a test run died at collection with an import error (AC-3).

    Classification rules (TASK-FIX-SIBTESTENV01):

    1. Exit code must be in :data:`_COLLECTION_ERROR_EXITS`. Exit 1 (tests
       ran and failed) is never reclassified.
    2. VETO: when :data:`_TESTS_ACTUALLY_RAN_RE` matches the output, tests
       executed -- the result stays ran-and-failed regardless of any
       import-error text.
    3. At least one :data:`_COLLECTION_IMPORT_ERROR_MARKERS` signature must
       be present. An ambiguous exit-2 with no marker stays ran-and-failed
       (bias to failure, per ``absence-of-failure-is-not-success``).
    """
    if returncode not in _COLLECTION_ERROR_EXITS:
        return False
    if _TESTS_ACTUALLY_RAN_RE.search(output):
        return False
    return any(marker in output for marker in _COLLECTION_IMPORT_ERROR_MARKERS)


def _resolve_repo_interpreter(repo: EvidenceRepo) -> Optional[str]:
    """Resolve the Python interpreter a sibling repo's tests pin to.

    Per-repo resolution (TASK-FIX-SIBTESTENV01): the sibling repo has its
    OWN dependency set, so its tests must never be pinned to the guardkit
    worktree venv (the FEAT-10AC run-2 mis-environmented oracle). Precedence:

    1. Explicit ``interpreter:`` field on the declaration. Relative paths
       resolve against ``repo.root``; a declared-but-missing path logs a
       loud WARNING and falls through (fail-open). Explicit precedes probed
       because a stale sibling ``.venv`` must not silently override an
       operator declaration (arch-review REC-2) -- mirrors the
       ``_resolve_venv_python`` precedent (explicit beats discovery).
    2. The sibling's own venv via :func:`probe_worktree_venv` on
       ``repo.root`` (covers ``.venv/bin/python`` and the legacy
       ``.guardkit/venv/bin/python`` layout).
    3. None -- the command runs verbatim via the shell in ``repo.root``.
    """
    if repo.interpreter:
        candidate = Path(repo.interpreter)
        if not candidate.is_absolute():
            candidate = repo.root / candidate
        if candidate.exists():
            logger.info(
                "evidence_repos: %s tests pin to declared interpreter %s",
                repo.name,
                candidate,
            )
            return str(candidate)
        logger.warning(
            "evidence_repos: declared interpreter %r for %s does not exist "
            "(resolved to %s) -- falling through to the sibling venv probe.",
            repo.interpreter,
            repo.name,
            candidate,
        )

    probed = probe_worktree_venv(repo.root)
    if probed is not None:
        logger.info(
            "evidence_repos: %s tests pin to sibling venv interpreter %s",
            repo.name,
            probed,
        )
        return str(probed)

    logger.info(
        "evidence_repos: no interpreter resolved for %s -- test_command "
        "runs verbatim via shell in %s",
        repo.name,
        repo.root,
    )
    return None


def run_repo_tests(
    repo: EvidenceRepo,
    timeout: int = 600,
) -> EvidenceTestResult:
    """Run the declared per-repo ``test_command`` independently in ``repo.root``.

    This is the Coach's trust-but-verify pass for sibling-repo work (AC-002).
    The result is meant to be folded into the evidence bundle.

    Interpreter pinning is PER-REPO (TASK-FIX-SIBTESTENV01): when the command
    starts with a bare ``pytest``/``python`` token, it is rewritten to run
    under the interpreter :func:`_resolve_repo_interpreter` resolves for THIS
    repo (explicit ``interpreter:`` field, else the sibling's own venv).
    The guardkit worktree venv is structurally unreachable here -- pinning a
    sibling suite to the caller's venv is the FEAT-10AC run-2 defect. When no
    interpreter resolves, the command runs verbatim via the shell.

    Absent signal, not pass: a repo with no ``test_command`` returns
    ``ran=False, passed=False``. The caller decides how to surface that (it is
    feedback / unverified, never a silent approval). A run that died at
    collection with an import error is likewise ABSENT (``ran=False``) -- the
    suite never executed, so there is no test verdict (AC-3; the
    ``absence-of-failure`` family).
    """
    if not repo.test_command:
        return EvidenceTestResult(
            repo_name=repo.name,
            command=None,
            ran=False,
            passed=False,
            output_summary="No test_command declared for this evidence repo "
            "(sibling-repo tests UNVERIFIED).",
        )

    interpreter = _resolve_repo_interpreter(repo)
    argv, shell = _build_repo_test_argv(repo.test_command, interpreter)
    try:
        proc = subprocess.run(
            argv,
            cwd=str(repo.root),
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=shell,
        )
    except subprocess.TimeoutExpired:
        return EvidenceTestResult(
            repo_name=repo.name,
            command=repo.test_command,
            ran=False,
            passed=False,
            output_summary=f"Evidence-repo tests timed out after {timeout}s in {repo.root}.",
        )
    except Exception as exc:  # noqa: BLE001 -- failure to run is absent signal
        return EvidenceTestResult(
            repo_name=repo.name,
            command=repo.test_command,
            ran=False,
            passed=False,
            output_summary=f"Evidence-repo tests could not run in {repo.root}: {exc}",
        )

    combined = (proc.stdout or "") + (proc.stderr or "")
    if _is_collection_import_error(proc.returncode, combined):
        return EvidenceTestResult(
            repo_name=repo.name,
            command=repo.test_command,
            ran=False,
            passed=False,
            returncode=proc.returncode,
            output_summary=(
                f"Evidence-repo test collection failed with an import error "
                f"(exit {proc.returncode}) -- the suite NEVER ran, so "
                f"sibling-repo work is UNVERIFIED (absent signal, not a test "
                f"failure; TASK-FIX-SIBTESTENV01 AC-3). Likely an environment "
                f"/ interpreter mismatch, not a deliverable defect.\n"
                + _truncate(combined)
            ),
        )
    return EvidenceTestResult(
        repo_name=repo.name,
        command=repo.test_command,
        ran=True,
        passed=proc.returncode == 0,
        returncode=proc.returncode,
        output_summary=_truncate(combined),
    )


def _build_repo_test_argv(
    test_command: str, interpreter: Optional[str]
) -> Tuple[Any, bool]:
    """Return ``(argv, shell)`` for running a repo test command.

    When the command is a bare ``pytest ...`` / ``python ...`` invocation and
    a per-repo interpreter resolved, run it as a pinned argv list (no shell).
    Otherwise run the command string through the shell verbatim.
    """
    tokens = test_command.split()
    if interpreter and tokens:
        head = tokens[0]
        if head == "pytest":
            return [str(interpreter), "-m", "pytest", *tokens[1:]], False
        if head in ("python", "python3"):
            return [str(interpreter), *tokens[1:]], False
    return test_command, True


def run_all_repo_tests(
    repos: Optional[List[EvidenceRepo]],
    timeout: int = 600,
) -> List[EvidenceTestResult]:
    """Run independent tests for every declared repo that has a command.

    Each repo resolves its own interpreter (TASK-FIX-SIBTESTENV01) -- there
    is deliberately no caller-supplied interpreter parameter here.
    """
    if not repos:
        return []
    return [run_repo_tests(repo, timeout=timeout) for repo in repos]


def evidence_repo_tests_blocking_reason(
    results: List[EvidenceTestResult],
) -> Optional[str]:
    """Decide whether sibling-repo test results should block the turn.

    Returns a feedback string (naming the offending repos) when any declared
    sibling test suite either failed or could not run; None when every
    declared suite passed (and repos without a declared command are ignored --
    "no test declared" is not a failure, it is simply out of scope).

    Note the absence-of-failure posture: a declared ``test_command`` that
    could NOT run (``command`` set, ``ran`` False) blocks, because a
    verification the Player asked for but which never executed must not be
    read as a silent pass. A repo with no command at all does not block.
    """
    failed = [r for r in results if r.command and r.ran and not r.passed]
    unrunnable = [r for r in results if r.command and not r.ran]
    if not failed and not unrunnable:
        return None

    lines: List[str] = []
    for r in failed:
        lines.append(
            f"- {r.repo_name}: sibling-repo tests FAILED (exit {r.returncode}) "
            f"for `{r.command}`"
        )
    for r in unrunnable:
        detail = r.output_summary.strip().splitlines()
        tail = detail[-1] if detail else ""
        lines.append(
            f"- {r.repo_name}: declared sibling-repo tests could NOT run "
            f"(`{r.command}`){f': {tail}' if tail else ''}"
        )
    return (
        "Sibling-repo (evidence_repos) independent tests did not pass:\n"
        + "\n".join(lines)
    )


def _truncate(text: str, max_length: int = 4000) -> str:
    """Truncate test output for the evidence bundle, keeping the tail."""
    text = text.strip()
    if len(text) <= max_length:
        return text
    return "...[truncated]...\n" + text[-max_length:]


__all__ = [
    "QUALIFIER_SEP",
    "EvidenceRepo",
    "EvidenceRepoChanges",
    "EvidenceTestResult",
    "qualify",
    "is_qualified",
    "split_qualified",
    "resolve_qualified_path",
    "resolve_evidence_repos",
    "record_repo_baseline",
    "record_repo_baselines",
    "detect_repo_changes",
    "detect_all_repo_changes",
    "qualified_paths_for_changes",
    "run_repo_tests",
    "run_all_repo_tests",
    "evidence_repo_tests_blocking_reason",
]
