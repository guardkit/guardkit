"""F3 · leak-sweep manifest (LPA-05).

Instance: ``qa/leak-sweep.yaml`` per app repo.

Seed: the hard-coded MOCK_NAMES deny-list + DONOR_PAGES/ATTORNEY_PAGES scope
map in ``lpa-platform-poc/qa/gates/gate_phase6_sweep.py`` (rescued in session
B0, commit 8980af1). This format is that knowledge as data: which surfaces are
claimed real, what strings/patterns must never appear inside a claimed-real
scope, and which regions are mock BY DESIGN (allowed, with a reason).

Writers: ``/feature-plan`` claims surfaces as real; the Player updates entries
as surfaces land. Readers: the live-gate runner sweep step (B3). Enforcement
(any mock identity/placeholder URL/fake count inside a claimed-real scope is a
red; a claimed-real surface with no manifest entry blocks the gate) is B2/B3 —
this module is schema only.

Stack-blind by design (scope-design §2 evolution rules): this format drives
the deployed artifact, so no framework/language field.

Note: scope-design §2's F3 field list opens with ``version`` — realized here
as the common ``format_version`` every instance carries (same field, canonical
name; not an addition).

Field list pinned by scope-design §2 (2026-07-07). Additions require a dated
note in that doc.
"""

from __future__ import annotations

from typing import ClassVar, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from guardkit.qa.formats.base import QAFormatModel


class Persona(BaseModel):
    """A login identity the sweep runs as (every claimed surface, every persona)."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    login_role: str = Field(min_length=1)
    # A REFERENCE (env var name, register key) — never a credential value.
    credentials_ref: str = Field(min_length=1)


class DenyPatterns(BaseModel):
    """Strings/patterns that must never appear inside a claimed-real scope."""

    model_config = ConfigDict(extra="forbid")

    identity_strings: List[str] = Field(default_factory=list)
    count_patterns: List[str] = Field(default_factory=list)
    url_patterns: List[str] = Field(default_factory=list)
    badge_patterns: List[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _not_all_empty(self) -> "DenyPatterns":
        if not (
            self.identity_strings
            or self.count_patterns
            or self.url_patterns
            or self.badge_patterns
        ):
            raise ValueError(
                "deny must carry at least one pattern — an empty deny-list "
                "sweeps for nothing and passes vacuously"
            )
        return self


class AllowedMockRegion(BaseModel):
    """A region that stays mock by design — allowed, with a reason on record."""

    model_config = ConfigDict(extra="forbid")

    selector: str = Field(min_length=1)
    reason: str = Field(min_length=1)


class Surface(BaseModel):
    """One claimed-real surface the sweep must cover."""

    model_config = ConfigDict(extra="forbid")

    route: str = Field(min_length=1)
    # The task/feature id that claimed this surface as real.
    claimed_by: str = Field(min_length=1)
    scope: Literal["full_page", "scoped"]
    # Required when scope=scoped: the selector bounding the wired (real)
    # region — everything outside it is not swept (mock by design).
    wired_selector: Optional[str] = None
    allowed_mock_regions: List[AllowedMockRegion] = Field(default_factory=list)
    extra_deny: List[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _scoped_needs_selector(self) -> "Surface":
        if self.scope == "scoped" and not self.wired_selector:
            raise ValueError(
                f"surface {self.route!r}: scope=scoped requires wired_selector "
                f"(the sweep must know which region is claimed real)"
            )
        return self


class LeakSweepManifest(QAFormatModel):
    """F3 root model."""

    FORMAT_KIND: ClassVar[str] = "leak-sweep"
    CURRENT_FORMAT_VERSION: ClassVar[str] = "1.0"

    personas: List[Persona] = Field(min_length=1)
    deny: DenyPatterns
    surfaces: List[Surface] = Field(min_length=1)
