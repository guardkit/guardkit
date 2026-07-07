"""F4 · gate-script contract + registry, with the results envelope (LPA-01, LPA-10, ST-11).

Two models:

- ``GateRegistry`` — instance ``qa/gates/registry.yaml``: the durable, named
  gate scripts a repo carries (scripts are products, never scratch files).
  Writers: Player/feature-build authors gate scripts; the registry is curated
  at merge review. Readers: the live-gate runner (executes only registered
  gates), the deploy stage (re-runs the accumulated pack as the live
  regression suite), Coach lint (LPA-02 self-calibrating assertions).

- ``ResultsEnvelope`` — the JSON envelope every ``guardkit qa`` runner
  invocation emits (scope-design §3), written under ``qa/gates/history/`` and
  returned on stdout for the forge adapter. The gate-script CONTRACT: exit 0 =
  pass; non-zero MUST enumerate failures as assertion results (assertion id,
  observed/expected, evidence ref) in this envelope's per-gate shape.

Enforcement (a feature whose pass bar declares a runtime surface cannot reach
feature-complete without at least one registered, green gate script) is B2's
deliverable — this module is schema only. The runner that emits envelopes is
B3's (``guardkit/orchestrator/live_gate/``).

``instrument_fail`` and ``environment_fail`` are first-class verdicts (ST-11
attribution discipline): they never indict the system under test and never
count as feature failures.

Stack-blind by design. Field lists pinned by scope-design §2 + §3
(2026-07-07). Additions require a dated note in that doc.
"""

from __future__ import annotations

from typing import Any, ClassVar, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from guardkit.qa.formats.base import QAFormatModel


# ---------------------------------------------------------------------------
# Registry side
# ---------------------------------------------------------------------------


class GateTarget(BaseModel):
    """Where the gate points. base_url_env is an ENV VAR NAME, never a URL —
    LPA-02: hard-coded targets in scripts are the anti-pattern the registry
    exists to retire."""

    model_config = ConfigDict(extra="forbid")

    base_url_env: str = Field(min_length=1)
    environment_id: str = Field(min_length=1)


class LastGreen(BaseModel):
    """The last time this gate passed, pinned to a sha."""

    model_config = ConfigDict(extra="forbid")

    date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    sha: str = Field(min_length=4)


class GateEntry(BaseModel):
    """One registered, durable gate script."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    # Repo-relative path to the script (or suite dir) honouring the exit-code
    # + JSON-envelope contract.
    path: str = Field(min_length=1)
    target: GateTarget
    # Named preconditions checked before the gate runs (e.g. suite_vs_ledger).
    # Open vocabulary — scope-design §2 lists suite_vs_ledger as the exemplar.
    preconditions: List[str] = Field(default_factory=list)
    # ST-11 instrument self-checks: does the tool load, does the login helper
    # work — a FAIL without a green preflight is instrument-attributable.
    preflight: List[str] = Field(default_factory=list)
    # Optional: not every gate sweeps (only surface-bearing web gates do).
    leak_sweep_manifest_ref: Optional[str] = None
    pass_bar_ref: str = Field(min_length=1)
    evidence_dir_pattern: str = Field(min_length=1)
    # Absent for a gate that has never gone green.
    last_green: Optional[LastGreen] = None


class GateRegistry(QAFormatModel):
    """F4 registry root model."""

    FORMAT_KIND: ClassVar[str] = "gate-registry"
    CURRENT_FORMAT_VERSION: ClassVar[str] = "1.0"

    gates: List[GateEntry] = Field(min_length=1)


# ---------------------------------------------------------------------------
# Results-envelope side (scope-design §3)
# ---------------------------------------------------------------------------


class AssertionResult(BaseModel):
    """One assertion outcome inside a gate run."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    status: Literal["pass", "fail"]
    observed: Optional[str] = None
    expected: Optional[str] = None
    evidence_ref: Optional[str] = None


class GateResult(BaseModel):
    """One gate's outcome. The script contract: exit 0 = pass; non-zero MUST
    enumerate its failures in ``assertions``."""

    model_config = ConfigDict(extra="forbid")

    gate_id: str = Field(min_length=1)
    exit_code: int
    assertions: List[AssertionResult] = Field(default_factory=list)


class PreflightResult(BaseModel):
    """Pre-flight outcome. Check-entry shape is pinned by F16 (the WS5-owned
    secrets-register / perishable-prereq checklist — WS2 defines only the
    consumer interface), so entries stay open mappings until B3 hardens the
    consumer against the WS5 schema."""

    model_config = ConfigDict(extra="forbid")

    checks: List[Dict[str, Any]] = Field(default_factory=list)
    instrument_ok: bool


class SweepResult(BaseModel):
    """F3 leak-sweep outcome inside a run."""

    model_config = ConfigDict(extra="forbid")

    surfaces_checked: int = Field(ge=0)
    leaks: List[str] = Field(default_factory=list)


class PollerOutcome(BaseModel):
    """LPA-06 async-poller classification for one watched operation."""

    model_config = ConfigDict(extra="forbid")

    op_id: str = Field(min_length=1)
    classification: Literal["progressing", "stuck", "failed"]


class ResultsEnvelope(QAFormatModel):
    """The per-invocation results envelope (scope-design §3)."""

    FORMAT_KIND: ClassVar[str] = "results-envelope"
    CURRENT_FORMAT_VERSION: ClassVar[str] = "1.0"

    run_id: str = Field(min_length=1)
    feature_id: str = Field(min_length=1)
    target_env: str = Field(min_length=1)
    started: str = Field(min_length=1)
    finished: str = Field(min_length=1)
    preflight: PreflightResult
    gates: List[GateResult] = Field(default_factory=list)
    sweep: Optional[SweepResult] = None
    poller_outcomes: List[PollerOutcome] = Field(default_factory=list)
    evidence_index_ref: Optional[str] = None
    dispositions_ref: Optional[str] = None
    attempts_ledger_ref: Optional[str] = None
    verdict: Literal["pass", "fail", "instrument_fail", "environment_fail"]
