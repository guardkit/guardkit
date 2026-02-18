# Review Report: TASK-REV-CB30 (Revision 2 — Deep Trace)

## Executive Summary

The boot-wave2 fixes (TASK-BOOT-{B032, F632, 0F53, 754A, 99A5}) are **all deployed and visibly working**. Both R1 (requires_infrastructure propagation) and R2 (dependency-only install) are confirmed active in the evidence.

TASK-DB-003 stalls with `UNRECOVERABLE_STALL` due to a **dual-Python-installation PATH resolution bug**:

**Verified Root Cause**: The bootstrap installs `sqlalchemy` to the **Framework Python** (`/Library/Frameworks/Python.framework/Versions/3.14/`) via `sys.executable` → `/usr/local/bin/python3`. But the Coach's SDK test runner spawns a CLI process that inherits the user's `PATH` (from `~/.zshrc`: `export PATH="/opt/homebrew/bin:$PATH"`). When the CLI's Bash tool runs `pytest`, the shell resolves to `/opt/homebrew/bin/pytest`, which uses the **Homebrew Python** (`/opt/homebrew/opt/python@3.14/bin/python3.14`). The Homebrew Python does **NOT** have sqlalchemy installed. Result: `ModuleNotFoundError: No module named 'sqlalchemy'` during test collection (0.19 seconds).

**Actual error** (from `coach_turn_1.json`):
```
ModuleNotFoundError: No module named 'sqlalchemy'
2 errors in 0.19s
```

This is NOT a `ConnectionRefusedError` or DATABASE_URL issue. The initial review (Revision 1) incorrectly hypothesised environment variable propagation — the deep trace disproves that.

## Review Details

- **Mode**: Architectural Review
- **Depth**: Comprehensive (deep trace with source verification)
- **Task**: TASK-REV-CB30
- **Parent Review**: TASK-REV-C9E5
- **Related Tasks**: TASK-BOOT-{B032, F632, 0F53, 754A, 99A5}
- **Revision**: 2 (supersedes Revision 1)

## C4 Sequence Diagrams

### Diagram 1: Bootstrap → Test Execution — The Python Path Divergence

```
┌─────────────┐  ┌──────────────┐  ┌─────────────┐  ┌──────────────┐  ┌─────────────┐
│  User Shell  │  │ FeatureOrch  │  │  Bootstrap   │  │CoachValidator│  │  SDK CLI     │
│  (zsh)       │  │  (Python)    │  │  (Python)    │  │  (Python)    │  │  (Mach-O)    │
└──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘
       │                 │                 │                 │                 │
       │ guardkit auto.. │                 │                 │                 │
       │────────────────>│                 │                 │                 │
       │                 │                 │                 │                 │
       │  PATH includes:                   │                 │                 │
       │  /opt/homebrew/bin                │                 │                 │
       │  /Library/.../3.14/bin            │                 │                 │
       │  /usr/local/bin                   │                 │                 │
       │                 │                 │                 │                 │
       │                 │  bootstrap()    │                 │                 │
       │                 │────────────────>│                 │                 │
       │                 │                 │                 │                 │
       │                 │                 │ pip install      │                 │
       │                 │                 │ sqlalchemy       │                 │
       │                 │                 │ ───────────┐     │                 │
       │                 │                 │            │     │                 │
       │                 │                 │  sys.executable = /usr/local/bin/python3
       │                 │                 │  ═══> Installs to Framework Python  │
       │                 │                 │  /Library/.../3.14/lib/.../site-packages/
       │                 │                 │            │     │                 │
       │                 │                 │ <──────────┘     │                 │
       │                 │  ✓ bootstrapped │                 │                 │
       │                 │<────────────────│                 │                 │
       │                 │                 │                 │                 │
       │                 │                 │                 │                 │
       │                 │  Coach.validate()                 │                 │
       │                 │─────────────────────────────────>│                 │
       │                 │                 │                 │                 │
       │                 │                 │                 │ _start_infra()  │
       │                 │                 │                 │ ──────┐         │
       │                 │                 │                 │       │ docker  │
       │                 │                 │                 │       │ run pg  │
       │                 │                 │                 │       │         │
       │                 │                 │                 │ os.environ[     │
       │                 │                 │                 │ "DATABASE_URL"] │
       │                 │                 │                 │ = pg://...5433  │
       │                 │                 │                 │ <─────┘         │
       │                 │                 │                 │                 │
       │                 │                 │                 │ _run_tests_via_sdk()
       │                 │                 │                 │ query(prompt,   │
       │                 │                 │                 │   options)      │
       │                 │                 │                 │────────────────>│
       │                 │                 │                 │                 │
       │                 │                 │     SDK passes env={**os.environ} │
       │                 │                 │     PATH still has /opt/homebrew  │
       │                 │                 │     first from user's .zshrc      │
       │                 │                 │                 │                 │
       │                 │                 │                 │                 │
```

