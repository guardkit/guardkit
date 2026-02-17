# Review Report: TASK-REV-D7B2 (Revised — Comprehensive)

## Executive Summary

The Player/Coach test divergence that caused an 18-turn infinite loop in TASK-DB-003 (FEAT-BA28) has **5 root causes** operating as a failure cascade. Each cause has been traced to exact code locations with definitive evidence from the execution log. The primary cause is an **environment parity gap** between the Player (SDK Bash tool with full shell profile) and the Coach (`subprocess.run()` with bare Python environment). This is compounded by four amplifying factors that prevented the system from self-correcting: non-actionable feedback, duplicate test paths, variable-output-defeating stall detection, and quality gate short-circuiting.

The task was ultimately terminated by **cooperative cancellation** (task timeout after 2400s/40min at Turn 18), NOT by stall detection — which never fired despite 15+ semantically-identical feedback turns.

## Review Details
- **Mode**: Architectural Review (Revised — Comprehensive depth)
- **Task ID**: TASK-REV-D7B2
- **Date**: 2026-02-16
- **Scope**: `coach_validator.py`, `autobuild.py`, `agent_invoker.py`, `db_timeout.md`

---

## Sequence Diagram: Normal Flow (Successful Task)

```
┌─────────┐     ┌──────────────┐     ┌────────────────┐     ┌──────────────┐
│AutoBuild│     │AgentInvoker  │     │Claude Agent SDK │     │CoachValidator│
│Orchestr.│     │(Player)      │     │(Bash tool)      │     │              │
└────┬────┘     └──────┬───────┘     └───────┬─────────┘     └──────┬───────┘
     │  invoke_player  │                     │                      │
     │────────────────>│  SDK query()        │                      │
     │                 │────────────────────>│                      │
     │                 │                     │ Bash: pytest tests/   │
     │                 │                     │──────────────────┐   │
     │                 │                     │ (user's shell    │   │
     │                 │                     │  profile, venv,  │   │
     │                 │                     │  PATH, env vars) │   │
     │                 │                     │<─────────────────┘   │
     │                 │  task_work_results  │                      │
     │                 │<────────────────────│                      │
     │  player_result  │                     │                      │
     │<────────────────│                     │                      │
     │                                                              │
     │  validate(task_id, turn, task)                               │
     │─────────────────────────────────────────────────────────────>│
     │                                                              │
     │                                          subprocess.run()    │
     │                                          ┌───────────────────│
     │                                          │ (bare Python env, │
     │                                          │  no shell profile,│
     │                                          │  no venv, no DB)  │
     │                                          └──────────────────>│
     │                                                              │
     │  CoachValidationResult(decision="approve")                   │
     │<─────────────────────────────────────────────────────────────│
     │                                                              │
     ▼ SUCCESS                                                      ▼
```

## Sequence Diagram: TASK-DB-003 Failure Flow (18-Turn Loop)

```
┌─────────┐    ┌──────────────┐    ┌────────────────┐    ┌──────────────┐    ┌──────────────┐
│AutoBuild│    │AgentInvoker  │    │Claude Agent SDK │    │CoachValidator│    │StallDetector │
│Orchestr.│    │(Player)      │    │(Bash tool)      │    │              │    │(_is_feedback │
│         │    │              │    │                 │    │              │    │  _stalled)   │
└────┬────┘    └──────┬───────┘    └───────┬─────────┘    └──────┬───────┘    └──────┬───────┘
     │                │                    │                     │                   │
     │ ═══════════════════════ TURN 1 ═══════════════════════════│                   │
     │                │                    │                     │                   │
     │ invoke_player  │                    │                     │                   │
     │───────────────>│ SDK query()        │                     │                   │
     │                │───────────────────>│ writes test files,  │                   │
     │                │                    │ reports "tests pass" │                   │
     │                │                    │ (may hallucinate)    │                   │
     │<───────────────│                    │                     │                   │
     │                │                    │                     │                   │
     │ validate()     │                    │                     │                   │
     │───────────────────────────────────────────────────────────>│                   │
     │                │                    │ _detect_tests_      │                   │
     │                │                    │ from_results()      │                   │
     │                │                    │ BUG: abs+rel paths  │                   │
     │                │                    │ → 2 unique (should  │                   │
     │                │                    │   be 1)             │                   │
     │                │                    │                     │                   │
     │                │                    │ subprocess.run(     │                   │
     │                │                    │   "pytest /abs/path │                   │
     │                │                    │    tests/rel/path", │                   │
     │                │                    │   shell=True,       │                   │
     │                │                    │   cwd=worktree)     │                   │
     │                │                    │                     │                   │
     │                │                    │ FAILS in 3.1s       │                   │
     │                │                    │ (no DB, no venv)    │                   │
     │                │                    │                     │                   │
     │                │                    │ _summarize_test_    │                   │
     │                │                    │ output():           │                   │
     │                │                    │ Returns last 3      │                   │
     │                │                    │ keyword lines       │                   │
     │                │                    │ (truncated, no      │                   │
     │                │                    │  error details)     │                   │
     │                │                    │                     │                   │
     │ feedback="- Independent test..."    │                     │                   │
     │<──────────────────────────────────────────────────────────│                   │
     │                │                    │                     │                   │
     │ _is_feedback_stalled(feedback, 0)   │                     │                   │
     │──────────────────────────────────────────────────────────────────────────────>│
     │                │                    │                     │ history=[(sig1,0)]│
     │                │                    │                     │ len < 3, skip     │
     │<─────────────────────────────────────────────────────────────────────────────│
     │                │                    │                     │                   │
     │ ═══════════════════════ TURN 2 ═══════════════════════════│                   │
     │                │                    │                     │                   │
     │ validate() → quality gates check    │                     │                   │
     │───────────────────────────────────────────────────────────>│                   │
     │                │                    │ coverage_met=False   │                   │
     │                │                    │ SHORT-CIRCUIT:       │                   │
     │                │                    │ returns BEFORE       │                   │
     │                │                    │ running independent  │                   │
     │                │                    │ tests                │                   │
     │                │                    │                     │                   │
     │ feedback="- Coverage threshold not met"                   │                   │
     │<──────────────────────────────────────────────────────────│                   │
     │                │                    │                     │                   │
     │ _is_feedback_stalled(feedback, 0)   │                     │                   │
     │──────────────────────────────────────────────────────────────────────────────>│
     │                │                    │                     │ history=[(sig1,0),│
     │                │                    │                     │  (sig2,0)]        │
     │                │                    │                     │ len < 3, skip     │
     │<─────────────────────────────────────────────────────────────────────────────│
     │                │                    │                     │                   │
     │ ═══════════════════ TURNS 3-6 ════════════════════════════│                   │
     │ (perspective reset at 3 and 5 — clears previous_feedback  │                   │
     │  but does NOT clear _feedback_history)                    │                   │
     │                │                    │                     │                   │
     │ validate() → gates pass → run_independent_tests()         │                   │
     │───────────────────────────────────────────────────────────>│                   │
     │                │                    │ cumulative diff      │                   │
     │                │                    │ finds test_users.py  │                   │
     │                │                    │ FAILS in 1.7s        │                   │
     │                │                    │                     │                   │
     │                │                    │ _summarize output:   │                   │
     │                │                    │ DIFFERENT each turn  │                   │
     │                │                    │ (Player rewrites     │                   │
     │                │                    │  test classes, so    │                   │
     │                │                    │  pytest output has   │                   │
     │                │                    │  different test      │                   │
     │                │                    │  names/tracebacks)   │                   │
     │                │                    │                     │                   │
     │ feedback="- Independent test...\n  {VARIABLE output}"     │                   │
     │<──────────────────────────────────────────────────────────│                   │
     │                │                    │                     │                   │
     │ _is_feedback_stalled(feedback, 0)   │                     │                   │
     │──────────────────────────────────────────────────────────────────────────────>│
     │                │                    │                     │ MD5 of full 500-  │
     │                │                    │                     │ char feedback text │
     │                │                    │                     │ DIFFERS each turn  │
     │                │                    │                     │ due to variable    │
     │                │                    │                     │ test output        │
     │                │                    │                     │                   │
     │                │                    │                     │ sigs={sig_a,sig_b} │
     │                │                    │                     │ len(sigs) != 1     │
     │                │                    │                     │ → return False     │
     │<─────────────────────────────────────────────────────────────────────────────│
     │                │                    │                     │                   │
     │ ═══════════ TURN 7 (different test files detected) ═══════│                   │
     │                │                    │                     │                   │
     │ validate() → _detect_tests_from_results()                 │                   │
     │───────────────────────────────────────────────────────────>│                   │
     │                │                    │ 4 files detected:    │                   │
     │                │                    │ /abs/test_config.py  │                   │
     │                │                    │ /abs/test_foundation │                   │
     │                │                    │ tests/core/test_cfg  │                   │
     │                │                    │ tests/test_found.    │                   │
     │                │                    │ (test_users.py NOT   │                   │
     │                │                    │  in files this turn) │                   │
     │                │                    │                     │                   │
     │ feedback="- Independent...\n  FAILED tests/test_foundation.py::TestM..."     │
     │<──────────────────────────────────────────────────────────│                   │
     │                │                    │                     │                   │
     │ _is_feedback_stalled → DIFFERENT test file → streak RESET │                   │
     │                │                    │                     │                   │
     │ ═══════════ TURNS 8-17 (repeat of 3-6 pattern) ══════════│                   │
     │                │                    │                     │                   │
     │ Same cycle: variable test output defeats MD5 matching     │                   │
     │ 0/6 criteria passing every turn                           │                   │
     │ Stall detection NEVER fires                               │                   │
     │                │                    │                     │                   │
     │ ═══════════ TURN 18 ═════════════════════════════════════ │                   │
     │                │                    │                     │                   │
     │ FeatureOrchestrator timeout (2400s) │                     │                   │
     │ → cooperative cancellation event set│                     │                   │
     │ → Player completes but Coach never runs                   │                   │
     │ → decision: "cancelled" (NOT "unrecoverable_stall")       │                   │
     ▼                ▼                    ▼                     ▼                   ▼
```

