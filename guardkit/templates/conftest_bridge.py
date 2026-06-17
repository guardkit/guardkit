"""Auto-install the canonical ``features/conftest.py`` pytest-bdd bridge.

Single source of truth for installing the GuardKit ``features/conftest.py``
collection bridge into a target directory (a freshly-created autobuild worktree
or a ``guardkit init`` target). Without the bridge, ``pytest`` cannot collect a
``.feature`` file by path and exits 4 ("ERROR: not found"), which the BDD oracle
historically surfaced as a stacking false-red across every task (FEAT-MEM-07
Error 1, "BDD exit-4 affects every task"). See TASK-AB-BDDNEUTRAL01.

The companion verdict fix in
``guardkit.orchestrator.quality_gates.bdd_runner._is_absent_feature_collection``
makes a missing bridge *neutral* rather than a failure (defence in depth); this
installer removes the missing-bridge condition entirely at bootstrap so tagged
scenarios actually run.

The canonical template lives at
``installer/core/templates/common/features/conftest.py.template`` and is
resolved via the same mechanism ``guardkit init`` uses to locate templates.
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

from guardkit.templates.resolver import _get_templates_base_dir

logger = logging.getLogger(__name__)

# Canonical bridge template, relative to the templates base dir.
_CONFTEST_TEMPLATE_RELPATH = ("common", "features", "conftest.py.template")

# Directory names excluded from the ``.feature`` scan. Mirrors
# ``bdd_runner._EXCLUDED_DIR_NAMES`` so vendored ``.feature`` files shipped with
# third-party packages do not trigger an install. Dotdirs are excluded
# separately (any path part starting with ``.``).
_EXCLUDED_DIR_NAMES: frozenset[str] = frozenset(
    {"node_modules", "__pycache__", "site-packages"}
)


def _features_dir_has_feature_files(features_dir: Path) -> bool:
    """Return True when ``features_dir`` holds at least one ``.feature`` file.

    Uses the same recursive scan + exclusions as ``bdd_runner``'s discovery so
    the installer fires under exactly the conditions the BDD oracle would look
    for feature files (the canonical ``features/`` root).
    """
    if not features_dir.is_dir():
        return False
    for fp in features_dir.rglob("*.feature"):
        rel_parts = fp.relative_to(features_dir).parts
        if any(
            part.startswith(".") or part in _EXCLUDED_DIR_NAMES
            for part in rel_parts
        ):
            continue
        return True
    return False


def install_features_conftest_bridge(target_dir: Path) -> bool:
    """Install ``features/conftest.py`` from the canonical template if needed.

    Idempotent, guarded, and non-raising. Installs only when ALL hold:

    * ``<target_dir>/features`` exists and contains at least one ``.feature``
      file (the project actually uses task-scoped BDD), AND
    * ``<target_dir>/features/conftest.py`` does NOT already exist (never
      clobber a project's own bridge), AND
    * the canonical template is resolvable on disk.

    Returns ``True`` when the bridge was written, ``False`` otherwise (guard not
    met, already present, template missing, or a copy error). Never raises — the
    caller is a bootstrap path (worktree creation / ``guardkit init``) that must
    not fail because of BDD infrastructure.
    """
    try:
        target_dir = Path(target_dir)
        features_dir = target_dir / "features"
        if not _features_dir_has_feature_files(features_dir):
            return False

        dest = features_dir / "conftest.py"
        if dest.exists():
            logger.debug(
                "features/conftest.py already present at %s; not clobbering.",
                dest,
            )
            return False

        template = _get_templates_base_dir().joinpath(*_CONFTEST_TEMPLATE_RELPATH)
        if not template.is_file():
            logger.warning(
                "Cannot auto-install features/conftest.py: canonical template "
                "not found at %s.",
                template,
            )
            return False

        shutil.copy2(template, dest)
        logger.info(
            "Auto-installed features/conftest.py bridge at %s (from %s).",
            dest,
            template,
        )
        return True
    except Exception as exc:  # noqa: BLE001 — bootstrap must not fail on BDD infra
        logger.warning(
            "Failed to auto-install features/conftest.py into %s: %s",
            target_dir,
            exc,
        )
        return False


__all__ = ["install_features_conftest_bridge"]
