"""``patterns-manifest.json`` sidecar schema + mechanical backfill (PB-7 §3).

Per-template sidecar at ``T/templates/patterns-manifest.json`` — additive,
never touches ``settings.json`` semantics. Declares, per ``.template`` file:
the ``layer`` it belongs to (joins to ``settings.json layer_mappings``, K7),
a ``keywords`` vocabulary for hint-matching, a ``priority`` for deterministic
truncation under the token cap (lowest number survives first), and optional
``pairs_with`` co-selection advice.

This module is read ONLY by :mod:`guardkit.knowledge.template_pattern_loader`
when ``GUARDKIT_PATTERN_SELECTION_V2`` is on — a missing or malformed manifest
degrades to the flag-off path exactly (K4's never-raise contract extends to
this tier). ``load_patterns_manifest`` therefore never raises.

Harvest (``template-create``) emits the manifest for new templates going
forward; :func:`generate_backfill_manifest` derives a mechanical v1 for the
existing shipped templates from directory structure alone (layer = the
loader's real leaf-parent-directory-name join; priority = alphabetical order
within each layer) — a starting point meant to be hand-reviewed, not a
final answer.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

CURRENT_SCHEMA_VERSION = 1

_MANIFEST_FILENAME = "patterns-manifest.json"


@dataclass(frozen=True)
class PatternEntry:
    """One ``.template`` file's selection metadata.

    Attributes:
        file: Template-directory-relative POSIX path (e.g.
            ``"api/router.py.template"``).
        layer: Matchable tag — the loader's leaf-parent-directory-name for
            this file. Not required to equal a ``settings.json
            layer_mappings`` key (it is matched against hint path segments
            and keywords, same as today's directory-name matching).
        keywords: Vocabulary for hint/task-keyword matching.
        priority: Lower survives truncation first (default 1 = highest).
        pairs_with: Optional co-selection advice — other manifest ``file``
            values that should ride along while budget allows.
    """

    file: str
    layer: str
    keywords: List[str] = field(default_factory=list)
    priority: int = 1
    pairs_with: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class PatternsManifest:
    schema_version: int
    patterns: List[PatternEntry]


def _manifest_path(template_dir: Path) -> Path:
    return template_dir / "templates" / _MANIFEST_FILENAME


def _parse_entry(raw: Any) -> Optional[PatternEntry]:
    """Parse one raw pattern dict. Returns None on any malformed shape."""
    if not isinstance(raw, dict):
        return None
    file_ = raw.get("file")
    layer = raw.get("layer")
    if not isinstance(file_, str) or not file_:
        return None
    if not isinstance(layer, str) or not layer:
        return None

    keywords = raw.get("keywords", [])
    if not isinstance(keywords, list) or not all(isinstance(k, str) for k in keywords):
        return None

    priority = raw.get("priority", 1)
    if not isinstance(priority, int) or isinstance(priority, bool):
        return None

    pairs_with = raw.get("pairs_with", [])
    if not isinstance(pairs_with, list) or not all(isinstance(p, str) for p in pairs_with):
        return None

    return PatternEntry(
        file=file_,
        layer=layer,
        keywords=list(keywords),
        priority=priority,
        pairs_with=list(pairs_with),
    )


def load_patterns_manifest(template_dir: Path) -> Optional[PatternsManifest]:
    """Load and validate the sidecar manifest for one template.

    Returns ``None`` on ANY failure — missing file, invalid JSON, wrong/
    missing ``schema_version``, a non-list ``patterns``, or any malformed
    entry. Never raises: the caller (selector v2) treats ``None`` as
    "degrade to the flag-off path", so a partially-bad manifest can never
    make selection louder or emptier than today.
    """
    path = _manifest_path(template_dir)
    try:
        raw_text = path.read_text(encoding="utf-8")
    except OSError:
        return None

    try:
        data = json.loads(raw_text)
    except ValueError:
        return None

    if not isinstance(data, dict):
        return None

    schema_version = data.get("schema_version")
    if schema_version != CURRENT_SCHEMA_VERSION:
        return None

    raw_patterns = data.get("patterns")
    if not isinstance(raw_patterns, list):
        return None

    entries: List[PatternEntry] = []
    for raw_entry in raw_patterns:
        entry = _parse_entry(raw_entry)
        if entry is None:
            # One malformed entry invalidates the whole manifest — a partial,
            # silently-degraded selection is worse than falling back cleanly.
            return None
        entries.append(entry)

    return PatternsManifest(schema_version=schema_version, patterns=entries)


def manifest_to_dict(manifest: PatternsManifest) -> Dict[str, Any]:
    """Serialize a ``PatternsManifest`` to the on-disk JSON shape."""
    return {
        "schema_version": manifest.schema_version,
        "patterns": [asdict(p) for p in manifest.patterns],
    }


def write_patterns_manifest(template_dir: Path, manifest: PatternsManifest) -> Path:
    """Write ``manifest`` to ``T/templates/patterns-manifest.json``. Returns the path."""
    path = _manifest_path(template_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest_to_dict(manifest), indent=2) + "\n", encoding="utf-8")
    return path


def generate_backfill_manifest(template_dir: Path) -> PatternsManifest:
    """Mechanically derive a v1 manifest from directory structure.

    Layer is the loader's REAL join key — the immediate parent directory
    name of each ``.template`` file (matching
    ``template_pattern_loader._match_files_by_subdirs``), so a backfilled
    manifest never claims coverage the flag-off loader could not itself
    reach. Priority is alphabetical order within each layer (1-indexed).
    ``keywords`` and ``pairs_with`` start empty — this is a mechanical
    starting point for hand review, not a semantic analysis.
    """
    templates_subdir = template_dir / "templates"
    if not templates_subdir.is_dir():
        return PatternsManifest(schema_version=CURRENT_SCHEMA_VERSION, patterns=[])

    files = sorted(templates_subdir.rglob("*.template"))

    # Group by leaf parent-dir name, assign priority by alpha order per group.
    by_layer: Dict[str, List[Path]] = {}
    for fpath in files:
        by_layer.setdefault(fpath.parent.name, []).append(fpath)

    entries: List[PatternEntry] = []
    for layer in sorted(by_layer):
        group = sorted(by_layer[layer])
        for idx, fpath in enumerate(group, start=1):
            rel = fpath.relative_to(templates_subdir).as_posix()
            entries.append(
                PatternEntry(file=rel, layer=layer, keywords=[], priority=idx, pairs_with=[])
            )

    return PatternsManifest(schema_version=CURRENT_SCHEMA_VERSION, patterns=entries)


__all__ = [
    "CURRENT_SCHEMA_VERSION",
    "PatternEntry",
    "PatternsManifest",
    "load_patterns_manifest",
    "manifest_to_dict",
    "write_patterns_manifest",
    "generate_backfill_manifest",
]
