# Review Report: TASK-REV-A17A (Revised)

## Executive Summary

Deep analysis of two AutoBuild feature orchestration runs from `run_1.md`, verified against the source code of 8 modules across 4 packages, reveals **7 findings with verified root causes traced through C4 component interactions**. The two most critical failures both occur at technology seams between orchestration layers:

1. **Dual-layer timeout inversion**: The SDK timeout (2340s) for TASK-SAD-002 is *shorter* than the feature-level task_timeout (2400s), but for TASK-INST-002 (turn 2), the feature-level timeout fires *during* an SDK invocation that still has budget remaining — because the feature timer runs from wave start, not turn start
2. **task_type validation gap**: `task_type: enhancement` is never validated during feature loading (Phase 1) or task setup. Validation only occurs inside `coach_validator._resolve_task_type()` at Coach time — after the Player has already consumed a full turn

Both failures occur at integration boundaries between components that each work correctly in isolation.

## Review Details

- **Mode**: Failure Analysis (Revised — Deep Dive)
- **Depth**: Comprehensive
- **Source**: `docs/reviews/reduce-static-markdown/run_1.md` (3009 lines)
- **Code Traced**: `feature_orchestrator.py`, `autobuild.py`, `agent_invoker.py`, `coach_validator.py`, `worktree_checkpoints.py`, `state_tracker.py`, `state_detection.py`, `task_types.py`

---

## C4 System Context

```
┌─────────────────────────────────────────────────────────────────────┐
│                     AutoBuild Feature Orchestration                  │
│                                                                     │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────┐  │
│  │   Feature     │    │  AutoBuild   │    │    Agent Invoker     │  │
│  │ Orchestrator  │───>│ Orchestrator │───>│  (SDK Integration)   │  │
│  │              │    │              │    │                      │  │
│  │ task_timeout │    │ turn loop    │    │ sdk_timeout          │  │
│  │ = 2400s     │    │ cancellation │    │ = base * mode * cplx │  │
│  │ (wall-clock) │    │ event check  │    │ (per invocation)     │  │
│  └──────┬───────┘    └──────┬───────┘    └──────────┬───────────┘  │
│         │                   │                       │              │
│         │    ┌──────────────┴──────────────┐        │              │
│         │    │                             │        │              │
│         │    ▼                             ▼        ▼              │
│  ┌──────┴────────┐  ┌─────────────┐  ┌────────────────────────┐   │
│  │  Worktree     │  │   Coach     │  │   Claude Agent SDK     │   │
│  │  Checkpoints  │  │  Validator  │  │   (subprocess)         │   │
│  │              │  │             │  │                        │   │
│  │ pollution    │  │ task_type   │  │ asyncio.timeout()      │   │
│  │ detection    │  │ validation  │  │ _cancel_monitor()      │   │
│  │ rollback     │  │ indep tests │  │ _kill_child_processes() │   │
│  └──────────────┘  └─────────────┘  └────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Finding 1: Dual-Layer Timeout Inversion (CRITICAL)

**Severity**: CRITICAL | **Tasks Affected**: TASK-SAD-002, TASK-INST-002

### Sequence Diagram: TASK-SAD-002 SDK Timeout

```
                    TASK-SAD-002 (complexity=3, task-work mode)
                    sdk_timeout = 1200 * 1.5 * 1.3 = 2340s
                    task_timeout = 2400s (feature-level)

Time(s)  FeatureOrch    AutoBuild     AgentInvoker    Claude SDK
  0      │               │              │               │
         │──wait_for─────│              │               │
         │  (2400s)      │              │               │
         │               │──turn 1──────│               │
         │               │              │──invoke───────│
         │               │              │  timeout=2340s│
         │               │              │               │──Player
         │               │              │               │  impl...
         │               │              │               │  85 msgs
         │               │              │               │  66 tests ✓
         │               │              │               │  99% cov
         │               │              │               │  95/100 arch
         │               │              │               │  writing
2340     │               │              │ TIMEOUT!──────│  report...
         │               │              │ SDKTimeoutErr │
         │               │  state       │<──failure─────│
         │               │  recovery    │               │
         │               │  git: 3 files│               │
         │               │  tests: ×    │               │  (test runner
         │               │  (120s tmout)│               │   timed out)
         │               │              │               │
         │               │  synthetic   │               │
         │               │  report      │               │
         │               │              │               │
         │               │──cancellation check──────────│
         │               │  event.is_set() → True       │
         │               │  (set by gather finally)     │
         │               │                              │
         │               │  return "cancelled"          │
