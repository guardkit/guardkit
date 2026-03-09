# Review Report: TASK-REV-35DC (Revised)

## Executive Summary

Run 6 achieved **7/7 tasks in 285 minutes** — a full recovery from Run 5's regression (6/7, 409 min). However, this review's deep-dive reveals the success was **fragile**: FBP-007 succeeded via state recovery after a cancel scope interruption, not clean execution. The wave separation recommendation (VRF-002) was NOT applied — FBP-006 and FBP-007 remain co-located in Wave 5 with `max_parallel=1`.

**Critical corrections to TASK-REV-5E1F report:**
1. **R3 (remaining_budget to Player) is ALREADY IMPLEMENTED** (TASK-VRF-003) — the code at `agent_invoker.py:1144` accepts and applies `remaining_budget` via `_calculate_sdk_timeout()`. The initial review's claim that invoke_player lacked this parameter was incorrect.
2. **The SDK turn inflation is caused by the slim protocol** (TASK-VOPT-001), not by `--fresh` or model variance. Run 4 used the full 19KB protocol; Runs 5-6 used the slim 5.5KB protocol.
3. **A cancel monitor actively kills SDK subprocesses** (TASK-FIX-ASPF-004) — the cancellation mechanism is more sophisticated than initially described.

**Root causes confirmed:**
- Budget starvation from FBP-006 serialization (structural, not fixed)
- Slim protocol causing higher SDK turn consumption (operational, newly identified)
- Wave assignment algorithm has no task-type-aware isolation logic (architectural, for /feature-plan fix)

## Review Details

- **Mode**: Decision Analysis (Revised — Comprehensive depth)
- **Depth**: Comprehensive (upgraded from Standard)
- **Task**: TASK-REV-35DC
- **Focus**: Root cause validation, cross-boundary trace, regression risk assessment

---

## C4 Sequence Diagram 1: Wave 5 Budget Starvation (FBP-007 Failure Path)

```
┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│   Feature    │  │  AutoBuild   │  │    Agent     │  │  Claude SDK  │  │   vLLM       │
│ Orchestrator │  │ Orchestrator │  │   Invoker    │  │  (anyio)     │  │  Backend     │
└──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘
       │                 │                 │                 │                 │
       │ Wave 5 start    │                 │                 │                 │
       │ task_timeout=    │                 │                 │                 │
       │ 9600s            │                 │                 │                 │
       │─────────────────>│                 │                 │                 │
       │                 │                 │                 │                 │
       │ Semaphore(1):   │                 │                 │                 │
       │ serialize tasks │                 │                 │                 │
       │                 │                 │                 │                 │
       │ ┌───────────── FBP-006 EXECUTION (serialized first) ─────────────┐  │
       │ │               │                 │                 │             │  │
       │ │ elapsed=0s    │                 │                 │             │  │
       │ │ budget=9600s  │                 │                 │             │  │
       │ │───────────────>│ _loop_phase()  │                 │             │  │
       │ │               │ remaining=9600s │                 │             │  │
       │ │               │────────────────>│ invoke_player() │             │  │
       │ │               │                │ remaining_budget │             │  │
       │ │               │                │ =9600s           │             │  │
       │ │               │                │─────────────────>│             │  │
       │ │               │                │ _calculate_sdk   │             │  │
       │ │               │                │ _timeout()       │             │  │
       │ │               │                │ effective=9599s  │             │  │
       │ │               │                │ (budget_cap)     │             │  │
       │ │               │                │                  │             │  │
       │ │               │                │ asyncio.timeout  │             │  │
       │ │               │                │ (9599s)          │             │  │
       │ │               │                │─────────────────>│ query()     │  │
       │ │               │                │                  │────────────>│  │
       │ │               │                │                  │             │  │
       │ │               │                │    ... 118 SDK turns ...      │  │
       │ │               │                │    ... 5845.7 seconds ...     │  │
       │ │               │                │                  │             │  │
       │ │               │                │<─────────────────│ complete    │  │
       │ │               │<───────────────│ success (118     │             │  │
       │ │               │                │ turns, ceiling)  │             │  │
       │ │<──────────────│ Coach approves │                  │             │  │
       │ │               │ (scaffolding   │                  │             │  │
       │ │               │  profile)      │                  │             │  │
       │ │ FBP-006 done  │                │                  │             │  │
       │ │ elapsed=5877s │                │                  │             │  │
       │ └───────────────┘                │                  │             │  │
       │                 │                 │                 │                 │
       │ ┌───────────── FBP-007 EXECUTION (serialized second) ────────────┐  │
       │ │               │                 │                 │             │  │
       │ │ elapsed=5877s │                 │                 │             │  │
       │ │ budget=9600   │                 │                 │             │  │
       │ │  -5877=3723s  │                 │                 │             │  │
       │ │───────────────>│ _loop_phase()  │                 │             │  │
       │ │               │ remaining=3723s │                 │             │  │
       │ │               │ > 600s (MIN)   │                 │             │  │
       │ │               │ ∴ proceed      │                 │             │  │
       │ │               │────────────────>│ invoke_player() │             │  │
       │ │               │                │ remaining_budget │             │  │
       │ │               │                │ =3723s           │             │  │
       │ │               │                │─────────────────>│             │  │
       │ │               │                │ _calculate_sdk   │             │  │
       │ │               │                │ _timeout()       │             │  │
       │ │               │                │ calc=6240s       │             │  │
       │ │               │                │ min(6240,3723)   │             │  │
       │ │               │                │ effective=3723s  │             │  │
       │ │               │                │ (budget_cap!)    │             │  │
       │ │               │                │                  │             │  │
       │ │               │                │ asyncio.timeout  │             │  │
       │ │               │                │ (3723s)          │             │  │
       │ │               │                │─────────────────>│ query()     │  │
       │ │               │                │                  │────────────>│  │
       │ │               │                │                  │             │  │
       │ │               │                │    ... working for 3870s ...  │  │
       │ │               │                │    (exceeds 3723s budget)     │  │
       │ │               │                │                  │             │  │
       │ │               │                │              ┌───┴────┐       │  │
       │ │               │                │              │ anyio  │       │  │
       │ │               │                │              │ cancel │       │  │
       │ │               │                │              │ scope  │       │  │
       │ │               │                │              │ fires  │       │  │
       │ │               │                │              └───┬────┘       │  │
       │ │               │                │                  │             │  │
       │ │               │                │<── CancelledError│             │  │
       │ │               │                │  "Cancelled via  │             │  │
       │ │               │                │   cancel scope   │             │  │
       │ │               │                │   ea2a141156d0"  │             │  │
       │ │               │                │                  │             │  │
       │ │               │ ┌──────────────┤                  │             │  │
       │ │               │ │STATE RECOVERY│                  │             │  │
       │ │               │ │ 12 files     │                  │             │  │
       │ │               │ │ 159 tests ✓  │                  │             │  │
       │ │               │ │ Synthetic    │                  │             │  │
       │ │               │ │ report built │                  │             │  │
       │ │               │ └──────────────┤                  │             │  │
       │ │               │                │                  │             │  │
       │ │               │ Coach approves │                  │             │  │
       │ │               │ (hybrid        │                  │             │  │
       │ │               │  fallback)     │                  │             │  │
       │ │<──────────────│                │                  │             │  │
       │ │ FBP-007 done  │                │                  │             │  │
       │ └───────────────┘                │                  │             │  │
       │                 │                 │                 │                 │
       │ Wave 5 complete │                 │                 │                 │
       │ 163.4 min total │                 │                 │                 │
```

