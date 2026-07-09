"""F15 · walk-checkpoint schema (ST-07) — session B10.

Instance: ``qa/walk-<feature>.yaml`` — per-walk, written by ``/feature-spec``
(pre-registered) and executed by the walk driver (B5, scope-design §3). Exemplar
source: study-tutor retro §2 walk table.

The artifact under test IS the shipping composition (``build_cmd`` +
``compose_defines`` + ``install_cmd``) — a walk that builds something other than
what ships proves nothing. Every checkpoint is an act → verify → evidence step,
each with a negative-space assertion (what must be *absent*: an input disabled,
an affordance gone, an item dropped off the list). **Pass = every step
observed; an unobserved step is a failed step** — so this schema pre-registers
the steps a run must observe.

Field list pinned by scope-design §2 (2026-07-07). Additions require a dated
note in that doc, never silent invention.

> B5 (walk driver) is the consumer of this format. If B5 shipped an F15 minimal
> definition ahead of this session, this canonical schema supersedes it — the
> same hedge B4 carried for F8/F9 (WS2 build-plan §0 note on the F15 edge).
"""

from __future__ import annotations

from typing import Any, ClassVar, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from guardkit.qa.formats.base import QAFormatModel

#: The kind of act a checkpoint performs on the device.
ActKind = Literal["tap", "text", "curl", "wait", "none"]


class WalkArtifact(BaseModel):
    """How the artifact-under-test is built + installed (the shipping composition)."""

    model_config = ConfigDict(extra="forbid")

    build_cmd: str = Field(min_length=1)
    # The compile-time defines that make it the REAL flavour (e.g. --dart-define).
    compose_defines: List[str] = Field(default_factory=list)
    install_cmd: str = Field(min_length=1)


class WalkPrecondition(BaseModel):
    """A pre-walk condition (health check, model warm-up, documented blank slate)."""

    model_config = ConfigDict(extra="forbid")

    health_check_cmd: Optional[str] = None
    warm_up_action: Optional[str] = None
    blank_slate: Optional[str] = Field(
        default=None, description="The documented blank starting state"
    )


class WalkAct(BaseModel):
    """The act half of a checkpoint (what the driver does)."""

    model_config = ConfigDict(extra="forbid")

    kind: ActKind
    params: Dict[str, Any] = Field(default_factory=dict)
    coordinate_scaling_note: Optional[str] = Field(
        default=None, description="How screen coords scale for tap (device-specific)"
    )
    wait_s: Optional[float] = Field(
        default=None, description="Wait sized to the operation (~20s for LLM turns)"
    )


class WalkCheckpoint(BaseModel):
    """One pre-registered act → verify → evidence step."""

    model_config = ConfigDict(extra="forbid")

    n: int = Field(ge=1)
    act: WalkAct
    verify: str = Field(min_length=1, description="The expected observable state")
    evidence_artifact: str = Field(
        min_length=1, description="The named screenshot/artifact this step produces"
    )
    # What must be ABSENT — the negative-space assertion (LPA-04 discipline).
    negative_space: Optional[str] = None


class WalkCheckpoints(QAFormatModel):
    """F15 root model — one pre-registered device walk."""

    FORMAT_KIND: ClassVar[str] = "walk-checkpoints"
    CURRENT_FORMAT_VERSION: ClassVar[str] = "1.0"

    feature_id: str = Field(min_length=1)
    artifact: WalkArtifact
    preconditions: List[WalkPrecondition] = Field(default_factory=list)
    checkpoints: List[WalkCheckpoint] = Field(min_length=1)
