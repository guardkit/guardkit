"""F2 · known-failure ledger (LPA-09).

Instance: ``qa/known-failures.yaml`` per repo.

Lifted from the lpa practice ("1021 passed + these 2 transformers-import
failures, for this reason" — lpa retro :49-52): the expected suite outcome is
DOCUMENTED, and every run is compared against the ledger, not against "all
green". A failure not in the ledger fails the gate even if totals look
plausible; an unexpectedly-passing ledger entry ALSO fails (stale ledger is a
finding).

Writers: human/Coach at triage time only — never the Player mid-build (that
would neuter LPA-09; the no-Player-append code path is a B2 guardrail).
Readers: guardkit suite gate + ``completion_verification.py`` post-merge sweep
(the enforcement point already exists in embryo there — wired in B2, NOT here).

Language-agnostic by construction (scope-design §2 evolution rules, added
2026-07-07): consuming this ledger means parsing per-stack suite output, so the
instance carries explicit ``framework``/``language`` fields and the B2
enforcement point routes through a per-framework adapter (pytest is adapter #1;
``dotnet test``/jest/``flutter test`` are future adapters — adapter work, never
schema redesign).

Field list pinned by scope-design §2 (2026-07-07). Additions require a dated
note in that doc.
"""

from __future__ import annotations

from typing import ClassVar, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from guardkit.qa.formats.base import QAFormatModel


class ExpectedOutcome(BaseModel):
    """The documented expected suite outcome ("1021 passed")."""

    model_config = ConfigDict(extra="forbid")

    passed: int = Field(ge=0)


class SinceRef(BaseModel):
    """When the failure entered the ledger."""

    model_config = ConfigDict(extra="forbid")

    date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    sha: str = Field(min_length=4)


class KnownFailureEntry(BaseModel):
    """One triaged, documented failure."""

    model_config = ConfigDict(extra="forbid")

    test_id: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    # Optional: a failure may be unconditional; when set, names the environment
    # condition under which the failure manifests (e.g. "local env only").
    env_condition: Optional[str] = None
    since: SinceRef
    owner: str = Field(min_length=1)
    # A ledger entry is temporary by intent — review_by keeps it from rotting.
    review_by: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    tracking_ref: Optional[str] = None


class KnownFailureLedger(QAFormatModel):
    """F2 root model."""

    FORMAT_KIND: ClassVar[str] = "known-failures"
    CURRENT_FORMAT_VERSION: ClassVar[str] = "1.0"

    suite_id: str = Field(min_length=1)
    # Per-framework adapter routing (see module docstring): the enforcement
    # point picks its suite-output parser from these, never by sniffing.
    framework: str = Field(min_length=1)
    language: str = Field(min_length=1)
    expected: ExpectedOutcome
    # An empty list is valid — a fully-green suite still documents its
    # expected outcome so a new failure is a diff, not a shrug.
    known_failures: List[KnownFailureEntry] = Field(default_factory=list)
