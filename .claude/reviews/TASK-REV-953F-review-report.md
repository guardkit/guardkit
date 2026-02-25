# Review Report: TASK-REV-953F (Revised — Deep Architectural Analysis)

## Executive Summary

The four DMCP fixes (001-004) are **correctly implemented, active at runtime, and introduce no regressions** (6676 unit tests pass). They fully fix the Run 1 root cause.

**Run 2 failed for TWO distinct and previously unidentified reasons:**

1. **Turn 1**: The vLLM Player did not produce a structured `player_turn_1.json` report (the DMCP fixes address a *different* scenario where the report exists but data is lost in transit)
2. **Turns 2-3**: A **state recovery gap** — the autobuild orchestrator recovers synthetic data in memory after Player failure, but **never writes it to `task_work_results.json` on disk**. The Coach reads the stale ERROR-flagged version and short-circuits without evaluating criteria.

Both issues are **architectural gaps in the synthetic report pipeline** that were invisible when the Player reliably writes reports (MacBook + Anthropic API). They only surface when the Player fails to write a report (vLLM token exhaustion, SDK turn limits).

## C4 Architecture

### Level 1: System Context

```
┌─────────────────────────────────────────────────────────┐
│                     User / CI                           │
│  guardkit autobuild feature FEAT-3CC2 --verbose --fresh │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│              GuardKit AutoBuild System                   │
│                                                         │
│  Orchestrates Player→Coach adversarial loop             │
│  Quality gates: tests, coverage, criteria matching      │
│  Timeout management, state recovery, stall detection    │
└─────────────────────┬───────────────────────────────────┘
                      │
              ┌───────┴───────┐
              ▼               ▼
┌─────────────────┐ ┌─────────────────┐
│   LLM Backend   │ │   Worktree /    │
│                 │ │   Filesystem    │
│ Anthropic API   │ │                 │
│ OR vLLM local   │ │ player_turn.json│
│                 │ │ task_work_res.  │
│ (via Claude     │ │ coach_turn.json │
│  Agent SDK)     │ │                 │
└─────────────────┘ └─────────────────┘
```

