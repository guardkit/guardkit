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
It makes two checks:

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


def _safe_relative(entry: str) -> Optional[PurePosixPath]:
    """A repository-relative path git named, or ``None`` if it could leave the tree."""
    rel = PurePosixPath(entry.strip())
    if not entry.strip() or rel.is_absolute() or ".." in rel.parts:
        return None
    return rel


def changed_files(repo: Path, start_commit: str) -> List[PurePosixPath]:
    """The task's own changed files, with ``.guardkit/`` left out.

    The architecture check's helper: tracked files that differ from the start, plus
    files git is not yet tracking. Raises ``ValueError`` when git cannot answer.
    """
    from guardkit.orchestrator.arch_conformance import files_changed_since

    out: List[PurePosixPath] = []
    for entry in files_changed_since(Path(repo), start_commit):
        rel = _safe_relative(entry)
        if rel is None or rel.parts[0] == ".guardkit":
            continue
        out.append(rel)
    return out


def _is_settings_file(rel: PurePosixPath) -> bool:
    return rel.name in SCANNER_SETTINGS_FILES


def _looks_like_text(data: bytes) -> bool:
    return b"\0" not in data[:8192]


def _copy_head_files(
    repo: Path, files: Iterable[PurePosixPath], dest: Path, *, text_only: bool,
) -> Tuple[List[PurePosixPath], List[PurePosixPath]]:
    """Copy each changed file as it is in the worktree now into ``dest``.

    Leaves out the scanners' settings files, anything that is not a regular file
    (a symbolic link is never followed), and, when ``text_only``, binary files.
    Returns what was copied and the symbolic links that were skipped.
    """
    copied: List[PurePosixPath] = []
    links: List[PurePosixPath] = []
    for rel in files:
        if _is_settings_file(rel):
            continue
        source = repo / rel
        try:
            if source.is_symlink():
                links.append(rel)
                continue
            source.resolve().relative_to(repo.resolve())  # a linked folder on the way
            if not source.is_file():
                continue  # deleted by the task, or not a file
            data = source.read_bytes()
        except (OSError, ValueError):
            continue
        if text_only and not _looks_like_text(data):
            continue
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        copied.append(rel)
    return copied, links


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
    repo: Path, files: Sequence[PurePosixPath], gitleaks: Optional[str],
    work: Path, env: Dict[str, str], ignore_dir: Path, budget: Budget, outcome: Outcome,
) -> None:
    why = _executable(gitleaks)
    if why is not None:
        outcome.could_not_check(SECRETS, f"gitleaks {why}")
        return
    copy_root = work / "secrets"
    copy_root.mkdir()
    copied, links = _copy_head_files(repo, files, copy_root, text_only=True)
    for rel in links:
        outcome.notes.append(
            f"Secrets: {rel} is a symbolic link; it was recorded and not followed.")
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


@dataclass(frozen=True)
class Advisory:
    vuln_id: str
    names: frozenset  # the id and every alias OSV gives it
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


def _fixed_versions(vuln: Dict[str, Any], ecosystem: str, name: str) -> Tuple[str, ...]:
    out: Set[str] = set()
    for affected in vuln.get("affected") or []:
        pkg = affected.get("package") or {}
        if pkg.get("name") != name or (pkg.get("ecosystem") or "").split(":")[0] != ecosystem.split(":")[0]:
            continue
        for rng in affected.get("ranges") or []:
            for event in rng.get("events") or []:
                if isinstance(event, dict) and event.get("fixed"):
                    out.add(str(event["fixed"]))
    return tuple(sorted(out, key=_natural_key))