### Diagram 2: SDK CLI Bash Tool — The PATH Resolution Failure

```
┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐
│  SDK CLI     │  │  Haiku LLM   │  │ /bin/bash     │  │ pytest        │
│  (Mach-O)    │  │  (model)     │  │ (shell)       │  │ (resolved)    │
└──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └───────┬───────┘
       │                 │                 │                   │
       │ prompt: "Run    │                 │                   │
       │  pytest ..."    │                 │                   │
       │────────────────>│                 │                   │
       │                 │                 │                   │
       │                 │ Bash tool_use:  │                   │
       │                 │ "pytest tests/  │                   │
       │                 │ test_alembic_.. │                   │
       │                 │ -v --tb=short"  │                   │
       │<────────────────│                 │                   │
       │                 │                 │                   │
       │  spawn shell    │                 │                   │
       │  (inherits      │                 │                   │
       │   CLI env)      │                 │                   │
       │────────────────────────────────>│                   │
       │                 │                 │                   │
       │                 │   PATH lookup:  │                   │
       │                 │   1. /opt/homebrew/bin/pytest  ◄── FOUND FIRST
       │                 │   2. /Library/.../3.14/bin/pytest   │
       │                 │                 │                   │
       │                 │                 │ exec pytest       │
       │                 │                 │──────────────────>│
       │                 │                 │                   │
       │                 │                 │  #!/opt/homebrew/opt/python@3.14/bin/python3.14
       │                 │                 │  ═══> Uses HOMEBREW Python           │
       │                 │                 │  Homebrew site-packages does NOT     │
       │                 │                 │  have sqlalchemy installed           │
       │                 │                 │                   │
       │                 │                 │  ModuleNotFoundError:               │
       │                 │                 │  No module named 'sqlalchemy'       │
       │                 │                 │  2 errors in 0.19s                  │
       │                 │                 │<──────────────────│
       │                 │                 │                   │
       │  bash_is_error  │                 │                   │
       │  = True         │                 │                   │
       │<────────────────────────────────│                   │
       │                 │                 │                   │
```

### Diagram 3: Why the Subprocess Path Would Succeed

```
┌──────────────┐                          ┌──────────────┐
│CoachValidator│                          │ subprocess   │
│  (Python)    │                          │              │
└──────┬───────┘                          └──────┬───────┘
       │                                         │
       │  # Subprocess path (coach_validator.py:1225-1235)
       │  if test_cmd.startswith("pytest"):      │
       │    cmd = [sys.executable, "-m", "pytest"] + parts[1:]
       │    #     ^^^^^^^^^^^^^^                 │
       │    # = /usr/local/bin/python3           │
       │    # = Framework Python 3.14            │
       │    # HAS sqlalchemy in site-packages    │
       │                                         │
       │  subprocess.run(cmd, env=os.environ)    │
       │────────────────────────────────────────>│
       │                                         │
       │  /usr/local/bin/python3 -m pytest       │
       │  ═══> Framework Python ═══> HAS sqlalchemy
       │  ═══> Tests PASS                        │
       │                                         │
       │  ✓ tests_passed=True                    │
       │<────────────────────────────────────────│
       │                                         │
```

### Diagram 4: Conditional Approval 5-Condition Evaluation (Verified)

