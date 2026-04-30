# FEAT-ATR — Implementation Guide

## Wave 1 (parallel-safe, no inter-task dependencies)

### TASK-ATR-001 — Per-task `task_timeout` frontmatter override

**Goal**: Add `task_timeout` to the per-task `autobuild` frontmatter section,
mirroring the existing `sdk_timeout` override.

**Code site**: [guardkit/orchestrator/feature_orchestrator.py:2467–2561](../../../guardkit/orchestrator/feature_orchestrator.py#L2467-L2561)
(`_execute_task`). Today reads `task_autobuild.get("sdk_timeout", 1200)` at line 2523.

**Change shape** (~30 LoC):
1. In `_execute_task`, after loading `task_data` (line 2514), look up
   `task_data["frontmatter"]["autobuild"].get("task_timeout")`.
2. If present, that value (subject to the same `timeout_multiplier`) replaces
   `self.task_timeout` for the *time_budget_seconds* that this task receives
   in the `asyncio.wait_for(..., timeout=...)` wrapping at line 2079–2087.
3. Note the orchestrator's per-wave gather uses a single `task_timeout` for
   `wait_for`, so the override needs to be applied at the *queue site*
   (line 2077–2087) by passing per-task timeouts. Refactor the gather loop
   to compute timeout per task instead of using `self.task_timeout` uniformly.

**Test plan**:
- Unit: parameterise `_execute_task` with a frontmatter override → asserts
  `time_budget_seconds` equals overridden value × multiplier.
- Integration: temp feature YAML with one task carrying
  `autobuild.task_timeout: 4500` → wait_for is constructed with 4500s.

**Risk**: Low. Refactoring the per-wave gather to use per-task timeouts is
the load-bearing change; everything else is reading + plumbing.

---

### TASK-ATR-002 — Refresh `remaining_budget` between Phase 4 and Phase 5 specialists

**Goal**: Phase 5 (`code-reviewer`) cap should reflect Phase 4
(`test-orchestrator`) wall consumption.

**Code site**: [guardkit/orchestrator/autobuild.py:2880–2909](../../../guardkit/orchestrator/autobuild.py#L2880-L2909).

```python
# Today (the bug):
phase4_result = _loop.run_until_complete(
    _si.invoke_test_orchestrator(...,
        sdk_timeout=self._cap_specialist_timeout(remaining_budget=remaining_budget),
        ...
    )
)
if phase4_result.status == "passed":
    _loop.run_until_complete(
        _si.invoke_code_reviewer(...,
            sdk_timeout=self._cap_specialist_timeout(remaining_budget=remaining_budget),  # ← stale!
            ...
        )
    )
```

**Change shape** (~15 LoC):
```python
# Capture wall before Phase 4
_phase4_start = time.monotonic()
phase4_result = _loop.run_until_complete(_si.invoke_test_orchestrator(...))

# Refresh budget post-Phase-4
if remaining_budget is not None:
    _phase4_elapsed = time.monotonic() - _phase4_start
    phase5_remaining = max(0.0, remaining_budget - _phase4_elapsed)
else:
    phase5_remaining = None

if phase4_result.status == "passed":
    _loop.run_until_complete(_si.invoke_code_reviewer(...,
        sdk_timeout=self._cap_specialist_timeout(remaining_budget=phase5_remaining),
        ...
    ))
```

**Test plan**:
- Unit: mock `_cap_specialist_timeout`, mock `invoke_test_orchestrator` to
  consume 200s wall; assert Phase 5 receives `phase5_remaining ≈ remaining - 200`.
- Update the existing comment at line 2895 ("Phase 4 may have consumed wall —
  that's correct") to match the corrected behaviour.

**Risk**: Low, isolated to one method. Hot path though, so add the unit test.

---

## Wave 2 (depends on no Wave 1 task, but easier to land last)

### TASK-ATR-003 — Feature-level late-approval reconciliation

**Goal**: After `gather()` collects a `TimeoutError` for a task, peek at the
task's latest `coach_turn_*.json`. If `decision == "approve"` and the file's
mtime is within `LATE_APPROVAL_GRACE_S` (default 60s) of the timer-fire,
reclassify as `APPROVED_LATE` rather than `TIMEOUT`.

**Code site**: [guardkit/orchestrator/feature_orchestrator.py:2137–2178](../../../guardkit/orchestrator/feature_orchestrator.py#L2137-L2178)
(the `isinstance(result, asyncio.TimeoutError)` branch).

**Change shape** (~40 LoC):

```python
# In feature_orchestrator.py, near the existing TimeoutError handler:

LATE_APPROVAL_GRACE_S = int(os.environ.get("GUARDKIT_LATE_APPROVAL_GRACE", "60"))

def _check_late_approval(self, task_id: str, timer_fire_time: float) -> Optional[str]:
    """Return 'approve' if a Coach decision was written within the grace window
    after `timer_fire_time`. Read-only, never raises."""
    autobuild_dir = self.repo_root / ".guardkit" / "autobuild" / task_id
    if not autobuild_dir.exists():
        return None
    coach_files = sorted(autobuild_dir.glob("coach_turn_*.json"),
                         key=lambda p: p.stat().st_mtime, reverse=True)
    if not coach_files:
        return None
    latest = coach_files[0]
    if (latest.stat().st_mtime - timer_fire_time) > LATE_APPROVAL_GRACE_S:
        return None  # too old or too new
    try:
        return json.loads(latest.read_text()).get("decision")
    except Exception:
        return None
```

In the `isinstance(result, asyncio.TimeoutError)` block:
```python
late = self._check_late_approval(task_id, timer_fire_time=time.time())
if late == "approve":
    logger.info(f"[{task_id}] APPROVED_LATE: Coach decision arrived within "
                f"{LATE_APPROVAL_GRACE_S}s of timer fire; reclassifying.")
    # build a successful TaskExecutionResult instead of timeout result
    error_result = TaskExecutionResult(
        task_id=task_id,
        success=True,
        total_turns=...,  # read from turn_state file
        final_decision="approved_late",
        error=None,
    )
else:
    # existing TIMEOUT handling
```

**Test plan**:
- Unit: tmp_path with a stub `coach_turn_2.json` `{"decision": "approve"}`
  whose mtime is now-30s. Call `_check_late_approval` → returns "approve".
- Unit: same but mtime is now-90s → returns None.
- Integration: simulate a `TimeoutError` slot in gather; pre-write a
  Coach-approved file; assert feature YAML records `approved_late`.

**Risk**: Low. The check is read-only; the worst that happens is we still
record TIMEOUT (the current behaviour). No async cancellation logic changes.

---

## Test execution order

```bash
# After each task lands:
cd /Users/richardwoollcott/Projects/appmilla_github/guardkit
pytest tests/unit/test_feature_orchestrator.py -k "timeout or task_timeout" -v
pytest tests/unit/test_autobuild.py -k "specialist or budget" -v

# Smoke test on a small feature before re-baselining:
guardkit autobuild feature FEAT-SOME-SMALL --verbose
```

## Recommended driver

These three tasks are independent at the file level. ATR-001 is the most
user-visible, ATR-002 is the lowest-risk + smallest, ATR-003 is the
architectural cleanup. Suggested cadence:

1. ATR-002 first (smallest, safest, demonstrates the pattern).
2. ATR-003 second (read-only check; addresses the concrete incident).
3. ATR-001 last (touches the gather loop; needs more careful testing).
