# Review Report: TASK-REV-FB09

## Executive Summary

**Root Cause Identified**: The `_write_task_work_results()` method is implemented but **never invoked**. This is a critical integration gap where TASK-SDK-003 created the method but failed to wire it into the execution flow.

**Architecture Score**: 45/100 (Below threshold - requires remediation)

**Critical Finding**: The delegation flow in `_invoke_task_work_implement()` successfully executes task-work, but neither:
1. The task-work command writes `task_work_results.json` (it doesn't know about this GuardKit-specific artifact), nor
2. The `AgentInvoker` calls `_write_task_work_results()` after successful completion

This results in Coach failing validation because the file it expects doesn't exist.

## Review Details

- **Mode**: Architectural Review
- **Depth**: Comprehensive
- **Duration**: ~45 minutes
- **Files Analyzed**: 12 files, ~4,500 lines of code
- **Task ID**: TASK-REV-FB09

## Findings

### Finding 1: Dead Code - `_write_task_work_results()` Never Called (CRITICAL)

**Evidence**:
```bash
# Search for actual calls (excluding docstring examples)
grep -n "self._write_task_work_results" guardkit/orchestrator/agent_invoker.py | grep -v '>>>'
# OUTPUT: (empty - no actual invocations)
```

**Location**: `guardkit/orchestrator/agent_invoker.py:2012-2091`

**Impact**: Complete failure of Coach validation - the Coach cannot verify quality gates because the results file doesn't exist.

**Root Cause Chain**:
1. TASK-SDK-003 implemented `_write_task_work_results()` method ✅
2. TASK-SDK-003 acceptance criteria checked "Unit tests for writer" ✅
3. TASK-SDK-003 deferred "Integration test with Coach validator" to TASK-SDK-004
4. **Missing**: No acceptance criterion for "Method is called in actual flow"
5. TASK-SDK-004 integration tests likely **mocked** the existence of the file
6. Result: Method exists but is never invoked in production

### Finding 2: Incorrect Assumption in Code Comment

**Evidence** (`agent_invoker.py:435-437`):
```python
if result.success:
    # Create Player report from task-work results
    # task-work creates task_work_results.json, but orchestrator expects
    # player_turn_{turn}.json - this bridges the gap
    self._create_player_report_from_task_work(task_id, turn, result)
```

**Issue**: The comment states "task-work creates task_work_results.json" - this is **incorrect**. The `/task-work` command is a GuardKit slash command that doesn't know about this artifact. The `AgentInvoker` should write this file after parsing the task-work output.

### Finding 3: Missing Integration in `_invoke_task_work_implement()` Return Path

**Evidence** (`agent_invoker.py:1593-1720`):
```python
async def _invoke_task_work_implement(
    self,
    task_id: str,
    mode: str = "standard",
) -> TaskWorkResult:
    # ... SDK invocation ...

    logger.info(f"task-work completed successfully for {task_id}")
    return TaskWorkResult(
        success=True,
        output=self._parse_task_work_output(output_text),
    )
    # ❌ MISSING: self._write_task_work_results(task_id, parsed_result)
```

The method parses the output via `_parse_task_work_output()` but never writes the results to the expected location.

### Finding 4: `_create_player_report_from_task_work()` Graceful Fallback Masks the Bug

**Evidence** (`agent_invoker.py:1049-1094`):
```python
# Try to read task_work_results.json for richer data
if task_work_results_path.exists():
    # ... read and use data ...
else:
    # Fallback: detect git changes
    logger.info(
        f"task_work_results.json not found, detecting git changes for {task_id}"
    )
```

The fallback to git change detection provides partial functionality, masking the integration bug. However, this fallback provides incomplete data to Coach (missing test results, coverage, quality gate status).

### Finding 5: Coach Validator Receives Incomplete Data

**Evidence** (`coach_validator.py:395-413`):
```python
results_path = self.worktree_path / ".guardkit" / "autobuild" / task_id / "task_work_results.json"

if not results_path.exists():
    return {
        "error": f"task_work_results.json not found at {results_path}",
        "task_id": task_id,
    }
```

Coach returns an error when the file doesn't exist, causing validation to fail even when implementation succeeded.

## Architecture Assessment

### SOLID Compliance: 55/100

| Principle | Score | Notes |
|-----------|-------|-------|
| **S**ingle Responsibility | 60 | `_invoke_task_work_implement()` does invocation but not result persistence - unclear ownership |
| **O**pen/Closed | 65 | Good extensibility via TaskWorkStreamParser |
| **L**iskov Substitution | 70 | TaskWorkResult interface consistent |
| **I**nterface Segregation | 50 | Large AgentInvoker class with many responsibilities |
| **D**ependency Inversion | 35 | Direct file path construction instead of using injected paths |

### DRY Adherence: 60/100

- **Violation**: Multiple places construct the same path (`worktree_path / ".guardkit" / "autobuild" / task_id / "task_work_results.json"`)
- **Mitigation Available**: `TaskArtifactPaths.task_work_results_path()` exists but not consistently used
- **Finding**: Some methods use centralized paths, others construct manually

### YAGNI Compliance: 70/100

- **Concern**: `_write_task_work_results()` is implemented but unused - technically dead code
- **However**: The code will be needed, it's just not integrated
- **Observation**: Stream parser infrastructure ready but not fully utilized

### Overall Architecture Score: 45/100

**Below minimum threshold (60)**. The implementation is **incomplete** - the writer exists but is not wired into the execution flow.

## Root Cause Analysis

```
TASK-SDK-003: "Create task_work_results.json writer"
│
├── Implementation: ✅ Method created
├── Unit Tests: ✅ Writer tests pass
├── Integration Test: ⏳ Deferred to TASK-SDK-004
│
└── Missing Acceptance Criterion:
    "Method is actually invoked in _invoke_task_work_implement() flow"
```

**Why did this slip through?**

1. **Task scoping**: TASK-SDK-003 was scoped to "create the writer" not "integrate the writer"
2. **Deferred integration testing**: TASK-SDK-004 was supposed to catch this
3. **Mocked tests**: Unit tests verified the method works when called, but not that it's called
4. **Graceful fallback**: The git-based fallback provided partial functionality, making failures less obvious

## Recommendations

### Recommendation 1: Call `_write_task_work_results()` After Successful Task-Work (CRITICAL)

**Priority**: P0 - Blocking

**Location**: `agent_invoker.py:_invoke_task_work_implement()`, after line 1675

**Change**:
```python
# After line 1675 (successful task-work)
output_text = "\n".join(collected_output)

# Parse output using stream parser for structured data
parser = TaskWorkStreamParser()
parser.parse_message(output_text)
parsed_result = parser.to_result()

# Write task_work_results.json for Coach validation
self._write_task_work_results(task_id, parsed_result)

logger.info(f"task-work completed successfully for {task_id}")
return TaskWorkResult(
    success=True,
    output=parsed_result,  # Use parsed result instead of _parse_task_work_output
)
```

**Files Modified**: 1
- `guardkit/orchestrator/agent_invoker.py`

**Estimated Lines**: ~8 lines added/modified

**Complexity**: 2/10 (Simple integration fix)

### Recommendation 2: Fix Incorrect Code Comment

**Priority**: P1 - Important

**Location**: `agent_invoker.py:435-437`

**Change**:
```python
if result.success:
    # Create Player report from task-work results
    # The AgentInvoker writes task_work_results.json after parsing
    # task-work output. This method transforms it to player_turn_{turn}.json
    # format expected by the orchestrator.
    self._create_player_report_from_task_work(task_id, turn, result)
```

### Recommendation 3: Use TaskWorkStreamParser Instead of _parse_task_work_output()

**Priority**: P2 - Enhancement

**Rationale**: `TaskWorkStreamParser` (from TASK-SDK-002) provides richer parsing than the basic `_parse_task_work_output()` regex-based parser.

**Change**: Replace `_parse_task_work_output(output_text)` with `TaskWorkStreamParser().parse_message(output_text).to_result()`

### Recommendation 4: Add Integration Test for Full Flow

**Priority**: P1 - Important

**Location**: `tests/integration/test_sdk_delegation.py`

**Test Case**:
```python
async def test_task_work_results_written_after_successful_invocation():
    """Verify task_work_results.json is written in actual flow."""
    invoker = AgentInvoker(worktree_path=mock_worktree)

    result = await invoker._invoke_task_work_implement("TASK-001", mode="tdd")

    assert result.success
    results_path = mock_worktree / ".guardkit" / "autobuild" / "TASK-001" / "task_work_results.json"
    assert results_path.exists(), "task_work_results.json should be written after successful invocation"

    # Verify content has required fields for Coach
    content = json.loads(results_path.read_text())
    assert "quality_gates" in content
    assert "tests_passed" in content.get("quality_gates", {})
```

## Decision Matrix

| Recommendation | Impact | Effort | Risk | Priority |
|----------------|--------|--------|------|----------|
| Call `_write_task_work_results()` | Critical | Low (~8 LOC) | Low | P0 |
| Fix code comment | Medium | Trivial | None | P1 |
| Use TaskWorkStreamParser | Medium | Low | Low | P2 |
| Add integration test | High | Medium | None | P1 |

## Implementation Plan

### Phase 1: Critical Fix (Immediate)
1. Add `_write_task_work_results()` call in `_invoke_task_work_implement()`
2. Update code comment to reflect actual behavior
3. Verify with manual test

### Phase 2: Test Coverage (Follow-up)
1. Add integration test for full flow
2. Ensure test doesn't mock the results file creation
3. Update TASK-SDK-004 if needed

### Phase 3: Enhancement (Optional)
1. Replace `_parse_task_work_output()` with `TaskWorkStreamParser`
2. Consider deprecating `_parse_task_work_output()` if redundant

## Appendix

### Files Analyzed

| File | Lines | Purpose |
|------|-------|---------|
| `guardkit/orchestrator/agent_invoker.py` | 2136 | Main invocation logic |
| `guardkit/orchestrator/autobuild.py` | 2145 | Orchestration flow |
| `guardkit/orchestrator/quality_gates/coach_validator.py` | 800+ | Coach validation |
| `guardkit/orchestrator/quality_gates/task_work_interface.py` | 748 | Task-work interface |
| `guardkit/orchestrator/paths.py` | 400+ | Path utilities |
| `tests/unit/test_agent_invoker.py` | 3500+ | Unit tests |
| `tests/integration/test_sdk_delegation.py` | 700+ | Integration tests |

### Related Tasks

| Task ID | Title | Relevance |
|---------|-------|-----------|
| TASK-SDK-003 | Create task_work_results.json writer | Created the method (not integrated) |
| TASK-SDK-004 | Integration testing | Should have caught this |
| TASK-REV-fb02 | Task-work results not found analysis | Previous analysis of same issue |
| TASK-REV-fb03 | Delegation regression analysis | Related root cause |

### Evidence Files

- `docs/reviews/feature-build/feature_build_after_FB08.md` - Shows "task_work_results.json not found" error
- `tasks/completed/sdk-delegation-fix/TASK-SDK-003/TASK-SDK-003-results-writer.md` - Task completion without integration

---

**Review Completed**: 2026-01-12
**Reviewer**: Claude (Architectural Review Mode)
**Decision**: Implementation required - single integration fix will resolve issue
