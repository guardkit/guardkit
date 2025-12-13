# debugging-specialist - Extended Reference

This file contains detailed debugging patterns, technology-specific guidance, and advanced techniques.

**Load this file when**: You need detailed debugging patterns, technology-specific tools, or advanced troubleshooting guidance.

## Technology-Specific Debugging Patterns

### .NET MAUI / C# Debugging

#### Common Issues
```yaml
RX/Observable Issues:
  - RefCount() stream disconnection
  - Subscription lifecycle management
  - Memory leaks from undisposed subscriptions
  - Threading issues (UI thread vs background)

MVVM Binding Issues:
  - PropertyChanged not firing
  - Binding expressions incorrect
  - Data context not propagating
  - Converter errors

Platform-Specific Issues:
  - Android: Activity lifecycle
  - iOS: View controller lifecycle
  - Permissions not granted
```

#### Debugging Tools
```bash
# Check for disposed objects
grep -r "ObjectDisposedException" logs/

# Find subscription leaks
dotnet-trace collect --process-id <pid> --providers "Microsoft-Diagnostics-DiagnosticSource"

# Memory leak detection
dotnet-counters monitor --process-id <pid> --counters System.Runtime
```

### Python Debugging

#### Common Issues
```yaml
Async/Await Issues:
  - Event loop conflicts
  - Blocking calls in async functions
  - Unclosed async generators
  - Task cancellation not handled

Type Issues:
  - None handling
  - Type annotation mismatches
  - Duck typing failures

Dependency Issues:
  - Import errors
  - Version conflicts
  - Missing dependencies
```

#### Debugging Tools
```bash
# Add breakpoint debugging via pytest
pytest --pdb tests/

# Profile performance issues
python -m cProfile -o profile.stats script.py
python -m pstats profile.stats

# Memory profiling
python -m memory_profiler script.py
```

### TypeScript/React Debugging

#### Common Issues
```yaml
State Management:
  - Stale closures in useEffect
  - Missing dependencies in hooks
  - Infinite re-render loops
  - State not updating as expected

Async Issues:
  - Unhandled promise rejections
  - Race conditions
  - Cleanup not performed
  - Memory leaks from listeners

Type Issues:
  - any types masking errors
  - Type narrowing failures
  - Generic constraints too loose
```

#### Debugging Tools
```bash
# React DevTools profiling
npm run build -- --profile

# Memory leak detection
node --inspect-brk node_modules/.bin/jest --runInBand --detectLeaks

# Coverage analysis
npm test -- --coverage --watchAll=false
```

## Debugging Patterns by Issue Type

### Intermittent/Race Condition Bugs

```yaml
Strategy:
  1. Add deterministic timing
  2. Increase logging verbosity
  3. Add artificial delays to expose timing windows
  4. Use synchronization primitives
  5. Reproduce under stress (loop 1000x)

Example:
  // Add delays to expose race condition
  await Task.Delay(100); // Artificial delay
  _logger.LogDebug("Thread {ThreadId} accessing {Resource}",
                   Thread.CurrentThread.ManagedThreadId, resourceName);
```

### Memory Leak Debugging

```yaml
Strategy:
  1. Take heap snapshot before operation
  2. Perform operation (e.g., navigate and return)
  3. Force garbage collection
  4. Take heap snapshot after operation
  5. Compare snapshots for leaked objects

Tools:
  - .NET: dotnet-counters, dotnet-dump
  - Python: tracemalloc, objgraph
  - TypeScript: Chrome DevTools heap profiler
```

### Performance Issues

```yaml
Strategy:
  1. Profile to identify hotspots (don't guess)
  2. Measure before and after optimization
  3. Focus on algorithmic improvements first
  4. Consider caching for repeated computations
  5. Use appropriate data structures

Example:
  // ❌ O(n²) - Nested loops
  foreach (var item in list1)
    foreach (var other in list2)
      if (item.Id == other.Id) { }

  // ✅ O(n) - Dictionary lookup
  var dict = list2.ToDictionary(x => x.Id);
  foreach (var item in list1)
    if (dict.TryGetValue(item.Id, out var other)) { }
```

### Data Flow/State Issues

```yaml
Strategy:
  1. Map complete data flow (source → transformations → destination)
  2. Add logging at each transformation point
  3. Verify input assumptions at each stage
  4. Check for side effects modifying state
  5. Validate state transitions

Example:
  User Input → Validation → Use Case → Repository → Database
       ↓            ↓           ↓            ↓          ↓
     Log A       Log B       Log C        Log D      Log E

  Find where expected value diverges from actual value
```

## Debugging Deliverables

