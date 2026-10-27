"""Check each task's own change for secrets (a safety fence the cull keeps).

WHAT THIS IS
------------
One "run this command; exit 0 is the pass" check. :func:`security_check_command`
builds the command once, before the first turn, when the worktree still holds what
the task started from; the Coach's evidence run (``CoachValidator.gather_evidence``)
runs it every turn, and a confirmed secret sends the turn back with the lines that
hold one (``AgentInvoker._apply_security_check_guard``). (27 October 2026: the
dependency part of this check was removed with the other checks.)

The command is this module as a program (:func:`main`). It looks only at the files the
task changed (``git diff --name-only <start>`` plus files git is not yet tracking, with
``.guardkit/`` left out). Each changed file is read once, up to 20 MB. Gitleaks runs in
``dir`` mode over copies of the changed files, with its built-in rules, ``--redact``
and ``--ignore-gitleaks-allow``. A finding names the file, the line and the kind of
secret, never the value.

NO REPOSITORY SETTINGS REACH THE SCANNER
----------------------------------------
The copies never include ``.gitleaks.toml`` or ``.gitleaksignore``; Gitleaks' ignore
lookup is pointed at an empty folder (``/opt/factory-security/gitleaks-ignore`` in the
factory image, or a private empty one). The scanner runs with an environment built
from nothing. The command runs as ``<absolute interpreter> -I -m ...`` so a
``guardkit.py`` the code generator wrote cannot be imported instead of this checker.

A scanner that is missing, errors or runs out of time prints "<what> was not checked"
and exits 0: only a confirmed secret exits 1. ``--self-test`` (for the release's live
check inside the image) prints one line and exits 0 when this isolated interpreter
found the installed guardkit and Gitleaks starts.

THE SWITCH (17 October 2026). The check is added only when
``GUARDKIT_SECURITY_CHECK_BLOCKING`` is set (``1``, ``true``, ``yes`` or ``on``).
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple

from guardkit.lib.project_git import run_git

logger = logging.getLogger(__name__)

#: How long one git question may take.
_GIT_TIMEOUT_SECONDS = 60

#: The outer limit on one run of the command; it keeps its own budget inside it.
RULE_TIMEOUT_SECONDS = 300

#: The command's own running budget, and each part's deadline inside it.
BUDGET_SECONDS = 200.0
TOOL_DEADLINE_SECONDS = 60.0

#: Where the factory image keeps the scanners' own settings (Forge builds them).
FACTORY_SETTINGS_DIR = Path("/opt/factory-security")
FACTORY_GITLEAKS_IGNORE_DIR = FACTORY_SETTINGS_DIR / "gitleaks-ignore"

#: Files a scanner would read as its settings. Never copied for scanning.
SCANNER_SETTINGS_FILES = frozenset({".gitleaks.toml", ".gitleaksignore"})


#: The scanners' names on PATH when the rule is built.
GITLEAKS_NAME = "gitleaks"

_NOT_CHECKED = "{what} was not checked: {why}. Nothing was checked, which is not the same as clean."

_MODULE = "guardkit.orchestrator.security_check"


# ---------------------------------------------------------------------------
# The rule handed to the build loop
# ---------------------------------------------------------------------------


def _find_tool(name: str) -> Optional[str]:
    """The absolute path of ``name`` on PATH right now, or ``None``."""
    found = shutil.which(name)
    if not found:
        return None
    return os.path.abspath(found)


#: The operator's switch. Off unless set to one of :data:`_SWITCH_ON`.
BLOCKING_ENV_VAR = "GUARDKIT_SECURITY_CHECK_BLOCKING"

_SWITCH_ON = {"1", "true", "yes", "on"}


def blocking_requested(env: Optional[Mapping[str, str]] = None) -> bool:
    """Has the operator switched the security check on? Absent or unrecognised is no."""
    source = os.environ if env is None else env
    return str(source.get(BLOCKING_ENV_VAR, "")).strip().lower() in _SWITCH_ON


def security_check_command(
    worktree_path: Path,
    task_id: Optional[str] = None,
    env: Optional[Mapping[str, str]] = None,
    start_commit: Optional[str] = None,
) -> Optional[str]:
    """The secrets check command for this task, or ``None``.

    ``None`` when the switch :data:`BLOCKING_ENV_VAR` is not set (the default), when
    Gitleaks is not installed, or when the commit this task starts from cannot be
    read. ``start_commit`` names that commit when the caller knows it (a resumed
    task); otherwise the worktree's current commit is used. Gitleaks is named by the
    absolute path found now. Never raises.
    """
    try:
        if not blocking_requested(env):
            return None
        gitleaks = _find_tool(GITLEAKS_NAME)
        if gitleaks is None:
            logger.debug(
                "Security check: %s is not installed, so no check was added for %s.",
                GITLEAKS_NAME, task_id or "<task>")
            return None
        try:
            sha = start_commit or starting_commit(Path(worktree_path))
        except ValueError as exc:
            logger.warning(
                "Security check: the commit %s starts from could not be read (%s), "
                "so no check was added.", task_id or "<task>", exc)
            return None
        logger.info(
            "Security check: %s will be checked for secrets in the files it changes "
            "since %s (gitleaks: %s).", task_id or "<task>", sha[:12], gitleaks)
        return " ".join([
            shlex.quote(sys.executable), "-I", "-m", _MODULE,
            "--repo", ".", "--since", shlex.quote(sha),
            "--gitleaks", shlex.quote(gitleaks),
        ])
    except Exception as exc:  # noqa: BLE001 -- this can never fail a build
        logger.warning(
            "Security check: working out the check for %s raised %s, so no check was "
            "added.", task_id or "<task>", exc.__class__.__name__)
        return None


# ---------------------------------------------------------------------------
# Git and output helpers
# ---------------------------------------------------------------------------


def _git(repo: Path, *args: str, raw: bool = False, timeout: Optional[float] = None) -> Any:
    """Ask git one read-only question inside ``repo`` and return what it said.

    Text by default; the exact bytes when ``raw`` is set (for NUL-separated file
    names, which may not be valid text).

    Raises ``ValueError`` with a sentence a person can read whenever git is not there,
    does not answer, or answers with an error. Every caller here turns that into "the
    check could not run", never into a failed build.
    """
    if shutil.which("git") is None:
        raise ValueError("git is not on this machine.")
    try:
        done = run_git(
            ["-C", str(repo), *args],
            check=True,
            text=not raw,
            timeout=timeout or _GIT_TIMEOUT_SECONDS)
    except subprocess.CalledProcessError as exc:
        raise ValueError(
            f"git {' '.join(args)} failed in {repo}: "
            f"{(exc.stderr or '').strip() or 'no reason given'}") from exc
    except subprocess.TimeoutExpired as exc:
        raise ValueError(
            f"git {' '.join(args)} did not answer within "
            f"{int(timeout or _GIT_TIMEOUT_SECONDS)} seconds in {repo}") from exc
    except OSError as exc:
        raise ValueError(f"git could not be run in {repo}: {exc}") from exc
    return done.stdout


def starting_commit(worktree_path: Path) -> str:
    """The commit this worktree sits on right now.

    Read before the first turn, when the worktree still holds exactly what the task
    started from, so that everything different from it later is this task's own work.
    """
    sha = _git(Path(worktree_path), "rev-parse", "HEAD").strip()
    if not sha:
        raise ValueError(f"git named no commit for {worktree_path}.")
    return sha


def files_changed_since(repo: Path, start_commit: str,
                        timeout: Optional[float] = None,
                        *, no_renames: bool = False) -> list[str]:
    """The repository-relative files that differ from ``start_commit`` right now.

    Two questions, because one is not enough. ``git diff`` names every tracked file
    that differs from that commit, committed or not -- but it says nothing about a
    file git has never been told about, and a brand-new file is exactly where new code
    goes. So the files git is not tracking are asked for separately and added. Missing
    them would let a whole new file pass unread, which is this estate's known failure
    class: a check that runs, looks in the wrong place, and reports success.

    Both answers are asked for NUL-separated (``-z``, 17 October 2026). Without it git
    quotes and escapes any name holding a non-ASCII character, a quote or a
    backslash, and the escaped name names no file on disk, so such a file was never
    read. Names are taken exactly as given, never trimmed.

    ``no_renames`` (20 October 2026): git's rename detection names only the new
    path of a renamed file. With it a rename is a deleted path and a new path,
    and both are named; the repair round's audit asks for this so that moving a
    protected file is seen as touching it. Off by default, so every other
    caller gets exactly what it got before.
    """
    repo = Path(repo)
    diff_args = ["diff", "--name-only", "-z"]
    if no_renames:
        diff_args.append("--no-renames")
    changed = _git(repo, *diff_args, start_commit, raw=True, timeout=timeout)
    untracked = _git(repo, "ls-files", "--others", "--exclude-standard", "-z", raw=True,
                     timeout=timeout)
    names = (*changed.split(b"\0"), *untracked.split(b"\0"))
    return sorted({os.fsdecode(name) for name in names if name})


def visible(text: str) -> str:
    """``text`` with every control character and undecodable byte shown, not acted on.

    A file name may hold a newline, a terminal escape or bytes that are not UTF-8
    (kept by Python as surrogates). Printed raw, a newline would split one output line
    into two, and a surrogate stops ``print`` with UnicodeEncodeError. Each is shown
    as a backslash escape instead: ``\\n``, ``\\x1b``, ``\\xff``.
    """
    out = []
    for ch in str(text):
        code = ord(ch)
        if 0xDC80 <= code <= 0xDCFF:  # an undecodable byte kept by surrogateescape
            out.append(f"\\x{code - 0xDC00:02x}")
        elif code < 0x20 or code == 0x7F or 0x80 <= code < 0xA0:
            out.append(ch.encode("unicode_escape").decode("ascii"))
        else:
            out.append(ch)
    return "".join(out)


def safe_stdout() -> None:
    """Never let a character the terminal's encoding lacks stop the command.

    Under a full UTF-8 locale Python's standard output refuses a lone surrogate. The
    checks run as ``python -I``, which ignores PYTHONIOENCODING, so the stream is told
    here to write such a character as a backslash escape instead.
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="backslashreplace")
        except (AttributeError, ValueError, OSError):
            pass



