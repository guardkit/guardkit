"""The per-repo ``spec_track`` switch.

Historically this selected between the default ``gherkin`` spec track and the
optional ``dcl`` track. The DCL lane was deleted outright (card Q11, ruled
08-15); ``gherkin`` is now the only track. :func:`get_spec_track` is kept for
call-site compatibility and still follows the
:func:`guardkit.qa.enforcement.is_tier1_enforced` idiom:

    precedence  env ``GUARDKIT_SPEC_TRACK`` > ``.guardkit/config.yaml``
                ``qa.spec_track`` > default ``"gherkin"``.

Unlike the boolean enforcement flag, an *unrecognised* value is a hard, loud
error rather than a silent OFF: a typo (``gherkins``) — or a leftover ``dcl``
opt-in for the deleted track — must never be silently read as ``gherkin``.
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

#: The only legal track value.
ALLOWED_SPEC_TRACKS = frozenset({"gherkin"})

#: The default (and only) track.
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
        f"allowed values are exactly {{{allowed}}}. An unrecognised value must "
        "never silently mean gherkin; fix the value or remove it to use the "
        "default."
    )
    if value not in ALLOWED_SPEC_TRACKS:
        raise ValueError(raise_msg)
    return value


def get_spec_track(repo_root: Path) -> str:
    """Return the spec track for ``repo_root`` (always ``"gherkin"`` when legal).

    Precedence: ``GUARDKIT_SPEC_TRACK`` env var > ``.guardkit/config.yaml``
    ``qa.spec_track`` > default ``"gherkin"``.

    Kept for call-site compatibility after the DCL track's deletion (card Q11):
    the switch still reads and validates, but ``"gherkin"`` is the only legal
    value.

    Raises:
        ValueError: the env var or config value is set to anything other than
        ``"gherkin"`` (an unrecognised value — including a leftover ``"dcl"``
        opt-in — is loud, never a silent gherkin).
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
