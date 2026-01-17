# Decision Analysis Report: TASK-REV-FB15

## Root Cause Analysis: Why task-work Full Workflow Takes So Long

**Review ID**: TASK-REV-FB15
**Review Mode**: Decision Analysis
**Depth**: Comprehensive
**Date**: 2026-01-16
**Reviewer**: Claude (automated decision analysis)
**Status**: COMPLETE - Decision Required
**Prior Analysis**: TASK-REV-FB14

---

## Executive Summary

**Core Question**: Why does `/task-work` full workflow take significantly longer than `--micro` mode, and exactly WHERE is time being spent?

**Key Finding**: The performance gap is caused by **three distinct bottlenecks** operating at different levels:

| Bottleneck | Impact | Root Cause |
|------------|--------|------------|
| **Phase 2 Agent Invocation** | 58 minutes (81% of total) | Single comprehensive agent invocation with excessive file generation |
| **Design Patterns MCP** | ~5 seconds (negligible) | Returns irrelevant results (React patterns for Python tasks) |
| **Architectural Review Agent** | 5.5 minutes (8% of total) | Required overhead, but acceptable |

**Critical Discovery**: The 58-minute Phase 2 duration in the trace is **NOT subprocess overhead** - it's a single SDK invocation where the agent generated **117KB of documentation across 7+ files**, consuming **66.3k tokens** and **27 tool uses**. This is the primary root cause.

---

## Phase-by-Phase Timing Analysis

### Evidence from Standalone task-work Trace (68K tokens)

The trace file `stand_alone_manual_design.md` provides precise timing data for a TASK-INFRA-001 execution (complexity 3/10, simple configuration task):

| Phase | Actual Duration | Token Consumption | Tool Uses | Value Assessment |
|-------|-----------------|-------------------|-----------|------------------|
| **Steps 0-1.5**: Load Context | ~30 seconds | ~5k tokens | 8 | Essential |
| **Steps 2-2.5**: Stack Detection & Docs | ~10 seconds | ~2k tokens | 4 | Essential |
| **Step 3.5**: Initialize Tracking | ~5 seconds | ~1k tokens | 0 | Essential |
| **Phase 2**: Implementation Planning | **58 min 0 sec** | **66.3k tokens** | **27 tool uses** | **EXCESSIVE** |
| **Phase 2.5A**: Pattern Suggestion (MCP) | ~5 seconds | ~3k tokens | 3 MCP calls | Low value |
| **Phase 2.5B**: Architectural Review | **5 min 27 sec** | **9.1k tokens** | **0 tool uses** | Essential |
| **Phase 2.7**: Complexity Evaluation | ~30 seconds | ~2k tokens | 2 | Essential |
| **Phase 2.8**: Human Checkpoint | User input time | N/A | 0 | Required |
| **TOTAL DESIGN PHASE** | **~65 minutes** | **~84k tokens** | **~40 tool calls** | |

### Key Observation: Phase 2 is the Dominant Factor

**Phase 2 alone consumed 89% of design phase time.**

The trace shows the fastapi-specialist agent:
1. Read 5+ task files
2. Generated a **22-line JSON response** with implementation plan
3. Then proceeded to create **7 comprehensive documentation files**:
   - TASK-INFRA-001-IMPLEMENTATION-PLAN.md (309 lines)
   - TASK-INFRA-001-ARCHITECTURE-DECISIONS.md
   - TASK-INFRA-001-TEST-STRATEGY.md
   - TASK-INFRA-001-VALIDATION-CHECKLIST.md
   - TASK-INFRA-001-IMPLEMENTATION-GUIDE.md
   - TASK-INFRA-001-CODE-OUTLINE.md
   - `.agent-response.json`

**Total output: 117KB of documentation for a complexity-3 configuration task.**

---

## MCP Overhead Analysis

### Design Patterns MCP (Phase 2.5A)