### Level 2: Container Diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│                       GuardKit AutoBuild                             │
│                                                                      │
│  ┌────────────────────┐        ┌────────────────────────┐           │
│  │FeatureOrchestrator │        │ AutoBuildOrchestrator   │           │
│  │                    │───────▶│                         │           │
│  │ • Wave management  │ per    │ • Turn loop (Player→    │           │
│  │ • Task timeout     │ task   │   Coach)                │           │
│  │   (2400s)          │        │ • Stall detection       │           │
│  │ • Cooperative      │        │ • State recovery        │           │
│  │   cancellation     │        │ • Checkpoint/rollback   │           │
│  └────────────────────┘        └──────┬──────┬──────────┘           │
│                                       │      │                       │
│                               ┌───────┘      └──────┐               │
│                               ▼                      ▼               │
│  ┌────────────────────────────────┐ ┌────────────────────────────┐  │
│  │      AgentInvoker              │ │     CoachValidator         │  │
│  │                                │ │                            │  │
│  │ • invoke_player_direct()       │ │ • validate()               │  │
│  │ • SDK subprocess management    │ │ • read_quality_gate_results│  │
│  │ • Report detection             │ │ • validate_requirements()  │  │
│  │ • Synthetic report creation    │ │ • _match_by_promises()     │  │
│  │ • _write_direct_mode_results() │ │ • _match_by_text()         │  │
│  │ • _write_player_report()       │ │ • _hybrid_fallback()       │  │
│  └───────────┬────────────────────┘ └────────────┬───────────────┘  │
│              │                                    │                   │
│              ▼                                    ▼                   │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                    Filesystem Artifacts                      │    │
│  │                                                             │    │
│  │  .guardkit/autobuild/{task_id}/                             │    │
│  │    ├── player_turn_{N}.json    ← Written by AgentInvoker    │    │
│  │    ├── task_work_results.json  ← Written by AgentInvoker    │    │
│  │    ├── coach_turn_{N}.json     ← Written by CoachValidator  │    │
│  │    └── work_state_turn_{N}.json← Written by StateTracker    │    │
│  └─────────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────────┘
```

### Level 3: Component — Criteria Pipeline (The Critical Path)

```
┌─────────────────────────────────────────────────────────────────────┐
│                    CRITERIA VERIFICATION PIPELINE                     │
│                                                                      │
│  Three data sources feed into Coach validation:                      │
│                                                                      │
│  SOURCE 1: task_work_results.json (on disk)                         │
│    ├── requirements_addressed: [...]  ← For text matching           │
│    ├── requirements_met: [...]        ← Legacy fallback             │
│    ├── completion_promises: [...]     ← For promise matching        │
│    ├── _synthetic: bool               ← Routes to synthetic path    │
│    └── error: str (optional)          ← Short-circuits validation!  │
│                                                                      │
│  SOURCE 2: player_turn_{N}.json (on disk)                           │
│    └── completion_promises: [...]     ← Loaded via backward scan    │
│                                                                      │
│  SOURCE 3: task (in memory, from autobuild)                         │
│    └── acceptance_criteria: [...]     ← The standard to verify      │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                 CoachValidator.validate_requirements()         │   │
│  │                                                               │   │
│  │  ┌─────────────────────┐                                      │   │
│  │  │ _synthetic == True? │──YES──▶ SYNTHETIC FAST-PATH          │   │
│  │  └─────────┬───────────┘        │                             │   │
│  │            NO                   │ _load_completion_promises()  │   │
│  │            ▼                    │   ├── promises? → match      │   │
│  │  ┌─────────────────────┐       │   └── no promises? → ALL     │   │
│  │  │ completion_promises │       │       CRITERIA REJECTED       │   │
│  │  │ exist?              │       │                               │   │
│  │  └─────────┬───────────┘       │ ⚠ NO text fallback!          │   │
│  │       YES  │   NO              │ ⚠ NO hybrid fallback!        │   │
│  │        ▼   │    ▼              └──────────────────────────────│   │
│  │  PROMISES  │  TEXT MATCHING                                    │   │
│  │  MATCHING  │  (DMCP-002 fixed)                                │   │
│  │   │        │    │                                              │   │
│  │   │not all │    └─▶ _match_by_text(requirements_addressed)    │   │
│  │   │met?    │                                                   │   │
│  │   ▼        │                                                   │   │
│  │  HYBRID    │                                                   │   │
│  │  FALLBACK  │                                                   │   │
│  │  (text +   │                                                   │   │
│  │   promises)│                                                   │   │
│  └────────────┴──────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────┘
```

**Critical architectural insight**: The synthetic fast-path at `coach_validator.py:1506-1550` has **NO text matching fallback**. If promises exist but are insufficient, there's no second chance. If no promises exist, everything is immediately rejected. This is by design (synthetic reports have unreliable data), but it means the synthetic path is much stricter than the normal path.

### Level 4: Sequence Diagrams

#### Sequence A: MacBook / Anthropic API (Working Path)

```
Feature        AutoBuild       AgentInvoker       SDK/Claude        CoachValidator
  │               │                 │                  │                  │
  │──execute──▶   │                 │                  │                  │
  │               │──Turn 1──▶      │                  │                  │
  │               │                 │──invoke_direct──▶│                  │
  │               │                 │                  │──runs Player──▶  │
  │               │                 │                  │  (writes code)   │
  │               │                 │                  │  (writes tests)  │
  │               │                 │                  │  (writes         │
  │               │                 │                  │   player_turn_   │
  │               │                 │                  │   1.json with    │
  │               │                 │                  │   requirements_  │
  │               │                 │                  │   addressed AND  │
  │               │                 │                  │   completion_    │
  │               │                 │                  │   promises)      │
  │               │                 │◀─────────────────│                  │
  │               │                 │                  │                  │
  │               │                 │ Report EXISTS ✓  │                  │
  │               │                 │ Load report      │                  │
  │               │                 │ Write task_work_ │                  │
  │               │                 │  results.json    │                  │
  │               │                 │  (DMCP-001 copies│                  │
  │               │                 │   requirements_  │                  │
  │               │                 │   addressed) ✓   │                  │
  │               │◀────────────────│                  │                  │
  │               │                 │                  │                  │
  │               │──Coach──────────│──────────────────│──────────▶       │
  │               │                 │                  │           │      │
  │               │                 │                  │  Reads task_work │
  │               │                 │                  │  _results.json   │
  │               │                 │                  │  • _synthetic:   │
  │               │                 │                  │    False          │
  │               │                 │                  │  → NORMAL PATH   │
  │               │                 │                  │  → Has promises? │
  │               │                 │                  │    YES → match   │
  │               │                 │                  │    7/7 ✓         │
  │               │                 │                  │  → APPROVE       │
  │               │◀────────────────│──────────────────│──────────│       │
  │               │                 │                  │                  │
  │◀──COMPLETED───│                 │                  │                  │
