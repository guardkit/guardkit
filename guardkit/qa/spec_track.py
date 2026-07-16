"""The per-repo ``spec_track`` switch (Phase D, design §1 / D1).

DCL adoption rides an optional *spec track*. A repo declares which track it is
on; ``gherkin`` is the default and — by the Fallback law (design §0.1) — forever
the fallback. On the ``dcl`` track a feature's behaviour spec is a
compiler-checked ``.dcl`` capability whose outside-in verification is *derived*
from that spec (:mod:`guardkit.qa.dcl`); on ``gherkin`` nothing new runs and
guardkit behaves byte-for-byte as it does today.

:func:`get_spec_track` follows the :func:`guardkit.qa.enforcement.is_tier1_enforced`
idiom exactly:

    precedence  env ``GUARDKIT_SPEC_TRACK`` > ``.guardkit/config.yaml``
                ``qa.spec_track`` > default ``"gherkin"``.

Unlike the boolean enforcement flag, an *unrecognised* value is a hard, loud
error rather than a silent OFF: a typo (``gherkins``, ``DCL ``) must never be
read as ``gherkin`` and quietly disable the DCL track a repo asked for.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

import yaml

logger = logging.getLogger(__name__)

__all__ = [
    "SPEC_TRACK_ENV",
    "ALLOWED_SPEC_TRACKS",
    "DEFAULT_SPEC_TRACK",
    "get_spec_track",
]

#: Env override for the spec track. When set it wins over ``.guardkit/config.yaml``.
SPEC_TRACK_ENV = "GUARDKIT_SPEC_TRACK"

#: The only two legal track values.
ALLOWED_SPEC_TRACKS = frozenset({"gherkin", "dcl"})

#: The default + permanent fallback track (design §0.1 Fallback law).
DEFAULT_SPEC_TRACK = "gherkin"


def _load_config(repo_root: Path) -> dict:
    """Read ``<repo_root>/.guardkit/config.yaml``; empty dict if absent/unreadable."""
    path = repo_root / ".guardkit" / "config.yaml"
    if not path.is_file():
        return {}
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (yaml.YAMLError, OSError) as exc:
        logger.warning(
            "qa.spec_track: could not read %s (%s) — treating as default", path, exc
        )
        return {}
    return data if isinstance(data, dict) else {}


def _validate(value: str, *, source: str) -> str:
    """Return ``value`` if it is a legal track, else raise a loud ``ValueError``."""
    allowed = ", ".join(sorted(ALLOWED_SPEC_TRACKS))
    raise_msg = (
        f"{source} spec_track={value!r} is not a recognised track — "
        f"allowed values are exactly {{{allowed}}}. A typo must never silently "
        "mean gherkin; fix the value or remove it to use the default."
    )
    if value not in ALLOWED_SPEC_TRACKS:
        raise ValueError(raise_msg)
    return value


def get_spec_track(repo_root: Path) -> str:
    """Return the spec track for ``repo_root`` (``"gherkin"`` or ``"dcl"``).

    Precedence: ``GUARDKIT_SPEC_TRACK`` env var > ``.guardkit/config.yaml``
    ``qa.spec_track`` > default ``"gherkin"``.

    Default ``"gherkin"`` everywhere (design §0.1 Fallback law): a repo opts into
    the ``dcl`` track as an explicit step; with the switch absent nothing new runs.

    Raises:
        ValueError: the env var or config value is set to anything other than
        ``"gherkin"`` / ``"dcl"`` (a typo is loud, never a silent gherkin).
    """
    env: Optional[str] = os.environ.get(SPEC_TRACK_ENV)
    if env is not None and env.strip():
        return _validate(env.strip().lower(), source=f"{SPEC_TRACK_ENV} env var")

    qa = _load_config(repo_root).get("qa")
    if isinstance(qa, dict) and qa.get("spec_track") is not None:
        raw = qa.get("spec_track")
        token = str(raw).strip().lower()
        return _validate(token, source=".guardkit/config.yaml qa.spec_track")

    return DEFAULT_SPEC_TRACK
