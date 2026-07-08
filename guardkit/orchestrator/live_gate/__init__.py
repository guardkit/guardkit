"""Live-gate runner (WS2 session B3, 2026-07-08).

A DETERMINISTIC guardkit orchestrator component (DF-015 clause 1 — no model
calls on the execution path; the read-the-image hook is an interface only in
v1) that runs a repo's registered F4 gate scripts against a deployed instance
and emits the scope-design §3 results envelope. The v2 agentic verifier is a
different, later seat (scope §6).

Design source (binding): ai-transition/docs/ws2-qa-verifier-and-last-mile-
{scope-design,build-plan}-2026-07-07.md §3 / §B3. Verdict enum + attribution
discipline: DECISION-DF-017.

Module map (one per format-consumer, scope-design §3):

    preflight.py  F16 checklist + ST-11 instrument self-check + reservation +
                  F6 broker diff (seams; loud Unconfigured* stubs)
    registry.py   F4 load/validate + gate selection (risk order)
    executor.py   F4 gate-script contract execution (exit-code + JSON envelope)
    sweep.py      F3 leak sweep (generalizes gate_phase6_sweep.py)
    poller.py     LPA-06 progressing/stuck/failed classifier
    evidence.py   F5 emitter + index + read-the-image hook (interface only, v1)
    runner.py     orchestration + results-envelope emission + v1 verdict

    disposition.py / verdict.py / walk_driver.py are sessions B4 / B5 — they
    snap onto the envelope this runner emits.
"""

from __future__ import annotations

from guardkit.orchestrator.live_gate.errors import LiveGateError, LiveGateStubError
from guardkit.orchestrator.live_gate.poller import (
    Classification,
    PollSample,
    classify_operation,
)
from guardkit.orchestrator.live_gate.registry import (
    load_registry,
    registry_path_for,
    select_gates,
)
from guardkit.orchestrator.live_gate.runner import (
    LiveGateRunner,
    derive_verdict,
)

__all__ = [
    "LiveGateError",
    "LiveGateStubError",
    "LiveGateRunner",
    "derive_verdict",
    "classify_operation",
    "PollSample",
    "Classification",
    "load_registry",
    "registry_path_for",
    "select_gates",
]
