"""F-format · dcl-authoring — the seat-authoring receipt (W1-S1).

Instance: one file per authored feature at ``qa/dcl/authoring-<FEATURE>.yaml``,
written by :mod:`guardkit.qa.dcl.author` on BOTH a successful author and a loud
authoring failure (never on an exit-2 instrument fault — nothing is written then).

The receipt is the audit trail of a §10 authoring run: the model/endpoint, the
pinned sampling, the prompt shas + composition, the sha-pinned vocab reference,
how many attempts fired (≤2), the zero-shot vs repaired clean split, the checker
envelope summary for each attempt, the single-slot probe records, wall times,
finish reasons, and — when the author did NOT land — the loud ``failure_reason``.

Registered like every other kind, so ``guardkit qa validate/schema/kinds`` work
on it for free. ``extra="forbid"`` everywhere — a stray key fails LOUD.
"""

from __future__ import annotations

from typing import ClassVar, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from guardkit.qa.formats.base import QAFormatModel


class AuthoringSampling(BaseModel):
    """The pinned §10 decoding parameters the seat ran under."""

    model_config = ConfigDict(extra="forbid")

    temperature: float
    top_p: float
    max_tokens: int = Field(ge=1)


class AuthoringPrompt(BaseModel):
    """The composed authoring turn's provenance (shas + a composition note)."""

    model_config = ConfigDict(extra="forbid")

    system_sha256: str = Field(min_length=64, max_length=64)
    prompt_sha256: str = Field(min_length=64, max_length=64)
    composition: str = Field(min_length=1)


class AuthoringVocabRef(BaseModel):
    """The sha-pinned standing vocabulary reference that was appended."""

    model_config = ConfigDict(extra="forbid")

    path: str = Field(min_length=1)
    sha256: str = Field(min_length=64, max_length=64)


class AuthoringEnvelope(BaseModel):
    """A checker envelope summary for one attempt."""

    model_config = ConfigDict(extra="forbid")

    ok: bool
    error_count: int = Field(ge=0)
    warning_count: int = Field(ge=0)
    error_codes: List[str] = Field(default_factory=list)


class AuthoringEnvelopes(BaseModel):
    """Per-attempt checker summaries (attempt2 present iff the repair pass fired)."""

    model_config = ConfigDict(extra="forbid")

    attempt1: AuthoringEnvelope
    attempt2: Optional[AuthoringEnvelope] = None


class SingleSlotProbe(BaseModel):
    """One ``/running`` single-slot probe record (one per seat call)."""

    model_config = ConfigDict(extra="forbid")

    url: str = Field(min_length=1)
    ok: bool


class AuthoringFinishReasons(BaseModel):
    """The seat's finish_reason per attempt (attempt2 nullable)."""

    model_config = ConfigDict(extra="forbid")

    attempt1: Optional[str] = None
    attempt2: Optional[str] = None


class AuthoringToolIdentity(BaseModel):
    """The authoring tool + the vendored checker pin that produced this receipt."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    checker_pin: str = Field(min_length=1)


class DclAuthoring(QAFormatModel):
    """F-format · dcl-authoring root model."""

    FORMAT_KIND: ClassVar[str] = "dcl-authoring"
    CURRENT_FORMAT_VERSION: ClassVar[str] = "1.0"

    feature: str = Field(min_length=1)
    task: str = Field(min_length=1)
    capability: Optional[str] = None
    authored: bool
    #: Repo-relative path of the written artifact — null on an authoring failure.
    artifact: Optional[str] = None
    model: str = Field(min_length=1)
    endpoint: str = Field(min_length=1)
    sampling: AuthoringSampling
    prompt: AuthoringPrompt
    vocab_ref: AuthoringVocabRef
    attempts: int = Field(ge=1, le=2)
    zero_shot_clean: bool
    repaired_clean: Optional[bool] = None
    envelopes: AuthoringEnvelopes
    single_slot_probes: List[SingleSlotProbe] = Field(default_factory=list)
    wall_time_s: float = Field(ge=0)
    repair_wall_time_s: Optional[float] = None
    finish_reasons: AuthoringFinishReasons
    failure_reason: Optional[str] = None
    tool: AuthoringToolIdentity
