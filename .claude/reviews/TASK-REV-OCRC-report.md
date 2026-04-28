---
task_id: TASK-REV-OCRC
title: Diagnose orchestrator cancellation residual cleanup — `Task TASK-J004-013 not found in any state`
mode: diagnostic
depth: quick
parent_review: TASK-REV-WORS
related: [TASK-REV-COSE, FEAT-ABSR-9C6E]
verdict: real-bug-confirmed
recommendation: file-follow-up-implementation-task
priority: low
generated: 2026-04-28T13:05:00Z
---

# TASK-REV-OCRC — Quick Triage Report

## Executive summary

**Triage verdict: REAL BUG (two coupled issues, low priority).**

The 80 ms cluster at `events.jsonl` lines 45-49 is **not normal replay-summary
semantics**. It is the visible symptom of two distinct hygiene defects in the
feature orchestrator that compound when a `--fresh` invocation is cancelled
mid-clear:

1. **Non-atomic `_clean_state`** — `FeatureLoader.reset_state()` mutates the
   in-memory feature object, then `FeatureLoader.save_feature()` persists it.
   These are separate calls. Ctrl-C between them leaves the persisted YAML
   stale (still showing waves 1-4 completed).
2. **Misleading wave_completed emission on resume** — `_execute_wave_parallel`
   short-circuits tasks whose `status == "completed"` and returns synthetic
   success results, but the surrounding `_execute_wave` still emits a
   `WaveCompletedEvent` with full task counts and an instant timestamp. To any
   observer reading `events.jsonl`, this is indistinguishable from a wave that
   actually executed in 80 ms.

Neither issue is load-bearing for the demo. **Recommendation: file a single
low-priority follow-up implementation task** (proposed: `TASK-FIX-OCRC`)
covering both fixes, plus the orphan-START investigation. Full review/fix is
**not** required before the FEAT-ABSR-9C6E demo.

---

## 1. Symptom confirmation

`jarvis/.guardkit/autobuild/FEAT-J004-702C/events.jsonl` lines 45-50,
verbatim summary:

| Line | Time (UTC) | Role | Detail |
|------|------------|------|--------|
| 44 | `00:00:24.076` | router | wave-5 fail (1 worker, 0 completed, 1 failure) — **end of run-2** |
| 45 | `07:50:08.177` | router | wave-1 (4 workers, 4 completed) |
| 46 | `07:50:08.200` | router | wave-2 (5 workers, 5 completed) |
| 47 | `07:50:08.219` | router | wave-3 (1 worker, 1 completed) |
| 48 | `07:50:08.237` | router | wave-4 (2 workers, 2 completed) |
| 49 | `07:50:08.257` | player | **TASK-J004-013 START — no matching END** |
| 50 | `07:50:31.913` | player | TASK-J004-003 START (first real wave-1 task, 23 s gap) |

Cluster span: lines 45-49 fire in **80 ms**. Real per-task minimum runtime in
this run is ≥30 s. The cluster therefore cannot represent live execution.

After the cluster, a 23 s pause (worktree creation / environment bootstrap),
then real wave-1 tasks begin (lines 50-53 — J004-001/002/003/004, the four
wave-1 task IDs). This proves the run that emitted lines 50+ is a **fresh
start**, not a resume. The cluster at 45-49 is therefore not legitimate
"already-completed wave summary on resume" semantics.

The user-reported `Task TASK-J004-013 not found in any state` from attempt-1
(~06:50 UTC) is consistent with this picture: the cancelled `--fresh` left
behind partial state that the next invocation tripped on.

---

## 2. Code paths involved

### 2.1 The error message origin

`guardkit/tasks/state_bridge.py:312-316`:

```python
# Task not found
raise TaskNotFoundError(
    f"Task {self.task_id} not found in any state directory.\n"
    f"Searched: {[str(tasks_dir / s) for s in STATE_DIRECTORIES]}"
)
```

This fires in `StateBridge._find_task_file` when the orchestrator looks up a
task file by ID and finds nothing in `tasks/{backlog,in_progress,...}/`.
During `_clean_state`, task files may be moved/deleted by the worktree
cleanup; if the orchestrator queries a task ID after that point but before a
fresh worktree is set up, this error fires.

