# Review Report: TASK-REV-5E1F

## Executive Summary

The Run 5 regression (6/7 tasks, down from 7/7 in Run 4) has a **different root cause than initially hypothesized**. The task description incorrectly stated that TASK-FBP-007 was routed to `task-work` mode in Run 5 — log evidence proves it used `direct` mode in **both** runs with identical 6240s SDK timeout. The actual root cause is a combination of **budget starvation from FBP-006** and **infeasible acceptance criteria** for the vLLM backend.

## Review Details

- **Mode**: Decision Analysis
- **Depth**: Standard
- **Task**: TASK-REV-5E1F
- **Focus**: All aspects (root cause, timeout, cancel scope, acceptance criteria, regression attribution)
- **Priority**: Reliability

---

## Finding 1: Mode Routing Was NOT the Root Cause (CRITICAL CORRECTION)

**Severity**: Informational (corrects false hypothesis)

The task description stated:

| Metric | Run 4 | Run 5 |
|--------|-------|-------|
| TASK-FBP-007 mode | `direct` | `task-work` |
| TASK-FBP-007 SDK timeout | 6240s | 9360s |

**Actual evidence from both run logs**:

```
# Run 4 (line 3642):
INFO:guardkit.orchestrator.agent_invoker:[TASK-FBP-007] SDK timeout: 6240s (base=1200s, mode=direct x1.0, complexity=3 x1.3, backend x4.0)
INFO:guardkit.orchestrator.agent_invoker:Routing to direct Player path for TASK-FBP-007 (implementation_mode=direct)

# Run 5 (line 1900, repeated 8 times for each turn):
INFO:guardkit.orchestrator.agent_invoker:[TASK-FBP-007] SDK timeout: 6240s (base=1200s, mode=direct x1.0, complexity=3 x1.3, backend x4.0)
INFO:guardkit.orchestrator.agent_invoker:Routing to direct Player path for TASK-FBP-007 (implementation_mode=direct)
```

**Corrected comparison**:

| Metric | Run 4 | Run 5 |
|--------|-------|-------|
| TASK-FBP-007 mode | `direct` | `direct` |
| TASK-FBP-007 SDK timeout | 6240s | 6240s |
| Mode routing deterministic? | Yes | Yes (same code, same result) |

The mode routing logic in `agent_invoker.py:3162-3296` is fully deterministic — based on complexity (<=3), absence of high-risk keywords, and acceptance criteria count (<2). No LLM-based or random decisions are involved.

---

## Finding 2: Budget Starvation from FBP-006 Serialization

**Severity**: High — Primary root cause

Both runs used `max_parallel=1`, meaning Wave 5's two tasks (FBP-006, FBP-007) were **serialized via asyncio semaphore**, not run in parallel despite being in the same wave.

**Timeline reconstruction**:

```
Run 4:
  Wave 5 start:    23:15 + cumulative waves = 01:40:38
  FBP-006 SDK:     43 turns, ~82 minutes
  FBP-007 start:   ~03:00 (after FBP-006 completes)
  FBP-007 budget:  9600 - ~4838 = ~4762s remaining
  FBP-007 result:  1 turn, approved ✓

Run 5:
  Wave 5 start:    16:22:28
  FBP-006 SDK:     110 turns (CEILING HIT), 6749.3s (112 minutes)
  FBP-007 start:   18:15:28 (6780s after wave start)
  FBP-007 budget:  9600 - 6780 = 2820s remaining (~47 minutes)
  FBP-007 result:  8 turns, all cancelled, timeout_budget_exhausted ✗
```

**The critical difference**: FBP-006 consumed 6749s (112 min) in Run 5 vs ~4838s (~80 min) in Run 4. This left FBP-007 with only **2820s** (~47 min) of budget instead of ~4762s (~79 min).

The `task_budget` calculation in `feature_orchestrator.py:1475-1476`:
```python
elapsed_at_queue = time.monotonic() - wave_start_time
task_budget = max(0.0, self.task_timeout - elapsed_at_queue)
```

With `max_parallel=1`, `elapsed_at_queue` for the second task includes the entire first task's runtime, dramatically reducing the available budget.