## C4: Component Diagram — Failure Points

```
┌─────────────────────────────────────────────────────────────────────────┐
│ AutoBuild Orchestrator (autobuild.py)                                   │
│                                                                         │
│  ┌───────────────┐    ┌──────────────────┐    ┌─────────────────────┐  │
│  │ Turn Loop     │───>│ _execute_turn()  │───>│ _is_feedback_       │  │
│  │ (1..max_turns)│    │                  │    │   _stalled()        │  │
│  │               │    │ _extract_        │    │                     │  │
│  │ perspective   │    │   feedback()     │    │ [BUG F4] MD5 of    │  │
│  │ reset at 3,5  │    │ ┌──────────────┐ │    │ full feedback incl. │  │
│  │ (clears       │    │ │Formats issues│ │    │ variable test output│  │
│  │  feedback to  │    │ │into text with│ │    │ → signatures never  │  │
│  │  Player, NOT  │    │ │full 500-char │ │    │   match across turns│  │
│  │  history)     │    │ │test_output   │ │    │                     │  │
│  └───────────────┘    │ └──────────────┘ │    │ _feedback_history   │  │
│                       └──────────────────┘    │ never cleared       │  │
│                                               └─────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
          │                                               ▲
          │ invoke_player()                               │ feedback_text
          ▼                                               │
┌───────────────────────────────────┐   ┌─────────────────────────────────┐
│ Agent Invoker (agent_invoker.py)  │   │ CoachValidator                   │
│                                   │   │ (coach_validator.py)             │
│ ┌─────────────────────────┐       │   │                                  │
│ │ Claude Agent SDK        │       │   │ validate() flow:                 │
│ │ ┌─────────────────────┐ │       │   │ 1. verify_quality_gates()        │
│ │ │ Bash Tool            │ │       │   │    [BUG F5] Short-circuits on   │
│ │ │ ✅ Shell profile     │ │       │   │    coverage_met=False (Turn 2)  │
│ │ │ ✅ Virtual env       │ │       │   │                                  │
│ │ │ ✅ PATH              │ │       │   │ 2. run_independent_tests()       │
│ │ │ ✅ DATABASE_URL      │ │       │   │    [BUG F1] subprocess.run()    │
│ │ │ ✅ All env vars      │ │       │   │    ❌ No shell profile           │
│ │ └─────────────────────┘ │       │   │    ❌ No virtual env             │
│ │                         │       │   │    ❌ No DATABASE_URL             │
│ │ TaskWorkStreamParser    │       │   │    → ALWAYS fails for DB tests   │
│ │ ┌─────────────────────┐ │       │   │                                  │
│ │ │ [BUG F2] Collects   │ │       │   │    _detect_tests_from_results() │
│ │ │ both absolute AND   │ │       │   │    [BUG F2] set() dedup fails   │
│ │ │ relative paths from │ │       │   │    on mixed abs/rel paths       │
│ │ │ agent output into   │ │       │   │                                  │
│ │ │ files_created/      │ │       │   │    _summarize_test_output()     │
│ │ │ files_modified      │ │       │   │    [BUG F3] Returns only last   │
│ │ └─────────────────────┘ │       │   │    3 keyword lines (500 chars)  │
│ └─────────────────────────┘       │   │    Strips error/traceback info  │
│                                   │   │                                  │
│ task_work_results.json:           │   │ 3. validate_requirements()       │
│ {                                 │   │    (never reached — step 2 fails)│
│   "files_created": [              │   │                                  │
│     "/abs/tests/test_users.py",   │   │ → Returns feedback with         │
│     "tests/users/test_users.py"   │   │   non-actionable test output    │
│   ]                               │   │                                  │
│ }                                 │   └──────────────────────────────────┘
└───────────────────────────────────┘
```

---

## Findings (Definitive Evidence)

### Finding 1: Environment Parity Gap (ROOT CAUSE — Critical)

