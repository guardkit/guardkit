"""deploy-profile · per-repo deploy profile (``deploy/profile.yaml``) — session B10.

A tier-2 format (scope-design §4) even though **forge** is its consumer: the
DEPLOY stage reads it to render a typed runbook (reservation → pre-flight →
compose → seeds → warm models → health checks). B10 owns the canonical schema;
WS2-B8 built the forge *loader* (``forge/src/forge/deploy/profile.py``) against
scope-§4 ahead of B10 and filed a dated reconcile note
(``forge/docs/state/WS2-B8/deploy-profile-format-reconcile-note-2026-07-09.md``).

This canonical model is a faithful **superset** of the B8 loader shape, so a
conforming instance validates here AND is accepted by the B8 loader:

- ``env_id`` + ``compose.file`` are the only strictly-required fields.
- ``compose`` canonizes B8's ``{file, profile, script, env_file}`` (the deploy
  wrapper bridge — the FMDR ``deploy_compose`` step wraps a vetted deploy
  script, never freehand shell; the D12 safety property). [B10 reconcile 1]
- ``secret_injection`` entries are register key **NAMES only** (WS5 owns values);
  a value-bearing entry (``=``, URL/DSN shape, whitespace) is refused, mirroring
  the B8 guardrail. [B10 reconcile 2]
- ``models_required`` accepts a bare model-name string or ``{model,
  warm_up_action}`` (B8 convenience, canonized).
- ``cwd`` (working dir for the wrapped scripts) is canonized as a top-level field.

Guardrail (WS5 boundary): secrets are register REFS ONLY — names, never values.
The FLEET_MEMORY_PG_DSN leak of 2026-07-04 is exactly why.

Field list pinned by scope-design §4 (2026-07-07) + the B8 reconcile note.
Additions require a dated note, never silent invention.

Dated additions:

- 2026-07-16 (C4-prep, superset-invariant restore): ``rollback_image_ref`` —
  the kept ``:rollback-*`` image tag the O-32 revert re-deploys on a failing
  live gate; the B8 loader has carried it since WS2-C1, so a profile that set
  it failed here while the DEPLOY stage required it. ``live_gate`` — the
  per-target F16 repo-driver backend (forge loader ``b101933``): the target
  repo's own honest live-gate driver argv (+ optional gate subset, timeout,
  NON-SECRET UPPER_SNAKE env overlay). Absent ⇒ the deploy stage's live-gate
  seam stays Unconfigured and loud-fails (deny by default). Field parity with
  ``forge.deploy.profile._parse_live_gate`` is proven by the B8 seam test.

- 2026-07-16 (S2F, candidate-then-promote): ``candidate`` — the optional
  execution-surface overlay (forge loader ``c20f28e``). When present, the
  DEPLOY stage stands the build up first under a SEPARATE ``<live>-cand``
  compose project, gates it, and re-tags-and-promotes it to the live name only
  on a PASS — the live name is never touched by a candidate that fails. Its
  ``env`` (NON-SECRET UPPER_SNAKE overlay, e.g. ``CANDIDATE_PORT``) is threaded,
  alongside ``CANDIDATE=1``, to the candidate-leg compose / health-check /
  live-gate driver so they address the candidate instance; ``keep`` (default
  False) leaves the candidate project up after a successful promote. Absent ⇒
  byte-identical to the direct-live flow. Field parity with
  ``forge.deploy.profile._parse_candidate`` is proven by the B8 seam test.
"""

from __future__ import annotations

import re
from typing import Any, ClassVar, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from guardkit.qa.formats.base import QAFormatModel

#: A register-key NAME (letters, digits, and the . _ - separators of env-var /
#: dotted / scoped keys). Anything else marks a smuggled VALUE — refused.
#: Mirrors ``forge.deploy.profile._REF_NAME_RE`` (WS2-B8 guardrail).
_REF_NAME_RE = re.compile(r"^[A-Za-z0-9._-]+$")


class ComposeSpec(BaseModel):
    """The compose invocation for the ``deploy_compose`` step."""

    model_config = ConfigDict(extra="forbid")

    file: str = Field(min_length=1, description="The compose file path")
    profile: Optional[str] = None
    # The B8→B10 bridge: the FMDR deploy_compose step wraps a vetted deploy
    # script rather than inline `docker compose`. Canonized here (reconcile 1).
    script: Optional[str] = None
    env_file: Optional[str] = None


class DeployHost(BaseModel):
    """One host in the deploy target set."""

    model_config = ConfigDict(extra="forbid")

    host: str = Field(min_length=1)
    role: str = Field(min_length=1)


