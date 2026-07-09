"""F8 · failure-disposition record (LPA-08, ST-02, ST-09) — session B4.

Instance: ``qa/dispositions-<run|campaign>.yaml`` (referenced by the results
envelope's ``dispositions_ref``).

Every red an F4 run observes must be *binned* — attributed against the seam's
arbiter (F6) and given a disposition — before the run can close. That is the
load-bearing DF-017 §2.1 rule ("a red without a disposition = an UNCLOSED run");
its enforcement lives in ``guardkit/orchestrator/live_gate/disposition.py``, and
this module is the schema the enforcement reads/writes.

Attribution vocabulary (DF-017): ``app|backend|contract_gap|instrument|
environment``, assigned against the seam's arbiter. The wire collapse
(backward-edge §7 item 7, nats-core 0.7.0 ``AssertionDisposition``) is
``counts ⇐ {app, backend, contract_gap}``; ``instrument ⇐ instrument``;
``environment ⇐ environment`` — **instrument/environment never count against the
feature.** That mapping is code, not schema, and lives in ``disposition.py``.

ST-09 revisions: when attribution changes (a confound is disambiguated by a
controlled rerun — the study-tutor GPU-eviction case is the worked example), the
correction is appended as an ``AttributionRevision`` **same-day**, never a silent
overwrite. A verifier that never revises verdicts trains people to ignore them.

> **B10 reconcile (2026-07-09) — RATIFIED, no fields moved.** F8's field list
> was defined here minimally by B4 ahead of B10 (which owns tier-2/3 schemas).
> B10 reviewed it against scope-design §2 and ratifies it AS-IS: every §2 field
> (``failures[].{failure_id, assertion, observed, expected, evidence_ref,
> attribution, disposition, fix_ref, rescope_rationale, revisions[]}``) is
> present with the §2 vocabulary. The one addition beyond §2 is the ``run_id``
> root anchor (the container the ``failures`` list belongs to — B3 stamps the
> results-envelope run id here). No field was renamed or moved, so B4's F8 tests
> stay green. See the WS2 build-plan §B10 dated reconcile note.

Field list pinned by scope-design §2 (2026-07-07). Additions require a dated
note in that doc, never silent invention (the B1 rule).
"""

from __future__ import annotations

from typing import ClassVar, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from guardkit.qa.formats.base import QAFormatModel

#: Attribution classes (DF-017), assigned against the seam's arbiter (F6).
Attribution = Literal["app", "backend", "contract_gap", "instrument", "environment"]

#: How the red was dispositioned once attributed.
Disposition = Literal[
    "defect_fixed",
    "assertion_rescoped",
    "instrument_fixed",
    "accommodation_documented",
]


class AttributionRevision(BaseModel):
    """One ST-09 correction of a red's attribution.

    Appended (never overwritten) when a confound is disambiguated — e.g. a
    deadline spike first read as backend latency, later proven to be GPU
    eviction by a controlled quiet-GPU rerun, is corrected to ``environment``.
    """

    model_config = ConfigDict(extra="forbid")

    date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    prior_attribution: Attribution
    corrected_to: Attribution
    evidence: str = Field(min_length=1, description="What proved the correction")


class FailureDisposition(BaseModel):
    """One observed red, binned against the arbiter with a disposition."""

    model_config = ConfigDict(extra="forbid")

    failure_id: str = Field(min_length=1)
    assertion: str = Field(min_length=1, description="The assertion / sweep leak that went red")
    observed: Optional[str] = None
    expected: Optional[str] = None
    evidence_ref: Optional[str] = None
    attribution: Attribution = Field(description="Current attribution (latest, post-revision)")
    disposition: Disposition
    # One of these is expected depending on the disposition — not schema-enforced
    # here (v1 minimal; B10 may tighten), but the runner records the right one.
    fix_ref: Optional[str] = None
    rescope_rationale: Optional[str] = None
    # Same-day corrections when attribution changes (ST-09). Empty is the norm.
    revisions: List[AttributionRevision] = Field(default_factory=list)


class DispositionRecord(QAFormatModel):
    """F8 root model — every red for one run/campaign, each binned."""

    FORMAT_KIND: ClassVar[str] = "disposition-record"
    CURRENT_FORMAT_VERSION: ClassVar[str] = "1.0"

    run_id: str = Field(min_length=1)
    # An empty list is valid — a fully-green run closes with zero reds to bin.
    failures: List[FailureDisposition] = Field(default_factory=list)
