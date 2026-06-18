"""Declarative per-stack test-execution profiles for the AutoBuild Phase-4
deterministic runner (non-Python stacks).

TASK-AB-NPDET01. Follow-up to TASK-AB-PERTASKFG01 AC-004, which made Phase-4
test EXECUTION deterministic (a venv-pinned ``pytest`` subprocess — no LLM in
the loop, so it cannot hang) for PYTHON ONLY. This module extends the same
can't-hang property to single-task non-Python waves (.NET / JS-TS / Go) by
mapping a worktree's stack marker to a whole-suite test command and an
absence-of-failure-safe result classifier.

Design (Option B — declarative registry, adjudicated 2026-06-18). The rule
``.claude/rules/stack-plugin-architecture.md`` reserves the full ABC + loader
plugin shape for execution that is "irreducibly stack-specific" — its reference
impl (``guardkitfactory/bdd/``) exists because each stack parses a DIFFERENT
report FORMAT (JUnit XML / .trx / cucumber-json). This Phase-4 oracle has no
such surface: ``CoachValidator.run_independent_tests`` already runs any command
via ``subprocess.run(test_cmd, shell=True)`` and the authoritative verdict is
uniform ``returncode == 0``. The only stack-specific surface is DATA (marker
globs, the test command, and toolchain-absent / zero-test signal strings), so
the rule's controlling clause is "a new stack = a DATA row, not a code plugin"
+ "isolate the stack assumption in a named module" — which is this module. A new
stack is one ``StackTestProfile`` row.

Absence-of-failure safety (``.claude/rules/absence-of-failure-is-not-success.md``):
a run that did not actually exercise the deliverable's tests — a missing
toolchain, or a runner that exited cleanly having collected zero tests — is an
ABSENT signal (UNKNOWN), never a pass and never a Player test failure. Only a
ran-and-found result (returncode != 0 with a real failure, or returncode == 0
with at least one test executed) carries a verdict.

Pure stdlib — NO ``guardkitfactory`` / ``langchain`` imports, so the
safety-critical classifier tests run on the main CI suite
(``ci-tests-yml-no-guardkitfactory``), not behind a seam gate.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class StackTestProfile:
    """A non-Python stack's deterministic test-execution profile (DATA only)."""

    stack: str
    # Depth-0 (worktree-root, non-recursive) glob patterns that identify the
    # stack. Detection requires EXACTLY ONE stack to match (see
    # ``detect_stack_profile``), so a polyglot / vendored-marker repo defers to
    # the LLM specialist rather than risk mis-detection.
    marker_globs: tuple[str, ...]
    # The whole-suite test command, run via ``subprocess.run(cmd, shell=True)``
    # in the worktree. A pass/fail oracle (no coverage) — parity with the Python
    # deterministic path.
    whole_suite_command: str
    # Case-insensitive substrings that, anywhere in stdout+stderr, mean the
    # oracle did NOT produce a verdict on the deliverable's tests — a missing
    # toolchain or an UNAMBIGUOUS zero-test run. Matching one => signal_absent
    # (UNKNOWN). MUST stay narrow to toolchain-missing / zero-test-target phrases
    # only; a phrase that also appears in a genuine failure summary would
    # reclassify a real ran-and-failed result as absent. (That direction is
    # fail-toward-feedback — absent and ran-and-failed both map to a non-pass —
    # so it can never produce a false APPROVAL, but it loses the failure count.)
    absent_substrings: tuple[str, ...]
    # Return codes that mean the command never ran (127 command-not-found, 126
    # permission-denied) => signal_absent.
    absent_returncodes: frozenset[int]
    # Zero-test markers that are AMBIGUOUS: they can co-occur with a successful
    # run. ``go test ./...`` prints ``[no test files]`` for testless packages
    # even when other packages pass, so the marker counts as absent ONLY when no
    # positive "a test ran" signal (``ran_marker_regex``) is present. Empty for
    # stacks whose zero-test phrase is unambiguous (those live in
    # ``absent_substrings`` directly, e.g. dotnet "No test is available").
    ambiguous_zero_test_substrings: tuple[str, ...] = ()
    # A regex (already carrying its own (?mi) flags) matching output that proves
    # at least one test executed. Used (a) to disambiguate
    # ``ambiguous_zero_test_substrings`` and (b) as the success precondition when
    # ``success_requires_ran_marker`` is set.
    ran_marker_regex: Optional[str] = None
    # When True, a clean run (returncode == 0) with NO ``ran_marker_regex`` match
    # is treated as ABSENT (UNKNOWN), never a pass — a positive "a test actually
    # ran" precondition per ``absence-of-failure-is-not-success.md``. Needed for
    # stacks whose runner can exit 0 having executed ZERO tests with no fixed
    # phrase to match on (e.g. node: ``jest --passWithNoTests`` prints "No tests
    # found, exiting with code 0"; a bare ``echo``/``exit 0`` placeholder test
    # script prints nothing recognisable at all). The trade is intentional: an
    # exotic/custom runner whose pass output matches no marker is bounced as
    # absent (fail-toward-feedback, recoverable) rather than approved unverified.
    success_requires_ran_marker: bool = False


