"""Check each task's own change for secrets and for dangerous dependencies.

WHAT THIS IS (17 October 2026)
------------------------------
Piece 1 of the factory security design (``factory-security-check-2026-10-17`` in the
ai-transition repository). Rich asked for "a check on each change that takes
seconds". This is it: one "run this command; exit 0 is the pass" rule, built the same
way as the architecture rules check in :mod:`guardkit.orchestrator.arch_conformance`,
and carried by the machinery that already exists. :func:`build_security_rule` makes
the rule; ``snapshot_task_conformance`` freezes it beside the others before the first
turn; the existing Coach guard turns a failure into one must-fix issue on the code
generator's next turn. Nothing new enforces anything.

The command it runs is this module as a program (:func:`main`), and it looks at only
the files the task changed (``git diff --name-only <start>`` plus files git is not yet
tracking, with ``.guardkit/`` left out), using the architecture check's own helper.
Each changed file is read once (at most 20 MB); one that cannot be read is named as not
checked, never skipped silently. It makes two checks:

* **Secrets.** Gitleaks, in ``dir`` mode, over copies of just the changed text files,
  with its built-in rules, ``--redact`` and ``--ignore-gitleaks-allow``. A finding
  names the file, the line and the kind of secret, never the value.
* **Dependencies.** Only when the task changed a file OSV-Scanner reads (it decides
  which, by its own recognition). OSV-Scanner reads the head and the starting
  versions of those files, with ``--all-packages``. A package and advisory pair at
  head that was not there at the start blocks when the advisory is a known malicious
  package (``MAL-``) or scores 7.0 or more; anything lower is printed as advice. An
  advisory that was already there also blocks when this task changed that package's
  version and the advisory still applies (an upgrade that does not fix it). Every
  fixed version OSV records is listed; no versions are compared here. A package new
  in this change is looked up on deps.dev, and one first published under 30 days ago
  blocks.

NO REPOSITORY SETTINGS REACH A SCANNER
--------------------------------------
The code generator can write anything in the repository, so no scanner reads
settings from it. The copies never include ``.gitleaks.toml``, ``.gitleaksignore`` or
``osv-scanner.toml``. OSV-Scanner is given an explicit factory setting (an empty
``osv-scanner.toml``), Gitleaks' ignore-file lookup is pointed at an empty folder, and
inline ``gitleaks:allow`` comments are ignored. Both come from ``/opt/factory-security/``
in the factory image when it is there, and are made empty in a private folder when it
is not. The scanners run with an environment built from nothing (``PATH``, a private
``HOME`` and ``TMPDIR``, locale and proxy settings), so no ``GITLEAKS_CONFIG`` or
similar setting can reach them either.

The command is run as ``<absolute interpreter> -I -m ...`` with the scanners named by
absolute paths found when the rule was built, before the first turn. The worktree is
the current folder when the command runs, and a plain ``python -m`` would put it first
on the import path, so a ``guardkit.py`` the code generator wrote would be imported
instead of this checker. ``-I`` leaves the current folder, ``PYTHONPATH`` and the user's
site-packages out.

IT NEVER BECOMES A WALL
-----------------------
* No scanner installed when the rule is built: no rule, and the build is unchanged.
* A scanner missing at run time, a network that cannot be reached, a scanner that
  errors or runs out of time: that part prints "<what> was not checked: <why>.
  Nothing was checked, which is not the same as clean." and passes.
* Every part has its own deadline inside a running budget of 200 seconds, well
  inside the rule's 300-second limit, because the executor counts its own timeout as
  a failure. Confirmed findings from the parts that did finish still block.
* The top level catches everything and exits 0 unless it has a confirmed blocking
  finding.

``--self-test`` (for the release's live check inside the image) prints one line and
exits 0 when this isolated interpreter found the installed guardkit and both scanners
start.

There is no switch: the check runs whenever the image holds the tools. No project
declaration is needed, and nothing here names a language or a stack.
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
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

logger = logging.getLogger(__name__)

#: The id the rule carries in the task's rule block, and the name the code
#: generator sees at the head of the issue.
RULE_ID = "security-check"

#: The rule's outer limit. The executor treats reaching it as a failure, so the
#: command keeps its own budget well inside it.
RULE_TIMEOUT_SECONDS = 300

#: The command's own running budget, and each part's deadline inside it.
BUDGET_SECONDS = 200.0
TOOL_DEADLINE_SECONDS = 60.0
DEPS_DEV_TIMEOUT_SECONDS = 5.0
MAX_NEW_PACKAGE_LOOKUPS = 20

#: A package first published fewer days ago than this blocks.
NEW_PACKAGE_DAYS = 30

#: An advisory scoring this or more is serious.
SERIOUS_SCORE = 7.0

#: Where the factory image keeps the scanners' own settings (Forge builds them).
FACTORY_SETTINGS_DIR = Path("/opt/factory-security")
FACTORY_OSV_CONFIG = FACTORY_SETTINGS_DIR / "osv-scanner.toml"
FACTORY_GITLEAKS_IGNORE_DIR = FACTORY_SETTINGS_DIR / "gitleaks-ignore"

#: Files a scanner would read as its settings. Never copied for scanning.
SCANNER_SETTINGS_FILES = frozenset({".gitleaks.toml", ".gitleaksignore", "osv-scanner.toml"})

#: The deps.dev service, and its name for each OSV ecosystem it covers.
DEPS_DEV_URL = "https://api.deps.dev"
DEPS_DEV_SYSTEMS = {
    "npm": "NPM",
    "PyPI": "PYPI",
    "Go": "GO",
    "crates.io": "CARGO",
    "Maven": "MAVEN",
    "NuGet": "NUGET",
}

#: The scanners' names on PATH when the rule is built.
GITLEAKS_NAME = "gitleaks"
OSV_SCANNER_NAME = "osv-scanner"

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


def build_security_rule(
    worktree_path: Path,
    task_id: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """The security check to hand the build loop for this task, or ``None``.

    Shaped exactly like the rule dicts ``spec_conformance`` already runs, the same
    move :func:`guardkit.orchestrator.arch_conformance.build_arch_conformance_rule`
    makes. ``None``, and therefore nothing at all, when:

    * neither Gitleaks nor OSV-Scanner is installed (the build is then exactly what it
      was before this existed);
    * the commit this task starts from cannot be read, so the check could not be held
      to the task's own files.

    The scanners are named by the absolute paths found now, before the first turn,
    and never looked up on PATH when the command runs. Never raises.
    """
    try:
        gitleaks = _find_tool(GITLEAKS_NAME)
        osv_scanner = _find_tool(OSV_SCANNER_NAME)
        if gitleaks is None and osv_scanner is None:
            logger.debug(
                "Security check: neither %s nor %s is installed, so no check was "
                "added for %s.", GITLEAKS_NAME, OSV_SCANNER_NAME, task_id or "<task>")
            return None

        from guardkit.orchestrator.arch_conformance import starting_commit

        try:
            sha = starting_commit(Path(worktree_path))
        except ValueError as exc:
            logger.warning(
                "Security check: the commit %s starts from could not be read (%s), "
                "so no check was added. The check only ever judges the files a task "
                "changed, and without that commit it cannot tell them apart.",
                task_id or "<task>", exc)
            return None

        parts = [
            shlex.quote(sys.executable), "-I", "-m", _MODULE,
            "--repo", ".", "--since", shlex.quote(sha),
        ]
        if gitleaks is not None:
            parts += ["--gitleaks", shlex.quote(gitleaks)]
        if osv_scanner is not None:
            parts += ["--osv-scanner", shlex.quote(osv_scanner)]
        logger.info(
            "Security check: %s will be checked on the files it changes since %s "
            "(gitleaks: %s; osv-scanner: %s).",
            task_id or "<task>", sha[:12], gitleaks or "not installed",
            osv_scanner or "not installed")
        return {
            "id": RULE_ID,
            "type": "assert_command",
            "command": " ".join(parts),
            "expected_exit": 0,
            "timeout": RULE_TIMEOUT_SECONDS,
        }
    except Exception as exc:  # noqa: BLE001 -- this can never fail a build
        logger.warning(
            "Security check: working out the check for %s raised %s, so no check was "
            "added and the build is untouched.",
            task_id or "<task>", exc.__class__.__name__)
        return None


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

_TEXT_PROBE_BYTES = 8192
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
                  ) -> List[PurePosixPath]:
    """The task's own changed files, with ``.guardkit/`` left out.

    The architecture check's helper: tracked files that differ from the start, plus
    files git is not yet tracking, read NUL-separated so no name is escaped. A name
    that could point outside the repository is reported, never silently dropped.
    Raises ``ValueError`` when git cannot answer.
    """
    from guardkit.orchestrator.arch_conformance import files_changed_since

    out: List[PurePosixPath] = []
    for entry in files_changed_since(Path(repo), start_commit):
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
    text: Set[PurePosixPath] = field(default_factory=set)


def _copy_one(source: Path, target: Path) -> Tuple[Optional[bool], Optional[str]]:
    """Copy one regular file without following a link. Returns (is_text, why_not).

    Reads the file once, in chunks, and stops at :data:`MAX_FILE_BYTES`.
    """
    flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
    try:
        fd = os.open(source, flags)
    except OSError as exc:
        return None, f"it could not be opened ({exc.__class__.__name__})"
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            return None, "it is not a regular file"
        if info.st_size > MAX_FILE_BYTES:
            return None, f"it is too large (over {MAX_FILE_BYTES // (1024 * 1024)} MB)"
        target.parent.mkdir(parents=True, exist_ok=True)
        written = 0
        is_text = True
        src = os.fdopen(fd, "rb", closefd=True)
        fd = -1  # the file object owns it now
        with src, open(target, "wb") as dst:
            while True:
                chunk = src.read(_COPY_CHUNK)
                if not chunk:
                    break
                if written < _TEXT_PROBE_BYTES and b"\0" in chunk[:_TEXT_PROBE_BYTES - written]:
                    is_text = False
                written += len(chunk)
                if written > MAX_FILE_BYTES:
                    break
                dst.write(chunk)
        if written > MAX_FILE_BYTES:
            target.unlink()
            return None, f"it is too large (over {MAX_FILE_BYTES // (1024 * 1024)} MB)"
        return is_text, None
    except OSError as exc:
        return None, f"it could not be read ({exc.__class__.__name__})"
    finally:
        if fd >= 0:
            os.close(fd)


def stage_changed_files(
    repo: Path, files: Iterable[PurePosixPath], root: Path, outcome: "Outcome",
) -> Staged:
    """Read each changed file once into ``root``, reporting every one that is not read.

    Left out, each with a line saying so: the scanners' settings files (on purpose,
    so the repository cannot set them), symbolic links (never followed), anything
    reached through a linked folder, anything that is not a regular file, and files
    over :data:`MAX_FILE_BYTES`. A file the task deleted has nothing to read.
    """
    staged = Staged(root=root)
    root.mkdir(parents=True, exist_ok=True)
    real_repo = repo.resolve()
    for rel in files:
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
        is_text, why_not = _copy_one(source, root / rel)
        if why_not is not None:
            outcome.could_not_check(f"The changed file {rel}", why_not)
            continue
        staged.files.append(rel)
        if is_text:
            staged.text.add(rel)
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


def _start_version(repo: Path, start_commit: str, rel: PurePosixPath) -> Optional[bytes]:
    """The exact bytes of ``rel`` at the starting commit, or ``None`` if it was not there."""
    from guardkit.lib.project_git import run_git

    done = run_git(
        ["-C", str(repo), "cat-file", "blob", f"{start_commit}:{rel.as_posix()}"],
        text=False, timeout=30)
    if done.returncode != 0:
        return None
    return done.stdout


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
    copied = _link_into(staged, sorted(staged.text), copy_root)
    binary = len(staged.files) - len(copied)
    if binary:
        outcome.notes.append(
            f"Secrets: {binary} changed binary file(s) were not read for secrets.")
    if not copied:
        outcome.notes.append("Secrets: no changed text file to read.")
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
        f"Secrets: {len(copied)} changed text file(s) read; {len(seen)} finding(s).")


# ---------------------------------------------------------------------------
# Check 2: dependencies
# ---------------------------------------------------------------------------

DEPENDENCIES = "Dependency safety"


_LABEL_RANK = {"critical": 4, "high": 3, "medium": 2, "low": 1}


@dataclass(frozen=True)
class Advisory:
    """One OSV group: an advisory and the other ids it is listed under."""

    vuln_id: str  # the id shown first
    also: Tuple[str, ...]  # the group's other ids (e.g. a PYSEC beside a GHSA)
    names: frozenset  # every id and alias, for matching head against start
    score: Optional[float]
    label: str  # e.g. "critical"; "" when OSV gives none
    fixed: Tuple[str, ...]

    @property
    def malicious(self) -> bool:
        return any(n.startswith("MAL-") for n in self.names)

    @property
    def serious(self) -> bool:
        if self.malicious:
            return True
        if self.score is not None:
            return self.score >= SERIOUS_SCORE
        # No numeric score recorded: OSV's own label decides.
        return self.label in ("critical", "high")

    @property
    def shown(self) -> str:
        return f"{self.vuln_id} (also {', '.join(self.also)})" if self.also else self.vuln_id

    def severity_words(self) -> str:
        if self.malicious:
            return "known malicious package"
        bits = [b for b in (self.label, f"{self.score:g}" if self.score is not None else "") if b]
        return ", ".join(bits) if bits else "no severity score recorded"


#: (file, ecosystem, package) -> {version: [advisories]}
Packages = Dict[Tuple[str, str, str], Dict[str, List[Advisory]]]


def _natural_key(text: str) -> List[Any]:
    """Display order only: digits as numbers. Nothing is decided by it."""
    return [(0, int(p)) if p.isdigit() else (1, p) for p in re.split(r"(\d+)", text) if p]


def _fixed_versions(vuln: Dict[str, Any], ecosystem: str, name: str) -> Set[str]:
    """Every fixed version OSV records for this package; commit ranges (GIT) left out."""
    out: Set[str] = set()
    for affected in vuln.get("affected") or []:
        pkg = affected.get("package") or {}
        if pkg.get("name") != name or (pkg.get("ecosystem") or "").split(":")[0] != ecosystem.split(":")[0]:
            continue
        for rng in affected.get("ranges") or []:
            if str(rng.get("type") or "").upper() == "GIT":
                continue
            for event in rng.get("events") or []:
                if isinstance(event, dict) and event.get("fixed"):
                    out.add(str(event["fixed"]))
    return out


def _score(text: Any) -> Optional[float]:
    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def _primary_first(ids: Iterable[str]) -> List[str]:
    """MAL- first, then GHSA-, then the rest, each sorted: display order only."""
    def rank(i: str) -> Tuple[int, str]:
        return (0 if i.startswith("MAL-") else 1 if i.startswith("GHSA-") else 2, i)
    return sorted(set(ids), key=rank)


def _advisory(ids: List[str], members: List[Dict[str, Any]], group: Dict[str, Any],
              ecosystem: str, name: str) -> Advisory:
    names: Set[str] = set(ids) | {str(a) for a in group.get("aliases") or []}
    fixed: Set[str] = set()
    label = ""
    for vuln in members:
        names.update(str(a) for a in vuln.get("aliases") or [])
        fixed |= _fixed_versions(vuln, ecosystem, name)
        found = str(((vuln.get("database_specific") or {}).get("severity") or "")).lower()
        found = "medium" if found == "moderate" else found
        if _LABEL_RANK.get(found, 0) > _LABEL_RANK.get(label, 0):
            label = found
    ordered = _primary_first(ids)
    return Advisory(
        vuln_id=ordered[0], also=tuple(ordered[1:]), names=frozenset(names),
        score=_score(group.get("max_severity")), label=label,
        fixed=tuple(sorted(fixed, key=_natural_key)))


def parse_osv_output(text: str, copy_root: Path) -> Packages:
    """OSV-Scanner's JSON as (file, ecosystem, package) -> {version: [advisory]}.

    One advisory per OSV group, so an advisory listed under two ids (a PYSEC and a
    GHSA) is one line. Raises ``ValueError`` when it is not the shape OSV-Scanner writes.
    """
    data = json.loads(text)
    if not isinstance(data, dict) or not isinstance(data.get("results", []), list):
        raise ValueError("not OSV-Scanner's JSON")
    out: Packages = {}
    for result in data.get("results") or []:
        source = (result.get("source") or {}).get("path") or ""
        rel = _relative_to(source, copy_root)
        for entry in result.get("packages") or []:
            pkg = entry.get("package") or {}
            name, version = pkg.get("name"), pkg.get("version")
            ecosystem = pkg.get("ecosystem") or ""
            if not name:
                continue
            vulns = {str(v["id"]): v for v in entry.get("vulnerabilities") or []
                     if isinstance(v, dict) and v.get("id")}
            advisories: List[Advisory] = []
            grouped: Set[str] = set()
            for group in entry.get("groups") or []:
                ids = [str(i) for i in group.get("ids") or []]
                members = [vulns[i] for i in ids if i in vulns]
                if not members:
                    continue
                grouped.update(ids)
                advisories.append(_advisory(ids, members, group, ecosystem, name))
            for vid, vuln in vulns.items():
                if vid not in grouped:
                    advisories.append(_advisory([vid], [vuln], {}, ecosystem, name))
            versions = out.setdefault((rel, ecosystem, name), {})
            versions.setdefault(str(version or ""), []).extend(advisories)
    return out


def _run_osv(
    osv_scanner: str, folder: Path, config: Path, work: Path, env: Dict[str, str],
    budget: Budget, which: str,
) -> Tuple[Optional[Packages], Optional[str]]:
    """Scan ``folder``; returns the packages, or ``None`` and why not.

    ``--no-ignore`` so no ignore file can hide a lockfile (and none is copied in).
    """
    deadline = budget.deadline(budget.tool_deadline)
    if deadline is None:
        return None, "the check's time budget was spent"
    argv = [
        osv_scanner, "scan", "source", "--recursive", "--all-packages", "--no-ignore",
        "--format", "json", "--config", str(config), "--allow-no-lockfiles",
        "--no-call-analysis=all", "--verbosity", "error", str(folder),
    ]
    run = _run_scanner(argv, cwd=work, env=env, timeout=deadline)
    if run.why_not:
        return None, f"osv-scanner {run.why_not} reading the {which} versions"
    if run.returncode not in (0, 1):
        return None, (f"osv-scanner stopped with exit code {run.returncode} reading the "
                      f"{which} versions (it may not have reached the vulnerability "
                      f"database, or could not read a file)")
    try:
        return parse_osv_output(run.stdout, folder), None
    except (ValueError, AttributeError, TypeError, KeyError):
        return None, f"osv-scanner's answer for the {which} versions could not be read"


def _fixed_words(fixed: Tuple[str, ...], lead: str = "OSV lists it fixed in") -> str:
    if not fixed:
        return "OSV lists no fixed version"
    if len(fixed) == 1:
        return f"{lead} {fixed[0]}"
    return f"{lead} {', '.join(fixed[:-1])} and {fixed[-1]}"


def _advisory_names(versions: Dict[str, List[Advisory]]) -> Set[str]:
    return {n for advisories in versions.values() for a in advisories for n in a.names}


def compare_packages(head: Packages, start: Packages, outcome: Outcome) -> Set[Tuple[str, str]]:
    """Judge head against start. Returns the (ecosystem, package) pairs new in this change.

    * An advisory not on that package in that file at the start is new: it blocks when
      malicious or serious, and is advice otherwise.
    * An advisory already there blocks only at a version this change brought in (the
      package's version at head differs from every version at the start) and only
      when serious: an upgrade that does not fix it.
    """
    for (path, ecosystem, name), versions in sorted(head.items()):
        before = start.get((path, ecosystem, name))
        before_names = _advisory_names(before) if before else set()
        before_versions = set(before) if before else set()
        for version, advisories in sorted(versions.items()):
            reported: Set[str] = set()
            for adv in advisories:
                if adv.names & reported:
                    continue
                reported |= adv.names
                already = bool(adv.names & before_names)
                brought_in = before is not None and version not in before_versions
                where = f"{name} {version} ({ecosystem}) in {path}"
                if adv.malicious and not already:
                    outcome.blocking.append(
                        f"dependency -- {where} is listed as a known malicious package "
                        f"({adv.shown}). Remove it.")
                elif not already and adv.serious:
                    outcome.blocking.append(
                        f"dependency -- {where} has advisory {adv.shown} "
                        f"({adv.severity_words()}); {_fixed_words(adv.fixed)}.")
                elif not already:
                    outcome.advice.append(
                        f"advice -- {where} has advisory {adv.shown} "
                        f"({adv.severity_words()}); {_fixed_words(adv.fixed)}. "
                        f"This does not block.")
                elif brought_in and adv.serious:
                    kept = sorted(before_versions & set(versions), key=_natural_key)
                    if kept:
                        did = (f"this change added {name} {version} beside "
                               f"{' and '.join(kept)} in {path}")
                    else:
                        did = f"this change moved {name} to {version} in {path}"
                    outcome.blocking.append(
                        f"dependency -- {did}, which is still affected by {adv.shown} "
                        f"({adv.severity_words()}); "
                        f"{_fixed_words(adv.fixed, 'OSV lists fixes in')}.")
    head_names = {(eco, name) for (_p, eco, name) in head}
    start_names = {(eco, name) for (_p, eco, name) in start}
    return head_names - start_names


def _first_published(payload: Dict[str, Any]) -> Optional[datetime]:
    earliest: Optional[datetime] = None
    for version in payload.get("versions") or []:
        stamp = (version or {}).get("publishedAt")
        if not stamp:
            continue
        try:
            when = datetime.fromisoformat(str(stamp).replace("Z", "+00:00"))
        except ValueError:
            continue
        if when.tzinfo is None:
            when = when.replace(tzinfo=timezone.utc)
        if earliest is None or when < earliest:
            earliest = when
    return earliest


def check_new_packages(
    new: Set[Tuple[str, str]], deps_dev_url: str, budget: Budget, outcome: Outcome,
) -> None:
    """Look each package new in this change up on deps.dev; a young one blocks."""
    if not new:
        return
    looked = 0
    over_limit = 0
    unchecked: List[str] = []
    now = datetime.now(timezone.utc)
    # A fresh opener reads the proxy settings of this run (urlopen's shared one keeps
    # whatever it saw first).
    opener = urllib.request.build_opener()
    for ecosystem, name in sorted(new, key=lambda p: (p[0], p[1])):
        system = DEPS_DEV_SYSTEMS.get(ecosystem.split(":")[0])
        if system is None:
            unchecked.append(f"{name} ({ecosystem}: deps.dev does not cover it)")
            continue
        if looked >= MAX_NEW_PACKAGE_LOOKUPS:
            over_limit += 1
            continue
        deadline = budget.deadline(DEPS_DEV_TIMEOUT_SECONDS)
        if deadline is None:
            unchecked.append(f"{name} (the check's time budget was spent)")
            continue
        looked += 1
        url = (f"{deps_dev_url.rstrip('/')}/v3/systems/{system}/packages/"
               f"{urllib.parse.quote(name, safe='')}")
        try:
            with opener.open(url, timeout=deadline) as response:  # noqa: S310
                payload = json.loads(response.read(2_000_000).decode("utf-8"))
        except urllib.error.HTTPError as exc:
            reason = ("deps.dev does not know it" if exc.code == 404
                      else f"deps.dev answered {exc.code}")
            unchecked.append(f"{name} ({reason})")
            continue
        except Exception as exc:  # noqa: BLE001 -- network trouble is never a wall
            unchecked.append(f"{name} (deps.dev could not be reached: {exc.__class__.__name__})")
            continue
        first = _first_published(payload if isinstance(payload, dict) else {})
        if first is None:
            unchecked.append(f"{name} (deps.dev gave no publication date)")
            continue
        days = (now - first).days
        if now - first < timedelta(days=NEW_PACKAGE_DAYS):
            outcome.blocking.append(
                f"new package -- {name} ({ecosystem}) is new in this change, and its first "
                f"version was published {days} day(s) ago, on {first.date().isoformat()}. "
                f"Choose an established package instead.")
    if over_limit:
        outcome.could_not_check(
            f"The age of {over_limit} more new package(s)",
            f"only the first {MAX_NEW_PACKAGE_LOOKUPS} new packages are looked up")
    if unchecked:
        shown = "; ".join(unchecked[:10])
        more = f"; and {len(unchecked) - 10} more" if len(unchecked) > 10 else ""
        outcome.could_not_check(
            "The age of some new packages", f"{shown}{more}")


def check_dependencies(
    repo: Path, start_commit: str, staged: Staged, osv_scanner: Optional[str],
    work: Path, env: Dict[str, str], config: Path, deps_dev_url: str, budget: Budget,
    outcome: Outcome,
) -> None:
    why = _executable(osv_scanner)
    if why is not None:
        outcome.could_not_check(DEPENDENCIES, f"osv-scanner {why}")
        return
    head_root = work / "deps-head"
    head_root.mkdir()
    # No ignore file goes in: a .gitignore listing a lockfile must not hide it.
    copied = _link_into(staged, [r for r in staged.files if r.name != ".gitignore"], head_root)
    if not copied:
        return
    head, why = _run_osv(str(osv_scanner), head_root, config, work, env, budget, "changed")
    if head is None:
        outcome.could_not_check(DEPENDENCIES, why or "osv-scanner gave no answer")
        return
    recognised = sorted({path for (path, _e, _n) in head})
    if not recognised:
        outcome.notes.append("Dependencies: this change touched no file OSV-Scanner reads.")
        return

    start_root = work / "deps-start"
    start_root.mkdir()
    had_start = False
    for path in recognised:
        rel = _safe_relative(path)
        if rel is None or _is_settings_file(rel):
            continue
        data = _start_version(repo, start_commit, rel)
        if data is None:
            continue
        target = start_root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        had_start = True
    start: Packages = {}
    if had_start:
        scanned, why = _run_osv(str(osv_scanner), start_root, config, work, env, budget,
                                "starting")
        if scanned is None:
            # What was found at head still counts: the start is taken as holding no
            # packages, so every serious or malicious advisory at head blocks.
            outcome.notes.append(
                f"Dependencies: the starting versions could not be read ({why}), so "
                f"everything at head was judged as new to this change.")
        else:
            start = scanned
    new_packages = compare_packages(head, start, outcome)
    outcome.notes.append(
        f"Dependencies: {len(recognised)} changed file(s) OSV-Scanner reads were checked.")
    check_new_packages(new_packages, deps_dev_url, budget, outcome)


# ---------------------------------------------------------------------------
# The command
# ---------------------------------------------------------------------------


def _settings(work: Path) -> Tuple[Path, Path]:
    """The factory's OSV setting and empty Gitleaks ignore folder.

    From ``/opt/factory-security/`` when the image has them; otherwise made empty
    here, in this run's private folder. Never from the repository.
    """
    if FACTORY_OSV_CONFIG.is_file():
        config = FACTORY_OSV_CONFIG
    else:
        config = work / "settings" / "osv-scanner.toml"
        config.parent.mkdir(parents=True, exist_ok=True)
        config.write_text("", encoding="utf-8")
    if FACTORY_GITLEAKS_IGNORE_DIR.is_dir():
        ignore_dir = FACTORY_GITLEAKS_IGNORE_DIR
    else:
        ignore_dir = work / "settings" / "gitleaks-ignore"
        ignore_dir.mkdir(parents=True, exist_ok=True)
    return config, ignore_dir


def render(outcome: Outcome, file_count: int) -> Tuple[int, str]:
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
        f"{len(outcome.blocking)} problem(s) above must be fixed. Secrets: read them "
        f"from the environment or a secret file; in a test, build the value at run "
        f"time instead of writing it as a literal. Dependencies: move to a version OSV "
        f"lists as fixed for each serious advisory; this check runs again on the next "
        f"turn. Problems in files this task did not touch are not listed and are not "
        f"this task's to fix.",
    ]
    return 1, "\n".join([*head, *body, "", *outcome.blocking, *foot])


def run_check(
    repo: Path, start_commit: str, *, gitleaks: Optional[str], osv_scanner: Optional[str],
    budget_seconds: float = BUDGET_SECONDS, tool_deadline: float = TOOL_DEADLINE_SECONDS,
    deps_dev_url: str = DEPS_DEV_URL,
) -> Tuple[int, str]:
    """Run both checks on the files changed since ``start_commit``. Never raises."""
    outcome = Outcome()
    file_count = 0
    try:
        budget = Budget(budget_seconds, tool_deadline)
        repo = Path(repo).resolve()
        try:
            files = changed_files(repo, start_commit, outcome)
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
            config, ignore_dir = _settings(work)
            staged = stage_changed_files(repo, files, work / "changed", outcome)
            for name, part in (
                (SECRETS, lambda: check_secrets(
                    staged, gitleaks, work, env, ignore_dir, budget, outcome)),
                (DEPENDENCIES, lambda: check_dependencies(
                    repo, start_commit, staged, osv_scanner, work, env, config,
                    deps_dev_url, budget, outcome)),
            ):
                try:
                    part()
                except Exception as exc:  # noqa: BLE001 -- one part failing is not a wall
                    outcome.could_not_check(name, f"the check raised {exc.__class__.__name__}")
    except Exception as exc:  # noqa: BLE001 -- the command never raises out
        outcome.could_not_check("Part of this change", f"the check raised {exc.__class__.__name__}")
    return render(outcome, file_count)


def _version_line(text: str) -> str:
    for line in (text or "").splitlines():
        found = re.search(r"\d+(\.\d+)+\S*", line)
        if found:
            return found.group(0)[:40]
    return "version not stated"


def self_test(gitleaks: Optional[str], osv_scanner: Optional[str]) -> Tuple[int, str]:
    """For the release's live check inside the image. One plain line; exit 0 when the
    isolated (-I) interpreter found the installed guardkit and both scanners start.

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
        for label, given, flag in ((GITLEAKS_NAME, gitleaks, "version"),
                                   (OSV_SCANNER_NAME, osv_scanner, "--version")):
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
            "Check the files a task changed for secrets and dangerous dependencies. "
            "Exit 1 means a confirmed problem; exit 0 means none, or that a part could "
            "not be checked -- a check that cannot run must not stop a build."))
    parser.add_argument("--repo", type=Path, default=Path("."))
    parser.add_argument("--since", metavar="COMMIT",
                        help="the commit this task started from (required unless --self-test)")
    parser.add_argument("--self-test", action="store_true",
                        help="check that this isolated interpreter finds the installed "
                             "guardkit and that both scanners start; print one line")
    parser.add_argument("--gitleaks", default=None, metavar="PATH")
    parser.add_argument("--osv-scanner", default=None, metavar="PATH")
    # Kept off the built rule; tests use them to keep the proportions while waiting less.
    parser.add_argument("--budget", type=float, default=BUDGET_SECONDS, help=argparse.SUPPRESS)
    parser.add_argument("--tool-deadline", type=float, default=TOOL_DEADLINE_SECONDS,
                        help=argparse.SUPPRESS)
    parser.add_argument("--deps-dev-url", default=DEPS_DEV_URL, help=argparse.SUPPRESS)
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    try:
        args = build_parser().parse_args(argv)
    except SystemExit:
        print(_NOT_CHECKED.format(what="This change",
                                  why="the security check's command line could not be read"))
        return 0
    if args.self_test:
        try:
            code, text = self_test(args.gitleaks, args.osv_scanner)
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
            args.repo, args.since, gitleaks=args.gitleaks, osv_scanner=args.osv_scanner,
            budget_seconds=args.budget, tool_deadline=args.tool_deadline,
            deps_dev_url=args.deps_dev_url)
    except Exception as exc:  # noqa: BLE001 -- the command never raises out
        print(_NOT_CHECKED.format(what="This change",
                                  why=f"the security check raised {exc.__class__.__name__}"))
        return 0
    print(text)
    return code


if __name__ == "__main__":   # pragma: no cover
    sys.exit(main())
