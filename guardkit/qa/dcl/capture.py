"""The every-run DCL capture lane (W2ab) — CPU-only, ZERO seat calls.

Rich's idea (2026-07-17): *compile the DCL for every run even on BDD/Gherkin
repos, so we get more training data.* Accepted with one reframe (build-handoff
§3): the expensive §10 **authoring** protocol stays OFF the run's critical path
(it runs offline in the corpus generator, where the single seat is free); the
run itself only does the two CPU-cheap, zero-cost captures wired here:

  * **W2a — compile-every-artifact shadow** (:func:`compile_shadow`): on EVERY
    run, on EVERY track, any ``features/**/*.dcl`` in the repo is compiled with
    the vendored WASM checker (milliseconds, LLM-free, no network) and one queue
    row per file is appended. Catches artifact rot on gherkin repos for free; on
    ``dcl`` repos the oracle already gates — the shadow only ADDS the row.
  * **W2b — the brief harvest** (:func:`append_brief`): the guardkit-side seam
    for appending a feature's spec inputs (the authoring prompt's raw material)
    to the same capture queue. (The forge plan-commit leg carries its own harvest
    write; this is the guardkit door so guardkit-driven runs can harvest too —
    same sink, same schema.)

**Laws honoured (build-handoff §0):**

- **Fallback law (§0.1):** capture is default-OFF, flag-gated
  (``dcl.capture`` / ``GUARDKIT_DCL_CAPTURE``), and swallow-to-log on EVERY error
  path. Neither function EVER raises, changes a verdict, blocks a run, or adds a
  failure mode to the gherkin track. When the flag is off both functions return
  after the config read — zero further reads, no sink dir, no checker call, no
  log rows.
- **Single-slot law:** ZERO seat calls, ZERO network — this module imports only
  the vendored checker (subprocess/node, no socket) and stdlib. Nothing here can
  reach ``:9000``.
- **Honest gates:** a checker instrument fault (node missing, non-JSON, crash),
  an unreadable ``.dcl``, or an unwritable sink is caught and ``logger.warning``-ed
  in this lane only; the run's verdict is untouched.

**The single every-run seam (W2a wiring).** :func:`compile_shadow` is wired at
``AgentInvoker._write_task_work_results`` beside the ``_run_dcl_oracle`` call
(agent_invoker.py) — the ONE hook that fires exactly once per verification run,
on every track. The ``coach_validator`` seam is deliberately NOT used: it runs
independent *factory BDD* plugin discovery (``_run_factory_bdd``), not this
oracle, so wiring the shadow there would double-fire relative to the Player-side
oracle seam. One seam, one row per run.

Sink schema (JSONL, one object per line, ``sort_keys=True`` for stable bytes):

  * compile_shadow: ``{kind, repo, file, sha256, ok, error_count, warning_count,
    error_codes, run_id}``
  * brief:          ``{kind: "brief", **payload}``
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from guardkit.qa.dcl import checker

logger = logging.getLogger(__name__)

__all__ = [
    "CAPTURE_ENV",
    "DEFAULT_SINK",
    "is_capture_enabled",
    "resolve_sink",
    "compile_shadow",
    "append_brief",
]

#: Env override for the capture flag (truthy/falsy, the enforcement.py idiom).
#: When set it wins over ``.guardkit/config.yaml``; a falsy value forces OFF.
CAPTURE_ENV = "GUARDKIT_DCL_CAPTURE"

#: The default capture sink, resolved against ``repo_root`` (absolute paths in
#: config are honoured verbatim).
DEFAULT_SINK = ".guardkit/dcl-capture/queue.jsonl"

_TRUTHY = frozenset({"1", "true", "yes", "on"})
_FALSY = frozenset({"0", "false", "no", "off", ""})

#: Dotdirs and vendored dirs are skipped — the same exclusions the DCL discovery
#: scan uses (discovery.py) so a vendored ``.dcl`` shipped with a third-party
#: package is never compiled as a project capability.
_EXCLUDED_DIR_NAMES: frozenset[str] = frozenset(
    {"node_modules", "__pycache__", "site-packages"}
)


# ---------------------------------------------------------------------------
# Config (the enforcement.py / spec_track.py idiom): a top-level ``dcl`` mapping
# with ``capture`` (bool, default False) + ``capture_sink`` (str, default sink).
# ---------------------------------------------------------------------------


def _load_config(repo_root: Path) -> dict:
    """Read ``<repo_root>/.guardkit/config.yaml``; empty dict if absent/unreadable
    (the enforcement.py idiom — a bad config is treated as OFF, never a crash)."""
    path = repo_root / ".guardkit" / "config.yaml"
    if not path.is_file():
        return {}
    try:
        import yaml

        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 — a bad config never breaks a run
        logger.warning(
            "dcl.capture: could not read %s (%r) — treating as OFF", path, exc
        )
        return {}
    return data if isinstance(data, dict) else {}


def is_capture_enabled(repo_root: Path) -> bool:
    """Whether the DCL capture lane is on for ``repo_root``.

    Precedence: ``GUARDKIT_DCL_CAPTURE`` env (truthy/falsy) >
    ``.guardkit/config.yaml`` ``dcl.capture`` > ``False``.

    Default OFF everywhere (Fallback law): a repo flips ``dcl.capture: true`` as a
    one-line reversible step; nothing captures fleet-wide by default.
    """
    env = os.environ.get(CAPTURE_ENV)
    if env is not None:
        token = env.strip().lower()
        if token in _TRUTHY:
            return True
        if token in _FALSY:
            return False
        logger.warning(
            "%s=%r is not a recognised boolean — treating as OFF", CAPTURE_ENV, env
        )
        return False
    dcl = _load_config(repo_root).get("dcl")
    if not isinstance(dcl, dict):
        return False
    return bool(dcl.get("capture", False))


def resolve_sink(repo_root: Path) -> Path:
    """The capture sink path for ``repo_root``.

    ``.guardkit/config.yaml`` ``dcl.capture_sink`` overrides :data:`DEFAULT_SINK`;
    a relative value is resolved against ``repo_root``, an absolute value is
    honoured verbatim.
    """
    sink_rel = DEFAULT_SINK
    dcl = _load_config(repo_root).get("dcl")
    if isinstance(dcl, dict):
        configured = dcl.get("capture_sink")
        if isinstance(configured, str) and configured.strip():
            sink_rel = configured.strip()
    p = Path(sink_rel)
    return p if p.is_absolute() else (repo_root / p)


def _append_row(sink_path: Path, row: Dict[str, Any]) -> None:
    """Append one JSONL row (stable bytes). Raises on an unwritable sink — the
    caller swallows-to-log."""
    sink_path.parent.mkdir(parents=True, exist_ok=True)
    with sink_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, sort_keys=True) + "\n")


# ---------------------------------------------------------------------------
# Compile shadow (W2a) + the checker envelope summary.
# ---------------------------------------------------------------------------


def _summarize(envelope: Dict[str, Any]) -> Dict[str, Any]:
    """The compile-row summary from a checker envelope (mirrors author.py's
    ``_envelope_summary``)."""
    return {
        "ok": bool(envelope.get("ok")) and int(envelope.get("errorCount", 0) or 0) == 0,
        "error_count": int(envelope.get("errorCount", 0) or 0),
        "warning_count": int(envelope.get("warningCount", 0) or 0),
        "error_codes": [
            d.get("code")
            for d in envelope.get("diagnostics", []) or []
            if isinstance(d, dict) and d.get("severity") == "error" and d.get("code")
        ],
    }


def _iter_dcl_files(features_dir: Path) -> List[Path]:
    """All ``features/**/*.dcl`` (dotdirs + vendored dirs excluded), sorted for
    deterministic row order."""
    out: List[Path] = []
    for fp in sorted(features_dir.rglob("*.dcl")):
        rel_parts = fp.relative_to(features_dir).parts
        if any(
            part.startswith(".") or part in _EXCLUDED_DIR_NAMES for part in rel_parts
        ):
            continue
        out.append(fp)
    return out


def _shadow_one(
    fp: Path, repo: Path, sink_path: Path, run_id: Optional[str]
) -> None:
    """Compile ONE ``.dcl`` and append its row. Every error path is caught and
    ``logger.warning``-ed here — a bad file never aborts the sweep and never
    raises. On a checker fault the sink holds no row for this file."""
    try:
        raw = fp.read_bytes()
    except OSError as exc:
        logger.warning("dcl capture: unreadable .dcl %s (%r) — skipped", fp, exc)
        return
    sha256 = hashlib.sha256(raw).hexdigest()

    try:
        envelope = checker.check(fp)
    except Exception as exc:  # noqa: BLE001 — CheckerError, node missing, crash
        logger.warning(
            "dcl capture: checker fault on %s (%r) — logged, no row", fp, exc
        )
        return

    summary = _summarize(envelope)
    try:
        rel = str(fp.relative_to(repo))
    except ValueError:
        rel = str(fp)

    logger.info(
        "dcl compile-shadow: %s ok=%s errorCount=%s",
        rel,
        summary["ok"],
        summary["error_count"],
    )

    row = {
        "kind": "compile_shadow",
        "repo": str(repo),
        "file": rel,
        "sha256": sha256,
        "ok": summary["ok"],
        "error_count": summary["error_count"],
        "warning_count": summary["warning_count"],
        "error_codes": summary["error_codes"],
        "run_id": run_id,
    }
    try:
        _append_row(sink_path, row)
    except OSError as exc:
        logger.warning(
            "dcl capture: unwritable sink %s (%r) — row dropped", sink_path, exc
        )


def compile_shadow(repo_root: Path, *, run_id: Optional[str] = None) -> None:
    """Compile every ``features/**/*.dcl`` in ``repo_root`` and queue one row each.

    Default-OFF: when the ``dcl.capture`` flag is off this returns after the config
    read — zero further reads, no sink dir, no checker invocation, no log rows.

    When ON, on EVERY track: each ``.dcl`` is compiled (vendored checker,
    CPU-only, no seat, no network) and a ``compile_shadow`` row is appended to the
    configured sink. This function NEVER raises — every error path (checker
    crash, node missing, unreadable file, unwritable sink) is swallowed-to-log so
    the run's verdict/flow is untouched (Fallback law).
    """
    try:
        repo = Path(repo_root)
        if not is_capture_enabled(repo):
            return
        sink_path = resolve_sink(repo)
        features_dir = repo / "features"
        if not features_dir.is_dir():
            return
        for fp in _iter_dcl_files(features_dir):
            _shadow_one(fp, repo, sink_path, run_id)
    except Exception as exc:  # noqa: BLE001 — belt-and-suspenders: never raise
        logger.warning("dcl capture: compile_shadow guard swallowed %r", exc)


def append_brief(repo_root: Path, payload: Dict[str, Any]) -> None:
    """Append a brief-harvest row (``{kind: "brief", **payload}``) to the sink.

    Same flag gate + sink resolution as :func:`compile_shadow`; default-OFF
    (returns after the config read). No seat calls, no artifact writes. NEVER
    raises — an unwritable sink or any other fault is swallowed-to-log (Fallback
    law). The forge plan-commit leg carries its own harvest write; this is the
    guardkit-side door onto the same sink + schema.
    """
    try:
        repo = Path(repo_root)
        if not is_capture_enabled(repo):
            return
        sink_path = resolve_sink(repo)
        row = {"kind": "brief", **(payload or {})}
        _append_row(sink_path, row)
    except Exception as exc:  # noqa: BLE001 — never raise into the run
        logger.warning("dcl capture: append_brief guard swallowed %r", exc)
