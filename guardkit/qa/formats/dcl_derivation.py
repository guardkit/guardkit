"""F-format · dcl-derivation — the derivation receipt (D2, design §2).

Instance: one file per derived feature at ``qa/dcl/derivation-<FEATURE>.yaml``,
written beside the derived assertion set (``qa/dcl/derived/<FEATURE>.yaml``) by
:mod:`guardkit.qa.dcl.deriver`.

The receipt is the audit trail of a derivation run: which ``.dcl`` (path + sha)
was compiled, the checker envelope summary, which binding (sha) supplied the
J-facts, which rules fired (with counts), which judgment flags were used, the
assertion ids by disposition (RUN / SKIP), and the tool + upstream pin identity.
Registered like every other kind, so ``guardkit qa validate/schema/kinds`` work
on it for free. ``extra="forbid"`` — a stray key fails LOUD.
"""

from __future__ import annotations

from typing import ClassVar, Dict, List

from pydantic import BaseModel, ConfigDict, Field

from guardkit.qa.formats.base import QAFormatModel


class CheckerSummary(BaseModel):
    """The compile-gate outcome the receipt was derived from."""

    model_config = ConfigDict(extra="forbid")

    ok: bool
    error_count: int = Field(ge=0)
    warning_count: int = Field(ge=0)


class AssertionsByDisposition(BaseModel):
    """Derived assertion ids, partitioned by disposition."""

    model_config = ConfigDict(extra="forbid")

    run: List[str] = Field(default_factory=list)
    skip: List[str] = Field(default_factory=list)


class ToolIdentity(BaseModel):
    """The deriver + the vendored checker pin that produced this receipt."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    checker_pin: str = Field(min_length=1)


class DclDerivation(QAFormatModel):
    """F-format · dcl-derivation root model."""

    FORMAT_KIND: ClassVar[str] = "dcl-derivation"
    CURRENT_FORMAT_VERSION: ClassVar[str] = "1.0"

    feature: str = Field(min_length=1)
    capability: str = Field(min_length=1)
    source_dcl: str = Field(min_length=1)
    source_dcl_sha256: str = Field(min_length=64, max_length=64)
    checker: CheckerSummary
    binding_sha256: str = Field(min_length=64, max_length=64)
    #: rule id (e.g. "R3") -> number of assertions it fired.
    rules_fired: Dict[str, int] = Field(default_factory=dict)
    #: The judgment flags (J1..J9) any derived assertion needed.
    judgment_flags: List[str] = Field(default_factory=list)
    assertions: AssertionsByDisposition
    tool: ToolIdentity