# ---------------------------------------------------------------------------
# What the command collects
# ---------------------------------------------------------------------------


@dataclass
class Outcome:
    """Everything one run found, kept as it goes so a late failure loses nothing."""

    blocking: List[str] = field(default_factory=list)
    advice: List[str] = field(default_factory=list)
    not_checked: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    def could_not_check(self, what: str, why: str) -> None:
        self.not_checked.append(_NOT_CHECKED.format(what=what, why=why.rstrip(". ")))


class Budget:
    """The command's running budget. Each part's deadline is cut to what is left."""

    def __init__(self, seconds: float, tool_deadline: float) -> None:
        self._end = time.monotonic() + max(0.0, seconds)
        self.tool_deadline = tool_deadline

    def left(self) -> float:
        return max(0.0, self._end - time.monotonic())

    def deadline(self, cap: float) -> Optional[float]:
        """The deadline for the next part, or ``None`` when the budget is spent."""
        left = self.left()
        if left < 1.0:
            return None
        return min(cap, left)


# ---------------------------------------------------------------------------
# Files
# ---------------------------------------------------------------------------

#: A changed file bigger than this is not read; it is reported as not checked.
MAX_FILE_BYTES = 20 * 1024 * 1024

_COPY_CHUNK = 1024 * 1024


def _safe_relative(entry: str) -> Optional[PurePosixPath]:
    """A repository-relative path git named, or ``None`` if it could leave the tree.

    Taken exactly as git gave it: a name may begin or end with a space.
    """
    if not entry:
        return None
    rel = PurePosixPath(entry)
    if rel.is_absolute() or ".." in rel.parts:
        return None
    return rel


