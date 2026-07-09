"""F12 · discovery-gate schema (W0) (ST-10) — session B10.

Instance: ``qa/discovery-gates-<feature>.yaml`` (the structured form of the W0
block that lives in a build-plan / feature doc). Exemplar source: study-tutor
W0 / R-G1..6 (``docs/runbooks/evidence/voice-w0-preflight-2026-07-05/EVIDENCE.md``).

Every external claim a build leans on is either **verified** (probed with the
consumer's REAL artifact, against the live system) or **gated** — a
pre-registered gate whose ``fallback`` was agreed BEFORE the run. Enforcement
(later, at the forge planning gate): build start is blocked while a load-bearing
claim is unprobed and ungated. The model makes that structural: a load-bearing
claim that is not ``verified`` MUST carry a gate with a pre-agreed fallback.

Field list pinned by scope-design §2 (2026-07-07). Additions require a dated
note in that doc, never silent invention.
"""

from __future__ import annotations

from typing import ClassVar, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from guardkit.qa.formats.base import QAFormatModel

#: How a claim resolved: probed-and-verified, or held behind a gate.
ClaimResult = Literal["verified", "gate"]

#: A gate's live status.
GateStatus = Literal["open", "passed", "failed", "fallback_taken"]


class Probe(BaseModel):
    """How the claim is probed — with the consumer's REAL artifact, live."""

    model_config = ConfigDict(extra="forbid")

    cmd: str = Field(min_length=1)
    consumer_artifact_shape: str = Field(
        min_length=1,
        description="Probe with the shape the consumer actually produces (not a proxy)",
    )
    run_against: Literal["live_system"] = "live_system"


class DiscoveryGateSpec(BaseModel):
    """The pre-registered gate guarding a not-yet-verified claim."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    pass_criteria: str = Field(min_length=1)
    # The fallback MUST be agreed BEFORE the run (ST-10) — not improvised after.
    fallback: str = Field(min_length=1, description="Pre-agreed BEFORE the run")
    evidence_file: Optional[str] = None
    status: GateStatus = "open"


class ExternalClaim(BaseModel):
    """One external claim a build leans on, probed or gated."""

    model_config = ConfigDict(extra="forbid")

    claim: str = Field(min_length=1)
    load_bearing: bool
    probe: Probe
    result: ClaimResult
    gate: Optional[DiscoveryGateSpec] = None

    @model_validator(mode="after")
    def _load_bearing_needs_gate_when_unverified(self) -> "ExternalClaim":
        if self.load_bearing and self.result != "verified" and self.gate is None:
            raise ValueError(
                f"load-bearing claim {self.claim!r} is not 'verified' but has no "
                f"gate — a load-bearing external claim must be probed-and-verified "
                f"OR carry a pre-agreed gate/fallback (ST-10; build start is "
                f"otherwise blocked)."
            )
        return self


class DiscoveryGates(QAFormatModel):
    """F12 root model — a feature's W0 discovery gates."""

    FORMAT_KIND: ClassVar[str] = "discovery-gates"
    CURRENT_FORMAT_VERSION: ClassVar[str] = "1.0"

    feature_id: str = Field(min_length=1)
    external_claims: List[ExternalClaim] = Field(min_length=1)
