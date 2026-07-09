"""Shared exception types for the QA deeper stages (WS2 session B6).

These stages — ST-05 mutation, ST-06 boundary probes, ST-13 round-trips — are
"deeper stages of the same runner, separate invocations" (scope-design §3.8).
They run **standalone**: the Coach does not consume them in v1, and they make no
autobuild behavioural change.

The load-bearing type is :class:`QAStageStubError`. Like the live-gate runner's
``Unconfigured*`` seams (B3), any probe/mutation seam whose real target is not
wired **raises this the moment it is invoked** — never a silent success. A stub
that returns a green result is a false-green generator (the FEAT-DD4F lesson);
a stub that raises is a loud "not wired yet".
"""

from __future__ import annotations


class QAStageError(Exception):
    """Base for QA deeper-stage errors (mutation / boundary / round-trip)."""


class QAStageStubError(QAStageError):
    """A probe/mutation seam was invoked while unconfigured.

    Raised by every ``Unconfigured*`` default (e.g. an unconfigured boundary
    :class:`~guardkit.orchestrator.qa_stages.boundary.ProbeTarget`). It must
    never be swallowed into a passing result.
    """


class MutationError(QAStageError):
    """A mutation campaign could not run meaningfully.

    Raised when the pre-mutation baseline is not green — a surviving mutant is
    only meaningful against a green baseline, so an un-green baseline is a loud
    "cannot assess", never a silent "no coverage holes" (absence-of-failure).
    """


class BoundaryProbeError(QAStageError):
    """A boundary-probe run could not be assembled or executed."""
