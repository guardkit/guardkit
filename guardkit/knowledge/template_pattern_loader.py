"""
Template pattern loader — build-time resolution of template pattern context.

Reads a project's ``.claude/manifest.json`` to determine which GuardKit
template was used, resolves the template source directory, and enumerates
all available ``.template`` files. The result is a ``TemplatePatternContext``
dataclass consumed by the selector (TASK-TPL-003) and wiring (TASK-TPL-004).

The ``select_patterns`` function (TASK-TPL-003) narrows the available files
to a relevant subset using file-path hints, tech-stack matching, and
alphabetical fallback, respecting file-count and token-budget caps.

**Selection v2 (PB-7, flag-gated).** Set ``GUARDKIT_PATTERN_SELECTION_V2=1``
to switch selection to the per-template ``patterns-manifest.json`` sidecar
(declared ``layer``/``keywords``/``priority``/``pairs_with``) instead of the
hardcoded ``_TECH_STACK_SUBDIR_MAP`` + directory-name matching. Default OFF —
``select_patterns`` with the flag unset is byte-identical to today's
behaviour (see ``tests/unit/templates/test_selection_parity.py``). A missing
or malformed manifest degrades to the flag-off path exactly, extending K4's
never-raise contract to this tier.

Usage::

    from guardkit.knowledge.template_pattern_loader import (
        load_template_patterns,
        select_patterns,
    )

    ctx = load_template_patterns(Path(".claude/manifest.json"))
    ctx = select_patterns(ctx, tech_stack="Python", file_path_hints=["app/api/users.py"])
    for f in ctx.selected_files:
        print(f)
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional, Set

from guardkit.templates.resolver import resolve_template_source_dir

if TYPE_CHECKING:
    from guardkit.templates.patterns_manifest import PatternsManifest

logger = logging.getLogger(__name__)

_PATTERN_SELECTION_V2_ENV = "GUARDKIT_PATTERN_SELECTION_V2"


def pattern_selection_v2_enabled() -> bool:
    """Whether manifest-driven selection v2 is active (default OFF).

    Kill switch stays the flag itself: ``GUARDKIT_PATTERN_SELECTION_V2=0``
    (or unset) always resolves to the v1 path. Any future default flip lands
    as its own commit per the WS3 calibration protocol (PB-7 scope §4) — this
    function's default must not change outside that event.
    """
    raw = os.environ.get(_PATTERN_SELECTION_V2_ENV)
    if raw is None:
        return False
    return raw.strip().lower() in {"1", "true", "on", "yes"}


@dataclass
class TemplatePatternContext:
    """Context produced by the template pattern loader.

    Fields ``selected_files`` and ``prompt_block`` are populated by
    downstream tasks (selector and wiring respectively); they start empty.

    Attributes:
        template_name: Resolved template name, or ``None`` if unresolved.
        template_dir: Path to the template source directory, or ``None``.
        available_files: All ``.template`` files found under the template dir.
        selected_files: Populated by the selector (TASK-TPL-003).
        prompt_block: Formatted for injection; populated by wiring (TASK-TPL-004).
        warnings: Graceful-degradation messages collected during loading.
    """

    template_name: Optional[str]
    template_dir: Optional[Path]
    available_files: List[Path]
    selected_files: List[Path] = field(default_factory=list)
    prompt_block: str = ""
    warnings: List[str] = field(default_factory=list)


def _make_degraded_context(warning: str) -> TemplatePatternContext:
    """Return a TemplatePatternContext representing a graceful failure.

    Args:
        warning: Human-readable description of what went wrong.

    Returns:
        A context with ``template_name=None`` and the warning recorded.
    """
    return TemplatePatternContext(
        template_name=None,
        template_dir=None,
        available_files=[],
        warnings=[warning],
    )


def load_template_patterns(manifest_path: Path) -> TemplatePatternContext:
    """Load template pattern context from a project manifest.

    Reads ``.claude/manifest.json``, extracts the ``name`` field, resolves the
    corresponding template source directory, and enumerates all ``.template``
    files under its ``templates/`` subdirectory.

    On **any** failure (missing file, invalid JSON, unknown template, missing
    ``templates/`` subdirectory) the function returns a
    ``TemplatePatternContext`` with ``template_name=None`` and a descriptive
    warning — it **never** raises.

    Args:
        manifest_path: Path to the ``.claude/manifest.json`` file.

    Returns:
        A populated ``TemplatePatternContext``.
    """
    # --- Read manifest file ---------------------------------------------------
    try:
        raw = manifest_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        msg = f"Manifest not found: {manifest_path}"
        logger.warning(msg)
        return _make_degraded_context(msg)
    except OSError as exc:
        msg = f"Cannot read manifest {manifest_path}: {exc}"
        logger.warning(msg)
        return _make_degraded_context(msg)

    # --- Parse JSON -----------------------------------------------------------
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        msg = f"Invalid JSON in {manifest_path}: {exc}"
        logger.warning(msg)
        return _make_degraded_context(msg)

    # --- Extract name field ---------------------------------------------------
    template_name = data.get("name")
    if not template_name or not isinstance(template_name, str):
        msg = (
            f"Manifest {manifest_path} does not contain a valid `name` field "
            f"(got {template_name!r})"
        )
        logger.warning(msg)
        return _make_degraded_context(msg)

    # --- Resolve template directory -------------------------------------------
    template_dir = resolve_template_source_dir(template_name)
    if template_dir is None:
        msg = (
            f"Cannot resolve template source directory for '{template_name}'"
        )
        logger.warning(msg)
        return TemplatePatternContext(
            template_name=template_name,
            template_dir=None,
            available_files=[],
            warnings=[msg],
        )

    # --- Enumerate .template files --------------------------------------------
    templates_subdir = template_dir / "templates"
    warnings: List[str] = []

    if not templates_subdir.is_dir():
        msg = (
            f"No templates/ subdirectory found under {template_dir}"
        )
        logger.warning(msg)
        warnings.append(msg)
        available_files: List[Path] = []
    else:
        available_files = sorted(templates_subdir.rglob("*.template"))

    return TemplatePatternContext(
        template_name=template_name,
        template_dir=template_dir,
        available_files=available_files,
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# Domain-hint selector (TASK-TPL-003)
# ---------------------------------------------------------------------------

# Tech-stack keyword → template subdirectory name mappings.
# Each tech-stack keyword maps to subdirectory names likely relevant to it.
_TECH_STACK_SUBDIR_MAP: dict[str, list[str]] = {
    "python": ["api", "core", "config", "models", "schemas", "crud", "db"],
    "fastapi": ["api", "core", "config", "models", "schemas", "crud", "db", "dependencies"],
    "django": ["api", "models", "views", "templates", "static"],
    "react": ["components", "hooks", "pages", "styles", "utils"],
    "typescript": ["components", "hooks", "pages", "types", "utils"],
    "nextjs": ["pages", "components", "api", "styles", "public"],
    "dotnet": ["controllers", "models", "services", "data", "middleware"],
}


def _extract_path_segments(file_path_hints: List[str]) -> List[str]:
    """Extract unique directory segments from file path hints.

    For each hint like ``app/api/users.py``, extracts the directory
    segments (``app``, ``api``) and returns deduplicated segments.

    Args:
        file_path_hints: List of file path strings.

    Returns:
        Deduplicated list of path segments (lowercased), preserving order.
    """
    seen: set[str] = set()
    segments: List[str] = []
    for hint in file_path_hints:
        parts = Path(hint).parts
        # Exclude the filename itself — only directory segments
        for part in parts[:-1]:
            lower = part.lower()
            if lower not in seen:
                seen.add(lower)
                segments.append(lower)
    return segments


def _match_files_by_subdirs(
    available_files: List[Path],
    target_subdirs: List[str],
) -> List[Path]:
    """Select files whose parent directory name matches any target subdir.

    Args:
        available_files: All available ``.template`` files (absolute paths).
        target_subdirs: Subdirectory names to match against (lowercased).

    Returns:
        Matched files in the order they appear in ``available_files``.
    """
    target_set = set(target_subdirs)
    matched: List[Path] = []
    for fpath in available_files:
        # Match the immediate parent directory name
        parent_name = fpath.parent.name.lower()
        if parent_name in target_set:
            matched.append(fpath)
    return matched


def _estimate_tokens(file_path: Path) -> int:
    """Estimate the token count of a file using the rough 4-chars-per-token heuristic.

    Args:
        file_path: Path to the file.

    Returns:
        Estimated token count; 0 if the file cannot be read.
    """
    try:
        content = file_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return 0
    return len(content) // 4


def _apply_selection_caps(
    candidates: List[Path],
    max_files: int,
    max_tokens: int,
    warnings: List[str],
) -> "tuple[List[Path], List[str]]":
    """Dedup, apply ``max_files``, then apply the rough token budget.

    Shared by v1 and v2 selection so cap semantics can never diverge between
    the two paths — this is Step 4 of the original ``select_patterns``,
    extracted verbatim.
    """
    seen_paths: Set[str] = set()
    deduped: List[Path] = []
    for f in candidates:
        key = str(f)
        if key not in seen_paths:
            seen_paths.add(key)
            deduped.append(f)
    candidates = deduped

    if len(candidates) > max_files:
        candidates = candidates[:max_files]

    selected: List[Path] = []
    token_total = 0
    for fpath in candidates:
        tokens = _estimate_tokens(fpath)
        if token_total + tokens > max_tokens and selected:
            warnings.append(
                f"Skipped {fpath.name}: adding {tokens} tokens would exceed "
                f"budget ({token_total}/{max_tokens})"
            )
            continue
        selected.append(fpath)
        token_total += tokens

    logger.debug(
        "select_patterns: %d candidates → %d selected (%d tokens)",
        len(candidates),
        len(selected),
        token_total,
    )
    return selected, warnings


def select_patterns(
    context: TemplatePatternContext,
    tech_stack: str,
    file_path_hints: List[str],
    max_files: int = 5,
    max_tokens: int = 3000,
) -> TemplatePatternContext:
    """Select relevant template pattern files based on domain hints.

    Dispatches to v1 (default) or v2 (``GUARDKIT_PATTERN_SELECTION_V2=1``,
    manifest-driven — see module docstring). v2 falls back to v1 whenever no
    usable ``patterns-manifest.json`` is found, so a missing/malformed
    manifest degrades to exactly today's behaviour.

    The function returns a **new** ``TemplatePatternContext`` — it does not
    mutate the input context's ``available_files`` or ``selected_files``.

    Args:
        context: The template pattern context from ``load_template_patterns``.
        tech_stack: Technology stack string (e.g., ``"Python"``, ``"FastAPI"``).
        file_path_hints: File paths the task touches (e.g., ``["app/api/users.py"]``).
        max_files: Maximum number of files to return (default 5).
        max_tokens: Approximate token budget for selected file contents (default 3000).

    Returns:
        A new ``TemplatePatternContext`` with ``selected_files`` and
        ``warnings`` populated.
    """
    if pattern_selection_v2_enabled() and context.template_dir is not None:
        from guardkit.templates.patterns_manifest import load_patterns_manifest

        manifest = load_patterns_manifest(context.template_dir)
        if manifest is not None and manifest.patterns:
            return _select_patterns_v2(
                context, tech_stack, file_path_hints, manifest, max_files, max_tokens
            )
    return _select_patterns_v1(context, tech_stack, file_path_hints, max_files, max_tokens)


def _select_patterns_v1(
    context: TemplatePatternContext,
    tech_stack: str,
    file_path_hints: List[str],
    max_files: int,
    max_tokens: int,
) -> TemplatePatternContext:
    """Today's selection: directory-name matching, no manifest.

    Selection rules (in priority order):

    1. **File-path hints take precedence.** For each hint, match path segments
       against template subdirectory names and collect matching ``.template``
       files.
    2. **Tech-stack fallback.** If file-path hints produced zero matches, fall
       back to tech-stack keyword matching against subdirectory names.
    3. **Alphabetical fallback.** If still nothing, take the first 3 files
       alphabetically.
    4. **Cap enforcement.** Truncate to ``max_files`` (default 5). Compute
       rough token count (``len(content) / 4``); stop adding files once
       ``max_tokens`` reached. Record skipped files as warnings.
    """
    available = list(context.available_files)  # defensive copy
    warnings: List[str] = list(context.warnings)  # carry forward existing warnings

    # Early exit: nothing to select from
    if not available:
        return TemplatePatternContext(
            template_name=context.template_name,
            template_dir=context.template_dir,
            available_files=context.available_files,
            selected_files=[],
            prompt_block=context.prompt_block,
            warnings=warnings,
        )

    # --- Step 1: File-path hint matching ---
    candidates: List[Path] = []
    if file_path_hints:
        segments = _extract_path_segments(file_path_hints)
        if segments:
            candidates = _match_files_by_subdirs(available, segments)

    # --- Step 2: Tech-stack fallback ---
    if not candidates and tech_stack:
        tech_lower = tech_stack.lower()
        # Look for a direct mapping first, then partial keyword match
        mapped_subdirs: List[str] = []
        for keyword, subdirs in _TECH_STACK_SUBDIR_MAP.items():
            if keyword in tech_lower or tech_lower in keyword:
                mapped_subdirs.extend(subdirs)
        if mapped_subdirs:
            candidates = _match_files_by_subdirs(available, mapped_subdirs)

    # --- Step 3: Alphabetical fallback ---
    if not candidates:
        sorted_available = sorted(available)
        candidates = sorted_available[:3]

    # --- Step 4: Cap enforcement ---
    selected, warnings = _apply_selection_caps(candidates, max_files, max_tokens, warnings)

    return TemplatePatternContext(
        template_name=context.template_name,
        template_dir=context.template_dir,
        available_files=context.available_files,
        selected_files=selected,
        prompt_block=context.prompt_block,
        warnings=warnings,
    )


def _select_patterns_v2(
    context: TemplatePatternContext,
    tech_stack: str,
    file_path_hints: List[str],
    manifest: "PatternsManifest",
    max_files: int,
    max_tokens: int,
) -> TemplatePatternContext:
    """Manifest-driven selection (``GUARDKIT_PATTERN_SELECTION_V2=1``).

    Same staged fallback shape as v1 (hints > tech-stack > alphabetical), but
    steps 1-2 match against the manifest's declared ``layer``/``keywords``
    instead of raw directory names, honour ``priority`` ordering, and pull in
    ``pairs_with`` co-selection advice while the caps allow. Step 3 (no
    match) and Step 4 (cap enforcement) are identical to v1 — the caps are
    never relaxed under the flag (K4).
    """
    available = list(context.available_files)
    warnings: List[str] = list(context.warnings)

    if not available:
        return TemplatePatternContext(
            template_name=context.template_name,
            template_dir=context.template_dir,
            available_files=context.available_files,
            selected_files=[],
            prompt_block=context.prompt_block,
            warnings=warnings,
        )

    templates_subdir = context.template_dir / "templates"  # type: ignore[operator]
    available_by_rel: Dict[str, Path] = {}
    for f in available:
        try:
            rel = f.relative_to(templates_subdir).as_posix()
        except ValueError:
            continue
        available_by_rel[rel] = f

    entries_by_rel = {e.file: e for e in manifest.patterns}

    # --- Step 1: hint-segment matching against layer/keywords ---
    matched_entries = []
    if file_path_hints:
        segments = set(_extract_path_segments(file_path_hints))
        if segments:
            for entry in manifest.patterns:
                if entry.layer.lower() in segments:
                    matched_entries.append(entry)
                elif any(k.lower() in segments for k in entry.keywords):
                    matched_entries.append(entry)

    # --- Step 2: tech-stack fallback (same subdir table as v1, matched
    #     against declared layer) ---
    if not matched_entries and tech_stack:
        tech_lower = tech_stack.lower()
        mapped_subdirs: Set[str] = set()
        for keyword, subdirs in _TECH_STACK_SUBDIR_MAP.items():
            if keyword in tech_lower or tech_lower in keyword:
                mapped_subdirs.update(s.lower() for s in subdirs)
        if mapped_subdirs:
            for entry in manifest.patterns:
                if entry.layer.lower() in mapped_subdirs:
                    matched_entries.append(entry)

    # --- Step 3: alphabetical fallback (manifest-agnostic, same as v1) ---
    if not matched_entries:
        sorted_available = sorted(available)
        candidates = sorted_available[:3]
        selected, warnings = _apply_selection_caps(candidates, max_files, max_tokens, warnings)
        return TemplatePatternContext(
            template_name=context.template_name,
            template_dir=context.template_dir,
            available_files=context.available_files,
            selected_files=selected,
            prompt_block=context.prompt_block,
            warnings=warnings,
        )

    # Priority ascending (stable sort keeps match-stage order for ties).
    matched_entries.sort(key=lambda e: e.priority)

    # Honour pairs_with: queue each matched entry, then its declared pairs —
    # only when the pair is a real manifest entry resolvable on disk.
    ordered_rels: List[str] = []
    seen_rels: Set[str] = set()
    for entry in matched_entries:
        if entry.file not in seen_rels:
            ordered_rels.append(entry.file)
            seen_rels.add(entry.file)
        for paired in entry.pairs_with:
            if paired in seen_rels:
                continue
            if paired in entries_by_rel and paired in available_by_rel:
                ordered_rels.append(paired)
                seen_rels.add(paired)

    candidates = [available_by_rel[rel] for rel in ordered_rels if rel in available_by_rel]

    selected, warnings = _apply_selection_caps(candidates, max_files, max_tokens, warnings)

    return TemplatePatternContext(
        template_name=context.template_name,
        template_dir=context.template_dir,
        available_files=context.available_files,
        selected_files=selected,
        prompt_block=context.prompt_block,
        warnings=warnings,
    )
