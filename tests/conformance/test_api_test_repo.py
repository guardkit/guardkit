"""The acceptance test: the checker run against the real pilot repository.

api_test's rules file carries one known problem on purpose. Its search feature runs
its database queries inside the web route handler and imports another feature's model
to do it — one problem with two symptoms, written by the factory on 2026-08-16 and
merged. It was left in place so that this test can exist: if the checker does not find
it, the checker does not work; and if the checker finds anything else, the checker
cries wolf.

Nothing here hardcodes what to expect. The expectation is read out of the rules file's
own ``expected_current_finding`` annotations, so the day somebody fixes the search
router and updates the annotation, this test follows them.

The test skips when api_test is not on the machine, which is the only thing about it
that is not an assertion.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

from guardkit.conformance.engine import run
from guardkit.conformance.model import UNSUPPORTED

API_TEST = Path(__file__).resolve().parents[2].parent / "api_test"
RULES = API_TEST / "docs" / "architecture-rules.yaml"

# The docstring at this line contains "await db.execute(select(User))" as an example.
# It is prose, not code. A checker that reads text rather than syntax trees reports it,
# and if it ever appears below, every number this program has produced is suspect.
THE_DOCSTRING_TRAP = "src/db/dependencies.py:29"

pytestmark = pytest.mark.skipif(
    not RULES.is_file(),
    reason=f"api_test is not on this machine (looked for {RULES})")


@pytest.fixture(scope="module")
def report():
    return run(API_TEST)


@pytest.fixture(scope="module")
def expected() -> dict[str, dict[str, str]]:
    """What the rules file itself says the checker should find today."""
    cfg = yaml.safe_load(RULES.read_text(encoding="utf-8"))
    out: dict[str, dict[str, str]] = {}
    for rule in cfg["rules"]:
        for finding in (rule.get("expected_current_finding") or {}).get("findings", []):
            out[f"{rule['id']} {finding['at']}"] = finding
    return out


def test_the_checker_finds_exactly_what_the_rules_file_says_is_there_and_nothing_else(
        report, expected):
    seen = {f"{outcome.rule_id} {site.where}"
            for outcome in report.rules for site in outcome.findings}
    assert seen == set(expected)


def test_every_rule_in_the_pilot_repository_has_a_check_behind_it(report):
    unsupported = {r.rule_id: r.unsupported_reason for r in report.rules
                   if r.status == UNSUPPORTED}
    assert unsupported == {}, "a rule with no check behind it is not clean, it is unchecked"


def test_every_rule_looked_at_something(report):
    """A clean line means nothing if the check never had anything in front of it."""
    empty = [r.rule_id for r in report.rules if not r.examined]
    assert empty == []


def test_the_query_written_inside_a_docstring_is_invisible_to_every_rule(report):
    """The instrument's own validation, against the one line that proves it."""
    everywhere = {site.where for outcome in report.rules for site in outcome.sites}
    assert THE_DOCSTRING_TRAP not in everywhere


def test_the_line_that_runs_each_seeded_query_is_folded_into_the_line_that_built_it(
        report, expected):
    """The rules file settles the counting: four lines, two queries, two findings."""
    by_where = {f"{outcome.rule_id} {site.where}": site
                for outcome in report.rules for site in outcome.findings}
    checked = 0
    for key, annotation in expected.items():
        match = re.search(r"executed at line (\d+)", annotation.get("what", ""))
        if not match:
            continue
        checked += 1
        assert any(f"line {match.group(1)}" in extra for extra in by_where[key].also_at)
    assert checked, "the rules file no longer annotates which line runs which query"


def test_the_run_finishes_with_the_exit_code_that_means_there_is_something_to_read(report):
    assert report.ran is True
    assert report.exit_code() == 1


def test_the_liveness_probe_the_rules_file_excuses_is_seen_and_excused(report):
    """A silence somebody decided on, rather than a silence nobody noticed."""
    excepted = [site.where for outcome in report.rules for site in outcome.sites
                if site.placement == "excepted"]
    assert "src/health/router.py:41" in excepted
