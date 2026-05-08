---
id: TASK-FIX-CC-COND
title: _detect_source_file_contention false-positives on shared-worktree git diff
status: completed
created: 2026-05-08T00:00:00Z
updated: 2026-05-08T00:00:00Z
completed: 2026-05-08T00:00:00Z
previous_state: in_review
completed_location: tasks/completed/TASK-FIX-CC-COND/
priority: high
tags: [coach-validator, parallel-wave, conditional-approval, false-positive, autobuild, shared-worktree]
parent_review: TASK-REV-CC40 (study-tutor)
parent_review_path: /Users/richardwoollcott/Projects/appmilla_github/study-tutor/.claude/reviews/TASK-REV-CC40-review-report.md
related_tasks:
  - TASK-FIX-CC-BDD     # sibling; same FEAT-39E1 post-mortem
  - TASK-FIX-A7B2       # introduced _detect_source_file_contention
  - TASK-ABFIX-005      # introduced parallel_contention conditional approval
complexity: 5
estimated_effort: 4-6 hours
---

# Task: `_detect_source_file_contention` false-positives on shared-worktree git diff

## Context

**From review:** [TASK-REV-CC40 (study-tutor)](/Users/richardwoollcott/Projects/appmilla_github/study-tutor/.claude/reviews/TASK-REV-CC40-review-report.md) — finding F-3.