2400     │ TIMEOUT!──────│                              │
         │ asyncio.      │                              │
         │ TimeoutError  │                              │
         │               │                              │
         │ final_decision│                              │
         │ = "timeout"   │                              │
         ▼               ▼              ▼               ▼
```

### Verified Root Cause (Code-Level)

**Two independent timeout mechanisms compete without coordination:**

**Layer 1 — SDK timeout** (`agent_invoker.py:3039-3111`):
```python
# _calculate_sdk_timeout() — per-SDK-invocation timeout
effective = base * mode_multiplier * complexity_multiplier
# TASK-SAD-002: 1200 * 1.5 * 1.3 = 2340s
```
This is an `asyncio.timeout()` wrapping the Claude SDK streaming loop (`agent_invoker.py:1786-1919`). On expiry, raises `SDKTimeoutError` which is caught and converted to `AgentInvocationResult(success=False)`.

**Layer 2 — Feature task timeout** (`feature_orchestrator.py:1296-1310`):
```python
# _execute_wave_parallel() — wall-clock per-task timeout
asyncio.wait_for(
    asyncio.to_thread(self._execute_task, ...),
    timeout=self.task_timeout,  # 2400s
)
```
This wraps the *entire* `_execute_task` call (all turns, all Player+Coach phases). On expiry, raises `asyncio.TimeoutError` and sets the per-task `cancellation_event` in the `finally` block (`feature_orchestrator.py:1326-1332`).

**The inversion**: For TASK-SAD-002 (complexity=3), `sdk_timeout=2340s < task_timeout=2400s`, so the SDK timeout fires first. But for TASK-INST-002 (complexity=5), `sdk_timeout=2700s > task_timeout=2400s`, so the feature timeout fires first — *during* a valid SDK invocation.

**The compounding problem for multi-turn tasks**: TASK-INST-002 consumed ~300s on turn 1 Player + ~15s Coach + ~15s feedback processing before starting turn 2. Turn 2 began at ~330s wall-clock. The feature-level timeout counts from wave start (t=0), giving turn 2 only ~2070s before the 2400s fires — well short of its 2700s SDK budget.

### Sequence Diagram: TASK-INST-002 Feature-Level Timeout (Turn 2)

```
                    TASK-INST-002 (complexity=5, task-work mode)
                    sdk_timeout = 1200 * 1.5 * 1.5 = 2700s per invocation
                    task_timeout = 2400s (wall-clock from wave start)

Time(s)  FeatureOrch    AutoBuild     AgentInvoker    CoachValidator
  0      │──wait_for────│              │               │
         │  (2400s)     │──turn 1──────│               │
         │              │              │──Player────────│
  ~300   │              │              │  ✓ 32 files    │
         │              │              │  14 modified   │
         │              │              │<──success──────│
         │              │              │               │
         │              │──Coach───────│               │──validate
         │              │              │               │  indep tests
  ~315   │              │              │               │  FAILED (14.7s)
         │              │              │               │  class=code
         │              │              │               │  → feedback
         │              │              │               │
  ~330   │              │──turn 2──────│               │
         │              │              │──Player────────│
         │              │              │  sdk_timeout   │
         │              │              │  = 2700s       │
         │              │              │  (per invoc.)  │
         │              │              │               │
         │              │              │  ... working   │
         │              │              │  ... 2310s     │
         │              │              │  elapsed       │
         │              │              │               │
2400     │ TIMEOUT!     │              │               │
         │ asyncio.     │              │               │
         │ TimeoutError │              │               │
         │              │              │               │
         │──finally:────│              │               │
         │ cancel_event │              │               │
         │ .set()       │              │               │
         │              │              │               │
         │              │  _cancel_    │               │
         │              │  monitor()   │               │
         │              │  polls/2s    │               │
         │              │  event set!  │               │
         │              │  → kill child│               │
         │              │    processes │               │
         │              │              │               │
         │              │  Player SDK  │               │
         │              │  completes   │               │
         │              │  (turns=49)  │               │
         │              │              │               │
         │              │  cancellation│               │
         │              │  detected    │               │
         │              │  between     │               │
         │              │  Player/Coach│               │
         │              │              │               │
         │              │  return      │               │
         │              │  "cancelled" │               │
         ▼              ▼              ▼               ▼

         Result: CANCELLED (not TIMEOUT)
         Player work preserved but NEVER Coach-validated
