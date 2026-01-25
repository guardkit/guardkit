# Architectural Review Report: TASK-REV-FB08

**Review Mode:** Architectural
**Review Depth:** Comprehensive
**Date:** 2026-01-11
**Reviewer:** Claude Opus 4.5

---

## Executive Summary

This review analyzed two configuration propagation bugs in the GuardKit autobuild system:

1. **SDK Timeout Bug (CRITICAL)**: The `--sdk-timeout` CLI flag and YAML config are ignored; a hardcoded 600s default is always used in `TaskWorkInterface`
2. **enable_pre_loop Bug (HIGH)**: The `enable_pre_loop: false` setting is never read from feature YAML or task frontmatter; it defaults to `True`

Both bugs have been **root-caused** with specific file/line numbers identified. The issues stem from incomplete configuration cascade implementation.

---

## Bug 1: SDK Timeout Not Propagating

### Root Cause

**Location:** `guardkit/orchestrator/quality_gates/task_work_interface.py:48-49`

```python
# SDK timeout in seconds (default: 600s, can be overridden via env var or constructor)
DEFAULT_SDK_TIMEOUT = int(os.environ.get("GUARDKIT_SDK_TIMEOUT", "600"))
```

**Problem:** The `TaskWorkInterface` class uses `DEFAULT_SDK_TIMEOUT` (600s) as its default, but **no caller passes the `sdk_timeout` parameter** when instantiating it.

### Propagation Trace

| Layer | File:Line | Status | Value |
|-------|-----------|--------|-------|
| CLI | `cli/autobuild.py:402-407` | ✅ Works | `--sdk-timeout 1800` parsed |
| CLI→FeatureOrchestrator | `cli/autobuild.py:498` | ✅ Works | Passed as `sdk_timeout=sdk_timeout` |
| FeatureOrchestrator | `feature_orchestrator.py:268` | ✅ Works | Stored as `self.sdk_timeout` |
| FeatureOrchestrator→AutoBuild | `feature_orchestrator.py:900` | ✅ Works | `sdk_timeout=effective_sdk_timeout` |
| AutoBuildOrchestrator | `autobuild.py:380` | ✅ Works | Stored as `self.sdk_timeout` |
| **AutoBuild→PreLoopGates** | `autobuild.py:722-723` | ❌ **BUG** | **NOT PASSED** |
| **PreLoopGates→TaskWorkInterface** | `pre_loop.py:151` | ❌ **BUG** | **NOT PASSED** |

### Bug Location #1: `autobuild.py:722-723`

```python
# BUG: PreLoopQualityGates initialized without sdk_timeout
if self._pre_loop_gates is None:
    self._pre_loop_gates = PreLoopQualityGates(str(worktree.path))
    # MISSING: sdk_timeout parameter not passed!
```

**Should be:**
```python
if self._pre_loop_gates is None:
    self._pre_loop_gates = PreLoopQualityGates(
        str(worktree.path),
        sdk_timeout=self.sdk_timeout,  # Pass through
    )
```

### Bug Location #2: `pre_loop.py:151`

```python
# BUG: TaskWorkInterface initialized without sdk_timeout
self._interface = interface or TaskWorkInterface(self.worktree_path)
# MISSING: sdk_timeout parameter not passed!
```

**Should be:**
```python
self._interface = interface or TaskWorkInterface(
    self.worktree_path,
    sdk_timeout_seconds=self.sdk_timeout,
)
```

### Bug Location #3: `pre_loop.py:135-151`

The `PreLoopQualityGates.__init__` method doesn't accept or store an `sdk_timeout` parameter:

```python
def __init__(
    self,
    worktree_path: str,
    interface: Optional[TaskWorkInterface] = None,
):  # MISSING: sdk_timeout parameter
```

### Evidence from Logs

```
# CLI shows timeout received:
INFO:guardkit.orchestrator.autobuild:AutoBuildOrchestrator initialized:
    ... sdk_timeout=1200s ...

# But TaskWorkInterface uses hardcoded default:
ERROR:guardkit.orchestrator.quality_gates.task_work_interface:SDK timeout after 600s
```

---

## Bug 2: enable_pre_loop Flag Ignored

### Root Cause

**Location:** `guardkit/orchestrator/feature_orchestrator.py:894-901`

The `FeatureOrchestrator._execute_task()` method creates `AutoBuildOrchestrator` instances **without passing the `enable_pre_loop` parameter**, causing it to default to `True`.

```python
# BUG: enable_pre_loop never read from config or passed to AutoBuildOrchestrator
task_orchestrator = AutoBuildOrchestrator(
    repo_root=self.repo_root,
    max_turns=self.max_turns,
    resume=False,
    existing_worktree=worktree,
    worktree_manager=self._worktree_manager,
    sdk_timeout=effective_sdk_timeout,
    # MISSING: enable_pre_loop parameter!
)
```

### Missing Configuration Cascade

The `enable_pre_loop` flag should follow this cascade:
1. **CLI flag** (highest priority) - **NOT IMPLEMENTED**
2. **Task frontmatter** `autobuild.enable_pre_loop` - **NOT READ**
3. **Feature YAML** `autobuild.enable_pre_loop` - **NOT READ**
4. **Default** (`True`) - **Only this is used**

### Bug Location #1: `cli/autobuild.py`

The `feature` command has no `--enable-pre-loop` / `--no-pre-loop` option:

```python
@click.option(
    "--sdk-timeout",
    ...
)
# MISSING: --enable-pre-loop / --no-pre-loop option
@click.pass_context
def feature(ctx, feature_id, ...):
```

### Bug Location #2: `feature_orchestrator.py:894-901`

