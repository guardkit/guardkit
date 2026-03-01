# Review Report: TASK-REV-A327 (Revised — Deep Dive)

## Executive Summary

TASK-SAD-002 (Update ArchitectureDecision dataclass, complexity=3) timed out after 2340s during FEAT-E4F5 Wave 1 despite **completing all work successfully**. Deep analysis across all technology boundaries reveals **three distinct bugs** at integration seams, not a single root cause:

1. **Primary**: SDK stream hang — missing `break` after `ResultMessage` in the task-work invocation path (agent_invoker.py)
2. **Secondary**: State recovery information loss — player report test data ignored when CoachVerifier times out (state_tracker.py)
3. **Tertiary**: macOS subprocess cleanup disabled — `_kill_child_claude_processes()` is Linux-only, leaving zombie SDK processes on macOS

**Severity**: High — this class of bug silently wastes compute, fails working tasks, blocks downstream waves, and leaves orphan processes.

## Review Details
- **Mode**: Root Cause Analysis (debugging/investigation)
- **Depth**: Comprehensive (deep-dive revision with C4 diagrams)
- **Source**: `docs/reviews/system-arch-design-commands/run_1.md`

---

## C4 Diagrams

### Diagram 1: System Context — Feature Orchestration

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        FEAT-E4F5 Feature Run                           │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │              FeatureOrchestrator (Python, asyncio)               │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐                        │  │
│  │  │ SAD-001  │ │ SAD-002  │ │ SAD-003  │  asyncio.gather()      │  │
│  │  │ C=4      │ │ C=3      │ │ C=5      │  + to_thread()        │  │
│  │  └────┬─────┘ └────┬─────┘ └────┬─────┘                        │  │
│  └───────┼─────────────┼───────────┼───────────────────────────────┘  │
│          │             │           │                                    │
│  ┌───────▼─────────────▼───────────▼───────────────────────────────┐  │
│  │        AutoBuildOrchestrator (1 per task, own thread)           │  │
│  │        └─ AgentInvoker (1 per task, lazy-init)                  │  │
│  └───────┬─────────────┬───────────┬───────────────────────────────┘  │
│          │             │           │                                    │
│  ════════╪═════════════╪═══════════╪════════  PROCESS BOUNDARY  ═════  │
│          │             │           │                                    │
│  ┌───────▼──┐  ┌───────▼──┐  ┌───────▼──┐                            │
│  │ Claude   │  │ Claude   │  │ Claude   │  SDK subprocess (Node.js) │
│  │ CLI #1   │  │ CLI #2   │  │ CLI #3   │  stdin/stdout/stderr      │
│  └──────────┘  └──────────┘  └──────────┘                            │
│                      │                                                  │
│  ════════════════════╪══════════════════════  FILESYSTEM BOUNDARY ═══  │
│                      │                                                  │
│  ┌───────────────────▼─────────────────────────────────────────────┐  │
│  │           Shared Worktree: .guardkit/worktrees/FEAT-E4F5       │  │
│  │           (all 3 tasks read/write same directory)               │  │
│  └─────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

### Diagram 2: Sequence — Normal SDK Stream Lifecycle (SAD-001, SAD-003)

```
AgentInvoker          SDK query()         _read_messages()      CLI Subprocess
     │                     │                     │                     │
     │  async for message  │                     │                     │
     │────────────────────>│  connect()          │                     │
     │                     │────────────────────>│  spawn process      │
     │                     │                     │────────────────────>│
     │                     │                     │                     │
     │                     │   start()           │                     │
     │                     │────────────────────>│  _read_messages()   │
     │                     │                     │  (background task)  │
     │                     │                     │                     │
     │  AssistantMessage   │  ToolUseBlock       │  stdout JSON line   │
     │<────────────────────│<────────────────────│<────────────────────│
     │  (log: ToolUseBlock │                     │                     │
     │   Write/Edit/Read)  │                     │                     │
     │                     │                     │                     │
     │  ... 27-34 turns... │                     │                     │
     │                     │                     │                     │
     │  ResultMessage      │  {"type":"result"}  │  stdout JSON line   │
     │<────────────────────│<────────────────────│<────────────────────│
     │  (log: SDK          │                     │                     │
     │   completed: turns) │                     │                     │
     │                     │                     │                     │
     │  *** NO BREAK ***   │                     │  process.exit(0)    │
     │  loop continues     │                     │─────────X           │
     │  waiting...         │                     │                     │
     │                     │                     │  stdout EOF          │
     │                     │                     │<────────────────────│
     │                     │                     │                     │
     │                     │  {"type":"end"}     │  _read_messages()    │
     │  StopAsyncIteration │<────────────────────│  finally block       │
     │<────────────────────│                     │  sends "end"         │
     │                     │                     │                     │
     │  loop exits         │  close()            │                     │
     │  (natural end)      │────────────────────>│  cleanup             │
     │                     │                     │                     │
     ▼ SUCCESS             ▼                     ▼                     ▼

     Total time: ~5 minutes (subprocess exits cleanly → stream closes)
```