```

### Key Integration Seam Issues

1. **No coordination between layers**: `feature_orchestrator._execute_wave_parallel()` has no visibility into the AutoBuild turn state. It cannot tell whether a task is on turn 1 (fresh start) or turn 2 (already invested 300s + Coach feedback).

2. **Cancellation event semantics**: The `threading.Event` in `feature_orchestrator.py:1326-1332` is set for ALL tasks in the `finally` block — including tasks that completed normally. The `_cancel_monitor` in `agent_invoker.py` polls every 2s and sends SIGTERM to child processes, which can kill a Player mid-execution.

3. **State recovery timing**: After SDK timeout, `MultiLayeredStateTracker.capture_state()` runs git detection (5s) + test detection (up to 300s). For TASK-SAD-002, the test detection timed out at 120s (`coach_verification:Test execution timed out after 120s`), producing 0 tests — making state recovery appear to have found no test evidence even though 66 tests actually passed.

### Revised Recommendations

| # | Recommendation | Severity | Effort | Regression Risk |
|---|---------------|----------|--------|-----------------|
| 1a | **Make task_timeout per-turn, not per-wave**: In `_execute_wave_parallel()`, reset the `asyncio.wait_for` deadline after each completed turn. Implementation: track cumulative turn time and extend the `wait_for` timeout by `remaining_sdk_timeout` when a turn completes. | Critical | Medium | Low — only changes timeout bookkeeping, not execution flow |
| 1b | **Add a "grace period" after Player completes**: If Player returns `success=True` but the task_timeout is about to fire, give 120s for Coach to run (Coach typically takes 10-17s). Implementation: in `_loop_phase`, check remaining time before invoking Coach. | Critical | Low | Low — additive only |
| 1c | **Log timeout layer clearly**: When a task is cancelled, log which timeout layer fired (SDK vs feature) and the remaining budget on the other layer. Currently, TASK-INST-002 shows "TIMEOUT" in the feature summary but "CANCELLED" in the AutoBuild summary — these should be reconciled. | Medium | Trivial | None |
| 1d | **Cap sdk_timeout at task_timeout**: `_calculate_sdk_timeout()` should return `min(calculated, remaining_task_budget)` to prevent the SDK from believing it has more time than the feature allows. | High | Low | Low — strictly reduces timeout, never increases |

---

## Finding 2: task_type Validation Gap at Integration Seam (CRITICAL)

**Severity**: CRITICAL | **Task Affected**: TASK-INST-012

### Sequence Diagram: TASK-INST-012 Unrecoverable Stall

```
                    TASK-INST-012 (task_type: "enhancement")

Phase 1    FeatureLoader        FeatureOrch          feature YAML
           │                    │                    │
           │──load_feature()────│                    │
           │  ✓ YAML parsed     │                    │
           │  ✓ validate:       │                    │
           │    - tasks exist   │                    │
           │    - deps valid    │                    │
           │    - waves valid   │                    │
           │    (NO task_type   │                    │
           │     validation)    │                    │
           │                    │                    │
           │──return feature────│                    │

Phase 2    AutoBuild     AgentInvoker    CoachValidator     Checkpoints
Turn 1     │              │               │                  │
           │──Player───────│               │                  │
           │              │──SDK invoke────│                  │
           │              │  ✓ 8 files     │                  │
           │              │  51 modified   │                  │
           │              │<──success──────│                  │
           │              │               │                  │
           │──Coach────────│               │──validate()      │
           │              │               │                  │
           │              │               │  _resolve_       │
           │              │               │  task_type()     │
           │              │               │  TaskType(       │
           │              │               │   "enhancement") │
           │              │               │  → ValueError!   │
           │              │               │                  │
           │              │               │  category=       │
           │              │               │  "invalid_       │
           │              │               │   task_type"     │
           │              │               │                  │
           │              │               │  return          │
           │              │               │  decision=       │
           │              │               │  "feedback"      │
           │              │               │                  │
           │  feedback────│               │                  │──checkpoint
           │  received    │               │                  │  tests=fail
           │              │               │                  │  (no tests
           │              │               │                  │   ran)
