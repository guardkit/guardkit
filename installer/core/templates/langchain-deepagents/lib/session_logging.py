"""Session log writer and bootstrap logging configuration.

Two orchestrator-level logging primitives that every adversarial-cooperation
template needs:

1. ``write_session_log`` — unconditional per-run JSON diagnostic dump. Works
   for every pipeline outcome, including failures and retry exhaustion, so
   that post-hoc debugging has a structured record. The function is
   duck-typed over the ``result`` argument — it does not import any concrete
   ``PipelineResult`` type from a downstream template, so the base can ship
   it without reaching upward into ``langchain-deepagents-weighted-evaluation``
   or any other extension.

2. ``configure_logging`` — root-logger bootstrap called at the top of the
   orchestrator's dispatch function. Uses ``force=True`` so that logger
   configuration wins over framework-level handlers installed earlier in the
   process (e.g. by LangGraph dev server or the DeepAgents middleware stack).
   Without ``force=True``, ``logger.info`` calls are silently swallowed on
   every non-greenfield dispatch path.

Both helpers fix regression classes documented in specialist-agent testing
sessions as Category A bugs (missing diagnostics) and were originally
introduced inline in the weighted-evaluation orchestrator scaffold
(commit ``dfa8090d``). Promoting them here avoids duplication across
templates and gives the orchestrator template a vendorable single source of
truth.

Dependencies: stdlib only.
"""

from __future__ import annotations

import json
import logging
import pathlib
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Bootstrap logging
# ---------------------------------------------------------------------------

def configure_logging(*, debug: bool = False, verbose: bool = False) -> None:
    """Configure root logging before any agent work begins.

    Call this at the top of the orchestrator's dispatch function, before
    loading roles, models, or invoking agents. Without it, every non-greenfield
    dispatch path swallows ``logger.info`` output because the root logger
    already has handlers installed by the surrounding framework.

    Uses ``force=True`` to replace any pre-existing root-logger configuration.
    This is the fix for Category A bugs seen in specialist-agent testing where
    failed runs produced no diagnostic output at all.

    Args:
        debug: When true, sets root level to ``DEBUG``.
        verbose: When true (and ``debug`` is false), sets root level to ``INFO``.

    Neither flag set leaves logging at its pre-call configuration.
    """
    if debug:
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(name)s: %(message)s",
            force=True,
        )
    elif verbose:
        logging.basicConfig(
            level=logging.INFO,
            format="%(name)s: %(message)s",
            force=True,
        )


# ---------------------------------------------------------------------------
# Session log writer
# ---------------------------------------------------------------------------

def _serialize_verdict(verdict: Any) -> dict[str, Any] | None:
    """Serialize a verdict object into a JSON-safe dict.

    Duck-typed: we do not import a concrete verdict type. Instead we read the
    public attributes that exist and skip the ones that do not. This lets the
    same helper serialize:

    - ``CoachVerdict`` from the base template (``decision``, ``score``,
      ``issues``, ``criteria_met``, ``quality_assessment``)
    - ``WeightedVerdict`` from the weighted-evaluation extension
      (``decision``, ``composite_score``, ``criterion_scores``, ``issues``,
      ``quality_assessment``)
    - Any future verdict type that adheres to the same loose contract.

    ``criterion_scores`` receives special handling because each score is itself
    an object with ``name``, ``score``, and ``feedback`` attributes.
    """
    if verdict is None:
        return None

    out: dict[str, Any] = {}

    for attr in ("decision", "score", "composite_score", "issues",
                 "criteria_met", "quality_assessment"):
        if hasattr(verdict, attr):
            out[attr] = getattr(verdict, attr)

    criterion_scores = getattr(verdict, "criterion_scores", None)
    if criterion_scores is not None:
        out["criterion_scores"] = [
            {
                "name": getattr(cs, "name", None),
                "score": getattr(cs, "score", None),
                "feedback": getattr(cs, "feedback", ""),
            }
            for cs in criterion_scores
        ]

    return out


def write_session_log(
    target_id: str,
    result: Any,
    log_dir: str | pathlib.Path = "session-logs",
) -> pathlib.Path | None:
    """Write a per-run diagnostic JSON log, unconditionally.

    Called for every pipeline execution regardless of outcome — success,
    failure, or retry exhaustion. The symmetry is the point: without it,
    failed runs leave no trail and post-hoc debugging becomes guesswork.

    The ``result`` argument is duck-typed. It must expose:

    - ``.success`` (bool)
    - ``.attempts`` (int)
    - ``.error`` (str | None)

    and may optionally expose ``.verdict`` (any object; see
    :func:`_serialize_verdict` for the duck-typed contract).

    Args:
        target_id: Identifier for the target being processed (e.g. target UUID
            or human-readable name). Used in the log filename.
        result: Pipeline outcome object matching the contract above.
        log_dir: Directory for session logs. Created if it does not exist.
            Defaults to ``"session-logs"`` relative to the current working
            directory.

    Returns:
        The path the log was written to, or ``None`` if writing failed. The
        function never raises — a failing log write must not take down the
        pipeline; the warning is logged and the caller carries on.
    """
    log_path = pathlib.Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    timestamp_now = datetime.now()
    filename_stamp = timestamp_now.strftime("%Y%m%d_%H%M%S")
    log_file = log_path / f"{target_id}_{filename_stamp}.json"

    log_entry: dict[str, Any] = {
        "target_id": target_id,
        "timestamp": timestamp_now.isoformat(),
        "success": getattr(result, "success", None),
        "attempts": getattr(result, "attempts", None),
        "error": getattr(result, "error", None),
        "verdict": _serialize_verdict(getattr(result, "verdict", None)),
    }

    try:
        log_file.write_text(json.dumps(log_entry, indent=2))
        logger.info("Session log written: %s", log_file)
        return log_file
    except Exception as exc:  # noqa: BLE001 — diagnostic path must not raise
        logger.warning("Failed to write session log: %s", exc)
        return None
