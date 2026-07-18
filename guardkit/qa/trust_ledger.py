"""Stage 3 · DF-021 TRUST LEDGER — per-lane merge-attendance streak + demotion.

H-A RETIRE-THE-COORDINATOR, Stage 3 (see
``docs/ways-of-working/retire-the-coordinator-build-handoff-2026-07-17.md`` §3).

Stage 1 mechanized the by-hand VERIFY and Stage 2 emits an MG-3 adversarial-review
record at the merge boundary. This module is the third piece: a **per-lane trust
ledger** that counts consecutive clean merges and, once a lane has earned it,
lets the merge automate — while demoting a lane the instant a post-merge blocker
lands. The auto-merge act itself (rebuilt behind this gate on the previously
UNCALLED ``worktrees/manager.py:merge()`` primitive) lives in
``orchestrator/auto_merge.py``; this module is the observable record it keys on.

**Transport (binding, v1).** FILE-BASED. The ledger reads Stage 2's MG-3 YAML
records and live-gate demotion-event files straight from the target repo's
``qa/`` tree, and persists its own state as an **observable machine record** —
one YAML file per lane under the ledger root. NATS payloads are WS4; nothing
here builds a message bus. The disposition surface is the YAML record itself.

**Ratified DF-021 definitions (bind exactly).**

* **STREAK.** A lane starts ATTENDED. ``N=5`` **consecutive clean** merges — each
  proven CLEAN by an MG-3-format record — graduate the lane. The streak counts
  **only** from MG-3-format records (no retroactive credit for pre-format
  merges). ``N`` is tunable by a dated note only (the ``threshold`` argument).
* **DEMOTION.** One **confirmed** post-merge blocker demotes the lane INSTANTLY
  back to attended until a fresh streak is recorded. The blocker signal =
  non-empty ``charged_failures`` at merge/verify (Stage 1) OR a confirmed-blocker
  MG-3 (Stage 2) OR a live-gate-failure demotion event (Stage 3, MG-5).
* **CONSTITUTIONAL CLASSES NEVER GRADUATE.** Schema/data migrations,
  spend-affecting, client-facing irreversibles, forge
  ``CONSTITUTIONAL_OVERRIDE_TARGETS`` — checked before ANY auto act regardless of
  streak. Represented here as a self-contained registry (the deckhand
  ``TrustEngine`` is a *pattern* here, never an import).

Streak / graduation / demotion are all **machine records** — observable files a
dashboard can read (MG-6 is zero new build; out of scope).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List, Optional, Sequence

import yaml

logger = logging.getLogger(__name__)

# --- lane states (observable) ------------------------------------------------
STATE_ATTENDED = "attended"
STATE_GRADUATED = "graduated"

# --- ledger-event verdicts ---------------------------------------------------
VERDICT_CLEAN = "clean"
VERDICT_BLOCKER = "blocker"

# --- demotion sources --------------------------------------------------------
SOURCE_CHARGED_FAILURES = "charged_failures"
SOURCE_MG3 = "mg3"
SOURCE_LIVE_GATE = "live_gate"

#: DF-021 ratified streak length — N consecutive clean MG-3 records graduate a
#: lane. Tunable only by a dated note (pass ``threshold=`` explicitly).
DEFAULT_STREAK_THRESHOLD = 5

#: The F14 severities that make a *confirmed* finding a merge blocker — mirrors
#: forge ``review_gate.models.SERIOUS`` as a PATTERN (never an import; guardkit
#: is self-contained, DF-001).
SERIOUS_SEVERITIES = frozenset({"critical", "high"})

#: Constitutional target identifiers that NEVER graduate — mirrors forge
#: ``gating.constitutional.CONSTITUTIONAL_OVERRIDE_TARGETS`` as a PATTERN. The
#: full constitutional registry (schema/data migrations, spend-affecting,
#: client-facing irreversibles) is populated at MG-7 activation (Rich's,
#: post-window); this default seeds the pull-request override class so the gate
#: is never empty.
DEFAULT_CONSTITUTIONAL_TARGETS = frozenset({"review_pr", "create_pr_after_review"})


# ---------------------------------------------------------------------------
# Constitutional registry (self-contained — a pattern, not a forge import)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ConstitutionalRegistry:
    """The set of lane/target identifiers that NEVER graduate.

    Kept self-contained (guardkit does not import forge): the identifiers mirror
    forge's ``CONSTITUTIONAL_OVERRIDE_TARGETS`` plus whatever the operator adds
    at MG-7 activation. ``is_constitutional`` is a pure membership test so both
    the graduation predicate and the auto-merge decision can consult the same
    canonical set.
    """

    targets: frozenset[str] = DEFAULT_CONSTITUTIONAL_TARGETS

    def is_constitutional(self, identifier: Optional[str]) -> bool:
        return bool(identifier) and identifier in self.targets


# ---------------------------------------------------------------------------
# MG-3 record classification (Stage 2 shape)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Mg3Verdict:
    """The clean/blocker read of one Stage 2 MG-3 record."""

    review_id: str
    is_blocker: bool
    confirmed_serious: tuple[str, ...] = ()

    @property
    def verdict(self) -> str:
        return VERDICT_BLOCKER if self.is_blocker else VERDICT_CLEAN


def classify_mg3_record(path: str | Path) -> Mg3Verdict:
    """Read a Stage 2 MG-3 YAML record and decide clean vs confirmed-blocker.

    The record is the F14 ``review-findings`` shape forge's
    ``dispatch_merge_review_gate`` writes to ``qa/review-<id>.yaml``: a mapping
    with ``review_id`` and ``findings[]`` (each ``{severity, status, ...}``). A
    record is a **confirmed blocker** iff any finding is ``status: confirmed``
    with a serious severity (critical/high) — exactly forge's
    ``confirmed_serious``. Everything else is clean.

    Raises:
        LedgerRecordError: the record cannot be read or is not the F14 shape —
            an unreadable record must be loud, never a silent clean (the same
            honesty posture as Stage 1's fail-toward-attention rule).
    """
    p = Path(path)
    try:
        raw = p.read_text(encoding="utf-8")
    except OSError as exc:
        raise LedgerRecordError(f"cannot read MG-3 record {p}: {exc}") from exc
    try:
        doc = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        raise LedgerRecordError(f"MG-3 record {p} is not valid YAML: {exc}") from exc
    if not isinstance(doc, dict):
        raise LedgerRecordError(f"MG-3 record {p} is not a mapping")
    review_id = doc.get("review_id")
    if not isinstance(review_id, str) or not review_id:
        raise LedgerRecordError(f"MG-3 record {p} has no review_id")
    findings = doc.get("findings") or []
    if not isinstance(findings, list):
        raise LedgerRecordError(f"MG-3 record {p} findings is not a list")
    serious: List[str] = []
    for f in findings:
        if not isinstance(f, dict):
            continue
        if f.get("status") == "confirmed" and f.get("severity") in SERIOUS_SEVERITIES:
            fid = f.get("id")
            serious.append(str(fid) if fid is not None else "<unnamed>")
    return Mg3Verdict(
        review_id=review_id,
        is_blocker=bool(serious),
        confirmed_serious=tuple(serious),
    )


# ---------------------------------------------------------------------------
# Demotion-event file (Stage 3 defines the shape; forge's MG-5 edge writes it)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DemotionEvent:
    """A live-gate-failure demotion event read from the target repo's qa/ tree.

    Minimal by design (spec §3, Stage 3 seams): the forge deploy/live-gate leg
    writes one of these when a post-merge live gate fails, and the ledger demotes
    on it. The caller provides the timestamp — the ledger never invents wall time
    for a record it did not observe first-hand.
    """

    feature_id: str
    lane: str
    source: str
    verdict: str
    timestamp: str
    receipt_ref: Optional[str] = None


def load_demotion_event(path: str | Path) -> DemotionEvent:
    """Load a live-gate demotion-event YAML file (loud on a malformed shape).

    Shape (the minimal contract this stage defines)::

        feature_id: FEAT-XYZ
        lane: api_test
        source: live_gate
        verdict: fail
        timestamp: 2026-07-20T09:00:00Z   # caller-provided
        receipt_ref: qa/live-gate-FEAT-XYZ.yaml   # optional

    Raises:
        LedgerRecordError: the file cannot be read / is not the expected shape.
    """
    p = Path(path)
    try:
        raw = p.read_text(encoding="utf-8")
    except OSError as exc:
        raise LedgerRecordError(f"cannot read demotion event {p}: {exc}") from exc
    try:
        doc = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        raise LedgerRecordError(f"demotion event {p} is not valid YAML: {exc}") from exc
    if not isinstance(doc, dict):
        raise LedgerRecordError(f"demotion event {p} is not a mapping")
    for key in ("feature_id", "lane", "source", "verdict", "timestamp"):
        if not doc.get(key):
            raise LedgerRecordError(f"demotion event {p} is missing '{key}'")
    return DemotionEvent(
        feature_id=str(doc["feature_id"]),
        lane=str(doc["lane"]),
        source=str(doc["source"]),
        verdict=str(doc["verdict"]),
        timestamp=str(doc["timestamp"]),
        receipt_ref=(str(doc["receipt_ref"]) if doc.get("receipt_ref") else None),
    )


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class LedgerRecordError(Exception):
    """A ledger input (MG-3 record / demotion event) is unreadable or malformed.

    Loud by design: an unreadable blocker signal must never silently pass as a
    clean merge (the fail-toward-attention posture Stage 1 established).
    """


# ---------------------------------------------------------------------------
# Ledger state (the observable machine record)
# ---------------------------------------------------------------------------


@dataclass
class LaneLedger:
    """One lane's observable trust state — persisted as ``<root>/<lane>.yaml``."""

    lane: str
    threshold: int = DEFAULT_STREAK_THRESHOLD
    streak: int = 0
    state: str = STATE_ATTENDED
    events: List[dict] = field(default_factory=list)

    @property
    def graduated(self) -> bool:
        """A lane is graduated iff its streak has reached the threshold.

        The constitutional check is applied by :class:`TrustLedger.graduated`
        (which owns the registry) — a bare :class:`LaneLedger` reports the raw
        streak state so the file is a faithful record of what happened.
        """
        return self.state == STATE_GRADUATED and self.streak >= self.threshold

    def to_dict(self) -> dict:
        return {
            "lane": self.lane,
            "threshold": self.threshold,
            "streak": self.streak,
            "state": self.state,
            "graduated": self.graduated,
            "events": list(self.events),
        }


class TrustLedger:
    """Per-lane DF-021 trust ledger over a file-based ledger root.

    Each lane's state is one observable YAML file (``<root>/<lane>.yaml``). The
    ledger is fed events as merges happen — ``record_merge`` (an MG-3 record ±
    Stage 1 charged failures) and ``record_demotion`` (a live-gate event) — and
    recomputes the streak / graduation / demotion state deterministically. It
    never scans wall-clock ordering: the per-lane event log IS the order.
    """

    def __init__(
        self,
        ledger_root: str | Path,
        *,
        threshold: int = DEFAULT_STREAK_THRESHOLD,
        constitutional: Optional[ConstitutionalRegistry] = None,
    ) -> None:
        self.ledger_root = Path(ledger_root)
        self.threshold = threshold
        self.constitutional_registry = constitutional or ConstitutionalRegistry()

    # -- persistence ------------------------------------------------------

    def _lane_path(self, lane: str) -> Path:
        safe = lane.replace("/", "__")
        return self.ledger_root / f"{safe}.yaml"

    def load(self, lane: str) -> LaneLedger:
        """Load a lane's ledger (a fresh ATTENDED lane when no file exists)."""
        path = self._lane_path(lane)
        if not path.exists():
            return LaneLedger(lane=lane, threshold=self.threshold)
        try:
            doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError) as exc:
            raise LedgerRecordError(f"cannot read ledger {path}: {exc}") from exc
        if not isinstance(doc, dict):
            raise LedgerRecordError(f"ledger {path} is not a mapping")
        return LaneLedger(
            lane=doc.get("lane", lane),
            threshold=int(doc.get("threshold", self.threshold)),
            streak=int(doc.get("streak", 0)),
            state=doc.get("state", STATE_ATTENDED),
            events=list(doc.get("events", [])),
        )

    def _save(self, ledger: LaneLedger) -> Path:
        self.ledger_root.mkdir(parents=True, exist_ok=True)
        path = self._lane_path(ledger.lane)
        path.write_text(
            yaml.safe_dump(ledger.to_dict(), sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
        return path

    # -- queries ----------------------------------------------------------

    def streak(self, lane: str) -> int:
        return self.load(lane).streak

    def graduated(self, lane: str) -> bool:
        """Whether ``lane`` has graduated to auto-merge.

        Streak has reached the threshold AND the lane is NOT constitutional —
        constitutional classes NEVER graduate, regardless of streak (checked
        before any auto act, DF-021).
        """
        if self.constitutional(lane):
            return False
        return self.load(lane).graduated

    def constitutional(self, identifier: Optional[str]) -> bool:
        """Whether a lane/target identifier is a never-graduate constitutional class."""
        return self.constitutional_registry.is_constitutional(identifier)

    # -- mutations --------------------------------------------------------

    def record_merge(
        self,
        lane: str,
        *,
        mg3_path: str | Path,
        charged_failures: Sequence[str] = (),
        timestamp: Optional[str] = None,
    ) -> LaneLedger:
        """Record one merge from its Stage 2 MG-3 record (± Stage 1 signal).

        The merge is a **blocker** iff Stage 1 charged failures are non-empty OR
        the MG-3 record confirms a serious finding; either resets the streak and
        demotes the lane INSTANTLY. Otherwise it is CLEAN: the streak advances by
        one, and the lane graduates when it reaches the threshold. The streak
        only ever advances on an MG-3 record (no retroactive credit).
        """
        verdict = classify_mg3_record(mg3_path)
        charged = [str(c) for c in charged_failures]
        is_blocker = verdict.is_blocker or bool(charged)
        ledger = self.load(lane)

        if is_blocker:
            source = SOURCE_MG3 if verdict.is_blocker else SOURCE_CHARGED_FAILURES
            ledger.streak = 0
            ledger.state = STATE_ATTENDED
            ledger.events.append(
                {
                    "kind": "merge",
                    "review_id": verdict.review_id,
                    "record_ref": str(mg3_path),
                    "verdict": VERDICT_BLOCKER,
                    "source": source,
                    "charged_failures": charged,
                    "confirmed_serious": list(verdict.confirmed_serious),
                    "timestamp": timestamp or _now(),
                }
            )
        else:
            ledger.streak += 1
            if ledger.streak >= ledger.threshold and not self.constitutional(lane):
                ledger.state = STATE_GRADUATED
            ledger.events.append(
                {
                    "kind": "merge",
                    "review_id": verdict.review_id,
                    "record_ref": str(mg3_path),
                    "verdict": VERDICT_CLEAN,
                    "streak": ledger.streak,
                    "timestamp": timestamp or _now(),
                }
            )
        self._save(ledger)
        return ledger

    def record_demotion(self, lane: str, *, event_path: str | Path) -> LaneLedger:
        """Demote a lane on a live-gate-failure demotion event (MG-5).

        A live-gate failure after an auto-merge auto-reverts the merge (existing
        O-32 substrate — not this module) AND demotes the lane: streak resets to
        0, state returns to attended, and the event is appended to the record.
        """
        event = load_demotion_event(event_path)
        ledger = self.load(lane)
        ledger.streak = 0
        ledger.state = STATE_ATTENDED
        ledger.events.append(
            {
                "kind": "demotion",
                "source": event.source,
                "feature_id": event.feature_id,
                "verdict": event.verdict,
                "receipt_ref": event.receipt_ref,
                "event_ref": str(event_path),
                "timestamp": event.timestamp,
            }
        )
        self._save(ledger)
        return ledger


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


__all__ = [
    "STATE_ATTENDED",
    "STATE_GRADUATED",
    "VERDICT_CLEAN",
    "VERDICT_BLOCKER",
    "SOURCE_CHARGED_FAILURES",
    "SOURCE_MG3",
    "SOURCE_LIVE_GATE",
    "DEFAULT_STREAK_THRESHOLD",
    "SERIOUS_SEVERITIES",
    "DEFAULT_CONSTITUTIONAL_TARGETS",
    "ConstitutionalRegistry",
    "Mg3Verdict",
    "classify_mg3_record",
    "DemotionEvent",
    "load_demotion_event",
    "LedgerRecordError",
    "LaneLedger",
    "TrustLedger",
]
