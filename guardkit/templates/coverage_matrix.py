"""Exemplar-layer coverage matrix (DIM1-F3 / PB-7).

For each shipped template ``T``, computes whether every ``settings.json
layer_mappings`` key has at least one gate-validated, **loader-reachable**
``.template`` exemplar — the invariant the review's DIM1-F3 finding names:
harvest investment lives on the agent-prose side while the exemplar layer
(the *only* thing a template feeds the autobuild Player at build time,
``guardkit.knowledge.autobuild_context_loader._append_template_patterns``) has
no coverage requirement.

**A cell is COVERED iff all three hold** (design of record §2):

1. ``templates_present`` — >=1 ``.template`` file exists anywhere under the
   layer's effective subdirectory tree.
2. ``loader_reachable`` — the loader's REAL join is parent-directory-name
   equality (:func:`guardkit.knowledge.template_pattern_loader._match_files_by_subdirs`,
   case-insensitive). A file nested one level deeper than the layer's
   subdirectory (``templates/<subdir>/nested/x.py.template``) is
   ``templates_present`` but NOT ``loader_reachable`` — the loader would never
   select it. The effective subdirectory is ``layer_mapping.template_subdir``
   (additive optional alias) if present, else the layer key itself.
3. ``gate_status`` — >=1 of the loader-reachable files passes PB-8's
   deterministic render+parse gate (:mod:`guardkit.templates.parse_gate`) with
   status ``OK``. A file that is ``OPTOUT`` or ``SKIPPED`` (non-gated
   language, e.g. ``.ini``/``.toml``) counts toward *existence* but never
   toward *validated* coverage (``absence-of-failure-is-not-success.md``): a
   layer whose only reachable files are opt-out/skipped/error reports
   ``WARN``, never ``COVERED``.

**Enforcement posture — report-only first.** :data:`COVERAGE_ENFORCED` is the
declarative per-template opt-in registry (same seed-registry shape as
:data:`guardkit.templates.parse_gate.PARSE_OPTOUT`): templates on the list
must have zero non-covered rows; templates absent from it are report-only.
Empty at first — templates flip in one at a time as their holes are filled.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import FrozenSet, Iterable, List, Optional, Tuple

from guardkit.templates.parse_gate import FileStatus, check_file

# ---------------------------------------------------------------------------
# Declarative per-template enforcement registry (DATA)
# ---------------------------------------------------------------------------
#
# Templates named here must have zero non-covered rows in their matrix, or
# the CLI/CI check exits non-zero. Empty at first (report-only for every
# shipped template) — a template flips in individually once its holes are
# filled, mirroring PARSE_OPTOUT / the import tier's TEMPLATES registry.
#
# fastapi-python (PB-7 build step 4): 7/9 -> 9/9 after authoring a real
# services/service.py.template exemplar and adding the tests->testing
# template_subdir alias. Its config/ subdir (alembic.ini/pyproject.toml, both
# non-code) is deliberately NOT given a layer_mappings entry — the parse gate
# cannot validate non-gated-language files (see LANGUAGE_BY_EXT in
# parse_gate.py), so a "config" row could never leave WARN. Disposed of as
# intentionally loader-invisible packaging config rather than a permanent
# unwinnable row.
COVERAGE_ENFORCED: FrozenSet[str] = frozenset({"fastapi-python"})


class CoverageStatus(str, Enum):
    COVERED = "covered"
    WARN = "warn"       # present, at least one reachable file, none gate-OK
    MISSING = "missing"  # no loader-reachable file at all


@dataclass(frozen=True)
class LayerCoverage:
    """Coverage result for one ``layer_mappings`` key of one template."""

    layer: str
    effective_subdir: str
    used_alias: bool
    templates_present: bool
    loader_reachable: bool
    reachable_files: Tuple[str, ...] = field(default_factory=tuple)
    gate_ok_files: Tuple[str, ...] = field(default_factory=tuple)
    gate_optout_files: Tuple[str, ...] = field(default_factory=tuple)
    gate_error_files: Tuple[str, ...] = field(default_factory=tuple)
    gate_skipped_files: Tuple[str, ...] = field(default_factory=tuple)

    @property
    def status(self) -> CoverageStatus:
        if not self.templates_present or not self.loader_reachable:
            return CoverageStatus.MISSING
        if self.gate_ok_files:
            return CoverageStatus.COVERED
        return CoverageStatus.WARN


@dataclass(frozen=True)
class TemplateCoverage:
    """Coverage matrix for one template — one row per ``layer_mappings`` key."""

    template_name: str
    layers: Tuple[LayerCoverage, ...]
    enforced: bool

    @property
    def covered_count(self) -> int:
        return sum(1 for layer in self.layers if layer.status is CoverageStatus.COVERED)

    @property
    def total_count(self) -> int:
        return len(self.layers)

    @property
    def fully_covered(self) -> bool:
        """True when every row is COVERED (vacuously True for zero rows)."""
        return all(layer.status is CoverageStatus.COVERED for layer in self.layers)

    @property
    def non_covered(self) -> Tuple[LayerCoverage, ...]:
        return tuple(
            layer for layer in self.layers if layer.status is not CoverageStatus.COVERED
        )


def _default_templates_base() -> Path:
    from guardkit.templates.resolver import _get_templates_base_dir

    return _get_templates_base_dir()


def _load_settings(template_dir: Path) -> Optional[dict]:
    import json

    settings_path = template_dir / "settings.json"
    if not settings_path.is_file():
        return None
    try:
        return json.loads(settings_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _enumerate_dot_template_files(template_dir: Path) -> List[Path]:
    """The loader's REAL file universe: ``.template`` only, not ``.j2``.

    Mirrors ``template_pattern_loader.load_template_patterns``
    (``templates_subdir.rglob("*.template")``) — a ``.j2``-only layer is
    invisible to the build-time loader regardless of directory naming.
    """
    templates_subdir = template_dir / "templates"
    if not templates_subdir.is_dir():
        return []
    return sorted(templates_subdir.rglob("*.template"))


def _compute_layer_coverage(
    layer: str,
    mapping: dict,
    template_dir: Path,
    available: List[Path],
    check: bool,
) -> LayerCoverage:
    template_subdir = mapping.get("template_subdir") if isinstance(mapping, dict) else None
    used_alias = bool(template_subdir)
    effective_subdir = template_subdir if used_alias else layer

    templates_subdir = template_dir / "templates" / effective_subdir
    templates_present = templates_subdir.is_dir() and any(
        templates_subdir.rglob("*.template")
    )

    # loader_reachable: the loader's real join is leaf-parent-dir-name equality
    # (case-insensitive), NOT "anywhere under the subdir tree".
    target = effective_subdir.lower()
    reachable = [f for f in available if f.parent.name.lower() == target]
    loader_reachable = bool(reachable)

    gate_ok: List[str] = []
    gate_optout: List[str] = []
    gate_error: List[str] = []
    gate_skipped: List[str] = []
    if check:
        for fpath in reachable:
            rel = fpath.relative_to(template_dir).as_posix()
            result = check_file(fpath, rel)
            if result.status is FileStatus.OK:
                gate_ok.append(rel)
            elif result.status is FileStatus.OPTOUT:
                gate_optout.append(rel)
            elif result.status is FileStatus.ERROR:
                gate_error.append(rel)
            else:
                gate_skipped.append(rel)

    return LayerCoverage(
        layer=layer,
        effective_subdir=effective_subdir,
        used_alias=used_alias,
        templates_present=templates_present,
        loader_reachable=loader_reachable,
        reachable_files=tuple(f.relative_to(template_dir).as_posix() for f in reachable),
        gate_ok_files=tuple(gate_ok),
        gate_optout_files=tuple(gate_optout),
        gate_error_files=tuple(gate_error),
        gate_skipped_files=tuple(gate_skipped),
    )


def compute_coverage(
    template_name: str,
    templates_base: Optional[Path] = None,
    *,
    check_gate: bool = True,
) -> TemplateCoverage:
    """Compute the coverage matrix for one template.

    Args:
        template_name: Directory name under the templates base (e.g.
            ``"fastapi-python"``).
        templates_base: Override for the templates base directory (tests).
        check_gate: When False, skips the PB-8 gate check (every row's
            gate_status is treated as not-validated) — used when the
            tree-sitter runtime is unavailable so the tool still reports
            presence/reachability rather than raising.

    Returns:
        A ``TemplateCoverage`` with one ``LayerCoverage`` row per
        ``settings.json layer_mappings`` key. A template with no
        ``settings.json`` or an empty/missing ``layer_mappings`` yields zero
        rows (vacuously ``fully_covered``) — it is simply not this tool's
        concern, matching ``default``/``react-fastapi-monorepo`` today.
    """
    base = templates_base if templates_base is not None else _default_templates_base()
    return compute_coverage_for_dir(base / template_name, template_name, check_gate=check_gate)


def compute_coverage_for_dir(
    template_dir: Path,
    template_name: Optional[str] = None,
    *,
    check_gate: bool = True,
) -> TemplateCoverage:
    """Compute the coverage matrix for an arbitrary template directory.

    Unlike :func:`compute_coverage`, ``template_dir`` need not live under the
    installed templates base — this is what a freshly-harvested
    ``template-create`` output directory (global ``~/.agentecflow/templates/``
    or repo ``installer/core/templates/``) uses to report its own coverage as
    a closing harvest step, before the template is ever "installed".

    Args:
        template_dir: The template's root directory (containing
            ``settings.json`` and ``templates/``).
        template_name: Display name for the report; defaults to
            ``template_dir.name``.
        check_gate: See :func:`compute_coverage`.
    """
    name = template_name if template_name is not None else template_dir.name

    layers: List[LayerCoverage] = []
    settings = _load_settings(template_dir)
    layer_mappings = settings.get("layer_mappings") if isinstance(settings, dict) else None
    if isinstance(layer_mappings, dict) and layer_mappings:
        available = _enumerate_dot_template_files(template_dir)
        for layer, mapping in layer_mappings.items():
            mapping = mapping if isinstance(mapping, dict) else {}
            layers.append(
                _compute_layer_coverage(layer, mapping, template_dir, available, check_gate)
            )

    return TemplateCoverage(
        template_name=name,
        layers=tuple(layers),
        enforced=name in COVERAGE_ENFORCED,
    )


def compute_coverage_all(
    names: Optional[Iterable[str]] = None,
    templates_base: Optional[Path] = None,
    *,
    check_gate: bool = True,
) -> List[TemplateCoverage]:
    """Compute the coverage matrix for the named templates (all, by default)."""
    from guardkit.templates.parse_gate import list_template_names

    base = templates_base if templates_base is not None else _default_templates_base()
    selected = list(names) if names is not None else list_template_names(base)

    results: List[TemplateCoverage] = []
    for name in selected:
        if not (base / name).is_dir():
            continue
        results.append(compute_coverage(name, base, check_gate=check_gate))
    return results


def gate_is_available() -> bool:
    """True if the PB-8 parse-gate's tree-sitter runtime is importable."""
    from guardkit.templates.parse_gate import available_languages

    return available_languages()


__all__ = [
    "COVERAGE_ENFORCED",
    "CoverageStatus",
    "LayerCoverage",
    "TemplateCoverage",
    "compute_coverage",
    "compute_coverage_all",
    "compute_coverage_for_dir",
    "gate_is_available",
]
