"""
MaxParallel strategy resolution for wave execution (TASK-VRF-006).

Supports three modes:
- STATIC: Fixed max_parallel value (current behaviour)
- DYNAMIC: Adjust based on GPU memory before each wave
- PER_WAVE: Allow per-wave override from feature configuration

On top of the mode, one rule can lower any wave to a single task at a time:
two tasks that would work on the same area of the repository do not run at
the same time. See the "Same-area sequencing" section below.
"""

import asyncio
import logging
import os
from dataclasses import dataclass, field, replace
from enum import Enum
from pathlib import Path
from typing import (
    Any,
    Awaitable,
    Dict,
    List,
    Mapping,
    Optional,
    Sequence,
    Set,
)

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
    # Whether a wave whose tasks would work on the same area of the
    # repository is run one task at a time. One of ``SAME_AREA_POLICIES``,
    # read from ``GUARDKIT_WAVE_SAME_AREA`` at construction the same way
    # ``static_value`` is read from ``GUARDKIT_MAX_PARALLEL_TASKS``.
    same_area: str = field(default_factory=lambda: same_area_policy_from_env())

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


# ---------------------------------------------------------------------------
# Same-area sequencing: two tasks that would work on the same part of the
# repository do not run at the same time.
# ---------------------------------------------------------------------------
#
# Why this exists (build ``build-FEAT-3EF3-20260911171802``, 2026-09-11): a
# plan put "add the statistics schema" (notes naming ``src/users/schemas.py``)
# and "implement the statistics query" (notes naming ``src/users/crud.py``)
# into ONE wave, so they ran together. Running together put the coach on its
# isolated-snapshot path, which could not start the repository's test command
# at all; the coder was then told five turns running that its tests produced
# no signal, and while chasing that it deleted two working functions from
# ``src/users/crud.py``. 79 tests of shipped behaviour went with them. The
# task that ran ALONE in its own wave was clean in one turn.
#
# The rule decides an AREA from DECLARED PATHS ONLY. No source file is parsed
# and no language is named, so it behaves identically for Python, TypeScript
# and Go. Two tasks share an area when they name the same file, or when they
# name files in the same immediate parent directory — a module is an area, not
# just a file, because two tasks editing neighbouring files in one module
# interact through it.

# The setting, in plain words rather than numbers. Read from the environment
# the same way this module's other settings are (``GUARDKIT_MAX_PARALLEL_TASKS``
# is read for ``static_value``), so an operator sets it without a code change.
SAME_AREA_SEQUENCE_WHEN_UNSURE = "sequence-when-unsure"
SAME_AREA_SEQUENCE_ON_DECLARED_OVERLAP = "sequence-on-declared-overlap"
SAME_AREA_OFF = "off"

SAME_AREA_POLICIES = (
    SAME_AREA_SEQUENCE_WHEN_UNSURE,
    SAME_AREA_SEQUENCE_ON_DECLARED_OVERLAP,
    SAME_AREA_OFF,
)

#: The safe default: a wave is run one task at a time when two of its tasks
#: name the same area, AND when any of its tasks does not say what it will
#: touch. Unknown is not "no overlap", for the same reason unknown is not a
#: pass.
SAME_AREA_DEFAULT = SAME_AREA_SEQUENCE_WHEN_UNSURE

SAME_AREA_ENV_VAR = "GUARDKIT_WAVE_SAME_AREA"

#: How the repository root is named in the sentence the resolver logs, for the
#: case where two tasks both name top-level files.
_REPOSITORY_ROOT_LABEL = "the repository root"


def same_area_policy_from_env(
    environ: Optional[Mapping[str, str]] = None,
) -> str:
    """Read the same-area setting from the environment.

    ``GUARDKIT_WAVE_SAME_AREA`` takes one of three plain words:

    ``sequence-when-unsure``
        The default. A wave runs one task at a time when two of its tasks
        name the same file or the same directory, and also when any task in
        it does not say which files it will touch.
    ``sequence-on-declared-overlap``
        Only a declared overlap sequences a wave. Tasks that declare nothing
        are left to run together, which is what happened before this rule
        existed.
    ``off``
        The rule does nothing at all.

    An unset or unrecognised value gives the safe default, and an
    unrecognised one is logged so the operator can see their setting was
    not understood.

    Whatever this is set to, an explicit per-wave override in the feature's
    own configuration still wins: ``resolve_max_parallel`` honours the
    override before it looks at this rule at all.
    """
    source = os.environ if environ is None else environ
    raw = source.get(SAME_AREA_ENV_VAR)
    if raw is None:
        return SAME_AREA_DEFAULT
    value = raw.strip().lower()
    if value in SAME_AREA_POLICIES:
        return value
    if value:
        logger.warning(
            "%s=%r is not one of %s; using %r.",
            SAME_AREA_ENV_VAR,
            raw,
            ", ".join(SAME_AREA_POLICIES),
            SAME_AREA_DEFAULT,
        )
    return SAME_AREA_DEFAULT