### 2.2 Non-atomic `_clean_state`

`guardkit/orchestrator/feature_orchestrator.py:1597-1631`:

```python
def _clean_state(self, feature: Feature) -> None:
    # ...
    if feature.execution.worktree_path:
        worktree_path = Path(feature.execution.worktree_path)
        if worktree_path.exists():
            try:
                # ... worktree cleanup ...
                self._worktree_manager.cleanup(worktree_to_cleanup, force=True)
            except Exception as e:
                logger.warning(f"Failed to cleanup worktree: {e}")

    # Reset feature state            ← in-memory only
    FeatureLoader.reset_state(feature)
    FeatureLoader.save_feature(feature, self.repo_root)  ← persist
    console.print("[green]✓[/green] Reset feature state")
```

`FeatureLoader.reset_state` (`feature_loader.py:1275-1295`) is purely
in-memory: it sets `feature.execution = FeatureExecution()` and resets each
task's status. **No persistence.** Persistence happens on the next line via
`save_feature`.

If `KeyboardInterrupt` lands between `reset_state` (line 1629) and
`save_feature` (line 1630), the on-disk feature YAML still records
`completed_waves=[1, 2, 3, 4]` from run-2. The next invocation reads stale
state.

Worktree cleanup (lines 1610-1626) is also non-transactional with respect
to the YAML state, but its failure path only logs a warning.

### 2.3 Wave-completed event always emits, even when wave is fully short-circuited

`guardkit/orchestrator/feature_orchestrator.py:1994-2011`:

```python
# Skip already completed tasks (for resume)
if task.status == "completed":
    # ... display update ...
    results.append(
        TaskExecutionResult(
            task_id=task_id,
            success=True,                          # ← synthetic success
            total_turns=task.turns_completed,
            final_decision="already_completed",
        )
    )
    continue
```

Then `_execute_wave` (lines 2293-2321):

```python
all_succeeded = all(r.success for r in results)
if all_succeeded:
    self._mark_wave_completed(feature, wave_number)

# Emit wave.completed event (TASK-INST-004)
tasks_completed_count = sum(1 for r in results if r.success)  # counts already_completed
task_failures_count = sum(1 for r in results if not r.success)
try:
    asyncio.run(
        self._emit_wave_completed(
            feature_id=feature.id,
            wave_id=f"wave-{wave_number}",
            # ...
            tasks_completed=tasks_completed_count,
            task_failures=task_failures_count,
            # ...
        )
    )
```

Result: when a wave is entered with all tasks already `status=="completed"`
(typical resume case), the wave loop emits a `WaveCompletedEvent` with
`tasks_completed=N`, no failures, no rate limits, identical in shape to a
genuinely-executed wave. The only signal an observer has that this was not a
real execution is the **timestamp delta** (80 ms vs ≥30 s).

### 2.4 The orphan TASK-J004-013 START (line 49)

This is the least-explained part. The START event at 07:50:08.257 has:
- `run_id = "run-TASK-J004-013-20260428075008"` (matches the cluster timestamp)
- `feature_id = null` (player-level event, not router)
- No matching END event

Two plausible sources, both worth investigation in the follow-up task:

(a) **Leftover subprocess from cancelled attempt-1**: a Player subprocess
    spawned during attempt-1's wave-5 retry was not killed before
    `KeyboardInterrupt` propagated to the parent. It completed its
    initialization phase, emitted START at 07:50:08, then either died
    silently or was killed externally before emitting END.

(b) **Stale-state-driven re-emit**: attempt-2 read the stale YAML
    (`completed_waves=[1,2,3,4]`, wave-5 incomplete, J004-013 still
    pending), iterated to wave-5, emitted START for J004-013, then
    something (worktree mismatch? cleared task file? TaskNotFoundError
    from §2.1?) caused the run to abort/restart, leaving the START
    orphaned. The 23 s gap before the actual wave-1 fresh execution
    supports this — that's plausibly the time to recover and re-init.

Without a reproducer or stderr/stdout from the run, hypothesis (b) seems
more consistent with the "Task TASK-J004-013 not found in any state" error
the user observed. But (a) cannot be ruled out from `events.jsonl` alone.

