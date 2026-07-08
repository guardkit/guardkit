"""F3 · leak sweep (LPA-05) — WS2 session B3.

Generalizes ``lpa-platform-poc/qa/gates/gate_phase6_sweep.py`` (B0 rescue) over
the F3 ``LeakSweepManifest``: the rescued script's hard-coded ``MOCK_NAMES`` +
``DONOR_PAGES``/``ATTORNEY_PAGES`` scope map is now data (the F3 manifest); this
module is the engine that reads it.

The design splits cleanly along the DF-015 deterministic line:

- :func:`check_text_against_deny` is PURE — given the text of a claimed-real
  region and the deny patterns, it returns the leaks. No I/O, fully
  offline-testable.
- :class:`PageTextFetcher` is the LIVE seam — it returns the claimed-real
  region's text for a (persona, surface). DOM scoping (``wired_selector`` +
  ``allowed_mock_regions``) lives here, where Playwright lives, not in the pure
  core. The default :class:`UnconfiguredPageTextFetcher` raises loudly (v1 has
  no live browser wired) — never a silent empty string, which would sweep
  nothing and pass vacuously.

Deny-pattern semantics (documented so the mapping is not silent):

  identity_strings   substring containment (a mock name appearing anywhere)
  count_patterns     substring containment (a fabricated count like "of 156")
  url_patterns       regex search (a placeholder/mock URL shape)
  badge_patterns     regex search, per line (a bare numeric badge like "11")

``surface.extra_deny`` entries are treated as additional identity substrings for
that one surface (the F3 field is a free string list scoped to the surface).
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import List

from guardkit.qa.formats import LeakSweepManifest, Surface
from guardkit.qa.formats.gate_registry import SweepResult
from guardkit.qa.formats.leak_sweep import DenyPatterns, Persona

from guardkit.orchestrator.live_gate.errors import LiveGateStubError


def check_text_against_deny(
    text: str,
    deny: DenyPatterns,
    extra_deny: List[str],
    *,
    context: str = "",
) -> List[str]:
    """Return every deny-pattern hit in ``text`` (pure; the sweep's heart).

    ``context`` is a human label (e.g. "donor /insights") prefixed onto each
    leak string so the envelope's ``leaks`` list is self-describing.
    """
    prefix = f"{context}: " if context else ""
    leaks: List[str] = []

    for needle in list(deny.identity_strings) + list(extra_deny):
        if needle and needle in text:
            leaks.append(f"{prefix}mock identity {needle!r}")

    for needle in deny.count_patterns:
        if needle and needle in text:
            leaks.append(f"{prefix}fabricated count {needle!r}")

    for pattern in deny.url_patterns:
        try:
            if pattern and re.search(pattern, text):
                leaks.append(f"{prefix}placeholder url matching {pattern!r}")
        except re.error:
            # A malformed pattern is a manifest bug, not a leak — but it must be
            # loud, not silently skipped (it would sweep for nothing).
            leaks.append(f"{prefix}INVALID url_pattern {pattern!r} (fix the F3 manifest)")

    for pattern in deny.badge_patterns:
        try:
            if pattern and re.search(pattern, text, re.MULTILINE):
                leaks.append(f"{prefix}fake badge matching {pattern!r}")
        except re.error:
            leaks.append(f"{prefix}INVALID badge_pattern {pattern!r} (fix the F3 manifest)")

    return leaks


class PageTextFetcher(ABC):
    """Live seam: return the claimed-real region text for a (persona, surface).

    For a ``scope: scoped`` surface the implementation returns ONLY the
    ``wired_selector`` region's text (excluding ``allowed_mock_regions``); for a
    ``full_page`` surface it returns the whole page body. This is where the DOM
    lives — the pure sweep never touches a browser.
    """

    @abstractmethod
    def fetch(self, persona: Persona, surface: Surface) -> str:
        """Return the claimed-real text for this persona on this surface."""


class UnconfiguredPageTextFetcher(PageTextFetcher):
    """Default fetcher: raises loudly (no live browser wired in v1).

    Wiring a fetcher that returned ``""`` here would make every sweep pass
    vacuously (nothing to match against) — a textbook false-green. Raising means
    the runner records the sweep as un-runnable and the verdict is
    ``environment_fail``, never ``pass``.
    """

    def fetch(self, persona: Persona, surface: Surface) -> str:
        raise LiveGateStubError(
            "PageTextFetcher is not configured: the leak sweep needs a live "
            "page-text source (Playwright/browser) to read claimed-real "
            f"surfaces (asked for persona {persona.id!r} on {surface.route!r}). "
            "The live fetcher lands with the deploy stage (B8); until then the "
            "sweep cannot run and the run is environment_fail, not pass."
        )


def run_sweep(
    manifest: LeakSweepManifest,
    fetcher: PageTextFetcher,
) -> SweepResult:
    """Run the F3 leak sweep: every claimed-real surface, as every persona.

    Raises:
        LiveGateStubError: propagated from an unconfigured fetcher. The runner
            only calls ``run_sweep`` on the live path (pre-flight green); on the
            environment_fail short-circuit it never reaches here.
    """
    leaks: List[str] = []
    surfaces_checked = 0
    for persona in manifest.personas:
        for surface in manifest.surfaces:
            text = fetcher.fetch(persona, surface)
            surfaces_checked += 1
            context = f"{persona.id} {surface.route}"
            leaks.extend(
                check_text_against_deny(
                    text, manifest.deny, surface.extra_deny, context=context
                )
            )
    return SweepResult(surfaces_checked=surfaces_checked, leaks=leaks)