@dataclass(frozen=True)
class SameAreaDecision:
    """Whether a wave must run one task at a time, and the sentence why.

    ``reason`` is one plain sentence naming the tasks and the area they
    share (or the task that said nothing). It is empty when
    ``sequence`` is False.
    """

    sequence: bool
    reason: str = ""


def _normalise_declared_path(raw: Any) -> Optional[str]:
    """Turn one declared path into a comparable repository-relative path.

    Accepts the shapes task documents actually carry: a plain string, or a
    string wrapped in backticks or quotes, with either slash. Returns
    ``None`` for anything that is not a usable path.

    A trailing slash is KEPT, because it is the one unambiguous signal that
    the entry names a whole directory rather than a single file — a task
    that writes ``files_to_modify: - src/users/`` is claiming the directory.
    Dropping the slash would turn that claim into a file called
    ``src/users``, whose area would then read as ``src``, and a second task
    naming ``src/users/crud.ts`` would look like no overlap at all. Nothing
    here guesses from the end of a name: no extension is ever inspected, so
    this behaves the same whatever language the repository is written in.
    """
    if not isinstance(raw, str):
        return None
    text = raw.strip().strip("`").strip("'\"").strip()
    text = text.replace("\\", "/")
    if not text:
        return None
    names_a_directory = text.endswith("/")
    parts = [part for part in text.split("/") if part not in ("", ".")]
    if not parts or ".." in parts:
        return None
    cleaned = "/".join(parts)
    return cleaned + "/" if names_a_directory else cleaned


def _names_a_directory(entry: str) -> bool:
    """True when this declared entry is a whole directory, not one file."""
    return entry.endswith("/")


def _area_of(entry: str) -> str:
    """The area a declared entry belongs to.

    For a file, that is its immediate parent directory. For an entry that
    names a directory, the directory itself IS the area.
    """
    if _names_a_directory(entry):
        return entry[:-1]
    head, _, _tail = entry.rpartition("/")
    return head


def _files_among(entries: Sequence[str]) -> Set[str]:
    """Just the entries that name a single file."""
    return {entry for entry in entries if not _names_a_directory(entry)}


def _shared_area(
    first_paths: Sequence[str], second_paths: Sequence[str]
) -> Optional[str]:
    """The area two tasks both work in, or ``None`` if there is not one.

    Two tasks share an area when they name files in the same immediate
    parent directory, or when one of them claims a directory and the other
    names anything inside it, however deep.
    """
    both = sorted({_area_of(p) for p in first_paths} & {_area_of(p) for p in second_paths})
    if both:
        return both[0]

    for claimed, other_paths in (
        (first_paths, second_paths),
        (second_paths, first_paths),
    ):
        for entry in claimed:
            if not _names_a_directory(entry):
                continue
            area = entry[:-1]
            inside = area + "/"
            for other in other_paths:
                other_path = other[:-1] if _names_a_directory(other) else other
                if other_path.startswith(inside):
                    return area
    return None


def _format_area(area: str) -> str:
    return area if area else _REPOSITORY_ROOT_LABEL


def _declared_set(paths: Optional[Sequence[str]]) -> Optional[List[str]]:
    """Normalise one task's declared paths, or ``None`` if it declared none."""
    if paths is None:
        return None
    cleaned = []
    for raw in paths:
        normalised = _normalise_declared_path(raw)
        if normalised is not None and normalised not in cleaned:
            cleaned.append(normalised)
    return cleaned or None


