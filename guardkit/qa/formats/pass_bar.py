"""F1 · pass-bar block (ST-01, ST-12; LPA-04).

Instance: ``qa/pass-bar-<TASK-ID>.yaml`` (or a ``pass_bar:`` block in the
task/feature doc), committed BEFORE implementation; ``registered_at``
{sha, date} must predate implementation commits — that ordering is
mechanically checkable but is NOT checked here: the Coach task-start
precondition is session B2's enforcement, this module is schema only.

WS1 CONTRACT (FEAT-SPL-007/008 — flagged for the WS1 sessions):
    The headless ``/feature-spec`` + ``/feature-plan`` tools are the named
    WRITERS of this block (scope-design §2 F1 "Writers"). Every field on
    ``PassBar`` below is a field WS1's emitters must produce — in particular
    ``task_id``, ``registered_at``, ``preconditions``, ``criteria`` (with the
    machine|operator class split and per-criterion ``evidence_kind``),
    ``auth_surface_bearing`` (PB-14 — see below), ``negative_paths`` (required
    minimum set, conditional on ``auth_surface_bearing``), and
    ``checkpoint_list_ref`` (the F15 walk-checkpoint file, also WS1-emitted for
    walk-bearing features). If a field here changes, the WS1↔WS2 contract note
    in both build plans must change with it.

Readers: Coach (task start), live-gate runner (its criteria ARE the gate),
feature-complete. Operator-class criteria are barred from the checker loop
and routed to an ``operator_handoff`` runbook (ST-12) — never silently
dropped (enforced in B2/B3, not here).

Field list pinned by scope-design §2 (2026-07-07). Additions require a dated
note in that doc.

PB-14 (DECISION-DF-012 rider 1, 2026-07-08 — via this format's own dated-note
evolution channel, NOT a reopen of the frozen ``b9f5eff8`` formats): the four
auth-shaped negative paths (``wrong_credential``, ``anonymous_deep_link``,
``post_logout_401``, ``unauthorized_403_ui``) are now CONDITIONAL on the new
required ``auth_surface_bearing`` flag; ``dependency_down_degradation`` stays
mandatory for EVERY bar. An emitter for an authless feature (CLI / library /
pipeline) can now write an honest bar instead of fabricating four auth paths
it has no surface for — day-one fabricated bars would poison the QAV eval
corpus at birth. Auth-surface-bearing features keep all five mandatory (the
study-tutor Flutter fixture proves the full set maps honestly). The flag is
required with NO default: guessing it (statically or from other fields) re-
introduces the very fabrication hazard the flag exists to close, so an emitter
must state it explicitly. Adding a required field is a breaking change, so the
schema majors to 2.0 (base.py additive-vs-breaking convention); B2/B3 per-path
evidence enforcement keys on the same flag.
"""

from __future__ import annotations

from typing import ClassVar, List, Literal, Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationInfo,
    field_validator,
    model_validator,
)

from guardkit.qa.formats.base import QAFormatModel

#: The negative path mandatory for EVERY pass bar, auth-surface-bearing or not
#: (PB-14): a feature with a dependency it can degrade against must prove the
#: degraded path. There is no honest bar without it.
UNIVERSAL_NEGATIVE_PATHS: frozenset = frozenset({"dependency_down_degradation"})

#: The four auth-surface-shaped negative paths. Mandatory only when the bar
#: declares ``auth_surface_bearing: true`` — an authless feature has no auth
#: surface to exercise these against, and requiring them would force fabrication
#: (PB-14 / DECISION-DF-012 rider 1).
AUTH_NEGATIVE_PATHS: frozenset = frozenset(
    {
        "wrong_credential",
        "anonymous_deep_link",
        "post_logout_401",
        "unauthorized_403_ui",
    }
)

#: The scope-design §2 F1 "required minimum set" of negative paths for an
#: auth-surface-bearing bar — all five. A path with an auth surface that does
#: not declare all five is invalid; negative paths are mandatory (LPA-04) and
#: each declared path must be evidenced by a criterion at gate time (B3's job).
REQUIRED_NEGATIVE_PATHS: frozenset = AUTH_NEGATIVE_PATHS | UNIVERSAL_NEGATIVE_PATHS

