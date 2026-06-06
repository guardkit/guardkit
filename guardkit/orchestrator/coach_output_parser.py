"""Coach verdict extractor — orchestrator-side parser for structured Coach output.

Implements **Shape A** of TASK-FIX-COACHOUT01 (Coach Verdict-Emission Contract).

## Why this exists

Under the LangGraph harness (qwen36-workhorse), the legacy Coach contract —
"write your verdict to ``coach_turn_N.json`` via a Bash heredoc" — failed
~33% of the time. Constructing a multi-line, syntactically-valid,
JSON-inside-heredoc Bash command after ~140s of adversarial reasoning is
right at the edge of qwen36-workhorse's instruction-following envelope.
See ``tasks/design_approved/autobuild-harness-migration/TASK-FIX-COACHOUT01-coach-verdict-emission-contract.md``
for the empirical run-5 data and the architectural review at
``docs/state/TASK-FIX-COACHOUT01/architectural_review.md`` for the
Shape A vs Shape B trade-off (82/100, strict intensity).

The fix replaces the Bash-heredoc emission primitive entirely. Coach is now
told to end its response with a fenced ``json`` block; the orchestrator
parses Coach's final response text, extracts the JSON block, validates
required fields, and writes ``coach_turn_N.json`` itself. Coach remains
read-only (``allowed_tools`` unchanged: ``[Read, Bash, Grep, Glob]``).

## Substrate parity

Both ``ClaudeSDKHarness`` (``sdk_harness.py:340``) and ``LangGraphHarness``
(``langgraph_harness.py:370``) emit ``AssistantMessageEvent`` with ``text``
populated. SDK may emit multiple events per turn (one per ``AssistantMessage``
in the stream); LangGraph emits exactly one. The concatenation strategy below
(join all ``AssistantMessageEvent.text`` fields with newlines) is correct
for SDK and identity-correct for LangGraph — see the parity assessment at
``docs/state/TASK-FIX-COACHOUT01/architectural_review.md`` §"Substrate Parity
Assessment".

## COACHSF01 coupling (Gap 2 from Phase 2.5B review)

``autobuild.py:5676-5678`` (COACHSF01 safety net) matches on the literal
substrings ``"Coach decision not found"`` and ``"Coach decision invalid"`` to
fire its synthetic-feedback fallback. Every exception raised from this module
MUST have a ``str(...)`` representation containing one of those substrings
verbatim — otherwise the safety net silently misses verdict-emission
failures and the wave loop hard-fails instead of giving the Player a turn
N+1 with synthetic feedback. The raise sites below prefix every message
with the matching substring; the regression test
``tests/unit/test_coach_output_parser.py::test_coachsf01_error_string_coupling``
pins this contract.

## Module-level function, not class (Gap 3 from Phase 2.5B review)

``extract_and_write`` is a module-level function. A stateless
``CoachOutputParser`` class would be a YAGNI violation — no constructor
arguments, no instance state. If future parameterisation is needed
(swappable regex pattern, output-path strategy), the parameters become
function kwargs with sensible defaults, not constructor arguments.
"""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List

from guardkit.orchestrator.exceptions import (
    CoachDecisionInvalidError,
    CoachDecisionNotFoundError,
)
from guardkit.orchestrator.harness.adapter import (
    AssistantMessageEvent,
    HarnessEvent,
)

logger = logging.getLogger(__name__)


# Fenced JSON block anywhere in the Coach response text. DOTALL so the body
# may span newlines. ``.+?`` is non-greedy — combined with the outer fence
# delimiters this yields one capture per fence pair. ``findall`` returns all
# matches in source order; the caller takes the last one (handles models that
# emit exploratory JSON mid-reasoning and a corrected final block).
#
# The leading ``\s*\n?`` after ``json`` tolerates models that emit
# ``\`\`\`json{...}`\`\`\`` without a newline after the language tag, and
# the trailing ``\s*`` before the closing fence tolerates trailing whitespace.
#
# Note the body capture is intentionally permissive (``.+?`` rather than
# ``\{.*?\}``): malformed JSON, top-level arrays, and top-level scalars are
# valid matches at the regex level so that the JSON / structural validation
# step below produces a precise ``CoachDecisionInvalidError`` instead of a
# misleading ``CoachDecisionNotFoundError``. The COACHSF01 safety net at
# ``autobuild.py:5676-5678`` discriminates on the two substrings — we want
# the right one to fire for each failure class.
_FENCE_PATTERN = re.compile(
    r"```json\s*\n?(.+?)\s*\n?```",
    re.DOTALL,
)

# Required top-level keys on every Coach decision (whether approve or feedback).
# Mirrors the contract enforced by ``AgentInvoker._validate_coach_decision``
# downstream, but checked here too so the parser raises the COACHSF01-friendly
# ``CoachDecisionInvalidError`` instead of letting an under-specified file hit
# the validator. ``decision`` must additionally be ``"approve"`` or
# ``"feedback"`` (validated below).
_REQUIRED_TOP_LEVEL_KEYS = ("task_id", "turn", "decision")


def _collect_assistant_text(harness_events: Iterable[HarnessEvent]) -> str:
    """Concatenate every ``AssistantMessageEvent.text`` from a harness stream.

    Both substrates emit ``AssistantMessageEvent`` with ``text`` populated
    (adapter.py:33-45). SDK may emit multiple events per turn; LangGraph emits
    exactly one. Concatenating with newlines preserves block boundaries that
    the SDK splits across events, while leaving the single-event LangGraph
    case identity-correct (one event → one ``text`` string with no leading
    or trailing newline added by ``join``).

    Non-``AssistantMessageEvent`` variants (``ToolUseEvent``,
    ``ToolResultEvent``, ``ResultMessageEvent``) are skipped — Coach's
    verdict prose is text, not tool calls.
    """
    return "\n".join(
        event.text
        for event in harness_events
        if isinstance(event, AssistantMessageEvent)
    )