### 1. Root Cause Analysis Document
```markdown
# TASK-XXX Root Cause Analysis

## Summary
[One-sentence root cause]

## Reproduction Steps
1. [Step 1]
2. [Step 2]
3. [Expected vs Actual behavior]

## Investigation Timeline
- [What was tried and what was learned]

## Root Cause
[Detailed explanation with evidence]

## Fix Applied
[Code changes with explanations]

## Verification
- [Test results]
- [Manual verification]

## Prevention
[How to avoid this class of bug in future]
```

### 2. Regression Test
```
Create a test that:
- Reproduces the bug (fails before fix)
- Passes after fix
- Prevents future regressions
- Documents expected behavior
```

### 3. Updated Task Documentation
```markdown
Add to task file:
- Link to root cause analysis
- Link to fix PR/commit
- Lessons learned
- Related issues (if any)
```

## Collaboration Points

### With test-verifier
- Receive failing test reports
- Identify which tests are failing and why
- Request additional test coverage
- Validate fix doesn't break other tests

### With code-reviewer
- Discuss fix approach
- Ensure fix follows architectural principles
- Verify fix is minimal and focused
- Check for potential side effects

### With architectural-reviewer
- Escalate architectural issues uncovered during debugging
- Discuss if bug reveals design flaw
- Propose architectural improvements
- Validate fix aligns with system design

### With task-manager
- Report debugging progress
- Update task status (BLOCKED if investigation ongoing)
- Document findings in task file
- Request clarification if requirements ambiguous

## Success Metrics

```yaml
Debugging Effectiveness:
  time_to_root_cause: "< 2 hours for most bugs"
  fix_success_rate: "> 95% (fix resolves issue)"
  regression_rate: "< 5% (bug doesn't return)"
  test_coverage_added: "> 0 (always add regression test)"

Quality Metrics:
  minimal_fix: "Changes only what's necessary"
  evidence_based: "Fix supported by investigation evidence"
  tested: "Fix verified by automated tests"
  documented: "Root cause and fix documented"
```

## Anti-Patterns to Avoid

### ❌ Shotgun Debugging
```
DON'T:
- Make random changes hoping something works
- Add code without understanding the problem
- Try multiple fixes simultaneously
- Skip root cause analysis

DO:
- Form hypothesis, test it, learn, repeat
- Understand why each change should help
- Test one thing at a time
- Always identify root cause first
```

### ❌ Symptom Fixes
```
DON'T:
- Add workarounds without understanding why they're needed
- Catch and ignore exceptions
- Add arbitrary delays or retries
- Band-aid over architectural issues

DO:
- Fix the underlying problem
- Handle exceptions appropriately
- Understand timing requirements
- Refactor if architecture is flawed
```

### ❌ Debugging in Production
```
DON'T:
- Test fixes directly in production
- Add debug logging to production without cleanup
- Deploy without testing
- Make changes without version control

DO:
- Reproduce in development/test environment
- Use proper logging levels (Debug/Trace for investigation)
- Test thoroughly before deployment
- Commit all changes with clear messages
```

## When to Escalate

Escalate to human developer when:
1. **Cannot reproduce** - Bug is truly intermittent and cannot be triggered consistently
2. **Multiple root causes** - Evidence points to several interacting issues
3. **Architectural redesign needed** - Fix requires significant refactoring
4. **Security implications** - Bug has security consequences
5. **Time limit exceeded** - 2+ hours of investigation without clear progress

## Best Practices

1. **Always reproduce first** - No fix without reproduction
2. **Evidence over intuition** - Use logs, tests, profiling data
3. **Minimal fixes** - Change only what's necessary
4. **Test-driven** - Add regression tests for every fix
5. **Document thoroughly** - Future you will thank present you
6. **Learn patterns** - Build mental library of common issues
7. **Systematic approach** - Don't skip phases of methodology

## Related Agents

The debugging-specialist coordinates with four critical agents to ensure comprehensive issue resolution:

### 1. test-verifier Integration

**Purpose**: Receive failing test reports and coordinate fix verification

**Flow Diagram**:
```yaml
workflow:
  - name: Test Failure Detection
    steps:
      - test-verifier: Runs test suite
      - test-verifier: Detects failures (exit code != 0)
      - test-verifier: Generates failure report
      - test-verifier: Invokes debugging-specialist

  - name: Debugging Session
    steps:
      - debugging-specialist: Receives failure context
      - debugging-specialist: Analyzes root cause
      - debugging-specialist: Applies fix
      - debugging-specialist: Requests verification

  - name: Fix Verification
    steps:
      - test-verifier: Re-runs affected tests
      - test-verifier: Reports success/failure
      - debugging-specialist: Iterates if needed (max 3 attempts)
```

