"""Task-level BDD oracle for task-work.

Runs Gherkin scenarios produced by ``/feature-spec`` as a verification oracle
during ``/task-work`` Phase 4. Activation is by **artefact presence** (a
``features/*.feature`` file containing the task's ``@task:<TASK-ID>`` tag),
never by frontmatter flag — see TASK-BDD-E8954 for rationale.

Three-state outcome model
-------------------------
A scenario can be in one of three states. Pending must NOT collapse into
failed, otherwise the first run after ``/feature-spec`` scaffolding looks
like "BDD broke the build" when nothing of the sort happened.

* **passed**  — step ran, assertion succeeded.
* **failed**  — step ran, assertion failed (real Coach-blocking bug).
* **pending** — step definition not yet implemented (scaffolding state).

Coach approval rule:
``bdd_results.scenarios_failed == 0`` (pending is tolerated).

Scope boundaries
----------------
This runner handles task-level BDD only — scenarios tagged
``@task:<TASK-ID>``. It does NOT run whole-feature ``.feature`` files
without task-scope tags; that is feature-level smoke (TASK-SMK-F703A
territory) and is intentionally out of scope here.
"""

from __future__ import annotations

import logging
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from guardkit.lib.pytest_argv import isolated_basetemp

logger = logging.getLogger(__name__)

# Marker substrings for distinguishing pending steps from real failures in
# pytest-bdd output. ``StepDefinitionNotFoundError`` is the canonical signal;
# the prose form covers older pytest-bdd releases.
_PENDING_MARKERS: Tuple[str, ...] = (
    "StepDefinitionNotFoundError",
    "Step definition is not found",
)

# pytest exit code 5 = no tests collected. Treated as "no scenarios ran" rather
# than a runner failure.
_PYTEST_EXIT_NO_TESTS = 5

# Documented pytest exit codes for runner errors. Any non-zero exit code other
# than 5 (NO_TESTS) is treated as a runner error and surfaced as a synthetic
# failure so Coach's `scenarios_failed == 0` approval rule catches it rather
# than silently approving an unrun test suite. See TASK-FIX-F584.
_PYTEST_EXIT_TEST_FAILURES = 1     # tests collected, some failed — normal path
_PYTEST_EXIT_INTERRUPTED = 2       # user/system interrupt (SIGINT, KeyboardInterrupt)
_PYTEST_EXIT_INTERNAL_ERROR = 3    # pytest internal error (usually a crash)
_PYTEST_EXIT_USAGE_ERROR = 4       # pytest usage error (e.g. "not found", bad argv)
# TASK-ABFIX-010 (W2b/L2): sentinel returncode set ONLY by the
# subprocess.TimeoutExpired handler below. A BDD-runner TIMEOUT is an ABSENT
# oracle signal (pytest produced no verdict), NOT a ran-and-failed scenario —
# synthesising a failure for it (the F584 path) coerces absence into a failure,
# which three turns running trips the context-pollution guard and kills a
# converging task. See
# ``.claude/rules/absence-must-survive-every-reconciliation-layer.md``.
_PYTEST_EXIT_TIMEOUT = -1          # our sentinel; never a real pytest exit code

# Absent-feature collection markers (TASK-AB-BDDNEUTRAL01). pytest exits 4 with
# one of these signatures when it could not COLLECT the ``.feature`` path(s) we
# passed — almost always because the project has no ``features/conftest.py``
# bridge to map ``.feature`` argv onto the glue module (or the path does not
# resolve). pytest never imported a conftest or ran a scenario, so this is an
# ABSENT BDD input, not a runner failure: per
# ``.claude/rules/absence-of-failure-is-not-success.md`` an absent oracle signal
# must be neutral, never a synthetic failure that stacks into an
# ``unrecoverable_stall`` (the FEAT-MEM-07 Error 1 "exit-4 affects every task"
# mechanism). Verified against pytest 9.0.2.
_PYTEST_UNCOLLECTABLE_MARKERS: Tuple[str, ...] = (
    "ERROR: not found:",
    "ERROR: file or directory not found:",
)

# Genuine runner/environment errors can ALSO exit 4 — most notably a conftest
# import failure. Those must STILL surface as a synthetic failure (TASK-FIX-F584),
# so a conftest-load signature vetoes the neutral mapping above. Defence in depth:
# a conftest ImportError does not print "not found:" on its own, but if any
# pytest version emitted both we keep treating it as a failure (bias toward
# surfacing on ambiguity, per the absence-of-failure remediation pattern).
_PYTEST_RUNNER_ERROR_MARKERS: Tuple[str, ...] = (
    "while loading conftest",
)

# Cap raw output captured into BDDResult to keep result JSON small.
_MAX_RAW_OUTPUT_CHARS = 8_000

# Env-var contract (TASK-AB-004): the pytest subprocess advertises the active
# task ID so the project's ``features/conftest.py`` collection bridge can pick
# the per-task glue module ``test_<slug>__<sanitised_task_id>.py`` over the
# legacy shared ``test_<slug>.py``. Solves the FEAT-FG-001 race where two
# parallel tasks both rewrote the same shared glue file. Sanitisation matches
# ``_build_pytest_argv`` (``:`` and ``-`` → ``_``); the conftest is responsible
# for applying that on the consumer side.
_BDD_TASK_ID_ENV: str = "GUARDKIT_BDD_TASK_ID"

# Cap runner-error reason snippets to keep synthetic FailureDetail compact.
_RUNNER_ERROR_REASON_MAX = 200

# Directory names excluded from recursive feature discovery. Dotdirs (anything
# whose name starts with ``.``) are filtered separately — this set covers the
# non-dot vendored dirs we do not want to walk. See TASK-FIX-F584.
_EXCLUDED_DIR_NAMES: frozenset[str] = frozenset({
    "node_modules",
    "__pycache__",
    "site-packages",
})