def _score(text: Any) -> Optional[float]:
    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def parse_osv_output(text: str, copy_root: Path) -> Packages:
    """OSV-Scanner's JSON as (file, ecosystem, package) -> {version: [advisory]}.

    Raises ``ValueError`` when it is not the shape OSV-Scanner writes.
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
            group_for: Dict[str, Dict[str, Any]] = {}
            for group in entry.get("groups") or []:
                for vid in group.get("ids") or []:
                    group_for[vid] = group
            advisories: List[Advisory] = []
            for vuln in entry.get("vulnerabilities") or []:
                vid = vuln.get("id")
                if not vid:
                    continue
                group = group_for.get(vid, {})
                names = {vid, *(vuln.get("aliases") or []), *(group.get("aliases") or []),
                         *(group.get("ids") or [])}
                label = str(((vuln.get("database_specific") or {}).get("severity") or "")).lower()
                if label == "moderate":
                    label = "medium"
                advisories.append(Advisory(
                    vuln_id=vid, names=frozenset(str(n) for n in names),
                    score=_score(group.get("max_severity")), label=label,
                    fixed=_fixed_versions(vuln, ecosystem, name)))
            versions = out.setdefault((rel, ecosystem, name), {})
            versions.setdefault(str(version or ""), []).extend(advisories)
    return out


def _run_osv(
    osv_scanner: str, folder: Path, config: Path, work: Path, env: Dict[str, str],
    budget: Budget, which: str,
) -> Tuple[Optional[Packages], Optional[str]]:
    """Scan ``folder``; returns the packages, or ``None`` and why not."""
    deadline = budget.deadline(budget.tool_deadline)
    if deadline is None:
        return None, "the check's time budget was spent"
    argv = [
        osv_scanner, "scan", "source", "--recursive", "--all-packages",
        "--format", "json", "--config", str(config), "--allow-no-lockfiles",
        "--no-call-analysis=all", "--verbosity", "error", str(folder),
    ]
    run = _run_scanner(argv, cwd=work, env=env, timeout=deadline)
    if run.why_not:
        return None, f"osv-scanner {run.why_not} reading the {which} versions"
    if run.returncode not in (0, 1):
        return None, (f"osv-scanner stopped with exit code {run.returncode} reading the "
                      f"{which} versions (it may not have reached the vulnerability "
                      f"database)")
    try:
        return parse_osv_output(run.stdout, folder), None
    except (ValueError, AttributeError, TypeError):
        return None, f"osv-scanner's answer for the {which} versions could not be read"


def _fixed_words(fixed: Tuple[str, ...]) -> str:
    if not fixed:
        return "OSV lists no fixed version"
    if len(fixed) == 1:
        return f"OSV lists it fixed in {fixed[0]}"
    return f"OSV lists it fixed in {', '.join(fixed[:-1])} and {fixed[-1]}"


def _advisory_names(versions: Dict[str, List[Advisory]]) -> Set[str]:
    return {n for advisories in versions.values() for a in advisories for n in a.names}


def compare_packages(head: Packages, start: Packages, outcome: Outcome) -> Set[Tuple[str, str]]:
    """Judge head against start. Returns the (ecosystem, package) pairs new in this change."""
    for (path, ecosystem, name), versions in sorted(head.items()):
        before = start.get((path, ecosystem, name))
        before_names = _advisory_names(before) if before else set()
        version_changed = before is not None and set(before) != set(versions)
        for version, advisories in sorted(versions.items()):
            reported: Set[str] = set()
            for adv in advisories:
                if adv.vuln_id in reported:
                    continue
                reported.add(adv.vuln_id)
                already = bool(adv.names & before_names)
                where = f"{name} {version} ({ecosystem}) in {path}"
                if adv.malicious and not already:
                    outcome.blocking.append(
                        f"dependency -- {where} is listed as a known malicious package "
                        f"({adv.vuln_id}). Remove it.")
                elif not already and adv.serious:
                    outcome.blocking.append(
                        f"dependency -- {where} has advisory {adv.vuln_id} "
                        f"({adv.severity_words()}); {_fixed_words(adv.fixed)}.")
                elif not already:
                    outcome.advice.append(
                        f"advice -- {where} has advisory {adv.vuln_id} "
                        f"({adv.severity_words()}); {_fixed_words(adv.fixed)}. "
                        f"This does not block.")
                elif version_changed and adv.serious:
                    fixes = _fixed_words(adv.fixed).replace("lists it fixed in", "lists fixes in")
                    outcome.blocking.append(
                        f"dependency -- this change moved {name} to {version} in {path}, "
                        f"which is still affected by {adv.vuln_id} "
                        f"({adv.severity_words()}); {fixes}.")
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
    repo: Path, start_commit: str, files: Sequence[PurePosixPath], osv_scanner: Optional[str],
    work: Path, env: Dict[str, str], config: Path, deps_dev_url: str, budget: Budget,
    outcome: Outcome,
) -> None:
    why = _executable(osv_scanner)
    if why is not None:
        outcome.could_not_check(DEPENDENCIES, f"osv-scanner {why}")
        return
    head_root = work / "deps-head"
    head_root.mkdir()
    copied, _links = _copy_head_files(repo, files, head_root, text_only=False)
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
            outcome.could_not_check(
                DEPENDENCIES,
                f"{why}, so what this change added could not be told from what was "
                f"already there")
            return
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
            files = changed_files(repo, start_commit)
        except ValueError as exc:
            outcome.could_not_check("This change", f"{exc}".rstrip("."))
            return render(outcome, 0)
        file_count = len(files)
        if not files:
            return 0, ("Security check: this task has changed no files yet, so there was "
                       "nothing of its own to check.")
        with tempfile.TemporaryDirectory(prefix="guardkit-security-") as tmp:
            work = Path(tmp)
            home, scratch = work / "home", work / "tmp"
            home.mkdir()
            scratch.mkdir()
            env = _scanner_environment(home, scratch)
            config, ignore_dir = _settings(work)
            for name, part in (
                (SECRETS, lambda: check_secrets(
                    repo, files, gitleaks, work, env, ignore_dir, budget, outcome)),
                (DEPENDENCIES, lambda: check_dependencies(
                    repo, start_commit, files, osv_scanner, work, env, config,
                    deps_dev_url, budget, outcome)),
            ):
                try:
                    part()
                except Exception as exc:  # noqa: BLE001 -- one part failing is not a wall
                    outcome.could_not_check(name, f"the check raised {exc.__class__.__name__}")
    except Exception as exc:  # noqa: BLE001 -- the command never raises out
        outcome.could_not_check("Part of this change", f"the check raised {exc.__class__.__name__}")
    return render(outcome, file_count)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=f"python -I -m {_MODULE}",
        description=(
            "Check the files a task changed for secrets and dangerous dependencies. "
            "Exit 1 means a confirmed problem; exit 0 means none, or that a part could "
            "not be checked -- a check that cannot run must not stop a build."))
    parser.add_argument("--repo", type=Path, default=Path("."))
    parser.add_argument("--since", required=True, metavar="COMMIT")
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