def changed_files(repo: Path, start_commit: str, outcome: Optional["Outcome"] = None,
                  budget: Optional["Budget"] = None) -> List[PurePosixPath]:
    """The task's own changed files, with ``.guardkit/`` left out.

    The architecture check's helper: tracked files that differ from the start, plus
    files git is not yet tracking, read NUL-separated so no name is escaped. A name
    that could point outside the repository is reported, never silently dropped.
    Raises ``ValueError`` when git cannot answer.
    """
    out: List[PurePosixPath] = []  # names are made visible when printed (render)
    timeout = None if budget is None else max(1.0, min(60.0, budget.left() / 2))
    for entry in files_changed_since(Path(repo), start_commit, timeout=timeout):
        rel = _safe_relative(entry)
        if rel is None:
            if outcome is not None:
                outcome.could_not_check(
                    f"The changed path {entry!r}", "it does not name a file inside the "
                    "repository")
            continue
        if rel.parts[0] == ".guardkit":
            continue
        out.append(rel)
    return out


def _is_settings_file(rel: PurePosixPath) -> bool:
    return rel.name in SCANNER_SETTINGS_FILES


@dataclass
class Staged:
    """The changed files as they are now, each read once into a private folder."""

    root: Path
    files: List[PurePosixPath] = field(default_factory=list)
    #: Files over the size limit: only their first MAX_FILE_BYTES were read.
    truncated: Set[PurePosixPath] = field(default_factory=set)


