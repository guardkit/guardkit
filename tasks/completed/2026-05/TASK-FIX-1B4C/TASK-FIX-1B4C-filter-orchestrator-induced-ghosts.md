---
id: TASK-FIX-1B4C
title: "Layer 3': Filter orchestrator-induced state-bridge moves out of post-turn git enrichment"
status: completed
created: 2026-05-06T00:00:00Z
updated: 2026-05-06T17:27:00Z
completed: 2026-05-06T17:27:00Z
completed_location: tasks/completed/2026-05/TASK-FIX-1B4C/
previous_state: in_review
state_transition_reason: "All 7 ACs satisfied; quality gates green (5 new + 36 existing related tests). Pair-ready with TASK-FIX-1B4A."
priority: high
task_type: implementation
tags: [autobuild, state-bridge, agent-invoker, union-merge, layer-3-prime, preventative]
parent_review: TASK-REV-1B452
feature_id: FEAT-1B452
implementation_mode: task-work
wave: 1
conductor_workspace: honesty-fix-wave1-2
complexity: 5
test_results:
  status: passed
  coverage: null
  last_run: 2026-05-06T17:25:00Z
  new_tests: 5
  existing_tests_pass: 36
---

# Task: Layer 3' — Filter orchestrator-induced ghost paths at union-merge

## Description

Stop the FEAT-FFC3 false-fail at the source: filter out paths that state_bridge moved during the turn from the post-turn `git diff --name-only` enrichment in `_create_player_report_from_task_work`. The ghost path never reaches the Coach.

This is Layer 3' of three from the [v2 review](../../../.claude/reviews/TASK-REV-1B452-review-report.md), replacing the (incorrect) Layer 3 from v1. Independently load-bearing — alone, it closes the FFC3 reproducer. Pair with TASK-FIX-1B4A (Layer 1) for defence-in-depth.

## Context

**Why this layer exists** (validated in v2 review §C4 + §3):

The `tasks/backlog/...` ghost path enters `report["files_modified"]` at [`agent_invoker.py:2796-2797`](../../../guardkit/orchestrator/agent_invoker.py):

```python
report["files_modified"] = sorted(list(original_modified | git_modified))
```

`git_modified` comes from `git diff --name-only <baseline>` where `baseline` was captured **before** state_bridge mutated the worktree. Without `-M`/rename detection, `shutil.move` shows the source path in the diff output and the destination in `git ls-files --others`. The union-merge attributes the orchestrator-induced ghost path to the Player, who never put it there.

**Why v1's Layer 3 was wrong**: v1 proposed injecting the canonical path into the Player's prompt context. But the Player never put `tasks/backlog/...` in the report — the orchestrator's union-merge did. Changing the Player's prompt would not affect the union-merge's output.

**The correct fix**: state_bridge persists every move it performs to a per-task `.guardkit/autobuild/{task_id}/state_transitions.json`. The orchestrator subtracts these paths from `git_modified` before the union-merge.

## Acceptance Criteria

- [ ] **AC-C1**: `TaskStateBridge.transition_to_design_approved` (or its underlying `_move_task_to_state` helper) persists the move to `.guardkit/autobuild/{task_id}/state_transitions.json` on success. The persisted record contains `{"task_id": str, "pre_path": str, "post_path": str, "timestamp": str (ISO 8601), "kind": "design_approved_transition"}`. New entries append; existing entries are preserved.
- [ ] **AC-C2**: `TaskStateBridge` exposes a public method `orchestrator_induced_paths_for(task_id) -> Set[str]` that reads `.guardkit/autobuild/{task_id}/state_transitions.json` and returns the set of `pre_path` values for that task. Returns empty set when the file does not exist (fail-open) or is malformed (logged warning, fail-open).
- [ ] **AC-C3**: `AgentInvoker._create_player_report_from_task_work` filters orchestrator-induced paths from the union-merged file lists. After the existing union-merge at line 2797, before the validity-filter at line 2803, subtract `state_bridge.orchestrator_induced_paths_for(task_id)` from `report["files_modified"]` and `report["files_created"]`.
- [ ] **AC-C4**: When the filter fires, `logger.info` emits a structured message: `"Filtered N orchestrator-induced ghost path(s) for {task_id}: {paths}"`. This is for observability/forensics.
- [ ] **AC-C5**: When `state_transitions.json` does not exist, the filter is a no-op — behaviour matches current (fail-open). No exception propagates from `orchestrator_induced_paths_for`.
- [ ] **AC-C6**: All five regression tests in the new module `tests/unit/test_orchestrator_induced_path_filter.py` pass:
  - `test_state_bridge_persists_transition_record` — calling `transition_to_design_approved` writes a transition entry.
  - `test_orchestrator_induced_paths_filtered_from_files_modified` — a real worktree fixture with a state-bridge move + git diff confirms `tasks/backlog/...` is filtered out of the final Player report.
  - `test_filter_no_op_when_state_transitions_json_missing` — fixture without the file, filter is a no-op, no exception.
  - `test_filter_no_op_when_state_transitions_json_malformed` — fixture with corrupt JSON, filter is a no-op, warning logged.
  - `test_multiple_state_bridge_moves_in_same_turn_all_filtered` — two transition entries, both pre-paths filtered.