```
┌──────────────────────────────────────────────────────────────────────┐
│  CONDITIONAL APPROVAL CHECK (coach_validator.py:630-636)             │
│                                                                      │
│  conditional_approval = (                                            │
│      failure_class == "infrastructure"    ═══> TRUE  (line 320)     │
│      and failure_confidence == "high"     ═══> TRUE  (line 320)     │
│      and bool(requires_infra)             ═══> TRUE  (BOOT-B032 ✓)  │
│      and not docker_available             ═══> FALSE ◄── BLOCKS     │
│      and gates_status.all_gates_passed    ═══> TRUE  (line 312)     │
│  )                                                                   │
│                                                                      │
│  Result: FALSE — conditional approval does NOT fire                  │
│                                                                      │
│  This is CORRECT BEHAVIOR:                                           │
│  - Docker IS available (containers start at line 314)                │
│  - Conditional approval is designed for when Docker is unavailable   │
│  - The real fix is to make tests pass WITH Docker running (R5)       │
│                                                                      │
│  Note: The test failure is NOT about DATABASE_URL or Docker —        │
│  it's about sqlalchemy not being importable due to PATH resolution.  │
│  Even if conditional approval fired, it would be masking the real    │
│  bug rather than fixing it.                                          │
└──────────────────────────────────────────────────────────────────────┘
```

## Boot-Wave2 Deployment Verification

All 5 boot-wave2 tasks are confirmed deployed (all in `tasks/completed/`):

| Task | Title | Status | Evidence |
|------|-------|--------|----------|
| TASK-BOOT-B032 | Fix requires_infrastructure propagation | Completed | Docker starts at line 314 (was absent before) |
| TASK-BOOT-F632 | Dependency-only install for incomplete projects | Completed | Lines 169-175: sqlalchemy, asyncpg, alembic installed |
| TASK-BOOT-0F53 | State-aware hash persistence with retry | Completed | Inter-wave bootstrap runs (lines 168-176) |
| TASK-BOOT-754A | Diagnostic logging for conditional approval | Completed | `logger.debug` at line 620-628 — but at DEBUG level |
| TASK-BOOT-99A5 | Integration tests for requires_infrastructure | Completed | Tests for propagation logic exist |

## Findings

### Finding 1: Dual-Python PATH Resolution Mismatch (CRITICAL — Root Cause)

**Severity**: Critical — single root cause of the stall

**Actual Error** (verbatim from `coach_turn_1.json`):
```
ModuleNotFoundError: No module named 'sqlalchemy'
2 errors in 0.19s
```

**Evidence chain with source verification**:

1. User's `~/.zshrc` sets: `export PATH="/opt/homebrew/bin:$PATH"`
2. Two Python 3.14 installations exist:
   - **Framework**: `/Library/Frameworks/Python.framework/Versions/3.14/` (via `/usr/local/bin/python3`)
   - **Homebrew**: `/opt/homebrew/opt/python@3.14/` (via `/opt/homebrew/bin/python3`)
