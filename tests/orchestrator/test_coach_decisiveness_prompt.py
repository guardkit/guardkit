"""TASK-FIX-COACHSCHEMA (Path 1B, re-scoped) — Coach decisiveness + self-check prompt block.

Pins the "## Verification Budget — Be Decisive" block into the rendered Coach
prompt (``AgentInvoker._build_coach_prompt``). The block is a prompt-only nudge
that targets the two observed FEAT-AOF Coach failure modes:

* **run-13 TIMEOUT (primary)** — gemma4-coach ran as an agent for ~39 min and
  never converged on a verdict (SDK timeout). The block sets a decisive /
  efficient operating posture (verify each AC once, then STOP and emit) BEFORE
  the responsibilities list, where it can curb over-exploration from the start.
* **run-12 SCHEMA (secondary)** — when the Coach did emit, the block sometimes
  lacked required fields. The closing self-check reinforces the three required
  fields (``task_id`` / ``turn`` / ``decision``).

This is a *structural* test: it asserts the guidance reaches the prompt. The
*behavioural* claim (that gemma4-coach actually converges + emits) is the
falsifier for a real autobuild run, NOT this unit test — and deliberately so,
because a single-shot smoke would not represent the tool-bound agentic Coach
(see ``docs/research/dgx-spark/grammars/README.md`` run-13 finding).
"""

from __future__ import annotations

from pathlib import Path

from guardkit.orchestrator.agent_invoker import AgentInvoker


def _build_invoker(worktree: Path) -> AgentInvoker:
    invoker = AgentInvoker.__new__(AgentInvoker)
    invoker.worktree_path = worktree
    return invoker


def _render(worktree: Path) -> str:
    return _build_invoker(worktree)._build_coach_prompt(
        task_id="TASK-DEC-001",
        turn=2,
        requirements="Implement the thing per the acceptance criteria.",
        player_report={"files_modified": [], "files_created": []},
    )


class TestCoachDecisivenessBlock:
    """The decisiveness + self-check block must be rendered into every Coach prompt."""

    def test_decisiveness_section_present(self, tmp_path: Path) -> None:
        prompt = _render(tmp_path)
        assert "## Verification Budget — Be Decisive" in prompt

    def test_targets_run13_timeout_with_stop_condition(self, tmp_path: Path) -> None:
        prompt = _render(tmp_path)
        # The load-bearing decisiveness levers (curb the run-13 over-exploration).
        assert "never emits a verdict is a FAILURE" in prompt
        assert "Verify each acceptance criterion ONCE" in prompt
        assert "Do not re-read files you have already seen or re-run passing tests" in prompt
        assert "STOP investigating and emit your verdict" in prompt
        assert "More deliberation adds latency, not certainty" in prompt

    def test_does_not_invite_false_approve(self, tmp_path: Path) -> None:
        prompt = _render(tmp_path)
        # "Decisive" must never read as "skip verification" — the guardrail
        # against a fast-but-wrong approval must be present verbatim.
        assert "Decisive means efficient, never lazy" in prompt
        assert "still verify EACH criterion and run the tests" in prompt
        assert "A false approve is the worst outcome" in prompt

    def test_reinforces_three_required_fields(self, tmp_path: Path) -> None:
        prompt = _render(tmp_path)
        # The run-12 schema self-check: the 3 hard-required fields (the parser +
        # COACH_DECISION_SCHEMA contract).
        assert (
            'task_id (string), turn (integer), decision ("approve" or "feedback")'
            in prompt
        )
        assert "If any is missing, add it, then emit" in prompt

    def test_block_precedes_decision_format(self, tmp_path: Path) -> None:
        # Posture-setting placement: the budget block must appear BEFORE the
        # "## Your Responsibilities" / "## Decision Format" sections so it shapes
        # behaviour from the start rather than as a late gate.
        prompt = _render(tmp_path)
        budget_idx = prompt.index("## Verification Budget — Be Decisive")
        responsibilities_idx = prompt.index("## Your Responsibilities")
        decision_idx = prompt.index("## Decision Format")
        assert budget_idx < responsibilities_idx < decision_idx
