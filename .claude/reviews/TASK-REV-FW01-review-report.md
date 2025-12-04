# Review Report: TASK-REV-FW01

## Feature Workflow Streamlining - Decision Analysis

**Review Mode**: Decision Analysis
**Review Depth**: Standard
**Date**: 2025-12-04
**Reviewer**: software-architect, architectural-reviewer agents

---

## Executive Summary

This review analyzes how to formalize the evolved feature development workflow into GuardKit commands. The current manual workflow is effective but requires 5-6 separate steps with flag memorization. The proposed enhancements would reduce this to 1-2 commands while maintaining human decision points.

**Recommendation**: Implement in 2 phases:
- **Phase 1** (Pre-public release): Enhanced `/task-review` [I]mplement option
- **Phase 2** (SDK integration): New `/feature-plan` command with automation

**Competitive Impact**: This would be a significant differentiator - no other spec-driven development tool (BMAD, SpecKit, AgentOS) offers this level of workflow automation with quality gates.

---

## Current Situation Assessment

### Evolved Manual Workflow

The user has developed an effective but manual pattern:

```
Step 1: /task-create "Review task to plan [feature]" task_type:review
Step 2: /task-review TASK-XXX --mode=decision
Step 3: Choose [R]evise or [I]mplement
Step 4: Request subfolder organization → tasks/backlog/{feature}/
Step 5: Request IMPLEMENTATION-GUIDE.md creation
Step 6: (Optional) Request README.md
```

### Pain Points Identified

| Pain Point | Impact | Frequency |
|------------|--------|-----------|
| Remembering flags for `/task-create` | Medium | Every feature |
| Manual subfolder organization request | Low | Every feature |
| Manual implementation guide request | High | Every feature |
| Wave/parallel analysis is manual | High | Every feature |
| No README template | Low | 50% of features |

### Established Patterns (Already Working)

Looking at `tasks/backlog/progressive-disclosure/`:
- ✅ Subfolder structure: `tasks/backlog/{feature-slug}/`
- ✅ README.md: Feature documentation
- ✅ IMPLEMENTATION-GUIDE.md: Wave breakdown with method recommendations
- ✅ Task prefix convention: `TASK-{PREFIX}-{NUMBER}`
- ✅ Method legend: `/task-work` vs `Direct` vs `Manual`
- ✅ Parallel execution analysis with Conductor worktrees

---

## Option Evaluation Matrix

### Option A: New `/feature-plan` Command (REVISED - No SDK Required!)

```bash
/feature-plan "implement dark mode"
```

**Key Discovery**: Slash commands are markdown instruction files - they don't require SDK!

**Behavior**:
1. Auto-create review task with correct flags (`task_type:review`)
2. Auto-invoke `/task-review --mode=decision`
3. On [I]mplement: Auto-create subfolder + all subtasks
4. Auto-generate IMPLEMENTATION-GUIDE.md with wave analysis
5. Auto-generate README.md

**Implementation**: Single markdown file (`/feature-plan.md`) that:
```markdown
# Feature Plan - Single Command Feature Planning

## Execution Flow
When user runs `/feature-plan "feature description"`:

1. Execute: /task-create "Plan: {description}" task_type:review priority:high
2. Capture task ID from output
3. Execute: /task-review {TASK-ID} --mode=decision --depth=standard
4. On [I]mplement: Enhanced behavior (auto subfolder, auto guide, auto readme)
```

| Criterion | Score | Notes |
|-----------|-------|-------|
| User Experience | 10/10 | Single command, maximum convenience |
| Implementation Effort | **Low** | Just a markdown command file! |
| Backward Compatibility | 10/10 | Additive, no breaking changes |
| SDK Dependency | **None** | Markdown orchestration only |
| Risk | **Low** | Reuses existing commands |

**Verdict**: ⭐⭐⭐ Best UX AND low effort! **Recommend for Phase 1**.

---

### Option B: Enhanced `/task-review` [I]mplement Option (REVISED)

**Current Behavior**:
```
[I]mplement → Creates single implementation task
```

**Proposed Behavior** (Fully Automatic):
```
[I]mplement chosen...

✅ Auto-detected:
   Feature slug: dark-mode (from review title)
   Subtasks: 7 (from recommendations)
   Parallel groups: 3 waves

→ Creates tasks/backlog/{feature-slug}/ folder
→ Creates all subtasks with:
  - implementation_mode: task-work | direct | manual (auto-detected)
  - parallel_group: 1, 2, 3... or null (auto-detected from file conflicts)
  - conductor_workspace: suggested worktree name
→ Generates IMPLEMENTATION-GUIDE.md
→ Generates README.md

Next: Review IMPLEMENTATION-GUIDE.md and start with Wave 1
```

