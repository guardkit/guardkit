"""
Unit tests for parallel strategy resolution (TASK-VRF-006).

Tests:
- GpuMemorySnapshot dataclass and utilization calculation
- NullGpuMonitor fallback behaviour
- classify_pressure threshold mapping
- MaxParallelMode enum values
- ParallelConfig creation (direct and from_legacy)
- resolve_max_parallel for all modes and pressure levels

Coverage Target: >=85%
"""

import pytest

from guardkit.orchestrator.gpu_monitor import (
    GpuMemoryPressure,
    GpuMemorySnapshot,
    GpuMonitor,
    NullGpuMonitor,
    classify_pressure,
)
from guardkit.orchestrator.parallel_strategy import (
    MaxParallelMode,
    ParallelConfig,
    resolve_max_parallel,
)


# ============================================================================
# GpuMemorySnapshot Tests
# ============================================================================


class TestGpuMemorySnapshot:
    """Test GpuMemorySnapshot dataclass."""

    def test_default_values(self):
        snap = GpuMemorySnapshot()
        assert snap.total_mib is None
        assert snap.used_mib is None
        assert snap.free_mib is None
        assert snap.pressure == GpuMemoryPressure.UNKNOWN

    def test_utilization_pct_with_values(self):
        snap = GpuMemorySnapshot(total_mib=24000, used_mib=12000)
        assert snap.utilization_pct == pytest.approx(50.0)

    def test_utilization_pct_none_when_missing(self):
        snap = GpuMemorySnapshot()
        assert snap.utilization_pct is None

    def test_utilization_pct_none_when_total_zero(self):
        snap = GpuMemorySnapshot(total_mib=0, used_mib=0)
        assert snap.utilization_pct is None

    def test_full_utilization(self):
        snap = GpuMemorySnapshot(total_mib=24000, used_mib=24000)
        assert snap.utilization_pct == pytest.approx(100.0)


# ============================================================================
# NullGpuMonitor Tests
# ============================================================================


class TestNullGpuMonitor:
    """Test NullGpuMonitor fallback."""

    def test_returns_unknown_pressure(self):
        monitor = NullGpuMonitor()
        snap = monitor.snapshot()
        assert snap.pressure == GpuMemoryPressure.UNKNOWN
        assert snap.total_mib is None
        assert snap.used_mib is None

    def test_accepts_device_index(self):
        monitor = NullGpuMonitor()
        snap = monitor.snapshot(device_index=1)
        assert snap.pressure == GpuMemoryPressure.UNKNOWN

    def test_satisfies_protocol(self):
        monitor = NullGpuMonitor()
        assert isinstance(monitor, GpuMonitor)


# ============================================================================
# classify_pressure Tests
# ============================================================================


class TestClassifyPressure:
    """Test GPU memory pressure classification."""

    def test_low_pressure_below_60(self):
        assert classify_pressure(0.0) == GpuMemoryPressure.LOW
        assert classify_pressure(30.0) == GpuMemoryPressure.LOW
        assert classify_pressure(59.9) == GpuMemoryPressure.LOW

    def test_medium_pressure_60_to_80(self):
        assert classify_pressure(60.0) == GpuMemoryPressure.MEDIUM
        assert classify_pressure(70.0) == GpuMemoryPressure.MEDIUM
        assert classify_pressure(80.0) == GpuMemoryPressure.MEDIUM

    def test_high_pressure_above_80(self):
        assert classify_pressure(80.1) == GpuMemoryPressure.HIGH
        assert classify_pressure(95.0) == GpuMemoryPressure.HIGH
        assert classify_pressure(100.0) == GpuMemoryPressure.HIGH


# ============================================================================
# MaxParallelMode Tests
# ============================================================================


class TestMaxParallelMode:
    """Test MaxParallelMode enum."""

    def test_enum_values(self):
        assert MaxParallelMode.STATIC.value == "static"
        assert MaxParallelMode.DYNAMIC.value == "dynamic"
        assert MaxParallelMode.PER_WAVE.value == "per-wave"


# ============================================================================
# ParallelConfig Tests
# ============================================================================


