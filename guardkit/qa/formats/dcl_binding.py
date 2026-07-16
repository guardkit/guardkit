"""F-format · dcl-binding — the J1–J3 (+ opt-in) binding table (D2, design §2).

Instance: one file per repo at ``qa/dcl/binding.yaml``.

The derivation rules R1–R10 (``api_test/qa/dcl-spike/derivation-rules.md``) are
mechanical GIVEN a small, fixed per-repo binding table. That table is exactly
the facts the DCL does not carry — the judgment flags J1–J3 the spike proved are
reusable across any HTTP capability:

    J1  capability intent -> HTTP verb + path      (``intents``)
    J2  success outcome -> HTTP status             (``success_status``, default 200)
    J3  DCL identifier -> wire key naming          (``naming``: camel_to_snake)

Two per-field opt-ins are also carried here, each FLAGGED in the derivation
receipt as the judgment it is (never silently applied):

    J5  a field's Text value has a concrete format (e.g. iso8601_utc) —
        ``fields.<camelName>.format``. R3 emits an extra ``A-<ABBR>-FORMAT``
        assertion ONLY when a field opts in.
    J6/J9 a field is the observable wire fact for a lifecycle state (nullable
        until the state is entered, then stable) — ``fields.<camelName>.state``.
        R6/R7 bind their post-transition / terminal-stability assertion to it.

``fields.<camelName>.abbrev`` is a short label used to build the assertion id
(``A-FIELD-<ABBR>``). Abbreviations (svc, req, fra) are a repo/feature labelling
choice the DCL does not carry, so they live in the binding — repo facts in the
binding table, feature facts in the ``.dcl``, rules in code once. When absent the
deriver falls back to the uppercased wire key.

Nothing beyond J1–J3 + these two flagged opt-ins lives here: J4/J7/J8 are DCL
v1.0 expressiveness gaps carried by pass-bars / unit tests (design §2), not the
binding. ``extra="forbid"`` so a stray key fails LOUD.
"""

from __future__ import annotations

from typing import ClassVar, Dict, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from guardkit.qa.formats.base import QAFormatModel


class IntentBinding(BaseModel):
    """J1 · a declared intent's HTTP invocation surface (verb + path)."""

    model_config = ConfigDict(extra="forbid")

    method: str = Field(min_length=1)
    path: str = Field(min_length=1)


class FieldBinding(BaseModel):
    """Per-field judgment opt-ins (each flagged in the derivation receipt).

    All optional — a field with no binding entry still yields its R3
    presence+type assertion (id from the uppercased wire key).
    """

    model_config = ConfigDict(extra="forbid")

    #: Short label for the assertion id (``A-FIELD-<ABBR>``). Default: wire key.
    abbrev: Optional[str] = None
    #: J5 opt-in: a concrete Text format the DCL cannot express (e.g. iso8601_utc).
    format: Optional[str] = None
    #: J6/J9 opt-in: the lifecycle state this field is the observable wire fact
    #: for (nullable until entered, stable once terminal). Binds R6/R7.
    state: Optional[str] = None


class CapabilityBinding(BaseModel):
    """The binding facts for one DCL capability."""

    model_config = ConfigDict(extra="forbid")

    #: J1 · intent name -> {method, path}. At least one (the invocation surface).
    intents: Dict[str, IntentBinding] = Field(min_length=1)
    #: J2 · the HTTP status a success outcome maps to.
    success_status: int = Field(default=200, ge=100, le=599)
    #: J3 · DCL identifier -> wire key convention. Only camel_to_snake in v1.0.
    naming: Literal["camel_to_snake"] = "camel_to_snake"
    #: Per-field judgment opt-ins, keyed by the DCL (camelCase) field name.
    fields: Dict[str, FieldBinding] = Field(default_factory=dict)


class DclBinding(QAFormatModel):
    """F-format · dcl-binding root model."""

    FORMAT_KIND: ClassVar[str] = "dcl-binding"
    CURRENT_FORMAT_VERSION: ClassVar[str] = "1.0"

    #: Capability name (as declared in the ``.dcl``) -> its binding.
    capabilities: Dict[str, CapabilityBinding] = Field(min_length=1)