```

#### Sequence B: GB10 / vLLM Run 2 Turn 1 (Synthetic Path — No Report)

```
Feature        AutoBuild       AgentInvoker       SDK/vLLM          CoachValidator
  │               │                 │                  │                  │
  │──execute──▶   │                 │                  │                  │
  │               │──Turn 1──▶      │                  │                  │
  │               │                 │──invoke_direct──▶│                  │
  │               │                 │                  │──runs Player──▶  │
  │               │                 │                  │  (writes 12+19   │
  │               │                 │                  │   files, 720s)   │
  │               │                 │                  │                  │
  │               │                 │                  │  ╔═══════════╗   │
  │               │                 │                  │  ║ Does NOT  ║   │
  │               │                 │                  │  ║ write     ║   │
  │               │                 │                  │  ║ player_   ║   │
  │               │                 │                  │  ║ turn_1.   ║   │
  │               │                 │                  │  ║ json!     ║   │
  │               │                 │                  │  ╚═══════════╝   │
  │               │                 │◀─────────────────│                  │
  │               │                 │                  │                  │
  │               │                 │ Report MISSING ✗ │                  │
  │               │                 │ Create SYNTHETIC │                  │
  │               │                 │  _synthetic: True│                  │
  │               │                 │  requirements_   │                  │
  │               │                 │   addressed: []  │                  │
  │               │                 │  promises: [7    │                  │
  │               │                 │   file-existence]│                  │
  │               │                 │                  │                  │
  │               │                 │ Write task_work_ │                  │
  │               │                 │  results.json    │                  │
  │               │                 │  (from synthetic │                  │
  │               │                 │   — all empty)   │                  │
  │               │◀────────────────│                  │                  │
  │               │                 │                  │                  │
  │               │──Coach──────────│──────────────────│──────────▶       │
  │               │                 │                  │  Reads task_work │
  │               │                 │                  │  _results.json   │
  │               │                 │                  │  • _synthetic:   │
  │               │                 │                  │    True           │
  │               │                 │                  │  → SYNTHETIC     │
  │               │                 │                  │    FAST-PATH     │
  │               │                 │                  │  → Has promises? │
  │               │                 │                  │    YES (7 file-  │
  │               │                 │                  │    existence)    │
  │               │                 │                  │  → match: 1/7 ✗ │
  │               │                 │                  │                  │
  │               │                 │                  │  ⚠ NO TEXT       │
  │               │                 │                  │    FALLBACK ON   │
  │               │                 │                  │    SYNTHETIC     │
  │               │                 │                  │    PATH!         │
  │               │                 │                  │  → FEEDBACK      │
  │               │◀────────────────│──────────────────│──────────│       │