class TestParallelConfig:
    """Test ParallelConfig creation."""

    def test_default_values(self):
        config = ParallelConfig()
        assert config.mode == MaxParallelMode.STATIC
        assert config.static_value is None
        assert isinstance(config.gpu_monitor, NullGpuMonitor)

    def test_from_legacy_with_value(self):
        config = ParallelConfig.from_legacy(2)
        assert config.mode == MaxParallelMode.STATIC
        assert config.static_value == 2

    def test_from_legacy_none(self):
        config = ParallelConfig.from_legacy(None)
        assert config.mode == MaxParallelMode.STATIC
        assert config.static_value is None

    def test_custom_gpu_monitor(self):
        """Custom GPU monitor is accepted."""

        class FakeMonitor:
            def snapshot(self, device_index=0):
                return GpuMemorySnapshot(
                    total_mib=24000,
                    used_mib=12000,
                    pressure=GpuMemoryPressure.LOW,
                )

        config = ParallelConfig(
            mode=MaxParallelMode.DYNAMIC,
            gpu_monitor=FakeMonitor(),
        )
        assert config.mode == MaxParallelMode.DYNAMIC


# ============================================================================
# resolve_max_parallel Tests
# ============================================================================


class _FakeGpuMonitor:
    """Test helper that returns configurable pressure."""

    def __init__(self, pressure: GpuMemoryPressure):
        self._pressure = pressure

    def snapshot(self, device_index: int = 0) -> GpuMemorySnapshot:
        return GpuMemorySnapshot(pressure=self._pressure)


class TestResolveMaxParallel:
    """Test resolve_max_parallel for all modes."""

    # --- STATIC mode ---

    def test_static_returns_value(self):
        config = ParallelConfig(mode=MaxParallelMode.STATIC, static_value=3)
        assert resolve_max_parallel(config) == 3

    def test_static_returns_none_for_unlimited(self):
        config = ParallelConfig(mode=MaxParallelMode.STATIC, static_value=None)
        assert resolve_max_parallel(config) is None

    # --- DYNAMIC mode ---

    def test_dynamic_low_pressure_returns_2(self):
        config = ParallelConfig(
            mode=MaxParallelMode.DYNAMIC,
            gpu_monitor=_FakeGpuMonitor(GpuMemoryPressure.LOW),
        )
        assert resolve_max_parallel(config) == 2

    def test_dynamic_medium_pressure_returns_1(self):
        config = ParallelConfig(
            mode=MaxParallelMode.DYNAMIC,
            gpu_monitor=_FakeGpuMonitor(GpuMemoryPressure.MEDIUM),
        )
        assert resolve_max_parallel(config) == 1

    def test_dynamic_high_pressure_returns_1(self):
        config = ParallelConfig(
            mode=MaxParallelMode.DYNAMIC,
            gpu_monitor=_FakeGpuMonitor(GpuMemoryPressure.HIGH),
        )
        assert resolve_max_parallel(config) == 1

    def test_dynamic_unknown_falls_back_to_static(self):
        config = ParallelConfig(
            mode=MaxParallelMode.DYNAMIC,
            static_value=1,
            gpu_monitor=_FakeGpuMonitor(GpuMemoryPressure.UNKNOWN),
        )
        assert resolve_max_parallel(config) == 1

    def test_dynamic_unknown_falls_back_to_none(self):
        config = ParallelConfig(
            mode=MaxParallelMode.DYNAMIC,
            static_value=None,
            gpu_monitor=_FakeGpuMonitor(GpuMemoryPressure.UNKNOWN),
        )
        assert resolve_max_parallel(config) is None

    # --- PER_WAVE mode ---

    def test_per_wave_with_override(self):
        config = ParallelConfig(mode=MaxParallelMode.PER_WAVE, static_value=1)
        assert resolve_max_parallel(config, wave_override=3) == 3

    def test_per_wave_override_clamped_to_1(self):
        config = ParallelConfig(mode=MaxParallelMode.PER_WAVE, static_value=1)
        assert resolve_max_parallel(config, wave_override=0) == 1
        assert resolve_max_parallel(config, wave_override=-5) == 1

    def test_per_wave_without_override_falls_back(self):
        config = ParallelConfig(mode=MaxParallelMode.PER_WAVE, static_value=2)
        assert resolve_max_parallel(config, wave_override=None) == 2

    # --- Wave metadata ---

    def test_wave_number_passed_through(self):
        """wave_number is used for logging, should not affect result."""
        config = ParallelConfig(mode=MaxParallelMode.STATIC, static_value=2)
        assert resolve_max_parallel(config, wave_number=5) == 2
