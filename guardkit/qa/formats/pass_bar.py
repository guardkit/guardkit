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
    ``negative_paths`` (required minimum set), and ``checkpoint_list_ref``
    (the F15 walk-checkpoint file, also WS1-emitted for walk-bearing
    features). If a field here changes, the WS1↔WS2 contract note in both
    build plans must change with it.

Readers: Coach (task start), live-gate runner (its criteria ARE the gate),
feature-complete. Operator-class criteria are barred from the checker loop
and routed to an ``operator_handoff`` runbook (ST-12) — never silently
dropped (enforced in B2/B3, not here).

Field list pinned by scope-design §2 (2026-07-07). Additions require a dated
note in that doc.
"""

from __future__ import annotations

from typing import ClassVar, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from guardkit.qa.formats.base import QAFormatModel

#: The scope-design §2 F1 "required minimum set" of negative paths. A pass bar
#: that does not declare all five is invalid — negative paths are mandatory
#: (LPA-04), and each declared path must be evidenced by a criterion at gate
#: time (B3's job).
REQUIRED_NEGATIVE_PATHS: frozenset = frozenset(
    {
        "wrong_credential",
        "anonymous_deep_link",
        "post_logout_401",
        "unauthorized_403_ui",
        "dependency_down_degradation",
    }
)

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
    CURRENT_FORMAT_VERSION: ClassVar[str] = "1.0"

    task_id: str = Field(min_length=1)
    registered_at: RegisteredAt
    preconditions: List[Precondition] = Field(min_length=1)
    criteria: List[PassBarCriterion] = Field(min_length=1)
    negative_paths: List[str] = Field(min_length=1)
    # F15 walk-checkpoint file ref (tier 3, schema in B10). Optional: not every
    # feature has a walk; a walk-bearing feature without it fails at B3's gate,
    # not here.
    checkpoint_list_ref: Optional[str] = None

    @field_validator("negative_paths")
    @classmethod
    def _minimum_negative_set(cls, value: List[str]) -> List[str]:
        missing = REQUIRED_NEGATIVE_PATHS - set(value)
        if missing:
            raise ValueError(
                f"negative_paths is missing the required minimum set entries "
                f"{sorted(missing)} (scope-design §2 F1). Declare all five; "
                f"extras are allowed."
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