```

#### Sequence C: GB10 / vLLM Run 2 Turn 2 (State Recovery Gap — THE BUG)

```
Feature        AutoBuild       AgentInvoker       SDK/vLLM          CoachValidator
  │               │                 │                  │                  │
  │               │──Turn 2──▶      │                  │                  │
  │               │                 │──invoke_direct──▶│                  │
  │               │                 │                  │──runs Player──▶  │
  │               │                 │                  │  ... 1440s ...   │
  │               │                 │                  │  SDK TIMEOUT ⏱   │
  │               │                 │◀──SDKTimeoutError│                  │
  │               │                 │                  │                  │
  │               │                 │ Writes ERROR     │                  │
  │               │                 │ task_work_results│                  │
  │               │                 │  .json:          │                  │
  │               │                 │  {               │                  │
  │               │                 │   success: false │                  │
  │               │                 │   error: "SDK    │                  │
  │               │                 │    timeout..."   │◀── ⚠ Has "error"│
  │               │                 │   requirements_  │      key!       │
  │               │                 │    addressed: [] │                  │
  │               │                 │  }               │                  │
  │               │◀──error result──│                  │                  │
  │               │                 │                  │                  │
  │               │ STATE RECOVERY  │                  │                  │
  │               │ ┌──────────────┐│                  │                  │
  │               │ │Git detection ││                  │                  │
  │               │ │67 tests found││                  │                  │
  │               │ │Build         ││                  │                  │
  │               │ │synthetic rpt ││                  │                  │
  │               │ │IN MEMORY     ││                  │                  │
  │               │ │              ││                  │                  │
  │               │ │╔════════════╗││                  │                  │
  │               │ │║ Does NOT   ║││                  │                  │
  │               │ │║ write to   ║││                  │                  │
  │               │ │║ task_work_ ║││                  │                  │
  │               │ │║ results.   ║││                  │                  │
  │               │ │║ json!      ║││                  │                  │
  │               │ │╚════════════╝││                  │                  │
  │               │ └──────────────┘│                  │                  │
  │               │                 │                  │                  │
  │               │ player_result = │                  │                  │
  │               │  recovered      │                  │                  │
  │               │  (in memory)    │                  │                  │
  │               │                 │                  │                  │
  │               │──Coach──────────│──────────────────│──────────▶       │
  │               │                 │                  │                  │
  │               │                 │                  │  Reads task_work │
  │               │                 │                  │  _results.json   │
  │               │                 │                  │  FROM DISK       │
  │               │                 │                  │                  │
  │               │                 │                  │  Finds: {"error":│
  │               │                 │                  │   "SDK timeout"} │
  │               │                 │                  │                  │
  │               │                 │                  │  "error" in dict │
  │               │                 │                  │  → SHORT-CIRCUIT │
  │               │                 │                  │  → "Task-work    │
  │               │                 │                  │    results not   │
  │               │                 │                  │    found"        │
  │               │                 │                  │                  │
  │               │                 │                  │  ⚠ NEVER         │
  │               │                 │                  │    EVALUATES     │
  │               │                 │                  │    CRITERIA!     │
  │               │                 │                  │  → FEEDBACK      │
  │               │◀────────────────│──────────────────│──────────│       │
```

## Findings (Revised with Architectural Context)

### Finding 1: All DMCP Fixes Are Present and Active — No Regressions

All four fixes confirmed. 6676 unit tests pass. See original report for details.

### Finding 2 (ROOT CAUSE 1): vLLM Player Does Not Write Report — Synthetic Fallback Triggered

**Severity**: Critical | **Files**: `agent_invoker.py:2640-2691`

The `invoke_player_direct` method at line 2640 calls `_invoke_with_role()` which runs the Claude Agent SDK subprocess. The SDK subprocess is expected to write `player_turn_{N}.json` to disk as part of its execution protocol. After the SDK returns, `agent_invoker.py:2656-2657` checks:

```python
report_path = self._get_report_path(task_id, turn, "player")
if not report_path.exists():
    # → SYNTHETIC PATH
