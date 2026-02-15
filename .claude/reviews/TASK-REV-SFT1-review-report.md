# Review Report: TASK-REV-SFT1 (Revised)

## Executive Summary

The FEAT-AC1A autobuild failed due to **six compounding root causes** that turned a complexity-2 scaffolding task into an unrecoverable 45-minute stall. Through deep code tracing, I've confirmed that the failure chain was: (1) the task-work delegation path consumed most of the 1800s SDK timeout on session preamble, leaving insufficient time for actual work, (2) when the SDK timed out, the synthetic recovery report lacked `completion_promises` so the Coach could never verify criteria, (3) the Coach's `_extract_feedback` method surfaced only the generic issue description instead of the detailed `rationale` containing specific missing criteria, (4) the test detection ran `pytest --tb=no -q` across the entire worktree (not scoped to `tests/seam/`) so pre-existing test failures masked the Player's new tests, (5) the feature orchestrator's `asyncio.wait_for(asyncio.to_thread(...))` pattern cannot terminate threads, and (6) Graphiti connection loss added latency to every turn from Turn 4 onwards.

**Result**: 1/11 tasks completed, 1 failed (UNRECOVERABLE_STALL after 8 turns), 9 never started.

---

## Review Details

- **Mode**: Decision Analysis (Root Cause) — Revised with deep code tracing
- **Depth**: Comprehensive
- **Task**: TASK-REV-SFT1 — Analyse seam-first testing autobuild stall
- **Feature**: FEAT-AC1A — Seam-First Testing Strategy
- **Source**: `docs/reviews/seam_first_testing/stall_1.md` (2271 lines)
- **Code Files Traced**: `agent_invoker.py`, `autobuild.py`, `feature_orchestrator.py`, `coach_validator.py`, `coach_verification.py`, `state_detection.py`

---

## Architecture Context: Player-Coach Loop

Before diving into findings, here is how the Player-Coach architecture works end-to-end, and where each failure occurred:

```
Feature Orchestrator
  └── _execute_wave_parallel()
        └── asyncio.gather(*[asyncio.wait_for(asyncio.to_thread(_execute_task), timeout=2400)])
              └── _execute_task() → AutoBuildOrchestrator.run()
                    └── _loop_phase() — for turn in range(1, max_turns+1):
                          │
                          ├── Player Phase:
                          │     invoke_player() → routes by implementation_mode
                          │       ├── "direct" → _invoke_player_direct() [SDK session, no /task-work]
                          │       └── "task-work" → _invoke_task_work_implement() ← TASK-SFT-001 path
                          │             └── asyncio.timeout(sdk_timeout_seconds=1800)
                          │                   └── async for msg in query("/task-work TASK-XXX --implement-only --mode=tdd")
                          │                         └── Full Claude Code session: CLAUDE.md → Skill → Phases 3-5
                          │
                          │     If Player fails → _attempt_state_recovery()
                          │       └── MultiLayeredStateTracker.capture_state()
                          │             ├── detect_git_changes() → files modified/created
                          │             └── detect_test_results() → CoachVerifier._run_tests()
                          │                   └── subprocess.run(["pytest", "--tb=no", "-q"])  ← ENTIRE worktree
                          │
                          ├── Coach Phase:
                          │     invoke_coach() → CoachValidator.validate()
                          │       ├── 1. read_quality_gate_results() → task_work_results.json
                          │       ├── 2. verify_quality_gates() → profile-based gate checks
                          │       ├── 3. run_independent_tests() → SKIPPED for scaffolding
                          │       ├── 4. validate_requirements() → match acceptance criteria
                          │       │     ├── Strategy 1: completion_promises (ID-based) ← PREFERRED
                          │       │     └── Strategy 2: requirements_met (text-based) ← FALLBACK
                          │       └── 5. Return approve/feedback decision
                          │
                          ├── _extract_feedback(coach_report)
                          │     └── issues[0].description = "Not all acceptance criteria met" ← GENERIC
                          │         (rationale has specifics but is NOT used when issues exist)
                          │
                          └── Stall Detection:
                                └── _is_feedback_stalled() — MD5(feedback) same for 3 turns + 0 criteria → UNRECOVERABLE_STALL
```

**Key architectural insight**: The Player-Coach loop is designed so that Coach feedback guides the Player on subsequent turns. When this feedback loop breaks (as happened here), the system cannot self-correct and will stall until the `_is_feedback_stalled()` detector triggers.

