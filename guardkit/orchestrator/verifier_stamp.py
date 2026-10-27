"""Scenario ``verifier:`` stamps on planning artifacts (card Q8/A.2).

A stamp names where a scenario is proven: one of the homes in
:data:`VERIFIER_HOMES`. Stamps live in the feature YAML's ``scenarios:`` map
(title -> stamp) and, optionally, as ``verifier:`` / ``test_ref:`` in a task's
frontmatter. The stamp normaliser (``stamp_normalizer.py``) writes them by
rule.

The cull (27 October 2026, GKT-036 / GKT-041): GuardKit no longer refuses a
plan or a task over a stamp. An unknown home, a ``toolchain`` stamp without a
``test_ref``, an unstamped scenario and the ``routing_law:`` flag are no
longer checked; a stamp is kept as written.

The toolchain linkage: for a task stamped ``verifier: toolchain`` with a
``test_ref:``, :func:`build_rule_from_frontmatter` builds a ``token_coverage``
rule for ``spec_conformance`` so the named test token stays under the
declared ``test_paths`` (default ``tests/**/*``).
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)


# The homes a stamp can name (A.2): six live homes, the dormant browser home
# and attended human work. The stamp normaliser and its model fallback mint
# only these.
VERIFIER_HOMES: Tuple[str, ...] = (
    "toolchain",
    "hurl",
    "exam",
    "probe:bus",
    "probe:process",
    "flutter",
    "playwright",
    "operator",
)

# Default search space for a toolchain stamp's `test_ref` token when the
# stamp declares no `test_paths` of its own. One conventional location, not a
# guess-ladder: a repo whose tests live elsewhere declares `test_paths`.
DEFAULT_TEST_REF_PATHS: Tuple[str, ...] = ("tests/**/*",)

# Rule id for the synthesized token_coverage rule (task-frontmatter linkage).
TEST_REF_RULE_ID = "routing-law-test-ref"

# Gherkin scenario-title lines. Longest keyword first so "Scenario Outline:"
# never half-matches as "Scenario"; "Example:" (a Gherkin-6 Scenario alias)
# matches but "Examples:" (an Outline's table header) cannot — the "s" breaks
# the literal-plus-colon match.
_SCENARIO_LINE_RE = re.compile(
    r"^\s*(?:Scenario Outline|Scenario Template|Scenario|Example)\s*:\s*(?P<title>\S.*?)\s*$",
    re.MULTILINE,
)


class ScenarioStamp(BaseModel):
    """One scenario's ``verifier:`` stamp (feature-YAML per-scenario map).

    Fields are kept as written; unknown keys are ignored (the cull, 27
    October 2026). ``owner_task`` names the task whose acceptance criteria
    state the scenario's observable behaviour (B9, 19 September 2026).
    """

    model_config = ConfigDict(extra="ignore")

    verifier: str
    test_ref: Optional[str] = None
    test_paths: Optional[List[str]] = None
    owner_task: Optional[str] = None


def validate_task_verifier(
    task_id: str, raw: Any, test_ref: Any = None
) -> Optional[str]:
    """A task's frontmatter ``verifier:`` stamp, as written.

    Returns the stripped name for a non-empty string and ``None`` otherwise.
    Nothing is refused since the cull (27 October 2026); the name and
    signature are kept for the task-start caller in ``autobuild.py``.
    """
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    return None


def extract_scenario_titles(feature_text: str) -> List[str]:
    """Extract scenario titles from Gherkin text (order kept, duplicates kept).

    Line-shaped lexing, not a Gherkin parser: ``Scenario:``,
    ``Scenario Outline:``, ``Scenario Template:`` and the Gherkin-6
    ``Example:`` alias all title a scenario; ``Examples:`` (an Outline's
    table header) never matches.
    """
    return [m.group("title") for m in _SCENARIO_LINE_RE.finditer(feature_text)]


def build_token_coverage_rule(
    verifier: Optional[str],
    test_ref: Optional[str],
    test_paths: Optional[List[str]] = None,
    *,
    rule_id: str = TEST_REF_RULE_ID,
) -> Optional[Dict[str, Any]]:
    """The toolchain linkage: build the ``token_coverage`` rule for a stamp.

    Returns a rule dict shaped exactly for ``spec_conformance``'s
    ``TokenCoverageRule`` (the live, snapshotted, Coach-guarded machinery —
    wire, don't rebuild) when the stamp is ``verifier: toolchain`` AND carries
    a ``test_ref``; otherwise ``None``. Pure — no I/O, no logging; the
    frontmatter wrapper below owns the loud-unconsumed warning.
    """
    if verifier != "toolchain" or not test_ref:
        return None
    return {
        "id": rule_id,
        "type": "token_coverage",
        "paths": list(test_paths) if test_paths else list(DEFAULT_TEST_REF_PATHS),
        "require_tokens": [test_ref],
    }


def build_rule_from_frontmatter(
    frontmatter: Dict[str, Any], *, task_id: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Frontmatter seam for the toolchain linkage (never raises).

    Called from ``snapshot_task_conformance``. Returns the ``token_coverage``
    rule for a ``verifier: toolchain`` stamp with a non-empty string
    ``test_ref``; otherwise ``None``. ``test_paths`` that is not a non-empty
    list of strings is replaced by the default.
    """
    verifier = frontmatter.get("verifier")
    test_ref = frontmatter.get("test_ref")
    test_paths = frontmatter.get("test_paths")

    if not (isinstance(test_ref, str) and test_ref.strip()):
        return None
    if not (
        isinstance(test_paths, list)
        and test_paths
        and all(isinstance(p, str) and p.strip() for p in test_paths)
    ):
        test_paths = None

    rule = build_token_coverage_rule(
        verifier if isinstance(verifier, str) else None,
        test_ref.strip(),
        test_paths,
    )
    if rule is not None:
        logger.info(
            "Task %s (`verifier: toolchain`, test_ref=%r): token_coverage "
            "rule %r over %s.",
            task_id or "<task>",
            test_ref,
            rule["id"],
            rule["paths"],
        )
    return rule


__all__ = [
    "VERIFIER_HOMES",
    "DEFAULT_TEST_REF_PATHS",
    "TEST_REF_RULE_ID",
    "ScenarioStamp",
    "validate_task_verifier",
    "extract_scenario_titles",
    "build_token_coverage_rule",
    "build_rule_from_frontmatter",
]
