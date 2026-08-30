"""The things this checker produces: sites, rule outcomes, and one report.

Nothing here draws a conclusion. The word used throughout is *site*: a place in the
code where a pattern a rule names occurs. A site the rule already allows — it is in
the file the rule names as the pattern's home, or the rules file lists it as an
exception — is still recorded, because "nine of the eleven other query sites in this
repo are in crud.py" is the sentence that makes a finding readable. Only sites in
neither place are reported as findings.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Where a site sits relative to what its rule allows.
AT_HOME = "at_home"        # in the file the rule names as the pattern's home
EXCEPTED = "excepted"      # named in the rule's own exceptions list, with a reason
ELSEWHERE = "elsewhere"    # in neither — this is what becomes a finding

# What a rule's run came to.
CLEAN = "clean"
FINDING = "finding"
UNSUPPORTED = "unsupported"   # the engine could not run this rule. Never "clean".


class Unsupported(Exception):
    """Raised by a check when it cannot run the rule as written.

    This exists so that a rule the engine does not understand is loud. Silent
    success that does nothing is this estate's known failure class, so a rule that
    was never checked is never reported as clean, and it drives the exit code to 2.
    """


@dataclass
class Site:
    rule_id: str
    path: str                       # repo-relative
    line: int                       # 0 means the fact is about the file tree, not a line
    observed: str                   # what is there, in words
    how_observed: str               # the syntax-tree (or file-tree) fact that established it
    placement: str = ELSEWHERE
    enclosing: str | None = None    # the function the site sits in, if any
    exception_reason: str | None = None
    also_at: list[str] = field(default_factory=list)   # lines folded into this one
    # Some observations are findings wherever they sit — "this table class does not
    # inherit the base the rule names" is true in the home file too. Those set this,
    # so being in the home file does not excuse them.
    always_a_finding: bool = False
    # Set only when the run was narrowed to the files a git range touched: True when
    # this site is in one of them. None means the run was not narrowed.
    in_this_change: bool | None = None

    @property
    def where(self) -> str:
        return f"{self.path}:{self.line}" if self.line else self.path


@dataclass
class Tally:
    """What a rule actually looked at, counted while it looked.

    This exists because of the failure this estate keeps meeting: a check that runs,
    matches nothing because it was looking in the wrong place, and reports success. A
    rule that says "20 route handlers examined, none in a shape the rule did not name"
    can be told apart from one that examined nothing at all. A clean line with a zero
    population is a checker defect, and this is how a reader sees it.
    """

    counts: dict[str, int] = field(default_factory=dict)

    def add(self, noun: str, n: int = 1) -> None:
        if n:
            self.counts[noun] = self.counts.get(noun, 0) + n

    def as_text(self) -> str:
        return ", ".join(f"{k}: {v}" for k, v in self.counts.items()) or "nothing"


@dataclass
class RuleOutcome:
    rule_id: str
    says: str
    source: dict[str, Any]
    kind: str
    scope: str
    status: str = CLEAN
    unsupported_reason: str | None = None
    sites: list[Site] = field(default_factory=list)
    exceptions: list[dict[str, Any]] = field(default_factory=list)
    examined: dict[str, int] = field(default_factory=dict)
    inherited_signals: list[str] = field(default_factory=list)

    @property
    def findings(self) -> list[Site]:
        """Every site in a place the rule did not name, anywhere in the repository."""
        return [s for s in self.sites if s.placement == ELSEWHERE]

    def reported_findings(self, narrowed: bool) -> list[Site]:
        """The findings this run reports: all of them, or only those in the change."""
        return [s for s in self.findings if not narrowed or s.in_this_change]

    def counts(self) -> dict[str, int]:
        return {p: sum(1 for s in self.sites if s.placement == p)
                for p in (AT_HOME, EXCEPTED, ELSEWHERE)}


@dataclass
class Report:
    repo: str
    rules_path: str | None = None
    ran: bool = False
    could_not_run: str | None = None
    repo_identified_as: str | None = None
    rules_written_for: str | None = None
    files_scanned: int = 0
    files_unparsed: list[dict[str, str]] = field(default_factory=list)
    rules: list[RuleOutcome] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    # The repo-relative files a git range touched, when the run was narrowed to a
    # change. None means the whole repository was reported on.
    diff_scope: list[str] | None = None

    @property
    def narrowed(self) -> bool:
        return self.diff_scope is not None

    @property
    def all_findings(self) -> list[Site]:
        """Everything found, whether or not this run reports on it."""
        return [s for r in self.rules for s in r.findings]

    @property
    def reported_findings(self) -> list[Site]:
        """What this run reports: narrowed to the change, if it was narrowed."""
        return [s for r in self.rules for s in r.reported_findings(self.narrowed)]

    @property
    def unsupported(self) -> list[RuleOutcome]:
        return [r for r in self.rules if r.status == UNSUPPORTED]

    def exit_code(self) -> int:
        """0 ran clean, 1 ran with findings, 2 could not run.

        A rule the engine cannot run counts as "could not run", not as clean: exit 0
        on an unchecked rule would be the checker reporting success for work it never
        did.
        """
        if self.could_not_run or not self.ran or self.unsupported:
            return 2
        return 1 if self.reported_findings else 0
