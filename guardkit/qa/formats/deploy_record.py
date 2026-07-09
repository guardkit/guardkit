"""F7 · deploy record (LPA-17) — session B10.

Instance: ``docs/state/<task>/deploy-record-<date>.md`` (house pattern) or
``deploys/<env>/<date>.md``. The house instance is markdown with dated addenda
accreting in place (the TASK-MP-012 addenda-1..7 pattern); this schema is the
machine-readable form the deploy stage writes and the completion gate reads —
the structured instance beside the human narrative (design core: "a
machine-readable format plus a gate that refuses to proceed without it").

The load-bearing rule (enforcement map): **a runtime claim with no artifact is
unverified by definition.** Every :class:`DeployClaim` therefore carries a
non-empty ``evidence_artifact`` (consumer-info JSON, boot-log lines, an image
digest, stream-info output) committed the same day as the claim — the model
refuses a claim without one.

Field list pinned by scope-design §2 (2026-07-07). Additions require a dated
note in that doc, never silent invention.
"""

from __future__ import annotations

from typing import ClassVar, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from guardkit.qa.formats.base import QAFormatModel

_DATE = r"^\d{4}-\d{2}-\d{2}$"


class DeployHeader(BaseModel):
    """Who/what/when of a deploy run."""

    model_config = ConfigDict(extra="forbid")

    env: str = Field(min_length=1)
    date: str = Field(pattern=_DATE)
    deployer: str = Field(min_length=1, description="Session id / operator")
    runbook_ref: Optional[str] = None
    deploy_profile_ref: Optional[str] = None


class DeployClaim(BaseModel):
    """One runtime claim + the same-day artifact that verifies it.

    ``evidence_artifact`` is required and non-empty: a runtime claim with no
    artifact is unverified by definition (F7 enforcement).
    """

    model_config = ConfigDict(extra="forbid")

    runtime_claim: str = Field(min_length=1)
    evidence_artifact: str = Field(
        min_length=1,
        description="consumer-info JSON, boot-log lines, image digest, stream info",
    )
    committed_at: str = Field(pattern=_DATE, description="Same day as the claim")


class DeployAddendum(BaseModel):
    """A dated incident section accreting in place (never a rewrite)."""

    model_config = ConfigDict(extra="forbid")

    date: str = Field(pattern=_DATE)
    note: str = Field(min_length=1)


class DeployRecord(QAFormatModel):
    """F7 root model — one deploy run's verifiable record."""

    FORMAT_KIND: ClassVar[str] = "deploy-record"
    CURRENT_FORMAT_VERSION: ClassVar[str] = "1.0"

    header: DeployHeader
    # A record with zero claims is a record that verifies nothing — at least one
    # runtime claim (each with its artifact) is required for a completed deploy.
    claims: List[DeployClaim] = Field(min_length=1)
    addenda: List[DeployAddendum] = Field(default_factory=list)
