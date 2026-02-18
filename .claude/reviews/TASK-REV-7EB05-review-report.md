# Review Report: TASK-REV-7EB05 (Revision 2)

## Executive Summary

After the three TASK-REV-CB30 recommendations were implemented, FEAT-BA28 makes significant forward progress — TASK-DB-001 and TASK-DB-002 both APPROVE. TASK-DB-003 hits UNRECOVERABLE_STALL after 4 turns.

**The most important framing**: The Player completed TASK-DB-003 correctly on turn 1. `player_turn_1.json` contains all 6 `completion_promises` marked complete with detailed evidence, all 6 `requirements_addressed` populated, implementation files created. The agent_invoker confirms: "Recovered 6 completion_promises" and "Recovered 6 requirements_addressed". The work was done. Everything that went wrong after turn 1 is orchestration scaffolding failing to recognise work that was already complete.

The stall has **three compounding failures**, not two:

1. **Turn 1 — psycopg2 misclassified as infrastructure failure**: `_classify_test_failure` promotes `psycopg2` `ModuleNotFoundError` to `("infrastructure", "high")` because `psycopg2` is in `_KNOWN_SERVICE_CLIENT_LIBS`. But this is not an infrastructure problem — it's a wrong-library-choice by the Player. The Coach then gives the Player feedback saying "infrastructure/environment issues (not code defects)" with hints about mock fixtures or SQLite. That is the wrong feedback. Even if R2 (criteria verification) were fixed, the Player would still receive misleading turn-1 feedback that actively misdirects it.

2. **Turns 2-4 — Criteria verification always 0/6**: The Player does not write `completion_promises` or `requirements_met` in its fresh `task_work_results.json` on iterative fix turns. Since no agent-written `player_turn_N.json` exists before `_process_task_work_results()` runs on those turns, the recovery path in agent_invoker cannot help either. Both fields remain empty → 0/6 → identical feedback → stall.

3. **Turns 2-4 — Enrichment timing bug**: `task_work_results.json` is freshly overwritten by the Player at the start of each turn. The enrichment from turn N-1 (which correctly contained `completion_promises`) is discarded. Each turn starts from a blank slate. The Coach's `_load_completion_promises()` first checks `task_work_results.get("completion_promises", [])` — guaranteed empty on iterative turns — then looks for `player_turn_{turn}.json` which doesn't exist yet at that point. The pipeline has no cross-turn memory of previously verified criteria.

All three TASK-REV-CB30 fixes (R5 Option B, R6, R7) are **confirmed working and correct**.

## Review Details

- **Mode**: Architectural Review
- **Depth**: Standard (revised per additional evidence analysis)
- **Task**: TASK-REV-7EB05
- **Parent Review**: TASK-REV-CB30
- **Evidence**: `docs/reviews/autobuild-fixes/db_after_more_fiexes.md`

## TASK-REV-CB30 Fix Verification

All three recommendations confirmed working:

| Fix | Status | Evidence |
|-----|--------|---------|
| R5 Option B (subprocess pinning) | ✅ | Line 443: `Running independent tests via subprocess (infra-pinned, sys.executable=/usr/local/bin/python3)` |
| R7 (interpreter diagnostic) | ✅ | Line 439: correct sys.executable logged |
| R6 (conditional approval at logger.info) | ✅ | Line 447: visible in log output |

**R5 Option B is structurally correct**: The 0.7s failure duration (vs 0.19s before) confirms sqlalchemy now imports fine — the PATH resolution bug is resolved. The new failure is psycopg2, a different package entirely, occurring after sqlalchemy succeeds.

## Findings

### Finding 1: Player Work Was Complete on Turn 1 (CRITICAL CONTEXT)

**Severity**: Critical context — reframes all subsequent findings

**Evidence**: agent_invoker log for TASK-DB-003 turn 1:
```
Recovered 6 completion_promises from agent-written player report for TASK-DB-003
Recovered 6 requirements_addressed from agent-written player report for TASK-DB-003
```

The Player wrote a complete `player_turn_1.json` with all 6 promises satisfied. The orchestration then failed to use this data correctly over the next 3 turns. This is not a Player competence failure — it is an orchestration resilience failure.

### Finding 2: psycopg2 Classified as Infrastructure — Wrong and Actively Harmful (HIGH)

**Severity**: High — produces wrong feedback on turn 1, misdirects Player on subsequent turns