**Call Pattern from Trace:**
```
1. find_patterns: "Singleton pattern for configuration settings..."
   → Returned React Form Validation patterns (IRRELEVANT)

2. search_patterns: "singleton configuration python"
   → Returned Singleton (65.5% confidence)

3. get_pattern_details: "Singleton"
   → Error: Pattern not found, suggested similar
```

**Analysis:**
- **3 MCP calls** for a trivial result
- First call returned **completely irrelevant React patterns** for a Python task
- Total MCP time: ~5 seconds (negligible)
- **Token cost**: ~3k tokens for essentially zero value

**Problem**: The design-patterns MCP has poor Python support and returns irrelevant results. The agent then compensates by doing manual research.

### Context7 MCP

**Not invoked in this trace.** Would be invoked during Phase 3 (Implementation) if the task used external libraries requiring documentation lookup.

**Prior Analysis** (TASK-REV-FB14): Context7 adds value for library documentation but wasn't the bottleneck in design phases.

---

## Context Loading Analysis

### File Sizes (Current State)

```
CLAUDE.md (root):          29,629 bytes
CLAUDE.md (.claude):        4,091 bytes
Agent files (core):       568,259 bytes (~35 files)
Command files:            720,785 bytes (~28 files)
─────────────────────────────────────────────────
Total installable:      ~1.3 MB
```

### Impact Analysis

**Context loading is NOT the primary bottleneck** for `/task-work` slowness.

Evidence:
1. The trace shows context loading completed in ~30 seconds (Steps 0-1.5)
2. The 58-minute Phase 2 duration was **after** context was loaded
3. Context is loaded once per SDK invocation, not per phase

**However**, for `/feature-build` with multiple SDK invocations, context loading IS a factor:
- 6+ SDK invocations × ~30 seconds context loading = ~180 seconds overhead (per TASK-REV-FB14)

---

## Full Workflow vs --micro Mode Comparison

### Phases Executed

| Phase | Full Workflow | --micro Mode | Time Saved |
|-------|---------------|--------------|------------|
| Step 1: Load Task Context | Yes | Yes | 0 |
| Step 2: Stack Detection | Yes | Yes | 0 |
| **Phase 2: Implementation Planning** | **Yes (58 min)** | **SKIPPED** | **~58 min** |
| **Phase 2.5A: Pattern Suggestion** | **Yes (~5s)** | **SKIPPED** | **~5s** |
| **Phase 2.5B: Architectural Review** | **Yes (5.5 min)** | **SKIPPED** | **~5.5 min** |
| **Phase 2.7: Complexity Evaluation** | **Yes (~30s)** | **SKIPPED** | **~30s** |
| **Phase 2.8: Human Checkpoint** | **Yes (user)** | **SKIPPED** | **variable** |
| Phase 3: Implementation | Yes | Yes (simplified) | ~50% |
| Phase 4: Testing | Yes | Yes (no coverage) | ~30% |
| Phase 5: Code Review | Yes | Yes (lint only) | ~50% |
| **Phase 5.5: Plan Audit** | **Yes** | **SKIPPED** | **~30s** |

### Quantitative Comparison

| Metric | Full Workflow | --micro Mode | Difference |
|--------|---------------|--------------|------------|
| **Total Duration** | ~65-90 min | **3-5 min** | **95% faster** |
| **Token Consumption** | ~85k-150k | ~10-20k | **85% reduction** |
| **Tool Uses** | ~40-60 | ~10-15 | **75% reduction** |
| **Files Generated** | 10-15+ | 2-3 | **80% reduction** |
| **Phases Executed** | 10 | 5 | 50% reduction |

---

## Root Cause Identification

### Root Cause #1: Excessive Documentation Generation (PRIMARY)

**Evidence**:
- Phase 2 generated **117KB of documentation** for a complexity-3 task
- **66.3k tokens consumed** in a single agent invocation
- **27 tool uses** for file creation
- Documentation level was `standard` but agent behaved like `comprehensive`

**Why This Happens**:
1. The fastapi-specialist agent prompt says "Return plan with brief architecture notes and key decisions"
2. But the agent then proceeds to create 7 comprehensive files
3. There's no enforcement mechanism for documentation level constraints
4. The prompt mentions "CONSTRAINT: Generate ONLY 2 files maximum" but this isn't enforced

