"""DCL machine-authoring — the faithful §10 protocol port (W1-S1).

The seat authors a feature's ``.dcl`` capability under the machine-chain authoring
protocol frozen at fleet-evals ``8a3b9d1`` (``dcl-heldout-suite-scope.md`` §10),
whose working code is ``fleet-evals/harness/run_dcl_heldout.py``. This module ports
that runner's SEMANTICS into guardkit — it does not reinvent them.

The protocol (verbatim, do not improvise a variant):

  1. **Standing compiler-verified vocabulary reference.** The sha-pinned
     ``vocab-reference.md`` (vendored beside this module) is appended verbatim to
     the composed authoring prompt under :data:`VOCAB_DELIM`; ``prompt_sha256``
     covers the FULL composed user turn including it.
  2. **≤ 1 bounded compile→repair pass.** ONE seat call authors the ``.dcl``; the
     vendored checker compiles it; if dirty, EXACTLY ONE second call carries the
     checker's verbatim diagnostics envelope + the first attempt + a terse repair
     instruction. The graded candidate is the FINAL response. The bound is
     STRUCTURAL — a single straight-line ``if not zero_shot_clean:`` block, no loop
     construct — so at most one repair call is physically impossible to exceed.

Laws honoured here (build-handoff §0):

- **Single-slot law (build-lane):** this module makes ZERO live seat calls in any
  test — the seat call and the ``/running`` probe are INJECTABLE edges
  (``seat_call`` / ``running_probe``) defaulting to the real urllib
  implementations; tests inject spies and never touch the network.
- **§10 protocol only:** the pinned strings (system prompt, vocab delimiter, repair
  instruction) and sampling (temperature 0.3 / top_p 0.9 / max_tokens 16384) are
  module constants copied byte-exact from the fleet-evals runner, with provenance
  comments. They are NOT config-overridable.
- **Honest gates:** a wrong path / refusal / dirty-second-attempt / empty-or-
  vacuous final content fails LOUD in its own lane (exit 1 with a receipt, or exit
  2 with nothing written) — never a silent fallback. The gherkin verification
  track is untouched: absence of a ``.dcl`` simply means the derived DCL gate does
  not run, the existing absence discipline carries the feature.

Instrument (exit-2) faults raise :class:`AuthoringInstrumentError` and write
NOTHING. Authoring outcomes (exit 0 success / exit 1 loud authoring failure)
return an :class:`AuthoringResult` and ALWAYS write the ``dcl-authoring`` receipt.

stdlib-only transport (urllib) — no new dependency; the checker is the existing
:mod:`guardkit.qa.dcl.checker` (vendored WASM, node-driven, LLM-free).
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.parse import urlsplit, urlunsplit

import yaml

from guardkit.qa.dcl.checker import (
    BIN_DIR,
    CHECKER_PIN,
    HARNESS,
    CheckerError,
)
from guardkit.qa.dcl.checker import check as run_check

__all__ = [
    "PINNED_SYSTEM_PROMPT",
    "PINNED_SYSTEM_PROMPT_SHA256",
    "VOCAB_DELIM",
    "REPAIR_INSTRUCTION",
    "TEMPERATURE",
    "TOP_P",
    "MAX_TOKENS",
    "TRANSPORT_RETRIES",
    "VOCAB_REF",
    "VOCAB_REF_SHA256",
    "DEFAULT_ENDPOINT",
    "DEFAULT_MODEL",
    "DCL_AUTHOR_ENDPOINT_ENV",
    "DCL_AUTHOR_MODEL_ENV",
    "SeatCall",
    "RunningProbe",
    "AuthoringInstrumentError",
    "AuthoringResult",
    "resolve_endpoint_model",
    "compose_author_prompt",
    "render_criteria",
    "author_dcl",
]

# ---------------------------------------------------------------------------
# Pinned §10 strings (byte-exact from fleet-evals/harness/run_dcl_heldout.py).
# Shas verified in tests/qa/dcl/test_author.py. NOT config-overridable.
# ---------------------------------------------------------------------------

#: The one-line system turn (run_dcl_heldout.py L57).
#: sha256 419e455b26af1d3014e28100f6e6520c1fbdba10d05941adbbd0e2d0163d7316
PINNED_SYSTEM_PROMPT = (
    "Output ONLY the DCL source. No prose, no explanation, no markdown fences."
)
PINNED_SYSTEM_PROMPT_SHA256 = (
    "419e455b26af1d3014e28100f6e6520c1fbdba10d05941adbbd0e2d0163d7316"
)

#: The standing vocabulary reference is appended under this delimiter at the very
#: END of the composed user prompt (run_dcl_heldout.py L69). prompt_sha256 covers it.
VOCAB_DELIM = "\n\n=== DCL v1.0 VERIFIED VOCABULARY REFERENCE ===\n"

#: The terse repair instruction for the ONE bounded second call
#: (run_dcl_heldout.py L79-84, verbatim).
REPAIR_INSTRUCTION = (
    "The DCL compiler REJECTED your previous attempt with the diagnostics above. "
    "Fix exactly those errors while preserving the declared semantics, and return "
    "ONLY the corrected, compile-clean DCL source — the full .dcl file, no prose, "
    "no explanation, no markdown fences."
)

# ---------------------------------------------------------------------------
# Pinned sampling — §10 ran the seat exactly here (run_dcl_heldout.py L384-386).
# Module constants with a provenance comment; NOT config-overridable (the frozen
# protocol pins the seat's decoding).
# ---------------------------------------------------------------------------
TEMPERATURE = 0.3
TOP_P = 0.9
MAX_TOKENS = 16384

#: 2 retries => up to 3 attempts, then ABORT (run_dcl_heldout.py L63). Retry only
#: on connection / 5xx / timeout / JSON-decode — a 4xx is a request defect and a
#: compiling-or-not .dcl is a RESULT (never retry-on-bad-content).
TRANSPORT_RETRIES = 2
SEAT_TIMEOUT_S = 900.0
PROBE_TIMEOUT_S = 15.0

#: The vendored, sha-pinned vocabulary reference (see VOCAB-PROVENANCE.md).
VOCAB_REF: Path = Path(__file__).resolve().parent / "vocab-reference.md"
VOCAB_REF_SHA256 = "25121afe7415b15cba161fa2f3e728dad7095675f214a298317b51bb0e8fee2b"

# ---------------------------------------------------------------------------
# Config (the enforcement.py idiom): endpoint/model from .guardkit/config.yaml
# ``qa.dcl_author: {endpoint, model}``; env overrides win; then the defaults.
# ---------------------------------------------------------------------------
DCL_AUTHOR_ENDPOINT_ENV = "GUARDKIT_DCL_AUTHOR_ENDPOINT"
DCL_AUTHOR_MODEL_ENV = "GUARDKIT_DCL_AUTHOR_MODEL"
DEFAULT_ENDPOINT = "http://127.0.0.1:9000/v1/chat/completions"
DEFAULT_MODEL = "qwen36-workhorse"

#: The composition string recorded on the receipt (audit provenance).
COMPOSITION = (
    "recorded feature Request (verbatim) + machine criteria (rendered: each "
    "criterion's class/evidence_kind/text + the negative paths) + VOCAB_DELIM + "
    "the sha-pinned vocab-reference.md (verbatim, at the end)"
)


# ---------------------------------------------------------------------------
# Injectable edges (so unit tests never touch the network) — the SeatCall /
# RunningProbe type-alias pattern (review_seat.py L209-213), adapted to the §10
# raw-passthrough transport.
# ---------------------------------------------------------------------------

#: A seat call: (endpoint, model, system, user) -> the raw completion JSON dict.
#: The §10 content extraction is a pure passthrough of
#: ``raw["choices"][0]["message"]["content"]`` (no fence stripping).
SeatCall = Callable[[str, str, str, str], Dict[str, Any]]

#: A single-slot probe: (endpoint, model) -> a ``{"url", "ok"}`` receipt on
#: success; it RAISES :class:`AuthoringInstrumentError` on any doubt (the seat
#: could not be proven free+ready), which is a loud exit-2 instrument error.
RunningProbe = Callable[[str, str], Dict[str, Any]]


class AuthoringInstrumentError(Exception):
    """A loud exit-2 instrument/usage fault: node/checker missing, config invalid,
    inputs missing, seat unreachable, or the single-slot probe could not prove the
    seat free+ready. NOTHING is written when this is raised."""


class _TransportAborted(RuntimeError):
    def __init__(self, attempts: int, last: str) -> None:
        super().__init__(f"transport aborted after {attempts} attempt(s): {last}")
        self.attempts = attempts
        self.last = last


# ===========================================================================
# 1. Config resolution (env > config > default).
# ===========================================================================


def _load_config(repo_root: Path) -> dict:
    """Read ``<repo_root>/.guardkit/config.yaml``; empty dict if absent/unreadable
    (the enforcement.py idiom)."""
    path = repo_root / ".guardkit" / "config.yaml"
    if not path.is_file():
        return {}
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (yaml.YAMLError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def resolve_endpoint_model(repo_root: Path) -> Tuple[str, str]:
    """Resolve (endpoint, model) with precedence env > config > default.

    Env: ``GUARDKIT_DCL_AUTHOR_ENDPOINT`` / ``GUARDKIT_DCL_AUTHOR_MODEL``.
    Config: ``.guardkit/config.yaml`` ``qa.dcl_author: {endpoint, model}``.
    Default: :data:`DEFAULT_ENDPOINT` / :data:`DEFAULT_MODEL`.
    """
    cfg = _load_config(repo_root)
    qa = cfg.get("qa") if isinstance(cfg.get("qa"), dict) else {}
    author_cfg = qa.get("dcl_author") if isinstance(qa.get("dcl_author"), dict) else {}

    endpoint = os.environ.get(DCL_AUTHOR_ENDPOINT_ENV)
    if not endpoint:
        endpoint = author_cfg.get("endpoint") if isinstance(author_cfg.get("endpoint"), str) else None
    if not endpoint:
        endpoint = DEFAULT_ENDPOINT

    model = os.environ.get(DCL_AUTHOR_MODEL_ENV)
    if not model:
        model = author_cfg.get("model") if isinstance(author_cfg.get("model"), str) else None
    if not model:
        model = DEFAULT_MODEL

    return endpoint, model


# ===========================================================================
# 2. Prompt composition (deterministic; nothing sourced from pinned templates).
# ===========================================================================


def render_criteria(criteria_data: dict) -> str:
    """Render the machine criteria YAML into a readable authoring prompt block.

    Each criterion's ``class``/``evidence_kind``/``text`` + the negative paths.
    Tolerant of a pass-bar or a pass-bar-seed shape (unknown keys ignored) — this
    is prompt material, not a schema validation. NOTHING here is sourced from the
    pinned 007/008 templates; it renders the feature's own recorded criteria.
    """
    lines: List[str] = ["## Acceptance criteria (the behaviour the capability must satisfy)"]
    criteria = criteria_data.get("criteria")
    if isinstance(criteria, list) and criteria:
        for c in criteria:
            if not isinstance(c, dict):
                continue
            cid = str(c.get("id", "?"))
            text = str(c.get("text", "")).strip()
            evidence = str(c.get("evidence_kind", "")).strip()
            cls = str(c.get("class", c.get("criterion_class", ""))).strip()
            tag = "/".join(t for t in (cls, evidence) if t)
            prefix = f"- [{cid}]" + (f" ({tag})" if tag else "")
            lines.append(f"{prefix} {text}".rstrip())
    else:
        lines.append("- (no machine criteria recorded)")

    negative = criteria_data.get("negative_paths")
    if isinstance(negative, list) and negative:
        lines.append("")
        lines.append("## Negative paths (must be handled)")
        for n in negative:
            lines.append(f"- {n}")
    return "\n".join(lines)


def compose_author_prompt(
    request_text: str, criteria_data: dict, vocab_text: str
) -> Tuple[str, str, str]:
    """Return (system, user, prompt_sha256) for the authoring turn.

    The user turn = a fixed authoring preamble + the feature Request (verbatim) +
    the rendered machine criteria, then :data:`VOCAB_DELIM` + the vocab bytes
    appended verbatim at the END. ``prompt_sha256`` covers the FULL composed user
    turn (including the vocab) — the §10 rule. Deterministic: same inputs =>
    same bytes => same sha.
    """
    body = "\n".join(
        [
            "# Author a DCL v1.0 capability",
            "",
            "You are authoring a DCL v1.0 capability file for the feature described "
            "below. Use ONLY the verified vocabulary reference at the end of this "
            "message — every literal you emit must be a member of a closed set there. "
            "Output the full .dcl source and nothing else.",
            "",
            "## Feature request",
            "",
            request_text.rstrip("\n"),
            "",
            render_criteria(criteria_data),
        ]
    )
    user = body.rstrip("\n") + "\n"
    user = user + VOCAB_DELIM + vocab_text
    prompt_sha256 = hashlib.sha256(user.encode("utf-8")).hexdigest()
    return PINNED_SYSTEM_PROMPT, user, prompt_sha256


# ===========================================================================
# 3. Single-slot probe (repo law — before EVERY seat call).
# ===========================================================================


def _probe_base(endpoint: str) -> str:
    parts = urlsplit(endpoint)
    return urlunsplit((parts.scheme, parts.netloc, "", "", ""))


def _slot_entries(payload: Any) -> List[dict]:
    if isinstance(payload, dict):
        for key in ("running", "models", "data"):
            if isinstance(payload.get(key), list):
                return [e for e in payload[key] if isinstance(e, dict)]
        return [{"model": k, "state": v} for k, v in payload.items() if isinstance(v, str)]
    if isinstance(payload, list):
        return [e for e in payload if isinstance(e, dict)]
    return []


def slot_ready(payload: Any, alias: str) -> bool:
    for e in _slot_entries(payload):
        name = e.get("model") or e.get("alias") or e.get("id") or e.get("name")
        state = e.get("state") or e.get("status")
        if name == alias and isinstance(state, str) and state == "ready":
            return True
    return False


def _default_running_probe(endpoint: str, model: str) -> Dict[str, Any]:
    """Refuse loudly (exit 2) unless ``<base>/running`` shows ``model`` ``ready``."""
    url = _probe_base(endpoint) + "/running"
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=PROBE_TIMEOUT_S) as resp:  # noqa: S310
            raw = resp.read().decode("utf-8")
    except (urllib.error.URLError, OSError, TimeoutError) as exc:
        raise AuthoringInstrumentError(
            f"single-slot probe GET {url} failed ({exc!r}) — cannot prove the seat "
            f"is free and ready; refusing to author."
        )
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        raise AuthoringInstrumentError(
            f"single-slot probe {url} returned non-JSON:\n{raw}"
        )
    if not slot_ready(payload, model):
        raise AuthoringInstrumentError(
            f"single-slot probe {url} does not show alias {model!r} in state "
            f"'ready' (got: {raw})."
        )
    return {"url": url, "ok": True}


# ===========================================================================
# 4. Transport (stdlib urllib, OpenAI chat-completions shape).
# ===========================================================================


def _default_seat_call(
    endpoint: str, model: str, system: str, user: str
) -> Dict[str, Any]:
    body = json.dumps(
        {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": TEMPERATURE,
            "top_p": TOP_P,
            "max_tokens": MAX_TOKENS,
            "stream": False,
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        endpoint, data=body, headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(req, timeout=SEAT_TIMEOUT_S) as resp:  # noqa: S310
        return json.loads(resp.read().decode("utf-8"))


def _with_transport_retries(fn: Callable[[], Any], retries: int = TRANSPORT_RETRIES) -> Any:
    """Retry on connection / 5xx / timeout / JSON-decode only. A 4xx is re-raised
    immediately (request defect). Raises :class:`_TransportAborted` after the
    retry budget. NO retry-on-bad-content — a compiling-or-not .dcl is a RESULT."""
    attempts = 0
    last = ""
    while attempts <= retries:
        attempts += 1
        try:
            return fn()
        except urllib.error.HTTPError as exc:
            if exc.code < 500:
                raise
            last = f"HTTP {exc.code}"
        except (urllib.error.URLError, OSError, TimeoutError, json.JSONDecodeError) as exc:
            last = repr(exc)
        if attempts <= retries:
            time.sleep(min(2 ** (attempts - 1), 5))
    raise _TransportAborted(attempts, last)


def _content_of(raw: Dict[str, Any]) -> str:
    """§10 passthrough: raw["choices"][0]["message"]["content"] or "" — no fence
    stripping, no cleanup."""
    try:
        return raw["choices"][0]["message"]["content"] or ""
    except (KeyError, IndexError, TypeError):
        return ""


def _finish_of(raw: Dict[str, Any]) -> Optional[str]:
    try:
        return raw["choices"][0].get("finish_reason")
    except (KeyError, IndexError, TypeError):
        return None


# ===========================================================================
# 5. Compile (the vendored checker — the firing decision, not a grade).
# ===========================================================================


def _require_checker() -> None:
    import shutil

    if shutil.which("node") is None:
        raise AuthoringInstrumentError(
            f"node is required to run the vendored DCL checker ({HARNESS}) — a "
            f"missing runtime is an instrument fault, never a clean compile."
        )
    if not HARNESS.is_file() or not (BIN_DIR / "dcl.wasm").is_file():
        raise AuthoringInstrumentError(f"vendored DCL checker not found at {HARNESS}")


def _compile_content(content: str) -> Dict[str, Any]:
    """Compile ``content`` via the vendored checker in an isolated temp dir (never
    pollutes the repo). A checker instrument fault is a loud exit-2 error — never
    silently read as dirty (that would fabricate a repair trigger)."""
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "attempt.dcl"
        p.write_text(content, encoding="utf-8")
        try:
            return run_check(p)
        except CheckerError as exc:
            raise AuthoringInstrumentError(f"DCL checker fault: {exc}") from exc


def _envelope_clean(envelope: Dict[str, Any]) -> bool:
    """The §10 clean predicate (G1): ok truthy AND errorCount == 0."""
    return bool(envelope.get("ok")) and envelope.get("errorCount", 1) == 0


def _envelope_summary(envelope: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "ok": bool(envelope.get("ok")),
        "error_count": int(envelope.get("errorCount", 0) or 0),
        "warning_count": int(envelope.get("warningCount", 0) or 0),
        "error_codes": [
            d.get("code")
            for d in envelope.get("diagnostics", [])
            if isinstance(d, dict) and d.get("severity") == "error" and d.get("code")
        ],
    }


# ===========================================================================
# 6. Artifact shaping (the // @task: marker + the empty-content guard).
# ===========================================================================

_CAPABILITY_DECL = re.compile(r"(?m)^\s*(?:private\s+)?capability\b")
_LANGUAGE_HEADER = re.compile(r"^\s*language\s+dcl\b")


def _has_capability_decl(content: str) -> bool:
    return bool(_CAPABILITY_DECL.search(content))


def _insert_task_marker(content: str, task: str) -> str:
    """Insert ``// @task:<TASK-ID>`` after the ``language dcl 1.0`` header if the
    model did not already include the marker; else prepend it near the top."""
    marker = f"// @task:{task}"
    if marker in content:
        return content
    lines = content.split("\n")
    for i, ln in enumerate(lines):
        if _LANGUAGE_HEADER.match(ln):
            lines.insert(i + 1, marker)
            return "\n".join(lines)
    return marker + "\n" + content


# ===========================================================================
# 7. The result + the entrypoint.
# ===========================================================================


@dataclass(frozen=True)
class AuthoringResult:
    """The outcome of an authoring attempt (exit 0 success / exit 1 loud failure).

    Exit-2 instrument faults raise :class:`AuthoringInstrumentError` instead (and
    write nothing) — they never produce an :class:`AuthoringResult`.
    """

    authored: bool
    attempts: int
    zero_shot_clean: bool
    repaired_clean: Optional[bool]
    artifact: Optional[str]  # repo-relative posix path, or None
    receipt: Optional[str]  # repo-relative posix path (always written here)
    failure_reason: Optional[str]
    exit_code: int
    single_slot_probes: Tuple[Dict[str, Any], ...] = field(default_factory=tuple)

    def envelope(self) -> Dict[str, Any]:
        """The ``--json`` machine envelope (the CLI contract shape)."""
        return {
            "authored": self.authored,
            "attempts": self.attempts,
            "zero_shot_clean": self.zero_shot_clean,
            "repaired_clean": self.repaired_clean,
            "artifact": self.artifact,
            "receipt": self.receipt,
            "failure_reason": self.failure_reason,
        }


def author_dcl(
    *,
    feature: str,
    task: str,
    repo_root: Path,
    request_path: Path,
    criteria_path: Path,
    capability: Optional[str] = None,
    endpoint: Optional[str] = None,
    model: Optional[str] = None,
    seat_call: Optional[SeatCall] = None,
    running_probe: Optional[RunningProbe] = None,
) -> AuthoringResult:
    """Author ``features/<feature>/<feature>.dcl`` under the §10 protocol.

    Returns an :class:`AuthoringResult` (exit 0 authored / exit 1 loud authoring
    failure — BOTH write the ``dcl-authoring`` receipt). Raises
    :class:`AuthoringInstrumentError` (exit 2) on any instrument/usage fault,
    writing NOTHING.

    ``seat_call`` / ``running_probe`` default to the real urllib implementations;
    tests inject spies so no test ever touches the network.
    """
    repo = Path(repo_root)
    if endpoint is None or model is None:
        cfg_endpoint, cfg_model = resolve_endpoint_model(repo)
        endpoint = endpoint or cfg_endpoint
        model = model or cfg_model

    call: SeatCall = seat_call or _default_seat_call
    probe: RunningProbe = running_probe or _default_running_probe

    # --- inputs (exit 2 if missing/unreadable) ---
    if not request_path.is_file():
        raise AuthoringInstrumentError(f"feature Request not found: {request_path}")
    if not criteria_path.is_file():
        raise AuthoringInstrumentError(f"machine criteria not found: {criteria_path}")
    try:
        request_text = request_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise AuthoringInstrumentError(f"cannot read Request {request_path}: {exc}")
    try:
        raw_criteria = yaml.safe_load(criteria_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise AuthoringInstrumentError(
            f"machine criteria {criteria_path} is not readable YAML: {exc}"
        )
    if not isinstance(raw_criteria, dict):
        raise AuthoringInstrumentError(
            f"machine criteria {criteria_path} must be a YAML mapping, got "
            f"{type(raw_criteria).__name__}"
        )

    # --- vocab (exit 2 if missing) ---
    if not VOCAB_REF.is_file():
        raise AuthoringInstrumentError(f"vendored vocab reference not found: {VOCAB_REF}")
    vocab_text = VOCAB_REF.read_text(encoding="utf-8")

    # --- checker present up front (loud, before any seat call) ---
    _require_checker()

    system, user, prompt_sha256 = compose_author_prompt(request_text, raw_criteria, vocab_text)

    probes: List[Dict[str, Any]] = []

    # --- attempt 1 (single-slot probe, then the seat call) ---
    probes.append(probe(endpoint, model))
    t0 = time.time()
    try:
        raw1 = _with_transport_retries(lambda: call(endpoint, model, system, user))
    except _TransportAborted as abort:
        raise AuthoringInstrumentError(f"seat unreachable — {abort}") from abort
    except urllib.error.HTTPError as exc:  # a 4xx is re-raised immediately (request defect)
        raise AuthoringInstrumentError(
            f"seat rejected the authoring request (HTTP {exc.code}) — {exc}"
        ) from exc
    wall_time_s = round(time.time() - t0, 2)

    content = _content_of(raw1)
    finish1 = _finish_of(raw1)
    envelope1 = _compile_content(content)
    zero_shot_clean = _envelope_clean(envelope1)

    final_content = content
    envelope2: Optional[Dict[str, Any]] = None
    finish2: Optional[str] = None
    repaired_clean: Optional[bool] = None
    repair_wall_time_s: Optional[float] = None
    attempts = 1

    # THE BOUND IS STRUCTURAL: a single straight-line if — NO loop. At most one
    # repair call is physically impossible to exceed.
    if not zero_shot_clean:
        checker1_json = json.dumps(envelope1, indent=2)
        repair_user = (
            user
            + "\n\n===== YOUR PREVIOUS ATTEMPT (REJECTED BY THE DCL COMPILER) =====\n"
            + content.rstrip("\n")
            + "\n\n===== DCL COMPILER DIAGNOSTICS (VERBATIM) =====\n"
            + checker1_json
            + "\n\n===== INSTRUCTION =====\n"
            + REPAIR_INSTRUCTION
            + "\n"
        )
        probes.append(probe(endpoint, model))  # single-slot law: probe before the SECOND call too
        t1 = time.time()
        try:
            raw2 = _with_transport_retries(lambda: call(endpoint, model, system, repair_user))
        except _TransportAborted as abort:
            raise AuthoringInstrumentError(f"seat unreachable (repair call) — {abort}") from abort
        except urllib.error.HTTPError as exc:
            raise AuthoringInstrumentError(
                f"seat rejected the repair request (HTTP {exc.code}) — {exc}"
            ) from exc
        repair_wall_time_s = round(time.time() - t1, 2)
        final_content = _content_of(raw2)
        finish2 = _finish_of(raw2)
        envelope2 = _compile_content(final_content)
        repaired_clean = _envelope_clean(envelope2)
        attempts = 2

    final_clean = zero_shot_clean if attempts == 1 else bool(repaired_clean)

    # --- the empty-content guard (the calibration run's vacuous-pass lesson) ---
    failure_reason: Optional[str] = None
    if not final_content.strip():
        failure_reason = "final graded content is empty/whitespace (vacuously clean is not authored)"
    elif not final_clean:
        codes = _envelope_summary(envelope2 if attempts == 2 else envelope1)["error_codes"]
        failure_reason = (
            f"final attempt did not compile clean after the bounded repair pass "
            f"(errors: {codes})"
            if attempts == 2
            else f"attempt compiled dirty (errors: {codes})"
        )
    elif not _has_capability_decl(final_content):
        failure_reason = (
            "final content compiles clean but declares no `capability` — a vacuous "
            "compile is not an authored capability"
        )

    authored = failure_reason is None

    # --- build + write the receipt (ALWAYS, on success AND authoring-failure) ---
    artifact_rel: Optional[str] = None
    if authored:
        artifact_rel = f"features/{feature}/{feature}.dcl"

    receipt_model = _build_receipt(
        feature=feature,
        task=task,
        capability=capability,
        authored=authored,
        artifact_rel=artifact_rel,
        model=model,
        endpoint=endpoint,
        prompt_sha256=prompt_sha256,
        attempts=attempts,
        zero_shot_clean=zero_shot_clean,
        repaired_clean=repaired_clean,
        envelope1=envelope1,
        envelope2=envelope2,
        probes=probes,
        wall_time_s=wall_time_s,
        repair_wall_time_s=repair_wall_time_s,
        finish1=finish1,
        finish2=finish2,
        failure_reason=failure_reason,
    )
    receipt_rel = f"qa/dcl/authoring-{feature}.yaml"
    receipt_path = repo / receipt_rel
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(
        yaml.safe_dump(receipt_model.model_dump(mode="json"), sort_keys=False),
        encoding="utf-8",
    )

    # --- write the artifact ONLY on a clean, non-vacuous final attempt ---
    if authored:
        artifact_path = repo / artifact_rel  # type: ignore[arg-type]
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        artifact_path.write_text(_insert_task_marker(final_content, task), encoding="utf-8")

    return AuthoringResult(
        authored=authored,
        attempts=attempts,
        zero_shot_clean=zero_shot_clean,
        repaired_clean=repaired_clean,
        artifact=artifact_rel,
        receipt=receipt_rel,
        failure_reason=failure_reason,
        exit_code=0 if authored else 1,
        single_slot_probes=tuple(probes),
    )


def _build_receipt(
    *,
    feature: str,
    task: str,
    capability: Optional[str],
    authored: bool,
    artifact_rel: Optional[str],
    model: str,
    endpoint: str,
    prompt_sha256: str,
    attempts: int,
    zero_shot_clean: bool,
    repaired_clean: Optional[bool],
    envelope1: Dict[str, Any],
    envelope2: Optional[Dict[str, Any]],
    probes: List[Dict[str, Any]],
    wall_time_s: float,
    repair_wall_time_s: Optional[float],
    finish1: Optional[str],
    finish2: Optional[str],
    failure_reason: Optional[str],
):
    # Lazy import to keep the module's import graph flat (mirrors the CLI idiom).
    from guardkit.qa.formats.dcl_authoring import (
        AuthoringEnvelope,
        AuthoringEnvelopes,
        AuthoringFinishReasons,
        AuthoringPrompt,
        AuthoringSampling,
        AuthoringToolIdentity,
        AuthoringVocabRef,
        DclAuthoring,
        SingleSlotProbe,
    )

    s1 = _envelope_summary(envelope1)
    env2_model = None
    if envelope2 is not None:
        s2 = _envelope_summary(envelope2)
        env2_model = AuthoringEnvelope(**s2)

    return DclAuthoring(
        format_version=DclAuthoring.CURRENT_FORMAT_VERSION,
        feature=feature,
        task=task,
        capability=capability,
        authored=authored,
        artifact=artifact_rel,
        model=model,
        endpoint=endpoint,
        sampling=AuthoringSampling(
            temperature=TEMPERATURE, top_p=TOP_P, max_tokens=MAX_TOKENS
        ),
        prompt=AuthoringPrompt(
            system_sha256=PINNED_SYSTEM_PROMPT_SHA256,
            prompt_sha256=prompt_sha256,
            composition=COMPOSITION,
        ),
        vocab_ref=AuthoringVocabRef(
            path="guardkit/qa/dcl/vocab-reference.md", sha256=VOCAB_REF_SHA256
        ),
        attempts=attempts,
        zero_shot_clean=zero_shot_clean,
        repaired_clean=repaired_clean,
        envelopes=AuthoringEnvelopes(
            attempt1=AuthoringEnvelope(**s1), attempt2=env2_model
        ),
        single_slot_probes=[
            SingleSlotProbe(url=str(p.get("url", "")), ok=bool(p.get("ok"))) for p in probes
        ],
        wall_time_s=wall_time_s,
        repair_wall_time_s=repair_wall_time_s,
        finish_reasons=AuthoringFinishReasons(attempt1=finish1, attempt2=finish2),
        failure_reason=failure_reason,
        tool=AuthoringToolIdentity(name="guardkit dcl author", checker_pin=CHECKER_PIN),
    )
