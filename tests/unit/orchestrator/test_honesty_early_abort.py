"""Unit tests for ``_check_honesty_early_abort`` rolling-average abort
(TASK-FIX-HEAB).

Covers:

- AC-5 (``test_honesty_early_abort_triggers_at_threshold``): a 4-turn
  honesty sequence ``[0.6, 0.4, 0.2, 0.1]`` aborts at turn 3 once the
  rolling average over the last ``window=3`` samples drops below the
  configured threshold.
- AC-6 (``test_honesty_early_abort_does_not_trigger_when_above_threshold``):
  a high-honesty sequence ``[0.9, 0.85, 0.95]`` never trips the abort
  with the default threshold of ``0.3``.
- AC-7 (``test_honesty_early_abort_window_partial_data``): with fewer
  than ``window`` honesty samples recorded, the abort is suppressed
  even when the available samples are deeply negative — first-turn
  false trips are guarded by the window precondition.

These are pure-Python unit tests — no SDK invocations, no live pytest
runs against the host repo. The orchestrator instance is constructed
via ``__new__`` so we don't need a worktree manager or a git repo.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import List

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from guardkit.orchestrator.autobuild import AutoBuildOrchestrator, TurnRecord
from guardkit.orchestrator.agent_invoker import AgentInvocationResult


# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------


def _make_orch(
    threshold: float = 0.3,
    window: int = 3,
    max_turns: int = 5,
) -> AutoBuildOrchestrator:
    """Construct a minimal orchestrator that exercises only the helper.

    Bypassing ``__init__`` avoids the WorktreeManager and ProgressDisplay
    construction the helper does not touch — we only need
    ``_honesty_history``, ``honesty_early_abort_threshold``,
    ``honesty_early_abort_window``, and ``max_turns``.
    """
    orch = AutoBuildOrchestrator.__new__(AutoBuildOrchestrator)
    orch._honesty_history = []
    orch.honesty_early_abort_threshold = threshold
    orch.honesty_early_abort_window = window
    orch.max_turns = max_turns
    return orch


def _make_turn(
    score: float,
    turn: int = 1,
    claim: str = "src/foo.py",
) -> TurnRecord:
    """Build a TurnRecord with a Coach report whose ``honesty_verification``
    payload reports ``score`` and whose ``issues`` list names ``claim`` as
    the most-flagged path. Mirrors the post-FFC3 serialisation shape:
    discrepancies are NOT in the honesty_verification dict — they live
    under ``issues[*]['details']['player_claim']`` (category 'honesty')
    where ``_honesty_issues_from`` placed them.
    """
    coach = AgentInvocationResult(
        task_id="TASK-FIX-HEAB",
        turn=turn,
        agent_type="coach",
        success=True,
        report={
            "honesty_verification": {
                "verified": False,
                "honesty_score": score,
                "discrepancy_count": 1,
                "resolved_paths": [],
            },
            "issues": [
                {
                    "severity": "must_fix",
                    "category": "honesty",
                    "description": (
                        f"Honesty verification failed: claim={claim} disagrees "
                        f"with worktree state."
                    ),
                    "details": {
                        "claim_type": "file_existence",
                        "player_claim": claim,
                        "actual_value": "not on disk",
                    },
                }
            ],
        },
        duration_seconds=0.1,
    )
    player = AgentInvocationResult(
        task_id="TASK-FIX-HEAB",
        turn=turn,
        agent_type="player",
        success=True,
        report={},
        duration_seconds=0.0,
    )
    return TurnRecord(
        turn=turn,
        player_result=player,
        coach_result=coach,
        decision="feedback",
        feedback=None,
        timestamp="2026-05-10T18:00:00Z",
    )


def _drive_loop(
    orch: AutoBuildOrchestrator,
    scores: List[float],
    worktree_path: Path,
    claim: str = "src/foo.py",
):
    """Replay the per-turn drive: append each score to honesty_history,
    append the matching TurnRecord to a local turn_history, and call the
    helper after each turn until it returns a non-None abort message or
    the input is exhausted.

    Returns ``(abort_message, abort_turn, turn_history)``.
    """
    turn_history: List[TurnRecord] = []
    for i, score in enumerate(scores, start=1):
        orch._honesty_history.append(score)
        turn_history.append(_make_turn(score, turn=i, claim=claim))
        msg = orch._check_honesty_early_abort(
            turn_history,
            task_id="TASK-FIX-HEAB",
            worktree_path=worktree_path,
        )
        if msg is not None:
            return msg, i, turn_history
    return None, None, turn_history


# ---------------------------------------------------------------------------
# AC-5: Triggers at threshold
# ---------------------------------------------------------------------------


def test_honesty_early_abort_triggers_at_threshold(tmp_path: Path) -> None:
    """AC-5: 4-turn honesty sequence aborts at turn 3.

    With ``window=3`` and ``threshold=0.5`` the rolling averages are:

    - After turn 1 (``[0.6]``)            len < window           → no abort
    - After turn 2 (``[0.6, 0.4]``)       len < window           → no abort
    - After turn 3 (``[0.6, 0.4, 0.2]``)  avg=0.40 < 0.5         → ABORT
    - After turn 4                        never reached

    The threshold is set above the default ``0.3`` for this fixture so
    that ``avg([0.6, 0.4, 0.2]) = 0.4`` strictly satisfies the
    ``rolling_avg < threshold`` predicate. The default threshold is
    intentionally conservative to avoid false trips during normal
    early-turn degradation; the AC's "exits at turn 3" assertion is
    about the algorithm's shape, not about the default value.
    """
    orch = _make_orch(threshold=0.5, window=3, max_turns=5)
    msg, abort_turn, turn_history = _drive_loop(
        orch, [0.6, 0.4, 0.2, 0.1], tmp_path, claim="src/foo.py"
    )

    assert abort_turn == 3, (
        f"Expected abort at turn 3 but fired at turn {abort_turn} "
        f"(history={orch._honesty_history})"
    )
    assert msg is not None
    # AC-4: message names rolling average and threshold.
    assert "0.40" in msg or "0.4" in msg, f"missing rolling avg in: {msg}"
    assert "0.5" in msg, f"missing threshold in: {msg}"
    # AC-4: message names the most-flagged path with its window count.
    assert "src/foo.py" in msg, f"missing flagged path in: {msg}"
    assert "3 of last 3" in msg, f"missing flag count in: {msg}"
    # AC-4: message names turns saved (max_turns=5, abort at 3 → 2 saved).
    assert "Saved 2 turn" in msg, f"missing turns-saved phrase in: {msg}"


# ---------------------------------------------------------------------------
# AC-6: Does not trigger when above threshold
# ---------------------------------------------------------------------------


def test_honesty_early_abort_does_not_trigger_when_above_threshold(
    tmp_path: Path,
) -> None:
    """AC-6: high-honesty sequence never aborts.

    With the default threshold ``0.3`` and ``window=3``, the rolling
    average over ``[0.9, 0.85, 0.95]`` is ``0.9`` — well above
    threshold — so the helper must return ``None`` after every turn
    and the loop continues normally.
    """
    orch = _make_orch(threshold=0.3, window=3, max_turns=5)
    msg, abort_turn, turn_history = _drive_loop(
        orch, [0.9, 0.85, 0.95], tmp_path, claim="src/foo.py"
    )

    assert abort_turn is None, (
        f"Abort fired unexpectedly at turn {abort_turn}: {msg}"
    )
    assert msg is None
    # All three samples retained in honesty_history (loop didn't exit).
    assert orch._honesty_history == [0.9, 0.85, 0.95]


# ---------------------------------------------------------------------------
# AC-7: Window precondition (partial data)
# ---------------------------------------------------------------------------


def test_honesty_early_abort_window_partial_data(tmp_path: Path) -> None:
    """AC-7: fewer than ``window`` samples → no abort, even when the
    available samples are deeply negative.

    This guards against first-turn false trips where a single bad
    honesty score (e.g. an early Player misclaim) would otherwise
    abort the loop before the window is even populated. The check
    must require ``len(_honesty_history) >= window`` before evaluating
    the rolling average.
    """
    orch = _make_orch(threshold=0.5, window=3, max_turns=5)

    # Two samples — both deeply below threshold — must NOT trip the
    # abort because the window has not been populated.
    msg, abort_turn, turn_history = _drive_loop(
        orch, [0.1, 0.05], tmp_path, claim="src/foo.py"
    )
    assert abort_turn is None, (
        f"Abort fired with only {len(orch._honesty_history)} sample(s) "
        f"(window=3): {msg}"
    )
    assert msg is None

    # Direct call after manually loading two samples — same precondition,
    # belt-and-braces against the loop helper masking the bug.
    orch2 = _make_orch(threshold=0.9, window=3)
    orch2._honesty_history = [0.0, 0.0]  # avg=0, but only 2 samples
    direct_msg = orch2._check_honesty_early_abort(
        turn_history=[],
        task_id="TASK-FIX-HEAB",
        worktree_path=tmp_path,
    )
    assert direct_msg is None
