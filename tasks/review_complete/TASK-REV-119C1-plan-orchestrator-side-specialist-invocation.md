---
id: TASK-REV-119C1
title: "Plan: Orchestrator-side specialist invocation for AutoBuild Phases 4 and 5"
status: review_complete
created: 2026-04-25T00:00:00Z
updated: 2026-04-25T07:48:00Z
previous_state: backlog
state_transition_reason: "Decision checkpoint resolved [I]mplement; FEAT-AB59 generated with 7 subtasks across 5 waves"
priority: high
task_type: review
review_results:
  mode: decision
  depth: standard
  findings_count: 4
  recommendations_count: 7
  decision: implement
  feature_id: FEAT-AB59
  report_path: docs/reviews/orchestrator-side-specialist-invocation/TASK-REV-119C1-review-report.md
  feature_folder: tasks/backlog/orchestrator-side-specialist-invocation/
tags: [autobuild, planning, orchestrator, specialist-invocation, phases-4-5, F4A1-followup]
related_to:
  - TASK-REV-F4A1
  - TASK-DIAG-F4A2
  - TASK-FIX-F4A3
  - TASK-FIX-7A07
  - TASK-FIX-7A08
clarification:
  context_a:
    timestamp: 2026-04-25T00:00:00Z
    decisions:
      review_focus: architecture_and_risk
      tradeoff_priority: quality
      test_dependency_choice: stub_sdk_harness
      complementary_signal: task_diag_f4a2_preservation
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Plan — Orchestrator-side specialist invocation for AutoBuild Phases 4 and 5

## Problem

TASK-REV-F4A1 (review of forge-run-4 / jarvis-FEAT-J002-run-2 / forge-run-3 /
forge-run-5) confirmed via Hypotheses H-B + H-G that the Player LLM in the
AutoBuild SDK subprocess has a strong inference-time prior to complete test
execution and code review **inline** via `Bash`/`Edit`/`Write` rather than
delegating to `test-orchestrator` and `code-reviewer` specialists via the
`Task` tool.

Three fresh runs across two repos (forge-run-3, forge-run-5,
jarvis-FEAT-002-run-2) showed **zero** `Task(subagent_type=...)` invocations
despite the prompt explicitly mandating them. TASK-FIX-7A08 attempted to fix
this with prompt wording and was reverted (commits `7f8f14ba`, `86688fc6`,
`a8789317`) because three independent runs proved the **prompt-class
fix-class is insufficient**.

The Coach's `agent_invocations` gate (TASK-FIX-7A07) correctly fires on the
missing phases, but no amount of Player-side instruction has changed Player
behaviour.

## Proposed solution direction (locked in by user)

Remove the Player's discretion to skip specialists by having
`AutoBuildOrchestrator` invoke them directly. After the Player completes
Phase 3 (implementation in inline `Bash`/`Edit`, which the Player demonstrably
DOES execute reliably), the orchestrator itself invokes:

- `test-orchestrator` (Phase 4) via `AgentInvoker` with its own
  `ClaudeAgentOptions` and SDK session.
- `code-reviewer` (Phase 5) via `AgentInvoker` with its own
  `ClaudeAgentOptions` and SDK session.

The Phase-3 specialist (e.g. `python-api-specialist`) remains optionally
Player-invoked, with orchestrator fallback if the Player skips it (deferred
— out of scope here).

The producer-side `agent_invocations_validation` gate at
`agent_invoker.py:5577-5620` is updated to credit orchestrator-invoked
specialists the same way it credits Player-invoked ones.

## Constraints (locked in by user)

- Do **NOT** modify TASK-FIX-7A07's classifier (the diagnostic is sound; it
  correctly identifies missing phases when they are missing).
- Do **NOT** re-attempt prompt-class fixes (refuted by F4A1).
- Pre-merge behavioural verification test MUST be deterministic — built
  against a **stub-SDK harness** that records orchestrator-side
  invocations. (Q1 decision: Option B.)
  - Test must pass in CI without a live SDK or Anthropic API call.
  - TASK-DIAG-F4A2's preservation infrastructure is preserved as the
    **complementary** slow signal (e.g. nightly canonical-task run with
    `GUARDKIT_AUTOBUILD_PRESERVE_DEBUG=1` asserting `messages.jsonl`
    shows orchestrator-issued specialist sessions).
- Acceptance test for the feature:
  - `jarvis-FEAT-J002-run-N` completes ≥ 18/23 tasks (vs. pre-phase-2
    baseline 14/23 — feature must restore AND improve).
  - `forge-FEAT-FORGE-002-run-N` completes ≥ 10/11 Wave-2 tasks (vs.
    post-phase-1 0/3).
- Backwards compatibility: tasks with `implementation_mode: direct` must
  still skip Phase 4/5 specialist invocation (existing behaviour).

