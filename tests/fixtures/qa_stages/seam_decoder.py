"""Boundary-probe fixture decoders — one leaky, one hardened (WS2 B6, ST-06).

``LEAKY`` reproduces the study-tutor retro's raw escapes: a proxy-style nested
``error`` string throws a raw ``TypeError`` past the sealed ``EnvelopeError``
set, and a missing discriminator throws a raw ``KeyError``. ``HARDENED`` folds
every non-conforming input into ``EnvelopeError`` and rejects garbage, so the
probe reports a clean posture.
"""

from __future__ import annotations

import json
from typing import Any, Tuple, Type


class EnvelopeError(Exception):
    """The seam's sealed error type (the 'closed set' the retro names)."""


_KINDS = {"queued", "started", "complete"}


class _LeakyDecoder:
    sealed_errors: Tuple[Type[BaseException], ...] = (EnvelopeError,)

    def decode(self, raw: Any) -> Any:
        data = json.loads(raw) if isinstance(raw, (bytes, bytearray, str)) else raw
        if not isinstance(data, dict):
            raise EnvelopeError("envelope must be an object")  # sealed → handled
        kind = data["kind"]  # raw KeyError leaks when 'kind' is absent
        if kind not in _KINDS:
            raise EnvelopeError(f"unknown kind: {kind!r}")  # sealed → handled
        # Proxy-style nested error — a raw TypeError if 'error' is a string.
        detail = data["error"]["detail"] if "error" in data else None
        return {"kind": kind, "detail": detail}


class _HardenedDecoder:
    sealed_errors: Tuple[Type[BaseException], ...] = (EnvelopeError,)

    def decode(self, raw: Any) -> Any:
        try:
            data = json.loads(raw) if isinstance(raw, (bytes, bytearray, str)) else raw
        except (ValueError, TypeError) as exc:
            raise EnvelopeError(f"undecodable envelope: {exc}") from exc
        if not isinstance(data, dict):
            raise EnvelopeError("envelope must be an object")
        kind = data.get("kind")
        if kind not in _KINDS:
            raise EnvelopeError(f"unknown or missing kind: {kind!r}")
        err = data.get("error")
        detail = err.get("detail") if isinstance(err, dict) else None
        return {"kind": kind, "detail": detail}


#: Instances (the CLI --target can point at these directly).
LEAKY = _LeakyDecoder()
HARDENED = _HardenedDecoder()