@dataclass
class FailureDetail:
    """A scenario whose step ran but assertion failed."""

    feature_file: str
    scenario_name: str
    failing_step: str
    reason: str


@dataclass
class PendingDetail:
    """A scenario referencing a step that has no implementation yet."""

    feature_file: str
    scenario_name: str
    pending_step: str


@dataclass
class BDDResult:
    """Three-state outcome from running task-scoped BDD scenarios.

    ``scenarios_pending`` is intentionally distinct from ``scenarios_failed``.
    See module docstring for the full rationale; collapsing the two would
    surface ``/feature-spec`` scaffolding as Coach-blocking failures.

    ``scenarios_undefined`` / ``undefined`` are populated ONLY by the
    authoring sweep (:func:`run_bdd_authoring_sweep`, TASK-AB-BDDAUTHOR01):
    in tag-scoped results they are structurally ``0`` / ``[]`` — undefined
    steps are definitionally reported as ``pending`` there, so a zero here is
    never a verdict from the tag-scoped oracle.
    """

    scenarios_passed: int = 0
    scenarios_failed: int = 0
    scenarios_pending: int = 0
    scenarios_undefined: int = 0
    failures: List[FailureDetail] = field(default_factory=list)
    pending: List[PendingDetail] = field(default_factory=list)
    undefined: List[PendingDetail] = field(default_factory=list)
    feature_files: List[str] = field(default_factory=list)
    tag: str = ""
    raw_output: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenarios_passed": self.scenarios_passed,
            "scenarios_failed": self.scenarios_failed,
            "scenarios_pending": self.scenarios_pending,
            "scenarios_undefined": self.scenarios_undefined,
            "failures": [asdict(f) for f in self.failures],
            "pending": [asdict(p) for p in self.pending],
            "undefined": [asdict(u) for u in self.undefined],
            "feature_files": list(self.feature_files),
            "tag": self.tag,
        }


def task_tag(task_id: str) -> str:
    """Tag convention emitted by ``/feature-spec`` and matched here."""
    return f"@task:{task_id}"


def is_bdd_glue_file(file_path: Any) -> bool:
    """Return True when the file appears to be pytest-bdd glue.

    Used by Coach's ``independent_tests`` path to keep pytest-bdd glue out
    of an unscoped ``pytest <files>`` invocation. Unscoped pytest collects
    every scenario in the matching ``.feature`` file, including those tagged
    for downstream peer tasks; their unbound steps surface as ``FAILED`` and
    the Coach's ``tests_passed`` / ``scenarios_failed > 0`` gates reject
    deterministically. The Player-side ``_run_bdd_oracle`` already routes
    BDD execution through :func:`run_bdd_for_task`, which is task-tag
    scoped. See TASK-FIX-CC-BDD.

    Detection is a cheap text scan for pytest-bdd v8 import signatures:
    ``from pytest_bdd import``, ``import pytest_bdd``, or
    ``pytest_bdd.scenarios(``. Returns ``False`` for missing files,
    non-``.py`` files, and files that cannot be read.
    """
    try:
        p = Path(file_path)
    except (TypeError, ValueError):
        return False
    if not p.is_file() or p.suffix != ".py":
        return False
    try:
        text = p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    return (
        "pytest_bdd.scenarios(" in text
        or "from pytest_bdd import" in text
        or "import pytest_bdd" in text
    )


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------


def find_feature_files_with_tag(features_dir: Path, tag: str) -> List[Path]:
    """Return ``.feature`` files containing the literal tag string.

    The check is a cheap text scan, not a Gherkin parse — if ``tag`` appears
    anywhere in the file we treat it as a candidate. pytest-bdd performs the
    real per-scenario filtering at runtime via the ``-m`` marker expression.

    Recursive discovery: jarvis's ``/feature-spec`` scaffold produces nested
    layouts like ``features/<feature-slug>/<feature-slug>.feature``; we walk
    the tree rather than the top level only. Dotdirs (``.venv``, ``.git``,
    ``.tox``, ...) and known vendored dirs (``node_modules``, ``__pycache__``,
    ``site-packages``) are excluded so vendored ``.feature`` files shipped
    with third-party packages are not mistaken for project scenarios.
    """
    matches: List[Path] = []
    if not features_dir.is_dir():
        return matches
    for fp in sorted(features_dir.rglob("*.feature")):
        rel_parts = fp.relative_to(features_dir).parts
        if any(
            part.startswith(".") or part in _EXCLUDED_DIR_NAMES
            for part in rel_parts
        ):
            continue
        try:
            text = fp.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            logger.debug("Could not read %s: %s", fp, exc)
            continue
        if tag in text:
            matches.append(fp)
    return matches


def has_pytest_bdd(python_executable: Optional[str] = None) -> bool:
    """Return True when ``pytest_bdd`` is importable.

    By default checks the current interpreter; pass an explicit
    ``python_executable`` to probe a different worktree environment.
    """
    if python_executable is None:
        try:
            import pytest_bdd  # noqa: F401  (probe import only)

            return True
        except ImportError:
            return False
    try:
        proc = subprocess.run(
            [python_executable, "-c", "import pytest_bdd"],
            capture_output=True,
            timeout=10,
        )
        return proc.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


# ---------------------------------------------------------------------------
# Output parsing
# ---------------------------------------------------------------------------


_FEATURE_FILE_FROM_NODEID = re.compile(r"(?P<feature>features/[^:\s]+\.feature)")

# Matches a Python traceback frame line: `  File "path", line N, in name`.
# The trailing `, in name` is optional because pytest collection errors
# sometimes omit it.
_TRACEBACK_FRAME_RE = re.compile(
    r'^\s*File "(?P<path>[^"]+)", line (?P<lineno>\d+)(?:, in .+)?$'
)