**No prompts required** - everything auto-detected from review findings.

| Criterion | Score | Notes |
|-----------|-------|-------|
| User Experience | 9/10 | Still 2 commands, but fully automatic |
| Implementation Effort | Medium | Enhance existing command |
| Backward Compatibility | 10/10 | Additive enhancement |
| SDK Dependency | None | Works today |
| Risk | Low | Builds on existing pattern |

**Verdict**: ⭐⭐ Best for Phase 1. **Recommend as immediate enhancement**.

---

### Option C: Minimal Enhancement (Flag Defaults)

**Change**:
- `/task-create "Review..."` auto-detects review task and sets flags
- User still manually requests organization

| Criterion | Score | Notes |
|-----------|-------|-------|
| User Experience | 6/10 | Slightly better, still manual |
| Implementation Effort | Low | Small change |
| Backward Compatibility | 10/10 | Additive |
| SDK Dependency | None | Works today |
| Risk | Very Low | Minimal changes |

**Verdict**: Too incremental. Doesn't address main pain points.

---

## Recommended Decision

### Phase 1: `/feature-plan` Command + Enhanced [I]mplement (Pre-Public Release)

**REVISED**: After investigation, `/feature-plan` can be implemented as a simple markdown command file with **zero SDK dependency**. This gives the single-command UX immediately.

**Phase 1 Now Includes Both**:

#### Part A: New `/feature-plan` Command (0.5 days)

Single markdown file that orchestrates existing commands:

```bash
/feature-plan "implement dark mode"
```

Automatically executes:
1. `/task-create "Plan: implement dark mode" task_type:review priority:high`
2. `/task-review TASK-XXX --mode=decision --depth=standard`

**Result**: User types ONE command, gets full planning workflow.

#### Part B: Enhanced [I]mplement Option

**Scope**:
1. When [I]mplement is chosen, **auto-detect** subtask decomposition from review findings
2. **Auto-generate** feature slug from review task title (e.g., "Plan: dark mode" → `dark-mode`)
3. Create subfolder `tasks/backlog/{feature-slug}/`
4. Generate subtasks with implementation mode tagging
5. Generate IMPLEMENTATION-GUIDE.md using established template
6. Generate README.md with feature scope

**Auto-Detection Logic**:

| Aspect | Detection Method |
|--------|------------------|
| Feature slug | Extract from review title, remove "review/plan/investigate" prefixes, slugify |
| Subtask count | Parse recommendations section, each actionable recommendation = 1 subtask |
| Implementation mode | Complexity + risk keywords → `task-work` if complex/risky, `direct` otherwise |
| Parallel groups | File conflict analysis from subtask file lists |

**No Manual Prompts Required** - the [I]mplement option becomes fully automatic:

```
[I]mplement chosen...

✅ Auto-detected:
   Feature slug: dark-mode
   Subtasks: 7 (from recommendations)
   Parallel groups: 3 waves

Creating tasks/backlog/dark-mode/
  ├── README.md
  ├── IMPLEMENTATION-GUIDE.md
  ├── TASK-DM-001-add-css-variables.md (direct, wave 1)
  ├── TASK-DM-002-theme-toggle-component.md (task-work, wave 1)
  ├── TASK-DM-003-persist-preference.md (direct, wave 1)
  ├── TASK-DM-004-update-navigation.md (task-work, wave 2)
  ├── TASK-DM-005-update-auth-flow.md (task-work, wave 2)
  ├── TASK-DM-006-add-dark-mode-tests.md (task-work, wave 3)
  └── TASK-DM-007-documentation.md (direct, wave 3)

Next: Review IMPLEMENTATION-GUIDE.md and start with Wave 1
```

**Implementation Mode Tagging**:

```yaml
# In each subtask frontmatter
implementation_mode: task-work  # or: direct, manual
parallel_group: 1               # or: null for sequential
conductor_workspace: feature-dark-mode-1
```

**IMPLEMENTATION-GUIDE.md Auto-Generation**:

