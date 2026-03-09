"""
MaxParallel strategy resolution for wave execution (TASK-VRF-006).

Supports three modes:
- STATIC: Fixed max_parallel value (current behaviour)
- DYNAMIC: Adjust based on GPU memory before each wave
- PER_WAVE: Allow per-wave override from feature configuration
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

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
    """
    if config.mode == MaxParallelMode.PER_WAVE and wave_override is not None:
        resolved = max(1, wave_override)
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
            logger.info(
                "Wave %d: GPU pressure unknown, falling back to static_value=%s",
                wave_number,
                resolved,
            )
            return resolved

        logger.info(
            "Wave %d: max_parallel=%s (dynamic, pressure=%s, util=%s)",
            wave_number,
            resolved,
            snap.pressure.value,
            f"{snap.utilization_pct:.1f}%" if snap.utilization_pct is not None else "N/A",
        )
        return resolved

    # STATIC mode (or fallback)
    if config.static_value is not None:
        logger.info(
            "Wave %d: max_parallel=%d (static)", wave_number, config.static_value
        )
    return config.static_value