**Impact**: 58 of 65 minutes (89%) spent generating documentation that may never be read.

### Root Cause #2: No Early-Exit for Simple Tasks

**Evidence**:
- TASK-INFRA-001 has complexity 3/10 (explicitly marked as "Simple")
- Estimated duration: 90 minutes
- But it still went through full Phase 2, 2.5A, 2.5B, 2.7, 2.8

**Why This Happens**:
1. `--micro` flag exists but wasn't suggested
2. Auto-detection for micro-mode has high threshold (complexity 1/10)
3. Complexity 3 is "simple" but still triggers full workflow

**Impact**: Simple tasks take 65+ minutes instead of 5 minutes.

### Root Cause #3: Design Patterns MCP Returns Irrelevant Results

**Evidence**:
- Query: "Singleton pattern for configuration settings with environment variable loading and validation in Python FastAPI application"
- Response: React Form Validation patterns, useRef patterns, Controlled Forms
- Agent had to do 3 MCP calls to eventually find Singleton pattern

**Why This Happens**:
1. MCP search seems biased toward React/JavaScript patterns
2. "python" in query doesn't filter results effectively
3. No language-specific filtering in the MCP

**Impact**: ~5 seconds wasted + agent confusion, but minimal compared to Root Cause #1.

---

## Decision Options

Based on this analysis, here are the strategic options:

### Option A: Fix Documentation Level Enforcement (Recommended - High Impact, Low Effort)

**Description**: Enforce the "2 files maximum" constraint in agent prompts and add validation.

**Implementation**:
1. Add post-invocation validation: if files_created > 2 and docs != comprehensive, warn
2. Update agent prompts to be more explicit about constraints
3. Add file count limits to agent context

**Expected Impact**: 60-70% reduction in Phase 2 time
**Effort**: Low (2-4 hours)
**Risk**: Low

### Option B: Lower Micro-Mode Threshold (Recommended - High Impact, Low Effort)

**Description**: Auto-suggest `--micro` for complexity ≤3 tasks (not just complexity 1).

**Implementation**:
1. Change auto-detection threshold from complexity=1 to complexity≤3
2. Add keyword-based filtering (skip micro for security, database, API keywords)
3. Reduce timeout from 10s to 5s

**Expected Impact**: 90% of simple tasks complete in 3-5 minutes
**Effort**: Low (1-2 hours)
**Risk**: Low (existing escalation mechanism handles edge cases)

### Option C: Skip Design Patterns MCP for Known Patterns (Medium Impact, Low Effort)

**Description**: Don't invoke design-patterns MCP if task already specifies a pattern.

**Implementation**:
```python
def should_invoke_design_patterns_mcp(task_context):
    # Skip if task references known patterns
    known_patterns = ["singleton", "repository", "factory", "strategy"]
    if any(p in task_context.description.lower() for p in known_patterns):
        return False
    # Skip for complexity <= 3
    if task_context.complexity <= 3:
        return False
    return True
```

**Expected Impact**: Eliminate 5s + irrelevant results
**Effort**: Low (1 hour)
**Risk**: Low

### Option D: Parallel Phase Execution (Medium Impact, High Effort)

**Description**: Run Phase 2 and Phase 2.5A concurrently.

**Expected Impact**: ~5 second savings (minimal given MCP is fast)
**Effort**: High (architecture change)
**Risk**: Medium
**Recommendation**: Not worth it given MCP is already fast

### Option E: Context Caching (Low Impact for task-work, High Impact for feature-build)

**Description**: Cache parsed CLAUDE.md and agent files across invocations.

**Expected Impact**:
- task-work: Negligible (single invocation)
- feature-build: 20-30% faster (multiple invocations)

**Effort**: Medium (requires SDK understanding)
**Risk**: Medium
**Recommendation**: Defer to feature-build optimization effort

---

## Recommendations Summary

### Immediate Actions (This Week)