Based on `progressive-disclosure/IMPLEMENTATION-GUIDE.md` template:
- Wave breakdown (groups of parallel-safe tasks)
- Method legend (task-work / Direct / Manual)
- Conductor workspace strategy
- Checkpoints between waves
- Summary matrix

**Effort Estimate**: 3-5 days
**Risk**: Low (builds on existing patterns)

---

### Phase 2: New `/feature-plan` Command (SDK Integration)

**Scope**:
1. Single command to initiate feature planning
2. Uses Claude Agent SDK to orchestrate `/task-create` + `/task-review`
3. Automatic checkpoint handling via message parsing
4. Full automation of Phase 1 behavior

**Command Naming Decision**: `/feature-plan`
- Clearer than `/feature-task-create` (too verbose)
- Better than `/feature-create` (could be confused with creating features in RequireKit)
- Aligns with "plan" concept (investigation + decomposition)

**SDK Integration Points**:
- Invoke `/task-create` with correct flags
- Invoke `/task-review` with correct mode
- Parse checkpoint output
- Handle [R]evise loop automatically
- Orchestrate [I]mplement behavior

**Effort Estimate**: 1-2 weeks (after Phase 1)
**Risk**: Medium (SDK dependency)

---

### Phase 3: `/feature-work` Command (Future)

**Scope**:
- Execute all subtasks using Conductor worktrees
- Parallel execution via Claude Agent SDK
- Integration testing at wave boundaries
- Final merge with human checkpoint

**Aligns with Research Documents**:
- [Claude_Agent_SDK_Two_Command_Feature_Workflow.md](../../docs/research/Claude_Agent_SDK_Two_Command_Feature_Workflow.md)
- Two-command pattern: `/feature-plan` + `/feature-work`

**Effort Estimate**: 2-3 weeks (after Phase 2)
**Risk**: Medium-High (git worktree orchestration)

---

## Competitive Differentiation Analysis

### Comparison with Alternatives

| Feature | GuardKit (Proposed) | BMAD | SpecKit | AgentOS |
|---------|---------------------|------|---------|---------|
| Single command to start | ✅ `/feature-plan` | ❌ | ❌ | ❌ |
| Automatic subtask creation | ✅ [I]mplement | ❌ | ❌ | ❌ |
| Wave/parallel analysis | ✅ Auto-generated | ❌ | ❌ | ❌ |
| Conductor integration | ✅ Worktree suggestions | ❌ | ❌ | ❌ |
| Quality gates built-in | ✅ Phase 2.5, 4.5 | Partial | Partial | ❌ |
| Human decision points | ✅ [A]/[R]/[I]/[C] | ❌ | ❌ | ❌ |
| Progressive automation | ✅ SDK path | ❌ | ❌ | ❌ |

### Key Differentiators

1. **Ease of Use**: One command to plan, one to execute
2. **Quality Without Ceremony**: Built-in gates, no extra process
3. **Parallel Execution**: First-class Conductor support
4. **Progressive Automation**: Manual → Semi-auto → Full SDK

### Marketing Angle

> "From feature idea to implementation plan in one command. GuardKit automatically decomposes your feature into parallel-safe tasks, identifies which need quality gates vs quick changes, and generates a Conductor-ready execution plan."

---

## Implementation Plan Summary

### Phase 1 Subtasks (Feature Plan Command + Enhanced [I]mplement)

| ID | Title | Method | Complexity | Effort |
|----|-------|--------|------------|--------|
| FW-001 | Create `/feature-plan` command (markdown orchestration) | Direct | 3 | 0.5d |
| FW-002 | Auto-detect feature slug from review task title | Direct | 3 | 0.5d |
| FW-003 | Auto-detect subtasks from review recommendations | /task-work | 5 | 1d |
| FW-004 | Add implementation mode auto-tagging (complexity/risk analysis) | /task-work | 5 | 1d |
| FW-005 | Add parallel group detection (file conflict analysis) | /task-work | 6 | 1.5d |
| FW-006 | Create IMPLEMENTATION-GUIDE.md generator | /task-work | 5 | 1d |
| FW-007 | Create README.md generator for features | Direct | 3 | 0.5d |
| FW-008 | Update /task-review [I]mplement flow (orchestrate all above) | /task-work | 5 | 1d |
| FW-009 | Update documentation (CLAUDE.md, task-review.md, feature-plan.md) | Direct | 3 | 0.5d |

**Total Phase 1**: ~7.5 days