class SeedFixture(BaseModel):
    """One seed-fixture contract entry."""

    model_config = ConfigDict(extra="forbid")

    script: str = Field(min_length=1)
    golden_state_ref: Optional[str] = None


class ModelRequirement(BaseModel):
    """A required llama-swap model plus its warm-up action."""

    model_config = ConfigDict(extra="forbid")

    model: str = Field(min_length=1)
    warm_up_action: Optional[str] = None


class HealthCheck(BaseModel):
    """One health-check command + its expected signal."""

    model_config = ConfigDict(extra="forbid")

    cmd: str = Field(min_length=1)
    expected: Optional[str] = None


class Reservation(BaseModel):
    """The environment-reservation lease request."""

    model_config = ConfigDict(extra="forbid")

    resource: str = Field(min_length=1)
    quiet_window: Optional[str] = None


#: An UPPER_SNAKE env-var NAME for the live-gate driver's non-secret overlay.
#: Mirrors ``forge.deploy.profile._ENV_NAME_RE`` (parity proven by the seam test).
_LIVE_GATE_ENV_NAME_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")


class LiveGateSpec(BaseModel):
    """The per-target live-gate driver spec (the F16 real backend, C4-prep).

    Names the target repo's own live-gate driver — the honest per-target
    command that injects a minimal F16 perishable-prereq provider into the
    UNMODIFIED guardkit ``LiveGateRunner`` (see the forge
    ``RepoDriverLiveGateInvoker`` for the full F16 story). Absent from a
    profile ⇒ the deploy stage's live-gate seam stays Unconfigured and
    loud-fails (deny by default — a fake pass is worse than none).
    """

    model_config = ConfigDict(extra="forbid")

    driver: List[str] = Field(min_length=1)
    gates: List[str] = Field(default_factory=list)
    timeout_seconds: int = Field(default=600, gt=0)
    env: dict[str, str] = Field(default_factory=dict)

    @field_validator("driver", "gates")
    @classmethod
    def _non_empty_parts(cls, value: List[str]) -> List[str]:
        """Every argv part / gate id is a non-empty string (B8 loader parity)."""
        for i, part in enumerate(value):
            if not isinstance(part, str) or not part.strip():
                raise ValueError(f"element [{i}] must be a non-empty string")
        return value

    @field_validator("timeout_seconds", mode="before")
    @classmethod
    def _int_only_timeout(cls, value: Any) -> Any:
        """Exactly an int (not bool/float/str) — B8 loader parity.

        Pydantic's lax mode would coerce "600"/600.0 where the forge loader's
        ``isinstance(..., int)`` check refuses; a canonical-green profile the
        DEPLOY stage refuses is the fatal direction of the superset invariant
        (parity-coach catch, 2026-07-16).
        """
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError("live_gate.timeout_seconds must be a positive integer")
        return value

    @field_validator("env")
    @classmethod
    def _upper_snake_names(cls, value: dict[str, str]) -> dict[str, str]:
        """Env keys are UPPER_SNAKE names; values are non-secret strings.

        Secrets stay register REFS (``secret_injection``) — never inlined here.
        """
        for name, val in value.items():
            if not isinstance(name, str) or not _LIVE_GATE_ENV_NAME_RE.match(name):
                raise ValueError(
                    f"live_gate.env key {name!r} must be UPPER_SNAKE_CASE "
                    "(a non-secret env-var NAME, e.g. API_TEST_BASE_URL)"
                )
            if not isinstance(val, str):
                raise ValueError(
                    f"live_gate.env[{name!r}] must be a string value "
                    "(non-secret, e.g. a base URL; secrets stay register REFS)"
                )
        return value