## Scope (in)

- New module: `guardkit/orchestrator/specialist_invocations.py` housing the
  three orchestrator-side specialist runners (clean separation from
  `AgentInvoker`'s existing surface).
- Turn-loop modification in `guardkit/orchestrator/autobuild.py`: insert
  post-Phase-3 orchestrator invocations of `test-orchestrator` and
  `code-reviewer` before evaluating Coach's gate.
- Extend `AgentInvoker` with per-specialist invocation helpers; ensure each
  specialist gets its own SDK session with appropriate `allowed_tools`.
- Extend `agent_invocations_validation` (agent_invoker.py:5577-5620) to
  credit orchestrator-invoked specialists.
- Trim `autobuild_execution_protocol{,_medium,_slim}.md`: keep specialist
  guidance as a soft recommendation for Player Phase 3 only; remove any
  remaining Phase 4/5 instructions to the Player.
- New tests:
  - `tests/orchestrator/test_orchestrator_specialist_invocation.py` (unit).
  - `tests/integration/test_autobuild_phase_4_5_orchestration.py`
    (end-to-end with stub-SDK harness).

## Scope (out)

- Phase 3 specialist invocation orchestration (deferred — Player reliably
  implements when given a plan; only Phase 4/5 fail).
- Removing `Bash` from `allowed_tools` (H-G(a) — orthogonal alternative,
  not pursued because `Bash` is needed for legitimate Phase 1/2 ops).
- Coach changes (Coach already correctly reads the gate block).
- Stack-template changes (specialist resolution already comes from
  `phase_specialists.py`, which is unchanged).

## Review focus (Q2 decision: Architecture + risk only)

The "what to build" is locked in. This review must concentrate on the four
high-leverage open architecture/risk questions:

### 1. Session lifecycle

- Does each specialist get its own `ClaudeAgentOptions`? What
  `allowed_tools` does each get?
- Sequential or parallelisable? (Likely sequential —
  `code-reviewer` needs `test-orchestrator` results — but verify.)
- Where does the new SDK session live in the worktree's resource tree?
- Timeout behaviour per specialist.

### 2. Gate credit path

- How does `agent_invocations_validation` get populated from
  orchestrator-side invocations rather than Player-emitted phase markers?
- Risk of **double-counting** if Player ALSO emits Phase 4/5 markers
  from the leftover prompt fragments — mitigation strategy?
- Schema for the gate's `phase_3 / phase_4 / phase_5` records — do
  orchestrator-invoked entries differ structurally?

### 3. `implementation_mode: direct` contract

- Does `direct` skip orchestrator invocation **entirely** or skip only
  the gate?
- Affects what the validation update at `agent_invoker.py:5577-5620`
  actually has to do.

### 4. Specialist failure handling

- Does a failing `test-orchestrator` block the Coach turn, get reported
  as a Player failure, or trigger an orchestrator-level retry?
- Test artefact propagation: `test-orchestrator`'s output must be
  visible to `code-reviewer` AND to Coach.
- Partial-completion rollback semantics if Phase 4 succeeds but Phase 5
  fails mid-stream.

## Acceptance criteria for this review task

- [ ] Decision presented for each of the four review-focus questions
      above, with rationale.
- [ ] Subtask breakdown with dependencies and parallel-group assignment.
- [ ] Stub-SDK harness design documented (interface, recording
      mechanism, what assertions the pre-merge test makes).
- [ ] `implementation_mode: direct` backwards-compat contract specified
      in writing.
- [ ] Mandatory diagrams (data flow, integration contract, task
      dependency graph) generated in IMPLEMENTATION-GUIDE.md if
      [I]mplement is chosen.
- [ ] §4 Integration Contracts section if cross-task data dependencies
      exist between subtasks.

## References

- Review report: `docs/reviews/bdd-acceptance-wired-up/forge-run-4-analysis.md`
- Review task: `tasks/review_complete/TASK-REV-F4A1-analyse-forge-run-4-post-phase2-failure.md`
- TASK-DIAG-F4A2 preservation infrastructure:
  `guardkit/orchestrator/sdk_debug.py`
- Sibling follow-ups: TASK-DIAG-F4A2 (completed), TASK-FIX-F4A3
  (pollution-detector resume hygiene)
- Reverted prompt-class fix attempts: commits `7f8f14ba`, `86688fc6`,
  `a8789317` (TASK-FIX-7A08 lifecycle).
- Producer-side validation gate: `agent_invoker.py:5577-5620`

## Notes

- This is the third TASK-REV-F4A1 follow-up (after TASK-DIAG-F4A2 and
  TASK-FIX-F4A3).
- Q1 (test dependency): Option B — stub-SDK harness, with TASK-DIAG-F4A2
  preservation as complementary nightly signal.
- Q2 (review focus): Option A — architecture + risk only.
