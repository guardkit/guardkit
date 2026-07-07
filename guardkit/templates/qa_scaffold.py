"""Install the ``qa/`` tier-1 format stubs into a ``guardkit init`` target.

Sibling of :mod:`guardkit.templates.conftest_bridge` — same pattern: the
canonical stubs live under ``installer/core/templates/common/qa/`` and are
copied per-file into ``<project>/qa/`` when absent (never clobbering existing
instances — a repo's committed qa/ data always wins).

The stubs validate as-is (``guardkit qa validate`` passes on a freshly
scaffolded repo) but carry placeholder content; enforcement
(``qa.enforce_tier1``, session B2) stays off until the repo replaces the
placeholders (flipped per-repo at WS2 V1/V2).
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import List

from guardkit.templates.resolver import _get_templates_base_dir

logger = logging.getLogger(__name__)

# Canonical stub dir, relative to the templates base dir.
_QA_TEMPLATE_RELPATH = ("common", "qa")


def install_qa_scaffold(project_dir: Path) -> List[str]:
    """Copy the ``qa/`` stubs into ``project_dir`` where absent.

    Non-raising: any problem is logged and skipped so ``guardkit init`` never
    fails on the scaffold step.

    Returns:
        Relative paths (under ``qa/``) of files actually copied.
    """
    copied: List[str] = []
    try:
        src_root = Path(_get_templates_base_dir()).joinpath(*_QA_TEMPLATE_RELPATH)
        if not src_root.is_dir():
            logger.info("No common/qa template dir found; skipping qa scaffold")
            return copied

        target_root = project_dir / "qa"
        for src in sorted(src_root.rglob("*")):
            if not src.is_file():
                continue
            rel = src.relative_to(src_root)
            dest = target_root / rel
            if dest.exists():
                logger.info(f"qa scaffold: {rel} already exists, skipping")
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
            copied.append(str(rel))
            logger.info(f"qa scaffold: installed qa/{rel}")
    except Exception as exc:  # pragma: no cover - defensive, never block init
        logger.warning(f"qa scaffold install failed (non-fatal): {exc}")
    return copied