### Diagram 3: Sequence — HUNG SDK Stream (SAD-002 — THE BUG)

```
AgentInvoker          SDK query()         _read_messages()      CLI Subprocess
     │                     │                     │                     │
     │  async for message  │                     │                     │
     │────────────────────>│  connect()          │                     │
     │                     │────────────────────>│  spawn process      │
     │                     │                     │────────────────────>│
     │                     │                     │                     │
     │  ... 33 turns of    │                     │                     │
     │  Edit/Write/Bash... │                     │                     │
     │                     │                     │                     │
     │  ResultMessage      │  {"type":"result"}  │  stdout JSON line   │
     │<────────────────────│<────────────────────│<────────────────────│
     │  (T+480s)           │                     │                     │
     │  log: SDK completed │                     │                     │
     │                     │                     │                     │
     │  *** NO BREAK ***   │                     │  subprocess hangs   │
     │  loop continues     │                     │  (no clean exit)    │
     │  ....               │                     │  stdout stays open  │
     │                     │                     │                     │
     │  HEARTBEAT          │  waiting for        │  blocked on         │
     │  (30s interval)     │  next message       │  async for stdout   │
     │  510s... 540s...    │  (stream open)      │  (no EOF)           │
     │  ...                │                     │                     │
     │  2310s...           │                     │                     │
     │                     │                     │                     │
     │  ┌──────────────┐   │                     │                     │
     │  │asyncio       │   │                     │                     │
     │  │.timeout      │   │                     │                     │
     │  │fires at      │   │                     │                     │
     │  │2340s         │   │                     │                     │
     │  └──────┬───────┘   │                     │                     │
     │         │           │                     │                     │
     │  TimeoutError       │                     │                     │
     │<────────┘           │                     │                     │
     │                     │                     │                     │
     │  SDKTimeoutError    │  (query.close()     │  (subprocess may    │
     │  raised to caller   │   NOT called —      │   remain running    │
     │                     │   no finally block   │   as zombie)        │
     │                     │   reached before     │                     │
     │                     │   timeout)           │                     │
     ▼ TIMEOUT (false)     ▼                     ▼                     ▼

     Wasted time: 1860 seconds (31 minutes of hanging after completion)
```

### Diagram 4: Sequence — State Recovery After Timeout

