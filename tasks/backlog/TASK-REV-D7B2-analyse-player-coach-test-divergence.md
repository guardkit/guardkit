---
id: TASK-REV-D7B2
title: Analyse Player/Coach test result divergence causing infinite loop
status: completed
created: 2026-02-16T00:00:00Z
updated: 2026-02-17T00:00:00Z
priority: high
tags: [autobuild, player-coach, test-divergence, infinite-loop, review]
task_type: review
complexity: 6
test_results:
  status: pending
  coverage: null
  last_run: null
review_results:
  mode: architectural
  depth: standard
  score: 35
  findings_count: 5
  recommendations_count: 5
  report_path: .claude/reviews/TASK-REV-D7B2-review-report.md
  decision: implement
  implementation_feature: FEAT-27F2
  implementation_tasks: [TASK-PCTD-5208, TASK-PCTD-9BEB, TASK-PCTD-3182]
---

# Task: Analyse Player/Coach test result divergence causing infinite loop

## Description

Investigate and resolve the Player/Coach test result divergence observed during FEAT-BA28 (PostgreSQL Database Integration) TASK-DB-003. The Player consistently reports tests passing (e.g., "54 tests pass, 100% coverage") while the Coach's independent `pytest` verification fails every turn. This creates an infinite loop where:

1. Player implements + claims tests pass
2. Coach runs `pytest tests/users/test_users.py -v --tb=short` independently
3. Tests fail in 1.7-1.9 seconds
4. Feedback relayed to Player: "Independent test verification failed: FAILED tests/users/test_users.py::Test..."
5. Player "fixes" the tests, claims they pass again
6. Repeat for 18 turns until timeout at 45m 58s

This is a **different problem class** from the test detection stall (TASK-REV-F3BE/FEAT-ABF). Test detection is now working correctly (via cumulative git diff and completion_promises fallbacks). The issue is that the tests **genuinely fail** when run independently by the Coach.

## Context

### Related Work
- **TASK-REV-F3BE**: Previous review that identified and fixed test detection stalls
- **FEAT-ABF**: Implementation tasks (ABF-001 through ABF-004) that fixed test detection
- **FEAT-BA28**: The PostgreSQL Database Integration feature that exhibits this issue
- **db_timeout.md**: Full log of the failing run (18 turns, 45m 58s timeout)

### Successful Tasks in Same Run
- TASK-DB-001 (scaffolding): SUCCESS in 1 turn - tests not required
- TASK-DB-002 (scaffolding): SUCCESS in 2 turns - tests not required

### Failed Task
- TASK-DB-003 (feature): 18 turns, tests fail every Coach verification, times out

### Key Evidence from Logs

**Turn 1 (line 348):** Player reports "11 files created, 3 modified, 1 tests (failing)"
- Even Player acknowledges tests failing on turn 1

**Turn 1 Coach (line 357):** `pytest /Users/.../tests/users/test_users.py tests/users/test_users.py -v --tb=short`
- Note: **duplicate paths** — one absolute, one relative (potential deduplication bug)
- Tests fail in 3.1s

**Turn 2 (line 476):** Player reports "2 files created, 6 modified, 1 tests (passing)"
- Player now claims tests pass

**Turn 2 Coach (line 484):** Quality gates fail: `coverage_met=False`
- Tests not re-run because gates already failed

**Turn 3+ Coach:** Tests consistently fail via cumulative diff fallback:
- `pytest tests/users/test_users.py -v --tb=short` — fails in 1.7s
- Later turns: `pytest tests/core/test_config.py tests/test_foundation.py tests/users/test_users.py -v --tb=short` — fails in 1.9s

**Feedback sent to Player:** "Independent test verification failed: FAILED tests/users/test_users.py::Test..."
- Truncated — Player doesn't see actual error message (import error? DB connection? assertion failure?)

## Acceptance Criteria

