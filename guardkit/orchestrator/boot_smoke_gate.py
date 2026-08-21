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

WHICH COPY OF THE DECLARATION IS USED
-------------------------------------
The declaration file is read from the commit the build branched from, not
from the working tree. The build itself can edit files in the working tree,
and a check whose own configuration the build can rewrite is not a check.
See :mod:`guardkit.orchestrator.seam_checks` for the machinery.

One consequence: the run that first *adds* the file reads it as absent (it did
not exist at the branch point). To avoid that meaning "nothing ever runs on the
day you introduce it", this module falls back to the working-tree copy and runs
it — but a working-tree-only declaration is **never allowed to block**, whatever
the environment variable says. Blocking only ever follows from the copy that was
committed before the build started.

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
ws3-s2-seam-check-semantics-2026-07-07.md`` §4 (check 2d, the boot-smoke gate).
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
SOURCE_FEATURE_BASE = "feature_base"       # committed before the build started
SOURCE_WORKING_TREE = "working_tree_only"  # added during this build; advisory only
SOURCE_NONE = "none"                       # no declaration anywhere


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
        """Did this repository declare any start-up checks at all?"""
        return self.config_source != SOURCE_NONE

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
    """Pick the declaration copy that governs this run.

    Prefers the copy committed at the point the build branched (which the
    build cannot rewrite). Falls back to the working-tree copy so a freshly
    added declaration still runs on the day it is written — that fallback is
    marked, and never blocks.
    """
    base_ref = resolve_feature_base(worktree_path, base_branch=base_branch)
    base_config = load_feature_base_config(worktree_path, base_ref)
    if base_config.has_boot_smoke:
        return base_config, SOURCE_FEATURE_BASE

    working = load_working_tree_config(worktree_path)
    if working.has_boot_smoke:
        return working, SOURCE_WORKING_TREE

    return SeamChecksConfig(present=False), SOURCE_NONE


def run_final_wave_boot_smoke(
    worktree_path: Path,
    *,
    venv_python: Optional[str] = None,
    base_branch: str = "main",
    env: Optional[Mapping[str, str]] = None,
) -> BootSmokeGateOutcome:
    """Run every declared start-up check for the finished build.

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

    if source == SOURCE_NONE:
        return BootSmokeGateOutcome(
            result=BootSmokeResult(ran=False),
            config_source=SOURCE_NONE,
            blocking_requested=wants_blocking,
        )

    tamper: List[Dict[str, Any]] = []
    if source == SOURCE_FEATURE_BASE:
        # Only meaningful when a committed copy exists to compare against. On
        # the run that first adds the file there is nothing to differ from, and
        # reporting "this differs from the committed copy" would be nonsense.
        try:
            base_ref = resolve_feature_base(worktree_path, base_branch=base_branch)
            tamper = detect_config_tamper(worktree_path, base_ref)
        except Exception as exc:  # noqa: BLE001 — never let reporting break a build
            logger.debug("seam-checks tamper detection skipped: %s", exc)

    result = run_boot_smoke(config, Path(worktree_path), venv_python=venv_python)
    return BootSmokeGateOutcome(
        result=result,
        config_source=source,
        tamper_findings=tamper,
        blocking_requested=wants_blocking,
    )


def render_report(outcome: BootSmokeGateOutcome) -> List[str]:
    """Turn the outcome into lines a person can read without context."""
    if not outcome.declared:
        return [
            "Start-up checks: none declared. Add .guardkit/seam-checks.yaml to "
            "have GuardKit actually start this project after a build."
        ]

    lines: List[str] = []
    posture = "BLOCKING" if outcome.blocking_requested else "advisory (reports only)"
    if outcome.config_source == SOURCE_WORKING_TREE:
        posture = (
            "advisory (reports only) — the declaration was added during this "
            "build, so it cannot stop it; it governs from the next build on"
        )
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

    for finding in outcome.tamper_findings:
        lines.append(
            "  Note: .guardkit/seam-checks.yaml differs from the copy committed "
            f"before this build ({finding.get('locus', 'unknown place')}); the "
            "committed copy is the one that was used."
        )

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
