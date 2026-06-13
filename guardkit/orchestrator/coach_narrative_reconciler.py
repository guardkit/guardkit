"""Coach narrative reconciler — keep synthesized feedback faithful to the records.

TASK-FIX-COACHNARR01 (2026-06-12). Companion to
:mod:`guardkit.orchestrator.coach_output_parser` (which extracts the verdict)
and to the deterministic post-synthesis guards in
``agent_invoker._reconcile_absent_independent_test_signal`` /
``_apply_spec_gap_absent_guard`` (which override false-green verdicts).

## Why this exists

Under the toolless **B-min synthesis** Coach path the LLM emits the
``issues``/``rationale`` prose verbatim into ``coach_turn_N.json``. When the
Phase-A gather degrades to B-min (the known ``gemma4:26b`` recursion-limit
failure, TASK-PERF-COACHGATHER01), the synthesis model narrates discrepancy
records it *cannot inspect with tools*. In FEAT-C332 run 2 (TASK-QAWE-002) the
deterministic honesty gate found a REAL discrepancy (the Player claimed test
runs while the test-orchestrator specialist had hung — TASK-FIX-SPECVIOL01),
but the synthesis model **invented a wrong explanation**::

    "The Player claimed to have run tests in files
    (`tests/orchestrator/test_coach_evidence_bundle.py` and
    `tests/unit/orchestrator/quality_gates/test_coach_validator.py`) that do
    not exist on disk."

Both files exist — they are tracked repo files. The Player received
"Ensure all claimed test files exist" (unactionable, since they do) and burned
a turn acting on a hallucinated cause. The verdict *direction* was right; the
*explanation* was fabricated.

## What this module guarantees

1. **Embed the record verbatim (AC-001).** When a deterministic gate produced
   honesty discrepancies, render the structured fields (``claim_type``,
   ``player_claim``, ``actual_value``, ``severity``) directly into the feedback
   issue list — template-formatted, not synthesized. The Player always sees the
   real record even when the LLM narrated something else.

2. **Strip unsupported non-existence claims (AC-002 / AC-003).** Every file
   path the rationale (or a synthesized issue description) claims "does not
   exist on disk" MUST appear in an actual ``file_existence``-class discrepancy.
   A claim that names a path absent from the records is corrected to a neutral,
   accurate phrasing and flagged — never shipped to the Player as-is.

This is an instance of the meta-frame in
``.claude/rules/path-string-mismatch-is-not-dishonesty.md`` and
``.claude/rules/absence-of-failure-is-not-success.md``: a low-fidelity oracle
(here, the toolless synthesis model) must not be allowed to assert a
positive/negative signal it has no evidence for. The remediation is the same —
pair the free-form verdict with the deterministic record and reconcile.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, List, Set, Tuple

if TYPE_CHECKING:  # pragma: no cover — annotation-only import
    from guardkit.orchestrator.coach_verification import HonestyVerification

logger = logging.getLogger(__name__)


# Claim types whose discrepancy legitimately means "a claimed path is not on
# disk". A non-existence narrative is only supported when it names a path drawn
# from one of these. Mirrors coach_verification.py's emit sites.
FILE_EXISTENCE_CLAIM_TYPES = frozenset(
    {"file_existence", "promise_file_existence"}
)

# Marker stamped on issues this module synthesizes from deterministic records,
# so a re-run (or the enrichment re-write at agent_invoker
# `_create_player_report_from_task_work`) does not double-embed them.
DETERMINISTIC_SOURCE = "deterministic_honesty_gate"

# A path-like token: starts with a word char, contains a dot extension. Matches
# ``src/foo.py``, ``tests/unit/x_test.py``, ``a.md`` — not bare words. Used both
# to harvest paths from discrepancy ``player_claim`` strings and to find paths
# referenced in a non-existence clause.
_PATH_TOKEN_RE = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_./\-]*\.[A-Za-z0-9_]+")

# A non-existence assertion about files on disk. Covers
# "do/does/did not exist [on disk]" and "is/are/was/were not present on disk"
# and "not found on disk". Case-insensitive. The replacement text below is
# carefully free of the substring "exist" so a corrected clause cannot re-match.
_NONEXISTENCE_PHRASE_RE = re.compile(
    r"(?:do|does|did)\s+not\s+exist(?:\s+on\s+disk)?"
    r"|(?:is|are|was|were)\s+not\s+present\s+on\s+disk"
    r"|not\s+found\s+on\s+disk",
    re.IGNORECASE,
)

# Neutral, accurate replacement for an unsupported non-existence claim. It both
# corrects (states what is actually known) and flags (names the missing record)
# without re-asserting a falsehood. MUST NOT contain "exist"/"present on disk".
_CORRECTION_TEXT = (
    "could not be independently verified "
    "(no file_existence discrepancy was recorded for the referenced path)"
)

# Sentence terminators used to scope a non-existence phrase to its clause, so a
# legitimate non-existence claim elsewhere in the same text is not disturbed.
# A ``.`` or ``;`` is a boundary ONLY when followed by whitespace or end-of-text
# — otherwise the ``.`` inside a path extension (``foo.py``) or a decimal would
# spuriously split the clause and orphan the path token from its assertion.
_SENTENCE_BOUNDARY_CHARS = ".;"


def _is_boundary(text: str, i: int) -> bool:
    """True if ``text[i]`` is a sentence boundary in context.

    Newline is always a boundary. A ``.``/``;`` is a boundary only when it ends
    a sentence (followed by whitespace or end-of-text), never when it sits
    inside a token like ``test_coach_validator.py``.
    """
    ch = text[i]
    if ch == "\n":
        return True
    if ch in _SENTENCE_BOUNDARY_CHARS:
        return i + 1 >= len(text) or text[i + 1].isspace()
    return False


@dataclass
class ReconcileResult:
    """Outcome of :func:`reconcile_narrative`.

    Attributes:
        changed: True if the decision dict was mutated (issues embedded and/or
            narrative corrected). Drives whether the caller re-persists
            ``coach_turn_N.json``.
        embedded_issue_count: Number of deterministic-record issues prepended
            to ``decision['issues']`` (AC-001).
        corrected_paths: Paths whose unsupported non-existence claim was
            stripped/corrected (AC-002 / AC-003). Empty when no fabrication
            was found.
    """

    changed: bool = False
    embedded_issue_count: int = 0
    corrected_paths: List[str] = field(default_factory=list)


def _normalize_path(path: str) -> str:
    """Normalize a path token for comparison: strip wrappers and ``./``.

    Trims surrounding backticks/quotes/parens/whitespace, collapses backslashes
    to forward slashes, and drops a leading ``./`` and trailing ``/``. Mirrors
    ``CoachVerifier._normalize_claimed_path`` closely enough for set membership;
    we do not need worktree-relativization here because both sides (record path
    and narrative token) are compared as-written.
    """
    p = path.strip().strip("`'\"()[]{}<>,").strip()
    p = p.replace("\\", "/")
    while p.startswith("./"):
        p = p[2:]
    return p.rstrip("/")


def extract_file_existence_paths(honesty: "HonestyVerification") -> Set[str]:
    """Collect normalized paths from ``file_existence``-class discrepancies.

    The ``player_claim`` of a file-existence discrepancy has the shape
    ``"<file_list_key>: <path>"`` (e.g. ``"files_created: src/foo.py"``). We
    take the segment after the last ``": "`` when present, then also harvest any
    path-like tokens, so the set tolerates either shape.

    Returns an empty set when ``honesty`` has no file-existence discrepancies —
    the FEAT-C332 case, where the only discrepancy was a ``test_result`` claim.
    """
    paths: Set[str] = set()
    for d in honesty.discrepancies:
        if getattr(d, "claim_type", None) not in FILE_EXISTENCE_CLAIM_TYPES:
            continue
        claim = getattr(d, "player_claim", "") or ""
        tail = claim.split(": ", 1)[1] if ": " in claim else claim
        for token in _PATH_TOKEN_RE.findall(tail):
            paths.add(_normalize_path(token))
    return paths


def _severity_to_issue_severity(severity: str) -> str:
    """Map a discrepancy severity to a feedback-issue severity.

    Verbatim-record embedding (AC-001) reflects the discrepancy's own severity;
    only ``critical`` is turn-rejecting (``must_fix``). The finer Layer-2
    demotion of a single ``file_existence`` critical lives in
    ``CoachValidator._honesty_issues_from`` and is intentionally NOT duplicated
    here — this embedding is an audit-faithful copy of the record, not a second
    gate.
    """
    return "must_fix" if severity == "critical" else "should_fix"


def render_deterministic_issues(
    honesty: "HonestyVerification",
) -> List[Dict[str, Any]]:
    """Render honesty discrepancies as feedback issues carrying the record
    fields verbatim (AC-001).

    Each issue embeds ``claim_type``, ``player_claim``, ``actual_value`` and
    ``severity`` in ``details`` unchanged, with a template-formatted
    ``description``. Issues are stamped ``details['source'] = DETERMINISTIC_SOURCE``
    for idempotency.
    """
    issues: List[Dict[str, Any]] = []
    for d in honesty.discrepancies:
        claim_type = getattr(d, "claim_type", "unknown")
        player_claim = getattr(d, "player_claim", "")
        actual_value = getattr(d, "actual_value", "")
        severity = getattr(d, "severity", "warning")
        issues.append(
            {
                "severity": _severity_to_issue_severity(severity),
                "category": "honesty",
                "description": (
                    "Deterministic honesty record "
                    f"({claim_type}, severity={severity}): "
                    f"Player claim: {player_claim}. "
                    f"Actual: {actual_value}."
                ),
                "details": {
                    "source": DETERMINISTIC_SOURCE,
                    "claim_type": claim_type,
                    "player_claim": player_claim,
                    "actual_value": actual_value,
                    "severity": severity,
                },
            }
        )
    return issues


def _clause_bounds(text: str, start: int, end: int) -> Tuple[int, int]:
    """Return the [start, end) span of the clause enclosing ``text[start:end]``.

    Walks back to the previous sentence terminator (exclusive) and forward to
    the next one (inclusive of the matched phrase, exclusive of the terminator).
    Used to scope a non-existence phrase so paths in a *different* sentence do
    not influence whether this claim is supported.
    """
    left = start
    while left > 0 and not _is_boundary(text, left - 1):
        left -= 1
    right = end
    while right < len(text) and not _is_boundary(text, right):
        right += 1
    return left, right


def strip_unsupported_nonexistence_claims(
    text: str, supported_paths: Set[str]
) -> Tuple[str, List[str]]:
    """Correct non-existence claims that name paths absent from the records.

    For every non-existence phrase in ``text``, scope it to its clause and
    gather the path tokens in that clause. The claim is **unsupported** when the
    clause names at least one path and *none* of its paths appear in
    ``supported_paths``. An unsupported claim has its non-existence phrase
    replaced with :data:`_CORRECTION_TEXT`; a supported (or path-less,
    unattributable) claim is left untouched.

    Returns ``(corrected_text, corrected_paths)``. ``corrected_paths`` is the
    sorted, de-duplicated list of paths whose claim was corrected.
    """
    matches = list(_NONEXISTENCE_PHRASE_RE.finditer(text))
    if not matches:
        return text, []

    corrected_paths: Set[str] = set()
    # Build the output by stitching original spans with corrected phrase spans.
    # Process matches left-to-right; non-overlapping by construction.
    out: List[str] = []
    cursor = 0
    for m in matches:
        clause_l, clause_r = _clause_bounds(text, m.start(), m.end())
        clause = text[clause_l:clause_r]
        tokens = [_normalize_path(t) for t in _PATH_TOKEN_RE.findall(clause)]
        if not tokens:
            # No path attributed to this assertion — cannot judge it. Leave it.
            continue
        if any(t in supported_paths for t in tokens):
            # At least one referenced path has a real file_existence record.
            # The claim is (at least partly) supported — do not disturb it.
            continue
        # Unsupported: every path named in the clause lacks a file_existence
        # discrepancy. Replace just the phrase span, preserving the rest.
        out.append(text[cursor : m.start()])
        out.append(_CORRECTION_TEXT)
        cursor = m.end()
        corrected_paths.update(tokens)

    if not corrected_paths:
        return text, []
    out.append(text[cursor:])
    return "".join(out), sorted(corrected_paths)


def reconcile_narrative(
    decision: Dict[str, Any], honesty: "HonestyVerification"
) -> ReconcileResult:
    """Reconcile a synthesized Coach verdict against deterministic records.

    Mutates ``decision`` in place:

    * **AC-001** — when ``decision['decision'] == 'feedback'`` and ``honesty``
      has discrepancies, prepend deterministic-record issues (idempotent: skips
      if already embedded).
    * **AC-002 / AC-003** — correct any unsupported non-existence claim in
      ``decision['rationale']`` and in every synthesized issue ``description``.

    The narrative correction runs regardless of decision direction (it only ever
    removes a falsehood). Returns a :class:`ReconcileResult` describing what
    changed so the caller can decide whether to re-persist and what to log.
    """
    result = ReconcileResult()

    supported = extract_file_existence_paths(honesty)

    # AC-002 / AC-003: correct the free-form rationale.
    rationale = decision.get("rationale")
    if isinstance(rationale, str) and rationale:
        corrected, paths = strip_unsupported_nonexistence_claims(
            rationale, supported
        )
        if paths:
            decision["rationale"] = corrected
            result.corrected_paths.extend(paths)
            result.changed = True

    # AC-002 / AC-003: correct synthesized issue descriptions. Skip issues this
    # module emitted (deterministic source) — they carry verbatim records and
    # never contain a fabricated narrative.
    for issue in decision.get("issues", []) or []:
        if not isinstance(issue, dict):
            continue
        details = issue.get("details")
        if isinstance(details, dict) and details.get("source") == DETERMINISTIC_SOURCE:
            continue
        description = issue.get("description")
        if not isinstance(description, str) or not description:
            continue
        corrected, paths = strip_unsupported_nonexistence_claims(
            description, supported
        )
        if paths:
            issue["description"] = corrected
            result.corrected_paths.extend(paths)
            result.changed = True

    # De-duplicate corrected paths across rationale + issues.
    if result.corrected_paths:
        result.corrected_paths = sorted(set(result.corrected_paths))

    # AC-001: embed deterministic records as feedback issues (feedback verdicts
    # only — embedding a must_fix honesty record into an approve verdict would
    # be self-contradictory; approve-over-discrepancy is owned by other guards).
    if decision.get("decision") == "feedback" and honesty.discrepancies:
        existing = decision.get("issues") or []
        already_embedded = any(
            isinstance(i, dict)
            and isinstance(i.get("details"), dict)
            and i["details"].get("source") == DETERMINISTIC_SOURCE
            for i in existing
        )
        if not already_embedded:
            embedded = render_deterministic_issues(honesty)
            decision["issues"] = [*embedded, *existing]
            result.embedded_issue_count = len(embedded)
            result.changed = result.changed or bool(embedded)

    return result
