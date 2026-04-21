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

# Cap raw output captured into BDDResult to keep result JSON small.
_MAX_RAW_OUTPUT_CHARS = 8_000


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
    """
    matches: List[Path] = []
    if not features_dir.is_dir():
        return matches
    for fp in sorted(features_dir.glob("*.feature")):
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

        if _classify_failure_text(full):
            pending.append(
                PendingDetail(
                    feature_file=feature_file,
                    scenario_name=name,
                    pending_step=step,
                )
            )
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
) -> _PytestInvocation:
    """Run pytest-bdd in a subprocess and capture its outputs.

    Isolated as its own function so unit tests can monkeypatch it without
    spawning real subprocesses.
    """
    argv = _build_pytest_argv(feature_files, tag, junit_xml_path)
    if python_executable:
        argv = [python_executable, "-m", *argv]
    try:
        proc = subprocess.run(
            argv,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout,
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

    Returns ``None`` (silently skipped) when any of:

    * No ``features/*.feature`` file exists in the worktree, or
    * No matching ``.feature`` file contains ``@task:<TASK-ID>``, or
    * ``pytest_bdd`` is not importable in the target environment.

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
        logger.info(
            "BDD runner: pytest-bdd not importable; skipping %d candidate "
            "feature file(s) for %s.",
            len(matching),
            task_id,
        )
        return None

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
]
