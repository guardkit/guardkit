# Review Report: TASK-REV-9745

## Executive Summary

Root cause identified through deep verification. The `completion_promises` stall regression is caused by **stochastic agent behaviour combined with a broken fallback chain**. The Player agent non-deterministically omits `completion_promises` from its player report. When this occurs, every fallback mechanism silently fails: `TaskWorkStreamParser` never populates them, Fix 2 is agent-dependent, the TASK-FIX-AE7E backward scan can only recover from prior turns that had them, and Fix 5 silently produces nothing because `_find_task_file()` does not search the `design_approved` directory (where autobuild tasks always live).

**Revised from initial report**: The initial hypothesis (TASK-FIX-0C22 causing SDK turn exhaustion on turn 1 → incomplete player report) was **disproved by deep verification**. Turns 2 and 3 in the failing run used only 42 and 18 SDK turns respectively yet still produced no `completion_promises`. Turn exhaustion is therefore not causal.

**True root cause**: Non-deterministic agent behaviour — the agent sometimes writes `completion_promises` and sometimes doesn't. The only reliable structural fallback (Fix 5) has always been broken for autobuild tasks due to `_find_task_file()` not searching `design_approved`.

**Verified by**:
- Turns 2 & 3 of failing run: 42 and 18 SDK turns (not exhausted) → still no completion_promises
- `TaskWorkStreamParser` source: zero regex patterns for `completion_promises`
- Worktree `player_turn_2.json`: `"implementation_notes": "Implementation via task-work delegation"` (orchestrator-injected default, Fix 2 found nothing to recover)
- `ls` of worktree `tasks/`: only `backlog/` and `design_approved/` exist; `_find_task_file()` searches neither `design_approved` nor any of the actual directories containing the task file

---

## Review Details

- **Mode**: Decision analysis (root cause investigation)
- **Depth**: Comprehensive (revised after initial standard review)
- **Complexity**: 4/10
- **Related commits examined**: TASK-FIX-AE7E, TASK-FIX-A7F1, TASK-FIX-70F3, TASK-FIX-4415, TASK-FIX-0C22
- **Evidence sources**: Failing run log (`first_task_now_fails.md`), passing run log (`db_after_more_fiexes.md`), preserved worktree artifacts, source code

---

## Findings

### Finding 1 — `TaskWorkStreamParser` Never Populates `completion_promises` (STRUCTURAL GAP)

**File**: `guardkit/orchestrator/agent_invoker.py` (`TaskWorkStreamParser` class, ~line 153+)

`task_work_results.json` is built by `TaskWorkStreamParser`, which has regex patterns for test counts, coverage percentages, quality gates, file paths — but **zero patterns for `completion_promises`**.

The `_write_task_work_results()` method (line ~4075) conditionally includes `completion_promises` from `result_data`, but `result_data` from the stream parser never has this key. So `task_work_results.json` never contains `completion_promises`, for any run, ever.

**Consequence**: `_load_completion_promises()` in `coach_validator.py` checks `task_work_results.get("completion_promises", [])` first — this always returns `[]`. The only source of truth is the agent-written `player_turn_N.json`.

**This is a pre-existing structural gap, not a regression.** The system has always depended entirely on the agent voluntarily writing `completion_promises`.

### Finding 2 — Fix 2 Is Agent-Dependent (CORRECT BUT INSUFFICIENT)

**File**: `guardkit/orchestrator/agent_invoker.py:1620`

Fix 2 reads the agent-written `player_turn_N.json` BEFORE overwriting it and recovers `completion_promises` if present. This is logically correct. In the passing run (turn 2), Fix 2 successfully recovered 6 promises ("Recovered 6 completion_promises from agent-written player report").

In the failing run, the agent wrote `player_turn_1.json` with `"completion_promises": []` on turn 1. Fix 2 read it, found `[]`, and correctly skipped recovery. Turns 2 and 3 also had no promises from the agent. Fix 2 has no defect — it depends entirely on the agent having written promises in the first place.

