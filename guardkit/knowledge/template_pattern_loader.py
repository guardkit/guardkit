"""
Template pattern loader — build-time resolution of template pattern context.

Reads a project's ``.claude/manifest.json`` to determine which GuardKit
template was used, resolves the template source directory, and enumerates
all available ``.template`` files. The result is a ``TemplatePatternContext``
dataclass consumed by the selector (TASK-TPL-003) and wiring (TASK-TPL-004).

Usage::

    from guardkit.knowledge.template_pattern_loader import load_template_patterns

    ctx = load_template_patterns(Path(".claude/manifest.json"))
    if ctx.template_name is not None:
        print(f"Template: {ctx.template_name}, files: {len(ctx.available_files)}")
    else:
        print(f"Warnings: {ctx.warnings}")
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from guardkit.templates.resolver import resolve_template_source_dir

logger = logging.getLogger(__name__)


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
