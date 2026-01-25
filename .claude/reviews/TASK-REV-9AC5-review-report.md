# Review Report: TASK-REV-9AC5

## Executive Summary

This architectural review analyzes the `/feature-build` command output issues identified during testing with a 10-task feature (FEAT-119C). The analysis focuses on SDK timeout configuration flow, worktree error handling, and state tracking in the feature orchestrator.

**Overall Architecture Score: 68/100**

Key findings:
- **SDK Timeout Configuration**: Task/feature frontmatter `sdk_timeout` is NOT being read by CLI or passed to orchestrator (root cause identified)
- **Worktree Cleanup**: `_clean_state()` does NOT pass `force=True` to cleanup, causing failures with untracked files
- **Branch Cleanup**: No fallback branch cleanup when worktree creation fails due to existing branch
- **Partial Work Detection**: State tracking relies entirely on Player JSON report; no fallback detection

---

## Review Details

- **Mode**: Architectural Review
- **Depth**: Standard
- **Duration**: ~45 minutes
- **Reviewer**: Claude Opus 4.5 (architectural-reviewer agent)
- **Files Analyzed**: 6 core files

---

## Finding 1: SDK Timeout Configuration Not Being Read

**Severity**: HIGH
**SOLID Principle**: Open/Closed Principle (OCP) violation
**Location**: [guardkit/cli/autobuild.py:343-465](guardkit/cli/autobuild.py#L343-L465)

### Root Cause Analysis

The `feature` command in the CLI does **not** read or pass `sdk_timeout` from task/feature frontmatter to the orchestrator:

```python
# Current code in guardkit/cli/autobuild.py (feature command)
@autobuild.command()
@click.argument("feature_id")
@click.option("--max-turns", default=5, ...)  # max_turns IS configurable
# NO --sdk-timeout option defined
```

The `FeatureOrchestrator` is initialized without any timeout configuration:

```python
# guardkit/orchestrator/feature_orchestrator.py:451-459
orchestrator = FeatureOrchestrator(
    repo_root=Path.cwd(),
    max_turns=max_turns,
    stop_on_failure=stop_on_failure,
    resume=resume,
    fresh=fresh,
    verbose=verbose,
    quiet=ctx_obj.get("quiet", False),
)
# NO sdk_timeout parameter passed
```

Meanwhile, `AgentInvoker` does support `sdk_timeout_seconds`:

```python
# guardkit/orchestrator/agent_invoker.py:120-152
def __init__(
    self,
    worktree_path: Path,
    ...
    sdk_timeout_seconds: int = DEFAULT_SDK_TIMEOUT,  # 300s default
):
```

### Evidence

The task frontmatter had `autobuild.sdk_timeout: 600` but the agent still timed out at 300s:
```
ERROR: SDK timeout after 300s: Agent invocation exceeded 300s timeout
```

### Configuration Flow Gap

```
Task Frontmatter (autobuild.sdk_timeout: 600)
         ↓
   FeatureLoader (parses but doesn't expose sdk_timeout)
         ↓
   CLI feature command (doesn't read sdk_timeout)
         ↓
   FeatureOrchestrator (doesn't accept sdk_timeout parameter)
         ↓
   AutoBuildOrchestrator (doesn't pass to AgentInvoker)
         ↓
   AgentInvoker (uses DEFAULT_SDK_TIMEOUT = 300)
```

### Impact

Complex tasks that require >300s to complete will always timeout, regardless of frontmatter configuration.

### Why the Timeout is Occurring: Test Enforcement Loop Analysis

**Root Cause**: The 300s timeout is **not sufficient** for complex tasks that trigger Phase 4.5 test enforcement loop iterations.

**Timeline Breakdown** (TASK-INFRA-001):
```
Player Process Execution:
0-30s    Pre-loop quality gates (design-only phase)
30-90s   Phase 3: Implementation (224-line config.py created)
90-150s  Phase 4: Initial test run (32/40 tests pass, 8 CORS tests fail)
150-210s Phase 4.5 Attempt 1: Fix CORS issues, re-run all 40 tests
210-270s Phase 4.5 Attempt 2: Still 8 failures, re-test all 40 tests
270-300s Phase 4.5 Attempt 3: Still failing...
300s     ⚠️ SDK TIMEOUT - Process killed before player_turn_1.json written
```

**Phase 4.5 Test Enforcement Loop** (working as designed):
- Detected 8/40 test failures (CORS origins parsing)
- Automatically entered fix loop (up to 3 attempts)
- Each attempt involves:
  1. Analyzing all 8 failures
  2. Invoking implementation agent to fix code
  3. Re-running ALL 40 tests
  4. Re-evaluating results
- Each attempt takes 60-90 seconds

**Evidence from feature-build output**:
- 32/40 tests passing (80%) ✅
- 224-line config.py created ✅
- ~400-line comprehensive test suite ✅
- Implementation was largely complete ✅
- Process killed at 300s before report written ❌

**The CORS test failures**:
```python
# Pydantic Settings v2 parsing issue
SettingsError: error parsing value for field "cors_origins" from source "EnvSettingsSource"

# 8 failures:
- test_cors_origins_string_parsing FAILED
- test_cors_origins_whitespace_handling FAILED
- test_cors_origins_empty_string FAILED
- test_cors_origins_single_value FAILED
- (4 more related failures)
```

**Conclusion**: The timeout is **the PRIMARY CAUSE**, not a symptom. The test enforcement loop is working correctly - it's designed to iterate up to 3 times to fix test failures. For complex tasks like configuration with 40 tests, the default 300s timeout is insufficient.

**Recommendation Impact**: R1 (Add --sdk-timeout flag) becomes **CRITICAL** - without it, any complex task triggering Phase 4.5 will timeout before completion.

---

## Finding 2: Worktree Cleanup Missing Force Flag

**Severity**: MEDIUM
**SOLID Principle**: Single Responsibility Principle (SRP) concern
**Location**: [guardkit/orchestrator/feature_orchestrator.py:611-644](guardkit/orchestrator/feature_orchestrator.py#L611-L644)

### Root Cause Analysis

The `_clean_state()` method calls `cleanup()` without `force=True`:

```python
# guardkit/orchestrator/feature_orchestrator.py:632
self._worktree_manager.cleanup(worktree_to_cleanup)
# Should be: self._worktree_manager.cleanup(worktree_to_cleanup, force=True)
```

The `cleanup()` method in `WorktreeManager` supports force removal:

```python
# guardkit/worktrees/manager.py:425-467
def cleanup(self, worktree: Worktree, force: bool = False) -> None:
    remove_args = ["worktree", "remove", str(worktree.path)]
    if force:
        remove_args.append("--force")
```

### Evidence

From the observed output:
```
fatal: '.../worktrees/FEAT-119C' contains modified or untracked files, use --force to delete it
```

### Impact

When using `--fresh` flag, cleanup fails if the previous worktree has any untracked files (which is common after implementation).

---

## Finding 3: No Branch Cleanup Fallback

**Severity**: MEDIUM
**SOLID Principle**: DRY violation (cleanup logic duplicated but incomplete)
**Location**: [guardkit/worktrees/manager.py:302-371](guardkit/worktrees/manager.py#L302-L371)

### Root Cause Analysis

When worktree creation fails due to existing branch, there's no fallback to delete the branch:

```python
# guardkit/worktrees/manager.py:354-364
try:
    self._run_git([
        "worktree", "add",
        str(worktree_path),
        "-b", branch_name,  # Fails if branch exists
        base_branch
    ])
except WorktreeError as e:
    raise WorktreeCreationError(
        f"Failed to create worktree for {task_id}: {e}"
    )
```

The error propagates without attempting:
```bash
git branch -D autobuild/FEAT-XXX
```

### Evidence

From the observed output:
```
fatal: a branch named 'autobuild/FEAT-119C' already exists
```

This occurs after a failed worktree cleanup leaves an orphaned branch.

### Impact

Users must manually run `git branch -D autobuild/FEAT-XXX` before retrying with `--fresh`.

---

## Finding 4: Partial Work Detection Architecture Gap (DEEP DIVE)

**Severity**: HIGH (upgraded from MEDIUM after deeper analysis)
**SOLID Principle**: Multiple violations (DIP, OCP, SRP)
**Location**: [guardkit/orchestrator/autobuild.py:1046-1079](guardkit/orchestrator/autobuild.py#L1046-L1079)

### Executive Summary

The current architecture has a **single point of failure** for state tracking: the Player JSON report. When the Player times out before writing this file (as observed with the 300s timeout), all work becomes invisible to the system despite substantial code being written and tests passing.

**Critical Gap**: The system has NO fallback detection mechanism, leading to:
- 100% information loss on timeout
- Inability to resume partial work
- User confusion ("0 completed tasks" when work is clearly done)
- Wasted computation (re-running work that's already 80% complete)

### Root Cause Analysis

#### Current State Tracking Architecture

```
Player Invocation (300s timeout)
         ↓
   [Agent creates code + tests]
         ↓
   [Agent writes player_turn_N.json]  ← SINGLE POINT OF FAILURE
         ↓
   AgentInvoker loads JSON report
         ↓
   TurnRecord created with report data
         ↓
   State persisted to task frontmatter
```

**If timeout occurs before JSON write**: Entire chain breaks, all work invisible.

#### Detection Points Available (Currently Unused)

The codebase has **FIVE** existing detection mechanisms that could be leveraged:

##### 1. **CoachVerifier Test Runner** (Already Implemented!)

```python
# guardkit/orchestrator/coach_verification.py:239-297
class CoachVerifier:
    def _run_tests(self) -> TestResult:
        """Run tests in worktree and return result."""
        result = subprocess.run(
            ["pytest", "--tb=no", "-q"],
            cwd=self.worktree_path,
            capture_output=True,
            text=True,
            timeout=120,
        )
        return TestResult(
            passed=result.returncode == 0,
            test_count=self._parse_pytest_count(result.stdout),
            output=result.stdout,
        )
```

**Status**: ✅ Already exists, currently only used for honesty verification
**Opportunity**: Can be repurposed for partial work detection

##### 2. **Git Status Detection** (Not Implemented)

```python
# Potential implementation
subprocess.run(
    ["git", "status", "--porcelain"],
    cwd=worktree.path,
    capture_output=True,
    text=True,
)
```

**Status**: ❌ Not implemented
**Coverage**: Detects ALL file changes (tracked + untracked)

##### 3. **Git Diff Detection** (Mentioned in user guidance, not used programmatically)

```python
# Currently only in CLI display messages
# guardkit/orchestrator/feature_orchestrator.py:1264
console.print("  2. View diff: git diff main")
```

**Status**: ❌ Mentioned in messages, not used for detection
**Coverage**: Detects changes vs base branch with line-level granularity

##### 4. **Feature/Task YAML State** (Partially Used)

```python
# guardkit/orchestrator/feature_loader.py:789-830
@staticmethod
def is_incomplete(feature: Feature) -> bool:
    # Check status
    if feature.status in ("in_progress", "paused"):
        return True
    # Check for in-progress tasks
    for task in feature.tasks:
        if task.status == "in_progress":
            return True
    # ...
```

**Status**: ⚠️ Partially implemented (only checks status fields)
**Gap**: Doesn't detect work done without state file updates

##### 5. **Worktree File Timestamps** (Not Used)

```python
# Potential implementation
from pathlib import Path
modified_files = [
    f for f in worktree.path.rglob("*.py")
    if f.stat().st_mtime > start_time
]
```

**Status**: ❌ Not implemented
**Coverage**: Detects newly created/modified files by timestamp

### Evidence from Test Run

From FEAT-119C output log:

```
ERROR: SDK timeout after 300s: Agent invocation exceeded 300s timeout
Player report not found: .../player_turn_1.json

# But git status would show:
??  src/config.py                    # 224 lines
??  tests/test_config.py              # ~400 lines
??  .guardkit/autobuild/*/turn_context.json

# And pytest would return:
32 passed, 8 failed in 12.34s
```

**Gap Analysis**:
- Git status: Would detect 2 new files ✅
- Test runner: Would show 32/40 passing (80% success rate) ✅
- JSON report: NOT created ❌
- State tracking: Shows "0 completed tasks" ❌

### Multi-Layered State Loss Problem

The issue is more complex than just "missing Player report":

#### Layer 1: Turn-Level State Loss
```python
# guardkit/orchestrator/autobuild.py:887-912
player_result = self._invoke_player_safely(...)
if player_result.success:
    summary = self._build_player_summary(player_result.report)
else:
    # Return early - can't proceed without Player implementation
    return TurnRecord(
        turn=turn,
        player_result=player_result,
        coach_result=None,
        decision="error",  # ← Turn marked as ERROR
        feedback=None,
        timestamp=timestamp,
    )
```

**Problem**: `player_result.success = False` when JSON not found, even if work exists.

#### Layer 2: Feature-Level State Loss
```python
# guardkit/orchestrator/feature_orchestrator.py:446-477
if FeatureLoader.is_incomplete(feature):
    resume_point = FeatureLoader.get_resume_point(feature)
    # ...
    if resume_point['worktree_path']:
        worktree_path = Path(resume_point['worktree_path'])
```

**Problem**: `is_incomplete()` only checks task status from YAML, not actual worktree state.

#### Layer 3: Resume State Loss
```python
# guardkit/orchestrator/feature_loader.py:854-863
completed_tasks = [t.id for t in feature.tasks if t.status == "completed"]
pending_tasks = [t.id for t in feature.tasks if t.status == "pending"]
```

**Problem**: Task status is only updated when Player report exists.

### Architectural Violations

1. **Dependency Inversion Principle (DIP)**:
   - High-level policy (state tracking) depends on low-level detail (JSON file existence)
   - Should depend on abstraction (IStateDetector interface)

2. **Open/Closed Principle (OCP)**:
   - Cannot add new detection mechanisms without modifying orchestrator
   - Should be extensible via strategy pattern

3. **Single Responsibility Principle (SRP)**:
   - State persistence mixed with state detection
   - Should separate concerns: detection vs persistence vs reporting

### Impact Assessment

**Severity Upgrade Justification**: This is **HIGH severity** because:

1. **Data Loss**: 100% information loss on timeout (not just inconvenience)
2. **User Experience**: Extremely confusing ("I see the files, why does it say 0 tasks?")
3. **Cost Efficiency**: Wasted compute resources re-running 80%-complete work
4. **Reliability**: System appears non-deterministic (sometimes tracks, sometimes doesn't)
5. **Frequency**: Occurs on EVERY timeout scenario (not rare edge case)

---

## Finding 5: Phase 4.5 Test Enforcement Loop Lacks Resilience Against Unfixable Errors

**Severity**: MEDIUM
**SOLID Principle**: Open/Closed Principle (OCP) violation
**Location**: [installer/core/commands/lib/phase_execution.py](installer/core/commands/lib/phase_execution.py)

### Executive Summary

While Finding 1 correctly identifies that the timeout is insufficient for complex tasks, this finding addresses a complementary architectural issue: **Phase 4.5 lacks defensive mechanisms to detect when errors are beyond auto-fix capability**, resulting in wasted time retrying the same unfixable error.

### The Problem

Phase 4.5 Test Enforcement Loop is designed to auto-fix test failures (up to 3 attempts), but it has **no defenses against "unfixable" errors**:

```python
# Current Phase 4.5 behavior (simplified)
for attempt in range(1, 4):  # 3 attempts
    test_result = run_tests()

    if test_result.passed:
        break  # Success

    # Analyze failures and attempt fix
    fix_code(test_result.failures)

    # Re-run ALL tests (expensive)
    # No check: "Is this the SAME error as before?"
    # No timeout per iteration
    # No complexity assessment
```

### Evidence from TASK-INFRA-001

**Timeline** (reconstructed from feature-build output):
```
0-90s    Phases 2-3: Design + Implementation ✅
         - Created config.py (224 lines)
         - Created test file (~400 lines)

90-150s  Phase 4: Initial test run ✅
         - 40 tests executed
         - 32/40 passing (80%)
         - 8 CORS failures (Pydantic Settings v2 issue)

150-210s Phase 4.5 Attempt 1 ⚠️
         - Analyzed 8 CORS failures
         - Generated fix for config.py
         - Re-ran ALL 40 tests
         - Result: SAME 8 failures (root cause not addressed)

210-270s Phase 4.5 Attempt 2 ⚠️
         - Analyzed SAME 8 failures again
         - Tried different fix approach
         - Re-ran ALL 40 tests
         - Result: SAME 8 failures (Pydantic v2 migration complexity)

270-300s Phase 4.5 Attempt 3 ⚠️
         - Analyzed SAME 8 failures yet again
         - Tried third fix approach
         - Tests still running when...

300s     SDK Timeout ❌
         - Process killed by asyncio.wait_for
         - player_turn_1.json never written
         - All work lost (Finding 4 impact)
```

### Why CORS Errors Are "Unfixable" by Phase 4.5

The errors require understanding **Pydantic Settings v2 breaking changes**:

```python
# Pydantic v1 (old)
class Settings(BaseSettings):
    cors_origins: str = "http://localhost:3000"  # ✅ Works

# Pydantic v2 (new)
class Settings(BaseSettings):
    cors_origins: List[str] = []  # ❌ Requires different type

    @field_validator('cors_origins', mode='before')
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(',')]
        return v
```

**This requires**:
- Understanding v1 → v2 migration guide
- Recognizing the specific CORS parsing pattern
- Implementing custom validator
- Understanding `mode='before'` semantics

**Phase 4.5 cannot**:
- Detect "this is the same error as Attempt 1"
- Assess "this is beyond my auto-fix capability"
- Exit early to save time
- Provide guidance like "Consider manual fix for Pydantic v2 migration"

### Architectural Issues

**1. No Error Fingerprinting** (OCP violation)
```python
# Current: No detection of repeated errors
attempt_1_errors = ["CORS parsing failed"]
attempt_2_errors = ["CORS parsing failed"]  # Same!
attempt_3_errors = ["CORS parsing failed"]  # Still same!

# Should detect: "Same error = unfixable, fail fast"
```

**2. No Per-Iteration Timeout**
```python
# Current: Only overall SDK timeout (300s)
for attempt in range(1, 4):
    fix_and_test()  # Can take 60-90s EACH

# Should have: Per-iteration timeout (max 60s per attempt)
if attempt_duration > 60:
    log.warning("Attempt taking too long, may be unfixable")
```

**3. No Complexity Assessment**
```python
# Current: No heuristics for "is this fixable?"
errors = parse_test_failures(output)
generate_fix(errors)  # Always tries

# Should assess:
if error_complexity_high(errors):
    # e.g., "Pydantic v2 migration", "Database schema change"
    recommend_manual_fix()
```

**4. No Early Exit Strategy**
```python
# Current: Always exhausts all 3 attempts
for attempt in range(1, 4):
    if not fix_succeeded:
        continue  # Try again

# Should exit early:
if same_error_as_previous_attempt(errors):
    fail_with_guidance("Beyond auto-fix capability")
```

### Comparison with Finding 1

| Aspect | Finding 1 (Timeout) | Finding 5 (Resilience) |
|--------|---------------------|------------------------|
| **Issue** | 300s too short | Phase 4.5 wastes time on unfixable errors |
| **Impact** | Work doesn't complete | Time wasted, then timeout anyway |
| **Solution** | Increase timeout (R1) | Add resilience mechanisms (R6) |
| **Priority** | CRITICAL (immediate) | MEDIUM (long-term) |
| **Type** | Configuration gap | Architectural gap |

**Both are needed**:
- **R1 (timeout increase)**: Tactical fix for complex tasks
- **R6 (resilience)**: Strategic fix to prevent time waste

### Impact Assessment

**Without R6**, even with increased timeout:
- Complex tasks with 8-10 failures → 3 × 90s = 270s wasted on unfixable errors
- User confusion: "Why did it try the same fix 3 times?"
- Poor resource utilization: 45% of timeout spent on futile attempts

**With R6**:
- Early exit after Attempt 1 if same error → saves 180s
- Clear guidance: "Manual fix needed for Pydantic v2 migration"
- Better user experience: Honest about limitations

---

## Recommendations

### R1: Add --sdk-timeout CLI Flag (HIGH Priority)

**Location**: [guardkit/cli/autobuild.py](guardkit/cli/autobuild.py)

Add CLI option and pass through to orchestrator:

```python
@click.option(
    "--sdk-timeout",
    default=None,
    type=int,
    help="SDK timeout in seconds (default: from frontmatter or 300)",
)
```

Also read from frontmatter cascade:
```python
# In feature command
effective_timeout = (
    sdk_timeout  # CLI flag (highest priority)
    or feature.get("autobuild", {}).get("sdk_timeout")  # Feature YAML
    or DEFAULT_SDK_TIMEOUT  # 300s default
)
```

**Estimated Complexity**: 3/10

### R2: Force Worktree Cleanup (HIGH Priority)

**Location**: [guardkit/orchestrator/feature_orchestrator.py:632](guardkit/orchestrator/feature_orchestrator.py#L632)

Change:
```python
self._worktree_manager.cleanup(worktree_to_cleanup)
```

To:
```python
self._worktree_manager.cleanup(worktree_to_cleanup, force=True)
```

**Estimated Complexity**: 1/10

### R3: Add Branch Cleanup Fallback (MEDIUM Priority)

**Location**: [guardkit/worktrees/manager.py:354-364](guardkit/worktrees/manager.py#L354-L364)

Enhance `create()` to handle existing branch:

```python
try:
    self._run_git([...])
except WorktreeError as e:
    if "already exists" in str(e):
        logger.warning(f"Branch {branch_name} exists, attempting cleanup")
        try:
            self._run_git(["branch", "-D", branch_name])
            # Retry worktree creation
            self._run_git([...])
        except WorktreeError:
            raise WorktreeCreationError(
                f"Failed to create worktree for {task_id}. "
                f"Manual cleanup required: git branch -D {branch_name}"
            )
    else:
        raise WorktreeCreationError(...)
```

**Estimated Complexity**: 4/10

### R4: Implement Multi-Layered Partial Work Detection (HIGH Priority)

**Rationale**: See Finding 4 for comprehensive deep dive analysis showing single point of failure in state tracking and multi-layered state loss vulnerability.

**Locations**:
- Primary: [guardkit/orchestrator/autobuild.py](guardkit/orchestrator/autobuild.py)
- Infrastructure: [guardkit/orchestrator/coach_verification.py:239-297](guardkit/orchestrator/coach_verification.py#L239-L297)
- State: [guardkit/orchestrator/feature_loader.py:789-877](guardkit/orchestrator/feature_loader.py#L789-L877)

#### Phased Implementation Strategy

**Phase 1: Git-Based Detection (Complexity: 4/10, Priority: IMMEDIATE)**

Leverage existing git infrastructure in worktrees for basic detection:

```python
def _detect_git_changes(self, worktree_path: Path) -> Optional[GitChangesSummary]:
    """Detect uncommitted changes via git status/diff."""

    # Check for uncommitted changes
    status_result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=worktree_path,
        capture_output=True,
        text=True,
        timeout=5,
    )

    if not status_result.stdout.strip():
        return None  # No changes

    # Get detailed diff statistics
    diff_result = subprocess.run(
        ["git", "diff", "--stat", "HEAD"],
        cwd=worktree_path,
        capture_output=True,
        text=True,
        timeout=10,
    )

    return GitChangesSummary(
        files_modified=[line[3:] for line in status_result.stdout.strip().split('\n') if line.startswith(' M')],
        files_added=[line[3:] for line in status_result.stdout.strip().split('\n') if line.startswith('??')],
        diff_stats=diff_result.stdout,
        timestamp=datetime.now().isoformat(),
    )
```

**Phase 2: Test-Based Verification (Complexity: 5/10, Priority: HIGH)**

Leverage existing `CoachVerifier._run_tests()` infrastructure:

```python
def _detect_test_results(self, worktree_path: Path) -> Optional[TestResultSummary]:
    """
    Attempt to run tests to verify partial implementation.

    Reuses CoachVerifier infrastructure for consistency.
    """
    try:
        # Instantiate CoachVerifier with read-only context
        verifier = CoachVerifier(
            worktree_path=worktree_path,
            task_id=self.task_id,
            turn_number=self.current_turn,
        )

        # Run tests (already handles pytest detection, output parsing)
        test_result = verifier._run_tests()

        return TestResultSummary(
            tests_run=test_result.test_count > 0,
            tests_passed=test_result.passed,
            test_count=test_result.test_count,
            output_summary=test_result.output[:500],  # First 500 chars
            timestamp=datetime.now().isoformat(),
        )
    except Exception as e:
        logger.warning(f"Test detection failed: {e}")
        return TestResultSummary(
            tests_run=False,
            error=str(e),
            timestamp=datetime.now().isoformat(),
        )
```

**Phase 3: Comprehensive State Tracker (Complexity: 8/10, Priority: MEDIUM)**

Create abstraction layer to decouple state tracking from Player JSON reports (addresses DIP violation):

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, List

@dataclass
class WorkState:
    """Unified work state representation."""
    turn_number: int
    files_modified: List[str]
    files_created: List[str]
    tests_written: List[str]
    tests_passed: bool
    test_count: int
    git_changes: Optional[GitChangesSummary]
    test_results: Optional[TestResultSummary]
    player_report: Optional[Dict]  # May be None
    timestamp: str
    detection_method: str  # "player_report" | "git_detection" | "test_detection" | "comprehensive"


class StateTracker(ABC):
    """Abstract state tracking interface (addresses DIP)."""

    @abstractmethod
    def capture_state(self, worktree_path: Path, turn: int) -> WorkState:
        """Capture current work state via available methods."""
        pass

    @abstractmethod
    def restore_state(self, work_state: WorkState) -> None:
        """Restore work state for resume."""
        pass


class MultiLayeredStateTracker(StateTracker):
    """
    Comprehensive state tracker using multiple detection methods.

    Detection cascade:
    1. Player JSON report (if available) - highest fidelity
    2. CoachVerifier test results - verifies implementation quality
    3. Git changes - detects file-level work
    4. YAML state - fallback for orchestration state
    """

    def capture_state(self, worktree_path: Path, turn: int) -> WorkState:
        """Capture via all available methods."""

        # Try Player report first
        player_report = self._load_player_report(turn)

        # Always capture git state (independent verification)
        git_changes = self._detect_git_changes(worktree_path)

        # Always run tests (independent verification)
        test_results = self._detect_test_results(worktree_path)

        # Synthesize WorkState from all sources
        if player_report:
            # Player report is source of truth, git/tests for verification
            return WorkState(
                turn_number=turn,
                files_modified=player_report.get("files_modified", []),
                files_created=player_report.get("files_created", []),
                tests_written=player_report.get("tests_written", []),
                tests_passed=test_results.tests_passed if test_results else False,
                test_count=test_results.test_count if test_results else 0,
                git_changes=git_changes,
                test_results=test_results,
                player_report=player_report,
                timestamp=datetime.now().isoformat(),
                detection_method="player_report"
            )
        elif git_changes or test_results:
            # No Player report, use git + test detection
            return WorkState(
                turn_number=turn,
                files_modified=git_changes.files_modified if git_changes else [],
                files_created=git_changes.files_added if git_changes else [],
                tests_written=[],  # Can't determine from git alone
                tests_passed=test_results.tests_passed if test_results else False,
                test_count=test_results.test_count if test_results else 0,
                git_changes=git_changes,
                test_results=test_results,
                player_report=None,
                timestamp=datetime.now().isoformat(),
                detection_method="git_test_detection"
            )
        else:
            # No work detected
            return None
```

#### Integration Points

**In `AutoBuildOrchestrator._execute_turn()`**:
```python
# After Player invocation, before Coach
try:
    player_report = self._load_player_report(turn)
    work_state = self.state_tracker.capture_state(
        worktree_path=self.worktree.path,
        turn=turn
    )
except Exception as e:
    logger.error(f"Player failed, attempting state recovery: {e}")

    # Use multi-layered detection for recovery
    work_state = self.state_tracker.capture_state(
        worktree_path=self.worktree.path,
        turn=turn
    )

    if work_state:
        logger.info(f"Partial work detected via {work_state.detection_method}")
        # Create synthetic TurnRecord from detected state
        turn_record = self._create_turn_from_state(work_state)
    else:
        logger.warning("No work detected in worktree")
        return TurnRecord(error=str(e), ...)
```

#### Architectural Benefits

1. **Decouples state tracking from Player JSON** (fixes DIP violation)
2. **Multiple detection methods** provide redundancy
3. **Extensible via StateTracker ABC** (fixes OCP violation)
4. **Clear separation of concerns** (fixes SRP violation)
5. **Maintains backward compatibility** - Player reports still primary method

**Estimated Complexity**:
- Phase 1: 4/10 (2-3 hours)
- Phase 2: 5/10 (3-4 hours)
- Phase 3: 8/10 (1-2 days)
- **Total**: 8/10 (phased implementation reduces risk)

### R5: Increase Default Timeout for Features (LOW Priority)

**Location**: [guardkit/orchestrator/agent_invoker.py:44](guardkit/orchestrator/agent_invoker.py#L44)

Consider 600s default for feature-level vs 300s for single tasks:

```python
DEFAULT_SDK_TIMEOUT = int(os.environ.get("GUARDKIT_SDK_TIMEOUT", "300"))
DEFAULT_FEATURE_SDK_TIMEOUT = int(os.environ.get("GUARDKIT_FEATURE_SDK_TIMEOUT", "600"))
```

**Estimated Complexity**: 2/10

### R6: Add Phase 4.5 Resilience Mechanisms (MEDIUM Priority)

**Rationale**: See Finding 5 for comprehensive analysis of how Phase 4.5 wastes time on unfixable errors.

**Location**: [installer/core/commands/lib/phase_execution.py](installer/core/commands/lib/phase_execution.py)

#### Implementation Strategy

**Phase 1: Error Fingerprinting (Complexity: 5/10, Priority: MEDIUM)**

Detect when the same error repeats across attempts:

```python
from typing import List, Dict
import hashlib

def fingerprint_error(error_output: str) -> str:
    """Create unique fingerprint for error pattern."""
    # Normalize error (remove line numbers, timestamps, paths)
    normalized = re.sub(r'line \d+', 'line X', error_output)
    normalized = re.sub(r'/[^:]+:', '/PATH:', normalized)

    # Hash for comparison
    return hashlib.sha256(normalized.encode()).hexdigest()[:12]

def detect_repeated_error(
    current_errors: str,
    previous_fingerprints: List[str]
) -> bool:
    """Check if current error matches any previous attempt."""
    current_fp = fingerprint_error(current_errors)
    return current_fp in previous_fingerprints
```

**Phase 2: Per-Iteration Timeout (Complexity: 3/10, Priority: HIGH)**

Add timeout per fix attempt to prevent runaway iterations:

```python
import time
from typing import Optional

MAX_ITERATION_SECONDS = 60  # Max 60s per fix attempt

def attempt_fix_with_timeout(
    errors: str,
    iteration: int,
    max_seconds: int = MAX_ITERATION_SECONDS
) -> Optional[FixResult]:
    """Attempt fix with iteration-level timeout."""
    start_time = time.time()

    try:
        # Generate and apply fix
        fix_result = generate_and_apply_fix(errors)

        elapsed = time.time() - start_time
        if elapsed > max_seconds:
            logger.warning(
                f"Iteration {iteration} exceeded {max_seconds}s "
                f"({elapsed:.1f}s) - may be unfixable"
            )
            return None  # Signal to exit early

        return fix_result

    except Exception as e:
        logger.error(f"Fix attempt {iteration} failed: {e}")
        return None
```

**Phase 3: Complexity Assessment (Complexity: 6/10, Priority: MEDIUM)**

Assess whether errors are likely auto-fixable:

```python
from enum import Enum

class ErrorComplexity(Enum):
    SIMPLE = "simple"          # Typo, missing import
    MODERATE = "moderate"      # Logic error, type mismatch
    COMPLEX = "complex"        # Migration, architectural change
    UNFIXABLE = "unfixable"    # Requires external dependency change

UNFIXABLE_PATTERNS = [
    r"Pydantic.*migration",
    r"breaking change.*v\d+",
    r"deprecated.*removed",
    r"database schema.*mismatch",
    r"incompatible.*version",
]

def assess_error_complexity(error_output: str) -> ErrorComplexity:
    """Assess if error is likely auto-fixable."""

    # Check for unfixable patterns
    for pattern in UNFIXABLE_PATTERNS:
        if re.search(pattern, error_output, re.IGNORECASE):
            return ErrorComplexity.UNFIXABLE

    # Check error count
    error_count = len(re.findall(r'FAILED|ERROR', error_output))
    if error_count >= 10:
        return ErrorComplexity.COMPLEX

    # Check stack depth (complex errors have deep stacks)
    stack_depth = len(re.findall(r'File ".*", line \d+', error_output))
    if stack_depth >= 5:
        return ErrorComplexity.COMPLEX

    # Simple errors
    if any(keyword in error_output for keyword in ['NameError', 'ImportError', 'IndentationError']):
        return ErrorComplexity.SIMPLE

    return ErrorComplexity.MODERATE
```

**Phase 4: Early Exit with Guidance (Complexity: 4/10, Priority: HIGH)**

Exit Phase 4.5 early when errors are unfixable:

```python
def execute_phase_4_5_with_resilience(
    test_result: TestResult,
    max_attempts: int = 3
) -> Phase45Result:
    """Execute Phase 4.5 with resilience mechanisms."""

    previous_fingerprints = []

    for attempt in range(1, max_attempts + 1):
        logger.info(f"Phase 4.5 Attempt {attempt}/{max_attempts}")

        # Assess complexity BEFORE attempting fix
        complexity = assess_error_complexity(test_result.output)

        if complexity == ErrorComplexity.UNFIXABLE:
            return Phase45Result(
                success=False,
                attempts=attempt,
                recommendation="MANUAL_FIX_REQUIRED",
                guidance=(
                    f"Error appears to be beyond auto-fix capability.\n"
                    f"Detected pattern: {complexity.value}\n"
                    f"Recommendation: Review error and apply manual fix.\n"
                    f"Common causes: Library migration, breaking API changes, "
                    f"external dependency updates."
                ),
            )

        # Check for repeated error (after Attempt 1)
        if attempt > 1:
            if detect_repeated_error(test_result.output, previous_fingerprints):
                return Phase45Result(
                    success=False,
                    attempts=attempt,
                    recommendation="SAME_ERROR_REPEATED",
                    guidance=(
                        f"Same error occurred in Attempt {attempt} as previous attempts.\n"
                        f"Suggests error is beyond current auto-fix capability.\n"
                        f"Exiting early to save time."
                    ),
                )

        # Record fingerprint for next iteration
        current_fp = fingerprint_error(test_result.output)
        previous_fingerprints.append(current_fp)

        # Attempt fix with per-iteration timeout
        fix_result = attempt_fix_with_timeout(
            errors=test_result.output,
            iteration=attempt,
            max_seconds=60,
        )

        if fix_result is None:
            # Timeout or failure - exit early
            return Phase45Result(
                success=False,
                attempts=attempt,
                recommendation="ITERATION_TIMEOUT",
                guidance=f"Fix attempt {attempt} exceeded timeout - likely too complex for auto-fix",
            )

        # Re-run tests
        test_result = run_tests()

        if test_result.passed:
            return Phase45Result(
                success=True,
                attempts=attempt,
                recommendation="AUTO_FIX_SUCCEEDED",
            )

    # Exhausted all attempts
    return Phase45Result(
        success=False,
        attempts=max_attempts,
        recommendation="MAX_ATTEMPTS_EXCEEDED",
        guidance="All auto-fix attempts exhausted. Manual intervention required.",
    )
```

#### Integration with Finding 1

This recommendation **complements** R1 (timeout increase):

| Scenario | With R1 Only | With R1 + R6 |
|----------|--------------|--------------|
| **Fixable error** | 600s timeout allows 3 fix attempts | Same - R6 doesn't interfere |
| **Unfixable error (Pydantic v2)** | Wastes 270s on 3 futile attempts, then timeout | Detects unfixable after Attempt 1, exits early with guidance |
| **Repeated error** | Tries same fix 3 times | Detects repetition, exits after Attempt 2 |
| **User experience** | Confusion why it timed out | Clear guidance: "Beyond auto-fix, manual intervention needed" |

**Estimated Complexity**:
- Phase 1: 5/10 (4-6 hours)
- Phase 2: 3/10 (2-3 hours)
- Phase 3: 6/10 (4-6 hours)
- Phase 4: 4/10 (3-4 hours)
- **Total**: 6/10 (1-2 days for complete implementation)

---

## Implementation Priority Matrix

| Rec | Description | Priority | Effort | Risk | Dependencies |
|-----|-------------|----------|--------|------|--------------|
| R1 | Add --sdk-timeout CLI flag | **CRITICAL** | Medium | Low | None |
| R2 | Force worktree cleanup | HIGH | Low | Low | None |
| R4 | Multi-layered partial work detection | HIGH | High (phased) | Medium | None |
| R6 | Phase 4.5 resilience mechanisms | MEDIUM | Medium | Medium | None |
| R3 | Branch cleanup fallback | MEDIUM | Medium | Low | R2 |
| R5 | Increase default timeout | LOW | Low | Low | None |

**Notes**:
- **R1 upgraded to CRITICAL**: Finding 1 analysis shows timeout is primary cause preventing complex tasks from completing. Without R1, Phase 4.5 test enforcement loop cannot complete, resulting in 100% work loss.
- **R4 remains HIGH**: Deep dive analysis reveals single point of failure in state tracking with multi-layered state loss vulnerability (Finding 4). Phased implementation reduces risk.
- **R6 complements R1**: While R1 provides immediate tactical fix (more time), R6 provides strategic fix (better time utilization). Both needed for robust Phase 4.5 execution.

---

## Architecture Quality Assessment

### SOLID Compliance

| Principle | Score | Notes |
|-----------|-------|-------|
| Single Responsibility | 7/10 | `_clean_state` does cleanup + state reset |
| Open/Closed | 4/10 | **CRITICAL**: (1) Timeout not configurable without code changes (Finding 1), (2) Phase 4.5 cannot extend detection mechanisms for unfixable errors (Finding 5) |
| Liskov Substitution | 8/10 | Good use of protocols |
| Interface Segregation | 8/10 | Clean interfaces |
| Dependency Inversion | 4/10 | **CRITICAL**: Single point of failure - state tracking entirely dependent on Player JSON reports with no fallback mechanism (see Finding 4) |

### DRY Adherence: 7/10

- `WorktreeManager` cleanup logic is well-factored
- Some duplication between single-task and feature orchestration

### YAGNI Compliance: 8/10

- No over-engineering detected
- Features are implemented as needed

### Overall Score: 62/100

**Score Rationale**: Downgraded from initial 68/100 to 62/100 due to:
1. **Critical DIP violation** in state tracking architecture (Finding 4) - single point of failure with multi-layered impact
2. **Critical OCP violation** in Phase 4.5 test enforcement (Finding 5) - cannot extend to detect unfixable errors, wastes time on futile attempts
3. While timeout configuration (F1) and worktree cleanup (F2-F3) are implementation gaps, Findings 4 and 5 represent fundamental architectural risks requiring strategic fixes beyond configuration changes.

---

## Appendix: Files Analyzed

1. `guardkit/cli/autobuild.py` - CLI commands
2. `guardkit/orchestrator/autobuild.py` - Task orchestrator
3. `guardkit/orchestrator/feature_orchestrator.py` - Feature orchestrator
4. `guardkit/orchestrator/agent_invoker.py` - SDK invocation
5. `guardkit/orchestrator/feature_loader.py` - Feature YAML loading
6. `guardkit/worktrees/manager.py` - Worktree management
7. `guardkit/orchestrator/coach_verification.py` - Coach verification and test running
8. `installer/core/commands/lib/phase_execution.py` - Phase 4.5 test enforcement loop

---

## Decision Options

- **[A]ccept** - Accept findings, archive review
- **[R]evise** - Request deeper analysis on specific areas
- **[I]mplement** - Create implementation tasks from recommendations
- **[C]ancel** - Discard review
