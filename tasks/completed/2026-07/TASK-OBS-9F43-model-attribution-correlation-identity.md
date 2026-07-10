---
autobuild:
  enabled: true
  max_turns: 5
  mode: tdd
complexity: 4
created: 2026-07-09
decision_of_record: D-OBS-1 (OBS-1) + WS4 Appendix A fields 4-5 (artifact identity,
  correlation ids)
dependencies:
- TASK-OBS-4899
feature_id: FEAT-OBSC
id: TASK-OBS-9F43
implementation_mode: task-work
priority: high
status: completed
task_type: feature
title: Real model attribution and joinable correlation identity on instrumentation
  events
wave: 2
---

# TASK-OBS-9F43: Real model attribution and joinable correlation identity on instrumentation events

## Description

With the emitter wired (TASK-OBS-4899), the events flow — but they are not yet
flywheel inputs. Four attribution defects, all verified 2026-07-09:

1. **Model falls back to the literal `"default"`** (`agent_invoker.py:4431`,
   `model=model or "default"`) whenever no `--model`/`--coach-model` flag was given —
   the common cloud-run case. The real model is available at that exact point:
   the resolved `model` local (`:4001-4009`) when flags were set, and the
   server-resolved `AssistantMessage.model` field on the raw stream
   (`response_messages` is already a parameter of `_emit_llm_call_event`, `:4389`;
   `ResultMessage.model_usage` is keyed by model name) when they weren't.
2. **Correlation identity is unwired**: `_run_id`, `_current_attempt`,
   `_current_agent_role`, `_prompt_profile` are read via getattr fallbacks
   (`agent_invoker.py:4413-4419`, `:4521-4527`) but never assigned anywhere — so
   run_id is the synthetic `run-{id(self)}`, attempt is always 1, tool-exec role is
   always `"player"`, and prompt_profile is always the fallback.
3. **Lifecycle events cannot join llm.call events**: each lifecycle emit fabricates
   its own timestamped run_id (`autobuild.py:5773`, `:5811`, `:5841`) — even
   task.started and task.completed for the same run carry different run_ids.
4. **ToolExecEvent fidelity**: the only call site hardcodes `exit_code=0` and
   `stderr_tail=""` (`agent_invoker.py:8481`) instead of extracting them from the
   ToolResultBlock; and LLMCallEvent's `ttft_ms` / `prefix_cache_hit` /
   `context_bytes` are never populated (acceptable to leave unpopulated — but
   exit_code/stderr are not).

WS4 Appendix A makes fields 4 (artifact identity: model/checkpoint id) and 5
(correlation ids) mandatory for a session to count as a flywheel input; without this
task, wired capture is still dark data.

## Changes

1. Model: prefer the server-resolved model from the raw message stream
   (`AssistantMessage.model` / `ResultMessage.model_usage`) when available; fall back
   to the resolved `model` local; only then the literal `"default"`. Applies to both
   Player and Coach roles (Coach resolution via `self._coach_model_name`, `:4001-4009`).
2. One run_id per orchestrator run: mint once (orchestrator level), thread to
   `AgentInvoker` (assign `self._run_id`) and to the three lifecycle emitters in
   `autobuild.py` so task.started/completed/failed and llm.call/tool.exec all share it.
3. Assign `self._current_attempt` and `self._current_agent_role` at each
   `_invoke_with_role` entry (turn number and player/coach/specialist role are both in
   scope there); assign `self._prompt_profile` from the active profile if one is
   configured, else keep the documented fallback.
4. Extract real `exit_code` and `stderr_tail` from the ToolResultBlock at
   `agent_invoker.py:8478-8486`; keep SecretRedactor application unchanged.

## Acceptance Criteria

- [ ] AC-1: In a run with no `--model` flag on the SDK harness, emitted `llm.call`
      events carry the server-resolved model id (e.g. `claude-*`), not `"default"`;
      with `--model`/`--coach-model` set, Player and Coach events carry their
      respective configured names. The literal `"default"` appears only when neither
      source is available, and a test pins that case as the exception, not the norm.
- [ ] AC-2: All events of one run (lifecycle + llm.call + tool.exec) share a single
      run_id; a test joins task.started→llm.call→task.completed by run_id.
- [ ] AC-3: `attempt` reflects the actual turn number (>1 on multi-turn runs);
      tool.exec `agent_role` is correct for coach-turn tool use.
- [ ] AC-4: ToolExecEvent carries the real exit_code (a failing Bash call yields
      non-zero) and a non-empty stderr_tail when stderr was produced — both redacted
      through the existing SecretRedactor path.
- [ ] AC-5: LangGraph-harness runs (the default substrate since TASK-HMIG-011) get
      the same attribution; where the substrate exposes no server-resolved model, the
      resolved/configured name is used and the gap is documented — never a silent
      `"default"` regression.

## Test Strategy

Unit tests against `_emit_llm_call_event` / `_emit_tool_exec_event` with synthetic
message streams carrying `AssistantMessage.model`; integration assertion on run_id
join across an events.jsonl produced by a stub run. Absence-of-failure discipline:
every "carries X" AC asserts the positive value, never just absence of "default".

## Operator build addendum (2026-07-10)

Built via `/feature-build FEAT-OBSC` on the **SDK harness** (`GUARDKIT_HARNESS=sdk`;
the default LangGraph harness is unusable on this machine — see the feature-level
build notes in the cluster README). Coach approved in 1 turn, but two post-build
operator fixes were required and committed on top of the autobuild checkpoints:

1. **`f6944681` (test-side, brittle tests)** — the AC-2/AC-3/AC-4/AC-5 tests in
   `tests/orchestrator/instrumentation/test_model_attribution_and_correlation.py`
   were sync and called the *fire-and-forget* emit helpers (`_emit_llm_call_event`
   / `_emit_tool_exec_event`, which schedule via `loop.create_task()` and silently
   skip when no loop is running — the documented TASK-INST-005b contract) with no
   running event loop, so **zero events were captured**. Made them `async` + a
   short `await asyncio.sleep()`; the two `TestRunIDCorrelation` tests also passed
   wrong `AutoBuildOrchestrator` kwargs — corrected to `repo_root`/`max_turns`/
   `sdk_timeout` + patched `WorktreeManager`, kept sync (the lifecycle emits use a
   blocking `asyncio.run()`). **Production attribution/correlation code was correct.**

2. **`cc416cd2` (PRODUCTION bug — regression introduced by this task)** —
   `_emit_task_failed` and `_emit_task_completed` built `TaskFailedEvent` /
   `TaskCompletedEvent` with `attempt=len(turn_history)`, which is `0` on an early
   failure and violates the events' `ge=1` schema constraint, raising
   `ValidationError` on the finalize path. This silently regressed **12 pre-existing
   tests in `tests/orchestrator/instrumentation/test_orchestrator_events.py`**
   (green on `main`, unmodified by this feature) that **no task-scoped Phase-4 gate
   ran** — a live instance of the `per-task-green-is-not-feature-green` gate-aperture
   class. Fixed by clamping `attempt = max(1, len(...))`. Verified green post-fix:
   instrumentation 509, orchestrator/worktrees/templates 2582, cli 148.