---

## Findings (Code-Verified)

### Finding 1: Zero-Message SDK Timeouts Caused by Session Preamble Overhead

**Severity**: Critical | **Turns Affected**: 2, 4 | **Code**: `agent_invoker.py:2536`

The `_invoke_task_work_implement()` method wraps the SDK streaming loop in `asyncio.timeout(self.sdk_timeout_seconds)`:

```python
# agent_invoker.py:2536-2538
async with asyncio.timeout(self.sdk_timeout_seconds):
    async with async_heartbeat(task_id, "task-work implementation"):
        async for message in query(prompt=prompt, options=options):
```

The `query()` call launches a Claude Code CLI subprocess (`claude_agent_sdk._internal.transport.subprocess_cli`), which must:
1. Start the Node.js runtime
2. Load CLAUDE.md files (root + `.claude/CLAUDE.md` + rules)
3. Enumerate tools and configure permissions
4. Expand the `/task-work` skill into its full prompt
5. Execute the multi-phase workflow (Phases 3-5)

**On Turns 2 and 4**, the SDK subprocess consumed the entire 1800s without producing a single message to the async iterator. This means the subprocess was alive but the Claude Code session never started yielding `AssistantMessage` objects.

**Confirmed root cause**: The `query()` function yields messages only after the subprocess starts producing tool calls or text blocks. If the session stalls during CLAUDE.md loading, skill expansion, or the initial LLM call, zero messages are produced. The 1800s timeout fires and the Python side gets `asyncio.TimeoutError` with `message_count=0`.

**Why this only affects task-work mode**: Direct mode (`_invoke_player_direct`) uses `_invoke_with_role()` which sends a custom prompt directly — no skill expansion overhead. TASK-SFT-002 used direct mode and completed in one turn.

### Finding 2: Synthetic Recovery Reports Structurally Cannot Satisfy Coach Criteria

**Severity**: Critical | **Turns Affected**: 2, 4, 5 (all timeout turns) | **Code**: `autobuild.py:2114-2151`, `coach_validator.py:1077-1086`

When an SDK timeout fires, `_attempt_state_recovery()` creates a synthetic Player report via `_build_synthetic_report()`:

```python
# autobuild.py:2114-2136
report = {
    "task_id": "",
    "files_modified": work_state.files_modified,
    "files_created": work_state.files_created,
    "requirements_addressed": [],  # Cannot determine from detection
    "requirements_remaining": [],  # Cannot determine from detection
    ...
}
```

This report has **no `completion_promises`** (the preferred matching strategy) and **empty `requirements_addressed`/`requirements_remaining`** lists. The CoachValidator then:

```python
# coach_validator.py:1077-1086
completion_promises = self._load_completion_promises(task_work_results, turn)
if completion_promises:
    return self._match_by_promises(acceptance_criteria, completion_promises)

# Fallback: empty requirements_met → 0/10 verified
requirements_met = task_work_results.get("requirements_met", [])
return self._match_by_text(acceptance_criteria, requirements_met)
```

Since both `completion_promises` and `requirements_met` are empty/missing in the synthetic report, **every criterion is marked "rejected"** regardless of whether files actually exist.

**Architectural implication**: This is by design — the recovery is conservative. But for scaffolding tasks, this creates a dead end because the Coach can never verify criteria from a recovered report. The Player then receives feedback, tries again, potentially times out again, and the cycle repeats.

**Regression risk for any fix**: The `requirements_addressed: []` in synthetic reports is intentional — the system cannot determine from git diffs alone which acceptance criteria are met. Any fix must either (a) add file-existence verification to the Coach, or (b) add structured acceptance criteria checking to the state recovery layer. Option (b) risks coupling state detection to task semantics, which is a larger architectural change.

### Finding 3: Test Detection Runs Across Entire Worktree, Not Scoped to Task

**Severity**: High | **Turns Affected**: All 8 | **Code**: `coach_verification.py:254`, `state_detection.py:359-360`

The test detection during state recovery runs:

```python
# coach_verification.py:254
result = subprocess.run(
    ["pytest", "--tb=no", "-q"],
    cwd=self.worktree_path,  # Entire worktree, not tests/seam/
    ...
)
```

