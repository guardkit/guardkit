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
    cwd: Optional[str] = None

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
