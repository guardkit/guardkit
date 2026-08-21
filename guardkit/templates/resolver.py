"""
Template source directory resolver.

Resolves the source directory for a named GuardKit template against the
``installer/core`` template payload. That payload ships two ways, both handled
transparently here (DF-011):

1. **Packaged (wheel / plain ``pip install``).** ``installer/core`` is mapped
   into the wheel under the guardkit namespace as ``guardkit/_installer_core``
   (hatch ``force-include`` in ``pyproject.toml``) and located via
   :mod:`importlib.resources`. This is the channel DF-011 adds so a plain
   ``pip install guardkit-py`` is self-contained — the F1–F5 validator code and
   the template data it enforces now travel together.
2. **Editable / source install.** The force-included copy exists only in the
   built wheel; an editable install has no ``guardkit/_installer_core`` under the
   checkout, so resolution falls back to the repo's own ``installer/core`` via a
   ``__file__``-relative path.

**Never a top-level ``installer`` package** (DF-011 §2.2 / ``namespace-hygiene``):
``packages = ["guardkit", "installer"]`` would collide with the PyPI
``pypa/installer`` distribution, the same externally-defined-namespace class as
the ``mcp`` shadowing incident. The payload is therefore namespaced under
``guardkit/``.

Usage::

    from guardkit.templates.resolver import resolve_template_source_dir

    template_dir = resolve_template_source_dir("fastapi-python")
    if template_dir is not None:
        print(f"Found template at {template_dir}")
"""

from __future__ import annotations

import importlib.resources as importlib_resources
from pathlib import Path
from typing import Optional

# Force-include target: installer/core -> guardkit/_installer_core in the wheel.
# The subdir layout (templates/, commands/, agents/, ...) is a verbatim 1:1
# mirror of installer/core, so every consumer's relative sub-path is unchanged.
# The leading underscore marks it private/internal (it is the installer/core
# payload, not a public API).
_PACKAGED_SUBDIR = "_installer_core"


def _get_installer_core_dir() -> Path:
    """Return the ``installer/core`` payload root (templates, commands, ...).

    Resolution order (DF-011):

    1. Packaged data under the guardkit namespace
       (``guardkit/_installer_core``), located via :mod:`importlib.resources` —
       present in wheel / plain ``pip`` installs.
    2. The repo checkout's ``installer/core`` (``__file__``-relative) — the
       editable / source-install fallback, since the force-included copy is a
       build-time artefact and does not exist under an editable ``guardkit/``.

    Returns:
        Path to the ``installer/core`` payload root. The packaged path is
        preferred when it exists; otherwise the repo-relative path is returned
        (which may not exist on a broken install — callers already guard with
        ``.is_dir()`` / ``.is_file()``).
    """
    # 1. Packaged data (wheel / plain pip install). importlib.resources resolves
    #    to a real filesystem Path for the normal unzipped-install case; wrap in
    #    Path() so the many rglob()/copy2() consumers keep working unchanged.
    try:
        packaged = Path(str(importlib_resources.files("guardkit"))) / _PACKAGED_SUBDIR
        if packaged.is_dir():
            return packaged
    except (ModuleNotFoundError, TypeError, OSError):
        # ModuleNotFoundError: guardkit not importable (should never happen here).
        # TypeError: a non-filesystem Traversable (zipimport) — not a deploy mode
        #   guardkit supports; fall through to the editable path.
        pass

    # 2. Editable / source install: repo-root installer/core.
    # guardkit/templates/resolver.py -> guardkit/ -> repo root -> installer/core
    repo_root = Path(__file__).resolve().parent.parent.parent
    return repo_root / "installer" / "core"


def resolve_installer_core_dir() -> Path:
    """Public accessor for the ``installer/core`` payload root.

    Same resolution as :func:`_get_installer_core_dir` (packaged
    ``guardkit/_installer_core`` first, repo checkout as the editable-install
    fallback), exposed under a public name so consumers outside this module —
    notably the command-payload staleness check and ``guardkit init --update``
    — reuse the ONE resolution path instead of re-deriving a path themselves.

    Returns:
        Path to the ``installer/core`` payload root. May not exist on a broken
        install; callers guard with ``.is_dir()``.
    """
    return _get_installer_core_dir()


def _get_templates_base_dir() -> Path:
    """Return the base directory containing installed templates.

    Returns:
        Path to the ``installer/core/templates`` base directory (packaged under
        the guardkit namespace, or the repo checkout for editable installs).
    """
    return _get_installer_core_dir() / "templates"


def resolve_template_source_dir(template_name: str) -> Optional[Path]:
    """Resolve the source directory for a template.

    Resolves against the ``installer/core/templates`` payload — packaged in the
    wheel under the guardkit namespace, or the repo checkout for editable
    installs (see :func:`_get_installer_core_dir`).

    The former ``~/.guardkit/templates`` user-override fallback was **removed**
    in DF-011: no installer ever populated it (install.sh writes
    ``~/.agentecflow``), so it was a dead third namespace that only ever
    resolved to ``None``. Removing it leaves exactly one resolution path
    (packaged, with an editable fallback), which cannot silently diverge.

    Args:
        template_name: Name of the template to resolve.

    Returns:
        Path to the template source directory, or None if not found.
    """
    candidate = _get_templates_base_dir() / template_name
    if candidate.is_dir():
        return candidate
    return None