Turn 2     │──Player───────│               │                  │
           │  (same issue) │               │──"enhancement"──│
           │              │               │  → ValueError!   │  ──checkpoint
           │              │               │                  │    tests=fail
Turn 3     │──Player───────│               │                  │
           │  (perspective │               │──"enhancement"──│
           │   reset, same)│               │  → ValueError!   │  ──checkpoint
           │              │               │                  │    tests=fail
           │              │               │                  │
           │              │               │                  │──should_
           │              │               │                  │  rollback()
           │              │               │                  │  3 consecutive
           │              │               │                  │  failures!
           │              │               │                  │
           │              │               │                  │──find_last_
           │              │               │                  │  passing_
           │              │               │                  │  checkpoint()
           │              │               │                  │  → None!
           │              │               │                  │
           │  "unrecoverable_stall"────────│                  │
           ▼              ▼               ▼                  ▼
```

### Verified Root Cause (Code-Level)

**Seam 1: Feature loading has no task_type validation**

`feature_loader.py:643-726` (`validate_feature()`) checks:
- Tasks exist on disk
- Dependencies reference valid task IDs
- No circular dependencies
- No intra-wave dependencies
- **Does NOT validate `task_type` values in task frontmatter**

`feature_loader.py` task model (`FeatureTaskConfig`, line ~234):
```python
implementation_mode: Literal["direct", "task-work", "manual"] = "task-work"
# No task_type field in the feature task model — it comes from the task .md file
```

**Seam 2: AutoBuild orchestrator passes task_type through without validation**

`autobuild.py:762-765` reads `task_type` from task frontmatter and stores it in a dict that is later passed to `CoachValidator.validate()`. No validation occurs.

**Seam 3: Coach validator is the first and only place task_type is validated**

`coach_validator.py:495-543` (`_resolve_task_type()`):
```python
try:
    return TaskType(task_type_str)   # enum lookup
except ValueError:
    if task_type_str in TASK_TYPE_ALIASES:
        return TASK_TYPE_ALIASES[task_type_str]
    raise ValueError(f"Invalid task_type value: {task_type_str}...")
```

The `TaskType` enum (`task_types.py:21-49`) defines 7 values: `scaffolding, feature, infrastructure, integration, documentation, testing, refactor`. The alias table (`coach_validator.py:68-75`) adds 5 aliases: `implementation, bug-fix, bug_fix, benchmark, research`. **`enhancement` is in neither.**

`coach_validator.py:588-605` catches the `ValueError` and returns `decision="feedback"` with `category="invalid_task_type"` — which the AutoBuild loop treats identically to a test failure.

**Seam 4: Pollution detection cannot distinguish configuration errors from code failures**

`worktree_checkpoints.py:475-503` (`should_rollback()`):
```python
recent = self.checkpoints[-consecutive_failures:]  # last 3
all_failing = all(not cp.tests_passed for cp in recent)
```

When Coach returns `decision="feedback"` due to invalid task_type, the checkpoint is created with `tests_passed=False` (because Coach never ran tests). This is indistinguishable from an actual test failure, triggering pollution detection after 3 turns.

**Seam 5: Player cannot fix the root cause**

The Player receives Coach feedback containing the error message but operates on code files in the worktree — it has no ability to modify task frontmatter YAML, which lives outside the implementation scope. Even with perspective reset at turn 3 (`autobuild.py:2695`), the task_type remains `enhancement`.

### Why This Is Truly Unrecoverable

The feedback loop is deterministic:
1. Player implements → succeeds (code is fine)
2. Coach validates → fails immediately at task_type resolution (before testing)
3. Checkpoint recorded as `tests_passed=False`
4. Repeat 3 times → pollution detected → no passing checkpoint → `unrecoverable_stall`

No amount of Player iteration or perspective resets can fix a task frontmatter field that the Player doesn't control.

### Revised Recommendations

| # | Recommendation | Severity | Effort | Regression Risk |
|---|---------------|----------|--------|-----------------|
| 2a | **Add `enhancement` as alias for `feature`** in `TASK_TYPE_ALIASES` in both `coach_validator.py:68-75` and `autobuild.py:3800-3806` | Critical | Trivial | None — additive |
| 2b | **Validate task_type in `feature_loader.validate_feature()`**: Read each task's frontmatter and check `task_type` against `TaskType` enum + aliases. Fail fast with actionable error. | Critical | Low | Low — validation-only, read-only |
| 2c | **Add `is_configuration_error` flag to `CoachValidationResult`**: When `category="invalid_task_type"`, mark it as configuration rather than code. In `autobuild._loop_phase`, check this flag and exit immediately with a clear error instead of entering the feedback loop. | Critical | Medium | Medium — changes loop exit conditions; needs test coverage for the new path |
| 2d | **Do NOT count Coach configuration errors in pollution detection**: In checkpoint creation (`autobuild.py` around line 1648), check if the feedback category is `invalid_task_type` and either skip checkpoint creation or mark it as `tests_passed=True` (since tests were never run). | High | Low | Low — narrowly scoped |

---

## Finding 3: Coach Independent Test Verification — Shared Worktree Race Condition (HIGH)

**Severity**: HIGH | **Tasks Affected**: TASK-SAD-004, TASK-SAD-005, TASK-INST-002

### Sequence Diagram: Parallel Task Worktree Contention

```
         Wave 2: 5 parallel tasks sharing ONE worktree

