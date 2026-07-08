"""Literal ``{{Key}}`` renderer for ``.template`` / ``.j2`` scaffold files.

This is the small library extraction of the ``_render_template`` shim that had
lived inside ``tests/integration/test_template_render_import.py`` (the
``_RENDER_IMPL = "local"`` sentinel). Promoting it here gives guardkit a single,
importable ``.template`` renderer instead of a test-only helper, and it is the
first concrete piece of the **R4 render spike** (the "does guardkit want a
first-class ``.template`` renderer" question the modernization review left open):
this delivers the render half deterministically, leaving Jinja evaluation out of
scope on purpose.

**What it does.** Substitution is *literal* ``{{Key}} -> value`` string
replacement — it is deliberately NOT a Jinja2 evaluator. Files that carry real
Jinja (``{% for %}`` blocks, ``| default(...)`` filters, expression calls) are
out of scope: render them here and the Jinja syntax is left verbatim in the
output. Consumers that need those files handle them explicitly (a layout ``None``
skip in the import tier; the parse gate's opt-out registry).

Two consumers use this module:

* ``guardkit.templates.parse_gate`` renders each scaffold file standalone and
  parses the output per stack (the deterministic template gate, DIM1-F4 / PB-8).
* ``tests/integration/test_template_render_import.py`` renders a whole template
  into a scratch tree via a per-template ``layout`` and import-checks it (the
  stricter langchain-family Python-import smoke, retained alongside the parse
  gate).
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Mapping, Optional, Sequence, Tuple

# A layout is an ordered sequence of (source_prefix, target_prefix) pairs.
# ``target_prefix`` of ``None`` means "skip this source subtree". Longest
# source-prefix match wins. See ``resolve_target``.
Layout = Sequence[Tuple[str, Optional[str]]]

_TEMPLATE_SUFFIXES = (".template", ".j2")


def render_text(source: str, placeholders: Mapping[str, str]) -> str:
    """Substitute ``{{Key}}`` placeholders by literal string replacement.

    No Jinja evaluation is performed. Unknown placeholders are left intact so a
    template bug (or a missing registry entry) surfaces loudly downstream rather
    than being silently eaten. Longer keys are substituted first so a key that is
    a prefix of another (``EntityName`` vs ``EntityNamePlural``) cannot partially
    clobber it.
    """
    rendered = source
    for key in sorted(placeholders, key=len, reverse=True):
        rendered = rendered.replace("{{" + key + "}}", placeholders[key])
    return rendered


def strip_template_suffix(name: str) -> str:
    """Return ``name`` with a trailing ``.template`` / ``.j2`` suffix removed."""
    for suffix in _TEMPLATE_SUFFIXES:
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return name


def resolve_target(src_rel: Path, layout: Layout) -> Optional[Path]:
    """Map a template-root-relative source path to its rendered destination.

    Uses longest-prefix match against ``layout``. A ``None`` target — or no
    match at all — means "skip this file" (returns ``None``). The template
    suffix (``.template`` / ``.j2``) is stripped from the destination.

    For an exact file mapping (the layout prefix is itself a file) the target is
    used verbatim. For a directory mapping the matched prefix is replaced and the
    suffix stripped.
    """
    src_str = src_rel.as_posix()

    best_prefix = ""
    best_target: Optional[str] = ""
    matched = False
    for source_prefix, target in layout:
        if src_str == source_prefix or src_str.startswith(source_prefix):
            if len(source_prefix) > len(best_prefix):
                best_prefix = source_prefix
                best_target = target
                matched = True

    if not matched or best_target is None:
        return None

    if best_prefix.endswith(_TEMPLATE_SUFFIXES):
        dest_str = best_target
    else:
        suffix = src_str[len(best_prefix):]
        dest_str = strip_template_suffix(best_target + suffix)

    return Path(dest_str)


def iter_template_files(template_root: Path) -> List[Path]:
    """Return the sorted ``.template`` and ``.j2`` files under ``template_root``."""
    files: List[Path] = []
    for suffix in _TEMPLATE_SUFFIXES:
        files.extend(template_root.rglob("*" + suffix))
    return sorted(files)


def render_template(
    template_root: Path,
    placeholders: Mapping[str, str],
    layout: Layout,
    output_root: Path,
) -> List[Path]:
    """Render every ``.template`` / ``.j2`` file under ``template_root`` into
    ``output_root`` according to ``layout`` and ``placeholders``.

    Returns the rendered file paths, each relative to ``output_root``. Files the
    layout maps to ``None`` (or does not match) are skipped.
    """
    rendered: List[Path] = []
    for template_path in iter_template_files(template_root):
        src_rel = template_path.relative_to(template_root)
        dest_rel = resolve_target(src_rel, layout)
        if dest_rel is None:
            continue

        content = template_path.read_text(encoding="utf-8")
        rendered_content = render_text(content, placeholders)

        dest_abs = output_root / dest_rel
        dest_abs.parent.mkdir(parents=True, exist_ok=True)
        dest_abs.write_text(rendered_content, encoding="utf-8")
        rendered.append(dest_rel)

    return rendered
