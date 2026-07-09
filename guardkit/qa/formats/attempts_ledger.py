"""F9 · attempts ledger (ST-08) — session B4.

Instance: ``qa/attempts-<campaign>.yaml`` (or a RESULTS-file section) — referenced
by the results envelope's ``attempts_ledger_ref``.

The honest record of a *campaign*: every attempt at a live acceptance run, its
deployment state, the harness settings it used (and whether any were an
accommodation, not the contract), whether a warm-up was performed, what it
produced, the disposition refs for its reds, and — the load-bearing ST-08 rule —
the probes run *before* an expensive rerun. The five-attempt study-tutor
acceptance ledger (``study-tutor/docs/runbooks/RESULTS-study-tutor-p2-live-
acceptance-2026-07-05.md``) is the committed worked example, GPU-eviction
confound and all.

Two guardrails are structural, not advisory (WS2 build-plan §B4):

- **Accommodations are loud, named entries.** A :class:`HarnessSetting` whose
  ``status`` is ``accommodation`` MUST carry a ``reason`` and ``documented_where``
  — the model refuses to construct a silent accommodation. Product deadlines are
  never a harness setting here; the harness cannot stretch a product deadline
  (there is no field for it — the silent-deadline-stretch code path does not
  exist).
- **Probe-before-rerun is a checked field.** ``probes_run_first`` records the
  ST-08 probes; the campaign loop refuses an expensive rerun with an empty list.

> **B4 minimal definition (2026-07-09) — reconcile in B10.** F9's field list is
> defined here per scope-design §2 ahead of B10. B10 must retrofit/supersede this
> with a dated note if it diverges. See the WS2 build-plan §B4 / §B10 note.

Field list pinned by scope-design §2 (2026-07-07). Additions require a dated
note in that doc.
"""

from __future__ import annotations

from typing import ClassVar, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from guardkit.qa.formats.base import QAFormatModel

#: A harness setting is either the honest contract value, or an accommodation
#: (a deliberate deviation from contract) — which MUST be named.
HarnessSettingStatus = Literal["contract", "accommodation"]


class DeploymentState(BaseModel):
    """What was deployed for this attempt (the confound-analysis anchor)."""

    model_config = ConfigDict(extra="forbid")

    repo_shas: Dict[str, str] = Field(default_factory=dict)
    image_digests: Dict[str, str] = Field(default_factory=dict)
    backend_config: Optional[str] = Field(
        default=None, description="Human-readable backend config note (e.g. 'async Coach')"
    )


class HarnessSetting(BaseModel):
    """One harness parameter for an attempt — contract, or a named accommodation.

    An ``accommodation`` MUST carry ``reason`` and ``documented_where``: the
    validator rejects a silent accommodation, so the loud-named-entry guardrail
    cannot be bypassed by construction.
    """

    model_config = ConfigDict(extra="forbid")

    param: str = Field(min_length=1, description="e.g. 'turn_deadline_s'")
    status: HarnessSettingStatus
    value: Optional[str] = Field(default=None, description="The value used this attempt")
    vs_contract_value: Optional[str] = Field(
        default=None, description="The contract value this deviates from (accommodation)"
    )
    reason: Optional[str] = None
    documented_where: Optional[str] = None

    @model_validator(mode="after")
    def _accommodations_are_loud(self) -> "HarnessSetting":
        if self.status == "accommodation":
            missing = [
                name
                for name, val in (
                    ("reason", self.reason),
                    ("documented_where", self.documented_where),
                )
                if not (val and val.strip())
            ]
            if missing:
                raise ValueError(
                    f"harness setting {self.param!r} has status='accommodation' but "
                    f"is missing {missing} — an accommodation MUST be a loud, named "
                    f"entry (WS2 §B4 guardrail: no silent harness accommodation)."
                )
        return self


class Probe(BaseModel):
    """One ST-08 probe run before a rerun (probe-before-rerun evidence)."""

    model_config = ConfigDict(extra="forbid")

    probe_cmd: str = Field(min_length=1)
    finding: str = Field(min_length=1)


class Attempt(BaseModel):
    """One acceptance-run attempt."""

    model_config = ConfigDict(extra="forbid")

    n: int = Field(ge=1)
    date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    deployment_state: DeploymentState
    harness_settings: List[HarnessSetting] = Field(default_factory=list)
    warm_up_performed: bool = False
    result: str = Field(min_length=1, description="e.g. '22/35', '35/35'")
    passed: bool = Field(description="Did this attempt meet the pre-registered bar?")
    # Refs into the F8 disposition record for this attempt's reds (failure_ids).
    failure_disposition_refs: List[str] = Field(default_factory=list)
    probes_run_first: List[Probe] = Field(default_factory=list)


class AttemptsLedger(QAFormatModel):
    """F9 root model — the campaign's attempts, in order."""

    FORMAT_KIND: ClassVar[str] = "attempts-ledger"
    CURRENT_FORMAT_VERSION: ClassVar[str] = "1.0"

    campaign: str = Field(min_length=1)
    feature_id: str = Field(min_length=1)
    target_env: str = Field(min_length=1)
    attempts: List[Attempt] = Field(min_length=1)
