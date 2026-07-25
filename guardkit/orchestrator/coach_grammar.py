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

Contract resolution (TASK-CMIR-003):

* ``resolve_coach_contract()`` decides the active contract with precedence:
  env ``GUARDKIT_COACH_CONTRACT`` > ``.guardkit/config.yaml``
  ``autobuild.coach.contract`` > default ``"coachsplit"``.
* The grammar loader routes on the resolved contract to select the correct
  .gbnf file (``coach_verdict`` for ``"coachsplit"``, ``coach_verdict_v4``
  for ``"v4"``).
"""

from __future__ import annotations

import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

logger = logging.getLogger(__name__)

_GRAMMARS_DIR = Path(__file__).parent / "grammars"
_PRIMARY = "coach-verdict.gbnf"
_STRICT = "coach-verdict-strict.gbnf"
_V4 = "coach-verdict-v4.gbnf"

# Valid contract names recognised by resolve_coach_contract().
_VALID_CONTRACTS: frozenset[str] = frozenset({"coachsplit", "v4"})


def resolve_coach_contract() -> str:
    """Resolve the active Coach contract name.

    Resolution order (highest precedence first):

    1. ``GUARDKIT_COACH_CONTRACT`` environment variable.
    2. ``.guardkit/config.yaml`` key ``autobuild.coach.contract``.
    3. Default: ``"coachsplit"``.

    Returns
    -------
    str
        One of the recognised contract names (``"coachsplit"`` or ``"v4"``).
        If the env var is set to an unrecognised value the function falls
        through to the next tier rather than raising — this keeps the system
        resilient to typos in operator configuration.
    """
    # Tier 1: environment variable.
    env_val = os.environ.get("GUARDKIT_COACH_CONTRACT")
    if env_val and env_val in _VALID_CONTRACTS:
        return env_val

    # Tier 2: config.yaml (only if the file exists).
    config_path = Path(".guardkit/config.yaml")
    if config_path.is_file():
        try:
            import yaml  # pyright: ignore[reportUnknownVariableType]

            cfg = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
            contract = (
                cfg.get("autobuild", {})
                .get("coach", {})
                .get("contract")
            )
            if contract and contract in _VALID_CONTRACTS:
                return str(contract)
        except Exception:  # noqa: BLE001 — degrade gracefully
            logger.debug(
                "coach_grammar: failed to read config.yaml contract; "
                "falling through to default",
            )

    # Tier 3: default.
    return "coachsplit"


@lru_cache(maxsize=4)
def load_coach_verdict_grammar(
    strict: bool = False,
    contract: str | None = None,
) -> str:
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

    contract:
        The Coach contract to load.  Accepted values are ``"coachsplit"``
        (loads the primary or strict grammar) and ``"v4"`` (loads the
        v4 grammar).  When ``None`` the function calls
        :func:`resolve_coach_contract` to determine the active contract.

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
    if contract is None:
        contract = resolve_coach_contract()

    if contract == "v4":
        name = _V4
    elif strict:
        name = _STRICT
    else:
        name = _PRIMARY

    path = _GRAMMARS_DIR / name
    text = path.read_text(encoding="utf-8")
    logger.debug(
        "coach_grammar: loaded %s (contract=%s, %d bytes) from %s",
        name,
        contract,
        len(text),
        path,
    )
    return text
