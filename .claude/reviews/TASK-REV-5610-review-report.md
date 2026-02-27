# Review Report: TASK-REV-5610 (Deep-Dive Revision)

## Executive Summary

Run 2 of the vLLM/Qwen3 autobuild on GB10 shows **significant progress** over run 1: 5/8 tasks completed (vs 2/8), Waves 1-2 fully passing, and Wave 3 partially succeeding (1/3). The `timeout_multiplier=4.0x` fix from TASK-REV-8A94 resolved all Wave 2 failures.

Three **precisely identified failure modes** in Wave 3 require targeted, low-risk fixes:

1. **Task file search divergence** in `extract_acceptance_criteria()` — root cause of DB-005 Turn 1 0/6
2. **Excessive SDK turns** (93-101 vs Anthropic's 15-30) — root cause of DB-006/DB-008 timeout
3. **Transient vLLM streaming error** under 3-task parallel GPU load — triggers cascading failure

**Critical correction from initial review**: Finding 5 (R6) in the initial report incorrectly identified a matching strategy bug. Deep-dive confirms semantic matching IS active for vLLM on all paths. The 0/6 on DB-005 Turn 1 is caused by missing AC injection (Finding 3), not matching strategy. R6 is withdrawn.

**Estimated fix effort**: 2-3 small tasks. All fixes are surgical — no architectural changes needed. The hard-won architecture (timeout multiplier, text-matching fixes TM01-04, state recovery, cooperative cancellation) is validated and working correctly.

## Review Details

| Field | Value |
|-------|-------|
| **Mode** | Decision / Root Cause Analysis |
| **Depth** | Comprehensive (deep-dive revision) |
| **Duration** | Deep analysis of 532KB log, 6 source files, full architecture trace |
| **Related** | TASK-REV-8A94 (run 1 analysis) |
| **Revision** | v2 — corrected matching strategy analysis, added C4 diagrams |

## Progress: Run 1 vs Run 2 vs Anthropic

| Metric | Run 1 | Run 2 | Anthropic |
|--------|-------|-------|-----------|
| Config | `--max-turns 5` | `--max-turns 5 --fresh` | `--max-turns 10 --fresh` |
| Timeout multiplier | 1.0x (2400s) | 4.0x (9600s) | N/A (~2400s) |
| Wave 1 | PASS (1 turn) | PASS (2 turns) | PASS (1 turn) |
| Wave 2 | FAIL (1/3 pass) | **PASS (3/3 pass)** | PASS (3/3 pass) |
| Wave 3 | Not reached | **FAIL (1/3 pass)** | PASS |
| Wave 4 | Not reached | Not reached | PASS |
| Tasks completed | 2/8 | **5/8** | 5/5 |
| Duration | 72m 47s | 275m 25s | ~60 min |
| Key failures | Text matching, timeout | SDK error, excessive turns | None |

**Run 1 fixes that worked (MUST PRESERVE):**
- `timeout_multiplier=4.0x` — resolved Wave 2 timeouts completely
- `--fresh` flag — eliminated stale state issues
- Text-matching semantic fix (TASK-FIX-TM01-04) — improved Coach criteria matching
- Cooperative cancellation (TASK-ASF-007) — clean thread shutdown
- State recovery (TASK-ASF-006) — captures partial work on SDK errors

---

## C4 Architecture Diagrams

### Diagram 1: Feature → Wave → Task Execution Flow (Container Level)

```
┌─────────────────────────────────────────────────────────────────────┐
│                      FeatureOrchestrator                            │
│  (feature_orchestrator.py)                                          │
│                                                                     │
│  ┌──────────────┐     ┌──────────────────────────────────────────┐ │
│  │ execute_      │────▶│ _execute_wave_parallel()                 │ │
│  │ feature()     │     │                                          │ │
│  │               │     │  for task_id in wave:                    │ │
│  │ Wave 1 ─────▶│     │    cancel_event = threading.Event()      │ │
│  │ Wave 2 ─────▶│     │    asyncio.wait_for(                     │ │
│  │ Wave 3 ─────▶│     │      asyncio.to_thread(                  │ │
│  │ Wave 4 ─────▶│     │        _execute_task(task, worktree,     │ │
│  │               │     │          cancellation_event=cancel_event)│ │
│  │ stop_on_      │     │      ),                                  │ │
│  │ failure=True  │     │      timeout=self.task_timeout  ◄─9600s  │ │
│  └──────────────┘     │    )                                      │ │
│                        │                                          │ │
│                        │  asyncio.gather(*tasks, return_exc=True) │ │
│                        │  finally:                                 │ │
│                        │    for event: event.set()  ◄─ TASK-ASF-007│
│                        └──────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
        ┌───────────────┐ ┌───────────────┐ ┌───────────────┐
        │ _execute_task │ │ _execute_task │ │ _execute_task │
        │ (DB-005)      │ │ (DB-006)      │ │ (DB-008)      │
        │ Thread A      │ │ Thread B      │ │ Thread C      │
        └───────┬───────┘ └───────┬───────┘ └───────┬───────┘
                │                 │                 │
                ▼                 ▼                 ▼
        ┌───────────────┐ ┌───────────────┐ ┌───────────────┐
        │AutoBuild      │ │AutoBuild      │ │AutoBuild      │
        │Orchestrator   │ │Orchestrator   │ │Orchestrator   │
        │(autobuild.py) │ │(autobuild.py) │ │(autobuild.py) │
        └───────────────┘ └───────────────┘ └───────────────┘
```

**Key Architecture Points:**
- Each task runs in its own thread via `asyncio.to_thread()`
- `asyncio.wait_for()` wraps each task with `task_timeout=9600s` (4x multiplied)
- Timeout is PER-TASK from task dispatch (not wave start) — confirmed in code
- After `asyncio.gather()` completes, ALL cancellation events are set (cleanup)
- `stop_on_failure=True` breaks the wave loop on first failed wave

### Diagram 2: AutoBuild Player-Coach Adversarial Turn Loop

```
┌──────────────────────────────────────────────────────────────────────┐
│                    AutoBuildOrchestrator (autobuild.py)               │
│                                                                      │
│  for turn in range(1, max_turns + 1):     ◄─ max_turns=5            │
│                                                                      │
│    ┌──────────────┐     ┌──────────────────────────────────┐        │
│    │ CANCELLATION │     │ If cancellation_event.is_set():  │        │
│    │ CHECK #1     │────▶│   break  (TASK-ASF-007)          │        │
│    └──────┬───────┘     └──────────────────────────────────┘        │
│           │                                                          │
│           ▼                                                          │
│    ┌──────────────┐                                                  │
│    │   PLAYER     │──────────────────────────────────────────┐      │
│    │   (invoke)   │     AgentInvoker routes by                │      │
│    └──────┬───────┘     implementation_mode:                  │      │
│           │              ┌─────────────────────────────────┐  │      │
│           │              │ complexity ≤ 2 → direct mode    │──┘      │
│           │              │ complexity > 2 → task-work mode │         │
│           │              └─────────────────────────────────┘         │
│           │                                                          │
│           │  On SDK error:                                           │
│           │    → State recovery (git diff + test results)            │
│           │    → Synthetic report (_synthetic: True)                 │
│           │                                                          │
│           ▼                                                          │
│    ┌──────────────┐     ┌──────────────────────────────────┐        │
│    │ CANCELLATION │     │ If cancellation_event.is_set():  │        │
│    │ CHECK #2     │────▶│   break  (TASK-ASF-007)          │        │
│    └──────┬───────┘     └──────────────────────────────────┘        │
│           │                                                          │
│           ▼                                                          │
│    ┌──────────────┐                                                  │
│    │   COACH      │                                                  │
│    │   (validate) │──▶ CoachValidator.validate_requirements()        │
│    └──────┬───────┘                                                  │
│           │                                                          │
│      ┌────┴────┐                                                     │
│      │ Result? │                                                     │
│      └────┬────┘                                                     │
│    approved │ rejected/feedback                                      │
│      │      │                                                        │
│      ▼      ▼                                                        │
│    PASS   Loop to next turn                                          │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### Diagram 3: Coach validate_requirements() Decision Tree (CRITICAL)

```
validate_requirements(task, task_work_results, turn)
│
├── is_synthetic = task_work_results.get("_synthetic", False)
│
├─── IF is_synthetic ──────────────────────────────────────────────────┐
│    │                                                                  │
│    ├── Load completion_promises                                       │
│    │   ├── IF promises exist:                                         │
│    │   │   ├── _match_by_promises(AC, promises)                       │
│    │   │   ├── IF not all_met:                                        │
│    │   │   │   └── _hybrid_fallback(AC, requirements_addressed)       │
│    │   │   ├── IF 0/N: Log "matching_strategy: promises+hybrid        │
│    │   │   │          (synthetic)" ◄─── DB-006 Turn 1 hit THIS path   │
│    │   │   └── Return validation                                      │
│    │   │                                                              │
│    │   └── IF no promises:                                            │
│    │       ├── IF requirements_addressed exist:                       │
│    │       │   └── _match_by_text(AC, requirements_addressed)         │
│    │       │       └── Inside: calls _resolve_matching_strategy()     │
│    │       │           └── Returns 'semantic' for vLLM ✓              │
│    │       └── IF nothing: return all_unmet                           │
│    │                                                                  │
│    └──────────────────────────────────────────────────────────────────┘
│
└─── ELSE (normal report) ─────────────────────────────────────────────┐
     │                                                                  │
     ├── Load completion_promises                                       │
     │   ├── IF promises exist:                                         │
     │   │   ├── strategy = "promises"                                  │
     │   │   ├── _match_by_promises(AC, promises)                       │
     │   │   ├── IF not all_met:                                        │
     │   │   │   └── _hybrid_fallback(AC, requirements_addressed)       │
     │   │   │       strategy = "hybrid"                                │
     │   │   └── Return validation                                      │
     │   │                                                              │
     │   └── IF no promises:                                            │
     │       ├── strategy = "text"                                      │
     │       ├── _match_by_text(AC, requirements_met)                   │
     │       │   └── Inside: calls _resolve_matching_strategy()         │
     │       │       └── Returns 'semantic' for vLLM ✓                  │
     │       │                                                          │
     │       │   ◄─── DB-005 Turn 1 hit THIS path:                     │
     │       │        strategy var = "text" (code path label)           │
     │       │        BUT _match_by_text() internally uses              │
     │       │        _resolve_matching_strategy() → 'semantic'         │
     │       │        Diagnostic log shows "matching_strategy: text"    │
     │       │        which is the STRATEGY VARIABLE, not matching mode │
     │       │                                                          │
     │       └── Return validation                                      │
     │                                                                  │
     └──────────────────────────────────────────────────────────────────┘

KEY INSIGHT: The diagnostic "matching_strategy: text" at line 1718 logs the
local `strategy` variable (which tracks the CODE PATH: promises vs text),
NOT the actual matching mode. Inside _match_by_text(), the effective
matching mode is 'semantic' for vLLM (via _resolve_matching_strategy()).
```

### Diagram 4: DB-005 Root Cause Chain (Deep-Dive)

```
TASK-DB-005 Turn 1: WHY 0/6?

┌───────────────────────────────────────────────────────────────────┐
│ 1. Task file in: tasks/design_approved/TASK-DB-005-create-       │
│    initial-migration.md                                           │
│                                                                   │
│ 2. extract_acceptance_criteria("TASK-DB-005") called:             │
│    ┌──────────────────────────────────────────────────────────┐   │
│    │ Searches:                                                 │   │
│    │   tasks/in_progress/TASK-DB-005.md        ← NOT FOUND   │   │
│    │   tasks/backlog/TASK-DB-005.md             ← NOT FOUND   │   │
│    │   tasks/in_review/TASK-DB-005.md           ← NOT FOUND   │   │
│    │   tasks/in_progress/*/TASK-DB-005.md       ← NOT FOUND   │   │
│    │   tasks/backlog/*/TASK-DB-005.md           ← NOT FOUND   │   │
│    │   tasks/in_review/*/TASK-DB-005.md         ← NOT FOUND   │   │
│    │                                                           │   │
│    │   ✗ Missing: tasks/design_approved/ directory             │   │
│    │   ✗ Wrong:   exact "TASK-DB-005.md" not glob "*"          │   │
│    └──────────────────────────────────────────────────────────┘   │
│    → Returns [] (empty)                                           │
│    → WARNING: Task file not found for TASK-DB-005                 │
│                                                                   │
│ 3. Player prompt built WITHOUT acceptance criteria                │
│    → Qwen3 implements without knowing specific requirements       │
│    → Produces generic requirements_met:                           │
│      ["Initial database migration file created",                  │
│       "Migration script validates schema"]                        │
│                                                                   │
│ 4. Coach receives Player report:                                  │
│    - No completion_promises (direct mode, not task-work)          │
│    - strategy = "text" (code path: no promises → text fallback)   │
│    - _match_by_text(AC, requirements_met) called                  │
│    - INSIDE _match_by_text:                                       │
│      _resolve_matching_strategy() → 'semantic' (vLLM detected)   │
│      Semantic mode: 50% Jaccard + fuzzy prefix matching           │
│                                                                   │
│ 5. But semantic matching STILL fails because:                     │
│    AC text: "alembic/versions/001_create_users_table.py created   │
│             via alembic revision --autogenerate"                   │
│    requirements_met: "Initial database migration file created"    │
│                                                                   │
│    Jaccard("alembic versions 001 create users table py created    │
│            via alembic revision autogenerate",                     │
│           "initial database migration file created")              │
│    = intersection/union = ~2/12 = 17% < 50% threshold            │
│                                                                   │
│    → 0/6 criteria verified even with semantic matching             │
│    → Coach REJECTS                                                │
└───────────────────────────────────────────────────────────────────┘

CONTRAST with DB-005 Turn 2:
┌───────────────────────────────────────────────────────────────────┐
│ - Coach feedback includes specific AC text from the task file     │
│ - Qwen3 sees the criteria and implements specifically             │
│ - requirements_met now closely paraphrases the AC text            │
│ - Semantic matching: high Jaccard overlap → 6/6 APPROVED          │
└───────────────────────────────────────────────────────────────────┘

ROOT CAUSE: extract_acceptance_criteria() file search bug
            → missing AC injection into Player prompt
            → generic Qwen3 output can't match specific AC text
            → 0/6 even with semantic matching active
```

### Diagram 5: _find_task_file() vs extract_acceptance_criteria() Divergence

```
_find_task_file(task_id)                  extract_acceptance_criteria(task_id)
(agent_invoker.py:2226)                   (agent_invoker.py:4087)
─────────────────────────                 ──────────────────────────────────

DIRECTORIES SEARCHED:                     DIRECTORIES SEARCHED:
  ✓ tasks/backlog/                          ✓ tasks/in_progress/
  ✓ tasks/design_approved/  ◄── HAS        ✓ tasks/backlog/
  ✓ tasks/in_progress/                      ✓ tasks/in_review/
  ✓ tasks/in_review/                        ✗ tasks/design_approved/ ◄── MISSING
  ✓ tasks/completed/                        ✗ tasks/completed/
  ✓ tasks/blocked/                          ✗ tasks/blocked/

FILENAME PATTERN:                         FILENAME PATTERN:
  ✓ rglob(f"{task_id}*.md")               ✗ exact f"{task_id}.md"
    Matches: TASK-DB-005-create-             Expects: TASK-DB-005.md
    initial-migration.md                     Actual:  TASK-DB-005-create-
                                                      initial-migration.md

SUBDIRECTORY SEARCH:                      SUBDIRECTORY SEARCH:
  ✓ rglob searches recursively             ✓ Iterates subdirs but still
                                             uses exact filename match

RESULT:                                   RESULT:
  ✓ Finds task file correctly              ✗ Fails → returns []
                                             → WARNING logged
                                             → No AC injected
```

### Diagram 6: Wave 3 Timing — What Actually Happened

```
Time (seconds from wave start)
│
0s     ├── DB-005 starts (Thread A, direct mode, complexity=2)
       ├── DB-006 starts (Thread B, task-work mode, complexity=5)
       ├── DB-008 starts (Thread C, task-work mode, complexity=4)
       │   All 3 making concurrent requests to vLLM (single GPU)
       │
       │   ┌──── DB-005 ────┐  ┌────── DB-006 ──────┐  ┌────── DB-008 ──────┐
       │   │ Turn 1: Player  │  │ Turn 1: Player      │  │ Turn 1: Player      │
       │   │ (no AC injected)│  │ (task-work mode,     │  │ (task-work mode,     │
       │   │                 │  │  93+ SDK calls to    │  │  101 SDK turns,      │
       │   │                 │  │  vLLM in parallel    │  │  296 messages)       │
4800s  │   │ Player done     │  │  with DB-005/DB-008) │  │                      │
       │   │                 │  │                      │  │                      │
5430s  │   │ Coach: 0/6      │  │ ✗ SDK STREAM ERROR   │  │                      │
       │   │ (text path,     │  │   "unknown"          │  │                      │
       │   │  semantic mode, │  │   State recovery →   │  │                      │
       │   │  but generic    │  │   synthetic report   │  │                      │
       │   │  requirements)  │  │                      │  │                      │
5700s  │   │                 │  │ Coach: 0/6           │  │                      │
       │   │                 │  │ (promises+hybrid     │  │                      │
       │   │                 │  │  all "incomplete")   │  │                      │
5800s  │   │ Turn 2 starts   │  │                      │  │                      │
5900s  │   │                 │  │ Turn 2 starts        │  │                      │
       │   │                 │  │ (93 SDK turns,       │  │                      │
       │   │                 │  │  248 messages,       │  │                      │
       │   │                 │  │  9210+ seconds)      │  │                      │
7500s  │   │                 │  │                      │  │ Player done (101 SDK)│
       │   │                 │  │                      │  │                      │
8200s  │   │                 │  │                      │  │ Coach: 2/9 feedback  │
8500s  │   │                 │  │                      │  │ Turn 2 starts        │
8700s  │   │ Turn 2 done     │  │                      │  │ (29 SDK turns)       │
       │   │ Coach: 6/6 ✓    │  │                      │  │                      │
       │   │ APPROVED        │  │                      │  │                      │
       │   └─────────────────┘  │                      │  │                      │
9200s  │                        │                      │  │ Player done (29 SDK) │
9210s  │                        │ Player done (93 SDK) │  │ Coach Turn 2 starts  │
       │                        │ ◄── needs Coach but  │  │ (tests running)      │
       │                        │     timeout imminent  │  │                      │
       │                        │                      │  │                      │
9600s  ├─── TIMEOUT ────────────┤ ✗ CANCELLED         │  │ ✗ CANCELLED          │
       │    (per-task clock)    │   between Player &   │  │   during Coach       │
       │                        │   Coach              │  │   validation         │
       │                        │   8 files created,   │  │   all_gates_passed   │
       │                        │   39 modified,       │  │   =True before kill  │
       │                        │   1 test passing     │  │                      │
       │                        │   ALL DISCARDED      │  │   Work DISCARDED     │
       │                        └──────────────────────┘  └──────────────────────┘
       │
       │  RESULT: DB-005 APPROVED, DB-006 CANCELLED, DB-008 CANCELLED
       │          Wave 3: 1/3 passed → stop_on_failure → Wave 4 never runs
```

---

## Findings (Revised)

### Finding 1: `extract_acceptance_criteria()` Search Path Divergence (CRITICAL → ROOT CAUSE)

**Severity**: CRITICAL (root cause of DB-005 Turn 1 0/6, contributes to timeout cascade)
**Task**: TASK-DB-005 (Create initial migration), Turn 1
**Warning**: `WARNING: Task file not found for TASK-DB-005`

**Root Cause**: Two bugs in `extract_acceptance_criteria()` ([agent_invoker.py:4108-4133](guardkit/orchestrator/agent_invoker.py#L4108-L4133)):

| Issue | `extract_acceptance_criteria()` | `_find_task_file()` |
|-------|-------------------------------|---------------------|
| Directories | `in_progress/`, `backlog/`, `in_review/` | ALL 6 dirs including `design_approved/` |
| Filename | Exact `f"{task_id}.md"` | Glob `f"{task_id}*.md"` |
| Subdirs | Iterates but exact match | `rglob` (recursive) |

The task file is at `tasks/design_approved/TASK-DB-005-create-initial-migration.md`. Neither the missing directory nor the wrong filename pattern can find it.

**Causation Chain** (see Diagram 4):
1. File search fails → returns empty list
2. Player prompt has no acceptance criteria
3. Qwen3 produces generic `requirements_met` ("Initial database migration file created")
4. Coach uses text fallback path (no promises from direct mode)
5. Inside `_match_by_text()`, `_resolve_matching_strategy()` correctly returns `'semantic'` for vLLM
6. But semantic matching (50% Jaccard) still fails: generic text has ~17% overlap with specific AC text like "alembic/versions/001_create_users_table.py created via alembic revision --autogenerate"
7. 0/6 → Coach rejection → wasted Turn 1

**Why this matters**: This is the #1 fix. Every direct-mode task whose file has been moved to `design_approved/` (which is the state_bridge's standard flow) will fail Turn 1 and waste a turn. On Anthropic, faster turnaround means the wasted turn is absorbed. On vLLM with 4x slower generation, the wasted turn pushes tasks toward the timeout boundary.

**Correction from initial report**: Finding 5 (R6 "Ensure Semantic Matching on All vLLM Turns") was INCORRECT. The diagnostic log `matching_strategy: text` at line 1718 of coach_validator.py logs the local `strategy` variable (which tracks the code path: promises vs text), NOT the actual matching mode. Inside `_match_by_text()`, `_resolve_matching_strategy()` IS called and DOES return `'semantic'`. The matching strategy architecture is working correctly. R6 is withdrawn.

### Finding 2: Excessive SDK Turn Consumption (HIGH)

**Severity**: HIGH (direct cause of timeout exhaustion for DB-006 and DB-008)
**Affected Tasks**:
- TASK-DB-008 Turn 1: **101 SDK turns** (hit `TASK_WORK_SDK_MAX_TURNS=100`), 296 messages, 182 assistant
- TASK-DB-006 Turn 2: **93 SDK turns**, 248 messages, 154 assistant
- TASK-DB-008 Turn 2: 29 SDK turns (reasonable after Coach feedback)
- Anthropic typical: 15-30 SDK turns

**Root Cause**: Qwen3 takes many small incremental steps rather than batching operations. Each SDK turn involves a round-trip to vLLM, which on GB10 hardware (~4x slower than Anthropic API) means:
- 100 turns × ~90s/turn ≈ 9,000s per adversarial turn
- This consumes nearly the entire `task_timeout=9600s` on a single Player turn
- No time budget remains for Coach validation

**Architecture Context**: The `TASK_WORK_SDK_MAX_TURNS=100` limit ([agent_invoker.py:147](guardkit/orchestrator/agent_invoker.py#L147)) was designed for Anthropic models that complete in 15-30 turns. For local models, 100 turns is effectively unlimited.

**Impact**:
- DB-006: 93 turns on turn 2 used ~9,210s → cancelled at 9,600s before Coach could validate 8 files created, 39 modified
- DB-008: 101 turns on turn 1 used ~7,500s → Coach gave 2/9 feedback → turn 2 only had ~1,100s left

### Finding 3: SDK Streaming Error Under Parallel Load (HIGH)

**Severity**: HIGH (triggers cascading failure chain for DB-006)
**Task**: TASK-DB-006 (Implement CRUD operations), Turn 1
**Error**: `ERROR: [TASK-DB-006] SDK API error in stream: unknown`
**Elapsed**: ~5,430s into turn 1

**Root Cause**: Transient vLLM SSE stream interruption. Three concurrent SDK sessions (DB-005, DB-006, DB-008) all making parallel requests to the same local vLLM endpoint on a single GPU. The error is a connection-level break where the vLLM HTTP server dropped the stream mid-response under compute/memory pressure.

**Evidence**:
- Error occurs during peak concurrent load (3 tasks in Wave 3)
- No streaming errors during Waves 1-2 (sequential or lower parallelism)
- State recovery succeeded: captured 4 files changed, 157 tests
- Turn 2 of DB-006 completed without streaming errors (other tasks finished, reducing load)

**Cascading Impact**:
1. SDK error → state recovery → synthetic report with `_synthetic: True`
2. Synthetic report has git-analysis promises, all `incomplete` (partial work)
3. Coach receives synthetic report → `_match_by_promises()` → 0/6 (promises all incomplete)
4. Hybrid fallback → `_match_by_text()` with empty `requirements_addressed` → still 0/6
5. Coach rejection → full re-implementation on Turn 2 (93 SDK turns, 9,210s)
6. Turn 2 completes Player work but TIMEOUT fires before Coach runs

### Finding 4: Feature-Level Timeout and Cancellation Mechanics (MEDIUM)

**Severity**: MEDIUM (work lost but timeout design is architecturally correct)

**Architecture Confirmation**: Deep-dive of [feature_orchestrator.py:1286-1298](guardkit/orchestrator/feature_orchestrator.py#L1286-L1298) confirms:
- `asyncio.wait_for(..., timeout=self.task_timeout)` is per-task from dispatch time
- Each task gets its own `threading.Event` for cooperative cancellation (TASK-ASF-007)
- After `asyncio.gather()`, ALL events are signaled (cleanup for completed threads)

**What happened to DB-006**: The 9,600s timeout IS per-task, but DB-006 consumed:
- Turn 1: ~5,430s (Player until SDK error) + state recovery + Coach = ~5,700s
- Turn 2: ~3,510s more needed (9,210s total turn 2 elapsed)... but only ~3,900s remained
- The timeout is generous (160 min) but two SDK-intensive turns on Qwen3 exceeded it

**What happened to DB-008**: Similarly per-task, but:
- Turn 1: ~7,500s (101 SDK turns hitting the ceiling)
- Turn 2: ~1,700s (29 SDK turns, Player done, Coach started)
- Total: ~9,200s + Coach running → caught at 9,600s during Coach test execution
- `all_gates_passed=True` was set BEFORE cancellation → work was actually valid

**Secondary bug**: Both show `Critical error: None` in the summary — the cancellation path doesn't populate the error message field, producing a misleading display.

### Finding 5: Parallel Wave Resource Contention (LOW-MEDIUM)

**Severity**: LOW-MEDIUM
Wave 3 runs 3 tasks in parallel on local vLLM (single GPU):
- TASK-DB-005: complexity 2, direct mode, SDK timeout 5,760s
- TASK-DB-006: complexity 5, task-work mode, SDK timeout 10,800s
- TASK-DB-008: complexity 4, task-work mode, SDK timeout 10,080s

All three compete for the same GPU. The SDK streaming error on DB-006 correlates with peak parallel load. Anthropic API has effectively unlimited backend capacity; local vLLM does not.

However, reducing parallelism is a **medium-effort change** (new config parameter + execution logic changes) with **architectural risk** (affects all backends). The SDK error is the only direct consequence, and it was transient (Turn 2 succeeded). This is lower priority than Findings 1-2.

---

## Recommendations (Revised)

### Priority 1 (P0): Fix Before Next Run

#### R1: Fix `extract_acceptance_criteria()` Search Path (CRITICAL FIX)

**Target**: [agent_invoker.py:4108-4133](guardkit/orchestrator/agent_invoker.py#L4108-L4133)
**Change**: Align with `_find_task_file()` which already works correctly:
1. Add `design_approved/`, `completed/`, `blocked/` to search directories
2. Use glob pattern `f"{task_id}*.md"` instead of exact `f"{task_id}.md"`
3. Optionally: refactor to call `_find_task_file()` internally to avoid future divergence

**Implementation sketch**:
```python
# BEFORE (buggy):
possible_paths = [
    self.worktree_path / "tasks" / "in_progress" / f"{task_id}.md",
    self.worktree_path / "tasks" / "backlog" / f"{task_id}.md",
    self.worktree_path / "tasks" / "in_review" / f"{task_id}.md",
]

# AFTER (aligned with _find_task_file):
task_file = self._find_task_file(task_id)
if not task_file:
    logger.warning(f"Task file not found for {task_id}")
    return []
```

**Rationale**: This is the root cause of DB-005 Turn 1 0/6. Fixing this means direct-mode tasks get AC injection on Turn 1, dramatically improving first-turn success rate.
**Effort**: Small (5 lines changed, or 1 line if calling `_find_task_file()`)
**Risk**: Very low — `_find_task_file()` has been working correctly throughout

#### R2: Add SDK Turn Budget for Local Models

**Target**: [agent_invoker.py:147](guardkit/orchestrator/agent_invoker.py#L147) — `TASK_WORK_SDK_MAX_TURNS`
**Change**: Add `GUARDKIT_SDK_MAX_TURNS` env var override, defaulting to 50 for local backends
**Implementation sketch**:
```python
TASK_WORK_SDK_MAX_TURNS = int(os.environ.get(
    "GUARDKIT_SDK_MAX_TURNS",
    100  # Anthropic default
))
# In _calculate_sdk_timeout() or invoke_player():
if detect_timeout_multiplier() > 1.0:
    effective_max_turns = min(TASK_WORK_SDK_MAX_TURNS, 50)
```

**Rationale**: Qwen3 hitting 93-101 turns means each adversarial turn consumes the entire task timeout. A 50-turn limit forces Qwen3 to focus and fail faster, allowing more adversarial turns within the budget. At 50 turns × ~90s/turn ≈ 4,500s, leaving ~5,100s for a second turn + Coach.
**Effort**: Small (env var + conditional)
**Risk**: Low — env var override means it's tunable without code changes

### Priority 2 (P1): Improve Robustness

#### R3: Fix "Critical error: None" Cancellation Display

**Target**: `autobuild.py` summary rendering
**Change**: Detect `decision="cancelled"` and display "Task timed out" instead of "Critical error: None"
**Rationale**: Misleading error message makes debugging harder. The work may have been complete.
**Effort**: Small (display logic fix)
**Risk**: None

#### R4: Add vLLM Streaming Retry Logic

**Target**: `agent_invoker.py` SDK invocation
**Change**: On `SDK API error in stream: unknown`, retry the SDK invocation once (with 30s backoff) before falling to state recovery
**Rationale**: The streaming error was transient. A single retry might have succeeded without the expensive state-recovery → re-implementation path that consumed Turn 2's entire budget.
**Effort**: Medium (retry wrapper around SDK stream)
**Risk**: Low — single retry with backoff, falls through to existing state recovery on second failure

### Priority 3 (P2): Consider for Future

#### R5: Reduce Wave Parallelism for Local Backends

**Target**: `feature_orchestrator.py` wave execution
**Change**: Add `GUARDKIT_MAX_PARALLEL_TASKS` env var, defaulting to 2 for local backends
**Rationale**: 3 concurrent vLLM sessions contributed to the SDK streaming error. However, the error was transient and the primary issues (R1, R2) are more impactful.
**Effort**: Medium (new config + execution logic)
**Risk**: Medium — affects all backends, needs careful testing to avoid breaking Anthropic parallel execution

**Deferred reasoning**: With R1 (AC injection fix) and R2 (turn budget), Wave 3 timing improves dramatically:
- DB-005: Likely passes Turn 1 (AC injection → specific output → match), saving ~4,000s
- DB-006/DB-008: 50-turn limit means each turn takes ~4,500s max, fitting 2 turns + Coach in 9,600s
- Reduced total GPU time may naturally eliminate the streaming error

---

## Withdrawn Recommendations

### ~~R6: Ensure Semantic Matching on All vLLM Turns~~ (WITHDRAWN)

**Reason**: Deep-dive confirms semantic matching IS active on all paths for vLLM backends. The diagnostic log `matching_strategy: text` is the code path variable name, not the matching mode. Inside `_match_by_text()`, `_resolve_matching_strategy()` correctly returns `'semantic'` when `ANTHROPIC_BASE_URL` points to localhost. The 0/6 on DB-005 Turn 1 is caused by missing AC injection (Finding 1), not matching strategy.

### ~~R4 (original): Make Task Timeout Per-Task Not Per-Wave~~ (WITHDRAWN)

**Reason**: Deep-dive confirms the timeout IS already per-task. `asyncio.wait_for()` wraps each individual `asyncio.to_thread()` call with `self.task_timeout`. The timeout issue is caused by excessive SDK turns consuming the per-task budget, not by wave-level timing.

---

## Decision Matrix (Revised)

| Fix | Impact | Effort | Risk | Priority | Status |
|-----|--------|--------|------|----------|--------|
| R1: Fix AC search path | **Critical** | Small | Very Low | P0 | NEW: elevated from Medium |
| R2: SDK turn budget | High | Small | Low | P0 | Unchanged |
| R3: Fix error display | Low | Small | None | P1 | Unchanged (was R5) |
| R4: Streaming retry | Medium | Medium | Low | P1 | Unchanged (was R7) |
| R5: Reduce parallelism | Medium | Medium | Medium | P2 | Deferred (was P0) |
| ~~R6: Semantic matching~~ | ~~Medium~~ | ~~Small~~ | ~~Low~~ | N/A | **WITHDRAWN** |
| ~~R4-orig: Per-task timeout~~ | ~~High~~ | ~~Medium~~ | ~~Medium~~ | N/A | **WITHDRAWN** |

## Predicted Run 3 Outcome (With P0 Fixes Only)

With R1 (AC search fix) and R2 (50-turn SDK budget):

| Wave | Tasks | Prediction | Reasoning |
|------|-------|------------|-----------|
| Wave 1 | DB-001 | PASS | No change (already working) |
| Wave 2 | DB-002, DB-003, DB-004 | PASS | No change (timeout fix from run 1 working) |
| Wave 3 | DB-005, DB-006, DB-008 | **Likely PASS** | DB-005: AC injection → Turn 1 pass (saves ~4000s GPU time). DB-006/DB-008: 50-turn limit → ~4500s/turn → fits 2 turns + Coach in 9600s. Less GPU contention → streaming error less likely |
| Wave 4 | DB-007 | **Likely PASS** | Single task, benefits from all fixes |
| **Expected** | | **7-8/8 tasks** | |

**Conservative estimate**: 6-7/8 (Wave 3 streaming error may still occur under parallel load, but R1+R2 provide enough time budget for recovery)

## Architecture Validation Summary

The deep-dive confirms the following architecture is **working correctly** and **must not be changed**:

| Component | Status | Evidence |
|-----------|--------|----------|
| `timeout_multiplier=4.0x` auto-detection | ✓ Working | Wave 2 fully passing (was failing in run 1) |
| Cooperative cancellation (TASK-ASF-007) | ✓ Working | Clean thread shutdown, no zombie processes |
| State recovery (TASK-ASF-006) | ✓ Working | Captured 4 files changed after SDK error |
| Semantic matching auto-resolution | ✓ Working | `_resolve_matching_strategy()` returns 'semantic' for vLLM |
| Text-matching fixes (TASK-FIX-TM01-04) | ✓ Working | 50% Jaccard + fuzzy prefix matching active |
| Per-task timeout via `asyncio.wait_for()` | ✓ Working | Each task gets independent 9600s budget |
| `--fresh` flag | ✓ Working | No stale state issues in run 2 |
| State bridge `_find_task_file()` | ✓ Working | Uses correct glob + all directories |

## Appendix

### A. TASK-REV-8A94 Fixes Status (Updated)

| Run 1 Fix | Applied in Run 2? | Result | Preserve? |
|-----------|--------------------|--------|-----------|
| timeout_multiplier=4.0x | Yes | Wave 2 FIXED | ✓ YES |
| --fresh flag | Yes | Stale state FIXED | ✓ YES |
| TASK-FIX-TM01-04 text matching | Yes | Semantic matching working | ✓ YES |
| Cooperative cancellation (TASK-ASF-007) | Yes | Clean shutdown working | ✓ YES |
| State recovery (TASK-ASF-006) | Yes | Captures partial work | ✓ YES |
| SDK turn limit for local | No | NEW: 93-101 turns observed | → R2 |
| AC search path fix | No | NEW: design_approved/ missed | → R1 |

### B. Source Code Evidence

| File | Line(s) | What Was Verified |
|------|---------|-------------------|
| `agent_invoker.py` | 4108-4133 | `extract_acceptance_criteria()` — confirmed missing `design_approved/`, confirmed exact filename match |
| `agent_invoker.py` | 2226-2252 | `_find_task_file()` — confirmed correct: uses `rglob`, searches all 6 directories |
| `agent_invoker.py` | 147 | `TASK_WORK_SDK_MAX_TURNS = 100` — confirmed no per-backend override |
| `coach_validator.py` | 1217-1233 | `_resolve_matching_strategy()` — confirmed returns 'semantic' for custom API |
| `coach_validator.py` | 1513-1721 | `validate_requirements()` — confirmed decision tree, diagnostic log uses code path variable |
| `coach_validator.py` | 1702-1719 | 0/N diagnostic — confirmed `strategy` variable is code path label, not matching mode |
| `feature_orchestrator.py` | 1286-1298 | Per-task timeout via `asyncio.wait_for()` — confirmed per-task, not per-wave |
| `feature_orchestrator.py` | 1304-1311 | Cooperative cancellation — confirmed all events set after gather |
| `state_bridge.py` | 309 | `rglob(f"{self.task_id}*.md")` — confirmed correct pattern |

### C. Key Correction Log

| Initial Finding | Correction | Evidence |
|----------------|------------|----------|
| F5: "matching_strategy: text means text mode active" | `matching_strategy: text` is the code path variable, not matching mode. Semantic IS active inside `_match_by_text()` | coach_validator.py:1670 sets `strategy = "text"`, line 1718 logs it. But line 2051-2121 inside `_match_by_text()` calls `_resolve_matching_strategy()` which returns 'semantic' |
| R6: "Ensure semantic matching on all turns" | Semantic matching already works on all turns for vLLM. The 0/6 is caused by missing AC injection | DB-005 Turn 1 log shows "Matching strategy auto-resolved to 'semantic'" at line 1513 |
| R4-orig: "Timeout is per-wave not per-task" | Timeout is already per-task via `asyncio.wait_for()` | feature_orchestrator.py:1292-1298: each task wrapped independently |
| F1 severity: MEDIUM | Elevated to CRITICAL — this is the root cause of the entire DB-005 failure chain | Full causation chain traced in Diagram 4 |
