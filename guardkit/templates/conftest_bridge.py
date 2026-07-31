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


# ---------------------------------------------------------------------------
# TS-lane D.1c — the language check
# ---------------------------------------------------------------------------
#
# The bridge is a PYTEST-BDD collection hook. Written into a TypeScript repo
# it is not merely useless, it is a lie on disk: a Python file the Player
# never wrote, in a repo with no Python at all, that the factory then has to
# explain. ``ts-api-test`` reaches this code path for real — it carries
# ``features/get-time-endpoint/get-time-endpoint.feature`` (verified
# 2026-07-31), so without this check its very first worktree would receive a
# stray ``features/conftest.py``.
#
# The check is deliberately NEGATIVE, not positive. It refuses only when the
# target is POSITIVELY non-Python: a node manifest present AND no Python
# manifest at all. Backwards compatibility is the prime invariant — a repo
# with no ``package.json`` (i.e. every repo in the estate before tonight),
# and a polyglot repo carrying both, behave byte-for-byte as they did. Only
# the pure JS/TS repo is newly excluded, which is the whole of the cure.
_NODE_MANIFESTS: tuple[str, ...] = (
    "package.json",
    "tsconfig.json",
)

_PYTHON_MANIFESTS: tuple[str, ...] = (
    "pyproject.toml",
    "setup.py",
    "setup.cfg",
    "Pipfile",
    "tox.ini",
    "pytest.ini",
    "conftest.py",
)


def _is_non_python_worktree(target_dir: Path) -> bool:
    """Return True when ``target_dir`` is positively a non-Python project.

    "Positively" carries the weight: an absent Python manifest alone is not
    enough (the pre-existing tests install the bridge into a bare directory
    holding nothing but ``features/``, and that must keep working). A node
    manifest must be present AND every Python marker absent.
    """
    try:
        has_node = any((target_dir / m).is_file() for m in _NODE_MANIFESTS)
        if not has_node:
            return False
        if any((target_dir / m).is_file() for m in _PYTHON_MANIFESTS):
            return False
        # requirements*.txt is a glob, not a fixed name.
        if any(target_dir.glob("requirements*.txt")):
            return False
        return True
    except OSError:  # pragma: no cover - defensive; never fail a bootstrap
        return False


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
    * the target is not a POSITIVELY non-Python project — a node manifest
      with no Python manifest anywhere (TS-lane D.1c; a pytest-bdd bridge in
      a TypeScript repo is a Python file the Player never wrote), AND
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

        if _is_non_python_worktree(target_dir):
            # LOUD ABSENCE, not a silent skip: the operator must be able to
            # tell "the tool decided not to" from "the tool is broken".
            logger.info(
                "Skipping the features/conftest.py pytest-bdd bridge at %s: "
                "this is a non-Python project (a node manifest is present and "
                "no Python manifest is). The bridge is pytest-only, so writing "
                "it here would leave a Python file the project never asked "
                "for. TS-lane D.1c.",
                target_dir,
            )
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
