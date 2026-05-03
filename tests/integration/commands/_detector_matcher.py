"""Contract-mirror matcher for the operator_handoff detection rules.

This module is **not** a production detector. The Plan agent runs the actual
detection at plan time using its prompt-side reasoning over the rules in
``installer/core/commands/feature-plan.md`` (the "Detection Rules — when to
mark a task ``operator_handoff``" subsection added by TASK-FPTC-001).

This Python helper mirrors the strong/weak/pairing rules from that prompt
text so the test suite can mechanically verify the rules cover the two
real-world reproducers (study-tutor TASK-GR-SEED AC-SEED-01 and TASK-GR-DEMO
AC-DEMO-01) and reject the documented false-positive cases. If the prompt
ever drifts away from the rules encoded here, the contract test in
``test_feature_plan_class_c_detection.py`` will fail and force one of the
two surfaces to be brought back into alignment.

Rule summary (verbatim from feature-plan.md):

- **Strong signals (any one triggers):** live infrastructure markers
  (``FalkorDB at <host>``, ``Redis at <host>``, project hostnames),
  human verbs (``human-in-the-loop``, ``Claude Desktop``, ``conduct``,
  ``tutoring session``, ...), wall-clock language (``p50``, ``p95``,
  ``wall-clock``, ``soak``, ``burn-in``), and author self-disclosure
  (``no automated test harness``, ``manual verification required``, ...).
- **Weak signals (require pairing with at least one strong signal):**
  ``verify``/``ensure``/``check``, bare ``running``, project-specific
  user/dataset names.
- **False-positive guard:** weak signal alone does NOT trigger.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Mapping, Pattern, Sequence

# ---------------------------------------------------------------------------
# Strong signal patterns (any one match triggers the rule)
# ---------------------------------------------------------------------------
#
# The patterns are deliberately tight so the false-positive cases enumerated
# in feature-plan.md (e.g. ``FALKORDB_HOST`` env var as a config string) do
# not accidentally match. ``FalkorDB at`` is case-sensitive precisely so the
# all-caps env-var form fails to match.

_STRONG_SIGNALS: Mapping[str, Sequence[Pattern[str]]] = {
    "live_infrastructure": (
        re.compile(r"\bFalkorDB\s+at\b"),
        re.compile(r"\bRedis\s+at\b"),
        re.compile(r"\bwhitestocks\b"),
        re.compile(r"\bpromaxgb10-"),
        re.compile(r"real\s+(?:LLM|OpenAI)", re.IGNORECASE),
        re.compile(r"MCP\s+query\s+against\s+running", re.IGNORECASE),
    ),
    "human_verbs": (
        re.compile(r"\bhuman-in-the-loop\b"),
        re.compile(r"\bClaude\s+Desktop\b"),
        re.compile(r"\bopen\s+ChatGPT\b"),
        re.compile(r"\btutor(?:ing)?\s+session\b"),
        re.compile(r"\bconducted?\b"),
        re.compile(r"\bobserved?\b"),
        re.compile(r"\bdrive\s+\d+\s+turn"),
    ),
    "wall_clock": (
        re.compile(r"\bp50\b"),
        re.compile(r"\bp95\b"),
        re.compile(r"\bwall-clock\b"),
        re.compile(r"\bsoak\b"),
        re.compile(r"\bburn-in\b"),
        re.compile(r"latency\s+over\s+a\s+\d+-minute", re.IGNORECASE),
        re.compile(r"\d+\s+minutes\s+of\s+operation", re.IGNORECASE),
    ),
    "author_self_disclosure": (
        re.compile(r"no\s+automated\s+test\s+harness", re.IGNORECASE),
        re.compile(r"manual\s+verification\s+required", re.IGNORECASE),
        re.compile(r"operator\s+runs\s+the\s+script", re.IGNORECASE),
        re.compile(r"cannot\s+be\s+satisfied\s+by\s+autobuild", re.IGNORECASE),
    ),
}

# ---------------------------------------------------------------------------
# Weak signal patterns (require pairing with a strong signal to trigger)
# ---------------------------------------------------------------------------

_WEAK_SIGNALS: Sequence[Pattern[str]] = (
    re.compile(r"\b(?:verify|ensure|check)\b", re.IGNORECASE),
    re.compile(r"\brunning\b", re.IGNORECASE),
    re.compile(r"\bLilymay\b"),
    re.compile(r"\btest-user-\d+\b"),
)


@dataclass(frozen=True)
class MatchResult:
    """Outcome of running the matcher against one acceptance criterion."""

    triggered: bool
    strong_categories: tuple[str, ...]
    weak_count: int


def detect_operator_handoff(ac_text: str) -> MatchResult:
    """Apply strong/weak/pairing rules to one acceptance criterion.

    A strong signal alone triggers. A weak signal alone does NOT trigger
    (the false-positive guard from feature-plan.md). Mixed (1 strong + N
    weak) triggers because strong always wins.
    """
    strong_categories = tuple(
        sorted(
            category
            for category, patterns in _STRONG_SIGNALS.items()
            if any(pattern.search(ac_text) for pattern in patterns)
        )
    )
    weak_count = sum(1 for pattern in _WEAK_SIGNALS if pattern.search(ac_text))
    return MatchResult(
        triggered=bool(strong_categories),
        strong_categories=strong_categories,
        weak_count=weak_count,
    )
