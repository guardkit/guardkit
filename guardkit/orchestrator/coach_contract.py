"""Single source of truth for coach-contract resolution (TASK-CMIR-003 AC-1,
completed by coordinator fix-and-re-verify 2026-07-26).

Precedence: ``GUARDKIT_COACH_CONTRACT`` env > ``.guardkit/config.yaml``
``autobuild.coach.contract`` > default ``"coachsplit"`` — mirroring the
``_get_coach_test_model`` precedence convention.

Both prior resolvers (``agent_invoker._resolve_coach_contract`` and
``coach_output_parser._resolve_contract``) delegate here; no duplicated env
reads. Config discovery is cwd-relative by default because ``guardkit
autobuild`` always runs from the target repo root (the standing invocation
convention); callers that know the root pass it explicitly.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

COACH_CONTRACT_ENV = "GUARDKIT_COACH_CONTRACT"
COACH_CONTRACT_DEFAULT = "coachsplit"
_VALID = ("coachsplit", "v4")


def _config_contract(repo_root: Path) -> str | None:
    """Read ``autobuild.coach.contract`` from the repo config, tolerantly."""
    config_path = repo_root / ".guardkit" / "config.yaml"
    if not config_path.exists():
        return None
    try:
        import yaml

        data = yaml.safe_load(config_path.read_text())
        if not isinstance(data, dict):
            return None
        coach = data.get("autobuild", {})
        coach = coach.get("coach", {}) if isinstance(coach, dict) else {}
        value = coach.get("contract") if isinstance(coach, dict) else None
        return str(value) if value else None
    except Exception as exc:  # config problems must never break a build
        logger.warning("coach-contract config read failed (%s): %s", config_path, exc)
        return None


def resolve_coach_contract(repo_root: Path | None = None) -> str:
    """Return the active coach contract: env > config > default.

    Unknown values degrade loudly to the default rather than raising —
    a typo in config must never break a build.
    """
    raw = os.environ.get(COACH_CONTRACT_ENV) or _config_contract(
        Path(repo_root) if repo_root else Path.cwd()
    ) or COACH_CONTRACT_DEFAULT
    value = raw.strip().lower()
    if value not in _VALID:
        logger.warning(
            "coach-contract %r is not one of %s — using %r",
            raw, _VALID, COACH_CONTRACT_DEFAULT,
        )
        return COACH_CONTRACT_DEFAULT
    return value