def _extract_error_reason(message: str, body: str) -> str:
    """Build a rich ``reason`` string for junit ``<error>`` nodes.

    Composes three signals so the Coach's feedback names the actual failure
    class and location instead of the generic ``"collection failure"`` prose
    pytest writes into the ``message`` attribute:

    1. The ``<error message="...">`` attribute (e.g. ``collection failure``).
    2. The inner exception class+message — typically the last non-indented
       line of the traceback body (e.g. ``ModuleNotFoundError: No module
       named 'common'``).
    3. The *last* traceback frame ``File "path", line N`` plus the source
       snippet on the line immediately after it (e.g. ``from common.x import y``).

    No exception-class special-casing — whatever the body says, we surface.
    See TASK-AB-003.
    """
    msg_text = (message or "").strip()
    body_text = body or ""

    exception_line = ""
    for line in reversed(body_text.splitlines()):
        stripped = line.strip()
        if not stripped:
            continue
        # Skip indented continuation lines (source snippets, traceback frames).
        if line.startswith((" ", "\t")):
            continue
        if stripped.startswith("Traceback "):
            continue
        exception_line = stripped
        break

    last_frame: Optional[Tuple[str, str, str]] = None
    body_lines = body_text.splitlines()
    for i, line in enumerate(body_lines):
        m = _TRACEBACK_FRAME_RE.match(line)
        if not m:
            continue
        path = m.group("path")
        lineno = m.group("lineno")
        snippet = ""
        if i + 1 < len(body_lines):
            next_line = body_lines[i + 1]
            if not _TRACEBACK_FRAME_RE.match(next_line):
                snippet = next_line.strip()
        last_frame = (path, lineno, snippet)

    parts: List[str] = []
    if msg_text and exception_line and exception_line != msg_text:
        parts.append(f"{msg_text}: {exception_line}")
    elif msg_text:
        parts.append(msg_text)
    elif exception_line:
        parts.append(exception_line)

    if last_frame is not None:
        path, lineno, snippet = last_frame
        frame_str = f"  at {path}:{lineno}"
        if snippet:
            frame_str += f" ({snippet})"
        parts.append(frame_str)

    reason = "\n".join(parts).strip()
    if not reason:
        reason = msg_text or "<empty error>"
    if len(reason) > 800:
        reason = reason[:797] + "..."
    return reason


def _classify_failure_text(message: str) -> bool:
    """Return True when the failure message indicates a pending step.

    Pending = pytest-bdd raised ``StepDefinitionNotFoundError`` (or the older
    "Step definition is not found" string). Anything else is a real assertion
    failure.
    """
    return any(marker in message for marker in _PENDING_MARKERS)


def _extract_step_from_message(message: str) -> str:
    """Best-effort extraction of the offending step text from a failure body.

    pytest-bdd renders pending-step errors with a line such as::

        StepDefinitionNotFoundError: Step definition is not found:
        When I login with valid credentials

    For real failures we fall back to the first non-empty line, truncated.
    """
    for line in message.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        # Skip the StepDefinitionNotFoundError header itself.
        if "StepDefinitionNotFoundError" in stripped:
            continue
        if stripped.startswith("Step definition is not found"):
            continue
        # First non-header line is our best candidate.
        return stripped[:200]
    return ""


def parse_junit_xml(xml_text: str) -> Tuple[int, List[FailureDetail], List[PendingDetail]]:
    """Parse pytest JUnit XML into three-state counters.

    Mirrors pytest-bdd's reporting: each scenario is a ``<testcase>``. Failure
    classification is text-based on the failure message — pending failures
    contain the ``StepDefinitionNotFoundError`` marker, real failures do not.
    """
    passed = 0
    failures: List[FailureDetail] = []
    pending: List[PendingDetail] = []

    if not xml_text.strip():
        return passed, failures, pending

    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        logger.warning("Could not parse JUnit XML: %s", exc)
        return passed, failures, pending

    for testcase in root.iter("testcase"):
        name = testcase.get("name", "")
        classname = testcase.get("classname", "")
        # pytest-bdd encodes the .feature path in the classname; fall back to
        # any matching path-like substring in the testcase id.
        feature_match = _FEATURE_FILE_FROM_NODEID.search(classname) or _FEATURE_FILE_FROM_NODEID.search(name)
        feature_file = feature_match.group("feature") if feature_match else classname

        failure_node = testcase.find("failure")
        error_node = testcase.find("error")
        problem_node = failure_node if failure_node is not None else error_node

        if problem_node is None:
            # A skipped node is neither passed nor failed; ignore it for the
            # three-state model.
            if testcase.find("skipped") is not None:
                continue
            passed += 1
            continue

        message = problem_node.get("message", "") or ""
        body = (problem_node.text or "")
        full = f"{message}\n{body}"
        step = _extract_step_from_message(full)

        # Collection errors land in `<error>` (not `<failure>`) and never
        # represent a missing step definition — they are always real
        # failures. Skip the pending classifier and use the richer
        # `_extract_error_reason` so the Coach feedback names the actual
        # exception class+message and the last traceback frame, not the
        # generic ``"collection failure"`` prose pytest writes into the
        # `<error message>` attribute. See TASK-AB-003.
        is_error_only = failure_node is None and error_node is not None

        if not is_error_only and _classify_failure_text(full):
            pending.append(
                PendingDetail(
                    feature_file=feature_file,
                    scenario_name=name,
                    pending_step=step,
                )
            )
        else:
            if is_error_only:
                reason = _extract_error_reason(message, body)
            else:
                # Trim the reason to keep BDDResult compact.
                reason = (message or body or "").strip()
                if len(reason) > 500:
                    reason = reason[:497] + "..."
            failures.append(
                FailureDetail(
                    feature_file=feature_file,
                    scenario_name=name,
                    failing_step=step,
                    reason=reason,
                )
            )

    return passed, failures, pending


# ---------------------------------------------------------------------------
# Subprocess invocation (mockable seam for tests)
# ---------------------------------------------------------------------------


@dataclass
class _PytestInvocation:
    """Captured result of a pytest subprocess call."""

    returncode: int
    stdout: str
    stderr: str
    junit_xml: str