**Confirmed**: Worktree `player_turn_2.json` contains `"implementation_notes": "Implementation via task-work delegation"` — this is the orchestrator-injected default string, confirming Fix 2 found nothing to recover on turn 2.

### Finding 3 — TASK-FIX-AE7E Backward Scan Is Correct (NOT THE CAUSE)

**File**: `guardkit/orchestrator/quality_gates/coach_validator.py:1610`

The backward scan introduced by TASK-FIX-AE7E iterates prior `player_turn_N.json` files looking for `completion_promises`. This is logically correct and handles the scenario where turn 1 had promises but later turns omitted them.

In this regression, no turn ever had `completion_promises`. The backward scan therefore finds nothing — not because it has a bug, but because there is nothing to find. TASK-FIX-AE7E is working as designed.

### Finding 4 — Fix 5 Silently Fails for All Autobuild Tasks (STRUCTURAL BUG)

**File**: `guardkit/orchestrator/agent_invoker.py:1653` (`_find_task_file()`, line 1823)

Fix 5 (`_generate_file_existence_promises`) is intended to synthesise `completion_promises` from file existence checks when the agent produces none. It calls `_find_task_file(task_id)` to load the acceptance criteria.

**`_find_task_file` search dirs** (line 1833–1838):
```python
task_dirs = [
    self.worktree_path / "tasks" / "backlog",
    self.worktree_path / "tasks" / "in_progress",
    self.worktree_path / "tasks" / "in_review",
    self.worktree_path / "tasks" / "completed",
    self.worktree_path / "tasks" / "blocked",
]
```

**Actual worktree task directories** (confirmed by inspection):
```
tasks/backlog/
tasks/design_approved/   ← NOT SEARCHED
```

In the autobuild workflow, tasks are moved to `design_approved` before Player invocation (via `state_bridge.py`). The task file is at `tasks/design_approved/TASK-DB-001-*.md`. Since `design_approved` is absent from the search list, `_find_task_file()` returns `None`, Fix 5 produces no promises, and the fallback silently fails.

**This is a pre-existing bug** — Fix 5 has never worked correctly for any autobuild task that follows the `design_approved` state flow. The worktree `tasks/` directory had only `backlog/` and `design_approved/` — Fix 5 would never find anything even in `backlog/` because the task had already moved to `design_approved/`.

### Finding 5 — None of the Intervening Commits Caused the Regression

All five commits between the passing run (16:17) and failing run (21:17) were examined:

| Commit | Task | Scope | Effect on completion_promises |
|--------|------|-------|-------------------------------|
| TASK-FIX-AE7E | Cross-turn memory | coach_validator.py | None (backward scan is additive) |
| TASK-FIX-A7F1 | Plan audit fix | plan_auditor.py | None |
| TASK-FIX-70F3 | Accumulate test files | coach_validator.py | None |
| TASK-FIX-4415 | psycopg2 feedback | coach_validator.py | None |
| TASK-FIX-0C22 | postgresql+asyncpg URL | docker fixtures | None (no `requires_infrastructure`) |

`autobuild_execution_protocol.md` (the protocol injected into the Player prompt instructing it to write `completion_promises`) was **not changed** between the two runs.

### Finding 6 — True Cause: Stochastic Agent Behaviour with No Working Fallback

The Player agent receives `autobuild_execution_protocol.md` instructing it to write a `player_turn_N.json` with a `completion_promises` array. The agent non-deterministically complies. In the passing run (turn 2), it happened to write all 6 promises. In the failing run (all 3 turns), it did not.

When the agent omits `completion_promises`, the system has no working fallback:

| Mechanism | Status | Why it fails |
|-----------|--------|-------------|
| `TaskWorkStreamParser` | Never populates | No regex pattern exists |
| Fix 2 recovery | Agent-dependent | Reads agent file, finds `[]` |
| TASK-FIX-AE7E backward scan | Correct but insufficient | No prior turn had promises to scan |
| Fix 5 file-existence synthesis | **Structurally broken** | `_find_task_file()` never finds task in `design_approved` |