def _atomic_write(output_path: Path, content: str) -> None:
    """Atomic write via ``.tmp`` + ``os.replace`` to avoid torn-file reads.

    Mirrors the pattern the Player uses for ``task_work_results.json``
    elsewhere in the orchestrator — write to a sibling ``.tmp`` then rename
    on top of the target. ``os.replace`` is atomic on POSIX and Windows,
    so a concurrent reader either sees the previous file (if any) or the
    new file, never a partial write.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = output_path.with_suffix(output_path.suffix + ".tmp")
    tmp_path.write_text(content)
    os.replace(tmp_path, output_path)


def extract_and_write(
    harness_events: List[HarnessEvent],
    task_id: str,
    turn: int,
    output_path: Path,
) -> Dict[str, Any]:
    """Extract the Coach verdict from a harness event stream and persist it.

    Concatenates every ``AssistantMessageEvent.text`` in ``harness_events``,
    finds every fenced ``json`` block in the joined text, takes the **last**
    block (handles models that emit exploratory JSON mid-reasoning then a
    corrected final block), parses it, validates required top-level fields,
    and writes the JSON document atomically to ``output_path``.

    Args:
        harness_events: The full ``List[HarnessEvent]`` ``_invoke_with_role``
            assembled during the Coach turn. May contain ``AssistantMessageEvent``,
            ``ToolUseEvent``, ``ToolResultEvent``, ``ResultMessageEvent`` —
            only ``AssistantMessageEvent`` contributes text.
        task_id: The task identifier this verdict belongs to. Used only for
            error messages; the parser does NOT enforce that the parsed
            ``task_id`` field matches (``_validate_coach_decision`` downstream
            owns that check).
        turn: The turn number. Same role as ``task_id`` above.
        output_path: Destination for ``coach_turn_{turn}.json``. The parser
            writes the document the existing ``_load_agent_report`` consumer
            (``agent_invoker.py:4109``) reads. Parent directory is created
            on demand.

    Returns:
        The parsed decision dict. The caller (``invoke_coach``) does not
        currently use the return value — ``_load_agent_report`` re-reads
        the file by design — but returning the dict makes the parser
        directly testable without round-tripping through disk and gives
        future callers a fast path that skips the second read.

    Raises:
        CoachDecisionNotFoundError: If no fenced ``json`` block is present
            in any ``AssistantMessageEvent``. ``str(error)`` is prefixed with
            ``"Coach decision not found"`` so the COACHSF01 safety net in
            ``autobuild.py:5672-5698`` fires.
        CoachDecisionInvalidError: If the last fenced block is malformed
            JSON, is not a JSON object, is missing a required top-level
            field (``task_id`` / ``turn`` / ``decision``), or has a
            ``decision`` value other than ``"approve"`` or ``"feedback"``.
            ``str(error)`` is prefixed with ``"Coach decision invalid"`` so
            COACHSF01 fires.
    """
    full_text = _collect_assistant_text(harness_events)

    # No assistant text at all is a known LangGraph edge case: a final
    # tool-call-only AIMessage with empty content collapses to an empty
    # AssistantMessageEvent.text. Treat as "decision not found" so COACHSF01
    # fires and the Player gets a retry turn.
    if not full_text:
        raise CoachDecisionNotFoundError(
            f"Coach decision not found: no assistant text in harness "
            f"events for {task_id} turn {turn} (0 AssistantMessageEvent)"
        )

    matches = _FENCE_PATTERN.findall(full_text)
    if not matches:
        raise CoachDecisionNotFoundError(
            f"Coach decision not found: no fenced ```json block in Coach "
            f"response for {task_id} turn {turn} "
            f"({len(full_text)} chars of assistant text)"
        )

    # Take the LAST block — handles "exploratory JSON then corrected final
    # block" (a real qwen36-workhorse pattern) and is consistent with how
    # instruction-tuned models are commonly prompted ("end your response
    # with a fenced JSON block").
    candidate = matches[-1]

    try:
        decision = json.loads(candidate)
    except json.JSONDecodeError as e:
        raise CoachDecisionInvalidError(
            f"Coach decision invalid: last fenced JSON block is malformed "
            f"for {task_id} turn {turn}: {e}"
        ) from e

    # Coach's decision must be a JSON object. A bare array or scalar at the
    # top level would parse but cannot carry the required fields and would
    # crash _validate_coach_decision downstream with a less helpful error.
    if not isinstance(decision, dict):
        raise CoachDecisionInvalidError(
            f"Coach decision invalid: last fenced JSON block is not an "
            f"object for {task_id} turn {turn} (got {type(decision).__name__})"
        )

    missing = [key for key in _REQUIRED_TOP_LEVEL_KEYS if key not in decision]
    if missing:
        raise CoachDecisionInvalidError(
            f"Coach decision invalid: missing required field(s) "
            f"{missing} for {task_id} turn {turn}"
        )

    if decision["decision"] not in ("approve", "feedback"):
        raise CoachDecisionInvalidError(
            f"Coach decision invalid: 'decision' must be 'approve' or "
            f"'feedback' for {task_id} turn {turn}, got "
            f"{decision['decision']!r}"
        )

    # Atomic write preserves the existing _load_agent_report consumer
    # contract — the file on disk is what the rest of the pipeline reads.
    _atomic_write(output_path, json.dumps(decision, indent=2))

    logger.debug(
        "coach_output_parser: extracted %s verdict for %s turn %s "
        "(%d fenced block(s) seen, used last; %d chars assistant text)",
        decision["decision"], task_id, turn, len(matches), len(full_text),
    )

    return decision