# A passing node run prints an unambiguous "N passing"/"N passed" count, a
# jest per-file ``PASS`` line, a TAP ``ok N``, a jasmine "N specs", or a reporter
# checkmark. Crucially NONE of these appear in the zero-test messages
# ("No tests found, exiting with code 0" / "No test files found, exiting with
# code 0"), so a clean exit with none present means NO test ran -> absent. Counts
# are anchored to ``[1-9]`` so "0 passing" / "0 passed" do not count as a ran
# test. Covers jest / mocha / vitest / jasmine / ava / tap / node:test.
_NODE_RAN_MARKER = (
    r"(?mi)("
    r"\b[1-9]\d*\s+(?:passing|passed)\b"  # mocha "3 passing"; jest/vitest "3 passed"
    r"|\b[1-9]\d*\s+tests?\s+passed\b"  # ava "3 tests passed"
    r"|\b[1-9]\d*\s+spec"  # jasmine "3 specs, 0 failures"
    r"|^\s*PASS\b"  # jest per-file "PASS src/x.test.js"
    r"|\bok\s+[1-9]\d*\b"  # TAP / node:test "ok 1 - ..."
    r"|#\s*pass\s+[1-9]"  # TAP "# pass 3"
    r"|[✓✔√]"  # reporter checkmarks ✓ ✔ √
    r")"
)


# Each row is one stack. ``detect_stack_profile`` requires a UNIQUE marker match,
# so declaration order carries no priority — it is purely cosmetic. Python is
# DELIBERATELY ABSENT: the pytest deterministic path (TASK-AB-PERTASKFG01 AC-004)
# and its absent classifier are untouched by this module.
STACK_TEST_PROFILES: tuple[StackTestProfile, ...] = (
    StackTestProfile(
        stack="dotnet",
        marker_globs=("*.sln", "*.csproj"),
        whole_suite_command="dotnet test",
        absent_substrings=(
            # Toolchain-missing: a missing binary reliably exits 127 (caught by
            # ``absent_returncodes``); the bare ": not found" substring is
            # DELIBERATELY omitted — it matched genuinely-passing output (an HTTP
            # "404: Not Found", a test title "id: not found") and false-red'd
            # correct deliverables. "command not found" (bash) stays as a backstop.
            "command not found",
            "is not recognized",
            "no .net sdks were found",
            "could not execute because the specified command or file was not found",
            "no test is available",  # zero tests discovered (unambiguous)
            "no test matches the given testcase filter",
            "msb1003",  # "Specify a project or solution file" — nothing to test
            "could not find a project",
        ),
        absent_returncodes=frozenset({126, 127}),
    ),
    StackTestProfile(
        stack="node",
        marker_globs=("package.json",),
        # Plain ``npm test`` (NOT ``--silent``, which can suppress the very
        # "missing script" / "no test specified" lines the classifier matches).
        whole_suite_command="npm test",
        absent_substrings=(
            "command not found",  # bash; missing binary also exits 127
            "missing script",  # no "test" script in package.json
            "no test specified",  # the ``npm init`` placeholder test script (exit 1)
        ),
        absent_returncodes=frozenset({126, 127}),
        # node has no reliable exit-0 zero-test PHRASE: ``jest/vitest
        # --passWithNoTests`` exit 0, and a bare ``echo``/``exit 0`` placeholder
        # prints nothing. So pair the pass with a positive "a test ran"
        # precondition — an exit-0 run matching no ran-marker is ABSENT, not a
        # pass (closes the passWithNoTests / placeholder false-green).
        ran_marker_regex=_NODE_RAN_MARKER,
        success_requires_ran_marker=True,
    ),
    StackTestProfile(
        stack="go",
        marker_globs=("go.mod",),
        whole_suite_command="go test ./...",
        absent_substrings=(
            "command not found",  # bash; missing binary also exits 127
            "no go files",
            "matched no packages",
            "go: cannot find main module",
        ),
        absent_returncodes=frozenset({126, 127}),
        # ``[no test files]`` co-occurs with passing packages in a mixed module,
        # so it is absent ONLY when no ``ok <pkg>`` pass-line is present.
        ambiguous_zero_test_substrings=("[no test files]",),
        ran_marker_regex=r"(?mi)^ok\s",
    ),
)