Result: `completion_promises = []` across all turns → `matching_strategy: text` → `requirements_met: []` → 0/6 → `UNRECOVERABLE_STALL`.

### Finding 7 — SDK Turn Exhaustion Is Not Causal (INITIAL HYPOTHESIS DISPROVED)

**Initial hypothesis** (from first review): TASK-FIX-0C22 caused the Player to exhaust max_turns=50 on turn 1, preventing it from writing `completion_promises`.

**Disproved by deep verification**:
- Failing run turn 2: 42 SDK turns (not exhausted) → still no `completion_promises`
- Failing run turn 3: 18 SDK turns (not exhausted) → still no `completion_promises`
- Passing run turn 1: 34 SDK turns → also no `completion_promises`
- Passing run turn 2: 25 SDK turns → **6 completion_promises written** ✓

The agent's decision to write `completion_promises` is non-deterministic across turns and runs. Turn exhaustion may correlate with lower probability of writing them (less time to complete all protocol steps), but it is not the necessary condition. The agent can fail to write promises even with ample turns remaining.

**TASK-FIX-0C22** is also irrelevant to TASK-DB-001 specifically: `requires_infrastructure` is not set in TASK-DB-001's task file, so the `postgresql+asyncpg://` URL change in docker fixtures does not affect what the Player agent does.

---

## Verified Root Cause Chain

```
Agent non-deterministically writes player_turn_N.json WITHOUT completion_promises
    ├─► TaskWorkStreamParser: never populates (structural gap)
    ├─► Fix 2: reads agent file, finds [] → no recovery
    ├─► TASK-FIX-AE7E backward scan: no prior turn had promises → finds nothing
    └─► Fix 5: _find_task_file() returns None (design_approved not searched)
        └─► completion_promises = [] across all turns
            └─► _verify_requirements(): matching_strategy = text
                └─► requirements_met = [] → 0/6 criteria
                    └─► UNRECOVERABLE_STALL
```

---

## Recommendations

### Recommendation 1 (IMMEDIATE FIX): Add `design_approved` to `_find_task_file` search dirs

**File**: `guardkit/orchestrator/agent_invoker.py:1833`
**Priority**: HIGH — trivial change that enables the only structural fallback to actually work
**Complexity**: 1 line

```python
task_dirs = [
    self.worktree_path / "tasks" / "backlog",
    self.worktree_path / "tasks" / "design_approved",  # ADD THIS
    self.worktree_path / "tasks" / "in_progress",
    self.worktree_path / "tasks" / "in_review",
    self.worktree_path / "tasks" / "completed",
    self.worktree_path / "tasks" / "blocked",
]
```

**Impact**: Fix 5 can now find the task file, read its acceptance criteria, and generate file-existence promises. This provides a meaningful fallback when the agent omits `completion_promises`. The file-existence promises are imperfect (they check whether files exist, not whether criteria are truly met) but they are far better than 0/6 → stall.

**Regression risk**: Zero. Adding a directory to the search list cannot break existing behavior.

### Recommendation 2 (STRENGTHEN PROTOCOL): Make completion_promises mandatory in Player prompt

**File**: `guardkit/orchestrator/prompts/autobuild_execution_protocol.md`
**Priority**: HIGH — addresses the root non-determinism directly
**Complexity**: Low

The current protocol instructs the agent to write `player_turn_N.json` with `completion_promises`. Strengthen this to make non-compliance harder to miss:

1. Move `completion_promises` to the **first** field in the player report schema (agents tend to write fields top-to-bottom; front-loading reduces truncation risk)
2. Add an explicit instruction: "You MUST populate `completion_promises` for every acceptance criterion in the task. If you cannot evaluate a criterion, include it with `status: uncertain` and explain why in `evidence`. An empty `completion_promises` array causes a stall — never leave it empty."
3. Consider adding a self-check step at the end of the protocol: "Before writing your player report, verify that `completion_promises` has one entry per acceptance criterion."

