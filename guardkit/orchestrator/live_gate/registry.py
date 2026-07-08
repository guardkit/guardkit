"""F4 · gate registry load + selection (WS2 session B3).

Reads ``qa/gates/registry.yaml`` (the F4 ``GateRegistry``) and selects which
registered gates a run executes, in risk order.

Selection honours ``--gates g1,g2`` (an explicit subset) and refuses an unknown
gate id loudly — a typo'd gate id must not silently select nothing (which would
pass vacuously).

Risk ordering (scope-design §3 step 2: "riskiest / never-exercised hop first").
The full hop-risk matrix is F10 (tier-2/3, not yet built). Until F10 lands, the
deterministic proxy is: **never-exercised gates first** (a gate with no
``last_green`` has never been proven and is the riskiest to leave for last),
then registry order preserved (a stable sort). When F10 lands, this ordering key
is where its risk score plugs in — documented so the seam is visible.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Sequence

from guardkit.qa.formats import GateRegistry, QAFormatError, validate_instance
from guardkit.qa.formats.gate_registry import GateEntry

from guardkit.orchestrator.live_gate.errors import LiveGateError


def registry_path_for(repo_root: Path) -> Path:
    """Canonical F4 registry path for a repo (``qa/gates/registry.yaml``)."""
    return repo_root / "qa" / "gates" / "registry.yaml"


def load_registry(path: Path) -> GateRegistry:
    """Load + validate the F4 gate registry at ``path``.

    Raises:
        QAFormatError: the registry is missing or malformed (loud config error).
    """
    return validate_instance("gate-registry", path)  # type: ignore[return-value]


def select_gates(
    registry: GateRegistry,
    requested_ids: Optional[Sequence[str]] = None,
) -> List[GateEntry]:
    """Select gates to execute, in risk order (never-exercised first).

    Args:
        registry: the loaded F4 registry.
        requested_ids: if given, only these gate ids run (a ``--gates`` subset).
            An id not in the registry raises :class:`LiveGateError` — a typo
            must not silently select nothing.

    Returns:
        The selected gates, never-exercised (no ``last_green``) first, then
        registry order preserved.
    """
    by_id = {g.id: g for g in registry.gates}

    if requested_ids is not None:
        unknown = [gid for gid in requested_ids if gid not in by_id]
        if unknown:
            raise LiveGateError(
                f"unknown gate id(s) {unknown} — not in the registry. "
                f"Registered gates: {sorted(by_id)}"
            )
        # Preserve the caller's order within the requested subset before the
        # risk sort so an explicit selection is honoured deterministically.
        selected = [by_id[gid] for gid in requested_ids]
    else:
        selected = list(registry.gates)

    # Stable sort: never-exercised (no last_green) first. `sorted` is stable, so
    # ties keep their prior order (caller order / registry order).
    return sorted(selected, key=lambda g: g.last_green is not None)


__all__ = [
    "registry_path_for",
    "load_registry",
    "select_gates",
    "GateRegistry",
    "GateEntry",
    "QAFormatError",
    "LiveGateError",
]
