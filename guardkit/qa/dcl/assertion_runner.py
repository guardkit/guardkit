"""Generic executor of a derived assertion set -> the F4 gate envelope (D2, §2).

ONE stdlib-HTTP executor for ANY derived set (``qa/dcl/derived/<FEATURE>.yaml``),
faithful to the spike runner's semantics
(``api_test/qa/dcl-spike/run_derived_assertions.py``): sample the invocation
surface twice (for the monotone / stability / latency checks), evaluate every
RUN assertion's predicate, and emit the **F4 gate envelope**
``{"assertions": [{id, status, observed, expected, evidence_ref}]}`` on stdout —
exit 0 when every assertion passed, 1 when any failed. It plugs straight into the
live-gate executor (``SubprocessGateScriptRunner`` / ``parse_gate_result``).

The base URL comes from a NAMED environment variable (LPA-02 — never hard-coded).
A missing env var / unreadable set is a loud config fault (exit 2). A service
that cannot be reached fails every dependent assertion LOUD (never green, never
silent-skip).
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

_HTTP_TIMEOUT_S = 10
_LATENCY_BOUND_DEFAULT = 5.0


class RunnerError(RuntimeError):
    """The assertion set / base URL could not be resolved (config fault, exit 2)."""


@dataclass
class _Sample:
    """Two successive observations of the invocation surface."""

    status1: int
    body1: Dict[str, Any]
    dt1: float
    status2: int
    body2: Dict[str, Any]


def load_assertion_set(path: Path) -> Dict[str, Any]:
    p = Path(path)
    if not p.is_file():
        raise RunnerError(f"assertion set not found: {p}")
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "assertions" not in data:
        raise RunnerError(f"{p}: not a derived assertion set (no 'assertions' key)")
    return data


def resolve_base_url(base_url_env: str) -> str:
    if not base_url_env:
        raise RunnerError("a base-url env var NAME is required (never a hard-coded URL)")
    value = os.environ.get(base_url_env)
    if not value:
        raise RunnerError(
            f"env var {base_url_env!r} is unset — the base URL must come from the "
            "environment (LPA-02). Set it and retry."
        )
    return value.rstrip("/")


def _request(base_url: str, method: str, path: str, body: Optional[str]) -> Tuple[int, str, float]:
    url = base_url + path
    data = body.encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method.upper())
    if data is not None:
        req.add_header("Content-Type", "application/json")
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=_HTTP_TIMEOUT_S) as resp:
            payload = resp.read().decode("utf-8")
            status = resp.status
    except urllib.error.HTTPError as exc:  # 4xx/5xx are real observations, not faults
        payload = exc.read().decode("utf-8", "replace") if exc.fp else ""
        status = exc.code
    dt = time.monotonic() - t0
    return status, payload, dt


def _sample(base_url: str, method: str, path: str) -> _Sample:
    status1, raw1, dt1 = _request(base_url, method, path, None)
    status2, raw2, _ = _request(base_url, method, path, None)
    try:
        body1 = json.loads(raw1) if raw1 else {}
        body2 = json.loads(raw2) if raw2 else {}
    except json.JSONDecodeError as exc:
        raise ConnectionError(f"response was not JSON: {exc}") from exc
    return _Sample(status1, body1, dt1, status2, body2)


def _is_iso8601_utc(s: Any) -> bool:
    if not isinstance(s, str):
        return False
    v = s.replace("Z", "+00:00") if s.endswith("Z") else s
    try:
        d = datetime.fromisoformat(v)
    except ValueError:
        return False
    off = d.utcoffset()
    return off is not None and off.total_seconds() == 0


def _numeric(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


_MISSING = object()


def _eval_read(pred: Dict[str, Any], sample: _Sample) -> Tuple[bool, str, str]:
    """Evaluate a predicate that reads the sampled invocation surface."""
    check = pred.get("check")
    if check == "status_equals":
        expected = pred["expected"]
        return sample.status1 == expected, str(sample.status1), str(expected)
    if check == "field_present_typed":
        key = pred["wire_key"]
        val = sample.body1.get(key, _MISSING)
        present = val is not _MISSING
        if not present:
            return False, "<missing>", f"{key} present"
        if pred.get("nullable"):  # J6: presence only, value may be null
            return True, repr(val), f"{key} present (nullable)"
        dcl_type = pred.get("dcl_type", "Text")
        if dcl_type == "Text":
            ok = isinstance(val, str) and len(val) > 0
            return ok, repr(val), "non-empty Text"
        if dcl_type == "Number":
            return _numeric(val), repr(val), "Number"
        if dcl_type == "Flag":
            return isinstance(val, bool), repr(val), "Flag"
        return val is not None, repr(val), "present"
    if check == "non_decreasing":
        key = pred["wire_key"]
        v1, v2 = sample.body1.get(key), sample.body2.get(key)
        ok = _numeric(v1) and _numeric(v2) and v2 >= v1
        return ok, f"{v1} -> {v2}", "non-decreasing"
    if check == "latency_below":
        bound = pred.get("bound_seconds", _LATENCY_BOUND_DEFAULT)
        return sample.dt1 < bound, f"{sample.dt1 * 1000:.1f} ms", f"< {bound * 1000:.0f} ms"
    if check == "field_non_null":
        key = pred["wire_key"]
        val = sample.body1.get(key)
        return val is not None, repr(val), f"{key} non-null"
    if check == "field_stable":
        key = pred["wire_key"]
        v1, v2 = sample.body1.get(key), sample.body2.get(key)
        return (v1 == v2 and v1 is not None), f"{v1!r} == {v2!r}", "stable, non-null"
    if check == "format":
        key = pred["wire_key"]
        val = sample.body1.get(key)
        fmt = pred.get("format")
        if fmt == "iso8601_utc":
            return _is_iso8601_utc(val), repr(val), "UTC ISO-8601"
        raise RunnerError(f"unknown format check {fmt!r}")
    raise RunnerError(f"unknown read predicate {check!r}")


def _eval_request(pred: Dict[str, Any], status: int) -> Tuple[bool, str, str]:
    """Evaluate a predicate over a status from the assertion's own request."""
    check = pred.get("check")
    if check == "status_in_range":
        low, high = pred["low"], pred["high"]
        return low <= status < high + 1, str(status), f"{low}-{high}"
    if check == "status_equals":
        return status == pred["expected"], str(status), str(pred["expected"])
    raise RunnerError(f"unknown request predicate {check!r}")