---

## Finding 3: Cancel Scope Chain — SDK-Level Cancellation

**Severity**: Medium — Explains the failure mechanism

All 8 FBP-007 turns were cancelled via anyio cancel scopes, not by SDK timeout (6240s) or asyncio.wait_for:

| Turn | Started | Cancelled After | Cancel Scope ID |
|------|---------|----------------|-----------------|
| 1 | 18:15:28 | 2460s (41m) | f8ad386af740 |
| 2 | 18:57:21 | 1020s (17m) | f8ad382dec90 |
| 3 | 19:15:10 | 1260s (21m) | f8ace852b380 |
| 4 | 19:36:49 | 1110s (19m) | f8ad08157500 |
| 5 | 19:55:49 | 960s (16m) | f8ace8516660 |
| 6 | 20:12:30 | 330s (6m) | f8ad386543e0 |
| 7 | 20:18:45 | 1260s (21m) | f8ace852b860 |
| 8 | 20:40:?? | 510s (9m) | f8ad38183f80 |

**Key observations**:
- Cancellation intervals (6-41 min) are well below the 6240s SDK timeout
- Each cancellation comes from a different `Task-XXXX` asyncio task via `async_generator_athrow`
- The pattern suggests the Claude SDK's internal anyio cancel scopes are being triggered by external timeout signals propagating into the SDK's streaming loop
- Total elapsed across all 8 turns: ~9910s (exceeds the 2820s budget), indicating the autobuild loop continued retrying despite budget exhaustion — state recovery between turns adds overhead

**~~Asymmetric budget handling~~ CORRECTED** (code evidence from `agent_invoker.py`):
- ~~`invoke_player()`: Does NOT accept `remaining_budget` parameter~~ **CORRECTION (TASK-REV-35DC):** `invoke_player()` DOES accept `remaining_budget` (added via TASK-VRF-003, at `agent_invoker.py:1144`). The full chain flows through:
  - `feature_orchestrator.py:1483` → `task_budget = max(0, task_timeout - elapsed)`
  - `autobuild.py:2069` → `_invoke_player_safely(remaining_budget=...)`
  - `agent_invoker.py:1197` → `_calculate_sdk_timeout(remaining_budget=...)`
  - `agent_invoker.py:3456` → `effective = min(effective, int(remaining_budget))`
- `invoke_coach()`: DOES accept `remaining_budget`, caps SDK timeout to remaining wall-clock time
- Both Player and Coach SDK calls are dynamically shortened as budget depletes

---

## Finding 4: Acceptance Criteria Infeasibility

**Severity**: High — Secondary root cause

The Coach consistently rejected FBP-007's work. The unmet criteria evolved across turns:

```
Turn 1: missing ['All type annotations complete — no Any types']
Turn 2: missing ['All type annotations complete — no Any types', 'CI-ready script or Makefile target']
Turn 3: missing ['All type annotations complete — no Any types']
...
Turn 8: missing ['pyproject.toml ruff config', 'pyproject.toml mypy config: strict mode',
                  'mypy src/ passes with zero errors in strict mode',
                  'All type annotations complete — no Any types']
```

**Assessment**: Achieving `mypy --strict` with zero `Any` types across the entire `src/` directory is an extremely demanding criterion for vLLM-backed code generation:
1. vLLM produces less precise type annotations than cloud models
2. Third-party library stubs frequently use `Any` types (unavoidable)
3. Strict mode flags re-exports, decorators, and dynamic patterns
4. In Run 4, the same task passed in 1 turn — suggesting the Coach was less strict or the codebase state was more amenable

**The criteria regression across turns** (Turn 8 lost ground vs Turn 1) indicates that state recovery + re-invocation is counterproductive for this task — the Player undoes previous work or creates new type issues while trying to fix existing ones.

---

## Finding 5: Regression Attribution

**Severity**: Low — No direct causal link

