"""
MaxParallel strategy resolution for wave execution (TASK-VRF-006).

Supports three modes:
- STATIC: Fixed max_parallel value (current behaviour)
- DYNAMIC: Adjust based on GPU memory before each wave
- PER_WAVE: Allow per-wave override from feature configuration
"""

import asyncio
import logging
from dataclasses import dataclass, field, replace
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


# TASK-AB-WAVECTL01: provenance of ParallelConfig.static_value. Drives the
# feature-YAML tier of the max-parallel precedence chain
# (env > CLI flag > feature-YAML recommended_parallel > auto-detect):
# only a value that was NOT operator-set (source == auto-detect) may be
# BOUNDED (lowered, never raised) by the loaded feature's
# ``recommended_parallel``.
PARALLEL_SOURCE_ENV = "env"
PARALLEL_SOURCE_FLAG = "flag"
PARALLEL_SOURCE_FEATURE_YAML = "feature-yaml"
PARALLEL_SOURCE_AUTO_DETECT = "auto-detect"


@dataclass
class ParallelConfig:
    """Resolved parallel execution configuration."""

    mode: MaxParallelMode = MaxParallelMode.STATIC
    static_value: Optional[int] = None  # None = unlimited
    gpu_monitor: GpuMonitor = field(default_factory=NullGpuMonitor)
    # TASK-AB-WAVECTL01: where static_value came from (one of the
    # PARALLEL_SOURCE_* constants). Operator-set sources (env/flag) always
    # win over the feature YAML; auto-detect is the only tier the YAML's
    # ``recommended_parallel`` may bound (lower, never raise).
    source: str = PARALLEL_SOURCE_AUTO_DETECT

    @classmethod
    def from_legacy(cls, max_parallel: Optional[int]) -> "ParallelConfig":
        """Create a ParallelConfig from the legacy max_parallel int.

        Provides backward compatibility with existing callers. An explicit
        int is treated as operator-set (``flag``) so the feature-YAML tier
        cannot override it; ``None`` means "nothing set" (``auto-detect``),
        the only tier ``apply_feature_recommended_parallel`` may bound
        (lower, never raise; TASK-AB-WAVECTL01).
        """
        source = (
            PARALLEL_SOURCE_FLAG
            if max_parallel is not None
            else PARALLEL_SOURCE_AUTO_DETECT
        )
        return cls(
            mode=MaxParallelMode.STATIC, static_value=max_parallel, source=source
        )


def apply_feature_recommended_parallel(
    config: ParallelConfig,
    recommended_parallel: Optional[int],
) -> ParallelConfig:
    """Apply the feature-YAML tier of the max-parallel precedence chain.

    TASK-AB-WAVECTL01. Precedence: env > CLI flag > feature-YAML
    ``recommended_parallel`` > auto-detect. This helper implements ONLY the
    feature-YAML tier, and the YAML may only LOWER concurrency, never raise
    it: an operator-set config (source env/flag) is returned unchanged; an
    auto-detected value is BOUNDED by a valid ``recommended_parallel`` (an
    explicit int >= 1) — ``new_value = min(yaml_value, auto_detect_value)``,
    where an auto-detect value of ``None`` (unlimited) means the YAML
    applies as-is.

    The lowering-only contract exists because ``generate_feature_yaml`` has
    always emitted ``recommended_parallel`` as a machine default
    (min(max wave size, 4)), so existing feature YAMLs carry 2-5 as
    previously-inert metadata — while on local backends the auto-detect
    result of 1 is the TASK-VPT-001 KV-cache safety cap. A machine-emitted
    YAML default must never raise that cap; bounding the UNLIMITED cloud
    default (the retro-motivating use) still works because a ``None``
    auto-detect takes the YAML value as-is.

    The caller MUST apply this ONCE to the shared config, before BOTH
    ``resolve_max_parallel`` call sites (the read-only ``log=False`` display
    resolution and the authoritative executor resolution), so the wave
    banner and the executor consume the identical decision — see
    ``.claude/rules/display-must-derive-from-enforcement-source-not-proxy.md``.

    Parameters
    ----------
    config : ParallelConfig
        Config resolved from env / CLI flag / auto-detect.
    recommended_parallel : Optional[int]
        ``orchestration.recommended_parallel`` from the loaded feature YAML.
        ``None`` (absent), bools, non-ints, and values < 1 are ignored —
        an absent/invalid YAML tier falls through to the auto-detect result
        unchanged. A value >= the finite auto-detect result is also ignored
        (it cannot lower anything).

    Returns
    -------
    ParallelConfig
        Either ``config`` unchanged (with its auto-detect source intact), or
        a copy with ``static_value`` lowered to the YAML value and ``source``
        set to ``PARALLEL_SOURCE_FEATURE_YAML``. The feature-YAML source is
        stamped ONLY when the YAML actually changed the value.
    """
    if config.source != PARALLEL_SOURCE_AUTO_DETECT:
        return config
    # bool is an int subclass; a YAML `recommended_parallel: true` must not
    # be honoured as 1.
    if isinstance(recommended_parallel, bool):
        return config
    if not isinstance(recommended_parallel, int) or recommended_parallel < 1:
        return config
    # Lowering-only: the YAML may bound an unlimited (None) auto-detect
    # result, but may never raise a finite one (e.g. the local-backend
    # TASK-VPT-001 KV-cache cap of 1). An equal-or-higher YAML value changes
    # nothing, so the auto-detect value AND source stand.
    if (
        config.static_value is not None
        and recommended_parallel >= config.static_value
    ):
        return config
    return replace(
        config,
        static_value=recommended_parallel,
        source=PARALLEL_SOURCE_FEATURE_YAML,
    )


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
        # TASK-AB-WAVECTL01: the authoritative (executor-side) resolution logs
        # the precedence-chain source once; the display resolution passes
        # log=False, so the source is never double-logged per wave.
        logger.info(
            "Wave %d: max_parallel=%d (static) [source: %s]",
            wave_number,
            config.static_value,
            config.source,
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