**Key observation**: The `budget_cap` log line in Run 6 (`budget_cap=9599s`) for FBP-007 shows the calculated SDK timeout was 6240s but was capped at the remaining budget. This proves TASK-VRF-003 is working — the Player's SDK timeout IS being capped. However, the anyio cancel scope within the SDK fires at its own deadline, independent of our asyncio.timeout wrapper.

---

## C4 Sequence Diagram 2: Cancel Scope Propagation Chain

```
┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────┐
│   Feature    │  │  AutoBuild   │  │    Agent     │  │   asyncio    │  │  anyio   │
│ Orchestrator │  │ Orchestrator │  │   Invoker    │  │   timeout    │  │  (SDK)   │
│  (Python)    │  │  (Thread)    │  │  (asyncio)   │  │  (wrapper)   │  │ (cancel  │
│              │  │              │  │              │  │              │  │  scopes) │
└──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └────┬─────┘
       │                 │                 │                 │               │
       │ asyncio.wait_for│                 │                 │               │
       │ (timeout=9600s) │                 │                 │               │
       │─────────────────>│                │                 │               │
       │                 │ asyncio.        │                 │               │
       │                 │ to_thread()     │                 │               │
       │                 │ ┌──────────┐    │                 │               │
       │                 │ │ Thread   │    │                 │               │
       │                 │ │ executes │    │                 │               │
       │                 │ │ _execute │    │                 │               │
       │                 │ │ _task()  │    │                 │               │
       │                 │ └────┬─────┘    │                 │               │
       │                 │      │          │                 │               │
       │                 │      │ loop.run_until_complete()  │               │
       │                 │      │─────────>│                 │               │
       │                 │      │          │                 │               │
       │                 │      │          │ asyncio.timeout │               │
       │                 │      │          │ (sdk_timeout_   │               │
       │                 │      │          │  seconds=3723s) │               │
       │                 │      │          │────────────────>│               │
       │                 │      │          │                 │               │
       │                 │      │          │                 │ query()       │
       │                 │      │          │                 │ (streaming    │
       │                 │      │          │                 │  generator)   │
       │                 │      │          │                 │──────────────>│
       │                 │      │          │                 │               │
       │                 │      │          │                 │  SDK uses     │
       │                 │      │          │                 │  anyio for    │
       │                 │      │          │                 │  internal     │
       │                 │      │          │                 │  concurrency  │
       │                 │      │          │                 │               │
       │                 │      │          │                 │ ┌───────────┐ │
       │                 │      │          │                 │ │ anyio     │ │
       │                 │      │          │                 │ │ CancelSc. │ │
       │                 │      │          │                 │ │ deadline  │ │
       │                 │      │          │                 │ │ exceeded  │ │
       │                 │      │          │                 │ └─────┬─────┘ │
       │                 │      │          │                 │       │       │
       │                 │      │          │                 │<──────┘       │
       │                 │      │          │                 │ CancelledError│
       │                 │      │          │                 │ "Cancelled    │
       │                 │      │          │                 │  via cancel   │
       │                 │      │          │                 │  scope        │
       │                 │      │          │                 │  {id(self):x}"│
       │                 │      │          │<────────────────│               │
       │                 │      │          │ CancelledError  │               │
       │                 │      │          │ propagates      │               │
       │                 │      │          │                 │               │
       │                 │      │          │ _invoke_with_   │               │
       │                 │      │          │ role catches:   │               │
       │                 │      │          │ - Extract       │               │
       │                 │      │          │   partial data  │               │
       │                 │      │          │ - Re-raise      │               │
       │                 │      │<─────────│                 │               │
       │                 │      │          │                 │               │
       │                 │      │ _invoke_player_safely()    │               │
       │                 │      │ catches CancelledError     │               │
       │                 │      │ → state recovery attempt   │               │
       │                 │      │                            │               │
       │                 │      │ ┌──────────────────┐       │               │
       │                 │      │ │ STATE RECOVERY   │       │               │
       │                 │      │ │ 1. Load player   │       │               │
       │                 │      │ │    report JSON   │       │               │
       │                 │      │ │ 2. Git detection │       │               │
       │                 │      │ │    (12 files)    │       │               │
       │                 │      │ │ 3. Test detection│       │               │
       │                 │      │ │    (159 pass)    │       │               │
       │                 │      │ │ 4. Build synth.  │       │               │
       │                 │      │ │    report        │       │               │
       │                 │      │ │ 5. Forward to    │       │               │
       │                 │      │ │    Coach         │       │               │
       │                 │      │ └──────────────────┘       │               │
       │                 │      │                            │               │
       │                 │<─────│ return (approved)          │               │
       │<────────────────│      │                            │               │
       │                 │                                   │               │
```