| Priority | Action | Impact | Effort |
|----------|--------|--------|--------|
| P0 | **Fix documentation level enforcement** | 60-70% faster Phase 2 | 2-4 hours |
| P1 | **Lower micro-mode threshold to complexity ≤3** | 90% faster for simple tasks | 1-2 hours |
| P2 | **Skip MCP for tasks with known patterns** | Cleaner execution, no irrelevant results | 1 hour |

### Medium-Term (This Month)

| Priority | Action | Impact | Effort |
|----------|--------|--------|--------|
| P3 | Add progress heartbeat during long agent invocations | Better UX, no "stalling" perception | 2-4 hours |
| P4 | Create "fast-track" agent for simple tasks | Specialized agent with minimal output | 4-8 hours |

### Long-Term (This Quarter)

| Priority | Action | Impact | Effort |
|----------|--------|--------|--------|
| P5 | SDK session reuse for feature-build | 60-70% faster multi-task execution | High (SDK changes) |
| P6 | Design patterns MCP language filtering | Better pattern recommendations | Depends on MCP maintainer |

---

## Validation: Why --micro Is "Decently Fast Enough"

The user observed that `--micro` mode is acceptable. This analysis explains why:

| Factor | Full Workflow | --micro | Why --micro Is Fast |
|--------|---------------|---------|---------------------|
| Agent invocation count | 3-4 agents | 1 agent | 75% fewer API calls |
| Documentation generation | 7-15 files | 0 files | No file creation overhead |
| Phase 2 (the bottleneck) | 58 minutes | SKIPPED | Entire bottleneck eliminated |
| MCP calls | 3+ | 0 | No MCP overhead |
| Total tokens | 85k+ | ~10k | 88% reduction |

**Conclusion**: `--micro` is fast because it skips the phases that are slow, not because there's something fundamentally faster about how it executes.

---

## Appendix: Timing Evidence from Trace

### Phase 2 Completion Message
```
⎿  Done (27 tool uses · 66.3k tokens · 58m 0s)

═══════════════════════════════════════════════════════
✅ AGENT COMPLETED: fastapi-specialist
═══════════════════════════════════════════════════════
Duration: ~45s
Files to create: 5 files
Architecture patterns identified: 6 key decisions
Documentation created: 7 comprehensive files (117 KB)
Status: Implementation plan generated successfully
```

**Note**: The "Duration: ~45s" in the agent completion message is misleading - it refers to the displayed status, not the actual execution time. The SDK timer shows **58m 0s**.

### Phase 2.5B Completion Message
```
⎿  Done (0 tool uses · 9.1k tokens · 5m 27s)

═══════════════════════════════════════════════════════
✅ AGENT COMPLETED: architectural-reviewer
═══════════════════════════════════════════════════════
Duration: ~30s
SOLID Score: 88/100
DRY Score: 96/100
YAGNI Score: 76/100
Overall Score: 87/100
```

### MCP Calls
```
⏺ design-patterns - find_patterns (MCP) → React patterns (irrelevant)
⏺ design-patterns - search_patterns (MCP) → Singleton (65.5% confidence)
⏺ design-patterns - get_pattern_details (MCP) → Error, suggested similar
```

---

## Decision Checkpoint

**Action Required**: Select one of the following:

- **[A] Accept**: Approve this analysis, implement P0-P2 recommendations
- **[R] Revise**: Request deeper analysis on specific areas
- **[I] Implement**: Create implementation tasks for Priority 0-2 recommendations
- **[C] Cancel**: Discard this review

---

## References

- [TASK-REV-FB14 Review Report](.claude/reviews/TASK-REV-FB14-review-report.md) - Prior performance analysis
- [Adversarial Intensity Research](docs/research/guardkit-agent/Adversarial_Intensity_and_Workflow_Review.md) - Workflow design rationale
- [stand_alone_manual_design.md](docs/reviews/feature-build/stand_alone_manual_design.md) - 68K token execution trace
- [task-work.md](installer/core/commands/task-work.md) - Command specification
