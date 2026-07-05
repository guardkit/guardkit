"""Single source of truth for parsing the pytest short-summary line.

TASK-AB-REVIEWCLEAN01 (item 1). Before this module three call sites each
re-implemented "read the pytest summary": ``specialist_invocations`` (the
Phase-4 counts tuple), ``coach_validator`` (the advisory skip count), and the
``agent_invoker`` streaming parser (the max-wins passed/failed/skipped it
accumulates). Each carried its own regex and its own return shape; drift
between them is a latent inconsistency.

The absence contract is load-bearing and identical across all three
consumers (``absence-of-failure-is-not-success`` /
``absence-must-survive-every-reconciliation-layer``): a count that could not
be parsed is ``None`` (UNKNOWN), never ``0``. A summary that parsed cleanly
but carried no token for a given outcome is ``0`` for that outcome. So:

- unparseable / empty output → every field ``None``;
- parsed summary, no ``skipped`` token → ``skipped == 0`` (a real "zero
  skipped" observation), ``passed``/``failed`` likewise 0 when absent but the
  summary parsed.

``max`` per outcome tolerates pytest reprinting the summary line.

The authoritative pass/fail signal is always the subprocess return code, not
these counts — a parse miss therefore never changes a gate verdict; the
counts are metadata / advisory only.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

__all__ = ["PytestSummary", "parse_pytest_summary"]

# One regex for every consumer. ``errors?`` collapses to the ``error`` key.
_PYTEST_OUTCOME_RE = re.compile(
    r"(\d+)\s+(passed|failed|errors?|xpassed|xfailed|skipped)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class PytestSummary:
    """Parsed pytest outcome counts.

    Every field is tri-state ``Optional[int]``: ``None`` = the output could
    not be parsed (UNKNOWN — never coerce to 0), ``0`` = the summary parsed
    but had no token for this outcome, ``N`` = the observed count.
    """

    passed: Optional[int] = None
    failed: Optional[int] = None
    errors: Optional[int] = None
    xpassed: Optional[int] = None
    xfailed: Optional[int] = None
    skipped: Optional[int] = None

    @property
    def parsed(self) -> bool:
        """True when at least one outcome token was recognised."""
        return self.passed is not None

    @property
    def tests_run(self) -> Optional[int]:
        """passed + failed + errors + xpassed + xfailed (skipped EXCLUDED — a
        skipped test executed no assertions). ``None`` when nothing parsed."""
        if not self.parsed:
            return None
        return (
            (self.passed or 0)
            + (self.failed or 0)
            + (self.errors or 0)
            + (self.xpassed or 0)
            + (self.xfailed or 0)
        )

    @property
    def tests_failed(self) -> Optional[int]:
        """failed + errors. ``None`` when nothing parsed."""
        if not self.parsed:
            return None
        return (self.failed or 0) + (self.errors or 0)


def parse_pytest_summary(output: Optional[str]) -> PytestSummary:
    """Parse a pytest short-summary line into a :class:`PytestSummary`.

    Returns an all-``None`` summary when ``output`` is falsy or carries no
    recognisable outcome token (the UNKNOWN case). Otherwise every outcome
    seen is its max-wins count and every outcome NOT seen is ``0`` — the
    summary parsed, so its silence about (say) ``skipped`` is a real "zero
    skipped" observation.
    """
    if not output:
        return PytestSummary()
    counts: dict[str, int] = {}
    for match in _PYTEST_OUTCOME_RE.finditer(output):
        key = match.group(2).lower()
        if key == "errors":
            key = "error"
        counts[key] = max(counts.get(key, 0), int(match.group(1)))
    if not counts:
        return PytestSummary()
    return PytestSummary(
        passed=counts.get("passed", 0),
        failed=counts.get("failed", 0),
        errors=counts.get("error", 0),
        xpassed=counts.get("xpassed", 0),
        xfailed=counts.get("xfailed", 0),
        skipped=counts.get("skipped", 0),
    )