The log consistently shows `Test detection (TASK-SFT-001 turn N): 0 tests, failed`. This happens because:
1. `pytest --tb=no -q` runs ALL tests in the worktree, not just `tests/seam/`
2. If any pre-existing test fails, `returncode != 0` → `passed=False`
3. The `_parse_pytest_count()` likely failed to parse the count from the failing output

**Evidence**: Turn 5's SDK output showed 13 tests in `tests/seam/test_conftest_fixtures.py`, yet state detection found 0 tests. The tests the Player wrote were valid; they were masked by broader test failures.

**Regression risk**: Scoping test detection to task-specific paths requires passing task context (which test directories to check) into `CoachVerifier._run_tests()`. This is a moderate change that touches the test verification interface. Care needed to not break the Coach's independent verification for non-scaffolding tasks.

### Finding 4: Coach Feedback Text Extraction Loses Specificity

**Severity**: High | **Turns Affected**: 1, 3, 6, 7, 8 | **Code**: `coach_validator.py:710-717`, `autobuild.py:3124-3146`

The CoachValidator creates detailed feedback with both `issues` and `rationale`:

```python
# coach_validator.py:710-717
return self._feedback_result(
    issues=[{
        "description": "Not all acceptance criteria met",  # ← Generic
        "missing_criteria": requirements.missing,           # ← Specific (but nested)
    }],
    rationale=f"Missing {len(requirements.missing)} acceptance criteria: {', '.join(requirements.missing)}",
    # ← The rationale has the specific list!
)
```

But `_extract_feedback()` in the autobuild orchestrator extracts only the `description`:

```python
# autobuild.py:3124-3141
issues = coach_report.get("issues", [])
if not issues:
    return coach_report.get("rationale", "No specific feedback provided")
# When issues exist, rationale is NEVER used:
for issue in issues[:3]:
    desc = issue.get("description", "")  # = "Not all acceptance criteria met"
    suggestion = issue.get("suggestion", "")  # = ""
    feedback_lines.append(f"- {desc}")  # Generic line
```

**The `rationale` field is only used when there are no `issues`**. But the Coach always emits at least one issue when criteria aren't met. So the specific `"Missing 10 acceptance criteria: ..."` rationale is discarded, and the Player receives only `"- Not all acceptance criteria met"`.

**Fix safety**: The fix is straightforward — include `missing_criteria` from the issue in the feedback, or prefer `rationale` over issue descriptions. This is a low-regression change because it only affects the text passed to the Player, not the Coach's validation logic itself.

### Finding 5: Feature Orchestrator Thread Cannot Be Cancelled — Confirmed with Code + Log Evidence

**Severity**: High | **Turns Affected**: 4-8 (post-feature-failure) | **Code**: `feature_orchestrator.py:1139-1149`

```python
# feature_orchestrator.py:1139-1143
tasks_to_execute.append(
    asyncio.wait_for(
        asyncio.to_thread(self._execute_task, task, feature, worktree),
        timeout=self.task_timeout,  # 2400s
    )
)
```

**Confirmed by log evidence**:
- **Line 1298-1300**: `RuntimeWarning: The executor did not finishing joining its threads within 300 seconds.` — This is Python's asyncio executor warning when threads survive past event loop shutdown.
- **Line 1302**: `Wave 1 ✗ FAILED: 1 passed, 1 failed` — Feature declares failure
- **Line 1307-1335**: Full `FEATURE RESULT: FAILED` display rendered
- **Line 1336**: `[TASK-SFT-001] task-work implementation in progress... (270s elapsed)` — Turn 4 **continues** in the background thread

The thread ran from Turn 4 through Turn 8, consuming another ~35 minutes of API resources after the feature was already declared failed.

**Why `asyncio.wait_for` doesn't help**: `asyncio.to_thread` submits work to the default `ThreadPoolExecutor`. When `wait_for` times out, it cancels the `asyncio.Future` but has no mechanism to interrupt the thread. The `_loop_phase()` method runs synchronously in the thread with no cancellation check.

**Regression risk for any fix**:
- **Cooperative cancellation** (recommended): Pass a `threading.Event` to `_execute_task`. Check it at the start of each turn in `_loop_phase()`. Low risk — adds one `if cancelled.is_set(): return` check per turn. Must ensure the worktree is left in a clean state (checkpoint before exit).
- **Process-based execution**: Higher risk — would require serializing `AutoBuildOrchestrator` state across process boundaries, changing the Graphiti factory sharing model, and reimplementing progress display IPC.

### Finding 6: Graphiti Connection Loss Added Latency Without Value