Time     TASK-A (Player)  TASK-B (Player)  TASK-A (Coach)   Git Worktree
  0      │                │                │                │
         │──write src/a.py│                │                │ src/a.py created
         │──write test_a  │──write src/b.py│                │ src/b.py created
         │                │──write test_b  │                │ test_b.py created
         │                │──modify        │                │
         │                │  __init__.py   │                │ __init__.py v2
  300    │ ✓ Player done  │                │                │
         │                │                │──run indep     │
         │                │                │  tests         │
         │                │──modify        │                │ __init__.py v3!
         │                │  __init__.py   │  test_a.py     │
         │                │                │  imports from  │
         │                │                │  __init__ v3   │
         │                │                │  but expects   │
         │                │                │  v2 symbols    │
         │                │                │  → ImportError  │
         │                │                │  → "code" class│
         │                │                │  → FEEDBACK    │
         ▼                ▼                ▼                ▼

         Coach indep tests see a DIFFERENT worktree state
         than what the Player tested against!
```

### Verified Root Cause (Code-Level)

**Seam: Coach independent tests run against live worktree**

`coach_validator.py:1264-1455` (`run_independent_tests()`):
- Detects task-specific test files from `task_work_results.json`
- Runs `pytest <test_files> -v --tb=short` via SDK or subprocess
- **No isolation mechanism**: tests execute against the current worktree HEAD, which may have been modified by other parallel tasks

**The git locking in `worktree_checkpoints.py:279-427`** only serializes checkpoint *commits*, not the working tree state. Between `git add` and `git commit`, other tasks can modify files.

**Failure classification inconsistency** (`coach_validator.py:2713-2812`):
- `collection_error` (pattern: "errors during collection") → `conditional_approval=True` (when all gates passed)
- `code` (fallback when no infrastructure pattern matches) → `conditional_approval=False` → feedback

Both `collection_error` and `code` failures in this context are caused by the same root issue (worktree mutation by parallel tasks), but produce different Coach decisions.

**The conditional approval formula** (`coach_validator.py:665-774`):
```python
conditional_approval = (
    failure_class == "infrastructure" and ...
) or (
    failure_class == "collection_error"
    and gates_status.all_gates_passed
)
```
`code` classification is NOT included. An `ImportError` from a parallel task's mutation classifies as `code` (fallback), not `collection_error`, so it triggers feedback instead of conditional approval.

### Revised Recommendations

| # | Recommendation | Severity | Effort | Regression Risk |
|---|---------------|----------|--------|-----------------|
| 3a | **Run Coach tests against a per-task git snapshot**: Before running independent tests, `git stash push --include-untracked` the task's changes, run tests, then `git stash pop`. This isolates the test environment from concurrent mutations. | High | Medium | Medium — stash operations on a shared worktree need serialization; could conflict with parallel checkpoint commits |
| 3b | **Grant conditional approval for `code` failures when all gates passed and task is in a parallel wave**: Add wave-awareness to the conditional approval formula. If `wave_size > 1 and gates_status.all_gates_passed`, grant conditional approval regardless of failure class. | High | Low | Low — strictly more permissive |
| 3c | **Add `parallel_wave` flag to independent test failure classification**: When running in a parallel wave, reclassify `code` → `parallel_contention` with `conditional_approval=True`. | Medium | Low | Low — new classification, doesn't change existing paths |

---

## Finding 4: Feature Validation Gap — Intra-Wave Dependencies (MEDIUM)

**Severity**: MEDIUM | **Task Affected**: FEAT-CF57 first attempt

### Verified Root Cause

`feature_loader.py:722-724` (`validate_parallel_groups()`) correctly detects intra-wave dependencies, but this validation only runs at orchestration time inside `_setup_phase()`. There is no validation step during:
- `/feature-plan` output generation
- Manual YAML editing
- `guardkit autobuild feature` before the full setup

The validation IS correct — it caught the error. The issue is that it runs too late, after the user has already committed to a run.

### Recommendations

| # | Recommendation | Severity | Effort | Regression Risk |
|---|---------------|----------|--------|-----------------|
| 4a | **Add `guardkit feature validate FEAT-XXX` CLI command**: Runs `FeatureLoader.validate_feature()` standalone without creating worktrees | Medium | Low | None |
| 4b | **Run validation in `/feature-plan`**: After generating the YAML, call `validate_feature()` and report errors inline | Medium | Low | None |

---

## Finding 5: Documentation Level Constraint — False Positives (LOW)

**Severity**: LOW

### Verified Root Cause

`agent_invoker.py` counts ALL created files including `.guardkit/autobuild/{task_id}/player_turn_N.json` — an internal artifact that the Player cannot avoid creating. The "minimal level" constraint allows max 2 created files, but a TDD feature task inherently creates: 1 source file + 1 test file + 1 player report = 3 files minimum.

The constraint is logged as `WARNING` and does NOT affect Coach decisions — confirmed by checking `coach_validator.py` which has no reference to documentation level.

### Recommendations

| # | Recommendation | Severity | Effort | Regression Risk |
|---|---------------|----------|--------|-----------------|
| 5a | **Exclude `.guardkit/` paths from file creation count** | Low | Trivial | None |
| 5b | **Set documentation level to `standard` for feature/refactor task types** | Low | Trivial | None |

---

## Finding 6: Environment Bootstrap — No Fixture Exclusion (LOW)

**Severity**: LOW

### Verified Root Cause

`environment_bootstrap.py:346-365` (`ProjectEnvironmentDetector.detect()`) scans root + depth-1 non-hidden subdirectories. The `.sln` file at the root includes `tests/fixtures/sample_projects/maui_sample/MauiSample.csproj` which references EOL .NET 8 MAUI workloads. Since `dotnet restore` processes all projects referenced by the solution, the fixture project is included.

The detection code (`environment_bootstrap.py:411-558`) explicitly only skips hidden directories (starting with `.`). There is no mechanism to exclude `tests/fixtures/` or any other non-hidden directory.

### Recommendations

| # | Recommendation | Severity | Effort | Regression Risk |
|---|---------------|----------|--------|-----------------|
| 6a | **Add `bootstrap_ignore` patterns**: Support a `.guardkit/bootstrap-ignore` file (gitignore syntax) to exclude paths from dependency detection | Low | Medium | Low |
| 6b | **Exclude `tests/fixtures/` by default**: Add to the skip list alongside hidden directories | Low | Trivial | Low — might break projects that have real dependencies in test fixtures |

---

## Finding 7: Cancellation Timing — Player/Coach Gap (MEDIUM)

**Severity**: MEDIUM | **Tasks Affected**: TASK-SAD-002 (attempt 1), TASK-INST-002

### Sequence Diagram: Cancellation Between Player and Coach

```
         TASK-INST-002, Turn 2