**Severity**: Critical
**Files**: [coach_validator.py:868-876](guardkit/orchestrator/quality_gates/coach_validator.py#L868-L876), [agent_invoker.py:3366-3378](guardkit/orchestrator/agent_invoker.py#L3366-L3378)

**Definitive Evidence**:

The Player runs tests via the Claude Agent SDK's `Bash` tool, which spawns `/bin/bash` (or `/bin/zsh`) and **sources the user's shell profile** (`~/.bashrc`, `~/.zshrc`). This gives it access to:
- Virtual environments (poetry, pipenv, venv)
- User-configured `$PATH` (including homebrew, pyenv, nvm, etc.)
- Environment variables (`DATABASE_URL`, `REDIS_URL`, etc.)
- Docker/service orchestration commands

The Coach runs tests via bare `subprocess.run(test_cmd, shell=True, cwd=worktree_path)`:
```python
# coach_validator.py line 869-876
result = subprocess.run(
    test_cmd,           # "pytest tests/users/test_users.py -v --tb=short"
    shell=True,         # /bin/sh -c "..." — minimal shell, no profile
    cwd=str(self.worktree_path),
    capture_output=True,
    text=True,
    timeout=self.test_timeout,
)
```

`subprocess.run(shell=True)` invokes `/bin/sh -c`, which does **not** source user shell profiles. It inherits only `os.environ` from the parent Python process.

| Aspect | Player (Bash tool) | Coach (subprocess.run) |
|--------|-------------------|----------------------|
| Shell startup | Full profile sourced | Minimal `/bin/sh` |
| $PATH | User's full path | System default only |
| Virtual env | User's active venv | None |
| DB connectivity | Via user's env vars | No DATABASE_URL |
| Package access | Venv + system packages | System only |

**Log evidence**: Tests fail in 1.7-3.1 seconds consistently — characteristic of import failure or connection refusal, NOT actual test execution time:
- Line 359: `Independent tests failed in 3.1s`
- Lines 540, 600, 658, 716: `Independent tests failed in 1.7s`

**Why this creates an unfixable infinite loop**: The Player cannot fix a missing database connection by modifying code. Even if it adds mocked fixtures, the Coach's subprocess may lack the `pytest-mock` or `pytest-asyncio` packages needed to run them (if they're in a venv the Coach can't see).

---

### Finding 2: Duplicate Path Bug in Test Detection

**Severity**: Medium
**Files**: [coach_validator.py:1775-1800](guardkit/orchestrator/quality_gates/coach_validator.py#L1775-L1800), [agent_invoker.py:285-430](guardkit/orchestrator/agent_invoker.py#L285-L430)

**Definitive Evidence (Turn 1 and Turn 7)**:

Turn 1, line 357:
```
Running independent tests: pytest /Users/richardwoollcott/Projects/appmilla_github/
guardkit-examples/fastapi/.guardkit/worktrees/FEAT-BA28/tests/users/test_users.py
tests/users/test_users.py -v --tb=short
```
→ 1 file duplicated as absolute + relative = 2 paths passed to pytest

Turn 7, line 779:
```
Running independent tests: pytest /Users/.../tests/core/test_config.py
/Users/.../tests/test_foundation.py tests/core/test_config.py
tests/test_foundation.py -v --tb=short
```
→ 2 files duplicated = 4 paths passed to pytest

**Root cause chain**:

1. **Source**: `TaskWorkStreamParser` in `agent_invoker.py` collects file paths from SDK tool output. The SDK agent writes files using both absolute paths (from `Write` tool file_path parameter) and relative paths (from text descriptions). Both are stored in `_files_created` set.

2. **Propagation**: `task_work_results.json` contains both path forms in `files_created`/`files_modified` arrays. The `set()` dedup in `_write_task_work_results()` (line ~4052) fails because the strings differ.

3. **Bug site**: `_detect_tests_from_results()` at line 1780 does `self.worktree_path / filepath`. Python's `Path("/a") / "/b"` returns `Path("/b")` — the absolute path wins. So `full_path.exists()` succeeds for BOTH the absolute and relative entries. But `test_files.append(filepath)` preserves the ORIGINAL string, so both forms survive.

4. **Failed dedup**: Line 1793 `unique_files = sorted(set(test_files))` — `set()` on strings treats `/abs/path/test.py` and `tests/test.py` as distinct.

**Python pathlib proof**:
```python
>>> from pathlib import Path
>>> worktree = Path("/Users/rich/worktree")
>>> worktree / "tests/test.py"          # Relative → joined correctly
PosixPath('/Users/rich/worktree/tests/test.py')
>>> worktree / "/Users/rich/worktree/tests/test.py"  # Absolute → right wins
PosixPath('/Users/rich/worktree/tests/test.py')
# Both resolve to the same path, but the original strings differ
```

---

### Finding 3: Feedback Truncation Renders Feedback Non-Actionable

**Severity**: High
**Files**: [coach_validator.py:1802-1842](guardkit/orchestrator/quality_gates/coach_validator.py#L1802-L1842), [autobuild.py:3629-3669](guardkit/orchestrator/autobuild.py#L3629-L3669)

**Definitive Evidence (complete data flow trace)**:

```
Step 1: subprocess.run() captures stdout
Step 2: output = result.stdout or result.stderr or "No output"  [line 882]
Step 3: _summarize_test_output(output) [line 883]
        → Scans LAST 20 lines for keywords: "passed", "failed", "error", etc.
        → Returns up to 3 matching lines, max 500 chars
        → DISCARDS earlier lines (tracebacks, import errors, connection errors)
Step 4: IndependentTestResult.test_output_summary = summary [line 893]
Step 5: issue["test_output"] = test_result.test_output_summary [line 556]
Step 6: _extract_feedback() formats: "- {desc}:\n  {test_output}" [line 3667]
```

**What the Player receives**:
```
- Independent test verification failed:
  FAILED tests/users/test_users.py::TestUserCreate::test_create_user - ...
```

**What the Player NEEDS to see** (typical pytest output for a DB connection failure):
```
ERRORS
tests/users/test_users.py::TestUserCreate::test_create_user
E   sqlalchemy.exc.OperationalError: (psycopg2.OperationalError)
E   could not connect to server: Connection refused
E       Is the server running on host "localhost" (127.0.0.1) and
E       accepting TCP/IP connections on port 5432?
```

The `_summarize_test_output()` algorithm at line 1823-1830 scans **backwards** from the last 20 lines, looking for keyword matches. For a pytest failure, the last lines are typically:
```
FAILED tests/users/test_users.py::TestUserCreate::test_create_user
=================== 1 failed in 1.7s ===================
```

These match the keywords "failed" and "tests", so they're captured. But the actual error (lines E) is earlier in the output and is never included.

---

### Finding 4: Stall Detection Defeated by Variable Test Output

**Severity**: High
**Files**: [autobuild.py:2619-2699](guardkit/orchestrator/autobuild.py#L2619-L2699), [autobuild.py:597](guardkit/orchestrator/autobuild.py#L597)

**Definitive Evidence (traced end-to-end)**:

The full feedback text that reaches `_is_feedback_stalled()` is the output of `_extract_feedback()`, which includes the full `_summarize_test_output()` result (up to 500 chars). The MD5 is computed on this ENTIRE string:

```python
# autobuild.py line 2650-2652
feedback_sig = hashlib.md5(
    feedback.strip().lower().encode()  # Full feedback text including test output
).hexdigest()[:8]
```

**Why signatures differ between turns despite appearing identical in the log**:

The progress display at line 1928-1931 truncates feedback to 80 characters:
```python
summary = (
    f"Feedback: {feedback_text[:80]}..."
    if len(feedback_text) > 80
    else f"Feedback: {feedback_text}"
)
```

So the log shows `"FAILED tests/users/test_users.py::Test..."` for every turn — but the actual `feedback_text` contains the full 500-char `_summarize_test_output()` result. Since the Player rewrites test files each turn (different class names, method names, import structures), the pytest output changes:

- Turn 3: `"...FAILED tests/users/test_users.py::TestUserCreate::test_create_user - sqlalchemy..."`
- Turn 4: `"...FAILED tests/users/test_users.py::TestUserCRUD::test_create - OperationalError..."`
- Turn 5: `"...FAILED tests/users/test_users.py::TestUser::test_create_user - ConnectionRefused..."`

Each produces a different MD5 hash. The stall detector requires 3 IDENTICAL consecutive signatures, which never occurs.

**Confirmed**: `_feedback_history` is initialized once (line 597) and NEVER cleared. Perspective resets at turns 3 and 5 only set `previous_feedback = None` (line 1514) — they do NOT reset `_feedback_history`. This is correct behavior (stall detection should accumulate across resets), but is irrelevant because the signatures never match anyway.

**Stall detection state reconstruction**:

```
Turn 1: history = [(sig_A, 0)]                              → len < 3, skip
Turn 2: history = [(sig_A, 0), (sig_B, 0)]                  → len < 3, skip
         sig_B ≠ sig_A ("Coverage threshold not met")
Turn 3: history = [(sig_A, 0), (sig_B, 0), (sig_C, 0)]     → recent = [sig_B, sig_C]? No...
         WAIT — recent = history[-3:] = [(sig_A, 0), (sig_B, 0), (sig_C, 0)]
         sigs = {sig_A, sig_B, sig_C} → len != 1 → return False
Turn 4: history = [..., (sig_D, 0)]
         recent[-3:] = [(sig_B, 0), (sig_C, 0), (sig_D, 0)]
         sigs = {sig_B, sig_C, sig_D} → len != 1 → return False
Turn 5: history = [..., (sig_E, 0)]
         sigs = {sig_C, sig_D, sig_E} → len != 1 → return False
...continues forever because sig_X ≠ sig_Y for all turns
```

Each `sig_X` is different because the full 500-char test output differs each turn (variable test names/tracebacks).

---

### Finding 5: Quality Gates Short-Circuit Ordering

**Severity**: Low (contributory, not causal)
**Files**: [coach_validator.py:517-530](guardkit/orchestrator/quality_gates/coach_validator.py#L517-L530)

**Definitive Evidence (Turn 2 vs Turn 3+)**:

```python
# coach_validator.py validate() method, line 518-530:
if not gates_status.all_gates_passed:
    return self._feedback_from_gates(...)  # Returns BEFORE running independent tests

# Only if gates pass does it proceed to:
test_result = self.run_independent_tests(...)  # line 543
```

Turn 2 log (line 483-484):
```
Quality gate evaluation complete: tests=True (required=True), coverage=False
  (required=True), ... ALL_PASSED=False
Quality gates failed for TASK-DB-003: ...coverage_met=False...
```

This short-circuits to `_feedback_from_gates()` which generates:
```python
issues.append({
    "category": "coverage",
    "description": "Coverage threshold not met",  # line 2165
})
```

The feedback via `_extract_feedback()` becomes: `"- Coverage threshold not met"` — a completely different signature from the test verification feedback.

This is correct behavior (no point running tests if coverage is already failing), but it introduces a different feedback signature into `_feedback_history`, further defeating stall detection.

---

## Root Cause Causal Chain

```
                    ┌──────────────────────────────────────────┐
                    │ Player writes DB-dependent test code     │
                    │ (requires PostgreSQL, psycopg2, etc.)    │
                    └──────────────────┬───────────────────────┘
                                       │
                    ┌──────────────────▼───────────────────────┐
                    │ F1: Coach subprocess.run() has no DB,    │
                    │     no venv, no env vars                 │
                    │     → Tests ALWAYS fail (1.7-3.1s)       │
                    └──────────────────┬───────────────────────┘
                                       │
              ┌────────────────────────┼────────────────────────┐
              │                        │                        │
   ┌──────────▼──────────┐  ┌─────────▼──────────┐  ┌─────────▼──────────┐
   │ F3: Feedback only    │  │ F2: Duplicate paths │  │ F5: Turn 2 short-  │
   │ shows "FAILED..."    │  │ in pytest command   │  │ circuits on        │
   │ not the actual error │  │ (abs + rel)         │  │ coverage_met=False │
   │                      │  │                     │  │ → different sig    │
   │ Player cannot        │  │ Confusing output    │  │                    │
   │ diagnose the issue   │  │ may affect summary  │  │                    │
   └──────────┬───────────┘  └─────────┬───────────┘  └─────────┬──────────┘
              │                        │                        │
              └────────────────────────┼────────────────────────┘
                                       │
                    ┌──────────────────▼───────────────────────┐
                    │ F4: _summarize_test_output() returns     │
                    │     variable content each turn (Player   │
                    │     rewrites tests → different class     │
                    │     names → different pytest output)     │
                    │     → MD5 hash differs every turn        │
                    │     → _is_feedback_stalled() NEVER fires │
                    └──────────────────┬───────────────────────┘
                                       │
                    ┌──────────────────▼───────────────────────┐
                    │ 18 turns × ~2.5 min = 45 min             │
                    │ FeatureOrchestrator task_timeout (2400s)  │
                    │ → cooperative cancellation                │
                    │ → decision: "cancelled" (NOT stall)       │
                    └──────────────────────────────────────────┘
```

---

## Recommendations (Regression-Safe)

### R1: Include Error Context in Feedback (Quick Win)

**Impact**: High | **Effort**: Low | **Risk**: Low | **Priority**: 1

**File**: [coach_validator.py:1802-1842](guardkit/orchestrator/quality_gates/coach_validator.py#L1802-L1842)

**Change**: Modify `_summarize_test_output()` to include the first error/traceback from pytest output, not just the last summary lines.

**Proposed implementation**:
```python
def _summarize_test_output(self, output: str, max_length: int = 1500) -> str:
    """Summarize test output for reporting, preserving error context."""
    lines = output.strip().split("\n")

    # 1. Extract FIRST error/traceback (most actionable for the Player)
    error_lines = []
    for i, line in enumerate(lines):
        if any(kw in line for kw in [
            "Error:", "ERRORS", "ImportError", "ModuleNotFoundError",
            "ConnectionRefusedError", "OperationalError", "E   ",
            "FileNotFoundError", "ConnectionError",
        ]):
            error_lines = [l.strip() for l in lines[max(0, i-1):i+4] if l.strip()]
            break

    # 2. Extract final summary (existing behavior)
    summary_lines = []
    for line in reversed(lines[-20:]):
        if any(keyword in line.lower() for keyword in [
            "passed", "failed", "error", "skipped",
            "success", "failure", "ok", "tests"
        ]):
            summary_lines.insert(0, line.strip())
            if len(summary_lines) >= 3:
                break

    # 3. Combine: error context + summary
    parts = []
    if error_lines:
        parts.append("Error detail:\n  " + "\n  ".join(error_lines[:4]))
    if summary_lines:
        parts.append("Result:\n  " + "\n  ".join(summary_lines))

    if parts:
        summary = "\n".join(parts)
    else:
        summary = "\n".join(lines[-3:])

    if len(summary) > max_length:
        summary = summary[:max_length - 3] + "..."

    return summary
```

**Regression safety**:
- The method signature is unchanged (`output: str, max_length: int`) — no callers break
- The return type is unchanged (`str`) — no downstream consumers break
- The `max_length` default increases from 500 to 1500, but `IndependentTestResult.test_output_summary` is a plain string field with no length constraint
- The only consumer of `test_output_summary` is `_extract_feedback()` which embeds it in feedback text — longer text is fine
- **Existing tests**: Any test mocking `_summarize_test_output` should continue working; tests checking the output format may need updating to account for the "Error detail:" prefix

**Test plan**:
- Unit test: `_summarize_test_output` with ConnectionRefusedError pytest output → verify error context included
- Unit test: `_summarize_test_output` with passing pytest output → verify backward compatibility
- Unit test: Truncation at `max_length` boundary
- Integration test: Verify feedback text sent to Player includes error detail

---

### R2: Normalize Feedback for Stall Detection (Quick Win)

**Impact**: High | **Effort**: Low | **Risk**: Low | **Priority**: 2

**File**: [autobuild.py:2619-2699](guardkit/orchestrator/autobuild.py#L2619-L2699)

**Change**: Normalize feedback text before computing MD5 hash, stripping variable details to detect *semantic* repetition.

**Proposed implementation**:
```python
import re

# Class constant (add to AutoBuildOrchestrator)
_STALL_NORMALIZE_PATTERNS = [
    (re.compile(r'tests/\S+\.py::\S+'), 'tests/<FILE>::<TEST>'),  # test paths + classes
    (re.compile(r'line \d+'), 'line <N>'),                        # line numbers
    (re.compile(r'\d+(\.\d+)?%'), '<N>%'),                        # percentages
    (re.compile(r'in \d+\.\d+s'), 'in <N>s'),                     # durations
    (re.compile(r'\d+ (passed|failed|error|skipped)'), '<N> \\1'), # test counts
]

def _normalize_feedback_for_stall(self, feedback: str) -> str:
    """Normalize feedback to detect semantic repetition despite variable details.

    Strips test file names, class names, line numbers, percentages, and
    test counts so that semantically identical feedback (e.g., "tests failed
    due to import error" with different class names) hashes to the same
    MD5 signature.
    """
    normalized = feedback
    for pattern, replacement in self._STALL_NORMALIZE_PATTERNS:
        normalized = pattern.sub(replacement, normalized)
    return normalized
```

Then modify `_is_feedback_stalled` at line 2650:
```python
# BEFORE:
feedback_sig = hashlib.md5(
    feedback.strip().lower().encode()
).hexdigest()[:8]

# AFTER:
normalized = self._normalize_feedback_for_stall(feedback)
feedback_sig = hashlib.md5(
    normalized.strip().lower().encode()
).hexdigest()[:8]
```

**Regression safety**:
- `_is_feedback_stalled()` is only called from one location (line 1629)
- The normalization only affects the stall detection hash, NOT the actual feedback text sent to the Player
- The `_feedback_history` still stores the normalized signature — this is internal state, no external consumers
- **Risk of false positives**: The normalization could cause the stall detector to fire when the Player IS making meaningful progress but the feedback *structure* is similar. Mitigated by: (a) the criteria_passed_count check already prevents false positives when criteria are advancing, and (b) the extended threshold (threshold+2) gives extra runway for partial progress.

**Test plan**:
- Unit test: `_normalize_feedback_for_stall` with test verification feedback → verify normalization
- Unit test: `_is_feedback_stalled` with 3 turns of same-category but different-detail feedback → verify stall fires
- Unit test: `_is_feedback_stalled` with genuinely different feedback categories → verify no false positive
- Regression test: Replay TASK-DB-003 turn sequence → verify stall fires at Turn 5

---

### R3: Fix Duplicate Path Deduplication (Quick Win)

**Impact**: Medium | **Effort**: Low | **Risk**: Low | **Priority**: 3

**File**: [coach_validator.py:1775-1800](guardkit/orchestrator/quality_gates/coach_validator.py#L1775-L1800)

**Change**: Normalize all paths to relative form before deduplication.

**Proposed implementation** (replace lines 1775-1800):
```python
def _detect_tests_from_results(
    self, task_work_results: Dict[str, Any]
) -> Optional[str]:
    """Primary test detection: find test files from task_work_results."""
    test_files = []
    for file_list_key in ("files_created", "files_modified"):
        for filepath in task_work_results.get(file_list_key, []):
            # Normalize to relative path for consistent deduplication
            normalized = self._normalize_to_relative(filepath)
            basename = Path(normalized).name
            if (basename.startswith("test_") and basename.endswith(".py")) or \
               basename.endswith("_test.py"):
                full_path = self.worktree_path / normalized
                if full_path.exists():
                    test_files.append(str(normalized))

    if not test_files:
        logger.debug("No test files found in task_work_results")
        return None

    # Deduplicate (now safe — all paths are relative)
    unique_files = sorted(set(test_files))
    files_str = " ".join(unique_files)
    logger.info(
        f"Task-specific tests detected via task_work_results: "
        f"{len(unique_files)} file(s)"
    )
    logger.debug(f"Test files (from task_work_results): {files_str}")
    return f"pytest {files_str} -v --tb=short"

def _normalize_to_relative(self, filepath: str) -> str:
    """Normalize a filepath to be relative to the worktree.

    Handles both absolute paths (strips worktree prefix) and
    relative paths (returned as-is).
    """
    p = Path(filepath)
    if p.is_absolute():
        try:
            return str(p.relative_to(self.worktree_path))
        except ValueError:
            # Path is absolute but not under worktree — return as-is
            return filepath
    return filepath
```

**Regression safety**:
- `_detect_tests_from_results` is called from exactly one place: `_detect_test_command()` at line 1642
- The return type is unchanged (`Optional[str]`)
- The pytest command format is unchanged (`pytest {files} -v --tb=short`)
- The new `_normalize_to_relative` helper is side-effect-free
- **Edge case**: If `filepath` is absolute but NOT under `worktree_path`, `relative_to()` raises `ValueError` — caught and handled by returning the original path

**Test plan**:
- Unit test: `_normalize_to_relative` with absolute path under worktree → relative
- Unit test: `_normalize_to_relative` with relative path → unchanged
- Unit test: `_normalize_to_relative` with absolute path NOT under worktree → unchanged
- Unit test: `_detect_tests_from_results` with mixed abs/rel paths → single deduplicated entry
- Integration test: Verify pytest command has no duplicate paths

---

### R4: Classify Infrastructure vs Code Test Failures (Medium Effort)

**Impact**: High | **Effort**: Medium | **Risk**: Medium | **Priority**: 4

**File**: [coach_validator.py:828-914](guardkit/orchestrator/quality_gates/coach_validator.py#L828-L914)

**Change**: After `run_independent_tests()` fails, classify the failure as infrastructure vs code. For infrastructure failures, generate actionable feedback telling the Player to mock DB dependencies or use SQLite for tests.

**Proposed implementation** (add to `CoachValidator`):
```python
# Infrastructure failure patterns
_INFRA_FAILURE_PATTERNS = [
    "ConnectionRefusedError",
    "ConnectionError",
    "OperationalError",
    "psycopg2",
    "psycopg",
    "asyncpg",
    "sqlalchemy.exc.OperationalError",
    "could not connect to server",
    "Connection refused",
    "ModuleNotFoundError",
    "ImportError",
    "No module named",
    "django.db.utils.OperationalError",
    "pymongo.errors.ServerSelectionTimeoutError",
    "redis.exceptions.ConnectionError",
]

def _classify_test_failure(self, test_output: str) -> str:
    """Classify test failure as infrastructure or code issue.

    Returns 'infrastructure' if the failure is caused by missing
    dependencies, database connections, or environment issues that
    the Player cannot fix by modifying code alone.
    Returns 'code' for assertion failures, logic errors, etc.
    """
    for pattern in self._INFRA_FAILURE_PATTERNS:
        if pattern.lower() in test_output.lower():
            return "infrastructure"
    return "code"
```

Then in the feedback path at line 545-560, add classification:
```python
if not test_result.tests_passed:
    # Classify failure type
    failure_class = self._classify_test_failure(
        # Use raw output, not summary (which may strip the error)
        result.stdout + "\n" + result.stderr  # Need to capture raw output
    )

    if failure_class == "infrastructure":
        description = (
            "Independent test verification failed due to INFRASTRUCTURE dependency "
            "(database connection, missing package, or environment issue). "
            "This cannot be fixed by code changes alone. "
            "Options: (a) Add conftest.py with mocked DB fixtures, "
            "(b) Use SQLite for test database, "
            "(c) Mark tests as @pytest.mark.integration and skip in CI, "
            "(d) Add a pyproject.toml [tool.pytest.ini_options] with test DB config."
        )
    else:
        description = "Independent test verification failed"
```

**Regression safety**:
- Requires modifying `run_independent_tests()` to also store the raw stdout/stderr (currently only summary is stored)
- The `IndependentTestResult` dataclass may need a new optional field `raw_output: Optional[str] = None`
- The feedback content changes for infrastructure failures — this is intentional and beneficial
- **Risk**: False classification — a test could fail with `ImportError` due to a genuine code bug (e.g., circular import). Mitigated by: the feedback still tells the Player to investigate and provides options, not an automatic skip.

**Test plan**:
- Unit test: `_classify_test_failure` with ConnectionRefusedError → infrastructure
- Unit test: `_classify_test_failure` with AssertionError → code
- Unit test: `_classify_test_failure` with ImportError → infrastructure (acceptable trade-off)
- Integration test: Infrastructure failure → verify actionable feedback text

---

### R5: Resolve Coach/Player Environment Parity (Strategic)

**Impact**: Critical | **Effort**: Variable (see options) | **Risk**: Medium | **Priority**: 5

**File**: [coach_validator.py:868-876](guardkit/orchestrator/quality_gates/coach_validator.py#L868-L876)

This is the root cause finding (F1). Three options are analysed below, from lightweight to full parity.

---

#### Option A: Login Shell (`bash -l -c`)

**Effort**: Low | **Parity**: ~80%

Source the user's shell profile before running tests:
```python
result = subprocess.run(
    ["bash", "-l", "-c", test_cmd],
    cwd=str(self.worktree_path),
    capture_output=True,
    text=True,
    timeout=self.test_timeout,
)
```

| Pro | Con |
|-----|-----|
| Simple 1-line change | Only sources `~/.bash_profile` / `~/.profile`, NOT `~/.bashrc` (non-interactive login shell) |
| No API cost | Misses env vars set only in `.bashrc` or `.zshrc` |
| Deterministic | Doesn't help conda/poetry/nvm environments that use shell hooks |
| Fast (~0s overhead) | Doesn't pick up shell-function-based activations (e.g., `conda activate`) |

**Parity gap**: Anything set via interactive shell hooks (conda, nvm, pyenv) or `.bashrc`-only exports is still missing. For users whose venv is in PATH from their profile, this works. For conda/poetry users, it doesn't.

---

#### Option B: Explicit Environment Propagation

**Effort**: Medium | **Parity**: ~90%

Capture and propagate key environment variables explicitly:
```python
import shutil

env = os.environ.copy()

# Detect and activate virtual environments
venv_candidates = [
    self.worktree_path / ".venv" / "bin",
    self.worktree_path / "venv" / "bin",
    self.worktree_path / ".guardkit" / "venv" / "bin",
]
for venv_bin in venv_candidates:
    if venv_bin.exists():
        env["PATH"] = f"{venv_bin}:{env.get('PATH', '')}"
        env["VIRTUAL_ENV"] = str(venv_bin.parent)
        break

result = subprocess.run(
    test_cmd,
    shell=True,
    cwd=str(self.worktree_path),
    capture_output=True,
    text=True,
    timeout=self.test_timeout,
    env=env,
)
```

| Pro | Con |
|-----|-----|
| Handles venv/virtualenv explicitly | Hardcoded venv paths — misses custom locations |
| No API cost | Misses conda, poetry, nvm, pyenv, direnv |
| Deterministic | Grows into a maintenance burden as new env managers appear |
| Fast (~0s overhead) | Doesn't propagate env vars set by Docker/compose/.env files |

**Parity gap**: Better than Option A for the common venv case, but still a partial solution that requires ongoing maintenance as the Python ecosystem evolves.

---

#### Option C: Run Coach Tests via SDK Bash Tool (Full Player Parity) — RECOMMENDED

**Effort**: High (initial), Low (ongoing) | **Parity**: 100%

Use a minimal Claude Agent SDK invocation to run pytest, getting identical environment to the Player.

**How it would work**:

The SDK's `query()` function spawns the Claude Code CLI as a subprocess. Critically, this subprocess **inherits the full `os.environ`** from the parent process (confirmed in the SDK source at `subprocess_cli.py:379-411`):

```python
# SDK internal (subprocess_cli.py:390-399)
process_env = {
    **os.environ,               # ← FULL current environment inherited
    **self._options.env,        # ← User-provided extras (empty by default)
    "CLAUDE_CODE_ENTRYPOINT": "sdk-py",
}
```

The Claude Code CLI then runs its Bash tool using the user's shell, which sources their profile. This is the exact chain the Player uses:

```
GuardKit process (venv, PATH, DB_URL, etc.)
  → claude_agent_sdk.query()
    → Claude Code CLI subprocess (inherits os.environ)
      → Claude decides to use Bash tool
        → Bash runs with user's shell profile
          → pytest tests/ (full environment)
```

**Proposed implementation (validated against SDK v0.1.18 API surface)**:

The implementation below has been validated against every technology seam. Each
gap identified during validation is annotated with `# GAP-FIX:` comments.

```python
# ============================================================================
# New imports needed at top of coach_validator.py
# ============================================================================
import time
from typing import Optional, Dict, Any, List, Tuple
# SDK imports are lazy (inside method) to match existing codebase pattern


# ============================================================================
# New method in CoachValidator class
# ============================================================================
async def _run_tests_via_sdk(self, test_cmd: str) -> IndependentTestResult:
    """Run tests via SDK Bash tool for full environment parity with Player.

    Uses a minimal single-turn SDK invocation with a deterministic prompt
    that instructs Claude to run the exact test command and report results.

    SDK API contract (validated against claude_agent_sdk v0.1.18):
    - query() returns AsyncIterator[Message]
    - Message = UserMessage | AssistantMessage | SystemMessage | ResultMessage | StreamEvent
    - ToolResultBlock.content: str | list[dict[str, Any]] | None
    - ToolResultBlock.is_error: bool | None (True if non-zero exit code)
    - ClaudeAgentOptions.model: str (full model ID, NOT shorthand)
    - ClaudeAgentOptions.system_prompt: str | SystemPromptPreset | None
    - ClaudeAgentOptions.permission_mode: "default"|"acceptEdits"|"plan"|"bypassPermissions"
    """
    # GAP-FIX #1: Lazy import matches existing codebase pattern (agent_invoker.py:1354)
    from claude_agent_sdk import (
        query,
        ClaudeAgentOptions,
        CLINotFoundError,
        ProcessError,
        CLIJSONDecodeError,
        AssistantMessage,
        UserMessage,
        ToolUseBlock,
        ToolResultBlock,
        ResultMessage,
    )

    prompt = (
        "Run this exact command and report the full output. "
        "Do not modify the command. Do not add or remove any flags. "
        "Do not install packages. Just run it exactly as given.\n\n"
        f"```bash\n{test_cmd}\n```"
    )

    options = ClaudeAgentOptions(
        cwd=str(self.worktree_path),
        allowed_tools=["Bash"],       # Only Bash — minimal surface area
        permission_mode="bypassPermissions",
        max_turns=1,                  # Single turn — run command and stop
        # GAP-FIX #2: model must be full ID, not shorthand "haiku"
        # Using claude-haiku-4-5 for cheapest execution (~$0.01/turn)
        model="claude-haiku-4-5-20251001",
        # GAP-FIX #3: system_prompt is str|SystemPromptPreset|None
        # String value is passed directly via --system-prompt flag
        system_prompt=(
            "You are a test runner. Your only job is to run the exact "
            "command given by the user using the Bash tool. Do not modify "
            "the command in any way. Do not add flags, install packages, "
            "or take any other action."
        ),
    )

    start_time = time.time()
    bash_output = ""
    bash_is_error = False
    session_error = False

    async for message in query(prompt=prompt, options=options):
        # GAP-FIX #4: Bash tool output appears in UserMessage (tool result),
        # NOT in AssistantMessage. The SDK message flow is:
        #   1. AssistantMessage with ToolUseBlock(name="Bash", ...)
        #   2. UserMessage with ToolResultBlock(content="pytest output", is_error=True/False)
        #   3. AssistantMessage with TextBlock("The tests show...")
        # We MUST handle UserMessage to capture the actual Bash output.
        if isinstance(message, UserMessage):
            content = message.content
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, ToolResultBlock):
                        # GAP-FIX #5: content is str | list[dict] | None
                        # For Bash tool, it's typically str (combined stdout+stderr)
                        if isinstance(block.content, str):
                            bash_output = block.content
                        elif isinstance(block.content, list):
                            # list[dict] format: [{"type": "text", "text": "..."}]
                            parts = []
                            for item in block.content:
                                if isinstance(item, dict) and "text" in item:
                                    parts.append(item["text"])
                            bash_output = "\n".join(parts)
                        # GAP-FIX #6: is_error reflects non-zero exit code
                        # This is MORE reliable than parsing "passed"/"failed" from text
                        if block.is_error is not None:
                            bash_is_error = block.is_error

        elif isinstance(message, ResultMessage):
            session_error = message.is_error
            logger.info(
                f"SDK Coach test run: turns={message.num_turns}, "
                f"cost=${message.total_cost_usd or 0:.4f}, "
                f"error={message.is_error}"
            )

    duration = time.time() - start_time

    if not bash_output and session_error:
        # SDK session itself failed (not the tests)
        return IndependentTestResult(
            tests_passed=False,
            test_command=test_cmd,
            test_output_summary="SDK test execution failed - session error",
            duration_seconds=duration,
        )

    if not bash_output:
        # Claude didn't run the Bash command (unlikely with max_turns=1 + Bash-only)
        return IndependentTestResult(
            tests_passed=False,
            test_command=test_cmd,
            test_output_summary="SDK test execution: no Bash output captured",
            duration_seconds=duration,
        )

    # GAP-FIX #7: Use is_error (exit code) as primary signal, NOT text parsing.
    # is_error=True means pytest returned non-zero (tests failed).
    # is_error=False/None means pytest returned 0 (tests passed).
    # This avoids false positives from "passed" appearing in error messages.
    tests_passed = not bash_is_error

    summary = self._summarize_test_output(bash_output)

    return IndependentTestResult(
        tests_passed=tests_passed,
        test_command=test_cmd,
        test_output_summary=summary,
        # GAP-FIX #8: duration_seconds is a REQUIRED field (no default)
        duration_seconds=duration,
    )


# ============================================================================
# Modified run_independent_tests() with SDK-first execution
# ============================================================================
def run_independent_tests(
    self,
    task_work_results: Optional[Dict[str, Any]] = None,
) -> IndependentTestResult:
    """Run tests independently to verify Player's claimed results.

    Uses SDK Bash tool by default for full environment parity with Player.
    Falls back to subprocess.run() on explicit config or SDK errors.
    """
    start_time = time.time()

    test_cmd = self.test_command or self._detect_test_command(
        self.task_id, task_work_results=task_work_results
    )

    if test_cmd is None:
        return IndependentTestResult(
            tests_passed=True,
            test_command="skipped",
            test_output_summary="No task-specific tests detected",
            duration_seconds=0.0,
        )

    # SDK is always available in AutoBuild context (_require_sdk() enforced at CLI entry)
    # Use subprocess mode only if explicitly configured
    if self._coach_test_execution != "subprocess":
        try:
            # GAP-FIX #9: Match the async/sync bridge pattern from autobuild.py:3459-3463
            # (_invoke_player_safely and coach fallback use this exact pattern)
            import asyncio
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            return loop.run_until_complete(
                self._run_tests_via_sdk(test_cmd)
            )
        except Exception as e:
            # Defensive fallback — SDK invocation error, not a missing dependency
            logger.warning(
                f"SDK test execution error, falling back to subprocess: {e}"
            )

    # Fallback: direct subprocess (bare environment — explicit opt-in or error recovery)
    try:
        result = subprocess.run(
            test_cmd,
            shell=True,
            cwd=str(self.worktree_path),
            capture_output=True,
            text=True,
            timeout=self.test_timeout,
        )
        duration = time.time() - start_time
        tests_passed = result.returncode == 0
        output = result.stdout or result.stderr or "No output"
        summary = self._summarize_test_output(output)
        return IndependentTestResult(
            tests_passed=tests_passed,
            test_command=test_cmd,
            test_output_summary=summary,
            duration_seconds=duration,
        )
    except subprocess.TimeoutExpired:
        duration = time.time() - start_time
        return IndependentTestResult(
            tests_passed=False,
            test_command=test_cmd,
            test_output_summary=f"Test execution timed out after {self.test_timeout}s",
            duration_seconds=duration,
        )
    except Exception as e:
        duration = time.time() - start_time
        return IndependentTestResult(
            tests_passed=False,
            test_command=test_cmd,
            test_output_summary=f"Test execution failed: {e}",
            duration_seconds=duration,
        )
```

### Gaps Identified and Fixed (Technology Seam Analysis)

The original proposed implementation had **9 gaps** at technology seams. All are
fixed in the validated implementation above:

| # | Gap | Seam | Risk if Unfixed | Fix |
|---|-----|------|-----------------|-----|
| 1 | SDK imports not lazy | Python import seam | `ImportError` in non-AutoBuild context | Lazy import inside method, matching `agent_invoker.py:1354` pattern |
| 2 | `model="haiku"` is invalid | SDK → CLI `--model` flag | `ProcessError` — CLI doesn't recognize shorthand | Use full ID: `"claude-haiku-4-5-20251001"` (matching `agent_invoker.py:581-582` pattern) |
| 3 | `system_prompt` type assumption | SDK types seam | None (str is valid), but documented for clarity | Confirmed `str` is accepted, passed via `--system-prompt` flag |
| 4 | Only checking `AssistantMessage` | SDK message parser seam | **Bash output never captured** — `ToolResultBlock` is in `UserMessage` | Handle both `UserMessage` and `AssistantMessage` |
| 5 | `str(block.content)` on list content | SDK `ToolResultBlock.content` type union | Garbled output: `"[{'type': 'text', 'text': '...'}]"` | Type-check content: `str` vs `list[dict]` with proper extraction |
| 6 | `"PASSED" in output` for pass/fail | Text parsing seam | False positive if "passed" appears in error text | Use `ToolResultBlock.is_error` — reflects actual exit code |
| 7 | Missing `is_error` check | SDK tool result seam | Incorrect test pass/fail determination | Primary signal from `is_error`, not text parsing |
| 8 | Missing `duration_seconds` field | `IndependentTestResult` dataclass seam | `TypeError` — field has no default | Always provide `duration_seconds=duration` |
| 9 | `asyncio.get_event_loop()` without safety | async/sync bridge seam | `RuntimeError: no current event loop` | Use exact pattern from `autobuild.py:3459-3463` with try/except |

### C4 Level 3: Validated Component Interaction Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          AutoBuild Turn Loop                            │
│                          (SYNC — no running event loop)                 │
│                                                                         │
│  _execute_turn() [SYNC]                                                 │
│       │                                                                 │
│       ├──→ _invoke_player_safely() [SYNC]                               │
│       │       │                                                         │
│       │       ├── loop = asyncio.get_event_loop()  ←── GAP-FIX #9      │
│       │       └── loop.run_until_complete(                              │
│       │              agent_invoker.invoke_player()  [ASYNC]             │
│       │                  └── query(prompt, options)                     │
│       │                       model="claude-sonnet-4-5-20250929"       │
│       │                       allowed_tools=["Read","Write","Edit",    │
│       │                                      "Bash","Grep","Glob"]     │
│       │                       max_turns=50                              │
│       │                       ┌────────────────────────────────┐       │
│       │                       │ Claude Code CLI (Node.js)      │       │
│       │                       │   → Bash tool (user shell env) │       │
│       │                       │   → pytest tests/ ✓            │       │
│       │                       └────────────────────────────────┘       │
│       │                  )                                              │
│       │                                                                 │
│       └──→ _invoke_coach_safely() [SYNC]                                │
│               │                                                         │
│               ├── loop = asyncio.get_event_loop()  (for Graphiti)       │
│               │                                                         │
│               └── validator = CoachValidator(worktree_path, task_id)     │
│                   validation_result = validator.validate(...)  [SYNC]    │
│                       │                                                 │
│                       └── run_independent_tests()  [SYNC]               │
│                           │                                             │
│                           ├── if _coach_test_execution != "subprocess": │
│                           │   │                                         │
│                           │   ├── loop = asyncio.get_event_loop()       │
│                           │   │   ←── GAP-FIX #9: exact autobuild      │
│                           │   │       pattern with try/except           │
│                           │   │                                         │
│                           │   └── loop.run_until_complete(              │
│                           │          _run_tests_via_sdk()  [ASYNC]      │
│                           │              │                              │
│                           │              ├── query(prompt, options)      │
│                           │              │   model="claude-haiku-4-5-   │
│                           │              │         20251001"            │
│                           │              │   ←── GAP-FIX #2: full ID   │
│                           │              │   allowed_tools=["Bash"]     │
│                           │              │   max_turns=1                │
│                           │              │   permission_mode=           │
│                           │              │     "bypassPermissions"      │
│                           │              │   system_prompt="You are..." │
│                           │              │   ←── GAP-FIX #3: str ok    │
│                           │              │                              │
│                           │              │   ┌──────────────────────┐   │
│                           │              │   │ Claude Code CLI      │   │
│                           │              │   │ (SAME as Player)     │   │
│                           │              │   │  → Bash tool         │   │
│                           │              │   │  → user shell env    │   │
│                           │              │   │  → pytest tests/ ✓   │   │
│                           │              │   └──────────────────────┘   │
│                           │              │                              │
│                           │              ├── Handle UserMessage         │
│                           │              │   ←── GAP-FIX #4            │
│                           │              │   └── ToolResultBlock        │
│                           │              │       .content: str          │
│                           │              │       ←── GAP-FIX #5        │
│                           │              │       .is_error: bool        │
│                           │              │       ←── GAP-FIX #6,#7     │
│                           │              │                              │
│                           │              └── Return IndependentTestResult│
│                           │                  .tests_passed = !is_error  │
│                           │                  .duration_seconds = dur    │
│                           │                  ←── GAP-FIX #8            │
│                           │          )                                  │
│                           │                                             │
│                           └── FALLBACK: subprocess.run()                │
│                               (bare env — explicit opt-in or error)     │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### C4 Level 2: Event Loop Lifecycle (Critical Async/Sync Seam)

```
Thread: Main thread (AutoBuild orchestration is single-threaded, line 432)

_execute_turn()                          ←── No event loop running
    │
    ├── _invoke_player_safely()
    │   ├── loop = get_event_loop()      ←── Creates or gets loop
    │   ├── loop.run_until_complete(     ←── Blocks until SDK completes
    │   │       invoke_player()          ←── async: uses loop
    │   │   )
    │   └── loop is now idle             ←── Event loop exists but not running
    │
    └── _invoke_coach_safely()
        ├── loop = get_event_loop()      ←── Gets SAME loop (still exists)
        ├── loop.run_until_complete(     ←── Blocks for Graphiti context
        │       get_graphiti_context()
        │   )
        ├── CoachValidator.validate()    ←── SYNC call
        │   └── run_independent_tests()  ←── SYNC call
        │       ├── loop = get_event_loop()  ←── Gets SAME loop again
        │       └── loop.run_until_complete( ←── Blocks for SDK test run
        │               _run_tests_via_sdk() ←── async: uses loop
        │           )
        └── loop is now idle

KEY: loop.run_until_complete() is safe here because:
  1. The loop exists but is NOT currently running (no nested run_until_complete)
  2. Player has finished and returned before Coach starts
  3. Graphiti context fetch has finished before validate() starts
  4. Each run_until_complete() is sequential, never nested
```

### Required Changes to CoachValidator.__init__() and Instantiation

```python
# ============================================================================
# Modified CoachValidator.__init__() (coach_validator.py:358-386)
# ============================================================================
def __init__(
    self,
    worktree_path: str,
    test_command: Optional[str] = None,
    test_timeout: int = 300,
    task_id: Optional[str] = None,
    # NEW: config option for test execution mode
    coach_test_execution: str = "sdk",  # "sdk" (default) | "subprocess"
):
    self.worktree_path = Path(worktree_path)
    self.test_command = test_command
    self.test_timeout = test_timeout
    self.task_id = task_id
    self._coach_test_execution = coach_test_execution


# ============================================================================
# Modified instantiation in autobuild.py:3521
# ============================================================================
# Config loading follows security_config.py pattern (read from .guardkit/config.yaml)
coach_config = self._load_coach_config()

validator = CoachValidator(
    str(worktree.path),
    task_id=task_id,
    coach_test_execution=coach_config.get("test_execution", "sdk"),
)


# ============================================================================
# New method in AutoBuildOrchestrator (follows security_config.py:69 pattern)
# ============================================================================
def _load_coach_config(self) -> Dict[str, Any]:
    """Load Coach configuration from .guardkit/config.yaml.

    Config structure:
        autobuild:
          coach:
            test_execution: "sdk"  # or "subprocess"

    Returns empty dict if config file doesn't exist.
    """
    config_path = self._repo_root / ".guardkit" / "config.yaml"
    if not config_path.exists():
        return {}
    try:
        import yaml
        with open(config_path, "r") as f:
            config = yaml.safe_load(f) or {}
        return config.get("autobuild", {}).get("coach", {})
    except Exception:
        return {}
```

### Data Contract Validation

The `IndependentTestResult` returned by `_run_tests_via_sdk()` must satisfy the same
contract as the existing `subprocess.run()` path. Traced through all downstream consumers:

```
IndependentTestResult
  .tests_passed: bool    → checked at coach_validator.py:545 (approve vs feedback)
  .test_command: str     → serialized in to_dict() at line 294
  .test_output_summary: str → included in feedback issues at line 557
  .duration_seconds: float → serialized in to_dict() at line 296

All four fields populated ✓ in every return path of _run_tests_via_sdk()
All four fields populated ✓ in every return path of subprocess fallback
No new fields added — no downstream breakage possible
```

---

**Detailed Pros/Cons Analysis**:

| Pro | Con |
|-----|-----|
| **100% environment parity** — identical to Player | ~$0.01-0.03 per invocation (Haiku, 1 turn) |
| Zero maintenance — automatically adapts to any env manager | 5-15 second overhead per test run (SDK startup) |
| Works with venv, conda, poetry, nvm, pyenv, direnv, Docker | Non-deterministic: Claude *could* modify the command |
| Shell profile sourced naturally by CLI's Bash tool | Adds async dependency to CoachValidator |
| SDK always available (hard requirement for AutoBuild) | Network/API dependency for test execution |
| No hardcoded paths or env var lists to maintain | Slightly more complex error handling |
| Future-proof — any new env manager works automatically | |

**Mitigations for key cons**:

1. **Cost**: Using `model="claude-haiku-4-5-20251001"` with `max_turns=1` keeps cost to ~$0.01. Over 18 turns that's $0.18 — trivial compared to the $10-40 wasted on 18 full Player turns.

2. **Non-determinism**: The `system_prompt` + `max_turns=1` + `allowed_tools=["Bash"]` heavily constrains Claude. With only 1 turn and 1 tool available, the model has no room for creative deviation. The explicit "Do not modify the command" instruction provides additional safety.

3. **Latency**: The 5-15s SDK startup overhead is acceptable given that:
   - The Coach already waits 1.7-3.1s for subprocess tests
   - The Player turn takes 30-120s
   - Preventing a single infinite loop saves 45+ minutes

4. **Async dependency**: The `asyncio.get_event_loop().run_until_complete()` wrapper handles this. If CoachValidator is already called from an async context (which it is — AutoBuild uses async), this integrates naturally.

5. **SDK availability is guaranteed in AutoBuild context**: The `claude-agent-sdk` is listed as an optional dependency in `pyproject.toml` (line 42, under `[autobuild]` extra), but it is a **hard runtime requirement** for AutoBuild. Both AutoBuild CLI entry points call `_require_sdk()` ([cli/autobuild.py:282](guardkit/cli/autobuild.py#L282) and [cli/autobuild.py:594](guardkit/cli/autobuild.py#L594)) which exits immediately if the SDK is not importable. Since CoachValidator only runs within AutoBuild, the SDK is **always available** when Coach tests execute. The "optional" framing in `pyproject.toml` only means users who don't use AutoBuild (e.g., just the task workflow CLI) don't need to install it. A fallback to `subprocess.run()` is still prudent for defensive coding, but in practice, the SDK path will always be taken.

---

#### Comparison Matrix

| Criteria | Option A (Login Shell) | Option B (Explicit Env) | Option C (SDK Bash) |
|----------|----------------------|------------------------|---------------------|
| Parity with Player | ~80% | ~90% | **100%** |
| Cost per test run | $0 | $0 | ~$0.01-0.03 |
| Latency overhead | ~0s | ~0s | ~5-15s |
| Maintenance burden | Low | High (growing) | **None** |
| Works with venv | Yes | Yes | Yes |
| Works with conda | Partial | No | **Yes** |
| Works with poetry | Partial | No | **Yes** |
| Works with nvm/pyenv | Partial | No | **Yes** |
| Works with direnv | No | No | **Yes** |
| Works with Docker services | No | No | **Yes (if Player can)** |
| Future env managers | No | No | **Yes** |
| Requires SDK dependency | No | No | Yes (always present in AutoBuild) |
| Deterministic | Yes | Yes | ~99% (constrained) |
| Graceful degradation | N/A | N/A | **Falls back to subprocess** |

---

#### Architecture: Option C Component Diagram

```
┌─────────────────────────────────────────────────────┐
│                  AutoBuild Turn Loop                 │
│                                                     │
│  ┌──────────────┐          ┌──────────────────────┐ │
│  │    Player     │          │    CoachValidator     │ │
│  │ (AgentInvoker)│          │                      │ │
│  └───────┬──────┘          │  run_independent_    │ │
│          │                 │  tests()             │ │
│          ▼                 │    │                  │ │
│  ┌───────────────┐         │    ▼ (try SDK first) │ │
│  │ SDK query()   │         │  ┌─────────────────┐ │ │
│  │ allowed_tools:│         │  │ SDK query()     │ │ │
│  │  [Bash, ...]  │         │  │ allowed_tools:  │ │ │
│  │ max_turns: 50 │         │  │  [Bash]         │ │ │
│  │ model: sonnet │         │  │ max_turns: 1    │ │ │
│  └───────┬──────┘         │  │ model: haiku-4-5│ │ │
│          │                 │  └────────┬────────┘ │ │
│          ▼                 │           ▼          │ │
│  ┌───────────────┐         │  ┌────────────────┐  │ │
│  │ Claude Code   │         │  │ Claude Code    │  │ │
│  │ CLI           │         │  │ CLI            │  │ │
│  │ (full agent   │         │  │ (1-turn test   │  │ │
│  │  session)     │         │  │  runner)       │  │ │
│  └───────┬──────┘         │  └────────┬───────┘  │ │
│          │                 │           │          │ │
│          ▼                 │           ▼          │ │
│  ┌───────────────┐         │  ┌────────────────┐  │ │
│  │ Bash tool     │  SAME   │  │ Bash tool      │  │ │
│  │ (user shell,  │◄═══════►│  │ (user shell,   │  │ │
│  │  full env)    │  ENV    │  │  full env)     │  │ │
│  └───────────────┘         │  └────────────────┘  │ │
│                            │                      │ │
│                            │  ┌─────────────────┐ │ │
│                            │  │ FALLBACK:       │ │ │
│                            │  │ subprocess.run()│ │ │
│                            │  │ (bare env)      │ │ │
│                            │  └─────────────────┘ │ │
│                            └──────────────────────┘ │
└─────────────────────────────────────────────────────┘
```

The key insight: **both Player and Coach use the same Claude Code CLI Bash tool**, which provides identical environment propagation. The Coach's invocation is constrained (1 turn, Haiku, Bash-only) to minimize cost and maximize determinism.

---

#### Recommendation: Option C as Default (Revised)

**Primary**: Option C (SDK Bash tool) — provides true 100% parity, zero maintenance, future-proof.

Since `claude-agent-sdk` is a **hard runtime requirement** for AutoBuild (enforced by `_require_sdk()` at both CLI entry points), the SDK is always available when CoachValidator executes. There is no scenario where CoachValidator runs without the SDK being importable. This eliminates the "optional dependency" concern entirely — Option C is not relying on something that might not be there.

**Configuration**: Add `coach_test_execution: "sdk" | "subprocess"` to `.guardkit/config.yaml`:
- `"sdk"` (default): Use SDK Bash tool for full Player/Coach environment parity
- `"subprocess"`: Force bare subprocess behavior (for users who explicitly want CI-like environment testing)

A `subprocess.run()` fallback within the SDK path is still prudent as defensive coding (e.g., if the SDK errors out mid-invocation), but this is an error-recovery mechanism, not a feature toggle for missing dependencies.

This addresses the philosophical question: the Coach should verify tests in the **same environment as the Player** by default. If users want CI-like bare-environment testing, they can explicitly configure `"subprocess"` mode. The system should not silently use a different environment than the Player — that's the root cause of this entire 18-turn failure.

**Regression safety**:
- SDK always available in AutoBuild context — no missing dependency risk
- Explicit `"subprocess"` mode preserves current behavior for users who want it
- Defensive fallback to subprocess on SDK invocation errors prevents breakage
- The `max_turns=1` constraint prevents runaway SDK sessions
- Using Haiku model keeps costs negligible

**Test plan for R5 (Option C)**:

| # | Test | Type | What it Validates |
|---|------|------|-------------------|
| 1 | `_run_tests_via_sdk()` with mocked SDK returning passing tests | Unit | ToolResultBlock with `is_error=False` → `tests_passed=True` |
| 2 | `_run_tests_via_sdk()` with mocked SDK returning failing tests | Unit | ToolResultBlock with `is_error=True` → `tests_passed=False` |
| 3 | `_run_tests_via_sdk()` with `content` as `list[dict]` | Unit | GAP-FIX #5: list content correctly extracted to string |
| 4 | `_run_tests_via_sdk()` with `content` as `None` | Unit | No crash, empty output handled |
| 5 | `_run_tests_via_sdk()` with `ResultMessage.is_error=True` | Unit | Session error → `tests_passed=False` with error message |
| 6 | `run_independent_tests()` SDK path success | Unit | SDK called, `IndependentTestResult` has all 4 required fields |
| 7 | `run_independent_tests()` SDK error → subprocess fallback | Unit | SDK raises `ProcessError` → falls back to subprocess |
| 8 | `run_independent_tests()` with `_coach_test_execution="subprocess"` | Unit | SDK NOT called, subprocess used directly |
| 9 | `_load_coach_config()` with `.guardkit/config.yaml` present | Unit | Reads `autobuild.coach.test_execution` |
| 10 | `_load_coach_config()` with no config file | Unit | Returns empty dict (default to "sdk") |
| 11 | `CoachValidator.__init__()` with new parameter | Unit | `_coach_test_execution` stored correctly |
| 12 | Event loop safety: no `RuntimeError` on `get_event_loop()` | Unit | GAP-FIX #9: try/except pattern works |
| 13 | Full `validate()` with SDK test path | Integration | End-to-end: validate() → run_independent_tests() → SDK → result |
| 14 | Data contract: `IndependentTestResult.to_dict()` output matches schema | Unit | All downstream consumers get expected fields |
| 15 | Regression: Replay TASK-DB-003 scenario with SDK path | Integration | SDK Bash tool runs pytest in full env → tests pass (or meaningful error) |

---

## Decision Matrix

| # | Recommendation | Impact | Effort | Risk | Regression Risk | Priority |
|---|----------------|--------|--------|------|-----------------|----------|
| R1 | Error context in feedback | High | Low | Low | Low | 1 |
| R2 | Normalize stall detection | High | Low | Low | Low | 2 |
| R3 | Fix duplicate path dedup | Medium | Low | Low | Low | 3 |
| R4 | Classify infra vs code | High | Medium | Medium | Medium | 4 |
| R5 | SDK Bash parity (Option C) | Critical | High | Low | Low | 5 |

## Implementation Plan

**Wave 1 (Quick wins — implement together)**: R1 + R2 + R3
- Single task, estimated 3-4 hours including tests
- Eliminates the symptoms: non-actionable feedback, stall detection gap, duplicate paths
- No architectural changes required
- All changes are backward-compatible

**Wave 2 (Enhancement)**: R4
- Single task, estimated 4-6 hours
- Prevents the infinite loop class of failures for infrastructure-dependent tests
- Requires adding `raw_output` field to `IndependentTestResult`

**Wave 3 (Environment parity — Option C)**: R5
- Single task, estimated 6-8 hours including tests
- Implements SDK Bash tool execution for Coach with defensive subprocess fallback
- Adds `coach_test_execution` config option (`"sdk"` default / `"subprocess"`)
- SDK is a hard runtime requirement for AutoBuild (enforced by `_require_sdk()`) — always available
- **No design decision needed** — SDK parity is the default, subprocess available as explicit opt-out
- This is the definitive fix for F1 (environment parity gap)

---

## Appendix A: Complete Turn-by-Turn Evidence

| Turn | Gates Pass? | Independent Tests | Failure Duration | Feedback Category | Test Files Detected | Detection Method |
|------|------------|-------------------|------------------|-------------------|--------------------|--------------------|
| 1 | Yes | Fail | 3.1s | test_verification | 2 (duplicated) | task_work_results |
| 2 | No (coverage) | Not run | — | coverage_not_met | — | — |
| 3 | Yes | Fail | 1.7s | test_verification | 1 | cumulative diff |
| 4 | Yes | Fail | 1.7s | test_verification | 1 | cumulative diff |
| 5 | Yes | Fail | 1.7s | test_verification | 1 | cumulative diff |
| 6 | Yes | Fail | 1.7s | test_verification | 1 | cumulative diff |
| 7 | Yes | Fail | 0.7s | test_verification | 4 (duplicated) | task_work_results |
| 8 | Yes | Fail | 1.9s | test_verification | 3 | cumulative diff |
| 9-17 | Yes | Fail | 1.7-1.9s | test_verification | 1-3 | cumulative diff |
| 18 | — | — | — | cancelled (timeout) | — | — |

**Key log lines**:
- Line 357: Turn 1 duplicate paths: `pytest /abs/path tests/users/test_users.py`
- Line 484: Turn 2 short-circuit: `coverage_met=False`
- Line 496: Turn 3 perspective reset (does not clear `_feedback_history`)
- Line 615: Turn 5 perspective reset (does not clear `_feedback_history`)
- Line 779: Turn 7 duplicate paths: 4 files (2 abs + 2 rel), different test files
- Line 1404: Turn 18 timeout: `Task TASK-DB-003 timed out after 2400s (40 min)`
- Line 1423: Cancellation: `Cancellation detected for TASK-DB-003 between Player and Coach at turn 18`

## Appendix B: Stall Detection State Trace

```
_feedback_history after each turn:

Turn 1:  [(sig_A, 0)]
         len=1 < threshold=3 → skip

Turn 2:  [(sig_A, 0), (sig_B, 0)]          sig_B = "coverage threshold not met"
         len=2 < threshold=3 → skip

Turn 3:  [(sig_A, 0), (sig_B, 0), (sig_C, 0)]
         recent = [sig_A, sig_B, sig_C]
         sigs = {sig_A, sig_B, sig_C}      3 different → skip

Turn 4:  [..., (sig_D, 0)]
         recent = [sig_B, sig_C, sig_D]
         sigs = {sig_B, sig_C, sig_D}      3 different → skip

Turn 5:  [..., (sig_E, 0)]
         recent = [sig_C, sig_D, sig_E]
         sigs = {sig_C, sig_D, sig_E}      3 different → skip

Turn 6:  [..., (sig_F, 0)]
         recent = [sig_D, sig_E, sig_F]    3 different → skip

Turn 7:  [..., (sig_G, 0)]                 sig_G = "test_foundation" not "test_users"
         recent = [sig_E, sig_F, sig_G]    3 different → skip

Turn 8:  [..., (sig_H, 0)]
         recent = [sig_F, sig_G, sig_H]    3 different → skip

...pattern continues to Turn 17. Stall detection NEVER fires.

WITH R2 FIX (normalized signatures):
Turn 1:  [(norm_test_fail, 0)]             len < 3 → skip
Turn 2:  [(norm_test_fail, 0), (norm_coverage, 0)]    len < 3 → skip
Turn 3:  [(norm_test_fail, 0), (norm_coverage, 0), (norm_test_fail, 0)]
         sigs = {norm_test_fail, norm_coverage}  2 different → skip
Turn 4:  [..., (norm_test_fail, 0)]
         recent = [(norm_coverage, 0), (norm_test_fail, 0), (norm_test_fail, 0)]
         sigs = {norm_coverage, norm_test_fail}  2 different → skip
Turn 5:  [..., (norm_test_fail, 0)]
         recent = [(norm_test_fail, 0), (norm_test_fail, 0), (norm_test_fail, 0)]
         sigs = {norm_test_fail}             1 signature!
         counts = [0, 0, 0]                 all same!
         counts[0] == 0                     zero progress!
         → return True ✅ STALL DETECTED AT TURN 5
```

This proves R2 would catch the stall after exactly Turn 5 (3 consecutive normalized-identical turns with 0 criteria), preventing 13 wasted turns.
