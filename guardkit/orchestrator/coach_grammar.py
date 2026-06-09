"""Coach verdict GBNF grammar loader (TASK-ARCH-COACHSPLIT, D-3).

The AutoBuild Coach's verdict synthesis runs as a **toolless** model call
(:meth:`HarnessAdapter.invoke_synthesis`). On the llama.cpp + Gemma stack a
toolless request lets a per-request GBNF ``grammar`` constraint take effect
(verified 2026-06-09: toolless + grammar yields a schema-valid verdict;
tool-bound + grammar is hard-rejected with HTTP 400 "Cannot use custom
grammar constraints with tools"). This module loads the grammar string the
orchestrator threads into the synthesis call so the verdict schema is
*guaranteed* at the inference layer rather than merely prompted.

The grammar itself is the artefact authored and A/B-validated under
TASK-OPS-COACHGRAMMAR (Path 1A). It enforces the hard contract the
``coach_output_parser`` + ``_validate_coach_decision`` consume:

* the response ends with a single fenced ```json block,
* the block is a JSON object,
* it carries ``task_id`` (string), ``turn`` (bare integer), and
  ``decision`` (``"approve"`` | ``"feedback"``) in that order,

while *permitting* every optional member the Coach prompt asks for
(``validation_results``, ``criteria_verification``, ``issues``,
``rationale``, …) via generic productions. See the header of
``grammars/coach-verdict.gbnf`` for the full design rationale.

Packaged copies live under ``guardkit/orchestrator/grammars/`` so the
grammar travels with the orchestrator (the source of truth remains
``docs/research/dgx-spark/grammars/`` — the two are kept byte-identical;
``tests/unit/test_coach_grammar.py`` pins parity).
"""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)

_GRAMMARS_DIR = Path(__file__).parent / "grammars"
_PRIMARY = "coach-verdict.gbnf"
_STRICT = "coach-verdict-strict.gbnf"


@lru_cache(maxsize=2)
def load_coach_verdict_grammar(strict: bool = False) -> str:
    """Return the Coach verdict GBNF grammar string.

    Parameters
    ----------
    strict:
        When ``True`` load the early-emission fallback variant
        (``coach-verdict-strict.gbnf``) — biases the model toward emitting
        the verdict fence early at the cost of reasoning depth. Reach for it
        only if the primary grammar shows under-emission (model reasons past
        the Coach token budget without emitting a verdict). Default ``False``
        loads the primary grammar (free-reasoning prefix + guaranteed final
        verdict fence).

    Returns
    -------
    str
        The grammar text, ready to pass as the ``grammar`` argument to
        :meth:`HarnessAdapter.invoke_synthesis`.

    Raises
    ------
    FileNotFoundError
        If the packaged grammar file is missing. The caller
        (``AgentInvoker.invoke_coach``) catches this and falls back to a
        toolless-but-ungrammared synthesis call so a packaging glitch never
        hard-fails the Coach — see that call site for the degraded path.
    """
    name = _STRICT if strict else _PRIMARY
    path = _GRAMMARS_DIR / name
    text = path.read_text(encoding="utf-8")
    logger.debug(
        "coach_grammar: loaded %s (%d bytes) from %s", name, len(text), path
    )
    return text