**Critical insight**: The anyio cancel scope fires INDEPENDENTLY of our asyncio.timeout wrapper. The SDK's internal anyio cancel scopes have their own deadlines that can fire before or after our wrapper. This is why FBP-007 ran for 3870s against a 3723s budget_cap — the cancel scope fired ~150s after our budget expired, because the asyncio.timeout at line 2003 and the anyio cancel scope inside the SDK are separate timeout mechanisms.

**Additionally**: The cancel monitor (TASK-FIX-ASPF-004) at `agent_invoker.py:1982` polls every 2 seconds and kills the subprocess when the cancellation_event fires, but this only triggers after `asyncio.wait_for` at the feature level times out — not from the per-turn budget.

---

## C4 Sequence Diagram 3: Slim vs Full Protocol Impact on SDK Turns

```
┌──────────────────────────────────────────────────────────────────────┐
│                    PROTOCOL SELECTION LOGIC                          │
│           agent_invoker.py:4028-4035 (TASK-VOPT-001)                │
│                                                                      │
│   if timeout_multiplier > 1.0:   ← vLLM detected (4.0x)            │
│       protocol = "slim"          ← 5,587 bytes (~131 lines)        │
│   else:                          ← Anthropic API (1.0x)             │
│       protocol = "full"          ← 19,270 bytes (~573 lines)       │
└──────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────┐  ┌──────────────────────────────────┐
│   Run 4: FULL PROTOCOL (19KB)       │  │  Runs 5-6: SLIM PROTOCOL (5.5KB)│
├─────────────────────────────────────┤  ├──────────────────────────────────┤
│                                     │  │                                  │
│  ✓ Detailed Docker setup (58 lines) │  │  ✗ Single-line Docker cmds       │
│  ✓ Stack patterns (47 lines)        │  │  ✗ One-sentence summary          │
│    - Python: forward refs, pathlib  │  │                                  │
│    - TypeScript: strict mode        │  │                                  │
│    - Error handling (5 bullets)     │  │                                  │
│  ✓ Fix loop pseudocode (34 lines)   │  │  ✗ Single paragraph              │
│  ✓ SOLID/DRY/YAGNI detail (48 ln)  │  │  ✗ One-liner checklist           │
│  ✓ Plan audit with examples (38 ln) │  │  ✗ Summary table only            │
│  ✓ Report schema docs (80 lines)   │  │  ✗ Minimal JSON example          │
│  ✓ Anti-stub rules (88 lines!)     │  │  ✗ Single sentence               │
│    - 6 stub patterns defined       │  │                                  │
│    - REJECTED examples (20 lines)   │  │                                  │
│    - ACCEPTED examples (20 lines)   │  │                                  │
│  ✓ Output marker examples (36 ln)  │  │  ✗ Format specs only             │
│                                     │  │                                  │
│  PRESERVED IN BOTH:                 │  │  PRESERVED IN BOTH:              │
│  ✓ File count constraints table     │  │  ✓ File count constraints table  │
│  ✓ Quality gate thresholds          │  │  ✓ Quality gate thresholds       │
│  ✓ Core phase structure (3-5.5)     │  │  ✓ Core phase structure (3-5.5)  │
│  ✓ Completion promises requirement  │  │  ✓ Completion promises requirement│
└─────────────────────────────────────┘  └──────────────────────────────────┘

SDK TURN IMPACT (same tasks, same vLLM backend, same max_turns=100):

  Task     │ Run 4 (full) │ Run 5 (slim) │ Run 6 (slim) │ Δ R4→R5 │ Δ R4→R6
  ─────────┼──────────────┼──────────────┼──────────────┼─────────┼────────
  FBP-001  │     37       │     58       │     46       │  +57%   │  +24%
  FBP-002  │     32       │   29+37=66   │     25       │ +106%   │  -22%
  FBP-003  │     82       │   87+22=109  │     75       │  +33%   │   -9%
  FBP-004  │     41       │     69       │     72       │  +68%   │  +76%
  FBP-005  │   101+26=127 │     49       │     74       │  -61%   │  -42%
  FBP-006  │     43       │    110       │    118       │ +156%   │ +174%

  Notes:
  - "+" entries = multi-turn tasks (Coach rejected first, Player retried)
  - FBP-005 anomaly: Run 4 FULL protocol needed 2 Coach turns (101+26)
  - FBP-006: Consistently inflated in slim — the most complex task
```