The inter-run changes (TASK-REV-F8BA Graphiti fixes, TASK-GCF-001-003 group fixes, TASK-VOPT-001-003 optimizations) did **not** affect:
- Mode routing logic (deterministic, same result both runs)
- Timeout configuration (same parameters: task_timeout=9600s, timeout_multiplier=4.0x)
- Cancel scope mechanism (unchanged code paths)

The regression is attributable to **FBP-006's non-deterministic SDK turn consumption** (43 vs 110 turns), which is inherent to LLM-backed code generation and not caused by any code change.

---

## Decision Matrix

| Option | Reliability | Effort | Risk | Recommendation |
|--------|------------|--------|------|----------------|
| A: Increase task_timeout for Wave 5 | Medium | Low | Low | Quick fix, doesn't address root cause |
| B: Relax FBP-007 acceptance criteria | High | Low | Medium | Removes infeasible constraint |
| C: Move FBP-007 to separate wave | High | Medium | Low | Eliminates budget starvation |
| D: ~~Pass remaining_budget to Player~~ | ~~High~~ | ~~Medium~~ | ~~Low~~ | **ALREADY IMPLEMENTED** (TASK-VRF-003) — see TASK-REV-35DC correction |
| E: B + C combined | Very High | Medium | Low | **Recommended** |

---

## Recommendations

### R1: Relax TASK-FBP-007 acceptance criteria (Priority: HIGH)

Replace `mypy src/` strict with zero `Any` types → `mypy src/` with reasonable strictness:
- Accept `Any` from third-party stubs
- Use `--disallow-untyped-defs` without `--strict`
- Or use `mypy --strict` with explicit `# type: ignore` allowances for unavoidable cases

### R2: Move FBP-007 to its own wave (Priority: HIGH)

Separate FBP-007 from FBP-006 to eliminate budget starvation. With `max_parallel=1`, placing both in Wave 5 effectively gives FBP-007 only the leftover budget.

### R3: Pass remaining_budget to invoke_player (Priority: MEDIUM)

Add `remaining_budget` parameter to `invoke_player()` and use it to cap the SDK timeout, matching the existing Coach behavior. This prevents the Player from starting turns it cannot finish.

### R4: Add budget warning before turn start (Priority: LOW)

Log a warning when `remaining_budget < SDK_timeout` to make budget starvation visible in logs without waiting for timeout_budget_exhausted.

### R5: Correct the task description (Priority: LOW)

Update the TASK-REV-5E1F description to reflect the actual mode routing (both runs used `direct` mode).

---

## Acceptance Criteria Assessment

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Root cause of mode routing change identified | **N/A — No mode change occurred** | Both runs used `direct` mode (log lines Run4:3642, Run5:1900) |
| Timeout budget timeline reconstructed | **Done** | See Finding 2 timeline |
| Cancel scope source identified | **Done** | SDK-level anyio cancel scopes triggered by budget exhaustion (Finding 3) |
| Recommendation for preventing recurrence | **Done** | 5 recommendations (R1-R5) |
| Assessment of acceptance criteria adjustment | **Done** | Finding 4: mypy strict + zero Any is infeasible for vLLM backend |

---

## Deep-Dive A: Cancel Scope Propagation Chain

### Full Trace: Budget Exhaustion to Player Cancellation

```
Feature Orchestrator (feature_orchestrator.py:1478)
  └─ asyncio.wait_for(timeout=9600s) wraps asyncio.to_thread()
       └─ Thread runs _execute_task() in AutoBuildOrchestrator
            └─ _loop_phase() (autobuild.py:1732) checks remaining_budget
                 └─ _execute_turn() (autobuild.py:1951)
                      └─ _invoke_player_safely() (autobuild.py:3787)
                           └─ loop.run_until_complete(invoke_player())
                                └─ invoke_player() (agent_invoker.py:1071)
                                     └─ _invoke_with_role() (agent_invoker.py:1833)
                                          └─ asyncio.timeout(sdk_timeout_seconds) (line 1934)
                                               └─ query() from Claude Agent SDK (async generator)
                                                    └─ SDK subprocess with anyio internally
                                                         └─ anyio.CancelScope fires deadline
                                                              └─ CancelScope.cancel() at anyio/_backends/_asyncio.py:628
                                                                   └─ _cancel_reason = "Cancelled via cancel scope {id(self):x}"
                                                                        └─ CancelledError propagates up
```