```
AutoBuildOrchestrator     StateTracker        state_detection    coach_verification
     │                        │                     │                     │
     │  _attempt_state_       │                     │                     │
     │  recovery()            │                     │                     │
     │───────────────────────>│                     │                     │
     │                        │                     │                     │
     │                        │  Layer 1: Load      │                     │
     │                        │  player_turn_1.json │                     │
     │                        │  ✓ LOADED (66 tests,│                     │
     │                        │   99% coverage)     │                     │
     │                        │                     │                     │
     │                        │  Layer 2: Git       │                     │
     │                        │  detect_git_changes │                     │
     │                        │────────────────────>│                     │
     │                        │  ✓ 3 files changed  │                     │
     │                        │<────────────────────│                     │
     │                        │                     │                     │
     │                        │  Layer 3: Tests     │                     │
     │                        │  detect_test_results│                     │
     │                        │────────────────────>│                     │
     │                        │                     │  CoachVerifier      │
     │                        │                     │  ._run_tests()      │
     │                        │                     │────────────────────>│
     │                        │                     │                     │
     │                        │                     │         ┌───────────┤
     │                        │                     │         │subprocess │
     │                        │                     │         │.run()     │
     │                        │                     │         │pytest ... │
     │                        │                     │         │           │
     │                        │                     │         │TIMEOUT    │
     │                        │                     │         │after 120s │
     │                        │                     │         └───────────┤
     │                        │                     │                     │
     │                        │                     │  TestResult(        │
     │                        │                     │    passed=False,    │
     │                        │                     │    test_count=0)    │
     │                        │                     │<────────────────────│
     │                        │                     │                     │
     │                        │  TestResultsSummary │                     │
     │                        │  (tests_run=False,  │                     │
     │                        │   test_count=0)     │                     │
     │                        │<────────────────────│                     │
     │                        │                     │                     │
     │                        │  _state_from_       │                     │
     │                        │  player_report()    │                     │
     │                        │                     │                     │
     │                        │  ┌──────────────────────────────┐        │
     │                        │  │ BUG: test_count logic        │        │
     │                        │  │                              │        │
     │                        │  │ test_count = (               │        │
     │                        │  │   test_results.test_count    │ = 0    │
     │                        │  │   if test_results.tests_run  │ = False│
     │                        │  │   else 0  ← ALSO ZERO       │        │
     │                        │  │ )                            │        │
     │                        │  │                              │        │
     │                        │  │ player_report["test_count"]  │        │
     │                        │  │ = 66 ← NEVER READ           │        │
     │                        │  └──────────────────────────────┘        │
     │                        │                     │                     │
     │  WorkState(            │                     │                     │
     │    files_modified=3,   │                     │                     │
     │    test_count=0,  ✗    │                     │                     │
     │    tests_passed=False) │                     │                     │
     │<───────────────────────│                     │                     │
     │                        │                     │                     │
     │  Synthetic report:     │                     │                     │
     │  "2 files, 0 tests"   │                     │                     │
     │  (should be "66 tests")│                     │                     │
     ▼                        ▼                     ▼                     ▼
```

### Diagram 5: Component — Technology Boundary Map (Where Bugs Live)