def find_same_area_conflict(
    wave_task_paths: Optional[Mapping[str, Optional[Sequence[str]]]],
    policy: str = SAME_AREA_DEFAULT,
) -> SameAreaDecision:
    """Decide whether this wave's tasks would work on the same area.

    Parameters
    ----------
    wave_task_paths :
        One entry per task in the wave, in wave order: the task's id mapped
        to the repository-relative paths it says it will touch, or ``None``
        when the task says nothing. That one-entry-per-task mapping is how
        a wave is described here, and both live call sites always pass one.
        A caller who passes ``None`` for the whole mapping has described no
        tasks at all, so there is nothing to compare and the answer is "do
        not sequence" — today's behaviour, unchanged. If you are writing a
        new call site, do not pass ``None`` on a failure path expecting the
        wave to fail safe: pass one entry per task, with ``None`` against
        each task whose files you could not read.
    policy :
        One of ``SAME_AREA_POLICIES``.

    Returns
    -------
    SameAreaDecision
        ``sequence=True`` with one plain sentence when the wave must run one
        task at a time.
    """
    if policy == SAME_AREA_OFF:
        return SameAreaDecision(False)

    entries = list((wave_task_paths or {}).items())
    if len(entries) < 2:
        # One task cannot collide with anything, so the wave is untouched.
        return SameAreaDecision(False)

    declared = [(task_id, _declared_set(paths)) for task_id, paths in entries]

    if policy == SAME_AREA_SEQUENCE_WHEN_UNSURE:
        silent = [task_id for task_id, paths in declared if paths is None]
        if silent:
            if len(silent) == 1:
                who = f"{silent[0]} does not say which files it will touch"
            else:
                names = f"{', '.join(silent[:-1])} and {silent[-1]}"
                who = f"{names} do not say which files they will touch"
            return SameAreaDecision(
                True,
                f"{who}, so an overlap with the other tasks in this wave "
                f"cannot be ruled out and the wave runs one task at a time.",
            )

    known = [(task_id, paths) for task_id, paths in declared if paths]
    for index, (first_id, first_paths) in enumerate(known):
        for second_id, second_paths in known[index + 1 :]:
            shared_files = sorted(
                _files_among(first_paths) & _files_among(second_paths)
            )
            if shared_files:
                return SameAreaDecision(
                    True,
                    f"{first_id} and {second_id} both work on "
                    f"{shared_files[0]}, so this wave runs one task at a "
                    f"time.",
                )
            shared_area = _shared_area(first_paths, second_paths)
            if shared_area is not None:
                return SameAreaDecision(
                    True,
                    f"{first_id} and {second_id} both work on files in "
                    f"{_format_area(shared_area)}, so this wave runs one "
                    f"task at a time.",
                )

    return SameAreaDecision(False)


def collect_wave_task_paths(
    task_ids: Sequence[str],
    worktree_path: Path,
    task_files: Optional[Mapping[str, Path]] = None,
) -> Dict[str, Optional[List[str]]]:
    """Read the paths each task in a wave says it will touch.

    Declared paths only — nothing here opens a source file or knows what
    language the repository is written in.

    For each task, in order:

    1. the paths the task already declares, via the orchestrator's existing
       reader ``preflight_ignore_gate.load_planned_targets`` (the saved
       implementation plan if there is one, otherwise the task frontmatter's
       ``files_to_create`` / ``files_to_modify``);
    2. failing that, repository-relative paths mentioned in the task
       document's own text, via the plan-time reader
       ``wave_overlap_detector.infer_task_files``.

    A task that yields nothing from either source maps to ``None`` — "this
    task did not say", which the default setting treats as a reason to
    sequence the wave.

    This never raises: a task file that cannot be read, or a reader that
    cannot be imported, leaves that task as "did not say", which is the
    safe side.
    """
    collected: Dict[str, Optional[List[str]]] = {}
    for task_id in task_ids:
        paths = _declared_paths_for_task(
            task_id,
            worktree_path,
            (task_files or {}).get(task_id),
        )
        collected[task_id] = paths
    return collected


def _declared_paths_for_task(
    task_id: str,
    worktree_path: Path,
    task_file: Optional[Path] = None,
) -> Optional[List[str]]:
    """Declared paths for one task, or ``None`` when it declares none."""
    try:
        from guardkit.orchestrator.preflight_ignore_gate import (
            load_planned_targets,
        )
    except ImportError as exc:  # pragma: no cover - defensive
        logger.warning(
            "same-area check: the planned-target reader is unavailable (%s); "
            "treating %s as having declared nothing.",
            exc,
            task_id,
        )
        return None

    try:
        declared = load_planned_targets(task_id, worktree_path)
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning(
            "same-area check: could not read the planned targets of %s (%s); "
            "treating it as having declared nothing.",
            task_id,
            exc,
        )
        declared = None

    cleaned = _declared_set(declared)
    if cleaned:
        return cleaned

    text = _read_task_document(task_id, worktree_path, task_file)
    if not text:
        return None
    return _declared_set(_paths_mentioned_in_text(text))


