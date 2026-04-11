"""
Template source directory resolver.

Resolves the source directory for a named GuardKit template by checking
installed package templates first, then falling back to user-installed
templates at ``~/.guardkit/templates/``.

Usage::

    from guardkit.templates.resolver import resolve_template_source_dir

    template_dir = resolve_template_source_dir("fastapi-python")
    if template_dir is not None:
        print(f"Found template at {template_dir}")
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional


def _get_templates_base_dir() -> Path:
    """Return the base directory containing installed templates.

    Uses __file__-relative path to locate installer/core/templates/
    from the guardkit package installation.

    Returns:
        Path to the templates base directory.
    """
    # guardkit/templates/resolver.py -> guardkit/ -> project root -> installer/core/templates/
    package_root = Path(__file__).resolve().parent.parent.parent
    return package_root / "installer" / "core" / "templates"


def _get_user_templates_dir() -> Path:
    """Return the user-level templates directory (~/.guardkit/templates/).

    Returns:
        Path to the user templates directory.
    """
    return Path.home() / ".guardkit" / "templates"


def resolve_template_source_dir(template_name: str) -> Optional[Path]:
    """Resolve the source directory for a template.

    Checks installed package templates first, then falls back to
    user-installed templates at ~/.guardkit/templates/.

    Args:
        template_name: Name of the template to resolve.

    Returns:
        Path to the template source directory, or None if not found.
    """
    # Check package-installed templates
    pkg_templates = _get_templates_base_dir()
    pkg_candidate = pkg_templates / template_name
    if pkg_candidate.is_dir():
        return pkg_candidate

    # Fallback: user-installed templates
    user_templates = _get_user_templates_dir()
    user_candidate = user_templates / template_name
    if user_candidate.is_dir():
        return user_candidate

    return None