```
┌──────────────────────────────────────────────────────────────────────────┐
│  PYTHON PROCESS (GuardKit Orchestrator)                                  │
│                                                                          │
│  ┌─────────────────────┐     ┌──────────────────────┐                   │
│  │ feature_orchestrator │     │   autobuild.py       │                   │
│  │                     │     │                      │                   │
│  │ asyncio.gather()    │────>│ AutoBuildOrchestrator│                   │
│  │ + to_thread()       │     │ (1 per task)         │                   │
│  │                     │     │                      │                   │
│  │ task_timeout=2400s  │     │ _attempt_state_      │                   │
│  └─────────────────────┘     │  recovery()    ──────┼──── BUG #2       │
│                               └──────────┬───────────┘    (test_count   │
│                                          │                 info loss)   │
│                               ┌──────────▼───────────┐                  │
│                               │  agent_invoker.py    │                  │
│                               │                      │                  │
│                               │ _invoke_task_work_   │                  │
│                               │  implement()         │                  │
│                               │                      │                  │
│                               │ async for message    │                  │
│                               │   in query():  ──────┼──── BUG #1      │
│                               │                      │    (no break     │
│                               │ _kill_child_claude_  │     after        │
│                               │  processes()   ──────┼──── BUG #3      │
│                               │                      │    (macOS skip) │
│                               └──────────┬───────────┘                  │
│                                          │                              │
│  ════════════════════════════════════════╪═══════  SEAM 1: SDK API ════ │
│                                          │                              │
│  ┌───────────────────────────────────────▼──────────────────────────┐   │
│  │  claude_agent_sdk (Python package)                               │   │
│  │                                                                  │   │
│  │  query() → InternalClient.process_query()                        │   │
│  │  └─ Query._read_messages() (background asyncio task)             │   │
│  │  └─ Query.receive_messages() (user-facing async iterator)        │   │
│  │  └─ SubprocessCLITransport (manages subprocess I/O)              │   │
│  │                                                                  │   │
│  │  Signal chain: ResultMessage → "end" → StopAsyncIteration        │   │
│  │  Requires: subprocess exit → stdout EOF → _read_messages exit    │   │
│  └──────────────────────────────────┬───────────────────────────────┘   │
│                                     │                                    │
│  ═══════════════════════════════════╪═══════  SEAM 2: PROCESS I/O ════ │
│                                     │                                    │
│  ┌──────────────────────────────────▼───────────────────────────────┐   │
│  │  Claude Code CLI (Node.js subprocess)                            │   │
│  │                                                                  │   │
│  │  stdin  ← prompt JSON                                            │   │
│  │  stdout → stream-json messages (AssistantMsg, ToolUse, Result)   │   │
│  │  stderr → diagnostic output                                      │   │
│  │                                                                  │   │
│  │  HANG POINT: If process doesn't exit after writing ResultMessage │   │
│  │  then stdout stays open → _read_messages blocks → stream hangs   │   │
│  └──────────────────────────────────┬───────────────────────────────┘   │
│                                     │                                    │
│  ═══════════════════════════════════╪═══════  SEAM 3: FILESYSTEM ═════ │
│                                     │                                    │
│  ┌──────────────────────────────────▼───────────────────────────────┐   │
│  │  Shared Worktree + Coach Verification                            │   │
│  │                                                                  │   │
│  │  3 tasks write concurrently (no file locking)                    │   │
│  │  CoachVerifier subprocess: pytest with 120s timeout              │   │
│  │  State recovery: re-runs full test suite (not scoped)            │   │
│  └──────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────┘

BUG #1 (SEAM 1): agent_invoker.py:3971-3975
    No break after ResultMessage in async for loop.
    Stream hangs if subprocess doesn't cleanly exit.

BUG #2 (SEAM 3): state_tracker.py:376-380
    test_count from player_report.json ignored.
    Falls back to CoachVerifier result (0 on timeout).
    Both code paths yield test_count=0.

BUG #3 (SEAM 2): agent_invoker.py:799-815
    _kill_child_claude_processes() checks for /proc (Linux only).
    On macOS: returns with warning, no cleanup.
    Zombie subprocess may persist holding stdout open.
```

### Diagram 6: Sequence — Parallel Task Lifecycle Interaction

```
Time(s)  SAD-001 (C=4)      SAD-002 (C=3)       SAD-003 (C=5)       Feature Orch
  0      │ SDK start         │ SDK start          │ SDK start          │ gather()
         │ timeout=2520s     │ timeout=2340s      │ timeout=2700s      │
         │                   │                    │                    │
  90     │ Edit,Edit         │ Edit,Edit          │ Write,Write        │
         │                   │                    │                    │
  270    │ SDK done(27t)     │                    │                    │
  280    │ Message summary   │                    │                    │
  300    │ Player complete   │ ... working ...    │ ... working ...    │
         │                   │                    │                    │
  310    │ Coach start       │                    │                    │
  320    │ Coach test(13s)   │                    │ Write              │
  330    │ Coach APPROVED    │                    │ SDK done(34t)      │
         │                   │                    │ Message summary    │
  340    │ Checkpoint ✓      │                    │ Player complete    │
         │ ════ DONE ════    │                    │                    │
         │                   │                    │ Coach start        │
  350    │                   │                    │ Coach test(13s)    │
  360    │                   │                    │ Coach APPROVED     │
  370    │                   │                    │ Checkpoint ✓       │
         │                   │                    │ ════ DONE ════     │
         │                   │                    │                    │
  480    │                   │ SDK done(33t)      │                    │
         │                   │ log: "SDK          │                    │
         │                   │  completed:        │                    │
         │                   │  turns=33"         │                    │
         │                   │                    │                    │
         │                   │ *** STREAM HANGS ***                    │
         │                   │ (subprocess not    │                    │
         │                   │  exiting)          │                    │
         │                   │                    │                    │
  510    │                   │ heartbeat...       │                    │
  540    │                   │ heartbeat...       │                    │
   :     │                   │    :               │                    │
   :     │                   │    : (no tool      │                    │
   :     │                   │    :  activity)    │                    │
   :     │                   │    :               │                    │
 2310    │                   │ heartbeat...       │                    │
 2340    │                   │ ╔═══════════╗      │                    │
         │                   │ ║ TIMEOUT   ║      │                    │
         │                   │ ║ (asyncio) ║      │                    │
         │                   │ ╚═══════════╝      │                    │
         │                   │                    │                    │
 2340    │                   │ State recovery     │                    │
  -      │                   │ → git: 3 files ✓   │                    │
 2400    │                   │ → player rpt: ✓    │                    │
         │                   │ → tests: TIMEOUT   │                    │
         │                   │   (120s, 0 tests)  │                    │
         │                   │                    │                    │
 2400    │                   │ Feature timeout    │                    │ task_timeout
         │                   │ ════ FAILED ════   │                    │ = 2400s
         │                   │                    │                    │
 2400    │ ✓ SUCCESS         │ ✗ TIMEOUT          │ ✓ SUCCESS          │ Wave 1
         │                   │                    │                    │ result
         │                   │                    │                    │
         │                   │                    │                    │ stop_on_
         │                   │                    │                    │ failure=True
         │                   │                    │                    │ → STOP
```

