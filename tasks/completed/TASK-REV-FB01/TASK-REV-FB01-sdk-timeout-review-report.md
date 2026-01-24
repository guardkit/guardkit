# Review Report: TASK-REV-FB01 - SDK Timeout Configuration

## Executive Summary

This decision analysis reviews whether the default SDK timeout for `/feature-build` should be increased. The evidence shows a single observed timeout at 900s that required a retry, adding 14.5 minutes of overhead to a 23-minute successful run.

**Key Finding**: The codebase currently has **inconsistent timeout defaults** across multiple locations (600s, 900s, 1800s). This inconsistency is a more pressing issue than the specific timeout value itself.

**Recommendation**: **Harmonize defaults first** (Option B), then evaluate if further adjustment needed.

---

## Review Details

- **Mode**: Decision Analysis
- **Depth**: Standard (1-2 hours)
- **Reviewer**: task-review agent
- **Date**: 2026-01-24

---

## Current State Analysis

### Timeout Configuration Locations

| Location | Default | Notes |
|----------|---------|-------|
| `agent_invoker.py:97` | 1800s (30 min) | `DEFAULT_SDK_TIMEOUT` env-backed |
| `autobuild.py:320` | 900s (15 min) | Constructor parameter default |
| `feature_orchestrator.py:1233` | 900s (15 min) | Fallback when no frontmatter |
| `autobuild.py` CLI help | 600s (10 min) | **OUTDATED** - confuses users |

**Problem**: Four different "defaults" create confusion:
1. User expects 600s (per CLI help)
2. Orchestrator uses 900s
3. AgentInvoker has 1800s as fallback
4. Task frontmatter can override all of these

### Resolution Cascade

The actual timeout used follows this cascade:
```
CLI --sdk-timeout flag
    → task frontmatter autobuild.sdk_timeout
        → feature YAML autobuild.sdk_timeout (for feature mode)
            → orchestrator default (900s)
                → AgentInvoker DEFAULT_SDK_TIMEOUT (1800s - rarely reached)
```

---

## Evidence Analysis

### Timeout Incident: TASK-FHA-003

| Metric | Value |
|--------|-------|
| Task | TASK-FHA-003: Create FastAPI app entry point |
| Timeout occurred at | 900s |
| State at timeout | Phase 5: Code Review |
| Tests passing | 103 |
| Coverage | 92% |
| Retry attempt | Turn 2 - succeeded |
| Overhead from retry | ~14.5 minutes |

**Key Observation**: Task was actively progressing (Phase 5, 92% coverage) when timeout hit. It was NOT stuck.

### Successful Run Metrics

From `finally_success.md`:

| Task | Duration | Turns | Notes |
|------|----------|-------|-------|
| TASK-FHA-001 | ~365s (6 min) | 1 | Scaffolding - fast |
| TASK-FHA-002 | ~650s (11 min) | 1 | Core configuration |
| TASK-FHA-003 | ~560s retry | 1 (after retry) | FastAPI app - most complex |
| TASK-FHA-004 | ~540s (9 min) | 1 | Health module |
| TASK-FHA-005 | ~270s (4.5 min) | 1 | Testing setup |

**Total successful run**: 23m 24s
**Run with timeout + retry**: 37m 55s (62% longer)

### Task Duration Distribution

```
       0s        300s       600s       900s      1200s
       |----------|----------|----------|----------|
FHA-001 [====]                                        6 min
FHA-005     [====]                                    4.5 min
FHA-004            [=========]                        9 min
FHA-002                [===========]                  11 min
FHA-003                        [=============|TIMEOUT|] 15+ min
                                             ^900s limit
```

**Observation**: FHA-003 was the outlier, running 50%+ longer than average due to comprehensive test suite (103 tests).

---

## Options Evaluation

### Option A: Keep Current 900s Default

**Description**: Rely on retry mechanism to handle occasional timeouts.

**Pros**:
- No changes required
- Retry mechanism works correctly
- Faster failure detection when tasks are genuinely stuck

**Cons**:
- ~14.5 minute overhead per retry occurrence
- Wastes API tokens reprocessing context
- Poor UX when timeout happens on "almost done" tasks

**Risk**: Low
**Effort**: None
**Score**: 5/10

### Option B: Harmonize All Defaults to 900s (Recommended)

**Description**: Fix the inconsistent defaults first, standardize on 900s everywhere.

**Changes Required**:
1. Update CLI help text from 600s → 900s
2. Update `agent_invoker.py` DEFAULT_SDK_TIMEOUT from 1800s → 900s
3. Keep orchestrator defaults at 900s