```

**Why this works on MacBook**: The Anthropic API backend is fast enough and reliable enough that the model completes the full execution protocol including writing the structured report. The model has sufficient context window and tokens to finish.

**Why this fails on GB10/vLLM**: The vLLM model in Run 2 spent ~720s creating 31 file changes (12 created + 19 modified) but exhausted its tokens/turns before writing the structured JSON report. The `--fresh` flag forced the model to scaffold everything from scratch, requiring more tokens than Run 1 (where it had existing code).

**Evidence**: Run 1 Turn 1 (no `--fresh`): 1 created, 3 modified, report written. Run 2 Turn 1 (`--fresh`): 12 created, 19 modified, report NOT written.

**Architectural implication**: The report-writing step is delegated to the AI agent as an in-band operation. If the agent runs out of tokens/turns before reaching this step, there is no structured data to flow through the pipeline. This is a fundamental vulnerability in the direct-mode architecture.

### Finding 3 (ROOT CAUSE 2 — NEW): State Recovery Does Not Update `task_work_results.json` on Disk

**Severity**: Critical | **Files**: `autobuild.py:1844-1855` + `coach_validator.py:585-586`

When the Player fails (e.g., SDK timeout), the autobuild orchestrator runs `_attempt_state_recovery()` at line 1844. State recovery:
1. Detects changes via git (`MultiLayeredStateTracker`)
2. Builds a synthetic report via `_build_synthetic_report()` (lines 2238-2363)
3. Returns an `AgentInvocationResult` with the synthetic report
4. The autobuild replaces `player_result` **in memory** (line 1855)

**The bug**: State recovery does NOT write the recovered synthetic data to `task_work_results.json` on disk. The `task_work_results.json` still contains the ERROR version written by the agent_invoker's exception handler (with `"error": "SDK timeout..."` key).

When the Coach then calls `read_quality_gate_results()` at line 583, it reads the ERROR version. At line 585, `"error" in task_work_results` is True → the Coach logs "Task-work results not found" (misleading message — the file exists, it just contains an error) and returns feedback **without ever evaluating criteria**.

```python
# autobuild.py:1855 — memory only, disk NOT updated
player_result = recovered_player_result  # ← In-memory update

# coach_validator.py:583-586 — reads from DISK
task_work_results = self.read_quality_gate_results(task_id)  # ← Reads stale ERROR file
if "error" in task_work_results:  # ← True! Error from timeout handler
    logger.warning(f"Task-work results not found for {task_id}")
    return self._feedback_result(...)  # ← Short-circuits, no criteria evaluation
```

**This bug means Turn 2 NEVER has a chance to verify criteria.** Even though state recovery detected 67 tests and built file-existence promises, none of this data reaches the Coach.

### Finding 4: Synthetic Fast-Path Has No Text Matching Fallback (By Design, But Limits Recovery)

**Severity**: High | **File**: `coach_validator.py:1506-1550`

The synthetic fast-path deliberately skips text matching and hybrid fallback. The normal path has three strategies:
1. Promise matching → 2. Hybrid fallback (promises + text) → 3. Text matching

The synthetic path has only:
1. Promise matching → 2. All rejected (if no promises)

This design choice means that even if synthetic reports carried `requirements_addressed` data, it would be ignored. File-existence promises are the ONLY verification mechanism on the synthetic path.

**Architectural rationale**: Synthetic reports have unreliable data (auto-detected, not Player-verified), so giving them a text-matching path could produce false positives. However, this also means the synthetic path can never verify content-based criteria (e.g., "Settings class has log_level field").

### Finding 5: Three Distinct Synthetic Report Paths (Not One)

**Severity**: High (Complexity) | **Category**: Architecture

The codebase has THREE different synthetic report creation paths:

| Path | Trigger | Location | Writes task_work_results? | Used in |
|------|---------|----------|---------------------------|---------|
| **A** | SDK returns normally but no report file | `agent_invoker.py:2657-2691` | YES (from synthetic data) | Run 2 Turn 1 |
| **B** | Player error → state recovery | `autobuild.py:1844-2363` | **NO** (stale error version remains) | Run 2 Turn 2 |
| **C** | Task-work delegation path | `agent_invoker.py:1520-1740` | YES (enriched during write) | Not used in direct mode |

Path B has the state recovery gap described in Finding 3. Path A works correctly but the synthetic data has limited verification power. Path C is not relevant to direct mode.

### Finding 6: Cancellation Architecture Works Cooperatively, Not Preemptively

**Severity**: High | **Files**: `feature_orchestrator.py:1271-1296`, `autobuild.py:1547,1583,1890`

The cancellation mechanism:
1. `feature_orchestrator.py:1277` wraps task execution in `asyncio.wait_for(..., timeout=self.task_timeout)`
2. When timeout fires, `asyncio.TimeoutError` is raised
3. `feature_orchestrator.py:1295` sets `cancel_event.set()` in the `finally` block
4. `autobuild.py` checks `_cancellation_event.is_set()` at three points:
   - Top of turn loop (line 1547)
   - Between Player and Coach (line 1890)
   - After turn completes (line 1583)

**The gap**: If the Player SDK subprocess is running when timeout fires, the thread is **blocked on the subprocess** and cannot check the cancellation event. The `asyncio.wait_for` only cancels the asyncio wrapper; the underlying OS thread (via `asyncio.to_thread`) and its SDK subprocess continue.

The SDK subprocess only terminates when:
- It naturally completes (Run 2 Turn 3: 690s after timeout)
- It hits its own SDK timeout (1440s)

**Evidence**: Run 2 Turn 3 — feature timeout at 2400s (line 216), Player still logging at 540s elapsed (line 277), RuntimeWarning about threads at 300s (line 228), Player finally completes and writes files at 690s (line 283). The CANCELLED detection happens at line 288 when the autobuild finally reaches the between-Player-and-Coach checkpoint.

### Finding 7: Misleading "Task-work results not found" Log Message

**Severity**: Medium | **File**: `coach_validator.py:585-586`

```python
if "error" in task_work_results:
    logger.warning(f"Task-work results not found for {task_id}")