class CandidateSpec(BaseModel):
    """The candidate-then-promote overlay (S2F, execution-surface design).

    When a profile carries a ``candidate`` section, the DEPLOY stage stands the
    build up first under a SEPARATE compose project (``<live project>-cand``),
    gates it, and only re-tags-and-promotes it to the live name on a PASS — the
    live name is never touched by a candidate that fails its gate. Absent ⇒
    ``None`` ⇒ byte-identical to the direct-live flow. Refusal parity with
    ``forge.deploy.profile._parse_candidate`` (loader ``c20f28e``) is proven by
    the B8 seam test.
    """

    model_config = ConfigDict(extra="forbid")

    env: dict[str, str] = Field(default_factory=dict)
    keep: bool = False

    @field_validator("env")
    @classmethod
    def _upper_snake_names(cls, value: dict[str, str]) -> dict[str, str]:
        """Env keys are UPPER_SNAKE names; values are non-secret strings.

        The candidate-leg NON-SECRET overlay (e.g. ``CANDIDATE_PORT=8902``);
        secrets stay register REFS (``secret_injection``), never inlined here.
        Same validation idiom as :class:`LiveGateSpec.env` (forge ``_ENV_NAME_RE``).
        """
        for name, val in value.items():
            if not isinstance(name, str) or not _LIVE_GATE_ENV_NAME_RE.match(name):
                raise ValueError(
                    f"candidate.env key {name!r} must be UPPER_SNAKE_CASE "
                    "(a non-secret env-var NAME, e.g. CANDIDATE_PORT)"
                )
            if not isinstance(val, str):
                raise ValueError(
                    f"candidate.env[{name!r}] must be a string value "
                    "(non-secret, e.g. a port/base URL; secrets stay register REFS)"
                )
        return value

    @field_validator("keep", mode="before")
    @classmethod
    def _bool_only_keep(cls, value: Any) -> Any:
        """Exactly a bool (not int/float/str) — B8 loader parity.

        Pydantic's lax mode would coerce 1 / "true" / 1.0 where the forge
        loader's ``isinstance(keep, bool)`` check refuses; a canonical-green
        profile the DEPLOY stage refuses is the fatal direction of the superset
        invariant (the timeout_seconds lesson, applied to keep).
        """
        if not isinstance(value, bool):
            raise ValueError(
                "candidate.keep must be a boolean when present "
                "(True keeps the candidate project up after promote; default False)"
            )
        return value


class DeployProfile(QAFormatModel):
    """Canonical deploy-profile schema (B10). Faithful superset of the B8 loader."""

    FORMAT_KIND: ClassVar[str] = "deploy-profile"
    CURRENT_FORMAT_VERSION: ClassVar[str] = "1.0"

    env_id: str = Field(min_length=1)
    compose: ComposeSpec
    hosts: List[DeployHost] = Field(default_factory=list)
    secret_injection: List[str] = Field(default_factory=list)
    seed_fixture_contract: List[SeedFixture] = Field(default_factory=list)
    realm_import: Optional[str] = None
    models_required: List[ModelRequirement] = Field(default_factory=list)
    health_checks: List[HealthCheck] = Field(default_factory=list)
    broker_contract_ref: Optional[str] = None
    reservation: Optional[Reservation] = None
    # The kept :rollback-* image tag the O-32 revert re-deploys on a failing
    # live gate (dated addition 2026-07-16; B8 loader parity since WS2-C1).
    rollback_image_ref: Optional[str] = Field(default=None, min_length=1)
    cwd: Optional[str] = None

    @field_validator("rollback_image_ref")
    @classmethod
    def _rollback_ref_non_blank(cls, value: Optional[str]) -> Optional[str]:
        """Strip + refuse blank — B8 loader parity (forge strips and refuses
        whitespace-only). A blank ref validating green would feed the O-32
        revert garbage (parity-coach catch, 2026-07-16)."""
        if value is None:
            return value
        stripped = value.strip()
        if not stripped:
            raise ValueError(
                "rollback_image_ref must be a non-empty string when present"
            )
        return stripped
    # The per-target F16 live-gate driver (dated addition 2026-07-16; forge
    # loader b101933). Absent ⇒ the live-gate seam stays Unconfigured (loud).
    live_gate: Optional[LiveGateSpec] = None
    # The candidate-then-promote overlay (dated addition 2026-07-16; forge
    # loader c20f28e). Absent ⇒ byte-identical to the direct-live flow.
    candidate: Optional[CandidateSpec] = None

    @field_validator("models_required", mode="before")
    @classmethod
    def _coerce_bare_model_strings(cls, value: Any) -> Any:
        """Accept a bare model-name string as ``{model: <name>}`` (B8 convenience)."""
        if isinstance(value, list):
            return [
                {"model": item} if isinstance(item, str) else item for item in value
            ]
        return value

    @field_validator("secret_injection")
    @classmethod
    def _refs_only(cls, value: List[str]) -> List[str]:
        """Refuse any secret entry that looks like it carries a VALUE (refs only)."""
        for i, entry in enumerate(value):
            if not isinstance(entry, str) or not entry.strip():
                raise ValueError(
                    f"secret_injection[{i}] must be a non-empty register-key name"
                )
            if not _REF_NAME_RE.match(entry.strip()):
                raise ValueError(
                    f"secret_injection[{i}]={entry!r} is not a bare register-key "
                    f"name (it looks like a value — contains an assignment, URL, "
                    f"or whitespace). Secrets are register REFS ONLY: put the KEY "
                    f"NAME here; WS5 resolves the value at run time."
                )
        return value
