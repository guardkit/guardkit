"""Live-gate runner (WS2 session B3, 2026-07-08).

A DETERMINISTIC guardkit orchestrator component (DF-015 clause 1 — no model
calls on the execution path) that runs a repo's registered F4 gate scripts
against a deployed instance and emits the scope-design §3 results envelope.

Design source: ai-transition/docs/ws2-qa-verifier-and-last-mile-
{scope-design,build-plan}-2026-07-07.md §3 / §B3. Verdict enum: DECISION-DF-017.

Module map:

    preflight.py  reachability of each gate's address
    registry.py   F4 load + gate selection (risk order)
    executor.py   F4 gate-script execution (exit code + JSON assertions)
    evidence.py   F5 evidence index
    runner.py     orchestration + results-envelope emission + verdict

The leak sweep, the async-poller classifier and the disposition, verdict and
campaign layers were removed in the cull of 27 October 2026.
"""

from __future__ import annotations

from guardkit.orchestrator.live_gate.errors import LiveGateError
from guardkit.orchestrator.live_gate.preflight import DefaultF16ChecklistProvider
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
    "LiveGateRunner",
    "DefaultF16ChecklistProvider",
    "derive_verdict",
    "load_registry",
    "registry_path_for",
    "select_gates",
]