---

## 3. Triage decision and acceptance criteria

| AC | Verdict | Notes |
|----|---------|-------|
| AC-001 | ✓ | Real bug (two coupled defects). Not normal replay-summary. |
| AC-002 | ✓ (sketch) | Code paths identified at §2.2, §2.3, §2.4. Fix sketch in §4. |
| AC-003 | N/A | Real bug confirmed, so the "document replay semantics" branch does not apply. |
| AC-004 | ✓ | Confirms the bug surfaced in [TASK-REV-WORS report v2 §3.3](./TASK-REV-WORS-report.md#33-the-orphan-j004-013-start-at-075008-bug-to-file-as-sidequest). |
| AC-005 | ✓ | Verdict: **file follow-up implementation task**, low priority. |

---

## 4. Recommended fix sketch (for follow-up implementation task)

A single follow-up implementation task can cover all three:

### Fix 1 — Atomic `_clean_state`

`feature_orchestrator.py:1628-1631`. Either:

(a) **Reorder + persist-on-commit**: build a fresh `Feature` instance with
    reset state, save it first, then mutate the in-memory object the caller
    holds. So a Ctrl-C anywhere after the save is safe — disk is already
    consistent.

(b) **Signal-mask the critical section**: wrap the `reset_state →
    save_feature` pair in a small block that ignores `SIGINT` (using
    `signal.pthread_sigmask` or a `signal.signal` swap with try/finally).
    Cheaper but more platform-fragile.

Option (a) is preferred — it's structural rather than relying on signal
semantics.

### Fix 2 — Distinguish replayed wave_completed from executed

`feature_orchestrator.py:2300-2321`. Add a field on `WaveCompletedEvent`
distinguishing replay from execution:

```python
all_replayed = all(r.final_decision == "already_completed" for r in results)
# ...
WaveCompletedEvent(
    # ...existing fields...
    replay=all_replayed,         # NEW
)
```

Or, cleaner: don't emit a `WaveCompletedEvent` at all when the wave was
fully short-circuited. Emit a smaller `WaveSkippedEvent` (or just a log
line) instead. The observability pipeline in `concurrency.py` adapts to
ignore it. This avoids polluting wave-completion histograms with
zero-latency artificial datapoints.

### Fix 3 — Orphan player START investigation

Lower priority. Reproducer needed:
1. `guardkit autobuild feature FEAT-X --fresh`
2. Ctrl-C immediately after "[yellow]⚠[/yellow] Clearing previous incomplete state"
3. `guardkit autobuild feature FEAT-X --fresh` again
4. Inspect `events.jsonl` for orphan player START records.

If reproducible, trace whether the orphan comes from a leaked subprocess
(hypothesis (a) in §2.4) or stale-state-driven resume that aborts mid-wave
(hypothesis (b)). Fix likely shares code with Fix 1 once Fix 1 closes the
stale-state vector.

---

## 5. Out of scope for this triage

- Wave-4 failure mode (covered by [TASK-REV-WORS](./TASK-REV-WORS-report.md))
- Coach SDK opaque-stderr (covered by TASK-REV-COSE)
- Local reproducer (deferred to follow-up implementation task §4 Fix 3)
- Demo blocking — none of these defects block FEAT-ABSR-9C6E

---

## 6. Cross-references

- Source: [TASK-REV-WORS report v2 §3.3](./TASK-REV-WORS-report.md#33-the-orphan-j004-013-start-at-075008-bug-to-file-as-sidequest)
- Sibling sidequest: TASK-REV-COSE (Coach SDK opaque stderr)
- Parent feature: FEAT-ABSR-9C6E (autobuild-stall-resilience)
- Evidence file: `jarvis/.guardkit/autobuild/FEAT-J004-702C/events.jsonl` (lines 44-53)
- Code anchors:
  - `guardkit/tasks/state_bridge.py:312-316`
  - `guardkit/orchestrator/feature_orchestrator.py:1597-1631`
  - `guardkit/orchestrator/feature_orchestrator.py:1994-2011`
  - `guardkit/orchestrator/feature_orchestrator.py:2293-2321`
  - `guardkit/orchestrator/feature_loader.py:1275-1295`
