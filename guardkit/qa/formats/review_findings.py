"""F14 · review-findings / refutation record (LPA-14, LPA-15) — session B10.

Instance: ``qa/review-<id>.yaml`` — the structured form of the review block that
lives in ``docs/reviews/<id>.md``. Exemplar source: the forge FEAT-DD4F
post-merge review (16/16 findings survived, 0/32 refutations).

Two load-bearing rules are structural here:

- **Reading is not a verdict.** A ``confirmed`` finding MUST carry an
  ``executed_reproduction`` — the model refuses a confirmed finding without one
  (enforcement map: forge merge gate for agent-built features).
- **Adversarial by default.** Every critical/high finding carries ≥2 independent
  refuters, each defaulting to *refuted*; a finding survives only by surviving
  refutation.

The review subject may be a working TREE, not only a commit or merge — LPA-18:
an uncommitted tree is a reviewable surface.

Field list pinned by scope-design §2 (2026-07-07). Additions require a dated
note in that doc, never silent invention.
"""

from __future__ import annotations

from typing import ClassVar, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from guardkit.qa.formats.base import QAFormatModel

#: What was reviewed. A working tree (uncommitted) is reviewable (LPA-18).
SubjectKind = Literal["tree", "commit", "merge"]

#: A finding's severity.
Severity = Literal["critical", "high", "medium", "low"]

#: Did the finding survive verification?
FindingStatus = Literal["confirmed", "refuted"]

#: A single refuter's verdict (default refuted — a finding survives refutation).
RefuterVerdict = Literal["refuted", "not_refuted"]


class ReviewSubject(BaseModel):
    """What was reviewed and its reference."""

    model_config = ConfigDict(extra="forbid")

    kind: SubjectKind
    ref: str = Field(min_length=1, description="tree path / commit sha / merge ref")


class Refuter(BaseModel):
    """One independent attempt to refute a finding."""

    model_config = ConfigDict(extra="forbid")

    who: str = Field(min_length=1, description="Independent refuter id")
    verdict: RefuterVerdict = "refuted"
    note: Optional[str] = None


class Finding(BaseModel):
    """One review finding, verified adversarially."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    dimension: str = Field(min_length=1)
    severity: Severity
    status: FindingStatus
    summary: str = Field(min_length=1)
    # Required for confirmed — reading is not a verdict (LPA-15).
    executed_reproduction: Optional[str] = None
    refuters: List[Refuter] = Field(default_factory=list)

    @model_validator(mode="after")
    def _rigor(self) -> "Finding":
        if self.status == "confirmed" and not (
            self.executed_reproduction and self.executed_reproduction.strip()
        ):
            raise ValueError(
                f"finding {self.id!r} is 'confirmed' but has no "
                f"executed_reproduction — reading is not a verdict (LPA-15); a "
                f"confirmed finding must carry an executed reproduction."
            )
        if self.severity in {"critical", "high"} and len(self.refuters) < 2:
            raise ValueError(
                f"finding {self.id!r} is {self.severity!r} but has "
                f"{len(self.refuters)} refuter(s) — every critical/high finding "
                f"needs ≥2 independent refuters (LPA-14)."
            )
        return self


class ReviewStats(BaseModel):
    """The refutation tally (the review's honesty signal)."""

    model_config = ConfigDict(extra="forbid")

    findings_total: int = Field(ge=0)
    confirmed: int = Field(ge=0)
    refuted: int = Field(ge=0)
    refutations_attempted: int = Field(ge=0)


class ReviewFindings(QAFormatModel):
    """F14 root model — a review's findings + refutation record."""

    FORMAT_KIND: ClassVar[str] = "review-findings"
    CURRENT_FORMAT_VERSION: ClassVar[str] = "1.0"

    review_id: str = Field(min_length=1)
    subject: ReviewSubject
    dimensions: List[str] = Field(min_length=1)
    findings: List[Finding] = Field(default_factory=list)
    stats: ReviewStats