Even if CLI had the option, FeatureOrchestrator doesn't:
- Read `enable_pre_loop` from feature YAML
- Read `enable_pre_loop` from task frontmatter
- Pass `enable_pre_loop` to AutoBuildOrchestrator

### Evidence from Logs

```yaml
# Feature YAML config:
autobuild:
  enable_pre_loop: false  # Ignored!

# AutoBuildOrchestrator log:
INFO:guardkit.orchestrator.autobuild:AutoBuildOrchestrator initialized:
    ... enable_pre_loop=True ...  # Default used instead
```

---

## Configuration Cascade Analysis

### Current Implementation Status

| Config Source | sdk_timeout | enable_pre_loop |
|---------------|-------------|-----------------|
| CLI flag | ✅ Parsed | ❌ Not implemented |
| Task frontmatter | ✅ Read (lines 889-891) | ❌ Not read |
| Feature YAML | ❌ Not read | ❌ Not read |
| Default | ✅ 600s | ✅ True |

### Expected Configuration Cascade

Both settings should follow this priority (highest to lowest):
1. **CLI flag** - Explicit user override for this run
2. **Task frontmatter** - Task-specific override
3. **Feature YAML** - Feature-level default
4. **Code default** - Fallback value

---

## Test Coverage Gaps

### Missing Unit Tests

| Test File | Missing Coverage |
|-----------|-----------------|
| `test_pre_loop_delegation.py` | No tests for sdk_timeout propagation |
| `test_autobuild_orchestrator.py` | No tests for enable_pre_loop override |
| `test_feature_orchestrator.py` | No tests for config cascade |
| `test_task_work_interface.py` | No tests for sdk_timeout parameter |

### Recommended Test Cases

1. **sdk_timeout propagation**:
   - CLI flag overrides default
   - Task frontmatter overrides default (when CLI is None)
   - Default used when no override specified

2. **enable_pre_loop propagation**:
   - CLI flag overrides feature YAML
   - Feature YAML overrides default
   - Task frontmatter overrides feature YAML

---

## Recommendations

### Fix 1: SDK Timeout Propagation (Critical)

**Files to modify:**
1. `guardkit/orchestrator/quality_gates/pre_loop.py`
   - Add `sdk_timeout` parameter to `__init__`
   - Pass to `TaskWorkInterface`

2. `guardkit/orchestrator/autobuild.py`
   - Pass `sdk_timeout` when creating `PreLoopQualityGates`

**Estimated effort:** 2-3 hours

### Fix 2: enable_pre_loop Propagation (High)

**Files to modify:**
1. `guardkit/cli/autobuild.py`
   - Add `--enable-pre-loop` / `--no-pre-loop` CLI options

2. `guardkit/orchestrator/feature_orchestrator.py`
   - Read `enable_pre_loop` from feature YAML
   - Read `enable_pre_loop` from task frontmatter (with cascade)
   - Pass to `AutoBuildOrchestrator`

**Estimated effort:** 4-6 hours

### Fix 3: Test Coverage

**Files to create/modify:**
1. `tests/unit/test_config_propagation.py` (new)
   - End-to-end config cascade tests
   - SDK timeout propagation tests
   - enable_pre_loop propagation tests

**Estimated effort:** 3-4 hours

---

## Implementation Tasks

Based on this review, the following implementation tasks are recommended:

### TASK-FB-FIX-009: Fix sdk_timeout propagation to TaskWorkInterface
- **Priority:** Critical
- **Complexity:** 3
- **Scope:**
  - Add `sdk_timeout` parameter to `PreLoopQualityGates.__init__`
  - Pass `sdk_timeout` from `AutoBuildOrchestrator` to `PreLoopQualityGates`
  - Pass `sdk_timeout` from `PreLoopQualityGates` to `TaskWorkInterface`

### TASK-FB-FIX-010: Implement enable_pre_loop configuration cascade
- **Priority:** High
- **Complexity:** 5
- **Scope:**
  - Add `--enable-pre-loop` / `--no-pre-loop` CLI options
  - Read `enable_pre_loop` from feature YAML
  - Read `enable_pre_loop` from task frontmatter
  - Implement cascade priority (CLI > task > feature > default)
  - Pass to `AutoBuildOrchestrator`

### TASK-FB-FIX-011: Add config propagation integration tests
- **Priority:** Medium
- **Complexity:** 4
- **Scope:**
  - Test sdk_timeout cascade
  - Test enable_pre_loop cascade
  - Verify values reach TaskWorkInterface

---

## Architectural Assessment

### SOLID Compliance

| Principle | Score | Notes |
|-----------|-------|-------|
| Single Responsibility | 8/10 | Classes are well-focused |
| Open/Closed | 6/10 | Config extension requires code changes |
| Liskov Substitution | 9/10 | Interfaces are consistent |
| Interface Segregation | 8/10 | Appropriate interface boundaries |
| Dependency Inversion | 7/10 | DI used but inconsistently for config |

### DRY Compliance: 7/10

Configuration default values are duplicated:
- `DEFAULT_SDK_TIMEOUT = 600` in `task_work_interface.py`
- `sdk_timeout: int = 600` in `autobuild.py` (line 317)
- `sdk_timeout: int = 600` default in CLI

**Recommendation:** Create a `config.py` with centralized defaults.

### YAGNI Compliance: 9/10

No unnecessary complexity detected. The configuration cascade is needed functionality that was simply not fully implemented.

### Overall Score: 76/100

---

## Decision Checkpoint

Based on this comprehensive review:

- **[A]ccept** - Archive findings, no immediate action
- **[R]evise** - Request deeper analysis on specific component
- **[I]mplement** - Create implementation tasks for fixes
- **[C]ancel** - Discard review

**Recommendation:** Select **[I]mplement** to create the three fix tasks (TASK-FB-FIX-009, 010, 011) to resolve these configuration propagation bugs.