**Severity**: Medium | **Turns Affected**: 4-8 | **Code**: `autobuild_context_loader.py`, `graphiti_client.py`

Starting at Turn 4, every Coach validation phase attempted Graphiti context loading, which triggered:
1. OpenAI embedding requests → retried with exponential backoff (`0.45s, 0.85s, 0.39s...`)
2. FalkorDB search queries → `Connection error` (no timeout, just failure)
3. Episode creation → `Connection error`

The Graphiti client gracefully degrades (returns empty context), but each failed retry cycle adds 5-10 seconds per context load. With context loaded for both Player and Coach phases, this added ~20-30 seconds per turn.

**The connection loss appears to be environmental** — FalkorDB at `whitestocks:6379` became unreachable. The initial Graphiti connection at startup was successful (line 60: `Connected to FalkorDB via graphiti-core at whitestocks:6379`), so the failure occurred mid-run.

**Cleanup errors at process end** confirm the connection state:
```
ERROR:asyncio:Task was destroyed but it is pending!
  coro=<FalkorDriver.build_indices_and_constraints()>
RuntimeError: no running event loop
```

This is the Graphiti client trying to build indices during shutdown, finding no event loop. This is a cosmetic issue (cleanup after fatal failure) but indicates the connection was severed.

---

## Causal Chain Diagram

```
TASK-SFT-001 (complexity:2, mode:task-work, development:tdd)
  │
  ├── Turn 1: Player creates 5 files, 0 tests passing
  │     └── Coach: 0/10 criteria ← Synthetic report has no completion_promises
  │           └── Feedback: "Not all acceptance criteria met" ← Generic, no specifics
  │
  ├── Turn 2: SDK TIMEOUT (1800s, 0 messages) ← Session preamble consumed all time
  │     └── Recovery: git_only (5 files, 0 tests) ← pytest runs whole worktree, fails
  │           └── Coach: 0/10 criteria ← Synthetic report, same problem
  │
  ├── Turn 3: Player completes (70 messages, 1 file)
  │     └── Coach: 0/10 criteria ← task_work_results.json lacks completion_promises
  │           └── Feedback: "Not all acceptance criteria met" ← Same generic text
  │
  ├── T+40min: TASK TIMEOUT (2400s) → Feature declares FAILED
  │     └── Thread continues running (cannot be cancelled)
  │
  ├── Turn 4: SDK TIMEOUT (0 messages) + Graphiti connection errors start
  │     └── Recovery → Coach: 0/10 criteria → identical feedback
  │
  ├── Turn 5: SDK TIMEOUT (107 messages, code review 88/100!)
  │     └── Player actually COMPLETED the task (all files verified, 13 tests)
  │     └── But SDK timed out during state transition output
  │     └── Recovery: git_only → 0 tests (whole-worktree pytest masks seam tests)
  │     └── Coach: 0/10 criteria → identical feedback
  │
  ├── Turns 6-8: Identical feedback stall (sig=c1ddd473)
  │
  └── UNRECOVERABLE_STALL detected (3 identical turns, 0% progress)
```

**The most striking observation**: Turn 5 shows the Player **actually completed all acceptance criteria** (code review 88/100, all files verified, 13 tests passing, state transitioning to IN_REVIEW). But the 1800s SDK timeout fired during the final output, so the results were never captured into `task_work_results.json`. The recovery layer found 0 tests (whole-worktree masking), and the Coach rejected everything.

---

## Root Cause Summary

| # | Root Cause | Code Location | Turns | Severity |
|---|-----------|---------------|-------|----------|
| 1 | Session preamble overhead causes zero-message timeouts | `agent_invoker.py:2536` | 2, 4 | Critical |
| 2 | Synthetic recovery reports lack `completion_promises` | `autobuild.py:2114-2136` | 2, 4, 5 | Critical |
| 3 | Test detection unscoped — whole-worktree pytest masks task tests | `coach_verification.py:254` | All | High |
| 4 | `_extract_feedback` discards specific `rationale` when `issues` exist | `autobuild.py:3124-3141` | 1, 3, 6-8 | High |
| 5 | `asyncio.wait_for` + `to_thread` cannot cancel threads | `feature_orchestrator.py:1139` | 4-8 | High |
| 6 | Graphiti connection loss adds retry latency without value | `graphiti_client.py` | 4-8 | Medium |

---

## Recommendations

