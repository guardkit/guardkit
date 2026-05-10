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
    """

    scenarios_passed: int = 0
    scenarios_failed: int = 0
    scenarios_pending: int = 0
    failures: List[FailureDetail] = field(default_factory=list)
    pending: List[PendingDetail] = field(default_factory=list)
    feature_files: List[str] = field(default_factory=list)
    tag: str = ""
    raw_output: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenarios_passed": self.scenarios_passed,
            "scenarios_failed": self.scenarios_failed,
            "scenarios_pending": self.scenarios_pending,
            "failures": [asdict(f) for f in self.failures],
            "pending": [asdict(p) for p in self.pending],
            "feature_files": list(self.feature_files),
            "tag": self.tag,
        }


def task_tag(task_id: str) -> str:
    """Tag convention emitted by ``/feature-spec`` and matched here."""
    return f"@task:{task_id}"


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
        proc = subprocess.run(
            argv,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
    except subprocess.TimeoutExpired as exc:
        logger.warning("pytest-bdd timed out after %ss: %s", timeout, exc)
        return _PytestInvocation(
            returncode=-1,
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

    Returns ``None`` (legitimately skipped) when:

    * No ``features/*.feature`` file exists in the worktree, or
    * No matching ``.feature`` file contains ``@task:<TASK-ID>``.

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

    # Runner-error surfacing (TASK-FIX-F584). If pytest exited with any
    # non-zero code OTHER than 5 (NO_TESTS) and produced no parsed testcases,
    # something went wrong inside pytest itself (usage error, internal error,
    # interrupt, timeout, conftest import error, ...). Returning
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


__all__ = [
    "BDDResult",
    "FailureDetail",
    "PendingDetail",
    "find_feature_files_with_tag",
    "has_pytest_bdd",
    "parse_junit_xml",
    "run_bdd_for_task",
    "task_tag",
    "_BDD_TASK_ID_ENV",
]