def _read_task_document(
    task_id: str,
    worktree_path: Path,
    task_file: Optional[Path] = None,
) -> Optional[str]:
    """Return the text of the task's own document, or ``None``."""
    candidates: List[Path] = []
    if task_file is not None:
        candidate = Path(task_file)
        if not candidate.is_absolute():
            candidate = worktree_path / candidate
        candidates.append(candidate)

    try:
        from guardkit.orchestrator.preflight_ignore_gate import _find_task_file
    except ImportError:  # pragma: no cover - defensive
        _find_task_file = None  # type: ignore[assignment]
    if _find_task_file is not None:
        try:
            found = _find_task_file(task_id, worktree_path)
        except Exception:  # pragma: no cover - defensive
            found = None
        if found is not None:
            candidates.append(found)

    for candidate in candidates:
        try:
            if candidate.is_file():
                return candidate.read_text(encoding="utf-8")
        except OSError as exc:
            logger.warning(
                "same-area check: could not read the task document %s (%s).",
                candidate,
                exc,
            )
    return None


def _paths_mentioned_in_text(text: str) -> List[str]:
    """Repository-relative paths mentioned in a task document's own text.

    Reuses the plan-time detector's extractor so the runtime rule and the
    plan-time warning read prose the same way. If that module cannot be
    imported, the task simply counts as having declared nothing.
    """
    try:
        from installer.core.commands.lib.wave_overlap_detector import (
            infer_task_files,
        )
    except ImportError as exc:  # pragma: no cover - defensive
        logger.warning(
            "same-area check: the task-text path reader is unavailable (%s).",
            exc,
        )
        return []
    try:
        return sorted(infer_task_files({"description": text}))
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning(
            "same-area check: could not read paths out of a task document (%s).",
            exc,
        )
        return []


def resolve_max_parallel(
    config: ParallelConfig,
    wave_number: int = 1,
    wave_size: int = 1,
    wave_override: Optional[int] = None,
    log: bool = True,
    wave_task_paths: Optional[Mapping[str, Optional[Sequence[str]]]] = None,
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
        Per-wave override value (only used in PER_WAVE mode). An explicit
        per-wave override still wins: it is honoured before the same-area
        rule is even considered.
    log : bool
        When True (default) the resolved decision is logged at INFO. The
        wave dispatcher logs the *authoritative* decision; pass ``log=False``
        for read-only resolutions (e.g. the progress-display banner in
        ``WaveProgressDisplay.start_wave``) so the strategy decision is not
        logged twice per wave (TASK-FIX-MAXPARALLEL01).
    wave_task_paths : Optional[Mapping[str, Optional[Sequence[str]]]]
        One entry per task in this wave, in wave order: the task's id
        mapped to the repository-relative paths it says it will touch, or
        ``None`` when it says nothing. Build it with
        ``collect_wave_task_paths``. When two tasks would work on the same
        area, this wave resolves to 1 whatever the mode would otherwise
        have given, and the reason is logged as one plain sentence. Pass
        the SAME mapping to the display resolution and the authoritative
        one, so the banner shows the number the executor enforces.
    """
    if config.mode == MaxParallelMode.PER_WAVE and wave_override is not None:
        resolved = max(1, wave_override)
        if log:
            logger.info(
                "Wave %d: max_parallel=%d (per-wave override)", wave_number, resolved
            )
        return resolved

    # Two tasks that would work on the same area of the repository do not
    # run at the same time. This comes after the per-wave override (which
    # still wins) and before every mode, because it lowers the wave to a
    # single task whatever the mode would otherwise have resolved.
    same_area = find_same_area_conflict(
        wave_task_paths,
        policy=getattr(config, "same_area", SAME_AREA_DEFAULT),
    )
    if same_area.sequence:
        if log:
            logger.info(
                "Wave %d: max_parallel=1 (one task at a time) — %s",
                wave_number,
                same_area.reason,
            )
        return 1

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