3. Bootstrap at [environment_bootstrap.py:225](guardkit/orchestrator/environment_bootstrap.py#L225) uses `sys.executable` → `/usr/local/bin/python3` → installs sqlalchemy to **Framework** site-packages
4. SDK transport at `subprocess_cli.py:346` passes `env={**os.environ, ...}` → CLI inherits PATH with `/opt/homebrew/bin` **first**
5. CLI's Bash tool runs `pytest tests/...` → shell resolves to `/opt/homebrew/bin/pytest`
6. `/opt/homebrew/bin/pytest` shebang: `#!/opt/homebrew/opt/python@3.14/bin/python3.14` → uses **Homebrew** Python
7. Homebrew Python does NOT have sqlalchemy → `ModuleNotFoundError`

**Verified facts**:
- `/opt/homebrew/bin/python3 -c "import sqlalchemy"` → `ModuleNotFoundError: No module named 'sqlalchemy'` (verified live)
- `/usr/local/bin/python3 -c "import sqlalchemy"` → `sqlalchemy 2.0.46` (verified live)
- `/opt/homebrew/bin/pytest` shebang: `#!/opt/homebrew/opt/python@3.14/bin/python3.14` (verified live)
- `/Library/Frameworks/Python.framework/Versions/3.14/bin/pytest` shebang resolves to Framework Python (verified live)

**Why the Player succeeds but the Coach fails**: The Player is an LLM (Sonnet) running in a separate SDK session. It may use `python3 -m pytest` instead of bare `pytest`, or install packages within its session. The Player's test execution is autonomous — it doesn't go through the same PATH resolution as the Coach's Bash tool prompt.

**Disproved hypotheses from Revision 1**:
- ~~SDK does not inherit `os.environ`~~ → **Disproved**: SDK source code at `subprocess_cli.py:346-351` explicitly merges `{**os.environ, ...}`
- ~~`DATABASE_URL` not passed to subprocess~~ → **Disproved**: `os.environ` mutation happens BEFORE `query()` call; SDK snapshots env at `connect()` time
- ~~Docker readiness timing issue~~ → **Disproved**: Error is import failure (0.19s), not connection timeout
- ~~`ConnectionRefusedError`~~ → **Disproved**: Actual error is `ModuleNotFoundError`

### Finding 2: Subprocess Path Has Built-in Protection (INFORMATIONAL)

**Severity**: Informational — explains why the fix works

The subprocess test execution path at [coach_validator.py:1225-1227](guardkit/orchestrator/quality_gates/coach_validator.py#L1225-L1227) uses:
```python
if test_cmd.startswith("pytest"):
    parts = test_cmd.split()
    cmd = [sys.executable, "-m", "pytest"] + parts[1:]
```

`sys.executable` is `/usr/local/bin/python3` (Framework Python), which **bypasses PATH resolution entirely**. This path would succeed because it forces the same Python that has sqlalchemy installed. The comment at lines 1222-1224 explicitly states this design intent:

> For Python/pytest commands, use sys.executable to eliminate PATH ambiguity. This ensures the same interpreter as the orchestrator process is used, avoiding discrepancies when the shell resolves `python3` via PATH.

The irony is that the `"sdk"` execution mode was introduced for "environment parity" with the Player, but it actually **breaks** parity by using PATH-resolved `pytest` instead of `sys.executable`-pinned `python3 -m pytest`.

### Finding 3: Diagnostic Logging at DEBUG Level Not Visible (MODERATE)

**Severity**: Moderate — prevents rapid debugging

**Evidence**: Line 1 confirms `GUARDKIT_LOG_LEVEL=DEBUG` is set. The `conditional_approval check` log at [coach_validator.py:620](guardkit/orchestrator/quality_gates/coach_validator.py#L620) uses `logger.debug()`. This log line is NOT visible in 671 lines of evidence output despite running with DEBUG level.

The absence suggests the Python logging configuration doesn't propagate `GUARDKIT_LOG_LEVEL` to the `coach_validator` logger's handler, or the handler's threshold is above DEBUG.

### Finding 4: Conditional Approval Logic is Correct But Inapplicable (INFORMATIONAL)

**Severity**: Informational — not a bug

The 5-condition AND at [coach_validator.py:630-636](guardkit/orchestrator/quality_gates/coach_validator.py#L630-L636):
```python
conditional_approval = (
    failure_class == "infrastructure"        # True (line 320)
    and failure_confidence == "high"         # True (line 320)
    and bool(requires_infra)                 # True (TASK-BOOT-B032 ✓)
    and not docker_available                 # FALSE — Docker IS available
    and gates_status.all_gates_passed        # True (line 312)
)
```

`not docker_available` evaluates to `False` because Docker IS available. This is correct — conditional approval is for when Docker is unavailable. Even if conditional approval fired, it would mask the real bug (PATH resolution) rather than fix it.

### Finding 5: Docker Container Lifecycle is Correct (INFORMATIONAL)

Docker starts, readiness-checks, stops correctly across all 3 turns. The infrastructure is working as intended. The failure is at the Python import layer, not the database connection layer.

### Finding 6: Test Failure Timing Confirms Import Error (INFORMATIONAL)

Tests fail in 0.15-0.19 seconds during **collection** (not execution). The 5-7 second total includes SDK overhead (CLI startup, Haiku model inference, response streaming). This timing is consistent with a failed import, not a network timeout.

## Recommendations

### R5: Force `sys.executable`-pinned pytest in SDK test path (CRITICAL — Priority 1)

**Problem**: The SDK Bash tool runs bare `pytest` which resolves via PATH to the homebrew Python, which lacks sqlalchemy.

**Preferred fix**: Modify the prompt in `_run_tests_via_sdk()` to use `python3 -m pytest` with the explicit interpreter path:

```python
# At coach_validator.py:1012
# Replace bare pytest with sys.executable-pinned invocation
if test_cmd.startswith("pytest"):
    parts = test_cmd.split()
    test_cmd = f"{sys.executable} -m pytest {' '.join(parts[1:])}"

prompt = f"Run the following test command and report the output:\n\n```bash\n{test_cmd}\n```\n\nProvide the full test output."
```

This ensures the SDK Bash tool runs the same Python as the orchestrator, matching the subprocess path's existing protection at line 1225-1227.

**Alternative fix (Option B)**: Switch to subprocess execution when `requires_infra` is non-empty:

```python
# At coach_validator.py:1194, inside run_independent_tests try block
if self._coach_test_execution == "sdk" and not requires_infra:
    # SDK path only when no infrastructure dependencies
    ...
else:
    # Subprocess path: uses sys.executable, bypasses PATH
    ...
```

**Alternative fix (Option C)**: Install packages to ALL Python installations during bootstrap:

```python
# At environment_bootstrap.py:225 — also install to homebrew Python
# This is fragile and not recommended
```

### R6: Escalate Conditional Approval Diagnostic Log (MODERATE — Priority 2)

Change [coach_validator.py:620](guardkit/orchestrator/quality_gates/coach_validator.py#L620) from `logger.debug` to `logger.warning`.

### R7: Add Python Interpreter Consistency Check (LOW — Priority 3)

Add a diagnostic log at the start of `run_independent_tests()` that logs:
```python
logger.info(
    "Test execution environment: sys.executable=%s, "
    "which pytest=%s, coach_test_execution=%s",
    sys.executable,
    shutil.which("pytest"),
    self._coach_test_execution,
)
```

This would immediately reveal the PATH discrepancy in future runs.

## Decision Matrix

| Option | Impact | Effort | Risk | Recommendation |
|--------|--------|--------|------|----------------|
| R5 (pin sys.executable in SDK prompt) | High | Low (~3 lines) | Very Low | **Recommended** |
| R5 Option B (subprocess for infra tasks) | High | Low (~5 lines) | Low | Good alternative |
| R6 (escalate log level) | Medium | Trivial (1 line) | None | Do alongside R5 |
| R7 (interpreter consistency log) | Low | Low (3 lines) | None | Do alongside R5 |

## Architecture Score

| Principle | Score | Notes |
|-----------|-------|-------|
| SOLID - SRP | 8/10 | Coach validator handles too many concerns (test execution, Docker lifecycle, approval logic) |
| SOLID - OCP | 7/10 | Test execution strategy is configurable but environment handling is not |
| DRY | 7/10 | The sys.executable pinning at line 1225 should also apply to the SDK path but doesn't |
| YAGNI | 9/10 | No unnecessary abstractions |
| **Overall** | **78/100** | Architecture is sound; the bug is a cross-technology-seam environment consistency gap |

## Deep Trace Verification Summary

| Hypothesis | Status | Method |
|------------|--------|--------|
| SDK does not inherit os.environ | **Disproved** | Read SDK source: `subprocess_cli.py:346` uses `{**os.environ, ...}` |
| DATABASE_URL not set before SDK query | **Disproved** | Code trace: `_start_infrastructure_containers()` runs before `_run_tests_via_sdk()` with zero intervening code |
| Docker readiness timing issue | **Disproved** | Error is `ModuleNotFoundError` (import), not `ConnectionRefusedError` (network) |
| `ConnectionRefusedError` | **Disproved** | Actual error: `ModuleNotFoundError: No module named 'sqlalchemy'` (from `coach_turn_1.json`) |
| Dual-Python PATH resolution | **Confirmed** | Verified: homebrew pytest shebang uses homebrew Python; homebrew Python lacks sqlalchemy; user's .zshrc prepends /opt/homebrew/bin to PATH |
| Conditional approval logic bug | **Disproved** | Code trace: `not docker_available` is correctly `False` when Docker is available; this is by design |
| Boot-wave2 tasks not deployed | **Disproved** | All 5 tasks in `tasks/completed/`; evidence shows R1 and R2 active |

## Implementation Summary

All three recommendations were implemented in [coach_validator.py](guardkit/orchestrator/quality_gates/coach_validator.py) per user feedback adjusting priorities from the original review:

### R5 Option B: Force Subprocess for Infrastructure Tasks (CRITICAL)

User selected Option B over prompt pinning: *"removes the LLM from the test execution loop entirely, saves ~6s per test execution, eliminates PATH issues structurally."*

**Change**: Added `use_sdk` guard at ~line 1194 that checks `not requires_infra` before allowing the SDK path. When `requires_infra` is non-empty, tests are forced through the subprocess path which uses `sys.executable` (bypassing PATH entirely).

```python
use_sdk = (
    self._coach_test_execution == "sdk"
    and not requires_infra
)
```

Also added infrastructure-specific log message when subprocess is chosen due to this guard.

### R7: Interpreter Consistency Diagnostic (LOW)

**Change**: Added diagnostic log at the start of `run_independent_tests()` (~line 1158) that reports `sys.executable`, `shutil.which("pytest")`, and `coach_test_execution`. This immediately reveals PATH discrepancies in future runs.

### R6: Escalate Conditional Approval Log (MODERATE)

User adjusted: `logger.info` instead of originally recommended `logger.warning` — *"logger.warning is too aggressive for a diagnostic that fires on every successful run too."*

**Change**: Line 620 changed from `logger.debug` to `logger.info`.

### Test Verification

All 584 coach-related tests pass: **508 passed, 76 skipped, 0 failures** (105.92s).

### Unaddressed Items (Future Work)

1. **Player PATH vulnerability**: Whether the Player SDK session has the same dual-Python vulnerability is unverified. User flagged: *"That 'may' is doing a lot of work."*
2. **Dual-Python machine hygiene**: Common on macOS with both `python.org` installer and Homebrew. No GuardKit-level fix recommended — the subprocess path bypass is sufficient.

## Appendix

### Python Installation Map (This Machine)

```
/usr/local/bin/python3
  → /Library/Frameworks/Python.framework/Versions/3.14/bin/python3
  → site-packages: /Library/.../3.14/lib/python3.14/site-packages/
  → HAS sqlalchemy 2.0.46 ✓
  → HAS pytest 9.0.2 ✓
  → This is where bootstrap installs packages (sys.executable)

/opt/homebrew/bin/python3
  → /opt/homebrew/opt/python@3.14/bin/python3.14
  → site-packages: /opt/homebrew/lib/python3.14/site-packages/
  → NO sqlalchemy ✗
  → HAS pytest 8.4.2 (different version!) ✓
  → This is what the SDK's Bash tool resolves to (via PATH)
```

### Timeline of Evidence

| Line | Event |
|------|-------|
| 1 | `GUARDKIT_LOG_LEVEL=DEBUG` set |
| 32-35 | Initial bootstrap: fastapi, uvicorn, pydantic-settings, structlog |
| 140-149 | TASK-DB-001: APPROVED (1 turn) |
| 169-175 | Inter-wave bootstrap: adds sqlalchemy (to Framework Python), asyncpg, alembic |
| 314 | Docker container started for postgresql |
| 315 | `DATABASE_URL` set in os.environ |
| 316 | Tests dispatched via SDK → CLI Bash tool runs `pytest` → resolves to homebrew pytest |
| 317 | `Using bundled Claude Code CLI` — fresh CLI process inherits PATH with /opt/homebrew/bin first |
| 318 | SDK tests failed in 6.6s (pytest collection: 0.19s, SDK overhead: ~6.4s) |
| 319 | Docker container stopped |
| 320 | Classification: infrastructure, confidence: high |
| 526-538 | TASK-DB-002: APPROVED (2 turns) |
| 591-592 | Feedback stall detected (sig=f229025b, 3 turns, 0 criteria) |
| 595-614 | TASK-DB-003: UNRECOVERABLE_STALL |

### Key Source Files

| File | Role | Critical Lines |
|------|------|----------------|
| [coach_validator.py](guardkit/orchestrator/quality_gates/coach_validator.py) | Test execution, conditional approval | 1012 (SDK prompt), 1225-1227 (subprocess sys.executable pin), 607-768 (approval), 1305-1342 (Docker lifecycle) |
| [docker_fixtures.py](guardkit/orchestrator/docker_fixtures.py) | Docker recipes | 22-51 (fixtures), 55-91 (start commands) |
| [autobuild.py](guardkit/orchestrator/autobuild.py) | Orchestration | 3594-3598 (task dict with _docker_available) |
| [environment_bootstrap.py](guardkit/orchestrator/environment_bootstrap.py) | Dependency install | 225 (sys.executable for pip), 614-707 (bootstrap) |
| `subprocess_cli.py` (SDK) | CLI transport | 346-351 (env={**os.environ, ...}) |
| `~/.zshrc` | User shell config | `export PATH="/opt/homebrew/bin:$PATH"` |
