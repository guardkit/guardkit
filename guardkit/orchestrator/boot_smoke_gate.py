"""Runs the repository's declared start-up checks after the last wave of a build.

PLAIN-LANGUAGE SUMMARY
----------------------
A build can finish with every test passing and still produce something that
cannot start. The usual reason is that the tests never start the real program:
they replace the parts that assemble it with stand-ins, so nobody finds out
that the assembly itself is broken until a person runs it.

This module closes that gap. A repository declares, in a small file called
``.guardkit/seam-checks.yaml``, a short list of things that must still work:
"this file must load", "this object must be creatable", "this command must
exit zero". After the last wave of an autobuild run, GuardKit runs that list
for real, in a separate process, and reports what happened.

ADVISORY FIRST — this is deliberate
-----------------------------------
By default the report is printed and **nothing else happens**. A failure does
not stop the build, does not fail the feature, and does not change any
existing behaviour. The point of the first weeks is to find out whether the
instrument says anything useful before it is allowed to stop work.

To make a failure stop the build, set the environment variable::

    GUARDKIT_BOOT_SMOKE_BLOCKING=1

When that is set and a declared check fails, the failure is attached to the
final wave as a smoke-gate failure, which the existing finalisation logic
already treats as a failed feature. Accepted values are ``1``, ``true``,
``yes`` and ``on`` (case-insensitive); anything else, including the variable
being absent, means advisory.

WHICH COPY OF THE DECLARATION IS USED — the one committed before the build
--------------------------------------------------------------------------
Only the copy of ``.guardkit/seam-checks.yaml`` that existed at the commit the
build branched from is ever read, and only the checks in THAT copy are ever
run. The build itself writes to the working files; a check whose own list of
things-to-run the build can rewrite is not a check at all. One of the kinds a
declaration may contain (``kind: command``) names a command line that is then
executed, so a build that could add entries mid-run could make GuardKit run
anything it liked.

So: an edit or an addition made during the build has **no effect on that
build**. It is reported, and it governs from the next build onwards. The
honest cost, accepted deliberately in the design spec
(``docs/design/specs/autobuild-reliability/
ws3-s2-seam-check-semantics-2026-07-07.md`` §1.3): a feature that legitimately
introduces the declaration cannot arm its own start-up checks in the same run
— a one-run lag on a new gate, versus a standing hole in every gate. See
:mod:`guardkit.orchestrator.seam_checks` for the machinery that finds the
committed copy and reports the difference.

KNOWN LIMITATION, worth knowing before trusting a red
-----------------------------------------------------
The checks run under the working copy's own Python interpreter. If that copy's
virtual environment is missing, or the project failed to install into it, then
"this file will not load" is true — but the cause is the missing installation,
not the code the build wrote. Projects that keep their code under ``src/`` are
the exposed case: nothing is importable from the repository root alone. Read a
report of ``No module named <the project>`` as an environment problem first.
This is one of the reasons the gate reports rather than blocks.

Design reference: ``docs/design/specs/autobuild-reliability/
ws3-s2-seam-check-semantics-2026-07-07.md`` §1.3 (which copy governs) and §4
(check 2d, the boot-smoke gate).
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

from guardkit.orchestrator.boot_smoke import BootSmokeResult, run_boot_smoke
from guardkit.orchestrator.seam_checks import (
    SeamChecksConfig,
    detect_config_tamper,
    load_feature_base_config,
    load_working_tree_config,
    resolve_feature_base,
)

logger = logging.getLogger(__name__)

#: Environment variable that promotes the gate from advisory to blocking.
BLOCKING_ENV_VAR = "GUARDKIT_BOOT_SMOKE_BLOCKING"

_TRUTHY = {"1", "true", "yes", "on"}

#: Where the governing declaration came from.
#: The only source whose checks are ever run: committed before the build began.
SOURCE_FEATURE_BASE = "feature_base"
#: A declaration exists, but only in files this build can write. It does NOT
#: govern this build and none of its checks are run — it applies from the next
#: build onwards.
SOURCE_ADDED_DURING_BUILD = "added_during_this_build"
#: No declaration anywhere.
SOURCE_NONE = "none"

#: Plain-English names for the places a changed declaration can be found.
_LOCUS_IN_WORDS = {
    "working_tree": "in the working files",
    "committed_wave": "in a commit this build made",
}


def blocking_requested(env: Optional[Mapping[str, str]] = None) -> bool:
    """Has the operator asked for start-up failures to stop the build?

    Reads :data:`BLOCKING_ENV_VAR`. Absent or unrecognised means no.
    """
    source = os.environ if env is None else env
    return str(source.get(BLOCKING_ENV_VAR, "")).strip().lower() in _TRUTHY


@dataclass
class BootSmokeGateOutcome:
    """What the start-up checks found, and whether it is allowed to matter."""

    result: BootSmokeResult
    config_source: str
    tamper_findings: List[Dict[str, Any]] = field(default_factory=list)
    blocking_requested: bool = False

    @property
    def declared(self) -> bool:
        """Did a declaration govern this run (and so were checks actually run)?

        A declaration that only appeared during the build does not count: it
        does not govern this build, and nothing in it was run.
        """
        return self.config_source == SOURCE_FEATURE_BASE

    @property
    def failed(self) -> bool:
        """Did a declared check actually fail (as opposed to not running)?"""
        return self.result.blocking

    @property
    def blocks_build(self) -> bool:
        """Should this outcome fail the feature?

        Only when a check really failed, the operator asked for blocking, and
        the declaration was committed before the build started.
        """
        return (
            self.failed
            and self.blocking_requested
            and self.config_source == SOURCE_FEATURE_BASE
        )


def resolve_governing_config(
    worktree_path: Path, base_branch: str = "main"
) -> tuple[SeamChecksConfig, str]:
    """Pick the declaration that governs this run — the committed copy, or none.

    Reads ``.guardkit/seam-checks.yaml`` as it stood at the commit the build
    branched from. That is the only copy that can govern, because it is the
    only copy the build cannot rewrite.

    When that copy declares no start-up checks, this returns an EMPTY
    configuration — nothing is run — and says which of the two "nothing to
    run" cases it is, so the report can explain itself:

    * :data:`SOURCE_ADDED_DURING_BUILD` — the working files DO declare checks,
      but that declaration appeared after the build started, so it applies
      from the next build on.
    * :data:`SOURCE_NONE` — no declaration anywhere.
    """
    base_ref = resolve_feature_base(worktree_path, base_branch=base_branch)
    base_config = load_feature_base_config(worktree_path, base_ref)
    if base_config.has_boot_smoke:
        return base_config, SOURCE_FEATURE_BASE

    if load_working_tree_config(worktree_path).has_boot_smoke:
        # Deliberately NOT returned for execution: an edit made during the
        # build has no effect on that build (spec §1.3).
        return SeamChecksConfig(present=False), SOURCE_ADDED_DURING_BUILD

    return SeamChecksConfig(present=False), SOURCE_NONE


def _detect_tamper_quietly(
    worktree_path: Path, base_branch: str
) -> List[Dict[str, Any]]:
    """Report any difference from the committed declaration; never raise.

    Runs whatever the outcome, including when the committed copy declares
    nothing — that is exactly the case where a build has just written a
    declaration of its own, and the operator should be told.
    """
    try:
        base_ref = resolve_feature_base(worktree_path, base_branch=base_branch)
        return detect_config_tamper(worktree_path, base_ref)
    except Exception as exc:  # noqa: BLE001 — never let reporting break a build
        logger.debug("seam-checks difference detection skipped: %s", exc)
        return []


def run_final_wave_boot_smoke(
    worktree_path: Path,
    *,
    venv_python: Optional[str] = None,
    base_branch: str = "main",
    env: Optional[Mapping[str, str]] = None,
) -> BootSmokeGateOutcome:
    """Run every start-up check the COMMITTED declaration names.

    Checks that only appear in the build's own working files are never run.

    Parameters
    ----------
    worktree_path:
        The build's working copy of the repository.
    venv_python:
        The Python interpreter belonging to that working copy. When absent the
        checks run under GuardKit's own interpreter, which may not have the
        project's dependencies installed.
    base_branch:
        The branch the build was taken from; used to find the committed copy
        of the declaration when no branch-point record exists.
    env:
        Environment mapping (for tests). Defaults to the real environment.
    """
    config, source = resolve_governing_config(worktree_path, base_branch=base_branch)
    wants_blocking = blocking_requested(env)
    tamper = _detect_tamper_quietly(Path(worktree_path), base_branch)

    if source != SOURCE_FEATURE_BASE:
        # Nothing governs this run, so nothing is executed. This is the
        # security-relevant branch: a `kind: command` entry runs a command
        # line, so a declaration the build wrote must stay inert.
        return BootSmokeGateOutcome(
            result=BootSmokeResult(ran=False),
            config_source=source,
            tamper_findings=tamper,
            blocking_requested=wants_blocking,
        )

    result = run_boot_smoke(config, Path(worktree_path), venv_python=venv_python)
    return BootSmokeGateOutcome(
        result=result,
        config_source=source,
        tamper_findings=tamper,
        blocking_requested=wants_blocking,
    )


def _difference_lines(outcome: BootSmokeGateOutcome) -> List[str]:
    """One readable line per place the declaration differs from the committed copy."""
    lines: List[str] = []
    for finding in outcome.tamper_findings:
        where = _LOCUS_IN_WORDS.get(
            str(finding.get("locus", "")), "somewhere in this build"
        )
        lines.append(
            f"  Note: .guardkit/seam-checks.yaml has been changed {where} since "
            "the commit this build started from. Changes made during a build "
            "never take effect in that build; only a change committed before "
            "the build starts does."
        )
    return lines


def render_report(outcome: BootSmokeGateOutcome) -> List[str]:
    """Turn the outcome into lines a person can read without context."""
    if outcome.config_source == SOURCE_NONE:
        return [
            "Start-up checks: none declared. Add .guardkit/seam-checks.yaml to "
            "have GuardKit actually start this project after a build."
        ]

    if outcome.config_source == SOURCE_ADDED_DURING_BUILD:
        return [
            "Start-up checks: .guardkit/seam-checks.yaml declares checks, but "
            "that declaration was not in the commit this build started from, "
            "so NOTHING in it was run. Gate configuration is changed by a "
            "person, never by the build itself; the file takes effect from the "
            "next build onwards.",
        ] + _difference_lines(outcome)

    lines: List[str] = []
    posture = "BLOCKING" if outcome.blocking_requested else "advisory (reports only)"
    lines.append(f"Start-up checks after the final wave — {posture}")

    for entry in outcome.result.entries:
        verdict = {
            "pass": "OK",
            "absent": "did not run",
            "ran_and_failed": "FAILED (started but never became usable)",
            "fail": "FAILED",
        }.get(entry.verdict, entry.verdict)
        lines.append(f"  [{verdict}] {entry.entry_id} ({entry.kind}): {entry.detail}")

    for followup in outcome.result.operator_followups:
        lines.append(f"  Needs a person: {followup}")

    lines.extend(_difference_lines(outcome))

    if outcome.failed and not outcome.blocks_build:
        lines.append(
            "  A start-up check failed. This build was NOT stopped because the "
            f"gate is advisory. Set {BLOCKING_ENV_VAR}=1 to make failures stop "
            "future builds."
        )
    elif outcome.blocks_build:
        lines.append(
            f"  A start-up check failed and {BLOCKING_ENV_VAR} is set, so this "
            "feature is marked failed."
        )
    return lines


def failure_summary(outcome: BootSmokeGateOutcome) -> str:
    """One-paragraph description of the failures, for logs and gate results."""
    bad = [
        e for e in outcome.result.entries
        if e.verdict in ("fail", "ran_and_failed")
    ]
    if not bad:
        return ""
    return "; ".join(f"{e.entry_id} ({e.kind}): {e.detail}" for e in bad)