def _synthesise_runner_error_failure(
    invocation: "_PytestInvocation",
    feature_files: Sequence[Path],
) -> FailureDetail:
    """Produce a synthetic FailureDetail for a pytest runner error.

    Invoked from :func:`run_bdd_for_task` when pytest exits with a non-zero
    code other than 5 (NO_TESTS) and no testcases were parsed — i.e. the
    runner itself failed (usage error, internal error, interrupt, timeout,
    conftest import error). Surfacing a synthetic failure drives Coach's
    ``scenarios_failed > 0`` rule so runner errors block approval rather than
    silently passing as ``(0, 0, 0, [], [])``. See TASK-FIX-F584.
    """
    snippet = (invocation.stderr or invocation.stdout or "").strip()
    if len(snippet) > _RUNNER_ERROR_REASON_MAX:
        snippet = snippet[: _RUNNER_ERROR_REASON_MAX - 3] + "..."
    reason = f"pytest_runner_error: exit={invocation.returncode}"
    if snippet:
        reason = f"{reason}; {snippet}"
    first_file = (
        str(feature_files[0]) if feature_files else "<runner>"
    )
    return FailureDetail(
        feature_file=first_file,
        scenario_name="pytest_runner_error",
        failing_step="",
        reason=reason,
    )


def _is_absent_feature_collection(invocation: "_PytestInvocation") -> bool:
    """Return True when a pytest exit 4 means "could not collect the feature".

    Distinguishes the ABSENT-input case — a tagged ``.feature`` file that pytest
    could not collect (no ``features/conftest.py`` bridge to map it to glue, or
    a path that does not resolve) — from a genuine runner error (a conftest
    ImportError, an internal pytest crash). Only the former is neutral /
    not-applicable (TASK-AB-BDDNEUTRAL01); the latter must still surface as a
    synthetic failure (TASK-FIX-F584).

    The neutral verdict is paired with a *positive-evidence* precondition (a
    pytest "not found" collection signature) rather than blanket-neutralising
    every exit 4 — that would re-open F584's silent-approval hole for conftest
    import failures. A conftest-load signature explicitly vetoes the mapping, and
    an ambiguous exit 4 with no diagnostic output is NOT treated as absent (it
    falls through to the runner-error path). See
    ``.claude/rules/absence-of-failure-is-not-success.md``.
    """
    if invocation.returncode != _PYTEST_EXIT_USAGE_ERROR:
        return False
    blob = f"{invocation.stdout or ''}\n{invocation.stderr or ''}"
    if any(marker in blob for marker in _PYTEST_RUNNER_ERROR_MARKERS):
        return False
    return any(marker in blob for marker in _PYTEST_UNCOLLECTABLE_MARKERS)


def _build_pytest_argv(
    feature_files: Sequence[Path],
    tag: str,
    junit_xml_path: Path,
) -> List[str]:
    """Construct the pytest argv used to run task-scoped scenarios.

    Mirrors the convention from the task spec:
    ``pytest --gherkin-terminal-reporter <feature_file> -m <tag>``.

    The leading ``@`` is stripped because pytest's ``-m`` marker expression
    rejects the literal ``@``. ``:`` is also normalised because pytest's
    marker parser refuses non-identifier characters; we keep the convention
    in the ``.feature`` source as ``@task:<TASK-ID>`` and translate it on
    invocation. pytest-bdd registers tag-derived markers using the same
    sanitised form.
    """
    sanitised_tag = tag.lstrip("@").replace(":", "_").replace("-", "_")
    argv: List[str] = [
        "pytest",
        "--gherkin-terminal-reporter",
        f"--junitxml={junit_xml_path}",
        "-m",
        sanitised_tag,
    ]
    argv.extend(str(p) for p in feature_files)
    return argv