Time     FeatureOrch    AutoBuild._loop_phase    AgentInvoker

  0      │──wait_for────│                         │
         │  (2400s      │                         │
         │   from wave  │                         │
         │   start)     │                         │
         │              │                         │
  ~330   │              │──turn 2 start───────────│
         │              │                         │──Player SDK
         │              │                         │  invoke...
         │              │                         │
2310     │              │                         │  SDK still
         │              │                         │  has 390s
         │              │                         │  budget
         │              │                         │  remaining
         │              │                         │
2400     │ TIMEOUT!     │                         │
         │ cancel_event │                         │
         │ .set()       │                         │
         │              │                         │
         │              │  _cancel_monitor()      │
         │              │  detects event           │
         │              │  _kill_child_processes() │
         │              │                         │
         │              │  Player returns          │
         │              │  (turns=49, success)     │
         │              │                         │
         │              │──cancellation check──────│
         │              │  between Player/Coach    │
         │              │  event.is_set() → True   │
         │              │                         │
         │              │  return "cancelled"      │
         │              │                         │
         │              │  Coach NEVER invoked     │
         │              │  (would take ~15s)       │
         ▼              ▼                         ▼

         49 SDK turns of work, never validated!
```

### Verified Root Cause

`autobuild.py:1588-1595` checks `cancellation_event.is_set()` AFTER each turn:
```python
if self._cancellation_event and self._cancellation_event.is_set():
    logger.info(f"Cancellation detected after turn {turn} for {task_id}")
    return turn_history, "cancelled"