---

## Deep-Dive Findings

### Finding 1: SDK Stream Hang After ResultMessage (ROOT CAUSE — CONFIRMED)

**Log attribution verified**: The `SDK completed: turns=33` at log line 335 is confirmed to belong to **TASK-SAD-002** based on:
- Progress bar timestamp `.218Z` matches TASK-SAD-002's consistent identifier
- Line 334 (immediately before): `[TASK-SAD-002] ToolUseBlock Write`
- Line 336 (immediately after): `[TASK-SAD-002] task-work implementation in progress... (510s elapsed)`
- TASK-SAD-001 completed with `turns=27` at line 208
- TASK-SAD-003 completed with `turns=34` at line 271

**SDK internal lifecycle traced** (via claude_agent_sdk source):

The stream termination chain requires 5 sequential steps:
1. CLI subprocess writes `{"type":"result"}` to stdout
2. CLI subprocess calls `process.exit(0)` → stdout closes
3. `SubprocessCLITransport.read_messages()` hits stdout EOF
4. `Query._read_messages()` background task exits `async for` loop → sends `{"type":"end"}` via memory channel
5. `Query.receive_messages()` receives "end" → `break` → loop exits naturally

**Failure mode**: If step 2 doesn't happen (subprocess doesn't exit cleanly), steps 3-5 never trigger. The `async for message in query()` loop in `agent_invoker.py:3911` blocks indefinitely on the SDK's memory channel, waiting for either a new message or the "end" signal that never comes.

**Why a `break` after `ResultMessage` is safe and correct**: The `ResultMessage` (SDK type `{"type":"result"}`) is the terminal message in every Claude Agent SDK conversation. No further `AssistantMessage`, `ToolUseBlock`, or `ToolResultBlock` will follow. The SDK itself uses `_first_result_event.set()` internally to signal that the result has been received (query.py:210-211). Breaking after `ResultMessage` is semantically correct and matches the SDK's own understanding of conversation completion.

**Code path** (`agent_invoker.py:3971-3975`):
```python
elif isinstance(message, ResultMessage):
    result_count += 1
    sdk_turns_used = message.num_turns
    logger.info(f"SDK completed: turns={message.num_turns}")
    # NO break statement — loop continues until stream closes
```

**Three invocation paths affected**:
| Method | Line | Has break? | Risk |
|--------|------|-----------|------|
| `_invoke_task_work_implement()` | 3911 | No | **Active** (SAD-002 hit this) |
| `_invoke_with_role()` | 1744 | No | Latent (direct Player/Coach) |
| `_invoke_player_direct()` | ~3050 | No | Latent (direct mode Player) |

### Finding 2: State Recovery Information Loss (SECONDARY BUG — CONFIRMED)

**Root cause in state_tracker.py:376-380**: When the player report is loaded successfully but CoachVerifier test re-run times out, the test count from the player report is **silently discarded**.