def _invoke_pytest_bdd(
    feature_files: Sequence[Path],
    tag: str,
    cwd: Path,
    junit_xml_path: Path,
    timeout: int,
    python_executable: Optional[str] = None,
    task_id: Optional[str] = None,
) -> _PytestInvocation:
    """Run pytest-bdd in a subprocess and capture its outputs.

    Isolated as its own function so unit tests can monkeypatch it without
    spawning real subprocesses.

    When ``task_id`` is given, ``GUARDKIT_BDD_TASK_ID=<task_id>`` is set in
    the subprocess environment (on top of the inherited env). The project's
    ``features/conftest.py`` reads this variable to pick the per-task glue
    module ``test_<slug>__<sanitised_task_id>.py`` over the legacy shared
    ``test_<slug>.py`` (TASK-AB-004). When ``task_id`` is ``None`` the env
    is inherited unchanged so legacy single-task callers stay untouched.
    """
    argv = _build_pytest_argv(feature_files, tag, junit_xml_path)
    if python_executable:
        argv = [python_executable, "-m", *argv]
    env: Optional[Dict[str, str]] = None
    if task_id is not None:
        env = os.environ.copy()
        env[_BDD_TASK_ID_ENV] = task_id
    try:
        # TASK-AB-BASETEMP01: unique --basetemp under the system temp dir so
        # concurrent orchestrator-run pytest invocations on one host cannot
        # race the shared /tmp/pytest-of-<user> default. Unrelated to the
        # --junitxml path (which stays under the worktree's .guardkit/bdd/);
        # the dir is best-effort removed after the run.
        with isolated_basetemp(
            f"{task_id}-bdd" if task_id else "bdd", argv
        ) as basetemp_argv:
            proc = subprocess.run(
                argv + basetemp_argv,
                cwd=str(cwd),
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env,
            )
    except subprocess.TimeoutExpired as exc:
        logger.warning("pytest-bdd timed out after %ss: %s", timeout, exc)
        return _PytestInvocation(
            returncode=_PYTEST_EXIT_TIMEOUT,  # TASK-ABFIX-010 (W2b/L2): absent sentinel
            stdout=exc.stdout.decode("utf-8", "replace") if isinstance(exc.stdout, bytes) else (exc.stdout or ""),
            stderr=exc.stderr.decode("utf-8", "replace") if isinstance(exc.stderr, bytes) else (exc.stderr or ""),
            junit_xml="",
        )

    junit_xml = ""
    if junit_xml_path.is_file():
        try:
            junit_xml = junit_xml_path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            logger.debug("Could not read junit xml at %s: %s", junit_xml_path, exc)

    return _PytestInvocation(
        returncode=proc.returncode,
        stdout=proc.stdout or "",
        stderr=proc.stderr or "",
        junit_xml=junit_xml,
    )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def run_bdd_for_task(
    task_id: str,
    worktree_path: Path,
    *,
    timeout: int = 120,
    python_executable: Optional[str] = None,
    features_subdir: str = "features",
) -> Optional[BDDResult]:
    """Run task-scoped BDD scenarios for ``task_id`` in ``worktree_path``.

    Returns ``None`` (legitimately skipped / not-applicable) when:

    * No ``features/*.feature`` file exists in the worktree, or
    * No matching ``.feature`` file contains ``@task:<TASK-ID>``, or
    * pytest collected zero scenarios (exit 5), or
    * pytest could not COLLECT the tagged ``.feature`` file(s) — exit 4 with a
      "not found" signature, typically a project missing the
      ``features/conftest.py`` bridge or a ``.feature`` with no glue module yet
      (TASK-AB-BDDNEUTRAL01). This is an absent BDD input, not a failure.

    When tagged feature files DO exist but ``pytest_bdd`` is not importable
    in the target environment, returns a synthetic :class:`BDDResult` with
    ``scenarios_failed=1`` so Coach blocks rather than silently approving on
    a vacuously-true ``scenarios_failed == 0`` rule. See TASK-FIX-BDDM-1
    (and the F584 sibling for the runner-error shape).

    Returns a :class:`BDDResult` otherwise.
    """
    worktree_path = Path(worktree_path)
    features_dir = worktree_path / features_subdir
    tag = task_tag(task_id)

    matching = find_feature_files_with_tag(features_dir, tag)
    if not matching:
        logger.debug(
            "BDD runner: no .feature files in %s contain %s — skipping.",
            features_dir,
            tag,
        )
        return None

    if not has_pytest_bdd(python_executable=python_executable):
        # TASK-FIX-BDDM-1: Surface as synthetic blocker rather than silently
        # skipping. Returning None here was approved by Coach's
        # ``scenarios_failed == 0`` rule — vacuously true when no result
        # exists — so a misconfigured worktree (tagged feature files present
        # but pytest-bdd not installed) ran AutoBuild with zero BDD oracle
        # verification. Same shape as F584's ``pytest_runner_error``.
        logger.warning(
            "BDD runner: pytest-bdd not importable but %d candidate "
            "feature file(s) for %s exist; surfacing as synthetic failure "
            "so Coach blocks. Add pytest-bdd to the project's pyproject.toml.",
            len(matching),
            task_id,
        )
        reason = (
            "pytest_bdd_not_importable: tagged feature files exist for "
            f"{task_id} but pytest-bdd is not installed in the worktree "
            "environment. Add 'pytest-bdd>=8.1,<9' (or compatible) to the "
            "project's pyproject.toml dependencies and reinstall."
        )
        return BDDResult(
            scenarios_passed=0,
            scenarios_failed=1,
            scenarios_pending=0,
            failures=[FailureDetail(
                feature_file=str(matching[0].relative_to(worktree_path)),
                scenario_name="pytest_bdd_not_importable",
                failing_step="",
                reason=reason,
            )],
            pending=[],
            feature_files=[
                str(p.relative_to(worktree_path)) for p in matching
            ],
            tag=tag,
            raw_output="",
        )

    junit_xml_path = worktree_path / ".guardkit" / "bdd" / f"{task_id}_junit.xml"
    junit_xml_path.parent.mkdir(parents=True, exist_ok=True)
    if junit_xml_path.exists():
        junit_xml_path.unlink()

    invocation = _invoke_pytest_bdd(
        feature_files=matching,
        tag=tag,
        cwd=worktree_path,
        junit_xml_path=junit_xml_path,
        timeout=timeout,
        python_executable=python_executable,
        task_id=task_id,
    )

    passed, failures, pending = parse_junit_xml(invocation.junit_xml)

    # No collected tests is a legitimate skip — for example a candidate
    # .feature file mentions the tag in a comment but no scenario is tagged.
    # Treat it the same as "no matching scenarios" rather than a runner error.
    if (
        passed == 0
        and not failures
        and not pending
        and invocation.returncode == _PYTEST_EXIT_NO_TESTS
    ):
        logger.debug(
            "BDD runner: pytest collected zero scenarios for %s (exit=%s).",
            task_id,
            invocation.returncode,
        )
        return None

    # Absent-feature collection (TASK-AB-BDDNEUTRAL01). pytest exit 4 with a
    # "not found" collection signature and zero parsed testcases means the
    # tagged ``.feature`` file(s) could not be collected — almost always a
    # project missing the ``features/conftest.py`` bridge (auto-installed at
    # bootstrap, but a pre-existing repo may still lack it; the bridge also
    # declines to collect a ``.feature`` with no sibling glue module yet). This
    # is an ABSENT BDD input, NOT a failure: returning ``None`` here leaves the
    # ``bdd_results`` key out of ``task_work_results`` entirely, so Coach's
    # ``_check_bdd_results`` treats the gate as not-applicable and it never
    # contributes a failure to the gate tally or the pollution checkpoint. A
    # genuine runner error (conftest ImportError, internal crash, exit 2/3,
    # timeout, or an exit 4 with no "not found" signature) is excluded by
    # ``_is_absent_feature_collection`` and still surfaces below (TASK-FIX-F584).
    if (
        passed == 0
        and not failures
        and not pending
        and _is_absent_feature_collection(invocation)
    ):
        logger.warning(
            "BDD runner for %s: pytest exit 4 with no collectable scenarios "
            "(tagged .feature present but uncollectable — most likely a missing "
            "features/conftest.py bridge or no glue module yet). Treating as "
            "not-applicable/absent, NOT a failure. Install the bridge "
            "(auto-installed at worktree/init bootstrap) to actually run these "
            "scenarios. First %d chars: %r",
            task_id,
            _RUNNER_ERROR_REASON_MAX,
            (invocation.stderr or invocation.stdout or "")[:_RUNNER_ERROR_REASON_MAX],
        )
        return None

    # TASK-ABFIX-010 (W2b/L2): a BDD-runner TIMEOUT is an ABSENT signal, NOT a
    # failure. The subprocess timed out (TimeoutExpired → _PYTEST_EXIT_TIMEOUT
    # sentinel) so pytest produced no verdict. Return None (not-applicable /
    # absent), mirroring the absent-feature-collection path above, so the
    # timeout NEVER reaches the F584 synthetic-failure path below — synthesising
    # ``scenarios_failed >= 1`` for it would coerce an absent signal into a
    # failure, which three turns running trips the context-pollution guard and
    # kills a converging task. A hanging scenario consumed the whole budget.
    # See ``.claude/rules/absence-must-survive-every-reconciliation-layer.md``.
    if (
        passed == 0
        and not failures
        and not pending
        and invocation.returncode == _PYTEST_EXIT_TIMEOUT
    ):
        logger.warning(
            "BDD runner for %s: pytest-bdd TIMED OUT (no verdict). Treating as "
            "ABSENT signal, NOT a failure (TASK-ABFIX-010). Ensure scenarios "
            "complete within the time budget.",
            task_id,
        )
        return None

    # Runner-error surfacing (TASK-FIX-F584). If pytest exited with any
    # non-zero code OTHER than 5 (NO_TESTS) and produced no parsed testcases,
    # something went wrong inside pytest itself (usage error, internal error,
    # interrupt, conftest import error, ...). A TIMEOUT is handled above as an
    # absent signal (TASK-ABFIX-010), not here. Returning
    # ``BDDResult(0, 0, 0, [], [])`` here would be silently approved by
    # Coach's ``scenarios_failed == 0`` rule — that is strictly a silent-
    # false-approval bug. Instead, surface a synthetic FailureDetail so
    # ``scenarios_failed >= 1`` and Coach rejects with a named runner error.
    if (
        passed == 0
        and not failures
        and not pending
        and invocation.returncode not in (0, _PYTEST_EXIT_NO_TESTS)
    ):
        failures = [_synthesise_runner_error_failure(invocation, matching)]
        logger.warning(
            "BDD runner for %s: pytest exited with %d and produced no "
            "testcases; surfacing as synthetic failure. First %d chars of "
            "stderr/stdout: %r",
            task_id,
            invocation.returncode,
            _RUNNER_ERROR_REASON_MAX,
            (invocation.stderr or invocation.stdout or "")[:_RUNNER_ERROR_REASON_MAX],
        )

    raw_chunks = [invocation.stdout, invocation.stderr]
    raw_output = "\n".join(chunk for chunk in raw_chunks if chunk).strip()
    if len(raw_output) > _MAX_RAW_OUTPUT_CHARS:
        raw_output = raw_output[: _MAX_RAW_OUTPUT_CHARS - 3] + "..."

    result = BDDResult(
        scenarios_passed=passed,
        scenarios_failed=len(failures),
        scenarios_pending=len(pending),
        failures=failures,
        pending=pending,
        feature_files=[str(p.relative_to(worktree_path)) for p in matching],
        tag=tag,
        raw_output=raw_output,
    )

    logger.info(
        "BDD runner for %s: passed=%d failed=%d pending=%d (files=%s)",
        task_id,
        result.scenarios_passed,
        result.scenarios_failed,
        result.scenarios_pending,
        result.feature_files,
    )
    return result


