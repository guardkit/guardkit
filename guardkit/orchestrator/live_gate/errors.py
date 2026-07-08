"""Shared exception types for the live-gate runner (WS2 session B3).

The load-bearing type here is :class:`LiveGateStubError`. B3 ships three seams
whose real implementations land later (F6 broker diff + reservation with B7/B8;
the read-the-image verifier is attended-only in v1 per scope Q1). Each seam has
an ``Unconfigured*`` default that **raises this error the moment it is invoked**
— never a silent success. That is the FEAT-DD4F lesson made structural: a stub
that returns a green result is a false-green generator; a stub that raises is a
loud "not wired yet" that the pre-flight records as environment/instrument
not-ready (an honest ``environment_fail`` / ``instrument_fail`` verdict), never
a pass.
"""

from __future__ import annotations


class LiveGateError(Exception):
    """Base for live-gate runner errors."""


class LiveGateStubError(LiveGateError):
    """A stubbed seam was invoked while unconfigured.

    Raised by every ``Unconfigured*`` seam default (broker diff, reservation,
    image verify). It is caught at the pre-flight boundary and recorded as a
    not-ready check — it must never be swallowed into a passing result.
    """