```python
# state_tracker.py:376-380 — THE BUG
test_count = (
    test_results.test_count        # ← 0 (CoachVerifier timed out)
    if test_results and test_results.tests_run  # ← False (timeout)
    else 0                          # ← Fallback is ALSO 0
)
# player_report["test_count"] = 66 ← NEVER READ
```

**Information flow traced**:
1. Player writes `player_turn_1.json` with `"test_count": 66, "tests_passed": true`
2. State tracker loads JSON successfully (`_load_player_report`)
3. State tracker calls `detect_test_results()` → `CoachVerifier._run_tests()`
4. CoachVerifier runs `subprocess.run(["pytest", ...], timeout=120)` on full worktree
5. Subprocess times out → `TestResult(passed=False, test_count=0)`
6. `_state_from_player_report()` prioritises the timed-out test_results over the loaded player_report
7. Both branches of the ternary yield `test_count=0`
8. Player's `"test_count": 66` is never extracted

**Why the coach verification timed out (120s)**: The state recovery ran pytest on the entire shared worktree (not scoped to TASK-SAD-002's test files). At this point, TASK-SAD-001 and TASK-SAD-003 had already committed checkpoint commits (680fedca, 4ea670db), potentially adding test files. Running the full suite of 66+ tests from all three tasks in 120s is marginal, and the shared worktree state may have been inconsistent.

### Finding 3: macOS Subprocess Cleanup Disabled (TERTIARY BUG — CONFIRMED)

**Code** (`agent_invoker.py:799-815`):
```python
def _kill_child_claude_processes(self) -> None:
    proc_path = Path("/proc")
    if not proc_path.exists():
        logger.warning(
            "TASK-FIX-ASPF-004: /proc not available on this platform, "
            "cannot kill child claude processes"
        )
        return  # ← macOS: NO CLEANUP HAPPENS
```

This method walks `/proc/{pid}/status` to find child Claude CLI processes and send SIGTERM. On macOS (Darwin), `/proc` doesn't exist, so the method returns immediately with a warning. This means:
- When a stream hangs and `asyncio.timeout` fires, the SDK subprocess may continue running
- The subprocess holds stdout/stderr file descriptors open
- Repeated runs accumulate zombie processes
- File descriptor exhaustion becomes more likely with each hung stream

**Impact on this incident**: After TASK-SAD-002 timed out, its Claude CLI subprocess (Node.js) may have remained running. No cleanup was performed. The feature orchestrator's cancellation event was set (line 1331-1332), but the cancellation monitor's `_kill_child_claude_processes()` call was a no-op on macOS.

### Finding 4: Shared Worktree — Exonerated But Fragile

**Exonerated for this incident**: Each task's agent completed its implementation work at approximately the same speed (5-8 minutes). The shared worktree did not cause contention that slowed TASK-SAD-002.

**However, the architecture is fragile**:
- No file locks on worktree writes — parallel tasks could corrupt each other's files
- Git lock (`_git_lock = threading.RLock()`) only protects git operations, not file I/O
- CoachVerifier checkpoint commits (680fedca for SAD-001, 4ea670db for SAD-003) modify the worktree state before SAD-002's state recovery runs
- Full-worktree pytest in state recovery picks up test files from all three tasks, not just the timed-out task

### Finding 5: timeout Race Condition — NOT RELEVANT to This Incident

Each parallel task gets its own `AutoBuildOrchestrator` (line 1552) and its own `AgentInvoker` (lazy-init at line 979-980). The `self.sdk_timeout_seconds` mutation in `_calculate_sdk_timeout` (lines 975-977) is per-instance, not shared across tasks.

However, within a single `AgentInvoker`, the save/restore pattern is not thread-safe for multi-turn scenarios:
```python
original_timeout = self.sdk_timeout_seconds  # line 976
self.sdk_timeout_seconds = effective_timeout  # line 977
# ... invocation ...
self.sdk_timeout_seconds = original_timeout  # line 1139 (finally)
```
This is a latent bug for future multi-turn scenarios where turns might overlap (not currently possible but worth noting).

### Finding 6: File Descriptor Analysis

The FD limit was raised from 256 → 4096 (feature_orchestrator.py:341-362). Each SDK subprocess uses ~60-90 FDs. With 3 parallel tasks: 3 × 75 = ~225 FDs — safely within the 4096 limit. FD exhaustion is **not** a contributing factor for this incident.

However, if BUG #3 (macOS subprocess cleanup) leads to zombie processes accumulating across runs, FD pressure could become an issue in long sessions.

---

## Root Cause Summary (Revised)

```
Timeline:
  T+0s       : SDK stream opened for TASK-SAD-002
  T+~90s     : First Edit tool use observed
  T+~300s    : SAD-001 SDK done (turns=27) — stream closes cleanly ✓
  T+~330s    : SAD-003 SDK done (turns=34) — stream closes cleanly ✓
  T+~480s    : SAD-002 SDK done (turns=33) — ResultMessage received
  T+~480s    : BUG #1: No break — async for loop continues waiting
  T+~480s    : CLI subprocess hangs (doesn't exit cleanly)
  T+~480s    : BUG #3: No macOS cleanup — subprocess stays alive
  T+510-2310s: Stream hung — heartbeat continues with zero activity
  T+2340s    : asyncio.timeout fires → SDKTimeoutError raised
  T+2340s    : State recovery begins
  T+2340s    : Player report loaded (66 tests, 99%, 95/100) ✓
  T+2340s    : Git changes detected (3 files) ✓
  T+2340-2460s: Coach pytest re-run on full worktree → 120s timeout
  T+~2460s   : BUG #2: test_count=0 (player report's 66 ignored)
  T+~2460s   : Synthetic report: "2 files, 0 tests" (should be 66)
  T+2400s    : Feature-level timeout → TASK-SAD-002 marked TIMEOUT
  T+2400s    : stop_on_failure=True → Feature FAILED, 7 tasks skipped
```

**Three bugs at three technology seams**:
1. **SEAM 1 (SDK API boundary)**: Missing `break` after `ResultMessage` → stream hang
2. **SEAM 3 (Filesystem/test boundary)**: Player report test data discarded → false "0 tests"
3. **SEAM 2 (Process boundary)**: macOS subprocess cleanup disabled → zombie processes

---

## Recommendations (Revised)

### R1: Add `break` After ResultMessage — ALL THREE PATHS (Critical)

**Files & lines**:
- `agent_invoker.py:3975` (`_invoke_task_work_implement`) — **active failure**
- `agent_invoker.py:1753` (`_invoke_with_role`) — latent risk
- `agent_invoker.py:~3050` (`_invoke_player_direct`) — latent risk

```python
elif isinstance(message, ResultMessage):
    result_count += 1
    sdk_turns_used = message.num_turns
    logger.info(f"SDK completed: turns={message.num_turns}")
    break  # ResultMessage is terminal — exit stream loop
```

**Impact**: Eliminates the entire class of "completed-but-timed-out" failures.
**Risk**: Very Low. `ResultMessage` is the SDK's documented terminal message.

### R2: Fall Back to Player Report Test Data in State Recovery (Critical)

**File**: `state_tracker.py:376-380`

```python
# Current (broken):
test_count = (
    test_results.test_count
    if test_results and test_results.tests_run
    else 0
)

# Fixed:
test_count = (
    test_results.test_count
    if test_results and test_results.tests_run
    else player_report.get("test_count", 0)  # Fall back to player report
)

tests_passed = (
    test_results.tests_passed
    if test_results and test_results.tests_run
    else player_report.get("tests_passed", False)  # Fall back to player report
)
```

**Impact**: State recovery correctly reports test results when CoachVerifier times out.
**Risk**: Low. Player report data is more authoritative than a timed-out re-run.

### R3: Implement macOS Subprocess Cleanup (High Priority)

**File**: `agent_invoker.py:799-815`

Replace the `/proc`-only Linux approach with cross-platform subprocess tracking:

```python
import psutil  # or use os.kill with tracked PIDs

def _kill_child_claude_processes(self) -> None:
    try:
        import psutil
        current = psutil.Process()
        for child in current.children(recursive=True):
            if "claude" in child.name() or "node" in child.name():
                child.terminate()
    except ImportError:
        # Fallback: track subprocess PIDs during creation
        pass
```

Or simpler: track the SDK subprocess PID when `query()` is called and store it on the invoker. On timeout, send SIGTERM to that PID directly.

**Impact**: Prevents zombie subprocess accumulation on macOS.
**Risk**: Medium — requires adding `psutil` dependency or subprocess PID tracking.

### R4: Increase Coach Verification Timeout for State Recovery Context

**File**: `coach_verification.py:269`

Add a configurable timeout parameter:
```python
def _run_tests(self, test_paths=None, timeout=120) -> TestResult:
    result = subprocess.run(cmd, ..., timeout=timeout)
```

State recovery callers pass `timeout=300`:
```python
verifier._run_tests(test_paths=test_paths, timeout=300)
```

**Impact**: Reduces false test detection failures during state recovery.
**Risk**: Very Low.

### R5: Scope State Recovery Tests to Task-Specific Files

**File**: `autobuild.py:2214-2220`

When the player report is available, extract test file paths from it rather than re-discovering:
```python
if player_report and player_report.get("tests_written"):
    test_paths = player_report["tests_written"]
```

**Impact**: Faster, more accurate test re-runs during state recovery.
**Risk**: Low.

### R6: Add `task_id` to SDK Completion Log (Diagnostic)

**File**: `agent_invoker.py:3975`

```python
logger.info(f"[{task_id}] SDK completed: turns={message.num_turns}")
```

**Impact**: Eliminates log attribution ambiguity in parallel execution.
**Risk**: None.

### R7: No Changes Needed to Timeout Formula

The formula `base × mode × complexity` is correctly designed and provided ample time. The issue was stream lifecycle management, not timeout calculation.

---

## Decision Matrix (Revised)

| Fix | Impact | Effort | Risk | Priority | Seam |
|-----|--------|--------|------|----------|------|
| R1: Break after ResultMessage (3 paths) | Critical | 3 lines | Very Low | **P0** | SEAM 1 |
| R2: Player report fallback in recovery | Critical | 4 lines | Low | **P0** | SEAM 3 |
| R3: macOS subprocess cleanup | High | ~30 lines | Medium | **P1** | SEAM 2 |
| R4: Increase recovery test timeout | Medium | 2 lines | Very Low | **P2** | SEAM 3 |
| R5: Scope recovery tests to task files | Medium | ~10 lines | Low | **P2** | SEAM 3 |
| R6: Add task_id to SDK completion log | Low | 1 line | None | **P3** | Diagnostic |
| R7: No timeout formula change | N/A | 0 | N/A | N/A | N/A |

## Acceptance Criteria Assessment

| Criterion | Status | Finding |
|-----------|--------|---------|
| Root cause identified | **PASS** | Three bugs at three technology seams (SDK stream, state recovery, process cleanup) |
| TASK-SAD-002 actually completed work | **PASS** | Yes — 66 tests, 99% coverage, arch 95/100, all quality gates passed |
| SDK timeout formula needs adjustment | **PASS** | No — formula is correct; issue is stream lifecycle management |
| State recovery evaluation | **PASS** | Two bugs: test data lost (state_tracker.py:376-380) + 120s timeout too short |
| Configuration recommendations | **PASS** | R1-R6 above with exact file paths and line numbers |
| Shared worktree impact | **PASS** | Exonerated for this incident; architecture noted as fragile for future |

## Confidence Assessment

| Area | Confidence | Basis |
|------|-----------|-------|
| BUG #1 (stream hang) | **Very High** | Code path verified, log attribution confirmed via timestamp analysis, SDK internals traced |
| BUG #2 (test data loss) | **Very High** | Both branches of ternary verified to yield 0, player_report.get() never called for test_count |
| BUG #3 (macOS cleanup) | **High** | `/proc` check confirmed Linux-only, Darwin platform confirmed in environment |
| Shared worktree exoneration | **High** | Timing analysis shows all 3 tasks completed agent work within similar timeframes |
| Timeout formula correctness | **Very High** | Formula verified against code, all 3 tasks completed well within their calculated timeouts |
| Log attribution (turns=33 = SAD-002) | **Very High** | Timestamp suffix `.218Z` matches, bracketed by explicit `[TASK-SAD-002]` log lines |