### Key Technical Details

1. **asyncio.timeout()** (line 1934 in agent_invoker.py) wraps the `query()` streaming call
2. **anyio** (transitive dependency of claude-agent-sdk) wraps asyncio timeout with its own cancel scope
3. When `CancelScope.deadline` is exceeded, `cancel()` sets `_cancel_reason = f"Cancelled via cancel scope {id(self):x} by {task}"`
4. The CancelledError propagates through `_invoke_with_role()` → `invoke_player()` → `_invoke_player_safely()`
5. At each level, the error is caught and re-raised or converted to `AgentInvocationResult(success=False)`

### Why Cancellation Occurs Before SDK Timeout (6240s)

The cancellation intervals (6-41 minutes) are well below the 6240s SDK timeout because:
- The `asyncio.timeout(sdk_timeout_seconds)` context manager at line 1934 uses the **per-turn calculated timeout**
- But the anyio cancel scopes within the Claude SDK have their own deadlines
- When the SDK's internal streaming response takes too long (vLLM latency), anyio's cancel scope fires
- The cancel scope ID changes per turn because each `asyncio.timeout()` creates a new scope

### Thread Safety Issue

`asyncio.wait_for()` at the feature level cannot cancel the thread started by `asyncio.to_thread()`. The thread continues running even after the asyncio wrapper raises TimeoutError. The actual cancellation happens at the asyncio event loop level within the thread's `loop.run_until_complete()` call, where the SDK's anyio cancel scopes fire independently.

---

## Deep-Dive B: FBP-006 Turn Inflation (110 vs 43 SDK Turns)

### ~~Root Cause: vLLM Non-Determinism + Expanded Scope~~ CORRECTED: Slim Protocol (TASK-VOPT-001)

**CORRECTION (TASK-REV-35DC):** The primary root cause of SDK turn inflation is the **slim protocol** (TASK-VOPT-001), not vLLM non-determinism or the `--fresh` flag. Run 4 used the full 19KB protocol; Runs 5-6 used the slim 5.5KB protocol (5,587 bytes, ~131 lines). The slim protocol removes detailed stack-specific patterns (47 lines → 1 sentence), fix loop pseudocode (34 lines → 1 paragraph), anti-stub rules with examples (88 lines → 1 sentence), and SOLID/DRY/YAGNI explanations (48 lines → 1 checklist). Without this pedagogical guidance, the vLLM model needs more iterations to converge on acceptable output. All three runs used the same vLLM backend.

| Metric | Run 4 | Run 5 |
|--------|-------|-------|
| SDK turns | 43 | 110 (CEILING HIT) |
| Total messages | 104 | 259 |
| Duration | ~23m | 112m |
| Avg time/turn | ~32s | 61.4s |
| Files created | 7 | 7 |
| Files modified | 3 | 6 |
| Tests passing | 1 | 5 |
| **Protocol variant** | **Full (19KB)** | **Slim (5.5KB)** |

~~**Run 5's Player produced more comprehensive output** (5 passing tests vs 1, 6 modified files vs 3), requiring proportionally more SDK turns. This is **not a regression** — Run 5 delivered better coverage but at higher cost.~~

**Revised attribution**: The 43→110 turn increase is primarily caused by the slim protocol reducing guidance. FBP-006 (highest complexity at 6) is the most sensitive to the removed guidance (anti-stub rules, detailed test patterns, error handling examples).

### Ceiling Hit Mechanics

- Ceiling configured at 100 turns (`min(TASK_WORK_SDK_MAX_TURNS, 100)`)
- SDK doesn't interrupt mid-turn; Turn 110 completed before returning
- `sdk_ceiling.py:ceiling_hit`: `turns_used >= max_turns` → `110 >= 100` → True
- Coach approved despite ceiling hit because deliverables met quality gates

### Impact on Wave 5 Budget

FBP-006's extra 69 minutes (112m vs 43m) directly reduced FBP-007's budget from ~79 minutes to ~47 minutes — a 40% reduction that crossed the feasibility threshold.