def run(assertion_set: Dict[str, Any], base_url: str) -> Tuple[Dict[str, Any], int]:
    """Execute the RUN assertions against ``base_url`` -> (F4 envelope, exit code)."""
    invocation = assertion_set.get("invocation") or {}
    inv_method = invocation.get("method", "GET")
    inv_path = invocation.get("path", "/")
    run_assertions = [
        a for a in assertion_set.get("assertions", []) if a.get("disposition") == "RUN"
    ]

    needs_sample = any(a.get("request") is None for a in run_assertions)
    sample: Optional[_Sample] = None
    sample_error: Optional[str] = None
    if needs_sample:
        try:
            sample = _sample(base_url, inv_method, inv_path)
        except (urllib.error.URLError, ConnectionError, OSError) as exc:
            sample_error = f"could not reach {base_url}{inv_path}: {exc}"

    results: List[Dict[str, Any]] = []
    for a in run_assertions:
        aid = a["id"]
        pred = a.get("predicate", {})
        request = a.get("request")
        try:
            if request is not None:
                status, _, _ = _request(
                    base_url,
                    request.get("method", inv_method),
                    request.get("path", inv_path),
                    request.get("body"),
                )
                ok, observed, expected = _eval_request(pred, status)
            elif sample is None:  # the surface was unreachable — fail LOUD
                ok, observed, expected = False, sample_error or "unreachable", "reachable"
            else:
                ok, observed, expected = _eval_read(pred, sample)
        except (urllib.error.URLError, ConnectionError, OSError) as exc:
            ok, observed, expected = False, f"request failed: {exc}", "reachable"
        results.append(
            {
                "id": aid,
                "status": "pass" if ok else "fail",
                "observed": observed,
                "expected": expected,
                "evidence_ref": f"{a.get('rule')} <- {a.get('dcl_source')}",
            }
        )

    envelope = {"assertions": results}
    exit_code = 0 if all(r["status"] == "pass" for r in results) else 1
    return envelope, exit_code


def run_file(assertion_set_path: Path, base_url_env: str) -> Tuple[Dict[str, Any], int]:
    """Load a derived set, resolve the base URL from ``base_url_env``, execute it."""
    aset = load_assertion_set(assertion_set_path)
    base_url = resolve_base_url(base_url_env)
    return run(aset, base_url)