**Code** ([coach_validator.py:2334-2340](guardkit/orchestrator/quality_gates/coach_validator.py#L2334-L2340)):
```python
# Promote ModuleNotFoundError to high confidence for known service-client libraries
if "modulenotfounderror" in output_lower and "no module named" in output_lower:
    match = re.search(r"no module named '([^']+)'", test_output, re.IGNORECASE)
    if match:
        missing_module = match.group(1).split(".")[0]
        if missing_module in self._KNOWN_SERVICE_CLIENT_LIBS:
            return ("infrastructure", "high")  # ← psycopg2 hits this path
```

**`_KNOWN_SERVICE_CLIENT_LIBS`** ([coach_validator.py:400-410](guardkit/orchestrator/quality_gates/coach_validator.py#L400-L410)):
```python
_KNOWN_SERVICE_CLIENT_LIBS: List[str] = [
    "psycopg2",   # ← classified as infrastructure dep
    "asyncpg",
    "pymongo",
    ...
]
```

**The problem**: `_KNOWN_SERVICE_CLIENT_LIBS` treats these as "missing infrastructure dependency" by definition. For `asyncpg`, `pymongo`, `redis` — that's usually correct. For `psycopg2` in an asyncpg-based stack, it means the Player chose the wrong library. The classification cannot distinguish between "psycopg2 not installed because it's needed and wasn't bootstrapped" and "psycopg2 not installed because this is an asyncpg project and psycopg2 shouldn't be used at all".

**Consequence**: Coach gives the Player feedback saying tests failed due to infrastructure/environment issues, hints at mock fixtures or SQLite testing. The Player receives this signal and tries to adapt — but the real problem is the import itself. This could cause the Player to add mock fixtures that bypass the database entirely, pass the test, but ship a codebase that still has a wrong import at the module level.

**Context-sensitivity**: `psycopg2` is infrastructure-related when the project uses it (e.g., Django with psycopg2). It is a code defect when the project uses asyncpg. The classifier has no access to the project's declared stack. The bootstrap dependency list IS accessible — if psycopg2 is not in the bootstrap deps, it's a Player code error.

### Finding 3: Criteria Verification Has No Cross-Turn Memory (CRITICAL)

**Severity**: Critical — structural gap that guarantees stalls on iterative turns when Player omits completion_promises

**The flow** (tracing the code):

1. Player SDK writes `task_work_results.json` — fresh each turn, no `completion_promises` on iterative turns
2. `agent_invoker._process_task_work_results()` checks `player_turn_{N}.json` for recovery — file doesn't exist on turns 2-4 (Player didn't write it directly)
3. File-existence synthetic fallback runs ([agent_invoker.py:1656-1675](guardkit/orchestrator/agent_invoker.py#L1656-L1675)) — but generates synthetic promises based on file existence, not criteria satisfaction
4. `task_work_results.json` is updated with enriched data including any synthetic promises
5. Coach reads `task_work_results.json`, calls `validate_requirements()`
6. `_load_completion_promises()` ([coach_validator.py:1560-1561](guardkit/orchestrator/quality_gates/coach_validator.py#L1560-L1561)) checks `task_work_results.get("completion_promises", [])` — may have synthetic ones
7. If synthetic promises don't match criteria text → 0/6 → `requirements_met: []` fallback → 0/6

**Why synthetic promises don't help**: The file-existence fallback generates promises like "file X exists therefore criterion Y is met" — but the criteria for TASK-DB-003 are behavioural ("CRUDBase provides generic CRUD operations with type safety", "CRUD methods use flush() not commit()"). File existence cannot verify behaviour. The synthetic promises fail criteria matching.

**Why turn 1's correct promises are lost**: Turn 1 agent_invoker successfully recovers 6 `completion_promises` and writes them back to `task_work_results.json`. But on turn 2, the Player overwrites `task_work_results.json` with a fresh file that has no `completion_promises`. The enriched turn-1 data is discarded. The autobuild orchestrator has no cross-turn memory of "we already verified these criteria from a previous turn's promises."

**Contrast with TASK-DB-001**: DB-001 turn 2 Player wrote `completion_promises` directly into its `task_work_results.json` (6 recovered, 6 requirements_addressed). DB-003 Player never did on turns 2-4. The only difference is Player output variability across tasks.

### Finding 4: Enrichment Timing — task_work_results.json Overwritten Each Turn (MODERATE)

**Severity**: Moderate — structural explanation for why promise recovery doesn't persist

**The sequence** each turn:
```
1. Player SDK runs → writes task_work_results.json (fresh, Player-controlled content)
2. agent_invoker._process_task_work_results():
   a. Reads task_work_results.json
   b. Tries to recover from player_turn_N.json (may not exist)
   c. Generates synthetic promises if needed
   d. Writes enriched task_work_results.json (now has completion_promises if recovery worked)
   e. Writes player_turn_N.json
3. Coach reads task_work_results.json (the enriched version from step 2d)
```

The enrichment in step 2 does propagate to `task_work_results.json` BEFORE Coach reads it — so there's no race condition in the strict sense. The problem is subtler: **each turn starts fresh**. The enriched `task_work_results.json` from turn N-1 is unconditionally overwritten by the Player at step 1 of turn N. The orchestrator accumulates no persistent per-task state across turns about which criteria were verified.

**The structural gap**: The autobuild loop uses `task_work_results.json` as a communication channel between Player and Coach. It was designed as a single-turn artifact. When the Player omits `completion_promises` on turn N, there is no mechanism to say "but we verified these criteria in turn N-1 based on strong evidence". The autobuild criteria tracker (`autobuild.py` criteria progress logic) does accumulate verified counts across turns — but it reads from Coach decisions, not from raw promises. When Coach gives feedback (not approve), criteria counts from that turn are marked rejected, not preserved.

### Finding 5: Independent Test Detection Fails on Iterative Turns (MODERATE)

**Severity**: Moderate — compound factor, independent of criteria issue

**Evidence**:
- Turn 1: `Task-specific tests detected via task_work_results: 1 file(s)` — `tests/users/test_users.py` listed in `files_created`
- Turns 2-4: `No task-specific tests found for TASK-DB-003, skipping independent verification. Glob pattern tried: tests/**/test_task_db_003*.py`

**Root cause**: `_detect_tests_from_results()` scans `files_created` and `files_modified` for test files. On iterative turns the Player modifies source code, not test files. The fallback glob `tests/**/test_task_db_003*.py` doesn't match `tests/users/test_users.py` (file name contains no task ID). The cumulative diff fallback should find it — `tests/users/test_users.py` was committed in checkpoint 3659ea3f — but in a shared worktree with TASK-DB-002, the `_find_first_checkpoint_parent()` logic may not isolate DB-003's commits correctly.

**Effect on stall**: Even if criteria verification (Finding 3) were fixed and Coach could verify 6/6 from prior promises, there's still no independent test execution on turns 2-4. If the psycopg2 issue were fixed and tests passed on turn 1, subsequent turns would approve without independent test confirmation. That may be acceptable (tests passed on turn 1 counts as verified), but it's a gap to be aware of.

### Finding 6: Conditional Approval Correctly Does NOT Fire (INFORMATIONAL)

`not docker_available` is `False` because Docker IS running. Correct behavior. The failure is a code choice issue, not Docker availability.

## Root Cause Summary

| Question | Answer |
|----------|--------|
| Why does psycopg2 import fail? | Player chose psycopg2 (sync adapter) for an asyncpg stack. Not a bootstrap gap. |
| Why does psycopg2 get classified as infrastructure? | `_KNOWN_SERVICE_CLIENT_LIBS` includes `psycopg2` unconditionally. Classification has no project-stack awareness. |
| Why does criteria verification fail with 0/6 every turn? | Player doesn't write `completion_promises` on iterative turns. Each turn's `task_work_results.json` starts fresh, discarding prior enrichment. Synthetic promises don't match behavioural criteria. |
| Why did TASK-DB-001 pass on turn 2 but TASK-DB-003 never does? | DB-001 Player wrote `completion_promises` on turn 2. DB-003 Player didn't on any iterative turn. |
| Why are independent tests skipped on turns 2-4? | `files_created` on iterative turns doesn't include test files. Fallback glob doesn't match by name. |
| Was the work actually done? | Yes. Player_turn_1.json had all 6 promises complete. The orchestration couldn't carry that evidence forward. |

## Recommendations

### R1: Fix psycopg2 misclassification — context-aware library failure detection (HIGH — Priority 1)

**Problem**: `psycopg2` classified as infrastructure regardless of project stack. Feedback tells Player to use mocks; real problem is wrong import.

**Option A — Consult bootstrap deps** (Recommended): In `_classify_test_failure`, cross-reference the missing module against the bootstrap dependency list. If the missing module is NOT in the task's `requires_infrastructure` or bootstrap packages, classify as `("code", "high")` with specific feedback: "ModuleNotFoundError for {module} — this module is not in your project's dependencies. If you're using asyncpg, remove psycopg2 imports."

**Option B — Remove psycopg2 from _KNOWN_SERVICE_CLIENT_LIBS**: `psycopg2` is ambiguous — it could be infrastructure or code error. `asyncpg` and connection errors are unambiguous infrastructure. Removing `psycopg2` causes it to fall through to `_INFRA_AMBIGUOUS` (ModuleNotFoundError) → `("infrastructure", "ambiguous")` — which gives less certain feedback and doesn't trigger conditional approval.

**Option C — Stack-aware classification**: Pass task's declared stack/framework to the classifier. If stack is asyncpg, treat `psycopg2` as `("code", "high")`.

**Recommended**: Option A is most precise; Option B is a safe, minimal-change improvement.

### R2: Add cross-turn criteria memory to autobuild orchestrator (CRITICAL — Priority 1)

**Problem**: Each turn starts fresh. Criteria verified by strong evidence in turn N are not preserved when turn N+1's Player omits completion_promises.

**Option A — Persist verified criteria in autobuild state** (Recommended):
When Coach approves individual criteria in turn N (even if overall decision is feedback due to other issues), mark those criteria as `verified` in the orchestrator's per-task state. In subsequent turns, pass the already-verified set to Coach so it only needs to verify the remaining unmet criteria.

```python
# In autobuild.py: accumulate per-turn verified criteria
if turn_result.decision == "feedback":
    # Some criteria may be verified even when decision is feedback
    for criterion_id, result in turn_result.criteria_results.items():
        if result.verified:
            self._verified_criteria.add(criterion_id)

# When building Coach context for next turn:
coach_context["previously_verified_criteria"] = list(self._verified_criteria)
```

**Option B — Read previous player report when current turn has no promises** (Faster to implement):
In `_load_completion_promises()`, when `task_work_results` has no promises, fall back to reading the most recent existing `player_turn_N.json` for N < current turn:

```python
for prev_turn in range(turn - 1, 0, -1):
    prev_path = self.worktree_path / f"player_turn_{prev_turn}.json"
    if prev_path.exists():
        agent_written = json.loads(prev_path.read_text())
        promises = agent_written.get("completion_promises", [])
        if promises:
            logger.info(f"Recovered completion_promises from player_turn_{prev_turn}.json")
            return promises
```

**Option C — Require Player to explicitly confirm criteria in turn reply**: When Coach gives criteria feedback, include in the prompt: "In your task_work_results.json, you MUST include a `completion_promises` section listing each acceptance criterion and whether it is met." This makes the Player responsible for re-confirming on every turn.

**Recommended**: Option A (orchestrator-level memory) is architecturally correct. Option B is a low-risk quick fix. Do B now, A as the proper design fix.

### R3: Fix test file detection across iterative turns (MODERATE — Priority 2)

**Problem**: `_detect_tests_from_results` only detects test files created/modified in the current turn.

**Fix**: Add accumulated test file tracking in autobuild orchestrator state. After turn 1 detects `tests/users/test_users.py`, store it. On subsequent turns, use the accumulated set as the default test target if no new test files are found.

Alternatively: the cumulative git diff fallback should already handle this — investigate why `_find_first_checkpoint_parent()` doesn't find DB-003's turn 1 test file in a shared worktree.

### R4: Classify psycopg2 import error with specific feedback in Coach output (LOW — Priority 3)

**Problem**: Even with R1 fixing the classification, the Coach's feedback message should be specific about what the Player did wrong and how to fix it.

**Fix**: Add a specific feedback path: when `ModuleNotFoundError: No module named 'psycopg2'` appears in test output and the project uses asyncpg (detectable from bootstrap deps or task metadata), generate Coach feedback: "Your test code imports `psycopg2` — remove this import. This is an asyncpg project. Use asyncpg-compatible patterns throughout."

## Decision Matrix

| Recommendation | Impact | Effort | Risk | Priority |
|----------------|--------|--------|------|----------|
| R1: Fix psycopg2 classification (Option B) | High | Trivial (remove 1 entry) | None | 1 |
| R1: Fix psycopg2 classification (Option A) | High | Medium (bootstrap-aware lookup) | Low | 1 |
| R2 Option B: Read prev player report | High (breaks stall) | Low (~15 lines) | Low | 1 |
| R2 Option A: Orchestrator criteria memory | Very high (structural fix) | Medium | Medium | 1 |
| R3: Accumulated test file tracking | Medium | Medium | Low | 2 |
| R4: Specific psycopg2 feedback message | Low | Low | None | 3 |

## Architecture Score

| Principle | Score | Notes |
|-----------|-------|-------|
| SOLID - SRP | 6/10 | Coach validates, classifies failures, manages Docker lifecycle, AND does criteria verification — too many responsibilities. Classification context-blindness is a consequence |
| SOLID - OCP | 6/10 | `_KNOWN_SERVICE_CLIENT_LIBS` list requires modification to add context-awareness. Not extensible without code change |
| DRY | 6/10 | Completion promises recovery logic duplicated between agent_invoker and coach_validator. Per-turn fresh start means turn N's enrichment work is discarded on turn N+1 |
| YAGNI | 8/10 | Four test file detection fallbacks is over-engineered; the simplest fix (accumulate test files across turns) would be simpler |
| **Overall** | **65/100** | Architecture is structurally sound for single-turn validation. The gap is cross-turn state: the system has no resilience when iterative Player turns produce code-only output without structured self-reporting |

## C4 Sequence: What Actually Happened

```
TASK-DB-003 Turn 1:
  Player → writes task_work_results.json (no completion_promises)
  Player → writes player_turn_1.json (WITH 6 completion_promises ✓)
  agent_invoker → recovers 6 promises → enriches task_work_results.json
  Coach → reads task_work_results.json (has 6 promises!) → runs tests
  Tests → psycopg2 import → classified as ("infrastructure", "high") ← WRONG
  Coach → gives infrastructure feedback (not code feedback) ← WRONG SIGNAL
  Criteria → 6 pending (not 6 rejected — infra path bypasses criteria check)

TASK-DB-003 Turn 2:
  Player → overwrites task_work_results.json (FRESH, no promises) ← prior enrichment LOST
  Player → does NOT write player_turn_2.json
  agent_invoker → no player report to recover from
  agent_invoker → generates synthetic promises (file-existence based) → too weak
  Coach → reads task_work_results.json → completion_promises: synthetic/weak
  Tests → no test files found (files_created has no test files) → SKIPPED
  Criteria → synthetic promises don't match behavioural criteria → 0/6 rejected

TASK-DB-003 Turns 3-4:
  [same as Turn 2 — identical signal]

Stall detector: 3 consecutive identical feedbacks, 0 criteria progress → UNRECOVERABLE_STALL

The Player's turn-1 work (complete and correct) was never recognised.
```

## Appendix

### Key Evidence Lines

| Line | Event |
|------|-------|
| 427-428 | agent_invoker: "Recovered 6 completion_promises/requirements_addressed" turn 1 |
| 439 | R7 diagnostic: sys.executable=/usr/local/bin/python3 |
| 443 | R5 Option B: infra-pinned subprocess |
| 444 | Tests failed in 0.7s (sqlalchemy imports OK; psycopg2 fails) |
| 447 | R6: conditional_approval check at logger.info |
| 455 | Turn 1 criteria: `0 verified, 0 rejected, 6 pending` (infra path, criteria not evaluated) |
| 504 | Turn 2: No task-specific tests found — skipped |
| 513 | Turn 2: `requirements_met: []` |
| 526-527 | Turn 2: "Not found in Player requirements_met" |
| 670 | Stall: identical feedback (sig=4b645870) for 3 turns |

### Key Source Locations

| File | Role |
|------|------|
| [coach_validator.py:2334-2340](guardkit/orchestrator/quality_gates/coach_validator.py#L2334-L2340) | psycopg2 promoted to infrastructure/high |
| [coach_validator.py:400-410](guardkit/orchestrator/quality_gates/coach_validator.py#L400-L410) | `_KNOWN_SERVICE_CLIENT_LIBS` list |
| [coach_validator.py:1487-1514](guardkit/orchestrator/quality_gates/coach_validator.py#L1487-L1514) | Criteria matching strategy selection |
| [coach_validator.py:1537-1580](guardkit/orchestrator/quality_gates/coach_validator.py#L1537-L1580) | `_load_completion_promises` — no cross-turn fallback |
| [agent_invoker.py:1616-1675](guardkit/orchestrator/agent_invoker.py#L1616-L1675) | Completion promises recovery pipeline |
| [agent_invoker.py:1683-1719](guardkit/orchestrator/agent_invoker.py#L1683-L1719) | task_work_results.json enrichment write-back |