def _copy_one(source: Path, target: Path) -> Tuple[bool, Optional[str]]:
    """Copy one regular file without following a link. Returns (truncated, why_not).

    Reads the file once, in chunks, and keeps at most :data:`MAX_FILE_BYTES`; a
    bigger file is cut there and ``truncated`` says so.
    """
    flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
    try:
        fd = os.open(source, flags)
    except OSError as exc:
        return False, f"it could not be opened ({exc.__class__.__name__})"
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            return False, "it is not a regular file"
        target.parent.mkdir(parents=True, exist_ok=True)
        written = 0
        truncated = False
        src = os.fdopen(fd, "rb", closefd=True)
        fd = -1  # the file object owns it now
        with src, open(target, "wb") as dst:
            while True:
                chunk = src.read(min(_COPY_CHUNK, MAX_FILE_BYTES + 1 - written))
                if not chunk:
                    break
                if written + len(chunk) > MAX_FILE_BYTES:
                    dst.write(chunk[:MAX_FILE_BYTES - written])
                    truncated = True
                    break
                dst.write(chunk)
                written += len(chunk)
        return truncated, None
    except OSError as exc:
        return False, f"it could not be read ({exc.__class__.__name__})"
    finally:
        if fd >= 0:
            os.close(fd)


def stage_changed_files(
    repo: Path, files: Iterable[PurePosixPath], root: Path, outcome: "Outcome",
    budget: Optional["Budget"] = None,
) -> Staged:
    """Read each changed file once into ``root``, reporting every one that is not read.

    Left out, each with a line saying so: the scanners' settings files (on purpose,
    so the repository cannot set them), symbolic links (never followed), anything
    reached through a linked folder and anything that is not a regular file. A file
    over :data:`MAX_FILE_BYTES` is read up to that size and reported as only partly
    read. A file the task deleted has nothing to read.
    """
    staged = Staged(root=root)
    root.mkdir(parents=True, exist_ok=True)
    real_repo = repo.resolve()
    files = list(files)
    for index, rel in enumerate(files):
        if budget is not None and budget.left() < 1.0:
            outcome.could_not_check(
                f"{len(files) - index} changed file(s)", "the check's time budget was spent")
            break
        source = repo / rel
        if _is_settings_file(rel):
            outcome.notes.append(
                f"{rel} is a scanner settings file; it is not read, and no scanner uses it.")
            continue
        try:
            info = os.lstat(source)
        except FileNotFoundError:
            continue  # deleted by the task: nothing to read
        except OSError as exc:
            outcome.could_not_check(f"The changed file {rel}",
                                    f"it could not be read ({exc.__class__.__name__})")
            continue
        if stat.S_ISLNK(info.st_mode):
            outcome.notes.append(f"{rel} is a symbolic link; it was recorded and not followed.")
            continue
        try:
            source.parent.resolve().relative_to(real_repo)
        except (ValueError, OSError):
            outcome.could_not_check(f"The changed file {rel}",
                                    "it sits behind a linked folder outside the repository")
            continue
        truncated, why_not = _copy_one(source, root / rel)
        if why_not is not None:
            outcome.could_not_check(f"The changed file {rel}", why_not)
            continue
        staged.files.append(rel)
        if truncated:
            staged.truncated.add(rel)
            outcome.could_not_check(
                f"The rest of the changed file {rel}",
                f"it is over {MAX_FILE_BYTES // (1024 * 1024)} MB, so only its first "
                f"{MAX_FILE_BYTES // (1024 * 1024)} MB were read for secrets")
    return staged