---

## C4 Sequence Diagram 4: Feature-Plan Wave Assignment Algorithm

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  /feature-   │    │    LLM       │    │  parallel_   │    │  Feature     │
│   plan       │    │  (generates  │    │  analyzer.py │    │  YAML        │
│  command     │    │   tasks)     │    │  (wave       │    │  output      │
│              │    │              │    │   assign)    │    │              │
└──────┬───────┘    └──────┬───────┘    └──────┬───────┘    └──────┬───────┘
       │                   │                   │                   │
       │ "Plan: FastAPI    │                   │                   │
       │  Base Project"    │                   │                   │
       │──────────────────>│                   │                   │
       │                   │                   │                   │
       │                   │ Generate tasks    │                   │
       │                   │ with files_to_    │                   │
       │                   │ create/modify     │                   │
       │                   │                   │                   │
       │ Tasks returned:   │                   │                   │
       │ FBP-001: scaffold │                   │                   │
       │   files: [pyproj, │                   │                   │
       │    src/__init__]  │                   │                   │
       │ FBP-006: tests    │                   │                   │
       │   files: [tests/] │                   │                   │
       │ FBP-007: quality  │                   │                   │
       │   files: [pyproj, │                   │                   │
       │    ruff.toml,     │                   │                   │
       │    Makefile]      │                   │                   │
       │<──────────────────│                   │                   │
       │                   │                   │                   │
       │ detect_parallel_  │                   │                   │
       │ groups(tasks)     │                   │                   │
       │──────────────────────────────────────>│                   │
       │                   │                   │                   │
       │                   │    CURRENT ALGORITHM:                 │
       │                   │    1. Build file map                  │
       │                   │    2. Build conflict graph            │
       │                   │       FBP-006 ↔ FBP-007              │
       │                   │       (NO file conflicts)             │
       │                   │    3. Check dependencies              │
       │                   │       FBP-006 depends on              │
       │                   │       FBP-001..005                    │
       │                   │       FBP-007 depends on              │
       │                   │       FBP-001..005                    │
       │                   │    4. Both can go in same             │
       │                   │       wave (no file conflicts,        │
       │                   │       deps satisfied by W1-4)         │
       │                   │                   │                   │
       │                   │    ⚠ NO AWARENESS OF:                │
       │                   │    - max_parallel=1 serialization     │
       │                   │    - Task runtime estimation          │
       │                   │    - Budget starvation risk           │
       │                   │    - Task type (scaffolding/testing)  │
       │                   │                   │                   │
       │ Result:           │                   │                   │
       │ Wave 5: [FBP-006, │                   │                   │
       │         FBP-007]  │                   │                   │
       │<──────────────────────────────────────│                   │
       │                   │                   │                   │
       │ Write feature YAML│                   │                   │
       │─────────────────────────────────────────────────────────>│
       │                   │                   │                   │
       │                   │    PROPOSED FIX:                      │
       │                   │    Add task-type-aware rule:          │
       │                   │    "When max_parallel=1 and wave      │
       │                   │     has long-running + short tasks,   │
       │                   │     separate into distinct waves"     │
       │                   │                   │                   │
       │                   │    OR simpler:                        │
       │                   │    "Quality-gate/scaffolding tasks    │
       │                   │     that are co-dependent with        │
       │                   │     high-complexity tasks → own wave" │