def _has_marker(worktree: Path, glob_pattern: str) -> bool:
    try:
        return any(worktree.glob(glob_pattern))
    except Exception:  # noqa: BLE001 — detection is best-effort, never raises
        return False


def detect_stack_profile(worktree: Path) -> Optional[StackTestProfile]:
    """Return the unique non-Python stack profile for ``worktree``, or ``None``.

    Matches each profile's marker globs at depth-0 (worktree root, non-recursive
    — consistent with the existing ``_detect_test_command`` fallback and the
    ``ProjectEnvironmentDetector`` top-level scan). Requires EXACTLY ONE stack to
    match: zero matches (Python-only / unknown) or more than one (polyglot, e.g.
    a .NET solution vendoring a root ``package.json``) both return ``None`` so
    the caller defers to the LLM specialist rather than guess a stack. Never
    raises.
    """
    try:
        matched = [
            p
            for p in STACK_TEST_PROFILES
            if any(_has_marker(worktree, g) for g in p.marker_globs)
        ]
    except Exception:  # noqa: BLE001 — detection is best-effort, never raises
        return None
    return matched[0] if len(matched) == 1 else None


def classify_absent_for_stack(
    profile: StackTestProfile, returncode: int, combined_output: str
) -> bool:
    """Return ``True`` when the run produced NO verdict on the deliverable's tests.

    Absence-of-failure-safe: a missing toolchain (``absent_returncodes`` /
    ``absent_substrings``) or a zero-test run is ABSENT (UNKNOWN), never a pass
    and never a Player test failure. The caller consults this on BOTH the
    success and failure branches (the exit-0 zero-test guard): a runner that
    exits 0 having executed zero tests would otherwise read as a false-green.

    A genuine compile/test failure matches none of these patterns, so this
    returns ``False`` and the caller classifies it as ran-and-failed
    (``returncode != 0``).
    """
    if returncode in profile.absent_returncodes:
        return True
    lowered = (combined_output or "").lower()
    if any(sub in lowered for sub in profile.absent_substrings):
        return True
    if profile.ambiguous_zero_test_substrings:
        has_zero_test = any(
            sub in lowered for sub in profile.ambiguous_zero_test_substrings
        )
        if has_zero_test:
            ran = bool(
                profile.ran_marker_regex
                and re.search(profile.ran_marker_regex, combined_output or "")
            )
            if not ran:
                return True
    # Positive ran-marker precondition (node): a clean exit (returncode == 0)
    # with NO evidence a test ran is ABSENT, never a pass. Closes the
    # ``--passWithNoTests`` / bare-placeholder exit-0 zero-test false-green.
    if profile.success_requires_ran_marker and returncode == 0:
        ran = bool(
            profile.ran_marker_regex
            and re.search(profile.ran_marker_regex, combined_output or "")
        )
        if not ran:
            return True
    return False