`_detect_source_file_contention` ([coach_validator.py:618–666](../../guardkit/orchestrator/quality_gates/coach_validator.py#L618-L666)) determines whether a `parallel_contention` failure is *real* (peer tasks edited overlapping files) vs *transient* (worth a retry, eligible for conditional approval). The function reads:

```python
own = set(task_work_results.get("files_created", []) or [])
own.update(task_work_results.get("files_modified", []) or [])
```

But in a shared-worktree autobuild, those fields are populated by **`agent_invoker`'s worktree-wide `git diff`**, not by what the player explicitly authored. From the FEAT-39E1 failure log:

> `Git detection added: 30 modified, 5 created files for TASK-NATS-PH1-006`

That detection is a `git diff` over the entire worktree at the moment the task's player turn finishes — which includes commits and edits from **every peer task** running in the same wave. So `task_work_results.files_modified` for TASK-006 contained `src/study_tutor/roles/__init__.py`, `registry.py`, `tutor/__init__.py`, `tests/unit/roles/test_registry.py` (owned by TASK-003) and `.env.example`, `tests/unit/test_env_example_nats.py` (owned by TASK-007). TASK-006 never wrote into those files; the orchestrator just attributed the worktree-wide diff to whichever task happened to finish at that moment.

`_detect_source_file_contention` then intersected this inflated set with `_peer_changed_files` and reported `parallel_contention` as "real source-level contention", which fell through to `feedback` instead of conditional approval. The Player retried, the underlying root cause (TASK-FIX-CC-BDD: BDD oracle scope) reappeared deterministically, and the budget was exhausted.

The result is a class of failure that **cannot escape feedback**: the false-positive contention signal blocks the conditional-approval path that the design relies on for parallel-wave robustness.

## Problem Surface

[guardkit/orchestrator/quality_gates/coach_validator.py:656–657](../../guardkit/orchestrator/quality_gates/coach_validator.py#L656-L657) — the `own` set construction; combined with the `agent_invoker` git-diff detection that feeds `task_work_results.files_modified`.

The integrity of the entire `parallel_contention + all_gates_passed → conditional_approval` path (lines 1192–1218) depends on `_peer_changed_files` and `own` being **disjoint when the task didn't actually edit peer files**. Today they almost always overlap in shared-worktree autobuilds — the design assumption is violated by the data source.

## Acceptance Criteria

- [ ] `_detect_source_file_contention` distinguishes player-authored edits from orchestrator-detected git-diff noise. Either:
  - (a) **Preferred:** `task_work_results.json` carries a separate `files_authored` field (player's explicit `Write`/`Edit` tool calls, captured by `agent_invoker` via SDK message inspection — already partially done for completion_promises), and `_detect_source_file_contention` uses *only* that field; OR
  - (b) `agent_invoker`'s git-diff detection performs per-task attribution (snapshot-diff against the task's start state, not the worktree's parent commit), so `files_modified` reflects only this task's edits.
- [ ] When peer tasks have committed before this task's git-diff sample, their files no longer appear in `files_modified` for this task.
- [ ] Replay test against FEAT-39E1 turn 2 fixture (preserved at `.guardkit/worktrees/FEAT-39E1/.guardkit/autobuild/TASK-NATS-PH1-006/`): `_detect_source_file_contention` returns an empty mapping (TASK-006 did not actually edit roles/ or .env.example), unblocking the `parallel_contention/high + all_gates_passed → conditional_approval` path.
- [ ] Genuine contention case (two tasks both writing into the same shared file, e.g. step-defs glue) still triggers — the regression suite from TASK-FIX-A7B2 must continue to pass.
- [ ] Existing serial-mode tasks (`wave_size=1`) are unaffected.

## Implementation Notes

**Recommended approach (option a, explicit authored set):**

1. `agent_invoker.py` already inspects SDK messages for `ToolUseBlock` events (Write, Edit). Aggregate the `file_path` argument across the task's player turn into a new field `task_work_results.files_authored: List[str]`.
2. `_detect_source_file_contention` reads `files_authored` instead of `files_modified` / `files_created`:
   ```python
   own = set(task_work_results.get("files_authored", []) or [])
   if not own:
       # Fallback for tasks that haven't migrated yet
       own = set(task_work_results.get("files_created", []) or [])
       own.update(task_work_results.get("files_modified", []) or [])
   ```
3. The fallback ensures backwards compatibility while the new field rolls out across stack templates.

**Why option (b) is harder:** per-task git snapshots inside a shared worktree require either checkpointed branch-per-task or pre-task `git stash` boundaries. That's a much larger orchestrator change with non-trivial perf implications. The shared-worktree design intentionally trades off this kind of attribution for parallelism speed; **option (a) keeps that trade-off intact** by capturing intent at the SDK boundary, which is cheap and authoritative.

**Bonus (optional):** add a structured-log line when `_detect_source_file_contention` finds overlap, recording both `files_authored` and `files_modified` so future false positives are diagnosable from logs alone.

## Test Plan

- [ ] Unit: `test_detect_source_file_contention_uses_files_authored_not_files_modified` — task with `files_authored=[a.py]` and `files_modified=[a.py, b.py]` (b.py from worktree noise); peer changed `b.py`; assert no overlap reported.
- [ ] Unit: `test_genuine_contention_still_detected` — task with `files_authored=[a.py]`; peer also changed `a.py`; assert overlap correctly reported (regression-pin TASK-FIX-A7B2's behaviour).
- [ ] Unit: `test_falls_back_to_files_modified_when_files_authored_absent` — backwards-compat path.
- [ ] Replay: load FEAT-39E1 turn-2 coach inputs, confirm `_detect_source_file_contention` returns `{}` and `conditional_approval == True`.
- [ ] `agent_invoker` regression: `task_work_results.files_authored` is populated from SDK Write/Edit tool calls and excludes worktree-noise files.

## Coach validation

```bash
pytest tests/orchestrator/quality_gates/test_coach_validator.py::test_detect_source_file_contention -v
pytest tests/orchestrator/test_agent_invoker.py -k "files_authored" -v
ruff check guardkit/orchestrator/quality_gates/coach_validator.py guardkit/orchestrator/agent_invoker.py
```

## Out of Scope

- Eliminating shared worktrees (out of scope; the design is intentional).
- The `bdd_oracle` scope bug — sibling task TASK-FIX-CC-BDD.
- Pre-1216 conditional_approval branches (`failure_class=infrastructure + docker_available`, `failure_class=collection_error`) — already correct.
- Per-task git branching for full attribution (option b) — not pursued unless option (a) proves insufficient.

## Evidence Pointers

- Failure log: `/Users/richardwoollcott/Projects/appmilla_github/study-tutor/docs/history/autobuild-FEAT-39E1-fail-run-1.md`
  - Line 606: `Git detection added: 30 modified, 5 created files for TASK-NATS-PH1-006`
  - Lines 802–804 / 914–916: `conditional_approval check: failure_class=parallel_contention, confidence=high, requires_infra=[], docker_available=False, all_gates_passed=True, wave_size=4` (gates pass but path doesn't fire because contention is "detected").
- Coach decision JSON: `/Users/richardwoollcott/Projects/appmilla_github/study-tutor/.guardkit/worktrees/FEAT-39E1/.guardkit/autobuild/TASK-NATS-PH1-006/coach_turn_2.json` — `issues[].description` lists "Overlapping files by peer" naming roles/ and .env.example as TASK-006's files.
- TASK-006 spec scope (proves no roles/ or .env.example ownership): `/Users/richardwoollcott/Projects/appmilla_github/study-tutor/tasks/backlog/nats-fleet-integration/TASK-NATS-PH1-006-serve-nats-cli-subcommand.md` lines 121–137.
- File-overlap reality check: TASK-REV-CC40 review report Appendix B.
- Sibling logic: `_detect_source_file_contention` lines 618–666; `_peer_changed_files` population in the FeatureOrchestrator.