### Immediate (Re-Run Blockers)

#### R1: Switch TASK-SFT-001 to `implementation_mode: direct` [1 line change]

The task-work delegation path adds session preamble, skill expansion, and multi-phase workflow overhead. Direct mode bypasses all of this. TASK-SFT-002 (direct mode) completed in 1 turn.

```yaml
# tasks/backlog/seam-first-testing/TASK-SFT-001-scaffolding.md
implementation_mode: direct  # was: task-work
```

**Regression risk**: None. This only changes how TASK-SFT-001 is invoked. The direct path uses `_invoke_player_direct()` which sends a custom prompt with full requirements — no phases skipped, just no skill expansion overhead.

#### R2: Verify Graphiti/FalkorDB connectivity before launch

```bash
redis-cli -h whitestocks -p 6379 ping  # Must return PONG
```

Or pass `--no-context` to disable Graphiti entirely for the re-run.

**Regression risk**: None. This is a pre-flight check, not a code change.

### Near-Term (Code Changes — Player-Coach Loop)

#### R3: Include `missing_criteria` in feedback text [Low regression risk]

**File**: `autobuild.py:3124-3146`

The fix: when `issue.get("missing_criteria")` exists, append the specific criteria to the feedback line.

```python
# Current:
feedback_lines.append(f"- {desc}")

# Proposed:
missing = issue.get("missing_criteria", [])
if missing:
    feedback_lines.append(f"- {desc}:")
    for criterion in missing[:5]:
        feedback_lines.append(f"  • {criterion[:100]}")
else:
    feedback_lines.append(f"- {desc}")
```

**Regression risk**: Low. This only changes the text content of feedback passed to the Player. The Coach's validation logic, decision-making, and stall detection are unaffected. The MD5 hash used for stall detection will change (different feedback text per set of missing criteria), which is actually desirable — it means the stall detector will only trigger when the same *specific* criteria are missing for 3 turns, not when different criteria sets happen to produce the same generic message.

**Architectural consideration**: This change improves the Player-Coach feedback loop's information density without altering the control flow. The Coach still makes the same approve/feedback decisions; only the feedback text quality improves.

#### R4: Add `completion_promises` to synthetic recovery reports [Medium regression risk]

**File**: `autobuild.py:2114-2151`

For scaffolding tasks, the state recovery could verify file existence and populate `completion_promises`:

```python
# In _build_synthetic_report(), after detecting files:
if task_type == "scaffolding" and acceptance_criteria:
    promises = self._verify_scaffolding_promises(
        work_state, acceptance_criteria, worktree_path
    )
    report["completion_promises"] = promises
```

**Regression risk**: Medium. This adds task-type-specific logic to the generic state recovery layer, creating coupling between recovery and task semantics. Should be gated behind a `task_type == "scaffolding"` check to avoid affecting other task types. Must handle edge cases (files created but with wrong content, partial implementations).

**Alternative (lower risk)**: Add an optional `_verify_files_exist()` step to the CoachValidator for scaffolding tasks, keeping the recovery layer generic. This keeps the separation of concerns intact — recovery detects what happened, Coach validates what's acceptable.

#### R5: Scope test detection to task-relevant directories [Medium regression risk]

**File**: `coach_verification.py:254`

```python
# Current:
result = subprocess.run(["pytest", "--tb=no", "-q"], cwd=self.worktree_path)

# Proposed: accept optional test_paths parameter
result = subprocess.run(
    ["pytest", "--tb=no", "-q"] + (test_paths or []),
    cwd=self.worktree_path,
)
```

**Regression risk**: Medium. The CoachVerifier is used both by the Coach phase and by state detection. Changing the test scope requires passing task-specific test paths through the call chain. Must ensure that for non-scaffolding tasks, the full-worktree run is preserved (it catches regressions). Could use task frontmatter to specify `test_scope: tests/seam/`.

### Backlog (Larger Architectural Changes)

#### R6: Cooperative thread cancellation in feature orchestrator [Low-Medium regression risk]

**File**: `feature_orchestrator.py:1139`, `autobuild.py:1490`

Pass a `threading.Event` to `_execute_task`, propagate it to `_loop_phase`, and check at the start of each turn:

```python
# In _loop_phase:
for turn in range(start_turn, self.max_turns + 1):
    if self._cancellation_event and self._cancellation_event.is_set():
        logger.info(f"Cancellation requested for {task_id} at turn {turn}")
        return turn_history, "cancelled"
```