```

This check runs between Player completion and Coach invocation. If the feature-level timeout fires during the Player, the event is set, and the loop exits before Coach gets to run — even though the Coach typically only needs 10-17s.

### Revised Recommendations

| # | Recommendation | Severity | Effort | Regression Risk |
|---|---------------|----------|--------|-----------------|
| 7a | **Skip cancellation check if Player succeeded and Coach is fast**: If `player_result.success == True`, invoke Coach regardless of cancellation event, but with a strict 120s timeout. The Coach validator typically takes 10-17s. | Medium | Medium | Low — Coach is already a separate SDK invocation with its own timeout |
| 7b | **Report CANCELLED vs TIMEOUT distinctly in feature summary**: Currently TASK-INST-002 shows "TIMEOUT" in the wave summary but "CANCELLED" in the AutoBuild summary | Low | Trivial | None |

---

## Summary of Recommendations by Priority

### Critical (Fix Immediately)

| # | Recommendation | Effort | Regression Risk |
|---|---------------|--------|-----------------|
| 2a | Add `enhancement` as alias for `feature` in `TASK_TYPE_ALIASES` | Trivial | None |
| 2b | Validate task_type in `feature_loader.validate_feature()` | Low | Low |
| 2c | Add `is_configuration_error` flag; exit loop immediately for config errors | Medium | Medium |
| 1a | Make task_timeout per-turn, not per-wave | Medium | Low |
| 1b | Add grace period for Coach after Player success | Low | Low |
| 1d | Cap sdk_timeout at remaining task_timeout budget | Low | Low |

### High (Fix Soon)

| # | Recommendation | Effort | Regression Risk |
|---|---------------|--------|-----------------|
| 2d | Don't count config errors in pollution detection | Low | Low |
| 3a | Run Coach tests against per-task git snapshot | Medium | Medium |
| 3b | Grant conditional approval for `code` failures in parallel waves | Low | Low |

### Medium (Plan for Next Sprint)

| # | Recommendation | Effort | Regression Risk |
|---|---------------|--------|-----------------|
| 3c | Add `parallel_contention` failure classification | Low | Low |
| 7a | Skip cancellation check if Player succeeded and Coach is fast | Medium | Low |
| 4a | Add `guardkit feature validate` pre-flight CLI command | Low | None |
| 1c | Log which timeout layer fired | Trivial | None |

### Low (Backlog)

| # | Recommendation | Effort | Regression Risk |
|---|---------------|--------|-----------------|
| 5a | Exclude `.guardkit/` from file creation count | Trivial | None |
| 5b | Set documentation level to `standard` for feature tasks | Trivial | None |
| 6a | Add `bootstrap_ignore` pattern support | Medium | Low |
| 6b | Exclude `tests/fixtures/` from bootstrap by default | Trivial | Low |
| 7b | Distinguish TIMEOUT from CANCELLED in feature summary | Trivial | None |

---

## Appendix A: Timeout Budget Table

All timeout values observed in run_1.md with the formula `base(1200) * mode(1.5) * complexity_mult`:

| Task | Complexity | SDK Timeout | Task Timeout | SDK > Task? | Outcome |
|------|-----------|------------|-------------|-------------|---------|
| TASK-SAD-001 | 4 | 2520s | 2400s | Yes | SDK killed by task timeout? No — completed in 1 turn |
| TASK-SAD-002 | 3 | 2340s | 2400s | **No** | SDK timeout fired first (2340s) |
| TASK-SAD-003 | 5 | 2700s | 2400s | Yes | Completed in 1 turn |
| TASK-SAD-004 | 5 | 2700s | 2400s | Yes | Completed (conditional approval) |
| TASK-SAD-005 | 6 | 2880s | 2400s | Yes | Completed (2 turns) |
| TASK-SAD-006 | 8 | 3240s | 2400s | Yes | Completed in 1 turn |
| TASK-SAD-007 | 8 | 3240s | 2400s | Yes | Completed in 1 turn |
| TASK-SAD-008 | 7 | 3060s | 2400s | Yes | Completed in 1 turn |
| TASK-SAD-009 | 6 | 2880s | 2400s | Yes | Completed in 1 turn |
| TASK-SAD-010 | 5 | 2700s | 2400s | Yes | Completed in 1 turn |
| TASK-INST-001 | 4 | 2520s | 2400s | Yes | Completed in 1 turn |
| TASK-INST-002 | 5 | 2700s | 2400s | Yes | **Feature timeout at turn 2** |
| TASK-INST-003 | 4 | 2520s | 2400s | Yes | Completed in 1 turn |
| TASK-INST-007 | 5 | 2700s | 2400s | Yes | Completed in 1 turn |
| TASK-INST-010 | 4 | 2520s | 2400s | Yes | Completed in 1 turn |
| TASK-INST-011 | 3 | 2340s | 2400s | **No** | Completed in 1 turn |
| TASK-INST-012 | 5 | 2700s | 2400s | Yes | Unrecoverable stall (task_type) |

**Key insight**: For complexity ≥4 (majority of tasks), `sdk_timeout > task_timeout`. The SDK timeout is effectively irrelevant — the feature-level timeout will always fire first. This makes the SDK timeout calculation wasted effort for most tasks.

## Appendix B: Timeline Summary

### FEAT-E4F5 Attempt 1 (17:38 - 18:35)
- Wave 1: TASK-SAD-001 ✓ (27 SDK turns), TASK-SAD-002 **SDK TIMEOUT at 2340s** (85 msgs, all gates passed), TASK-SAD-003 ✓ (34 SDK turns)
- stop_on_failure → halted
- Duration: 56m 43s, 2/10 completed

### FEAT-E4F5 Attempt 2 / Resume (20:06 - 21:00)
- Wave 1: SAD-001 skipped, SAD-002 ✓ (1 turn), SAD-003 skipped
- Wave 2: SAD-004 ✓ (conditional approval — collection_error), SAD-005 ✓ (2 turns — code failure then fix)
- Waves 3-5: All tasks ✓ (1 turn each)
- Duration: 53m 53s, 10/10 completed

### FEAT-CF57 Attempt 1 (failed validation)
- `validate_parallel_groups()` caught intra-wave dependency in Wave 4
- No tasks executed

### FEAT-CF57 Attempt 2 (13:06 - 14:20)
- Wave 1: 5 tasks, all ✓ (1 turn each)
- Wave 2: 5 tasks parallel
  - INST-003 ✓ (1 turn, 37 SDK turns)
  - INST-007 ✓ (1 turn, 62 SDK turns)
  - INST-011 ✓ (1 turn, 39 SDK turns)
  - **INST-002**: Turn 1 Player ✓ → Coach feedback (indep test code failure) → Turn 2 running → **FEATURE TIMEOUT at 2400s** → CANCELLED
  - **INST-012**: Turn 1 Player ✓ → Coach "invalid_task_type" → Turn 2 Player ✓ → Coach "invalid_task_type" → Turn 3 Player ✓ → Coach "invalid_task_type" → **UNRECOVERABLE_STALL**
- stop_on_failure → halted
- Duration: 51m 0s, 5/14 completed
