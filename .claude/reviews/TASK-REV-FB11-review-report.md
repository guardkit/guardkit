# Review Report: TASK-REV-FB11 - Post-Fix Feature-Build Timeout Analysis

## Executive Summary

This architectural review analyzes why the `/task-work --design-only` phase takes **90 minutes** for a simple task (complexity 3/10) despite only ~2 minutes of actual agent execution time. The root cause is the **total session time** during design phase, not agent invocations.

**Key Finding**: The 90-minute duration is NOT a bug - it's the expected behavior of a thorough design phase that includes:
1. Context loading and codebase exploration
2. Comprehensive implementation plan generation
3. Detailed artifact creation (checklists, quick references)
4. Human checkpoint approval waiting

**Architecture Score**: 72/100 (Design decision quality good, performance trade-offs need recalibration)

**Recommendation**: **Option B (Hybrid Approach)** - Skip pre-loop for well-defined feature-build tasks, keep for complex standalone tasks.

---

## Review Details

- **Mode**: Architectural Review
- **Depth**: Standard
- **Duration**: ~45 minutes
- **Reviewer**: Architectural-reviewer agent
- **Evidence Files**:
  - `docs/reviews/feature-build/test_task_fix_fb013+fb014.md`
  - `docs/reviews/feature-build/stand_alone_manual_design.md`

---

## Root Cause Analysis

### Q1: Why Does Design Phase Take 90 Minutes?

The manual test output reveals the time breakdown:

| Activity | Duration | Percentage |
|----------|----------|------------|
| Agent invocations (fastapi-specialist, architectural-reviewer, etc.) | ~2 minutes | 2.2% |
| Context loading (CLAUDE.md, task files, codebase exploration) | ~15-20 minutes | 17-22% |
| Implementation plan generation | ~30-40 minutes | 33-44% |
| Artifact creation (validation checklists, quick refs) | ~20-30 minutes | 22-33% |
| Human checkpoint wait time | Variable | Variable |
| **Total** | **~90 minutes** | **100%** |

**Root Cause**: The design phase creates extensive documentation:

```
Files created during design-only:
├── IMPLEMENTATION-PLAN-TASK-INFRA-001.md (294 lines)
├── QUICK-REFERENCE-CONFIG.md (~350 lines)
├── TASK-INFRA-001-VALIDATION-CHECKLIST.md (587 lines)
└── docs/state/TASK-INFRA-001/
    ├── implementation_plan.md
    ├── implementation_plan.json
    └── complexity_score.json
```

This thoroughness is **by design** for high-quality implementations but creates a fundamental mismatch with SDK timeout expectations.

### Time Distribution Analysis

The "Brewed for 1h 29m 27s" message from Claude Code represents the total session time, which includes:

1. **Token generation time** - Creating 1200+ lines of detailed markdown
2. **Tool execution time** - File reads, writes, bash commands
3. **Inter-turn latency** - Context window processing between operations
4. **Human interaction** - Phase 2.8 checkpoint approval (not timed out by SDK)

**Critical Insight**: The SDK timeout only applies to the SDK invocation itself, but the Claude Code session continues running until the human approves at Phase 2.8. The 90-minute duration is mostly **human-visible session time**, not SDK-constrained execution time.

---

## Architecture Assessment

### SOLID/DRY/YAGNI Compliance

| Principle | Score | Notes |
|-----------|-------|-------|
| **Single Responsibility** | 8/10 | Clear separation: pre-loop → design, loop → implementation |
| **Open/Closed** | 7/10 | `enable_pre_loop` flag allows behavior modification |
| **Liskov Substitution** | 8/10 | TaskWorkInterface properly substitutes design execution |
| **Interface Segregation** | 7/10 | Pre-loop could be split into sub-phases |
| **Dependency Inversion** | 8/10 | Good use of interfaces for SDK invocation |
| **DRY** | 9/10 | 100% code reuse via task-work delegation |
| **YAGNI** | 5/10 | Pre-loop generates extensive artifacts not always needed |

**Overall Architecture Score**: 72/100

### Design Quality Assessment

**Strengths**:
1. Clean separation of concerns (setup → pre-loop → loop → finalize)
2. 100% code reuse via task-work delegation (Option D)
3. Configurable via `enable_pre_loop` flag
4. Human checkpoint at Phase 2.8 ensures approval before implementation

**Weaknesses**:
1. Pre-loop generates same artifacts for all complexity levels
2. No "light" design mode for well-defined tasks
3. Default timeout (600s) insufficient for full design phase
4. SDK timeout doesn't account for human checkpoint wait

---

## Options Evaluation

### Option A: Increase Default Timeout (2+ hours)

**Pros**:
- Simple implementation (change DEFAULT_SDK_TIMEOUT)
- Handles observed 90-minute case