**Handoff Payload - Test Failure to Debugging**:
```json
{
  "trigger": "test_failure",
  "task_id": "TASK-1234",
  "failure_context": {
    "test_framework": "pytest",
    "failed_tests": [
      {
        "test_name": "test_user_authentication",
        "test_file": "tests/auth/test_login.py",
        "error_type": "AssertionError",
        "error_message": "Expected status 200, got 401",
        "stack_trace": "..."
      }
    ],
    "environment": {
      "python_version": "3.11.4",
      "dependencies": {"flask": "2.3.2"}
    }
  },
  "priority": "high"
}
```

**Verification Request Payload**:
```json
{
  "request_type": "verify_fix",
  "task_id": "TASK-1234",
  "fix_summary": "Fixed token validation in LoginHandler.authenticate()",
  "files_changed": ["src/auth/login_handler.py"],
  "tests_to_rerun": ["tests/auth/test_login.py::test_user_authentication"],
  "attempt_number": 1,
  "max_attempts": 3
}
```

### 2. code-reviewer Integration

**Purpose**: Ensure fixes meet code quality standards before merging

**Flow Diagram**:
```yaml
workflow:
  - name: Fix Verification Complete
    steps:
      - debugging-specialist: Tests pass
      - debugging-specialist: Prepares fix summary
      - debugging-specialist: Requests code review

  - name: Code Review
    steps:
      - code-reviewer: Reviews changed files
      - code-reviewer: Checks against coding standards
      - code-reviewer: Approves or requests changes
```

**Review Request Payload**:
```json
{
  "request_type": "review_fix",
  "task_id": "TASK-1234",
  "root_cause": "Token validator incorrectly checked expiry timestamp",
  "fix_description": "Updated TokenValidator.is_valid() to use UTC timestamps",
  "files_changed": ["src/auth/token_validator.py"],
  "tests_added": ["tests/auth/test_token_validator.py::test_utc_handling"],
  "verification_status": "all_tests_pass",
  "risk_assessment": "low"
}
```

### 3. architectural-reviewer Integration

**Purpose**: Escalate design flaws discovered during debugging

**Escalation Criteria**:
- Root cause violates SOLID principles
- Fix requires changes to >5 files
- Issue indicates missing abstraction layer
- Performance fix requires architectural change
- Security vulnerability in core design

**Escalation Payload**:
```json
{
  "escalation_type": "design_flaw",
  "task_id": "TASK-1234",
  "original_issue": "Race condition in order processing",
  "root_cause_analysis": {
    "symptom": "Duplicate order submissions",
    "immediate_cause": "No idempotency check",
    "architectural_gap": "No distributed locking mechanism"
  },
  "recommended_solution": {
    "approach": "Implement Saga pattern",
    "effort_estimate": "3-5 days"
  },
  "decision_needed": "Apply quick fix or block for proper solution?"
}
```

### 4. task-manager Integration

**Purpose**: Track debugging progress and update task status

**Status Update Payload**:
```json
{
  "update_type": "debug_progress",
  "task_id": "TASK-1234",
  "phase": "root_cause_analysis",
  "progress": {
    "current_phase": 3,
    "total_phases": 6,
    "elapsed_time_minutes": 45,
    "estimated_remaining_minutes": 30
  },
  "findings": [
    "Reproduced issue in local environment",
    "Identified timezone mismatch as root cause"
  ],
  "confidence": "high"
}
```

### Coordination Patterns

#### Pattern 1: Sequential Pipeline (Phase 4.5)
```
test-verifier → debugging-specialist → test-verifier → code-reviewer
  (Failure)       (Root Cause)         (Verify Fix)     (Review)
```

#### Pattern 2: Escalation Path
```
debugging-specialist → architectural-reviewer → task-manager
  (Design Flaw)         (Architectural Review)   (New Task Created)
```

## Debugging Workflow Integration

### Phase 4.5: Test Failure Trigger

```yaml
task_work_flow:
  - phase: 4
    agent: implementation-specialist
    output: Code changes committed

  - phase: 4.5
    agent: test-verifier
    decision_tree:
      - if: tests_pass
        then: proceed_to_phase_5
      - if: tests_fail
        then: invoke_debugging_specialist

  - phase: 4.5b
    agent: debugging-specialist
    trigger: test_failure_detected
    blocking: true  # Workflow paused until resolution
    max_attempts: 3
    escalation:
      - if: attempts >= max_attempts
        then: notify_human

  - phase: 5
    agent: code-reviewer
    precondition: all_tests_pass
```

### Task Blocking Behavior

When debugging is active, the task is blocked:

```python
task_states = {
    "initial": "in_progress",
    "test_failure": "debugging_in_progress",  # BLOCKED
    "fix_applied": "verifying_fix",           # BLOCKED
    "tests_pass": "pending_review",           # UNBLOCKED
}
```

**DO**: Respect blocking behavior
```python
# Wait for debugging to complete before proceeding
if task.is_debugging:
    wait_for_resolution()
    then_proceed_to_review()
```

**DON'T**: Bypass debugging
```python
# VIOLATION: Tests are failing!
if task.is_debugging:
    continue_with_next_phase()  # Never do this
```

## Advanced Debugging Patterns

### 1. Distributed System Debugging

**Challenge**: Tracing errors across microservices

**DO: Correlation ID Tracking**
```python
import uuid
from contextvars import ContextVar

correlation_id: ContextVar[str] = ContextVar('correlation_id', default=None)

class DistributedTracer:
    def start_trace(self):
        trace_id = str(uuid.uuid4())
        correlation_id.set(trace_id)
        return trace_id

    def propagate_context(self, outgoing_request):
        trace_id = correlation_id.get()
        outgoing_request.headers['X-Correlation-ID'] = trace_id
        return outgoing_request

    def log_with_context(self, message):
        trace_id = correlation_id.get()
        logger.info(f"[trace={trace_id}] {message}")

# Grep logs across services
# grep "trace=a1b2c3d4" order-service.log payment-service.log
```

**DON'T: Isolated Logging**
```python
# No way to correlate logs across services
def process_order(order):
    logging.info(f"Processing order {order.id}")  # Lost trace context
```

### 2. CI/CD Pipeline Debugging

**Challenge**: Flaky tests that pass locally but fail in CI

**DO: Environment Parity Checking**
```python
class EnvironmentValidator:
    def compare_environments(self, local_env, ci_env):
        discrepancies = []

        # Check Python version
        if local_env['python_version'] != ci_env['python_version']:
            discrepancies.append("Python version mismatch")

        # Check case sensitivity (macOS vs Linux)
        if platform.system() == 'Darwin' and ci_env['os'] == 'Linux':
            discrepancies.append("Case sensitivity difference")

        return discrepancies
```

**DON'T: Ignore Environment Differences**
```python
# Fails in CI due to different temp directory permissions
upload_file('/tmp/test.txt')  # Works on macOS, fails on Linux
```

### 3. Concurrency Debugging

**Challenge**: Deadlocks and race conditions

**DO: Deadlock Prevention with Lock Ordering**
```csharp
public class DeadlockSafeResourceManager
{
    public void AcquireLocks(params string[] resourceIds)
    {
        // Always acquire locks in sorted order
        var sortedIds = resourceIds.OrderBy(id => id).ToList();

        foreach (var id in sortedIds)
        {
            if (!Monitor.TryEnter(lockObj, TimeSpan.FromSeconds(5)))
            {
                ReleaseAcquiredLocks();
                throw new DeadlockException($"Timeout on {id}");
            }
        }
    }
}
```

**DON'T: Unordered Lock Acquisition**
```csharp
// Classic deadlock scenario
lock (_lockA)  // Thread 1 acquires A
{
    lock (_lockB)  // Thread 1 waits for B (held by Thread 2)
    {
        // Deadlock!
    }
}
```

## Debugging Checklist Template

Copy-paste this checklist at the start of any debugging session:

```markdown
# Debugging Session Checklist

**Task ID**: TASK-_____
**Issue**: ___________________________________________
**Started**: ______ (date/time)

---

## Phase 1: Issue Reproduction ⏱️ 15 min

- [ ] Collected error message/stack trace
- [ ] Reproduced locally: _____
- [ ] Reproduction rate: ___/10 attempts

---

## Phase 2: Context Gathering ⏱️ 20 min

- [ ] Read recent code changes
- [ ] Identified files involved
- [ ] Last known working version: _______
- [ ] Suspect commit: _______

---

## Phase 3: Root Cause Analysis ⏱️ 30 min

**Hypothesis 1**: ___________________
- [ ] Tested: pass/fail
- [ ] Evidence: ___________________

**Root Cause** (confirmed): ___________________

---

## Phase 4: Fix Development ⏱️ 30 min

**Fix Strategy**: ___________________
**Files to Modify**: ___________________
**Risk Assessment**: Low / Medium / High

---

## Phase 5: Verification ⏱️ 10 min

- [ ] Failing test now passes
- [ ] All tests pass: ___/___
- [ ] New tests added

---

## Phase 6: Documentation ⏱️ 10 min

- [ ] Root cause documented
- [ ] Fix approach explained
- [ ] Commit message written

**Total Time**: _____ min
```

**Quick command**:
```bash
/debug TASK-1234 --create-checklist
```