# ---------------------------------------------------------------------------
# Authoring sweep (TASK-AB-BDDAUTHOR01)
# ---------------------------------------------------------------------------

# Sentinel scenario names whose presence in a sweep result marks a
# runner-level error (the glue was authored but could not run at all) —
# BLOCKING in the Coach gate, mirroring BDDM-1 / F584 for the sweep leg.
SWEEP_RUNNER_ERROR_SENTINELS: frozenset = frozenset(
    {"pytest_runner_error", "pytest_bdd_not_importable"}
)

# Textual binding constructs: authored glue containing one of these claims to
# make scenarios executable, so a zero-collected sweep over it is surfaced as
# a (non-blocking) advisory rather than silently absent.
_GLUE_BINDING_MARKERS = ("@scenario(", "scenarios(")


def _sanitised_task_suffix(task_id: str) -> str:
    """The per-task glue filename suffix for ``task_id``.

    Matches the conftest-template sanitisation (``:`` and ``-`` → ``_``), so
    ``TASK-XXX-002`` owns ``test_<slug>__TASK_XXX_002.py``.
    """
    return task_id.lstrip("@").replace(":", "_").replace("-", "_")


def find_per_task_glue(
    worktree_path: Path,
    task_id: str,
    features_subdir: str = "features",
) -> List[Path]:
    """Find per-task-named glue modules for ``task_id`` on disk.

    Re-arms the authoring sweep on turns where the Player does NOT touch its
    glue: activation from this turn's authored files alone is evadable — a
    Player blocked on undefined steps in turn N could clear the deterministic
    gate in turn N+1 simply by editing something else. Per-task naming
    (``test_*__<sanitised_task_id>.py``) is name-attributable to this task,
    so sweeping it every turn stays parallel-wave-safe. Mirrors
    ``find_feature_files_with_tag``'s directory exclusions.
    """
    features_dir = Path(worktree_path) / features_subdir
    if not features_dir.is_dir():
        return []
    suffix = f"__{_sanitised_task_suffix(task_id)}.py"
    matches: List[Path] = []
    try:
        for path in sorted(features_dir.rglob("test_*.py")):
            if any(
                part.startswith(".") or part in _EXCLUDED_DIR_NAMES
                for part in path.relative_to(features_dir).parts[:-1]
            ):
                continue
            if path.name.endswith(suffix):
                matches.append(path)
    except OSError:  # noqa: PERF203 — discovery is best-effort
        return matches
    return matches