```

This logs "not found" when the file EXISTS but contains an `"error"` key. The actual meaning is "task-work results contain an error" — but the log message makes it appear the file is missing, which misdirects debugging efforts. The task description for TASK-REV-953F was partially misled by this message.

### Finding 8: DMCP Fixes Improved the Synthetic Path (Partial Success)

Run 2 Turn 1 verified 1/7 criteria (vs 0/7 in all Run 1 turns). DMCP-003 propagated `_synthetic: True`, and DMCP-004 enabled file-existence promise generation. This is real progress, but insufficient for content-based criteria.

## Why MacBook Builds Work

```
MacBook + Anthropic API:
  ┌──────────┐    ┌──────────────┐    ┌──────────────┐
  │  Player   │───▶│ Writes report│───▶│ Coach reads  │
  │  completes│    │ with data    │    │ real data    │
  │  quickly  │    │ (requirements│    │ → APPROVE    │
  │  (<400s)  │    │  addressed,  │    │              │
  │           │    │  promises)   │    │              │
  └──────────┘    └──────────────┘    └──────────────┘

GB10 + vLLM:
  ┌──────────┐    ┌──────────────┐    ┌──────────────┐
  │  Player   │───▶│ NO report!   │───▶│ Coach reads  │
  │  exhausts │    │ Synthetic    │    │ synthetic    │
  │  tokens   │    │ fallback     │    │ (empty reqs, │
  │  (720s+)  │    │ (no reqs,    │    │  file-exist  │
  │           │    │  file-exist  │    │  only)       │
  │           │    │  only)       │    │ → FEEDBACK   │
  └──────────┘    └──────────────┘    └──────────────┘