Precondition = Literal["suite_green_vs_ledger", "analyze_clean", "build_artifact"]


class RegisteredAt(BaseModel):
    """Where/when the pass bar was pinned — must predate implementation."""

    model_config = ConfigDict(extra="forbid")

    sha: str = Field(min_length=4)
    date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")


class PassBarCriterion(BaseModel):
    """One observable acceptance criterion (behaviour, not activity)."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    # "class" is a Python keyword; the YAML key stays `class:` via the alias.
    criterion_class: Literal["machine", "operator"] = Field(alias="class")
    evidence_kind: Literal["screenshot", "json", "log", "operator_signoff"]
    runbook_ref: Optional[str] = None

    @model_validator(mode="after")
    def _operator_needs_runbook(self) -> "PassBarCriterion":
        # scope-design §2 F1: runbook_ref required when class=operator — an
        # operator criterion with nowhere to route is a silently-dropped
        # criterion (ST-12).
        if self.criterion_class == "operator" and not self.runbook_ref:
            raise ValueError(
                f"criterion {self.id!r}: class=operator requires runbook_ref "
                f"(operator criteria route to an operator_handoff runbook, "
                f"never the checker loop)"
            )
        return self


class PassBar(QAFormatModel):
    """F1 root model — see module docstring for the WS1 writer contract."""

    FORMAT_KIND: ClassVar[str] = "pass-bar"
    # 2.0 — PB-14 added the required `auth_surface_bearing` field (a breaking
    # change: an existing 1.0 bar without it no longer validates and must be
    # migrated). Majored per base.py's additive-vs-breaking convention.
    CURRENT_FORMAT_VERSION: ClassVar[str] = "2.0"

    task_id: str = Field(min_length=1)
    registered_at: RegisteredAt
    # PB-14 (DECISION-DF-012 rider 1): does this feature expose an auth surface?
    # Required with NO default — an emitter must declare it, because guessing it
    # re-opens the fabrication hazard the flag closes. `true` keeps all five
    # negative paths mandatory; `false` requires only dependency_down_degradation
    # (the four auth paths become optional). Declared BEFORE `negative_paths` so
    # the negative-path validator can read it from ValidationInfo.data.
    auth_surface_bearing: bool
    preconditions: List[Precondition] = Field(min_length=1)
    criteria: List[PassBarCriterion] = Field(min_length=1)
    negative_paths: List[str] = Field(min_length=1)
    # F15 walk-checkpoint file ref (tier 3, schema in B10). Optional: not every
    # feature has a walk; a walk-bearing feature without it fails at B3's gate,
    # not here.
    checkpoint_list_ref: Optional[str] = None

    @field_validator("negative_paths")
    @classmethod
    def _minimum_negative_set(
        cls, value: List[str], info: ValidationInfo
    ) -> List[str]:
        # PB-14: the required set is conditional on auth_surface_bearing. When
        # that field failed its own validation (or is absent) it is not in
        # info.data — fall back to the strict all-five set so an incomplete bar
        # is never waved through on a missing flag (an absent flag must not
        # relax the gate).
        auth_bearing = info.data.get("auth_surface_bearing", True)
        required = (
            REQUIRED_NEGATIVE_PATHS if auth_bearing else UNIVERSAL_NEGATIVE_PATHS
        )
        missing = required - set(value)
        if missing:
            if auth_bearing:
                # Message shape preserved verbatim (auth-bearing = the pre-PB-14
                # contract): all five required.
                raise ValueError(
                    f"negative_paths is missing the required minimum set entries "
                    f"{sorted(missing)} (scope-design §2 F1). Declare all five; "
                    f"extras are allowed."
                )
            raise ValueError(
                f"negative_paths is missing {sorted(missing)} "
                f"(scope-design §2 F1, PB-14). dependency_down_degradation is "
                f"mandatory for every pass bar, auth-surface-bearing or not."
            )
        return value

    @field_validator("criteria")
    @classmethod
    def _unique_criterion_ids(cls, value: List[PassBarCriterion]) -> List[PassBarCriterion]:
        ids = [c.id for c in value]
        dupes = {i for i in ids if ids.count(i) > 1}
        if dupes:
            raise ValueError(f"duplicate criterion ids: {sorted(dupes)}")
        return value
