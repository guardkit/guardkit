"""ONE RULE for the key and the address every OpenAI-compatible seat client uses.

Three clients in this repo talk to an OpenAI-compatible endpoint — the stamp
normalizer's model fallback (``guardkit/orchestrator/stamp_model_fallback.py``),
the QAV shadow (``guardkit/qa/qav_shadow.py``) and the code-review seat
(``guardkit/qa/review_seat.py``). Each used to send the literal placeholder key
``not-needed``, and two of them had the address ``http://localhost:9000/v1``
written into the code. That was fine while every call went straight to
llama-swap, which ignores the key. Since 2026-09-03 the factory's calls go
through LiteLLM instead, which checks the key and answers a real 401 — a
placeholder key stopped a planning run on 2026-09-04. This module is the one
place that decides what key is sent and which address is called, so the three
clients cannot drift apart again.

**The key.** ``OPENAI_API_KEY`` when it is set and not blank; otherwise the
client's own existing placeholder. A machine without the variable therefore
behaves exactly as it did before. The value is returned and used — it is never
logged, printed, or put in an error message.

**The address, in order of precedence.** An explicit setting for that one
client wins (the QAV shadow's ``endpoint`` in its config block, the base URL a
caller hands the review seat); then that client's own environment variable
(``GUARDKIT_STAMP_MODEL_URL``, ``GUARDKIT_QAV_SHADOW_URL``,
``GUARDKIT_REVIEW_SEAT_URL``); then the shared ``OPENAI_BASE_URL``; then the
client's built-in default, which for the QAV shadow and the review seat is
``http://localhost:9000/v1`` and for the stamp fallback is deliberately
nothing at all (no endpoint configured means the model is never asked).
"""

from __future__ import annotations

import os
import re
from typing import Mapping, Optional, Sequence

__all__ = [
    "API_KEY_ENV",
    "BASE_URL_ENV",
    "PLACEHOLDER_API_KEY",
    "DEFAULT_BASE_URL",
    "FEATURE_ROUTING_HEADER",
    "FEATURE_ROUTING_ID_ENV",
    "FEATURE_ROUTING_REQUIRED_ENV",
    "FeatureRoutingError",
    "resolve_api_key",
    "resolve_base_url",
    "resolve_feature_routing_headers",
]

#: The shared key variable every OpenAI-compatible client reads.
API_KEY_ENV = "OPENAI_API_KEY"

#: The shared address variable, consulted after a client's own variable.
BASE_URL_ENV = "OPENAI_BASE_URL"

#: What the three clients sent before this module existed. Kept as the fallback
#: so a box without ``OPENAI_API_KEY`` behaves byte-for-byte as it did.
PLACEHOLDER_API_KEY = "not-needed"

#: The estate's llama-swap address — the last resort for the two clients that
#: had it written into the code.
DEFAULT_BASE_URL = "http://localhost:9000/v1"

#: Per-child feature-routing contract.  These values are deliberately local to
#: GuardKit: sharing a helper with the build harness would introduce a package
#: dependency at the HTTP boundary.
FEATURE_ROUTING_ID_ENV = "GUARDKIT_FEATURE_ROUTING_ID"
FEATURE_ROUTING_REQUIRED_ENV = "GUARDKIT_FEATURE_ROUTING_REQUIRED"
FEATURE_ROUTING_HEADER = "x-feature-id"
_FEATURE_ROUTING_ID_RE = re.compile(r"[A-Za-z0-9_-]{1,256}\Z")


class FeatureRoutingError(ValueError):
    """The per-child routing contract cannot produce a safe HTTP header."""


def resolve_feature_routing_headers(
    headers: Optional[Mapping[str, str]] = None,
    *,
    environ: Optional[Mapping[str, str]] = None,
) -> dict[str, str]:
    """Return a copied header mapping with the validated feature route.

    The routing ID is an exact wire value: it is never stripped, truncated or
    coerced.  Header names are compared case-insensitively.  A caller may
    already carry the same single routing header, but a different value,
    duplicate case variant, or reserved header without the child environment
    is refused instead of overwritten.  ``headers`` and ``environ`` are never
    mutated.
    """
    source: Mapping[str, str] = os.environ if environ is None else environ
    result = dict(headers or {})

    required_raw = source.get(FEATURE_ROUTING_REQUIRED_ENV)
    if required_raw not in (None, "0", "1"):
        raise FeatureRoutingError(
            f"{FEATURE_ROUTING_REQUIRED_ENV} must be exactly '0' or '1'"
        )
    required = required_raw == "1"

    routing_id = source.get(FEATURE_ROUTING_ID_ENV)
    if routing_id is not None and (
        not isinstance(routing_id, str) or _FEATURE_ROUTING_ID_RE.fullmatch(routing_id) is None
    ):
        raise FeatureRoutingError(
            f"{FEATURE_ROUTING_ID_ENV} must match ASCII [A-Za-z0-9_-]{{1,256}}"
        )
    if routing_id is None and required:
        raise FeatureRoutingError(
            f"{FEATURE_ROUTING_ID_ENV} is required when {FEATURE_ROUTING_REQUIRED_ENV}=1"
        )

    reserved = [name for name in result if name.lower() == FEATURE_ROUTING_HEADER]
    if len(reserved) > 1:
        raise FeatureRoutingError(f"duplicate {FEATURE_ROUTING_HEADER} headers are not allowed")
    if reserved:
        name = reserved[0]
        if routing_id is None or result[name] != routing_id:
            raise FeatureRoutingError(
                f"caller-supplied {FEATURE_ROUTING_HEADER} conflicts with child routing"
            )
    elif routing_id is not None:
        result[FEATURE_ROUTING_HEADER] = routing_id
    return result


def resolve_api_key(placeholder: str = PLACEHOLDER_API_KEY) -> str:
    """The key to send: ``OPENAI_API_KEY`` when set and not blank, else the
    caller's placeholder.

    Never log, print, or interpolate the result into a message: the whole point
    of returning it here is that it goes straight into the request and nowhere
    else.
    """
    value = os.environ.get(API_KEY_ENV)
    if value is not None and value.strip():
        return value.strip()
    return placeholder


def resolve_base_url(
    *,
    explicit: Optional[str] = None,
    env_vars: Sequence[str] = (),
    default: Optional[str] = DEFAULT_BASE_URL,
    empty_env_disables: bool = False,
) -> str:
    """The address to call, by the precedence this module's docstring names.

    ``explicit`` is the per-client setting (a config value, a caller's
    argument); a blank or missing one is ignored. ``env_vars`` are the
    environment variable names to try in order — a client's own name first,
    then ``OPENAI_BASE_URL``. ``default`` is the built-in last resort; pass
    ``None`` for a client that must treat "nothing configured" as "do not call
    the model at all", and the answer is then the empty string.

    ``empty_env_disables`` is for the stamp fallback alone, whose oldest rule is
    that the FIRST of its variables that is *present* decides even when its
    value is empty — an empty value there means "deliberately switched off", and
    it never falls through to the next name. Everywhere else a blank value is
    simply skipped.
    """
    if explicit is not None and explicit.strip():
        return explicit.strip()
    for name in env_vars:
        raw = os.environ.get(name)
        if raw is None:
            continue
        if raw.strip():
            return raw.strip()
        if empty_env_disables:
            return ""
    return default or ""