**Regression risk**: None. Stronger protocol instructions can only improve agent compliance.

### Recommendation 3 (DIAGNOSTIC): Warn when Fix 5 is invoked but returns nothing

**File**: `guardkit/orchestrator/agent_invoker.py:1653`
**Priority**: MEDIUM — makes silent failures visible
**Complexity**: Trivial

Currently when `_find_task_file()` returns `None`, Fix 5 silently does nothing. Add a warning:

```python
task_file = self._find_task_file(task_id)
if task_file is None:
    logger.warning(
        f"Fix 5: _find_task_file returned None for {task_id} — "
        f"completion_promises fallback unavailable. "
        f"Searched: {[str(d) for d in task_dirs]}"
    )
```

This would have made the regression immediately diagnosable from logs.

### Recommendation 4 (DIAGNOSTIC): Warn on SDK turn exhaustion

**File**: `guardkit/orchestrator/agent_invoker.py` (after SDK completion)
**Priority**: LOW — aids future debugging
**Complexity**: Trivial

When `SDK completed: turns=N` and N equals `max_turns`, log a WARNING:
```
WARNING: SDK hit max_turns limit for TASK-DB-001 (turns=50).
Player report may be incomplete. Consider increasing max_turns or reducing task scope.
```

---

## Acceptance Criteria Assessment

- [x] **Root cause identified**: Stochastic agent behaviour + Fix 5 structurally broken (design_approved not searched)
- [x] **All 5 intervening commits verified as non-causal**
- [x] **Initial hypothesis revised**: SDK turn exhaustion disproved by turns 2/3 evidence
- [x] **TASK-FIX-AE7E regression risk**: None. Backward scan is correct; proposed fixes don't touch it.
- [x] **TASK-FIX-4415 regression risk**: None. psycopg2 detection is independent of completion_promises.
- [x] **Fix 5 blind spot**: Confirmed by `ls` of worktree tasks directory and `_find_task_file()` source.

---

## Implementation Tasks to Create

### TASK-FIX-XXXX (Priority: HIGH) — Add `design_approved` to `_find_task_file` search dirs
- **Scope**: Single line change in `agent_invoker.py`
- **Tests**: Add test case for `_find_task_file` with task in `design_approved`
- **Mode**: Standard (trivial fix)

### TASK-FIX-XXXX (Priority: HIGH) — Strengthen completion_promises protocol instructions
- **Scope**: `autobuild_execution_protocol.md` — reorder fields, add explicit mandate
- **Tests**: Not directly testable (LLM behaviour), but reduces non-compliance probability
- **Mode**: Standard

---

## Appendix: Evidence Artifacts

### Failing run diagnostics (all 3 turns identical pattern):
```
WARNING: Criteria verification 0/6 - diagnostic dump:
WARNING:   requirements_met: []
WARNING:   completion_promises: (not used)
WARNING:   matching_strategy: text
WARNING:   _synthetic: False
```

### SDK turn counts across runs:
| Run | Turn | SDK turns | completion_promises | Result |
|-----|------|-----------|---------------------|--------|
| Passing (16:17) | 1 | 34 | [] (not written) | 0/6 → feedback |
| Passing (16:17) | 2 | 25 | **[AC-001…AC-006]** | **6/6 → approved** |
| Failing (21:17) | 1 | **50 (max)** | [] | 0/6 → feedback |
| Failing (21:17) | 2 | 42 | [] | 0/6 → feedback |
| Failing (21:17) | 3 | 18 | [] | 0/6 → stall |

### player_turn_2.json `implementation_notes` (failing run, worktree):
```json
{ "implementation_notes": "Implementation via task-work delegation" }
```
This is the orchestrator-injected default — confirming Fix 2 found no agent-written promises to recover on turn 2.

### `_find_task_file` search dirs vs actual worktree layout:
```
Searched: backlog, in_progress, in_review, completed, blocked
Actual worktree tasks/: backlog/, design_approved/   ← mismatch
```