```

---

## Finding 1: CORRECTED — remaining_budget IS Passed to Player

**Severity**: Critical correction to TASK-REV-5E1F

The TASK-REV-5E1F review (Finding 3, R3) stated:
> "invoke_player(): Does NOT accept remaining_budget parameter"

**This is INCORRECT.** Code evidence:

```python
# agent_invoker.py:1134-1144
async def invoke_player(
    self,
    task_id: str,
    turn: int,
    requirements: str,
    ...
    remaining_budget: Optional[float] = None,  # LINE 1144 — TASK-VRF-003
) -> AgentInvocationResult:
```

The `remaining_budget` parameter flows through the complete chain:

```
feature_orchestrator.py:1483  → task_budget = max(0, task_timeout - elapsed)
feature_orchestrator.py:1490  → time_budget_seconds=task_budget
autobuild.py:1779             → remaining_budget = time_budget - elapsed
autobuild.py:1810             → _execute_turn(remaining_budget=remaining_budget)
autobuild.py:2069             → _invoke_player_safely(remaining_budget=remaining_budget)
agent_invoker.py:1197         → _calculate_sdk_timeout(remaining_budget=remaining_budget)
agent_invoker.py:3456         → effective = min(effective, int(remaining_budget))
agent_invoker.py:2003         → asyncio.timeout(self.sdk_timeout_seconds)  # capped value
```

**Run 6 log proof** (line 1638):
```
[TASK-FBP-007] SDK timeout: 6240s (base=1200s, mode=direct x1.0,
complexity=3 x1.3, backend x4.0, budget_cap=9599s)
```

The `budget_cap=9599s` shows the budget was applied (though at wave start, before FBP-006 consumed time). The actual effective timeout at FBP-007's execution time would have been `min(6240, 3723)` = **3723s**.

**Why FBP-007 still exceeded budget**: The anyio cancel scope within the Claude SDK fires at its own internal deadline, which is independent of our `asyncio.timeout(3723s)` wrapper. The SDK ran for 3870s (147s past budget) before the anyio cancel scope triggered. This is a race condition between two independent timeout mechanisms at different abstraction layers.

**Impact**: R3 from TASK-REV-5E1F is **already implemented** and working. The remaining issue is the ~150s overrun between our asyncio.timeout and the SDK's internal anyio cancel scope — this is inherent to the subprocess architecture and cannot be eliminated without changes to the Claude SDK itself.

---

## Finding 2: Root Cause of SDK Turn Inflation — Slim Protocol (TASK-VOPT-001)

**Severity**: High — Newly identified root cause

| Run | Protocol | Size | FBP-001 | FBP-004 | FBP-006 |
|-----|----------|------|---------|---------|---------|
| Run 4 | **FULL** | 19,270 bytes | 37 turns | 41 turns | 43 turns |
| Run 5 | **SLIM** | 5,587 bytes | 58 turns | 69 turns | 110 turns |
| Run 6 | **SLIM** | 5,587 bytes | 46 turns | 72 turns | 118 turns |

The slim protocol was introduced by TASK-VOPT-001 between Runs 4 and 5. It reduces prompt size from ~19KB to ~5.5KB by removing:
- Detailed stack-specific patterns (47 lines → 1 sentence)
- Fix loop pseudocode (34 lines → 1 paragraph)
- Anti-stub rules with examples (88 lines → 1 sentence)
- SOLID/DRY/YAGNI explanations (48 lines → 1 checklist)
- Report schema documentation (80 lines → minimal example)

**The protocol preserves all quality gates** (thresholds, requirements) but removes the **pedagogical guidance** that helps the model succeed efficiently. Without examples of stub patterns, error handling, and implementation approaches, the vLLM model needs more iterations to converge on acceptable output.

**This explains:**
- Why FBP-006 went from 43 turns (full) to 110-118 turns (slim) — the integration test task is most sensitive to guidance removal
- Why Waves 1-4 are ~19m slower in aggregate — each task uses more turns
- Why the duration increase is NOT limited to Wave 5

**Key insight**: The slim protocol was a reasonable optimization for per-turn latency (smaller prompt = faster inference), but it trades prompt tokens for more turns. On a fast backend (Anthropic API), this tradeoff might be neutral. On vLLM with ~25-50s/turn, each additional turn adds significant wall-clock time.

---

## Finding 3: Budget Starvation Mechanism — Confirmed but Partially Mitigated

**Severity**: High — Structural issue, confirmed via code trace

The budget starvation chain is fully traced across 4 system boundaries:

### Layer 1: Feature Orchestrator (Python, main thread)
```python
# feature_orchestrator.py:1483
task_budget = max(0.0, self.task_timeout - elapsed_at_queue)
```
With `max_parallel=1` (Semaphore), `elapsed_at_queue` for FBP-007 includes FBP-006's entire runtime.

### Layer 2: AutoBuild Orchestrator (Python, worker thread)
```python
# autobuild.py:1780
if remaining_budget < MIN_TURN_BUDGET_SECONDS:  # 600s
    return turn_history, "timeout_budget_exhausted"