- [ ] **AC-C7**: Existing tests in `tests/unit/test_state_bridge.py` and tests under the agent_invoker suite still pass with no regression.

## Implementation Notes

**Files to modify**:

1. `guardkit/tasks/state_bridge.py` (~30 lines added):
   - In `_move_task_to_state` (or `transition_to_design_approved` directly), after `shutil.move` succeeds, append a record to `<repo_root>/.guardkit/autobuild/{task_id}/state_transitions.json`. Create the directory if needed; create the file if it doesn't exist; otherwise append. Use atomic write (write to `.tmp` then rename).
   - Add public `orchestrator_induced_paths_for(task_id: str) -> Set[str]` method. Read the JSON; return `{record["pre_path"] for record in records}`. Catch `FileNotFoundError` → empty set. Catch `JSONDecodeError` → warning + empty set.

2. `guardkit/orchestrator/agent_invoker.py` (~15 lines modified):
   - In `_create_player_report_from_task_work` after the union-merge at line 2797:
     ```python
     # TASK-FIX-1B4C: filter orchestrator-induced ghost paths
     try:
         from guardkit.tasks.state_bridge import TaskStateBridge
         induced = TaskStateBridge.orchestrator_induced_paths_for(
             task_id, repo_root=self.worktree_path
         )
         if induced:
             before_modified = set(report["files_modified"])
             before_created = set(report["files_created"])
             report["files_modified"] = sorted(set(report["files_modified"]) - induced)
             report["files_created"] = sorted(set(report["files_created"]) - induced)
             filtered_paths = (before_modified | before_created) & induced
             if filtered_paths:
                 logger.info(
                     f"Filtered {len(filtered_paths)} orchestrator-induced "
                     f"ghost path(s) for {task_id}: {sorted(filtered_paths)}"
                 )
     except Exception as e:  # noqa: BLE001 — never block report generation
         logger.warning(f"Ghost-path filter failed for {task_id}: {e}")
     ```

3. `tests/unit/test_orchestrator_induced_path_filter.py` (new, ~200 lines):
   - 5 tests per AC-C6.
   - Use real subprocess git for the realism-fixture test (`test_orchestrator_induced_paths_filtered_from_files_modified`). The other tests can mock the JSON file directly.

**Atomicity and concurrency**:

- The append-to-state_transitions.json operation should be atomic. Recommended: lock-free single-writer (each task has its own subdirectory under `.guardkit/autobuild/{task_id}/`, so there's no cross-task contention on the file).
- For multi-turn safety: each turn appends; the file accumulates across turns within a task. `orchestrator_induced_paths_for` returns the union of all pre-paths recorded for the task. This is correct: if a path was state-bridged in turn 1, it remains a ghost in turn 2's git diff (still missing from disk; still `tasks/backlog/...`).

**Why a static method on TaskStateBridge instead of an instance method**: the orchestrator at line 2796-2797 doesn't have a `TaskStateBridge` instance handy. A static method that reads the persisted JSON given a `repo_root` and `task_id` is cleaner than instantiating a bridge just to read the file.

## Notes

- This is the **defence-in-depth preventative** fix. Layer 1 (TASK-FIX-1B4A) is the consumer-side resolution; Layer 3' is the source-side filter.
- Both must ship before next autobuild attempt. They are independent in code (1B4A → state_bridge.canonical_path_for + coach_*; 1B4C → state_bridge.orchestrator_induced_paths_for + agent_invoker). Both add to `state_bridge.py`; merge order is whichever lands first; the second resolves a small textual conflict at the bottom of the public-method block.
- Risk assessment in v2 review report §AC-8 "Layer 3' risk: filter scope creep" with four mitigations.
- Per FEAT-1B452 Wave-1 ship criteria, this task is required for next autobuild attempt.