def glue_owned_by_task(glue_path: Any, task_id: str, created_files: Sequence[str]) -> bool:
    """True when the authoring sweep should hold ``task_id`` to this glue.

    Ownership = the per-task naming convention (``…__<sanitised_task_id>.py``,
    per ``bdd-per-task-glue.md``) OR the file was CREATED this turn
    (``created_files`` membership — caller passes path strings from the same
    parser space as ``glue_path``, so exact string membership is correct). A
    Player that merely *edits* a pre-existing shared/legacy glue module is
    not held to that module's whole binding set — sweeping it would convert
    peer tasks' legitimately-pending scenarios into this task's blocking
    failures (the FEAT-39E1 class TASK-FIX-CC-BDD closed).
    """
    name = Path(str(glue_path)).name
    if name.endswith(f"__{_sanitised_task_suffix(task_id)}.py"):
        return True
    return str(glue_path) in set(created_files)


def _glue_has_binding_constructs(glue_files: Sequence[Path]) -> bool:
    for path in glue_files:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if any(marker in text for marker in _GLUE_BINDING_MARKERS):
            return True
    return False


def run_bdd_authoring_sweep(
    task_id: str,
    worktree_path: Path,
    glue_files: Sequence[Path],
    *,
    timeout: int = 120,
    python_executable: Optional[str] = None,
) -> Optional[BDDResult]:
    """Run the authoring sweep over the glue modules ``task_id`` authored.

    TASK-AB-BDDAUTHOR01 (R4): the step-def AUTHORING task owns zero
    ``@task:`` tags by design, so the tag-scoped oracle legitimately skips it
    and its glue is deliberately excluded from the Coach's independent pytest
    command (TASK-FIX-CC-BDD) — an undefined step sails through both legs.
    This sweep is the missing leg: pytest over the authored glue modules
    themselves (executing exactly the scenarios they bind), with NO ``-m``
    tag filter and NO ``GUARDKIT_BDD_TASK_ID``, emitting its own junit.

    Within the sweep ONLY, ``StepDefinitionNotFoundError`` testcases are
    counted under the distinct ``scenarios_undefined`` counter (blocking in
    the Coach gate); ordinary assertion failures stay in
    ``scenarios_failed`` and are ADVISORY there — pass/fail ownership of each
    scenario stays with its tag-scoped oracle, so the FEAT-39E1 cross-task
    false-red class stays closed. The tag-scoped path (``run_bdd_for_task``,
    ``_PENDING_MARKERS``, ``parse_junit_xml``) is byte-for-byte unchanged.

    Returns ``None`` (absent — no key written) when:

    * ``glue_files`` resolves to nothing on disk, or
    * pytest collected zero items from helpers-only glue (no binding
      constructs), or
    * the run TIMED OUT (TASK-ABFIX-010: a verification timeout is an absent
      signal, never a synthesised failure), or
    * pytest exit 4 with the "not found" collection signature (BDDNEUTRAL01
      semantics — e.g. a sibling deleted a shared file mid-run).

    Returns a synthetic-failure result (``pytest_bdd_not_importable`` /
    ``pytest_runner_error`` sentinel in ``failures``) when the authored glue
    exists but cannot run at all — a vacuous pass here is exactly the
    absence-of-failure hazard (BDDM-1 / F584 preserved for this leg).

    Returns an all-zero result (ran, collected zero) when the glue carries
    binding constructs yet bound nothing — surfaced as a non-blocking
    advisory by the Coach gate.
    """
    worktree_path = Path(worktree_path)
    existing = [Path(p) for p in glue_files]
    existing = [
        p if p.is_absolute() else worktree_path / p for p in existing
    ]
    existing = [p for p in existing if p.is_file()]
    if not existing:
        return None

    rel_files = []
    for p in existing:
        try:
            rel_files.append(str(p.relative_to(worktree_path)))
        except ValueError:
            rel_files.append(str(p))

    if not has_pytest_bdd(python_executable=python_executable):
        reason = (
            "pytest_bdd_not_importable: authored pytest-bdd glue exists for "
            f"{task_id} but pytest-bdd is not installed in the worktree "
            "environment. Add 'pytest-bdd>=8.1,<9' (or compatible) to the "
            "project's pyproject.toml dependencies and reinstall."
        )
        return BDDResult(
            scenarios_undefined=0,
            scenarios_failed=1,
            failures=[FailureDetail(
                feature_file=rel_files[0],
                scenario_name="pytest_bdd_not_importable",
                failing_step="",
                reason=reason,
            )],
            feature_files=rel_files,
            tag="",
        )

    junit_xml_path = (
        worktree_path / ".guardkit" / "bdd" / f"{task_id}_authoring_junit.xml"
    )
    junit_xml_path.parent.mkdir(parents=True, exist_ok=True)
    if junit_xml_path.exists():
        junit_xml_path.unlink()

    invocation = _invoke_pytest_sweep(
        glue_files=existing,
        cwd=worktree_path,
        junit_xml_path=junit_xml_path,
        timeout=timeout,
        python_executable=python_executable,
        task_id=task_id,
    )

    passed, failures, pending = parse_junit_xml(invocation.junit_xml)

    nothing_parsed = passed == 0 and not failures and not pending

    # Timeout → ABSENT (TASK-ABFIX-010): pytest produced no verdict.
    if nothing_parsed and invocation.returncode == _PYTEST_EXIT_TIMEOUT:
        logger.warning(
            "BDD authoring sweep for %s: pytest TIMED OUT (no verdict). "
            "Treating as ABSENT signal, NOT a failure.",
            task_id,
        )
        return None

    # Exit 5 (zero collected). Helpers-only glue (step defs with no binding
    # constructs — the documented ``_steps_<slug>.py`` pattern) is a
    # legitimate silent absence. Binding glue that collected zero is
    # surfaced as an all-zero result (advisory at the gate).
    if nothing_parsed and invocation.returncode == _PYTEST_EXIT_NO_TESTS:
        if _glue_has_binding_constructs(existing):
            logger.warning(
                "BDD authoring sweep for %s: authored glue carries binding "
                "constructs but pytest collected ZERO scenarios — surfacing "
                "as an advisory all-zero sweep result.",
                task_id,
            )
            return BDDResult(feature_files=rel_files, tag="")
        logger.debug(
            "BDD authoring sweep for %s: helpers-only glue collected zero "
            "items (exit 5) — absent.",
            task_id,
        )
        return None

    # Exit 4 with a "not found" collection signature → ABSENT (BDDNEUTRAL01
    # semantics; e.g. a mid-run TOCTOU deletion in a parallel wave). The
    # conftest-loading veto and ambiguous exit-4s fall through to the
    # runner-error path below (F584 preserved).
    if nothing_parsed and _is_absent_feature_collection(invocation):
        logger.warning(
            "BDD authoring sweep for %s: pytest exit 4 with a 'not found' "
            "collection signature — treating as absent, not a failure.",
            task_id,
        )
        return None

    if nothing_parsed and invocation.returncode not in (0, _PYTEST_EXIT_NO_TESTS):
        failures = [_synthesise_runner_error_failure(invocation, existing)]
        logger.warning(
            "BDD authoring sweep for %s: pytest exited %d with no testcases; "
            "surfacing as synthetic runner-error failure.",
            task_id,
            invocation.returncode,
        )

    raw_chunks = [invocation.stdout, invocation.stderr]
    raw_output = "\n".join(chunk for chunk in raw_chunks if chunk).strip()
    if len(raw_output) > _MAX_RAW_OUTPUT_CHARS:
        raw_output = raw_output[: _MAX_RAW_OUTPUT_CHARS - 3] + "..."

    # Sweep semantics: the pending classification (StepDefinitionNotFoundError)
    # IS the undefined-step signal here. The authoring task's whole job is
    # making scenarios executable, so "no step definition" is its defect —
    # counted under the distinct blocking counter, never under
    # scenarios_pending (whose non-blocking semantics belong to the
    # tag-scoped scaffolding workflow).
    result = BDDResult(
        scenarios_passed=passed,
        scenarios_failed=len(failures),
        scenarios_pending=0,
        scenarios_undefined=len(pending),
        failures=failures,
        pending=[],
        undefined=pending,
        feature_files=rel_files,
        tag="",
        raw_output=raw_output,
    )

    logger.info(
        "BDD authoring sweep for %s: passed=%d failed=%d undefined=%d (glue=%s)",
        task_id,
        result.scenarios_passed,
        result.scenarios_failed,
        result.scenarios_undefined,
        rel_files,
    )
    return result


