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

3. **A WARNING NEVER BURNS A BUILD (LANE-WF).** An advisory (non-``critical``)
   honesty record is recorded on the verdict payload *in both directions* —
   including on an ``approve`` — and NEVER changes the verdict. Only
   ``critical``-severity records are turn-rejecting, and their override path is
   owned elsewhere (``CoachValidator`` short-circuits gathering with
   ``partial_honesty_abort``; ``AgentInvoker._reconcile_incomplete_evidence_gathering``
   turns that into the approve→feedback flip). This module never writes
   ``decision['decision']`` on any path.

   The motivating receipt is build ``FEAT-STV1-20260801195639`` (2026-08-01):
   five turns carried the same two ``claim_audit_unmodified`` advisory records
   (``severity=should_fix``, whose own ``actual_value`` prose ends "this is a
   warning, not a turn-rejecting fabrication") as the FIRST issue on every
   feedback verdict, while the honesty channel simultaneously reported
   ``verified: false`` to the Coach. Advisory records must read as advisory
   everywhere they are surfaced, and must survive onto an approve rather than
   being silently dropped.

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

# LANE-WF. Discrepancy severities that are TURN-REJECTING ("must_fix class").
# Everything else on the ``Discrepancy.severity`` scale ("should_fix",
# "warning", "info") is ADVISORY: recorded, logged, never verdict-bearing.
# Single source of truth for :func:`_severity_to_issue_severity` and
# :func:`partition_by_class`; mirrors the ``severity == "critical"`` filter in
# ``CoachValidator._honesty_issues_from``.
MUST_FIX_DISCREPANCY_SEVERITIES = frozenset({"critical"})

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
        advisory_records_recorded: Number of ADVISORY (non-``critical``)
            honesty records written onto an ``approve`` verdict (LANE-WF).
            Non-zero only on the approve path; the feedback path reports its
            embeds through ``embedded_issue_count`` exactly as before. Lets
            the caller log the warning with task/turn context.
    """

    changed: bool = False
    embedded_issue_count: int = 0
    corrected_paths: List[str] = field(default_factory=list)
    advisory_records_recorded: int = 0


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
    return (
        "must_fix"
        if severity in MUST_FIX_DISCREPANCY_SEVERITIES
        else "should_fix"
    )


def is_must_fix_class(discrepancy: Any) -> bool:
    """True when ``discrepancy`` is turn-rejecting (LANE-WF).

    A record is must_fix-class iff its ``severity`` is in
    :data:`MUST_FIX_DISCREPANCY_SEVERITIES`. A record with no ``severity``
    attribute is treated as ADVISORY — an unknown shape must never acquire
    verdict-bearing power by accident (fail-open on the reject direction is
    owned by the critical-severity emit sites in ``coach_verification``).
    """
    return (
        getattr(discrepancy, "severity", "warning")
        in MUST_FIX_DISCREPANCY_SEVERITIES
    )


def partition_by_class(
    honesty: "HonestyVerification",
) -> Tuple[List[Any], List[Any]]:
    """Split ``honesty.discrepancies`` into ``(must_fix_class, advisory)``.

    ``must_fix_class`` records are turn-rejecting; ``advisory`` records are
    warnings that must be recorded and logged but MUST NOT change a verdict
    (LANE-WF: a warning never burns a build).
    """
    discrepancies = list(getattr(honesty, "discrepancies", None) or [])
    must_fix = [d for d in discrepancies if is_must_fix_class(d)]
    advisory = [d for d in discrepancies if not is_must_fix_class(d)]
    return must_fix, advisory


def render_deterministic_issues(
    honesty: "HonestyVerification",
    discrepancies: List[Any] | None = None,
) -> List[Dict[str, Any]]:
    """Render honesty discrepancies as feedback issues carrying the record
    fields verbatim (AC-001).

    Each issue embeds ``claim_type``, ``player_claim``, ``actual_value`` and
    ``severity`` in ``details`` unchanged, with a template-formatted
    ``description``. Issues are stamped ``details['source'] = DETERMINISTIC_SOURCE``
    for idempotency.

    Args:
        honesty: the verification whose records are rendered.
        discrepancies: optional explicit subset to render (LANE-WF — the
            approve path renders only the ADVISORY partition). ``None``
            renders ``honesty.discrepancies`` in full, byte-unchanged.
    """
    records = (
        honesty.discrepancies if discrepancies is None else discrepancies
    )
    issues: List[Dict[str, Any]] = []
    for d in records:
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
    * **LANE-WF** — when ``decision['decision'] == 'approve'`` and every
      record is ADVISORY (no ``critical``-severity record), APPEND the advisory
      records to ``decision['issues']`` so the honesty trail survives onto the
      approve instead of being silently dropped, and log at WARNING. The
      verdict is NOT touched.

    The narrative correction runs regardless of decision direction (it only ever
    removes a falsehood). Returns a :class:`ReconcileResult` describing what
    changed so the caller can decide whether to re-persist and what to log.

    **Invariant (LANE-WF):** this function NEVER writes
    ``decision['decision']`` on any path. A warning never burns a build; the
    turn-rejecting override for ``critical`` records is owned by
    ``CoachValidator.gather_evidence`` (``partial_honesty_abort``) and
    ``AgentInvoker._reconcile_incomplete_evidence_gathering``.
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

    # LANE-WF: a warning never burns a build — and it is never silently
    # dropped either. On an ``approve`` whose records are ALL advisory
    # (non-``critical``), record them verbatim on the approve's payload so the
    # honesty trail is complete in both verdict directions, and log at WARNING.
    #
    # APPENDED, not prepended: on the feedback path the deterministic record is
    # prepended because it is (part of) the reason for the rejection; on an
    # approve it is a warning riding along, and putting it first would make an
    # advisory record read as the headline finding — the exact mis-framing seen
    # on build FEAT-STV1-20260801195639.
    #
    # A ``critical`` record present ⇒ this branch stays out of the way
    # BYTE-UNCHANGED from main (no embed, no verdict touch): that turn is owned
    # by the ``partial_honesty_abort`` → ``_reconcile_incomplete_evidence_gathering``
    # override, which flips the verdict for real.
    elif decision.get("decision") == "approve":
        must_fix_class, advisory = partition_by_class(honesty)
        if advisory and not must_fix_class:
            existing = decision.get("issues") or []
            already_embedded = any(
                isinstance(i, dict)
                and isinstance(i.get("details"), dict)
                and i["details"].get("source") == DETERMINISTIC_SOURCE
                for i in existing
            )
            if not already_embedded:
                recorded = render_deterministic_issues(
                    honesty, discrepancies=advisory
                )
                decision["issues"] = [*existing, *recorded]
                result.embedded_issue_count = len(recorded)
                result.advisory_records_recorded = len(recorded)
                result.changed = result.changed or bool(recorded)
                logger.warning(
                    "LANE-WF: %d advisory honesty record(s) recorded on an "
                    "APPROVE verdict without changing it (claim_type(s): %s). "
                    "A warning never burns a build; only critical-severity "
                    "records are turn-rejecting.",
                    len(recorded),
                    sorted(
                        {
                            str(getattr(d, "claim_type", "unknown"))
                            for d in advisory
                        }
                    ),
                )

    return result