```

The key architectural difference: on MacBook, the Player always writes a structured report, so the DMCP-fixed pipeline works end-to-end. On GB10/vLLM, the Player sometimes doesn't write a report, exposing the synthetic fallback path which has limited verification capability and a state recovery bug.

## Regression Assessment

**Verdict: No regressions from DMCP fixes.**

| Test Suite | Result |
|------------|--------|
| `test_agent_invoker.py` | 407 passed |
| `test_coach_validator.py` | 230 passed |
| All unit tests | 6676 passed, 6 failed (pre-existing in `test_task_769d_ai_analyzer.py`) |

## Recommendations (Revised)

### P1 (CRITICAL): Commit DMCP Fixes — Correct and Tested

No change from initial assessment. The fixes address the Run 1 root cause and should be committed.

### P2 (CRITICAL — NEW): State Recovery Must Write `task_work_results.json`

**File**: `guardkit/orchestrator/autobuild.py`
**Location**: `_execute_turn()` after state recovery succeeds (~line 1855)

After `_attempt_state_recovery()` returns a recovered `player_result`, write the recovered data to `task_work_results.json` so the Coach can read it:

```python
# After line 1855: player_result = recovered_player_result
if recovered_player_result:
    player_result = recovered_player_result
    # NEW: Write recovered data to disk so Coach can read it
    self._agent_invoker._write_direct_mode_results(
        task_id, player_result.report, success=True
    )