---

## Deep-Dive C: FBP-007 Acceptance Criteria Convergence

### Turn-by-Turn Criteria Progression

```
Turn 1: 8/9 met (89%) — missing: AC-008 (no Any types)
Turn 2: 7/9 met (78%) — missing: AC-008, AC-009 (CI script)        ← REGRESSION
Turn 3: 8/9 met (89%) — missing: AC-008                             ← Recovery (perspective reset)
Turn 4: 1/9 met (11%) — CATASTROPHIC COLLAPSE                       ← Synthetic report corruption
Turn 5: 0/9 met (0%)  — COMPLETE FAILURE                            ← Report visibility lost
Turn 6: 0/9 met (0%)  — Identical to Turn 5
Turn 7: 5/9 met (56%) — Partial recovery (longer execution)
Turn 8: 0/9 met (0%)  — Collapse again → budget exhausted
```

### Three-Tier Failure Pattern

1. **Synthetic Report Corruption**: State recovery loads player_turn_N.json reliably, but `requirements_addressed` extraction from file content is non-deterministic. The Coach's hybrid fallback (promise matching → text matching) produces wildly varying results turn-to-turn.

2. **Oscillation, Not Convergence**: The system cannot accumulate progress. Each turn starts from a synthetic report that may or may not detect previous work. Turn 4's collapse from 8/9 to 1/9 and Turn 7's recovery from 0/9 to 5/9 show random re-entry into criteria assessment.

3. **State Pollution**: Turn 2 lost AC-009 (CI script) that was never a problem in Turn 1. Turn 4 lost 7 criteria simultaneously. The loaded state contains file lists and test counts but no execution context — the Coach cannot distinguish "criteria met but undetectable" from "criteria not met".

### Feasibility Assessment

| Criterion | Best Result | Feasible? |
|-----------|-------------|-----------|
| AC-001: ruff config | Met in Turns 3, 7 | Yes |
| AC-002: mypy config | Never met | Uncertain (config vs execution gap) |
| AC-003: pytest-cov config | Met in Turns 1-3, 7 | Yes |
| AC-004: ruff check | Met in Turn 7 | Yes |
| AC-005: ruff format | Met in Turn 7 | Yes |
| AC-006: mypy strict pass | Met only in Turn 7 | Marginal |
| AC-007: pytest coverage | Met in Turn 7 | Yes |
| AC-008: No Any types | **Never met in any turn** | **No** (for vLLM) |
| AC-009: CI script | Met in Turns 1, 3, 7 | Yes |

**AC-008 is the blocking criterion** — never achieved across 8 turns. Even in Turn 7 (best overall with 5/9), AC-008 remained unmet.

---

## Deep-Dive D: max_parallel=1 Impact

### Configuration Source

`guardkit/cli/autobuild.py:699-719`:
```python
# Auto-detect: default to 1 for local backends
# TASK-VPT-001: was 2, reduced due to KV cache contention
if detected_multiplier > 1.0:
    max_parallel = 1  # Explicitly 1 for vLLM
```

This was an **intentional reduction** from 2 to 1 after TASK-VPT-001 discovered GPU memory contention with concurrent vLLM requests.

### Budget Impact Calculation

| Scenario | FBP-007 Start | FBP-007 Budget | Outcome |
|----------|--------------|----------------|---------|
| max_parallel=1 (actual) | 18:15 (after FBP-006) | 2820s (47m) | FAILED |
| max_parallel=2 (parallel) | 16:22 (wave start) | 9600s (160m) | Likely SUCCESS |

With `max_parallel=2`, FBP-007 would have started immediately with the full 9600s budget — 3.4x more time than it actually received.

### Trade-off: KV Cache Contention vs Budget Starvation

- **max_parallel=1**: Safe for GPU memory, but creates budget starvation for later tasks in multi-task waves
- **max_parallel=2**: Risk of KV cache contention, but eliminates sequential budget consumption
- **No per-wave override exists** — the setting applies uniformly to all waves

---