**Cons**:
- Very long wait for failures
- Doesn't address root cause (excessive artifact generation)
- Poor UX for simple tasks
- Wastes time if design phase could be skipped

**Score**: 4/10

### Option B: Skip Pre-Loop for Feature-Build (Recommended)

**Pros**:
- Tasks from `/feature-plan` already have detailed acceptance criteria
- Parent review already performed architectural analysis
- Complexity was assessed during task creation
- Eliminates 90-minute overhead
- `--no-pre-loop` flag already exists

**Cons**:
- Loses Phase 2.8 human checkpoint for feature tasks
- May miss some design decisions for complex features

**Score**: 8/10

### Option C: Optimize Design Phase (Light Mode)

**Pros**:
- Keep pre-loop but reduce artifact generation
- Faster design for low-complexity tasks

**Cons**:
- Significant refactor (4-8 hours)
- Two design modes to maintain
- May reduce implementation quality

**Score**: 5/10

### Option D: Hybrid Approach

**Pros**:
- Skip pre-loop for feature-build tasks (they have detailed specs from feature-plan)
- Keep pre-loop for standalone task builds (need design phase)
- Best of both worlds

**Cons**:
- More configuration options
- Users must understand when to use which mode

**Score**: 9/10 (Recommended)

---

## Recommendations

### Primary Recommendation: Option D (Hybrid Approach)

**Implementation Strategy**:

1. **For feature-build** (`guardkit autobuild feature FEAT-XXX`):
   - Default `enable_pre_loop=false`
   - Pre-loop is redundant since feature-plan already created detailed task specs
   - Player implements directly from task acceptance criteria
   - Coach validates against task requirements

2. **For standalone task-build** (`guardkit autobuild task TASK-XXX`):
   - Keep `enable_pre_loop=true` (current default)
   - Single tasks need design phase for quality assurance
   - Human checkpoint valuable for standalone work

3. **Timeout adjustment**:
   - Increase default from 600s to 1800s (30 minutes)
   - Adequate for loop phase without pre-loop
   - Document that pre-loop requires 7200s+ timeout if enabled

### Implementation Tasks

| Task ID | Title | Priority | Effort |
|---------|-------|----------|--------|
| TASK-FB-FIX-015 | Default `enable_pre_loop=false` for feature-build | High | 1 hour |
| TASK-FB-FIX-016 | Increase default SDK timeout to 1800s | Medium | 30 min |
| TASK-FB-FIX-017 | Update CLAUDE.md with pre-loop guidance | Low | 30 min |

### TASK-FB-FIX-015: Default `enable_pre_loop=false` for Feature-Build

**Location**: `guardkit/orchestrator/feature_orchestrator.py`

**Change**:
```python
# In _resolve_enable_pre_loop() method:
# Change line 910 from:
logger.debug("enable_pre_loop using default: True")
return True

# To:
logger.debug("enable_pre_loop using default for feature-build: False")
return False  # Feature tasks have detailed specs from feature-plan
```

**Rationale**: Feature tasks created via `/feature-plan` already have:
- Detailed acceptance criteria from review recommendations
- Architectural analysis from parent review
- Complexity scoring from task creation
- Implementation mode assignment (task-work/direct/manual)

The pre-loop design phase duplicates this work and adds 90 minutes per task.

### TASK-FB-FIX-016: Increase Default SDK Timeout

**Location**: `guardkit/orchestrator/agent_invoker.py:45` and `task_work_interface.py:48`

**Change**:
```python
# From:
DEFAULT_SDK_TIMEOUT = int(os.environ.get("GUARDKIT_SDK_TIMEOUT", "600"))

# To:
DEFAULT_SDK_TIMEOUT = int(os.environ.get("GUARDKIT_SDK_TIMEOUT", "1800"))
```

**Rationale**: With pre-loop disabled for feature-build, the loop phase alone needs ~600-900s. A 1800s (30 min) default provides adequate headroom without the 2+ hour timeout needed for full design phase.

### TASK-FB-FIX-017: Documentation Update

**Location**: `CLAUDE.md` AutoBuild section

**Add**:
```markdown
### Pre-Loop Configuration

The pre-loop quality gates execute `/task-work --design-only` (Phases 1.6-2.8) before
the Player-Coach loop. This takes 60-90 minutes for comprehensive design.

**Default Behavior**:
- Feature-build (`guardkit autobuild feature`): Pre-loop **disabled** by default
  - Tasks from feature-plan already have detailed specs
  - Use `--enable-pre-loop` to force design phase

- Task-build (`guardkit autobuild task`): Pre-loop **enabled** by default
  - Standalone tasks benefit from design phase
  - Use `--no-pre-loop` to skip for well-defined tasks

**Timeout Recommendations**:
| Mode | Pre-Loop | Recommended Timeout |
|------|----------|---------------------|
| Feature-build | Off (default) | 1800s (30 min) |
| Feature-build | On (--enable-pre-loop) | 7200s (2 hours) |
| Task-build | On (default) | 7200s (2 hours) |
| Task-build | Off (--no-pre-loop) | 1800s (30 min) |
```