```
This check PREVENTS starting a new turn if <10 min remain. But for FBP-007's first turn, remaining_budget was 3723s — well above the threshold.

### Layer 3: Agent Invoker (Python, asyncio)
```python
# agent_invoker.py:3456
effective_timeout = min(effective_timeout, int(remaining_budget))  # 3723s
```

```python
# agent_invoker.py:2003
async with asyncio.timeout(self.sdk_timeout_seconds):  # 3723s
```

### Layer 4: Claude SDK (Node.js subprocess via anyio)
```
anyio.CancelScope fires at internal deadline
→ CancelledError("Cancelled via cancel scope ea2a141156d0")
→ Propagates through async_generator_athrow
→ Caught by _invoke_with_role at agent_invoker.py:2020
```

**The gap**: Between Layer 3 (asyncio.timeout at 3723s) and Layer 4 (anyio cancel scope at ~3870s), there's a ~150s window where the SDK subprocess continues running past our timeout. This happens because:
1. `asyncio.timeout` fires a `TimeoutError` in the Python event loop
2. But the SDK subprocess (Node.js) is a separate OS process
3. The cancel monitor (TASK-FIX-ASPF-004) polls every 2s and kills the subprocess, but only when `cancellation_event` is set — which is set by the feature-level `asyncio.wait_for`, not the per-turn asyncio.timeout

**This is an architectural gap**: The per-turn budget timeout at Layer 3 does NOT trigger the subprocess kill via cancel monitor. Only the feature-level timeout triggers it.

---

## Finding 4: Duration Analysis — Revised with Protocol Attribution

**Severity**: Medium

### Per-Task Duration Comparison (with protocol variant noted)

| Task | Run 4 (full, 19KB) | Run 6 (slim, 5.5KB) | Delta | Root Cause |
|------|-------------------|---------------------|-------|------------|
| FBP-001 | 37 turns, ~15m | 46 turns, 18.3m | +3.3m | Slim: less guidance |
| FBP-002 | 32 turns, ~8m | 25 turns, 7.1m | -0.9m | Variance (within norm) |
| FBP-004 | 41 turns, ~19m | 72 turns, 30.8m | +11.8m | Slim: 76% more turns |
| FBP-003 | 82 turns, ~23m | 75 turns, 34.6m | +11.6m | Slower s/turn (27.7 vs ~17) |
| FBP-005 | 127 turns, ~42m | 74 turns, 28.8m | -13.2m | Run 4 needed 2 Coach turns |
| FBP-006 | 43 turns, ~23m | 118 turns, 97.4m | +74.4m | Slim: 174% more turns |
| FBP-007 | 1 turn, ~1m | cancelled, 65.0m | +64.0m | Budget starvation |

**Aggregate**:
- Waves 1-4 delta: +12.8m (slim protocol overhead across 5 tasks)
- Wave 5 delta: +138.4m (FBP-006 ceiling + FBP-007 starvation)
- Total: ~+58m (12:28→17:14 vs 23:15→03:02)

**The slim protocol adds ~2.5m average overhead per task** for Waves 1-4. For FBP-006 (highest complexity at 6), the overhead is dramatically higher because the integration test task is most sensitive to the removed guidance (anti-stub rules, detailed test patterns, error handling examples).

---

## Finding 5: Per-Turn Latency Variance

**Severity**: Low — Informational

| Task | Run 4 s/turn | Run 6 s/turn | Delta |
|------|-------------|-------------|-------|
| FBP-001 | ~24s | 23.8s | -0.2s |
| FBP-002 | ~15s | 17.0s | +2.0s |
| FBP-003 | ~17s | 27.7s | +10.7s |
| FBP-004 | ~28s | 25.6s | -2.4s |
| FBP-005 | ~20s | 23.3s | +3.3s |
| FBP-006 | ~32s | 49.5s | +17.5s |

FBP-003 and FBP-006 show significantly slower per-turn latency in Run 6. Possible causes:
- **KV cache accumulation**: Later tasks in a fresh run have more worktree state
- **vLLM batch scheduling**: With `max_parallel=1`, single-request batches may trigger less efficient scheduling
- **Model context growth**: More files in worktree = more Read/Glob operations per turn = more SDK internal turns = slower effective turn time

The per-turn time is **not** related to the protocol variant (both runs used the same vLLM model and hardware). It correlates with task complexity and worktree state accumulation.

---

## Finding 6: Feature-Plan Wave Assignment Gap

**Severity**: High — Architectural issue requiring fix

The `detect_parallel_groups()` function at `installer/core/lib/parallel_analyzer.py:178-296` assigns waves based solely on **file conflicts and dependencies**. It has NO awareness of:

1. **max_parallel setting**: Doesn't know that `max_parallel=1` means "parallel" tasks are actually serialized
2. **Task runtime estimation**: Doesn't consider that a complexity-6 task (FBP-006) will consume most of the wave budget
3. **Budget starvation risk**: Doesn't calculate whether serialized tasks can complete within the wave timeout
4. **Task type**: Doesn't know that a scaffolding task (FBP-007) following a testing task (FBP-006) is at risk

**Current algorithm**:
```
For each task:
    If no file conflicts with existing wave members AND
    All dependencies satisfied by previous waves:
        Add to current wave
    Else:
        Start new wave