## Deep-Dive E: Feature-Plan AC Generation

### No Feasibility Validation Exists

The `/feature-plan` command generates acceptance criteria through LLM-driven prompts with **no validation mechanism** for:
- Backend-appropriateness (cloud vs vLLM)
- Time-to-complete feasibility
- Complexity-to-strictness mapping
- Third-party library constraints (unavoidable `Any` types)

### AC Generation Chain

```
/feature-plan "description"
  → Creates review task
    → LLM generates task breakdown with acceptance criteria (NO VALIDATION)
      → Criteria written to task files
        → AutoBuild executes with those criteria
          → Coach validates against criteria (may be infeasible)
```

### Systemic Issue

The feature planning system generates AC without checking whether they are achievable with the target backend and within the task's time budget. For TASK-FBP-007, this produced:
- `mypy src/` strict mode with zero errors → Marginal feasibility with vLLM
- `All type annotations complete — no Any types` → **Infeasible** for vLLM (third-party stubs, dynamic patterns)

### Recommended Safeguards

1. **Backend-aware AC templates**: Adjust strictness for vLLM vs cloud
2. **Complexity-to-AC scoring**: Rate each criterion 1-10 feasibility, warn if average < 5
3. **Task-type-specific gates**: SCAFFOLDING (lenient) vs FEATURE (moderate) vs TESTING (coverage-only)
4. **Pre-flight AC validation**: Check AC against known backend limitations before AutoBuild starts

---

## Revised Decision Matrix

| Option | Reliability | Effort | Risk | Recommendation |
|--------|------------|--------|------|----------------|
| A: Increase task_timeout for Wave 5 | Low | Low | Low | Band-aid, doesn't fix root causes |
| B: Relax FBP-007 acceptance criteria | High | Low | Medium | Removes infeasible AC-008 |
| C: Move FBP-007 to separate wave (Wave 6) | High | Low | Low | Eliminates budget starvation |
| D: ~~Pass remaining_budget to invoke_player~~ | ~~High~~ | ~~Medium~~ | ~~Low~~ | **ALREADY IMPLEMENTED** (TASK-VRF-003) — see TASK-REV-35DC correction |
| E: Add backend-aware AC validation to feature-plan | Very High | High | Low | Prevents future infeasible AC |
| F: Explore max_parallel=2 with GPU memory guardrails | Medium | Medium | Medium | Eliminates serialization penalty |
| **G: B + C + D + E (phased)** | **Very High** | **High** | **Low** | **Recommended** |

---

## Revised Recommendations

### R1: Relax TASK-FBP-007 acceptance criteria (Priority: CRITICAL, Effort: LOW)

Remove AC-008 ("no Any types") entirely. Replace with: "Type annotations present on all public functions; mypy passes with `--disallow-untyped-defs` (not `--strict`)."

**Rationale**: AC-008 was never met in 8 turns. Third-party library stubs make zero-Any infeasible regardless of backend.

### R2: Separate FBP-007 into its own wave (Priority: HIGH, Effort: LOW)

Move TASK-FBP-007 from Wave 5 to Wave 6. With `max_parallel=1`, co-locating with FBP-006 creates deterministic budget starvation when FBP-006 runs long.

### R3: ~~Pass remaining_budget to invoke_player~~ ALREADY IMPLEMENTED (Priority: ~~HIGH~~ N/A, Effort: ~~MEDIUM~~ N/A)

**CORRECTION (TASK-REV-35DC):** This is already implemented via TASK-VRF-003. The `remaining_budget: Optional[float]` parameter exists at `agent_invoker.py:1144` and is used by `_calculate_sdk_timeout()` at line 3456 to cap the SDK timeout. COMPLETED — implemented before Run 5.

~~Add `remaining_budget: Optional[float]` parameter to `invoke_player()` and use `min(calculated_timeout, remaining_budget)` for SDK timeout. This matches the existing Coach behavior and prevents starting turns that cannot complete.~~

### R4: Add backend-aware AC validation to feature-plan (Priority: HIGH, Effort: HIGH)