**Regression risk**: Low for the check itself. The cancellation event would be set by the feature orchestrator when `asyncio.wait_for` fires. The main risk is ensuring clean worktree state on cancellation (should create a checkpoint before exiting). Also need to handle the case where the SDK subprocess is still running when the thread exits — may need `subprocess.kill()`.

**Architectural consideration**: This is the right pattern for cooperative cancellation in Python threads. It follows the existing stall detection pattern (early loop exit) and reuses the existing return type (`"cancelled"` as a new literal in the decision enum). The `asyncio.to_thread` + `wait_for` pattern stays in place; only the thread's inner loop gains awareness of external cancellation.

#### R7: Add dynamic SDK timeout based on task complexity [Low regression risk]

**File**: `agent_invoker.py:2524`

```python
# Calculate timeout based on complexity and mode
if effective_mode == "tdd":
    effective_timeout = max(self.sdk_timeout_seconds, complexity * 600)
else:
    effective_timeout = self.sdk_timeout_seconds
```

This is a future optimization. For the immediate re-run, using direct mode (R1) eliminates the timeout issue for TASK-SFT-001.

---

## Re-Run Checklist

Before re-running `guardkit autobuild feature FEAT-AC1A`:

1. [ ] Change TASK-SFT-001 to `implementation_mode: direct` (R1)
2. [ ] Verify FalkorDB: `redis-cli -h whitestocks -p 6379 ping` (R2)
3. [ ] Reset feature YAML status: set `status: pending` for FEAT-AC1A and TASK-SFT-001
4. [ ] Clean up worktree: `rm -rf .guardkit/worktrees/FEAT-AC1A`
5. [ ] Consider `--sdk-timeout 2400` for Wave 2 tasks (complexity 4-6, must use task-work)

```bash
guardkit autobuild feature FEAT-AC1A --max-turns 30 --sdk-timeout 2400 --fresh
```

---

## Decision Matrix

| Option | Regression Risk | Effort | Impact | Recommendation |
|--------|----------------|--------|--------|----------------|
| R1: Switch SFT-001 to direct mode | None | 1 line | Eliminates timeout for this task | **Do now** |
| R2: Verify FalkorDB connectivity | None | Pre-flight | Prevents connection errors | **Do now** |
| R3: Include missing_criteria in feedback | Low | 0.5 day | Breaks identical-feedback stalls | **Near-term** |
| R4: Add promises to synthetic recovery | Medium | 1-2 days | Fixes scaffolding criteria matching | **Near-term** |
| R5: Scope test detection to task dirs | Medium | 1 day | Fixes test masking issue | **Near-term** |
| R6: Cooperative thread cancellation | Low-Medium | 2 days | Prevents ghost threads | **Backlog** |
| R7: Dynamic SDK timeout | Low | 0.5 day | Reduces future timeouts | **Backlog** |

---

## Appendix A: Timeline Reconstruction (Corrected)

Timestamps derived from log heartbeat intervals and FEAT-AC1A YAML execution data.

```
09:55:44  Feature orchestration starts
09:55:45  Wave 1 launches: SFT-001 (task-work/tdd) + SFT-002 (direct)
09:56:15  Graphiti context loaded (0 categories for both tasks — DB had no relevant data)
09:58:45  SFT-002 Turn 1: Player completes (2 files, 1 test) — direct mode, ~3 min
09:59:00  SFT-002 Turn 1: Coach approves → COMPLETED
10:00:00  SFT-001 Turn 1: Player completes (5 files, 0 tests) — task-work mode, ~5 min
10:01:00  SFT-001 Turn 1: Coach feedback "Not all AC met" (0/10 verified)
10:03:32  SFT-001 Turn 2: Player starts → 0 messages received for 30 min
10:33:32  SFT-001 Turn 2: SDK TIMEOUT (1800s, 0 messages)
10:33:35  SFT-001 Turn 2: Recovery via git_only (5 files, 0 tests)
10:33:59  SFT-001 Turn 2: Coach feedback "timeout message"
10:34:00  SFT-001 Turn 3: Player starts (completes with 70 messages, ~2 min)
10:35:45  SFT-001 Turn 3: Coach feedback "Not all AC met" (0/10)
10:35:45  TASK TIMEOUT (2400s) fires → Feature declares FAILED [Line 1302]
           FEATURE RESULT: FAILED rendered [Line 1308]
           Thread continues... [Line 1336+]
10:36:25  SFT-001 Turn 4: Player starts → 0 messages, Graphiti connection errors begin
11:06:25  SFT-001 Turn 4: SDK TIMEOUT (1800s, 0 messages)
11:06:45  SFT-001 Turn 5: Player starts → 107 messages (PRODUCTIVE SESSION)
           Created: tests/seam/__init__.py, conftest.py, test_conftest_fixtures.py (13 tests)
           Code review: 88/100
           State transition: DESIGN_APPROVED → IN_REVIEW
11:36:45  SFT-001 Turn 5: SDK TIMEOUT (just before completion output captured)
11:37:04  SFT-001 Turn 6: Quick turn, "Not all AC met" (0/10)
11:38:44  SFT-001 Turn 7: Quick turn, "Not all AC met" (0/10)
11:41:09  SFT-001 Turn 8: Quick turn, "Not all AC met" (0/10)
11:43:35  UNRECOVERABLE_STALL (3 identical feedback turns, sig=c1ddd473)
11:43:40  Asyncio cleanup errors, process ends
```