def _link_into(staged: Staged, rels: Iterable[PurePosixPath], dest: Path) -> List[PurePosixPath]:
    """Give a scanner its own folder of already-read files, without reading them again."""
    placed: List[PurePosixPath] = []
    for rel in rels:
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.link(staged.root / rel, target)
        except OSError:
            shutil.copyfile(staged.root / rel, target)
        placed.append(rel)
    return placed


def _relative_to(path: str, root: Path) -> str:
    try:
        return Path(path).resolve().relative_to(root.resolve()).as_posix()
    except (ValueError, OSError):
        return str(path)


# ---------------------------------------------------------------------------
# Running a scanner
# ---------------------------------------------------------------------------


def _scanner_environment(home: Path, tmp: Path) -> Dict[str, str]:
    """The environment a scanner runs with, built from nothing.

    ``PATH``; a private ``HOME`` and ``TMPDIR``; locale; proxy settings, so a scanner
    can reach the network the same way the build can. Nothing else, so no scanner
    setting from any environment reaches it.
    """
    from guardkit.orchestrator.project_command_env import PROXY_NAMES

    env = {
        "PATH": os.environ.get("PATH") or os.defpath,
        "HOME": str(home),
        "TMPDIR": str(tmp),
    }
    for name, value in os.environ.items():
        if name in ("LANG", "LC_ALL") or name.startswith("LC_") or name in PROXY_NAMES:
            env[name] = value
    return env


@dataclass
class ScanRun:
    returncode: Optional[int]
    stdout: str
    why_not: Optional[str] = None  # set when the scanner could not give an answer


