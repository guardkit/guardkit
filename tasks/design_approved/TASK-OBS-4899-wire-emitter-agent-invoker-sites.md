---
autobuild:
  enabled: true
  max_turns: 5
  mode: tdd
complexity: 3
consumer_context:
- contract: EVENT_EMITTER
  driver: guardkit/orchestrator/instrumentation/emitter.py
  format_note: EventEmitter protocol (async emit/flush/close); CompositeBackend fan-out;
    NullEmitter default
  producer: TASK-INST-002 (completed 2026-03)
- contract: agent_invoker emit paths
  driver: guardkit/orchestrator/agent_invoker.py
  format_note: LLMCallEvent emit at :4443, ToolExecEvent emit at :4546 — built, test-proven,
    dead in production via NullEmitter
  producer: TASK-INST-005b / TASK-INST-005c (completed 2026-03)
created: 2026-07-09
decision_of_record: D-OBS-1 (OBS-1, dashboard ask A-4b)
dependencies: []
feature_id: FEAT-OBSC
id: TASK-OBS-4899
implementation_mode: task-work
priority: high
status: design_approved
task_type: feature
title: Wire the emitter through the three AgentInvoker construction sites and task-mode
  CLI
wave: 1
---

# TASK-OBS-4899: Wire the emitter through the three AgentInvoker construction sites and task-mode CLI

## Description

Close the one severed hop that keeps the entire 2026-03 instrumentation layer dead in
production. `AutoBuildOrchestrator` already holds a forwarded emitter
(`autobuild.py:1566`, TASK-INST-004) and uses it for lifecycle events, but never hands
it to `AgentInvoker` — all three production construction sites omit `emitter=`, so
`agent_invoker.py:1488` installs a `NullEmitter` and every `LLMCallEvent` /
`ToolExecEvent` is silently dropped.

Also give `guardkit autobuild task` (single-task mode) emitter parity: today only the
`feature` command builds a `CompositeBackend` (`cli/autobuild.py:1046-1048`); task mode
(`cli/autobuild.py:555-572`) passes nothing, so single-task runs emit no events at all
— including lifecycle events.

## Changes

1. Pass `emitter=self._emitter` at the three `AgentInvoker(...)` construction sites:
   - `guardkit/orchestrator/autobuild.py:2151` (feature-mode / existing-worktree path)
   - `guardkit/orchestrator/autobuild.py:2183` (normal-mode path)
   - `guardkit/orchestrator/autobuild.py:8230` (`--resume` path)
2. In `guardkit/cli/autobuild.py` task command (`def task` at `:344`,
   `AutoBuildOrchestrator(...)` at `:555-572`): build the same
   `CompositeBackend([JSONLFileBackend(events_dir=...)])` the feature command builds
   (`:1046-1048`), pass `emitter=`, and mirror the feature command's finally-block
   `flush()`/`close()` (`:1107-1117`). Events dir: `.guardkit/autobuild/<task_id>/` in
   the main repo (cwd-relative, NOT the worktree), matching the feature command's
   placement so events survive worktree pruning.

## Out of scope (documented, not silent)

- CoachValidator's independent-test path (`coach_validator.py:4741-4832`) bypasses
  `_invoke_with_role` and will still emit no `llm.call` events — known limitation
  recorded in the feature README; not funded by D-OBS-1.
- Attribution/data-quality fixes (model name, run_id joins, exit codes) are
  TASK-OBS-9F43.

## Acceptance Criteria

- [ ] AC-1: All three `AgentInvoker` construction sites in
      `guardkit/orchestrator/autobuild.py` pass `emitter=self._emitter`; a repo grep
      finds no production `AgentInvoker(` construction without an `emitter=` kwarg
      (docstring examples and the two unrelated same-named Protocol classes in
      `installer/core/lib/` excluded).
- [ ] AC-2: An end-to-end feature-mode run (integration test acceptable) produces
      `llm.call` events for both Player and Coach turns and `tool.exec` events for
      Bash tool use in `<repo>/.guardkit/autobuild/<FEAT>/events.jsonl` — asserting
      `count > 0` per event type, never merely "no failures"
      (absence-of-failure rule).
- [ ] AC-3: `guardkit autobuild task TASK-X` writes lifecycle + llm.call events to
      `.guardkit/autobuild/<task_id>/events.jsonl` with flush/close on exit, matching
      feature-mode behaviour.
- [ ] AC-4: Specialist invocations (Phase-4 test-orchestrator, Phase-5 code-reviewer)
      emit llm.call events without further wiring — they reuse the passed invoker via
      composition (`specialist_invocations.py:316`); pinned by a test.
- [ ] AC-5: Zero behaviour change when no emitter is configured (NullEmitter default
      preserved); existing instrumentation tests stay green.

## Test Strategy

Extend `tests/orchestrator/instrumentation/` (the capturing-emitter pattern —
`NullEmitter(capture=True)` injected via the `_make_invoker` helper — in
`test_llm_call_events.py:83-87` and first exercised at `:150` is the precedent). Add a construction-site seam test
asserting the emitter instance held by `AutoBuildOrchestrator` is the same object
received by `AgentInvoker` (identity, not equality — the CLI7 shared-acquisition
lesson, `.claude/rules/cli-wrapper-shares-client-acquisition-path.md`).