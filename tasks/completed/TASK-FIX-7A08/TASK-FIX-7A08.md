---
id: TASK-FIX-7A08
title: Player prompt mandates Task-tool invocation for Phase 3/4/5 specialists
status: completed
created: 2026-04-24T18:30:00Z
updated: 2026-04-24T19:45:00Z
completed: 2026-04-24T19:45:00Z
completed_location: tasks/completed/TASK-FIX-7A08/
previous_state: in_review
state_transition_reason: "Task completion finalized via /task-complete"
organized_files:
  - TASK-FIX-7A08.md
priority: high
task_type: implementation
tags: [autobuild, player-prompt, task-tool, stall-resilience, specialist-invocation]
parent_review: TASK-REV-F3D7
feature_id: FEAT-F3D7
implementation_mode: task-work
wave: 1
conductor_workspace: autobuild-sdk-stall-resilience-phase2-w1-1
complexity: 4
depends_on: []
---

# Task: Player prompt mandates Task-tool invocation for Phase 3/4/5 specialists

## Description

The `coach_agent_invocations_stall` classifier (TASK-FIX-7A07) correctly detects
that the Player completes `task-work` mode tasks inline instead of invoking the
required specialists via the `Task` tool — but its remediation text references
`TASK-FIX-7A08` as the fix, which was never filed. This task files it.

**Root cause** (confirmed by TASK-REV-F3D7, see
[docs/reviews/bdd-acceptance-wired-up/forge-run-3-analysis.md](../../../docs/reviews/bdd-acceptance-wired-up/forge-run-3-analysis.md)):

The Player execution-protocol prompts describe phases narratively and even give
inline bash commands (`pytest tests/ -v`) that invite inline execution. The
`Task` tool is in `allowed_tools` ([agent_invoker.py:4745](../../../guardkit/orchestrator/agent_invoker.py#L4745))
but nothing in the prompt tells the Player when or why to call it.

This is a **specification defect in the prompt**. Same shape as the `anti-stub`
meta-pattern: when the spec doesn't name the deliverable, the agent substitutes
a plausible alternative. The model is doing exactly what the prompt tells it
to do — run tests inline.

## Acceptance Criteria

- [ ] All three execution-protocol prompts
      (`guardkit/orchestrator/prompts/autobuild_execution_protocol.md`,
      `_medium.md`, `_slim.md`) **mandate** `Task(subagent_type=<specialist>)`
      for Phase 3, Phase 4, and Phase 5, sourced from `phase_specialists.py`:
  - Phase 3: stack-specific specialist (or `GENERIC_PHASE_3_FALLBACK` when
    undetected)
  - Phase 4: `test-orchestrator`
  - Phase 5: `code-reviewer`
- [ ] Inline bash commands for tests (`pytest tests/ -v`, `npm test`, etc.) are
      **replaced** by prose directing the Player to invoke `test-orchestrator`
      via `Task`. Do NOT preserve inline-execution as a fallback — that is the
      defect.
- [ ] `_build_inline_implement_protocol` in
      [guardkit/orchestrator/agent_invoker.py](../../../guardkit/orchestrator/agent_invoker.py#L4479)
      (around lines 4479–4644) is updated so rendered prompts include the
      mandate language regardless of which template backs them.
- [ ] New test file `tests/orchestrator/test_player_prompt_mandate.py` asserts
      that for every non-`direct` task-type profile, the rendered prompt
      contains the literal substrings:
      `subagent_type="test-orchestrator"` and
      `subagent_type="code-reviewer"`.
- [ ] Existing test file `tests/orchestrator/test_stall_classification.py` is
      extended with a minimised replay fixture derived from forge-run-3's
      NFI-003 turn 1 and NFI-007 turn 1, asserting that **after the prompt
      change** (i.e. using a fixture that simulates a Player that followed the
      new mandate) the `agent_invocations_validation` block reports `3/3
      required` and the Coach does not reject.
- [ ] The remediation advice text at
      [autobuild.py:5062-5085](../../../guardkit/orchestrator/autobuild.py#L5062)
      continues to name this task ID as the remediation — no longer a dead
      reference once this task lands in `completed/`.
- [ ] Arch review (Phase 2.5) scores ≥60/100.
- [ ] Coverage on changed lines ≥80% (standard intensity).

## Implementation Notes

- **Source of truth for specialist names**: `phase_specialists.py`
  (`STACK_TO_PHASE_3_SPECIALIST`, `GENERIC_PHASE_3_FALLBACK`, and whatever
  constants name `test-orchestrator` and `code-reviewer`). The prompt must
  **consume** these, not hard-code strings. This preserves the single-source
  guarantee already used by Coach feedback at
  [coach_validator.py:713](../../../guardkit/orchestrator/quality_gates/coach_validator.py#L713).
- **Prompt structure**: preserve the Phase-N narrative headers and acceptance
  context; only *replace* the "how to execute" block with the Task-tool mandate.
  Something along these lines (example — adapt to each template's tone):

  > ### Phase 4: Testing
  >
  > Do NOT run `pytest` inline. Invoke the test specialist:
  >
  > ```
  > Task(subagent_type="test-orchestrator", description="Run tests for TASK-XXX", prompt="...")
  > ```
  >
  > Wait for the specialist's report before proceeding to Phase 5.

- **Fixture location**: `tests/fixtures/forge_run_3_replay/` (new). Keep the
  fixture minimal — just the two turn-1 transcripts and whatever state the
  classifier consumes.
- **Do not** relax the Coach's agent-invocations gate. The gate is correct; the
  Player prompt is the defect.

## Key References

- **Review report**: [docs/reviews/bdd-acceptance-wired-up/forge-run-3-analysis.md](../../../docs/reviews/bdd-acceptance-wired-up/forge-run-3-analysis.md)
- **Transcript**: [docs/reviews/bdd-acceptance-wired-up/forge-run-3.md](../../../docs/reviews/bdd-acceptance-wired-up/forge-run-3.md)
  (see lines 1095-1111, 1189-1205 for the classifier's remediation text that
  cites this task)
- **Phase specialists source of truth**: `guardkit/orchestrator/phase_specialists.py`
- **Coach feedback template** (for prompt tone consistency):
  `guardkit/orchestrator/quality_gates/coach_validator.py:650-734`
- **Sibling rule**: `.claude/rules/anti-stub.md` (anti-stub meta-pattern)
- **Graphiti seed** (to add post-completion): `guardkit__project_decisions` —
  *"Player execution-protocol prompts must mandate, not describe, Task-tool
  invocation for specialist phases"*