**Total wall time**: ~108 minutes (09:55 - 11:43)
**Time after feature declared FAILED**: ~68 minutes of wasted execution

### Appendix B: Key Log Lines

| Line | Event | Significance |
|------|-------|-------------|
| 4 | `task_timeout=2400s` | Feature-level timeout per task |
| 67 | Wave 1 starts | SFT-001 + SFT-002 parallel |
| 449 | `Executing via SDK: /task-work TASK-SFT-001 --implement-only --mode=tdd` | Task-work delegation path confirmed |
| 456 | `Max turns: 50`, `SDK timeout: 1800s` | Inner SDK config |
| 671 | Turn 1: `5 files created, 1 modified, 0 tests (failing)` | Files created but tests fail |
| 884 | `Criteria Progress (Turn 1): 0/10 verified (0%)` | Criteria matching broken from start |
| 973-974 | Turn 2: `SDK TIMEOUT`, `Messages processed: 0` | Zero-message timeout |
| 984 | `State from detection (git_only): 2 modified, 3 created, 0 tests` | Recovery finds no tests |
| 1192 | Turn 3: `SDK completed: turns=27` | Session productive but Coach still rejects |
| 1298-1300 | `executor did not finishing joining its threads within 300 seconds` | Thread cancellation failure confirmed |
| 1302 | `Wave 1 ✗ FAILED` | Feature failure declared |
| 1336 | `task-work implementation in progress... (270s elapsed)` | Turn 4 continues post-failure |
| 1387-1388 | Turn 4: `SDK TIMEOUT`, `Messages processed: 0` | Second zero-message timeout |
| 1407 | `Search request failed: Connection error` | Graphiti connection lost |
| 1656-1675 | Turn 5: 107 messages, code review 88/100, all files verified | **Near-success** |
| 1685 | `Test detection (TASK-SFT-001 turn 5): 0 tests, failed` | Whole-worktree pytest masks seam tests |
| 2204 | `Feedback stall: identical feedback (sig=c1ddd473) for 3 turns` | Stall detected |
| 2237 | `Status: UNRECOVERABLE_STALL` | Final outcome |

### Appendix C: Regression Risk Assessment for Recommended Changes

| Change | Files Modified | Interfaces Changed | Test Impact | Existing Tests |
|--------|---------------|-------------------|-------------|---------------|
| R1 (direct mode) | 1 task YAML | None | None | N/A |
| R3 (feedback text) | `autobuild.py` | `_extract_feedback()` return value | Feedback text changes | Update feedback assertion tests |
| R4 (recovery promises) | `autobuild.py` | `_build_synthetic_report()` adds field | Coach may now approve recovered turns | Add tests for scaffolding recovery |
| R5 (scoped tests) | `coach_verification.py` | `_run_tests()` signature (optional param) | Test scope changes | Ensure full-worktree default preserved |
| R6 (cancellation) | `feature_orchestrator.py`, `autobuild.py` | New `cancellation_event` param | New exit path | Add cancelled state handling tests |

All changes should be individually testable and can be deployed independently. R3 and R4 combined address the criteria matching loop; R5 addresses test detection; R6 addresses the thread lifecycle. None require changes to the Coach's core validation logic (`validate()` method), preserving the existing quality gate architecture.
