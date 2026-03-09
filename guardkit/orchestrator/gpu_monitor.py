"""
GPU memory monitoring for dynamic max_parallel scaling (TASK-VRF-006).

Provides a protocol for GPU memory monitoring and a NullGpuMonitor
fallback for environments without pynvml.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Protocol, runtime_checkable


class GpuMemoryPressure(Enum):
    """GPU memory pressure level."""

    LOW = "low"  # <60% VRAM used -- safe for max_parallel=2
    MEDIUM = "medium"  # 60-80% -- marginal, prefer max_parallel=1
    HIGH = "high"  # >80% -- definitely max_parallel=1
    UNKNOWN = "unknown"  # Cannot determine (no GPU, no pynvml)


@dataclass
class GpuMemorySnapshot:
    """Point-in-time GPU memory reading."""

    total_mib: Optional[int] = None
    used_mib: Optional[int] = None
    free_mib: Optional[int] = None
    pressure: GpuMemoryPressure = GpuMemoryPressure.UNKNOWN

    @property
    def utilization_pct(self) -> Optional[float]:
        """Return GPU memory utilization as a percentage, or None if unknown."""
        if self.total_mib is not None and self.used_mib is not None and self.total_mib > 0:
            return (self.used_mib / self.total_mib) * 100.0
        return None


@runtime_checkable
class GpuMonitor(Protocol):
    """Protocol for GPU memory monitoring."""

    def snapshot(self, device_index: int = 0) -> GpuMemorySnapshot:
        """Take a point-in-time GPU memory reading."""
        ...


class NullGpuMonitor:
    """No-op monitor when GPU monitoring is unavailable.

    Always returns UNKNOWN pressure. This is a legitimate thin wrapper,
    not a stub -- it provides defined fallback behaviour when pynvml
    is not installed.
    """

    def snapshot(self, device_index: int = 0) -> GpuMemorySnapshot:
        return GpuMemorySnapshot(pressure=GpuMemoryPressure.UNKNOWN)


def classify_pressure(utilization_pct: float) -> GpuMemoryPressure:
    """Classify GPU memory pressure from utilization percentage.

    Thresholds:
        <60% → LOW (safe for max_parallel=2)
        60-80% → MEDIUM (prefer max_parallel=1)
        >80% → HIGH (definitely max_parallel=1)
    """
    if utilization_pct < 60.0:
        return GpuMemoryPressure.LOW
    elif utilization_pct <= 80.0:
        return GpuMemoryPressure.MEDIUM
    else:
        return GpuMemoryPressure.HIGH