- [ ] Root cause of why tests fail when Coach runs `pytest` independently
- [ ] Identify whether the failure is: import error, missing DB connection, missing conftest/fixtures, PYTHONPATH issue, or actual assertion failure
- [ ] Assess whether the Player is hallucinating test results or running tests in a different environment
- [ ] Review the Coach's `run_independent_tests()` method for environment parity with Player
- [ ] Investigate the duplicate path bug (absolute + relative) in `_detect_tests_from_results`
- [ ] Evaluate whether Coach feedback is actionable (truncated "FAILED tests/...::Test..." is not helpful)
- [ ] Assess the stall detection gap — 18 turns of identical feedback should trigger stall detection much earlier
- [ ] Recommendations for fixes (ordered by impact and effort)

## Key Files to Review

### Primary (Coach independent test execution)
- `guardkit/orchestrator/quality_gates/coach_validator.py:828-914` — `run_independent_tests()` method
- `guardkit/orchestrator/quality_gates/coach_validator.py:1602-1731` — `_detect_test_command()` pipeline
- `guardkit/orchestrator/quality_gates/coach_validator.py:1755-1800` — `_detect_tests_from_results()` (duplicate path bug)
- `guardkit/orchestrator/quality_gates/coach_validator.py:1802-1842` — `_summarize_test_output()` (truncation)

### Secondary (Player test execution + feedback relay)
- `guardkit/orchestrator/agent_invoker.py` — Player invocation and test results extraction
- `guardkit/orchestrator/autobuild.py` — Stall detection logic (why 18 turns?)
- `guardkit/orchestrator/quality_gates/coach_validator.py:545-560` — Feedback construction for test failures

### Evidence
- `docs/reviews/autobuild-fixes/db_timeout.md` — Full failure log (18 turns)
- `docs/reviews/autobuild-fixes/db_stalled.md` — Previous stall for comparison
- `docs/reviews/autobuild-fixes/fast_api_summaries.md` — Successful baselines

## Review Focus Areas

### 1. Why do tests fail independently?
The tests require a PostgreSQL database (this is TASK-DB-003: User model schemas and CRUD). The Player likely:
- Runs tests with mocked DB fixtures, or
- Has a `conftest.py` that sets up test DB, or
- Simply hallucinates test results

The Coach runs `pytest` via `subprocess.run(test_cmd, shell=True, cwd=worktree_path)` with no environment setup. If the tests need:
- A running PostgreSQL instance
- Specific environment variables (DATABASE_URL, etc.)
- A conftest.py with async fixtures
- Docker compose services running

...then they'll always fail independently.

### 2. Duplicate path bug in test detection
Line 357 shows: `pytest /absolute/path/tests/users/test_users.py tests/users/test_users.py`

The `files_created`/`files_modified` lists likely contain both absolute and relative paths for the same file. The deduplication at line 1793 uses `set()` on strings, which doesn't normalize paths. This causes pytest to collect the same file twice.

### 3. Feedback truncation
The feedback "FAILED tests/users/test_users.py::Test..." is useless. The Player doesn't know:
- What the actual error is (ImportError? ConnectionRefused? AssertionError?)
- What the full pytest output shows
- Whether it's an environment issue or a code issue

The `_summarize_test_output()` method needs to relay actionable information.

### 4. Stall detection gap
The stall detector uses MD5 hash of feedback text to detect identical feedback. With 18 turns of "Independent test verification failed: FAILED tests/users/test_users.py::Test...", the stall detector should fire after 3-5 turns. Either:
- The feedback text varies slightly between turns (defeating MD5 dedup)
- The stall detector isn't checking this feedback path
- The extended threshold is too generous

### 5. Environment parity
The Player runs tests within the Claude Agent SDK subprocess. The Coach runs them via `subprocess.run(test_cmd, shell=True)`. Key differences:
- PYTHONPATH
- Virtual environment activation
- Environment variables
- Working directory (both use worktree, but PATH may differ)
- Docker/service dependencies

## Implementation Notes

Review task — analysis only, primary goal is to identify the root cause and recommend targeted fixes. Expected recommendations may include:
1. Include full test output (or first N lines of stderr) in Coach feedback
2. Fix duplicate path deduplication in `_detect_tests_from_results`
3. Adjust stall detection to catch test-failure loops earlier
4. Consider environment propagation from Player to Coach (or skip independent verification for integration/DB tests)

## Test Execution Log
[Automatically populated by /task-work]