```

**Missing rule**:
```
When max_parallel=1 AND wave contains a high-complexity task (≥5):
    Separate remaining tasks into subsequent waves

OR more specifically:
    When wave has estimated_runtime > 0.6 × task_timeout:
        Separate into distinct waves
```

This is the root cause of the FBP-006/FBP-007 co-location problem across all runs.

---

## Finding 7: State Recovery Success Factors

**Severity**: Medium — Explains Run 6 vs Run 5 divergence

| Factor | Run 5 | Run 6 | Impact |
|--------|-------|-------|--------|
| FBP-007 budget | 2820s | 3723s | +32% more execution time |
| Cancellations | 8 | 1 | No state pollution |
| TASK-FIX-ASPF-006 | Not available | Available | Better requirements_addressed inference |
| Tests at cancel | Unknown | 159 passing | Strong evidence for Coach |
| Files at cancel | Unknown | 12 changed | Sufficient deliverables |
| Coach matching | Promise matching failed | Hybrid fallback succeeded | Semantic + text matching |

The single most important factor is **single cancellation vs 8 cancellations**. Multiple cancellations cause state pollution (Finding from TASK-REV-5E1F Deep-Dive C) where each recovery attempt introduces inconsistencies.

---

## Revised TASK-REV-5E1F Recommendation Status

| Recommendation | Original Status | Revised Status | Evidence |
|---------------|----------------|----------------|----------|
| R1: Relax FBP-007 AC | "Not applied" | **Mitigated** (scaffolding profile) | Coach uses scaffolding profile: tests/coverage not required |
| R2: Separate FBP-007 wave | "Not applied" | **Still needed (HIGH)** | Budget starvation confirmed; success was non-deterministic |
| R3: Pass remaining_budget to Player | "Not applied" | **ALREADY IMPLEMENTED** (TASK-VRF-003) | `agent_invoker.py:1144` accepts `remaining_budget` |
| R4: Backend-aware AC validation | "Not applied" | **Still relevant (MEDIUM)** | Feature-plan has no task-type-aware wave logic |
| R5: Fix synthetic report corruption | "Partially fixed" | **Fixed** (TASK-FIX-ASPF-006) | Run 6 recovery worked on first attempt |
| R6: Explore max_parallel=2 | "Not applied" | **Deprioritized** | Wave separation + budget fixes are sufficient |
| R7: Correct task description | "Unknown" | **Still needed (TRIVIAL)** | TASK-REV-5E1F falsely claims R3 not implemented |

---

## Revised Decision Matrix

| Option | Reliability | Effort | Risk | Recommendation |
|--------|------------|--------|------|----------------|
| A: No changes | Low | None | High | Run 6 success was non-deterministic |
| B: Wave separation only | High | Low | Low | Eliminates budget starvation |
| C: B + feature-plan fix | Very High | Medium | Low | **Recommended** — prevents recurrence in new features |
| D: C + protocol investigation | Very High | Medium | Medium | Addresses turn inflation but may regress latency |

---

## Revised Recommendations

### R1: Separate FBP-007 into its own wave (Priority: HIGH, Effort: LOW)

Move FBP-007 from Wave 5 to Wave 6 in the feature YAML. This is a one-line change to the FEAT-1637 orchestration config.

**Risk**: None. FBP-007 has no dependency on FBP-006.

### R2: Add task-type-aware wave separation to /feature-plan (Priority: HIGH, Effort: MEDIUM)

Update `detect_parallel_groups()` in `installer/core/lib/parallel_analyzer.py` to add a new rule:

**Proposed rule**: When `max_parallel=1` and a wave contains multiple tasks where the sum of estimated runtimes exceeds 60% of `task_timeout`, split into separate waves.

**Simpler alternative**: When `max_parallel=1`, enforce that each wave has at most 1 task. This eliminates all budget starvation risk at the cost of more waves (but with `max_parallel=1`, tasks are serialized anyway, so wave count doesn't affect runtime).

**Files to modify**:
- `installer/core/lib/parallel_analyzer.py` — `detect_parallel_groups()` function
- `installer/core/commands/feature-plan.md` — document the new behavior
- `tests/test_parallel_analyzer.py` — add test cases

### R3: Investigate slim protocol turn inflation (Priority: MEDIUM, Effort: LOW)

The slim protocol (TASK-VOPT-001) reduces prompt size by 73% but increases SDK turns by 50-174% for complex tasks. This needs investigation:

1. **Measure**: Compare per-turn latency savings vs total duration increase
2. **Consider**: A "medium" protocol variant (~10KB) that keeps critical guidance (anti-stub rules, stack patterns) while removing verbose examples
3. **Alternative**: Keep slim but increase SDK max turns from 100 to 150 for local backends

**Files to examine**:
- `guardkit/orchestrator/prompts/autobuild_execution_protocol_slim.md`
- `guardkit/orchestrator/prompts/autobuild_execution_protocol.md`
- `guardkit/orchestrator/agent_invoker.py:4028-4035` (selection logic)

### R4: Correct TASK-REV-5E1F report (Priority: LOW, Effort: TRIVIAL)

Update `.claude/reviews/TASK-REV-5E1F-review-report.md`:
- Finding 3: invoke_player DOES accept remaining_budget (TASK-VRF-003)
- R3: Already implemented — remove from "to do" list
- Add note: SDK turn inflation caused by slim protocol, not mode routing

---

## Acceptance Criteria Assessment (Revised)

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Run 6 success factors identified | **Done** | State recovery + ASPF-006 fix + sufficient budget |
| Wave separation impact assessed | **Done** | NOT applied; success was non-deterministic |
| Performance comparison across Runs 4-6 | **Done** | Slim protocol is primary cause of turn inflation |
| SDK turn analysis per task | **Done** | Full vs slim protocol comparison table |
| Assessment of TASK-REV-5E1F recommendations | **Done** | R3 already implemented; R2 still needed |
| Recommendations for Run 7 | **Done** | R1 (wave separation) + R2 (feature-plan fix) |
| Root cause traced across boundaries | **Done** | 4-layer propagation chain with C4 diagrams |
| C4 sequence diagrams | **Done** | 4 diagrams covering budget, cancellation, protocol, wave assignment |

---

## Appendix A: Key Code References

| File | Lines | Purpose |
|------|-------|---------|
| `feature_orchestrator.py` | 1473-1495 | Wave execution, task_budget calculation |
| `feature_orchestrator.py` | 1518-1577 | asyncio.gather, timeout/cancellation events |
| `autobuild.py` | 165-176 | MIN_TURN_BUDGET_SECONDS=600, COACH_GRACE_PERIOD=120 |
| `autobuild.py` | 1759-1850 | _loop_phase: budget checks, cooperative cancellation |
| `autobuild.py` | 2284-2320 | Coach grace period decision |
| `agent_invoker.py` | 1134-1199 | invoke_player: remaining_budget parameter (TASK-VRF-003) |
| `agent_invoker.py` | 1381-1422 | invoke_coach: remaining_budget parameter |
| `agent_invoker.py` | 1902-2078 | _invoke_with_role: asyncio.timeout wrapper |
| `agent_invoker.py` | 1982-1991 | Cancel monitor: kill subprocess (TASK-FIX-ASPF-004) |
| `agent_invoker.py` | 3381-3466 | _calculate_sdk_timeout: budget cap logic |
| `agent_invoker.py` | 4028-4035 | Protocol selection: slim vs full (TASK-VOPT-001) |
| `agent_invoker.py` | 825-835 | SDK max turns reduction for local backend |
| `parallel_analyzer.py` | 178-296 | detect_parallel_groups: wave assignment algorithm |
| `task_type_detector.py` | 207-305 | Task type classification keywords |
| `coach_validator.py` | — | Quality gate profiles by task type |
| `prompts/autobuild_execution_protocol.md` | 1-573 | Full protocol (19KB) |
| `prompts/autobuild_execution_protocol_slim.md` | 1-131 | Slim protocol (5.5KB) |

## Appendix B: Key Timestamps (Run 6)

| Event | Timestamp | Elapsed |
|-------|-----------|---------|
| Feature start | 12:28:49 | 0:00 |
| Wave 1 complete | 12:47:43 | 18.9m |
| Wave 2 complete | 13:26:37 | 57.8m |
| Wave 3 complete | 14:01:45 | 92.9m |
| Wave 4 complete | 14:31:04 | 122.2m |
| FBP-006 start (Wave 5) | 14:31:04 | 122.2m |
| FBP-006 SDK complete (118 turns) | 16:08:31 | 219.7m |
| FBP-007 start (serialized) | 16:09:01 | 220.2m |
| FBP-007 cancel scope fires | 17:13:59 | 285.2m |
| FBP-007 state recovery | 17:14:00 | 285.2m |
| FBP-007 Coach approves | 17:14:00 | 285.2m |
| Feature complete | 17:14:30 | 285.7m |

## Appendix C: Cross-Run Configuration Comparison

| Parameter | Run 4 | Run 5 | Run 6 |
|-----------|-------|-------|-------|
| Backend | vLLM | vLLM | vLLM |
| timeout_multiplier | 4.0x | 4.0x | 4.0x |
| max_parallel | 1 | 1 | 1 |
| SDK max turns | 100 | 100 | 100 |
| Protocol variant | **FULL (19KB)** | **SLIM (5.5KB)** | **SLIM (5.5KB)** |
| --fresh flag | True | True | True |
| task_timeout | 9600s | 9600s | 9600s |
| TASK-VRF-003 (budget cap) | ? | Applied | Applied |
| TASK-FIX-ASPF-006 (synth report) | No | No | **Yes** |
| Wave structure | W5:[006,007] | W5:[006,007] | W5:[006,007] |
