"""
MaxParallel strategy resolution for wave execution (TASK-VRF-006).

Supports three modes:
- STATIC: Fixed max_parallel value (current behaviour)
- DYNAMIC: Adjust based on GPU memory before each wave
- PER_WAVE: Allow per-wave override from feature configuration
"""

import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Awaitable, List, Optional, Sequence

from guardkit.orchestrator.gpu_monitor import (
    GpuMemoryPressure,
    GpuMonitor,
    NullGpuMonitor,
)

logger = logging.getLogger(__name__)


class MaxParallelMode(Enum):
    """Strategy for determining max_parallel per wave."""

    STATIC = "static"  # Use fixed value (current behaviour)
    DYNAMIC = "dynamic"  # Adjust based on GPU memory before each wave
    PER_WAVE = "per-wave"  # Allow per-wave override from feature config


@dataclass
class ParallelConfig:
    """Resolved parallel execution configuration."""

    mode: MaxParallelMode = MaxParallelMode.STATIC
    static_value: Optional[int] = None  # None = unlimited
    gpu_monitor: GpuMonitor = field(default_factory=NullGpuMonitor)

    @classmethod
    def from_legacy(cls, max_parallel: Optional[int]) -> "ParallelConfig":
        """Create a ParallelConfig from the legacy max_parallel int.

        Provides backward compatibility with existing callers.
        """
        return cls(mode=MaxParallelMode.STATIC, static_value=max_parallel)


def resolve_max_parallel(
    config: ParallelConfig,
    wave_number: int = 1,
    wave_size: int = 1,
    wave_override: Optional[int] = None,
    log: bool = True,
) -> Optional[int]:
    """Resolve effective max_parallel for a specific wave.

    Returns None for unlimited, or a positive int for the limit.

    Parameters
    ----------
    config : ParallelConfig
        Parallel execution configuration.
    wave_number : int
        Current wave number (1-indexed).
    wave_size : int
        Number of tasks in this wave.
    wave_override : Optional[int]
        Per-wave override value (only used in PER_WAVE mode).
    log : bool
        When True (default) the resolved decision is logged at INFO. The
        wave dispatcher logs the *authoritative* decision; pass ``log=False``
        for read-only resolutions (e.g. the progress-display banner in
        ``WaveProgressDisplay.start_wave``) so the strategy decision is not
        logged twice per wave (TASK-FIX-MAXPARALLEL01).
    """
    if config.mode == MaxParallelMode.PER_WAVE and wave_override is not None:
        resolved = max(1, wave_override)
        if log:
            logger.info(
                "Wave %d: max_parallel=%d (per-wave override)", wave_number, resolved
            )
        return resolved

    if config.mode == MaxParallelMode.DYNAMIC:
        snap = config.gpu_monitor.snapshot()
        if snap.pressure == GpuMemoryPressure.LOW:
            resolved = 2
        elif snap.pressure in (GpuMemoryPressure.MEDIUM, GpuMemoryPressure.HIGH):
            resolved = 1
        else:
            # UNKNOWN: fall back to static_value
            resolved = config.static_value
            if log:
                logger.info(
                    "Wave %d: GPU pressure unknown, falling back to static_value=%s",
                    wave_number,
                    resolved,
                )
            return resolved

        if log:
            logger.info(
                "Wave %d: max_parallel=%s (dynamic, pressure=%s, util=%s)",
                wave_number,
                resolved,
                snap.pressure.value,
                f"{snap.utilization_pct:.1f}%" if snap.utilization_pct is not None else "N/A",
            )
        return resolved

    # STATIC mode (or fallback)
    if config.static_value is not None and log:
        logger.info(
            "Wave %d: max_parallel=%d (static)", wave_number, config.static_value
        )
    return config.static_value


def bound_concurrency(
    coros: Sequence[Awaitable],
    max_parallel: Optional[int],
) -> List[Awaitable]:
    """Wrap awaitables so at most ``max_parallel`` run concurrently.

    TASK-FIX-MAXPARALLEL01: extracted verbatim from the inline loop in
    ``FeatureOrchestrator._execute_wave_parallel`` so the wave dispatcher's
    concurrency-bounding logic is unit-testable in isolation (AC-4) rather
    than only being exercised by full end-to-end autobuild runs.

    The contract is unchanged from the original inline loop: when
    ``max_parallel`` is a positive int, every wrapped awaitable acquires a
    single shared ``asyncio.Semaphore(max_parallel)`` before awaiting its
    inner awaitable, so ``asyncio.gather`` runs at most ``max_parallel`` of
    them at a time. When ``max_parallel`` is ``None`` or ``<= 0`` the
    awaitables are returned unchanged (unlimited concurrency — the default
    behaviour for runs that do not set ``--max-parallel``).

    Parameters
    ----------
    coros : Sequence[Awaitable]
        The per-task awaitables to schedule.
    max_parallel : Optional[int]
        Maximum number to run at once. ``None`` or ``<= 0`` means unlimited.

    Returns
    -------
    List[Awaitable]
        Either the original awaitables (unlimited) or semaphore-bounded
        wrappers.
    """
    if max_parallel is None or max_parallel <= 0:
        return list(coros)

    semaphore = asyncio.Semaphore(max_parallel)

    async def _bounded(inner: Awaitable):
        async with semaphore:
            return await inner

    return [_bounded(c) for c in coros]