def _run_scanner(
    argv: Sequence[str], *, cwd: Path, env: Dict[str, str], timeout: float,
) -> ScanRun:
    """Run one scanner with its own deadline. Never raises.

    The scanner runs in a process group of its own, so a deadline ends everything it
    started. Its output is kept here and never printed: only fields this module picks
    out of it are.
    """
    from guardkit.orchestrator import process_group

    try:
        done = process_group.run_project_command(
            list(argv), env=env, cwd=str(cwd), capture_output=True, text=True,
            errors="replace", timeout=timeout, stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        return ScanRun(None, "", f"did not finish within {int(round(timeout))} seconds")
    except OSError as exc:
        return ScanRun(None, "", f"could not be started ({exc.__class__.__name__})")
    return ScanRun(done.returncode, done.stdout or "")


def _executable(path: Optional[str]) -> Optional[str]:
    """Why the scanner at ``path`` cannot be run, or ``None`` if it can."""
    if not path:
        return "is not installed"
    if not os.path.isabs(path):
        return "is not named by an absolute path"
    if not (os.path.isfile(path) and os.access(path, os.X_OK)):
        return f"is not there or cannot be run ({path})"
    return None


# ---------------------------------------------------------------------------
# Check 1: secrets
# ---------------------------------------------------------------------------

SECRETS = "Secret detection"


def check_secrets(
    staged: Staged, gitleaks: Optional[str], work: Path, env: Dict[str, str],
    ignore_dir: Path, budget: Budget, outcome: Outcome,
) -> None:
    why = _executable(gitleaks)
    if why is not None:
        outcome.could_not_check(SECRETS, f"gitleaks {why}")
        return
    copy_root = work / "secrets"
    copy_root.mkdir()
    # Every changed regular file, binary or not: Gitleaks decides what it can read.
    copied = _link_into(staged, sorted(staged.files), copy_root)
    if not copied:
        outcome.notes.append("Secrets: no changed file to read.")
        return
    deadline = budget.deadline(budget.tool_deadline)
    if deadline is None:
        outcome.could_not_check(SECRETS, "the check's time budget was spent")
        return
    report = work / "gitleaks-report.json"
    argv = [
        str(gitleaks), "dir", str(copy_root),
        "--no-banner", "--no-color", "--log-level", "error",
        "--redact", "--ignore-gitleaks-allow",
        "--gitleaks-ignore-path", str(ignore_dir),
        "--report-format", "json", "--report-path", str(report),
        "--exit-code", "0",
        "--timeout", str(max(1, int(deadline))),
    ]
    run = _run_scanner(argv, cwd=work, env=env, timeout=deadline)
    if run.why_not:
        outcome.could_not_check(SECRETS, f"gitleaks {run.why_not}")
        return
    if run.returncode != 0:
        outcome.could_not_check(SECRETS, f"gitleaks stopped with exit code {run.returncode}")
        return
    try:
        findings = json.loads(report.read_text(encoding="utf-8"))
        if not isinstance(findings, list):
            raise ValueError("not a list")
    except (OSError, ValueError):
        outcome.could_not_check(SECRETS, "gitleaks wrote no report that could be read")
        return
    finally:
        try:
            report.unlink()
        except OSError:
            pass
    seen: Set[Tuple[str, int, str]] = set()
    for item in findings:
        if not isinstance(item, dict):
            continue
        rel = _relative_to(str(item.get("File") or ""), copy_root)
        line = item.get("StartLine") if isinstance(item.get("StartLine"), int) else 0
        rule = re.sub(r"[^A-Za-z0-9_.-]", "", str(item.get("RuleID") or "unknown"))[:80]
        key = (rel, line, rule)
        if key in seen:
            continue
        seen.add(key)
        outcome.blocking.append(
            f"secret -- {rel}:{line}: this line holds what looks like a secret "
            f"(kind: {rule}). The value is not shown here.")
    outcome.notes.append(
        f"Secrets: {len(copied)} changed file(s) read; {len(seen)} finding(s).")


def _settings(work: Path) -> Path:
    """The factory's empty Gitleaks ignore folder.

    From ``/opt/factory-security/`` when the image has it; otherwise made empty
    here, in this run's private folder. Never from the repository.
    """
    if FACTORY_GITLEAKS_IGNORE_DIR.is_dir():
        return FACTORY_GITLEAKS_IGNORE_DIR
    ignore_dir = work / "settings" / "gitleaks-ignore"
    ignore_dir.mkdir(parents=True, exist_ok=True)
    return ignore_dir


def render(outcome: Outcome, file_count: int) -> Tuple[int, str]:
    """See :func:`_render`; every line passes through :func:`visible` first."""
    for bucket in (outcome.blocking, outcome.advice, outcome.not_checked, outcome.notes):
        bucket[:] = [visible(line) for line in bucket]
    return _render(outcome, file_count)


def _render(outcome: Outcome, file_count: int) -> Tuple[int, str]:
    """The text to print and the exit code. What must be read goes at the END.

    The build loop hands the code generator only the last 2000 characters of a
    failing command, so the closing sentence carries the point.
    """
    head = [f"Security check: {file_count} file(s) this task changed."]
    body = [*outcome.notes, *outcome.not_checked, *outcome.advice]
    if not outcome.blocking:
        return 0, "\n".join([*head, *body, "Security check: nothing here blocks."])
    foot = [
        "",
        f"{len(outcome.blocking)} problem(s) above must be fixed. Read secrets "
        f"from the environment or a secret file; in a test, build the value at run "
        f"time instead of writing it as a literal. This check runs again on the next "
        f"turn. Problems in files this task did not touch are not listed and are not "
        f"this task's to fix.",
    ]
    return 1, "\n".join([*head, *body, "", *outcome.blocking, *foot])


def run_check(
    repo: Path, start_commit: str, *, gitleaks: Optional[str],
    budget_seconds: float = BUDGET_SECONDS, tool_deadline: float = TOOL_DEADLINE_SECONDS,
) -> Tuple[int, str]:
    """Check the files changed since ``start_commit`` for secrets. Never raises."""
    outcome = Outcome()
    file_count = 0
    try:
        budget = Budget(budget_seconds, tool_deadline)
        repo = Path(repo).resolve()
        try:
            files = changed_files(repo, start_commit, outcome, budget)
        except ValueError as exc:
            outcome.could_not_check("This change", f"{exc}".rstrip("."))
            return render(outcome, 0)
        file_count = len(files)
        if not files:
            if outcome.not_checked:
                return render(outcome, 0)
            return 0, ("Security check: this task has changed no files yet, so there was "
                       "nothing of its own to check.")
        with tempfile.TemporaryDirectory(prefix="guardkit-security-") as tmp:
            work = Path(tmp)
            home, scratch = work / "home", work / "tmp"
            home.mkdir()
            scratch.mkdir()
            env = _scanner_environment(home, scratch)
            ignore_dir = _settings(work)
            staged = stage_changed_files(repo, files, work / "changed", outcome, budget)
            try:
                check_secrets(staged, gitleaks, work, env, ignore_dir, budget, outcome)
            except Exception as exc:  # noqa: BLE001 -- the check failing is not a wall
                outcome.could_not_check(SECRETS, f"the check raised {exc.__class__.__name__}")
    except Exception as exc:  # noqa: BLE001 -- the command never raises out
        outcome.could_not_check("Part of this change", f"the check raised {exc.__class__.__name__}")
    return render(outcome, file_count)


def _version_line(text: str) -> str:
    for line in (text or "").splitlines():
        found = re.search(r"\d+(\.\d+)+\S*", line)
        if found:
            return found.group(0)[:40]
    return "version not stated"


def self_test(gitleaks: Optional[str]) -> Tuple[int, str]:
    """For the release's live check inside the image. One plain line; exit 0 when the
    isolated (-I) interpreter found the installed guardkit and Gitleaks starts.

    Scanners named on the command line are used; otherwise they are found on PATH,
    exactly as the rule builder finds them before the first turn.
    """
    import guardkit

    problems: List[str] = []
    found: List[str] = []
    where = Path(guardkit.__file__).resolve().parent
    version = guardkit.__version__
    if not sys.flags.isolated:
        problems.append("it was not run isolated (-I)")
    with tempfile.TemporaryDirectory(prefix="guardkit-security-self-test-") as tmp:
        home, scratch = Path(tmp) / "home", Path(tmp) / "tmp"
        home.mkdir()
        scratch.mkdir()
        env = _scanner_environment(home, scratch)
        for label, given, flag in ((GITLEAKS_NAME, gitleaks, "version"),):
            path = given or _find_tool(label)
            why = _executable(path)
            if why is not None:
                problems.append(f"{label} {why}")
                continue
            run = _run_scanner([str(path), flag], cwd=Path(tmp), env=env, timeout=30)
            if run.why_not or run.returncode != 0:
                problems.append(
                    f"{label} at {path} {run.why_not or f'stopped with exit code {run.returncode}'}")
                continue
            found.append(f"{label} {_version_line(run.stdout)} at {path}")
    head = f"guardkit {version} from {where}"
    if problems:
        return 1, (f"Security check self-test failed: {'; '.join(problems)} "
                   f"({head}; {'; '.join(found) or 'no scanner started'}).")
    return 0, f"Security check self-test passed: {head}, isolated; {'; '.join(found)}."


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=f"python -I -m {_MODULE}",
        description=(
            "Check the files a task changed for secrets. "
            "Exit 1 means a confirmed problem; exit 0 means none, or that a part could "
            "not be checked -- a check that cannot run must not stop a build."))
    parser.add_argument("--repo", type=Path, default=Path("."))
    parser.add_argument("--since", metavar="COMMIT",
                        help="the commit this task started from (required unless --self-test)")
    parser.add_argument("--self-test", action="store_true",
                        help="check that this isolated interpreter finds the installed "
                             "guardkit and that Gitleaks starts; print one line")
    parser.add_argument("--gitleaks", default=None, metavar="PATH")
    # Kept off the built rule; tests use them to keep the proportions while waiting less.
    parser.add_argument("--budget", type=float, default=BUDGET_SECONDS, help=argparse.SUPPRESS)
    parser.add_argument("--tool-deadline", type=float, default=TOOL_DEADLINE_SECONDS,
                        help=argparse.SUPPRESS)
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    safe_stdout()
    try:
        args = build_parser().parse_args(argv)
    except SystemExit:
        print(_NOT_CHECKED.format(what="This change",
                                  why="the security check's command line could not be read"))
        return 0
    if args.self_test:
        try:
            code, text = self_test(args.gitleaks)
        except Exception as exc:  # noqa: BLE001 -- say what failed, in one line
            code, text = 1, f"Security check self-test failed: it raised {exc.__class__.__name__}."
        print(text)
        return code
    if not args.since:
        print(_NOT_CHECKED.format(what="This change",
                                  why="the security check was not told the starting commit"))
        return 0
    try:
        code, text = run_check(
            args.repo, args.since, gitleaks=args.gitleaks,
            budget_seconds=args.budget, tool_deadline=args.tool_deadline)
    except Exception as exc:  # noqa: BLE001 -- the command never raises out
        print(_NOT_CHECKED.format(what="This change",
                                  why=f"the security check raised {exc.__class__.__name__}"))
        return 0
    print(text)
    return code


if __name__ == "__main__":   # pragma: no cover
    sys.exit(main())