Add pre-flight AC validation that:
- Detects backend type (vLLM vs cloud) from `timeout_multiplier`
- Flags infeasible criteria (mypy strict + zero Any for vLLM)
- Suggests relaxed alternatives during task generation
- Scores each AC on 1-10 feasibility scale

### R5: Fix synthetic report corruption in state recovery (Priority: MEDIUM, Effort: MEDIUM)

The turn-by-turn criteria oscillation (89% → 11% → 0% → 56% → 0%) indicates the synthetic report generation is fundamentally unreliable. Investigate:
- Why `requirements_addressed` extraction varies non-deterministically
- Whether promise matching failure should fall back differently
- Whether cumulative criteria state should persist across turns

### R6: Explore max_parallel=2 with safeguards (Priority: LOW, Effort: MEDIUM)

The TASK-VPT-001 reduction from 2→1 was for KV cache contention. Investigate:
- Whether vLLM's KV cache management has improved
- Whether a per-wave max_parallel override would help Wave 5 specifically
- Whether max_parallel=2 for the final wave only is safe

### R7: Correct task description (Priority: LOW, Effort: TRIVIAL)

Update TASK-REV-5E1F to reflect that both runs used `direct` mode, and that FBP-007 SDK timeout was 6240s (not 9360s) in Run 5.

---

## Appendix: Code References

| File | Lines | Purpose |
|------|-------|---------|
| `guardkit/orchestrator/agent_invoker.py` | 3162-3296 | Mode routing (deterministic auto-detection) |
| `guardkit/orchestrator/agent_invoker.py` | 3298-3381 | SDK timeout calculation |
| `guardkit/orchestrator/agent_invoker.py` | 1071-1081 | invoke_player (has remaining_budget param — TASK-VRF-003) |
| `guardkit/orchestrator/agent_invoker.py` | 1312-1319 | invoke_coach (has remaining_budget param) |
| `guardkit/orchestrator/feature_orchestrator.py` | 1473-1486 | Wave execution, task_budget calculation |
| `guardkit/orchestrator/autobuild.py` | 1718-1790 | Timeout decision tree in loop phase |
| `docs/reviews/vllm-profiling/vllm_run_5.md` | 1900, 2813 | FBP-007 mode routing + Coach rejection |
| `docs/reviews/vllm-profiling/vllm_run_4.md` | 3642 | FBP-007 mode routing (identical) |
| `guardkit/orchestrator/agent_invoker.py` | 1833-1995 | _invoke_with_role() — SDK call + cancel scope |
| `guardkit/orchestrator/agent_invoker.py` | 1934 | asyncio.timeout(sdk_timeout_seconds) context |
| `guardkit/orchestrator/autobuild.py` | 3787-3821 | _invoke_player_safely() — CancelledError handler |
| `guardkit/orchestrator/autobuild.py` | 159-170 | MIN_TURN_BUDGET_SECONDS constant |
| `guardkit/cli/autobuild.py` | 699-719 | max_parallel auto-detection (TASK-VPT-001) |
| `anyio/_backends/_asyncio.py` | 628 | CancelScope.cancel() — "Cancelled via cancel scope" origin |
| `installer/core/commands/feature-plan.md` | — | Feature plan command spec (no AC validation) |

---

## Addendum: Corrections Applied (TASK-VR6-5497, ref: TASK-REV-35DC)

The following corrections were applied on 2026-03-09 based on findings from the TASK-REV-35DC deep-dive analysis:

1. **Finding 3 corrected**: `invoke_player()` DOES accept `remaining_budget` parameter (TASK-VRF-003, `agent_invoker.py:1144`). The original claim that it did not was incorrect.
2. **R3 marked as ALREADY IMPLEMENTED**: The `remaining_budget` parameter was implemented via TASK-VRF-003 before Run 5. R3 is no longer actionable.
3. **Deep-Dive B attribution corrected**: SDK turn inflation (43→110 turns for FBP-006) is caused by the slim protocol (TASK-VOPT-001), not vLLM non-determinism or the `--fresh` flag. Run 4 used the full 19KB protocol; Runs 5-6 used the slim 5.5KB protocol.
