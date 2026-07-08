"""F3 leak sweep (WS2 B3): pure deny-matching + the loud unconfigured fetcher."""

from __future__ import annotations

import pytest

from guardkit.orchestrator.live_gate.errors import LiveGateStubError
from guardkit.orchestrator.live_gate.sweep import (
    PageTextFetcher,
    UnconfiguredPageTextFetcher,
    check_text_against_deny,
    run_sweep,
)
from guardkit.qa.formats.leak_sweep import (
    DenyPatterns,
    LeakSweepManifest,
    Persona,
    Surface,
)


def _deny(**kw) -> DenyPatterns:
    base = dict(identity_strings=["Paul Jones"], count_patterns=["of 156"], badge_patterns=[r"^\d+$"])
    base.update(kw)
    return DenyPatterns(**base)


class TestCheckTextAgainstDeny:
    def test_clean_text_no_leaks(self):
        assert check_text_against_deny("Donald Donor · 3 real accounts", _deny(), []) == []

    def test_identity_leak(self):
        leaks = check_text_against_deny("signed in as Paul Jones", _deny(), [], context="donor /x")
        assert leaks == ["donor /x: mock identity 'Paul Jones'"]

    def test_count_leak(self):
        leaks = check_text_against_deny("showing 3 of 156 transactions", _deny(), [])
        assert any("fabricated count 'of 156'" in leak for leak in leaks)

    def test_badge_regex_multiline(self):
        leaks = check_text_against_deny("Notifications\n11\nMenu", _deny(), [])
        assert any("fake badge" in leak for leak in leaks)

    def test_extra_deny_is_surface_scoped_identity(self):
        leaks = check_text_against_deny("secret Athena mock", _deny(identity_strings=[]), ["Athena mock"])
        assert any("mock identity 'Athena mock'" in leak for leak in leaks)

    def test_invalid_url_pattern_is_loud_not_silent(self):
        leaks = check_text_against_deny("x", _deny(url_patterns=["([unclosed"]), [])
        assert any("INVALID url_pattern" in leak for leak in leaks)


class FakeFetcher(PageTextFetcher):
    """Signature-binding fake returning canned text per route."""

    def __init__(self, text_by_route):
        self._by_route = text_by_route
        self.calls = []

    def fetch(self, persona, surface):
        self.calls.append((persona.id, surface.route))
        return self._by_route.get(surface.route, "")


def _manifest() -> LeakSweepManifest:
    return LeakSweepManifest(
        format_version="1.0",
        personas=[Persona(id="donor", login_role="donor", credentials_ref="R")],
        deny=_deny(),
        surfaces=[
            Surface(route="/insights", claimed_by="F", scope="full_page"),
            Surface(route="/accounts", claimed_by="F", scope="full_page"),
        ],
    )


class TestRunSweep:
    def test_clean_sweep(self):
        fetcher = FakeFetcher({"/insights": "Donald Donor", "/accounts": "real bank"})
        res = run_sweep(_manifest(), fetcher)
        assert res.surfaces_checked == 2
        assert res.leaks == []

    def test_leaks_surface_with_context(self):
        fetcher = FakeFetcher({"/insights": "Paul Jones here", "/accounts": "clean"})
        res = run_sweep(_manifest(), fetcher)
        assert res.surfaces_checked == 2
        assert any("donor /insights" in leak and "Paul Jones" in leak for leak in res.leaks)

    def test_unconfigured_fetcher_raises_not_silent_pass(self):
        with pytest.raises(LiveGateStubError, match="PageTextFetcher is not configured"):
            run_sweep(_manifest(), UnconfiguredPageTextFetcher())