```

**Impact**: Fixes Turn 2+ criteria verification after Player failure. The Coach would see the recovered synthetic data instead of the stale ERROR version.
**Effort**: Low (3 lines)
**Risk**: Low (uses existing method)

### P3 (HIGH): Fix Misleading "not found" Log When Error Key Present

**File**: `guardkit/orchestrator/quality_gates/coach_validator.py`
**Location**: Line 585-586

```python
# Change:
logger.warning(f"Task-work results not found for {task_id}")
# To:
logger.warning(
    f"Task-work results for {task_id} contain error: "
    f"{task_work_results.get('error', 'unknown')}"
)
```

**Effort**: Trivial
**Risk**: None

### P4 (HIGH): Cancel SDK Subprocess on Feature Timeout

**File**: `guardkit/orchestrator/feature_orchestrator.py`
**Location**: `_execute_wave()` timeout handling (~line 1300)

When `asyncio.TimeoutError` is caught, the feature orchestrator should:
1. Set the cancellation event (already done at line 1295)
2. Additionally, terminate the SDK subprocess by sending SIGTERM to the Claude Code process

This requires the `AgentInvoker` to expose a `cancel()` method that terminates the current SDK subprocess. The `claude_agent_sdk` likely provides a way to cancel an active `query()` invocation.

**Impact**: Prevents GPU waste (480s of unused vLLM inference in Run 2)
**Effort**: Medium
**Risk**: Low

### P5 (MEDIUM): Investigate vLLM Report Non-Production

Before implementing complex workarounds for missing reports, investigate why the vLLM model doesn't write the report:

1. Check `TASK_WORK_SDK_MAX_TURNS` (used at `agent_invoker.py:1446`) — is the model running out of internal SDK turns?
2. Check if the execution protocol prompt is in the CLAUDE.md of the worktree — does the Player know it should write the report?
3. Consider adding a final "WRITE YOUR REPORT NOW" instruction as a system-level constraint rather than relying on the model to remember

**Impact**: Fixing report production would make the DMCP fixes work end-to-end on vLLM
**Effort**: Low (investigation) to Medium (fix)
**Risk**: Low

### P6 (MEDIUM): Enhance `build_synthetic_report` to Include `requirements_addressed`

**File**: `guardkit/orchestrator/synthetic_report.py`
**Location**: `build_synthetic_report()` line 91

Currently `requirements_addressed: []` is hardcoded. For the agent_invoker synthetic path (Path A), the synthetic report could attempt to extract requirements from:
1. The SDK conversation transcript (if accessible)
2. Test output matching against acceptance criteria
3. File content grep for criterion keywords

**Effort**: Medium-High
**Risk**: Medium (false positives)

### P7 (LOW): Eliminate Double-Write of `player_turn_N.json`

No change from initial assessment. Trivial fix, very low risk.

## Decision Matrix (Revised)

| # | Fix | Impact | Effort | Risk | Addresses |
|---|-----|--------|--------|------|-----------|
| **P1** | Commit DMCP fixes | Critical | Done | None | Run 1 root cause |
| **P2** | State recovery writes task_work_results.json | **Critical** | **Low (3 lines)** | Low | **Run 2 Turn 2+ failure** |
| **P3** | Fix misleading "not found" log | High | Trivial | None | Debugging clarity |
| **P4** | Cancel SDK subprocess on timeout | High | Medium | Low | Resource waste, race conditions |
| **P5** | Investigate vLLM report non-production | Medium | Low-Medium | Low | Run 2 Turn 1 root cause |
| **P6** | Enhance synthetic requirements | Medium | Medium-High | Medium | Synthetic path quality |
| **P7** | Eliminate double player report write | Low | Trivial | Very Low | Code cleanliness |

**P1 + P2 together would fix the most critical gap.** P2 is a 3-line fix that would have allowed Turn 2 to evaluate criteria instead of short-circuiting.

## Appendix: Run 2 Turn-by-Turn Data Flow

### Turn 1 (Synthetic Path A)

| Step | Component | Action | File Written | Key Data |
|------|-----------|--------|--------------|----------|
| 1 | SDK/vLLM | Player runs 720s | 12+19 source files | No report file |
| 2 | AgentInvoker | Detects missing report | — | `report_path.exists() == False` |
| 3 | AgentInvoker | Creates synthetic | — | `_synthetic: True`, `requirements_addressed: []`, 7 promises |
| 4 | AgentInvoker | Writes synthetic report | `player_turn_1.json` | Synthetic data |
| 5 | AgentInvoker | Loads from disk | — | Same synthetic data |
| 6 | AgentInvoker | Writes results | `task_work_results.json` | `_synthetic: True`, `requirements_addressed: []`, 7 promises |
| 7 | AgentInvoker | Overwrites report | `player_turn_1.json` | Same data (double write) |
| 8 | CoachValidator | Reads results from disk | — | Sees `_synthetic: True` |
| 9 | CoachValidator | Synthetic fast-path | — | Loads 7 file-existence promises |
| 10 | CoachValidator | Promise matching | — | 1/7 verified, 6 content-based criteria unverifiable |
| 11 | CoachValidator | Returns feedback | `coach_turn_1.json` | "6 criteria not met" |

### Turn 2 (State Recovery Gap — Path B)

| Step | Component | Action | File Written | Key Data |
|------|-----------|--------|--------------|----------|
| 1 | SDK/vLLM | Player runs 1440s | some source files | SDK timeout |
| 2 | AgentInvoker | Catches SDKTimeoutError | `task_work_results.json` | **`"error": "SDK timeout..."`**, `success: false` |
| 3 | AgentInvoker | Writes error report | `player_turn_2.json` | Error data |
| 4 | AgentInvoker | Returns error result | — | `success=False` |
| 5 | AutoBuild | State recovery starts | — | Detects 67 tests |
| 6 | AutoBuild | Builds synthetic report | — | **IN MEMORY ONLY** |
| 7 | AutoBuild | Replaces player_result | — | In-memory update |
| 8 | AutoBuild | **Does NOT write results** | ⚠ **NO WRITE** | **task_work_results.json still has ERROR from step 2** |
| 9 | CoachValidator | Reads results from disk | — | Finds `"error"` key |
| 10 | CoachValidator | Short-circuits | — | "Task-work results not found" |
| 11 | CoachValidator | Returns feedback | `coach_turn_2.json` | Timeout feedback (no criteria evaluated) |

### Turn 3 (Cancellation Race)

| Step | Component | Action | File Written | Key Data |
|------|-----------|--------|--------------|----------|
| 1 | SDK/vLLM | Player starts | — | ~240s elapsed when timeout fires |
| 2 | FeatureOrch | Task timeout (2400s total) | — | Sets cancellation event |
| 3 | FeatureOrch | Declares FAILED | — | Prints summary |
| 4 | SDK/vLLM | **Still running** | — | Not cancelled, continues to 690s |
| 5 | SDK/vLLM | Eventually completes | `task_work_results.json`, `player_turn_3.json` | 2 created, 2 modified |
| 6 | AutoBuild | Detects cancellation | — | Between Player and Coach |
| 7 | AutoBuild | Returns CANCELLED | — | Turn not evaluated |