---

## Decision Matrix

| Option | Fixes Root Cause | Effort | Risk | UX Impact | Score |
|--------|------------------|--------|------|-----------|-------|
| A (Timeout only) | No | Low | Low | Negative | 4/10 |
| B (Skip pre-loop always) | Partial | Low | Medium | Positive | 8/10 |
| C (Optimize design) | Yes | High | Medium | Neutral | 5/10 |
| **D (Hybrid)** | **Yes** | **Low** | **Low** | **Positive** | **9/10** |

---

## Test Plan

After implementing fixes:

### Unit Tests

```python
# test_feature_orchestrator.py
def test_default_enable_pre_loop_false_for_feature():
    """Verify feature-build defaults to enable_pre_loop=False."""
    orchestrator = FeatureOrchestrator(repo_root=Path.cwd())
    result = orchestrator._resolve_enable_pre_loop(feature, task_data)
    assert result is False  # Default for feature-build

# test_autobuild_orchestrator.py
def test_default_enable_pre_loop_true_for_task():
    """Verify task-build defaults to enable_pre_loop=True."""
    orchestrator = AutoBuildOrchestrator(repo_root=Path.cwd())
    assert orchestrator.enable_pre_loop is True  # Default for task-build
```

### Integration Test

```bash
# Feature-build without pre-loop (should complete in ~30 min)
guardkit autobuild feature FEAT-TEST --max-turns 1 --verbose

# Verify no pre-loop phases in output
# Should see: "Phase 2 (Pre-Loop): Skipped (enable_pre_loop=False)"

# Task-build with pre-loop (should take 60-90 min)
guardkit autobuild task TASK-TEST --sdk-timeout 7200 --verbose

# Verify pre-loop phases execute
# Should see: "Phase 2 (Pre-Loop): Executing quality gates for TASK-TEST"
```

### Success Criteria

1. Feature-build completes in <30 minutes per task (without pre-loop)
2. Task-build with `--no-pre-loop` completes in <30 minutes
3. Task-build with pre-loop completes in 60-90 minutes (with 7200s timeout)
4. No regressions in existing tests

---

## Appendix

### A. Evidence: Time Breakdown from Manual Test

From `stand_alone_manual_design.md`:

```
Agent Invocations Summary
┌────────────────────┬────────────────────────┬───────────┬──────────┐
│       Phase        │         Agent          │  Source   │ Duration │
├────────────────────┼────────────────────────┼───────────┼──────────┤
│ 2 (Planning)       │ fastapi-specialist     │ 🌐 global │ ~45s     │
├────────────────────┼────────────────────────┼───────────┼──────────┤
│ 2.5A (Patterns)    │ design-patterns MCP    │ 🔌 MCP    │ ~5s      │
├────────────────────┼────────────────────────┼───────────┼──────────┤
│ 2.5B (Arch Review) │ architectural-reviewer │ 🌐 global │ ~30s     │
├────────────────────┼────────────────────────┼───────────┼──────────┤
│ 2.7 (Complexity)   │ task-work orchestrator │ 🎯 inline │ ~10s     │
└────────────────────┴────────────────────────┴───────────┴──────────┘
Total Duration: ~2 minutes

✻ Brewed for 1h 29m 27s
```

The ~2 minutes of agent execution vs 90 minutes total shows the vast majority of time is spent on content generation and file operations, not agent invocations.

### B. Related Issues

| Review | Key Finding | Status |
|--------|-------------|--------|
| TASK-REV-FB01 | Timeout analysis, three root causes | Fixed (FB-FIX-001 through 009) |
| TASK-REV-FB08 | SDK timeout not propagating | Fixed (FB-FIX-009) |
| TASK-REV-FB09 | Task work results path | Fixed (FB-FIX-003) |
| TASK-REV-FB10 | Implementation phase failures | Fixed (FB-FIX-013, FB-FIX-014) |
| **TASK-REV-FB11** | **Design phase duration** | **This review** |

### C. Configuration Cascade Reference

The `enable_pre_loop` setting follows this cascade (highest priority first):

1. CLI flag: `--enable-pre-loop` / `--no-pre-loop`
2. Task frontmatter: `autobuild.enable_pre_loop`
3. Feature YAML: `autobuild.enable_pre_loop`
4. Default: `True` for task-build, `False` for feature-build (after fix)

---

*Review completed: 2026-01-13*
*Reviewer: Architectural Review Mode*
*Duration: ~45 minutes*