**Wave Analysis**:
- **Wave 1** (parallel): FW-001, FW-002, FW-007 (independent: command + utilities)
- **Wave 2** (parallel): FW-003, FW-004, FW-005, FW-006 (detection + generation)
- **Wave 3** (sequential): FW-008 (orchestration, depends on all above)
- **Wave 4** (sequential): FW-009 (documentation, after implementation stable)

**Quick Win**: FW-001 can be done in 0.5 days and immediately gives single-command UX!

### Phase 2 Subtasks (SDK Automation - `/feature-work`)

Since `/feature-plan` is now in Phase 1, Phase 2 focuses on automating the **execution** of planned features.

| ID | Title | Method | Complexity | Effort |
|----|-------|--------|------------|--------|
| FW-010 | Create /feature-work command specification | Direct | 4 | 0.5d |
| FW-011 | Implement SDK orchestration for parallel /task-work | /task-work | 7 | 2d |
| FW-012 | Add git worktree management via SDK | /task-work | 6 | 1.5d |
| FW-013 | Implement wave-based execution with checkpoints | /task-work | 6 | 1.5d |
| FW-014 | Add merge and integration testing | /task-work | 5 | 1d |
| FW-015 | Integration testing for full workflow | /task-work | 5 | 1d |
| FW-016 | Update documentation for /feature-work | Direct | 3 | 0.5d |

**Total Phase 2**: ~8 days

**Two-Command Workflow**:
```bash
/feature-plan "implement dark mode"   # Phase 1: Plan + decompose
/feature-work dark-mode               # Phase 2: Execute in parallel
```

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| File conflict detection is inaccurate | Medium | Low | Conservative defaults, human override |
| Implementation guide format evolves | Low | Low | Template-based, easy to update |
| SDK API changes | Medium | Medium | Abstraction layer, version pinning |
| User confusion with new commands | Low | Medium | Clear documentation, gradual rollout |

---

## Recommendations

1. **Immediate (Phase 1)**: Enhance `/task-review` [I]mplement option
   - Creates subfolder + subtasks + IMPLEMENTATION-GUIDE.md
   - No SDK dependency
   - Significant UX improvement for public release

2. **Post-Release (Phase 2)**: Add `/feature-plan` command
   - Uses Claude Agent SDK
   - Single-command feature planning
   - Full automation with checkpoints

3. **Future (Phase 3)**: Add `/feature-work` command
   - Parallel execution via SDK
   - Conductor worktree orchestration
   - Complete two-command workflow

---

## Decision Checkpoint

**Review Status**: COMPLETE

**Findings**:
- Current workflow is effective but manual (5-6 steps)
- Established patterns (progressive-disclosure) provide template
- Phase 1 enhancement is low-risk, high-value
- Full automation requires SDK (Phase 2+)

**Recommendations**:
- Phase 1: `/feature-plan` command + enhanced [I]mplement (~7.5 days, pre-release)
  - **Quick win**: FW-001 alone gives single-command UX in 0.5 days!
- Phase 2: `/feature-work` command with SDK (~8 days, post-release)
- Complete two-command workflow: `/feature-plan` → `/feature-work`

---

## Appendix

### Subfolder Structure Standard

```
tasks/backlog/{feature-slug}/
├── README.md                    # Feature documentation
├── IMPLEMENTATION-GUIDE.md      # Wave/method breakdown
├── TASK-{PREFIX}-001-*.md       # Subtask 1
├── TASK-{PREFIX}-002-*.md       # Subtask 2
└── ...
```

### Implementation Mode Frontmatter

```yaml
---
id: TASK-FW-001
title: Add implementation mode tagging
implementation_mode: direct      # task-work | direct | manual
parallel_group: 1                # null for sequential
conductor_workspace: feature-workflow-1
complexity: 4
effort_estimate: 0.5d
---
```

### Research Document References

1. [Claude_Agent_SDK_Two_Command_Feature_Workflow.md](../../docs/research/Claude_Agent_SDK_Two_Command_Feature_Workflow.md)
2. [Claude_Agent_SDK_Fast_Path_to_TaskWright_Orchestration.md](../../docs/research/Claude_Agent_SDK_Fast_Path_to_TaskWright_Orchestration.md)
3. [Claude_Agent_SDK_True_End_to_End_Orchestrator.md](../../docs/research/Claude_Agent_SDK_True_End_to_End_Orchestrator.md)