def _invoke_pytest_sweep(
    glue_files: Sequence[Path],
    cwd: Path,
    junit_xml_path: Path,
    timeout: int,
    python_executable: Optional[str] = None,
    task_id: Optional[str] = None,
) -> _PytestInvocation:
    """Run the unfiltered authoring-sweep pytest subprocess.

    Deliberately does NOT set ``GUARDKIT_BDD_TASK_ID`` and carries no ``-m``
    tag filter: the collection targets are the authored glue modules
    themselves, so the conftest bridge's glue lookup is never involved and a
    sibling task's glue can never be collected. Isolated as its own function
    so unit tests can monkeypatch it without spawning subprocesses.
    """
    argv: List[str] = [
        "pytest",
        "--gherkin-terminal-reporter",
        f"--junitxml={junit_xml_path}",
    ]
    argv.extend(str(p) for p in glue_files)
    if python_executable:
        argv = [python_executable, "-m", *argv]
    try:
        with isolated_basetemp(
            f"{task_id}-bdd-sweep" if task_id else "bdd-sweep", argv
        ) as basetemp_argv:
            proc = subprocess.run(
                argv + basetemp_argv,
                cwd=str(cwd),
                capture_output=True,
                text=True,
                timeout=timeout,
            )
    except subprocess.TimeoutExpired as exc:
        logger.warning("Authoring sweep timed out after %ss: %s", timeout, exc)
        return _PytestInvocation(
            returncode=_PYTEST_EXIT_TIMEOUT,
            stdout=exc.stdout.decode("utf-8", "replace") if isinstance(exc.stdout, bytes) else (exc.stdout or ""),
            stderr=exc.stderr.decode("utf-8", "replace") if isinstance(exc.stderr, bytes) else (exc.stderr or ""),
            junit_xml="",
        )

    junit_xml = ""
    if junit_xml_path.is_file():
        try:
            junit_xml = junit_xml_path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            logger.debug("Could not read sweep junit xml at %s: %s", junit_xml_path, exc)

    return _PytestInvocation(
        returncode=proc.returncode,
        stdout=proc.stdout or "",
        stderr=proc.stderr or "",
        junit_xml=junit_xml,
    )


__all__ = [
    "BDDResult",
    "FailureDetail",
    "PendingDetail",
    "SWEEP_RUNNER_ERROR_SENTINELS",
    "find_feature_files_with_tag",
    "find_per_task_glue",
    "glue_owned_by_task",
    "has_pytest_bdd",
    "is_bdd_glue_file",
    "parse_junit_xml",
    "run_bdd_authoring_sweep",
    "run_bdd_for_task",
    "task_tag",
    "_BDD_TASK_ID_ENV",
]
