---
id: TASK-INST-013
title: Wire EventEmitter into CLI and FeatureOrchestrator
task_type: feature
parent_review: TASK-REV-2FE2
feature_id: FEAT-INST
wave: 5
implementation_mode: task-work
complexity: 3
dependencies:
- TASK-INST-002
- TASK-INST-004
autobuild:
  enabled: true
  max_turns: 5
  mode: tdd
consumer_context:
- task: TASK-INST-002
  consumes: EVENT_EMITTER
  framework: JSONLFileBackend + CompositeBackend
  driver: guardkit.orchestrator.instrumentation.emitter
  format_note: Create CompositeBackend with JSONLFileBackend; pass as emitter to FeatureOrchestrator
- task: TASK-INST-004
  consumes: LIFECYCLE_EVENTS
  framework: AutoBuildOrchestrator + FeatureOrchestrator accept emitter param
  driver: guardkit.orchestrator.autobuild, guardkit.orchestrator.feature_orchestrator
  format_note: Both orchestrators default to NullEmitter; pass real emitter to activate
status: completed
completed: 2026-03-08T00:00:00Z
---

# Task: Wire EventEmitter into CLI and FeatureOrchestrator

## Description

The instrumentation backends (TASK-INST-002) and orchestrator integration (TASK-INST-004) are merged, but the CLI entry point does not create or pass a real emitter. All runs currently use `NullEmitter` (no-op), meaning no events are captured. This task connects the plumbing so that `guardkit autobuild` runs emit structured events to disk by default.

## Scope

This task ONLY modifies:
- `guardkit/cli/autobuild.py` — the `feature` command function (~line 733)
- `guardkit/orchestrator/feature_orchestrator.py` — ensure emitter is passed through to `AutoBuildOrchestrator` instances it creates

It does NOT:
- Change event schemas or emitter backends
- Add new CLI flags (instrumentation is always-on via JSONL; zero cost when not analysed)
- Modify `AutoBuildOrchestrator` (already accepts emitter via TASK-INST-004)

## Requirements

### CLI Emitter Creation

In the `feature` command in `guardkit/cli/autobuild.py`, before creating `FeatureOrchestrator`:

```python
from guardkit.orchestrator.instrumentation.emitter import (
    CompositeBackend,
    JSONLFileBackend,
)

events_dir = Path(".guardkit/autobuild") / feature_id
emitter = CompositeBackend(backends=[JSONLFileBackend(events_dir=events_dir)])
```

Pass `emitter=emitter` to the `FeatureOrchestrator` constructor.

### FeatureOrchestrator Pass-Through

Ensure `FeatureOrchestrator` passes its `emitter` to each `AutoBuildOrchestrator` it creates for individual tasks. The emitter parameter already exists on both constructors (TASK-INST-004); this task ensures the FeatureOrchestrator forwards it rather than letting AutoBuildOrchestrator default to NullEmitter.

### Emitter Lifecycle

- `emitter.flush()` should be called after orchestration completes (success or failure)
- `emitter.close()` should be called in a `finally` block to release resources
- Errors during flush/close should be logged but not propagate to the CLI exit code

### Events Directory

- Events are written to `.guardkit/autobuild/{feature_id}/events.jsonl`
- Directory is created automatically by `JSONLFileBackend` on first write
- No cleanup or rotation — files accumulate for offline analysis

## Acceptance Criteria

- [x] `guardkit autobuild feature FEAT-XXX` creates a `CompositeBackend` with `JSONLFileBackend`
- [x] Events directory is `.guardkit/autobuild/{feature_id}/`
- [x] `FeatureOrchestrator` receives the emitter and forwards it to `AutoBuildOrchestrator`
- [x] `task.started`, `task.completed`, `task.failed` events appear in `events.jsonl` after a run
- [x] `wave.completed` events appear in `events.jsonl` after a multi-task run
- [x] `emitter.flush()` called after orchestration (success or failure)
- [x] `emitter.close()` called in finally block
- [x] Flush/close errors are logged, not raised
- [x] Existing CLI tests pass without modification (NullEmitter still used in test paths)
- [x] New test verifies emitter is created and passed through

## File Location

Changes to:
- `guardkit/cli/autobuild.py` (feature command function, ~line 731-749)
- `guardkit/orchestrator/feature_orchestrator.py` (pass emitter to AutoBuildOrchestrator)

## Test Location

`tests/orchestrator/instrumentation/test_cli_emitter_wiring.py`

## Implementation Summary

### Changes Made

1. **`guardkit/cli/autobuild.py`**: Added import for `CompositeBackend` and `JSONLFileBackend`. In the `feature` command, creates emitter before `FeatureOrchestrator`, passes `emitter=emitter`, and manages lifecycle with `flush()`/`close()` in a `finally` block.

2. **`guardkit/orchestrator/feature_orchestrator.py`**: Added `emitter=self._emitter` to the `AutoBuildOrchestrator(...)` constructor call so the emitter is forwarded to each task orchestrator.

3. **`tests/orchestrator/instrumentation/test_cli_emitter_wiring.py`**: 14 tests covering emitter creation, pass-through, lifecycle management, error handling, and CLI wiring verification.

### Test Results

- 436/436 instrumentation tests pass
- 14 new tests all pass
- 0 regressions