**Pros**:
- Eliminates user confusion
- Consistent behavior across all entry points
- Single source of truth
- Preserves current working behavior

**Cons**:
- Still has occasional timeout + retry for complex tasks
- Doesn't solve the fundamental timeout frequency issue

**Risk**: Low (standardizing on already-working value)
**Effort**: Low (3 lines changed)
**Score**: 8/10

### Option C: Moderate Increase to 1200s (20 min)

**Description**: Increase default to 1200s with consistency fixes.

**Pros**:
- ~33% more headroom for complex tasks
- Reduces retry frequency
- Still reasonable wait time if stuck

**Cons**:
- Longer wait when tasks are genuinely stuck
- May mask slow implementations that should be optimized
- Need to update 4 locations

**Risk**: Low
**Effort**: Low (4 lines changed)
**Score**: 7/10

### Option D: Task-Type Based Timeouts

**Description**: Different defaults by task type:
- Scaffolding: 600s
- Feature: 1200s
- Testing: 1800s

**Pros**:
- Optimized per task type
- Faster failure for simple tasks
- More headroom for complex tasks

**Cons**:
- Added complexity
- Task type must be correctly identified
- Multiple places to maintain

**Risk**: Medium (complexity)
**Effort**: Medium (new logic required)
**Score**: 6/10

---

## Decision Matrix

| Option | Fixes Inconsistency | Reduces Timeouts | Complexity | Risk | Score |
|--------|---------------------|------------------|------------|------|-------|
| A (Keep) | No | No | None | Low | 5/10 |
| **B (Harmonize 900s)** | **Yes** | **No** | **Low** | **Low** | **8/10** |
| C (Increase 1200s) | Yes | Yes | Low | Low | 7/10 |
| D (Task-type) | Yes | Yes | Medium | Medium | 6/10 |

---

## Recommendation

**Recommended Option**: **B - Harmonize All Defaults to 900s**

**Rationale**:
1. The immediate problem is **inconsistent documentation and defaults**, not the timeout value itself
2. Only 1 timeout observed in testing across multiple task types
3. The retry mechanism successfully recovered
4. Fixing consistency has no risk and provides immediate user benefit
5. If timeouts remain frequent after harmonization, can then consider Option C

**Sequence**:
1. **Now**: Fix inconsistency (Option B) - 15 minutes
2. **Later**: Monitor timeout frequency in production use
3. **If needed**: Increase to 1200s (Option C) with data backing

---

## Implementation Details

### Files to Modify (Option B)

| File | Current | Change To |
|------|---------|-----------|
| `guardkit/cli/autobuild.py:158` | `help="...or 600"` | `help="...or 900"` |
| `guardkit/cli/autobuild.py:450` | `help="...or 600"` | `help="...or 900"` |
| `guardkit/orchestrator/agent_invoker.py:97` | `"GUARDKIT_SDK_TIMEOUT", "1800"` | `"GUARDKIT_SDK_TIMEOUT", "900"` |
| `guardkit/orchestrator/agent_invoker.py:444` | docstring says 600s | Update to 900s |

### Test Plan

1. Run existing test suite to verify no regressions
2. Manual test: `guardkit autobuild task TASK-XXX` without `--sdk-timeout` flag
3. Verify log shows `SDK timeout: 900s`
4. Verify CLI `--help` shows correct default

---

## Appendix

### Retry Overhead Calculation

| Metric | Value |
|--------|-------|
| Successful total | 23m 24s |
| With retry | 37m 55s |
| Retry overhead | 14m 31s (62%) |

The retry overhead exceeds the original timeout (14.5 min > 15 min) because:
1. Context must be re-loaded
2. Task-work reinvokes full workflow
3. Implementation plan re-parsed
4. Previous work detected but re-verified

### Configuration Priority Documentation

Recommend adding to CLAUDE.md:

```markdown
### SDK Timeout Resolution

The SDK timeout for `/feature-build` resolves in this order:
1. CLI flag: `--sdk-timeout 1200`
2. Task frontmatter: `autobuild.sdk_timeout: 1200`
3. Feature YAML: `autobuild.sdk_timeout: 1200`
4. Default: 900s (15 minutes)

Environment variable `GUARDKIT_SDK_TIMEOUT` can override the default.
```

---

*Review completed: 2026-01-24*
*Depth: Standard (1-2 hours)*
*Mode: Decision Analysis*
