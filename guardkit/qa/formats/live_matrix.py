"""F10 · live-validation hop/scenario matrix (LPA-21, LPA-20) — session B10.

Instance: ``qa/live-matrix-<feature>.yaml``, a planning artifact.

Every load-bearing hop is **assumed defective until driven** — defects stack
behind unexercised hops, so the runner orders the riskiest / never-driven hop
first, and feature-complete requires every load-bearing hop driven or explicitly
waived with rationale (enforcement map). The scenario rows carry the
``human_latency_sensitive`` flag (timeouts validated against real human
response times, LPA-20) and the ``redrive_policy`` (re-drive end-to-end after
each fix).

Field list pinned by scope-design §2 (2026-07-07). Additions require a dated
note in that doc, never silent invention.
"""

from __future__ import annotations

from typing import ClassVar, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from guardkit.qa.formats.base import QAFormatModel

_DATE = r"^\d{4}-\d{2}-\d{2}$"


class ValidationDebt(BaseModel):
    """When a hop was last driven end-to-end, and the evidence for it."""

    model_config = ConfigDict(extra="forbid")

    last_driven: str = Field(description="A YYYY-MM-DD date, or the literal 'never'")
    evidence_ref: Optional[str] = None

    @field_validator("last_driven")
    @classmethod
    def _date_or_never(cls, value: str) -> str:
        import re

        if value == "never" or re.match(_DATE, value):
            return value
        raise ValueError(
            f"last_driven must be a YYYY-MM-DD date or 'never', got {value!r}"
        )


class Hop(BaseModel):
    """One validation hop (a boundary the live path crosses)."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    risk_rank: int = Field(ge=1, description="1 = highest risk (driven first)")
    validation_debt: ValidationDebt
    # A hop is assumed defective until it has actually been driven (LPA-21).
    assumed_defective_until_driven: bool = True
    load_bearing: bool = Field(
        default=True,
        description="Load-bearing hops gate feature-complete unless waived",
    )
    waiver_rationale: Optional[str] = Field(
        default=None,
        description="Required to feature-complete a load-bearing, undriven hop",
    )


class Scenario(BaseModel):
    """One end-to-end scenario, and which hops it covers."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    hops_covered: List[str] = Field(min_length=1)
    human_latency_sensitive: bool = Field(
        default=False,
        description="True when timeouts must be validated against human response times",
    )
    result: Optional[str] = None
    evidence: Optional[str] = None


class LiveMatrix(QAFormatModel):
    """F10 root model — a feature's hop/scenario validation matrix."""

    FORMAT_KIND: ClassVar[str] = "live-matrix"
    CURRENT_FORMAT_VERSION: ClassVar[str] = "1.0"

    feature_id: str = Field(min_length=1)
    hops: List[Hop] = Field(min_length=1)
    scenarios: List[Scenario] = Field(default_factory=list)
    redrive_policy: str = Field(
        min_length=1,
        description="After each fix, re-drive end-to-end (defects stack behind unexercised hops)",
    )
