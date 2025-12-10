---
id: TASK-BDD-001
title: Investigate task-work mode implementation mechanism
status: completed
created: 2025-11-28T15:27:39.493246+00:00
updated: 2025-11-28T19:45:00.000000+00:00
completed: 2025-11-28T19:45:00.000000+00:00
priority: high
tags: [bdd-restoration, investigation, research, wave1]
complexity: 2
task_type: research
estimated_effort: 30 minutes
actual_effort: 45 minutes
wave: 1
parallel: true
implementation_method: claude-code-direct
parent_epic: bdd-restoration
test_results:
  status: not_applicable
  coverage: null
  last_run: null
  note: "Research task - no tests required"
completion_metrics:
  total_duration: 45 minutes
  research_time: 45 minutes
  deliverables_created: 1
  code_references_documented: 15+
  integration_points_identified: 5
  questions_answered: 5
---

# Task: Investigate task-work mode implementation mechanism

## Context

We need to restore `--mode=bdd` flag to task-work command. Before implementing, we must understand where and how the current `--mode=tdd` flag is implemented.

**Parent Epic**: BDD Mode Restoration
**Wave**: 1 (Foundation - runs in parallel with TASK-BDD-002 and TASK-BDD-006)
**Implementation**: Use Claude Code directly (research/exploration task)

## Description

Investigate the task-work command implementation to understand:
1. Where mode flags are parsed
2. How TDD mode routes to different workflow phases
3. Where agent invocation occurs
4. What integration points exist for BDD mode

This is pure research - no code changes in this task.

## Research Questions

### Primary Questions

1. **Where is `--mode=tdd` parsed?**
   - Is it in the command spec (task-work.md)?
   - Is there a Python script that parses it?
   - How does Claude Code interpret the flags?

2. **How does mode affect workflow routing?**
   - Where does TDD mode change Phase execution?
   - Which agents get invoked for TDD?
   - How does state flow differ between modes?

3. **Where is agent invocation handled?**
   - Which file/function invokes agents?
   - How are agents selected based on mode?
   - Where does require-kit integration happen?

4. **What are the integration points for BDD?**
   - Where should BDD validation occur?
   - Where should scenario loading happen?
   - Where should bdd-generator be invoked?

5. **How does feature detection work?**
   - Where is `supports_bdd()` currently used?
   - How does require-kit detection work?
   - Where should marker file check occur?

## Acceptance Criteria

### Research Deliverables

- [x] **Document where mode flag is parsed** ✅
  - File path and line numbers: `task-work.md:2743-2762`
  - Mechanism: Spec-driven (markdown-based, no Python script)
  - How flags reach workflow logic: Claude Code reads spec as prompt context

- [x] **Map TDD mode workflow** ✅
  - Phase-by-phase execution differences: RED-GREEN-REFACTOR cycle documented
  - Agent selection logic: Metadata-based discovery (stack, phase, capabilities)
  - State transitions: TDD splits Phase 3 into sub-phases

- [x] **Identify integration points** ✅
  - Where to add BDD validation: Phase 1 (lines 400-600)
  - Where to load scenarios: Phase 1 (lines 600-800)
  - Where to invoke bdd-generator: NEW Phase 3-BDD (lines 1750-1800)
  - Where to run BDD tests: Phase 4 (existing, lines 1970-2057)

- [x] **Create architecture diagram** ✅
  - Mode flag → validation → routing → execution: Text diagram created
  - Show TDD path (existing): Documented in findings
  - Show where BDD path should go: Complete flow with integration points

- [x] **Document findings** ✅
  - Created `TASK-BDD-001-investigation-findings.md` (31KB, comprehensive)
  - Includes 15+ code references with line numbers
  - Includes 5 integration point recommendations with rationale

### Questions to Answer

- [x] Is task-work a pure slash command (prompt-based)? ✅ **YES** - No Python orchestration
- [x] Or is there Python orchestration code? ✅ **NO** - Pure markdown specification
- [x] Where does `--mode=tdd` actually affect behavior? ✅ task-manager agent interpretation
- [x] How do we add `--mode=bdd` in the same pattern? ✅ Document in spec + agent routing
- [x] Where should we call `supports_bdd()`? ✅ Phase 1 validation (lines 400-600)

## Investigation Approach

### Step 1: Trace --mode=tdd References

```bash
# Search for mode flag references
grep -r "mode=tdd" installer/core/commands/
grep -r "mode.*tdd" .claude/commands/

# Find Python scripts
find installer/core/commands/lib -name "*.py" | xargs grep -l "mode"

# Check command spec
head -n 200 installer/core/commands/task-work.md
```

### Step 2: Analyze Command Structure

- Read task-work.md thoroughly
- Identify how flags are documented
- Look for mode-specific workflow descriptions
- Find agent selection logic

### Step 3: Find Agent Invocation

```bash
# Search for agent invocation patterns
grep -r "invoke_agent" installer/core/
grep -r "bdd-generator" installer/core/
grep -r "task-manager" installer/core/
```

### Step 4: Trace Feature Detection

```bash
# Find supports_bdd() usage
grep -r "supports_bdd" installer/core/
grep -r "require-kit.marker" installer/core/

# Read feature detection
cat installer/core/lib/feature_detection.py
```

### Step 5: Document Integration Points

Based on findings, document:
- Where to add mode validation
- Where to check marker file
- Where to load scenarios
- Where to route to bdd-generator
- Where to run BDD tests

## Deliverables

### Primary Deliverable

**File**: `tasks/backlog/bdd-restoration/TASK-BDD-001-investigation-findings.md`

**Required Sections**:
1. **Mode Flag Implementation**
   - How --mode=tdd works
   - Where it's parsed
   - How it affects workflow

2. **Integration Points for BDD**
   - Validation checkpoint
   - Scenario loading location
   - Agent invocation location
   - Test execution location

3. **Architecture Diagram** (text or Mermaid)
   ```
   /task-work TASK-XXX --mode=bdd
            ↓
   [Parse Flags] ← Where?
            ↓
   [Validate BDD Mode] ← Add here
            ↓ (check marker)
   [Load Scenarios] ← Add here
            ↓
   [Phase 1-2: Standard]
            ↓
   [Phase 3: Route to bdd-generator] ← Add here
            ↓
   [Phase 4: Run BDD Tests] ← Add here
            ↓
   [Phase 5: Review]
   ```

4. **Code References**
   - All file paths with line numbers
   - Functions/sections to modify
   - Existing patterns to follow

5. **Recommendations**
   - Cleanest integration approach
   - Where to add new code
   - What to avoid

## Success Criteria

- [x] Clear understanding of mode implementation ✅
- [x] Specific file paths and line numbers identified ✅
- [x] Integration points documented with rationale ✅
- [x] Architecture diagram showing BDD path ✅
- [x] Ready for TASK-BDD-003 implementation ✅

## Completion Summary

**Status**: ✅ **COMPLETED**

**Deliverables**:
- Comprehensive investigation findings document (31KB)
- 15+ code references with specific line numbers
- 5 integration points identified with implementation guidance
- Text-based architecture diagram showing BDD workflow
- Answers to all 5 research questions
- Actionable recommendations for TASK-BDD-003

**Key Findings**:
1. task-work is a pure slash command (prompt-based, no Python orchestration)
2. Mode flags are documented in task-work.md specification
3. Workflow routing handled by task-manager agent
4. BDD integration follows TDD pattern (validation → loading → generation → testing)
5. `supports_bdd()` already exists in feature_detection.py

**Impact**:
- Unblocks TASK-BDD-003 (flag implementation)
- Unblocks TASK-BDD-004 (workflow routing)
- Provides clear integration strategy for Wave 2 tasks
- Documents exact file locations and line numbers for implementation

**Lessons Learned**:
- Taskwright's architecture is elegantly simple (markdown-driven)
- Agent discovery system is metadata-based (highly extensible)
- Feature detection library is shared with require-kit (sync needed)
- Quality gates automatically apply to all modes (no special handling)

**Next Steps**:
1. TASK-BDD-003: Implement `--mode=bdd` flag using documented pattern
2. TASK-BDD-004: Add workflow routing logic to task-manager agent
3. Wave 2 tasks can proceed with clear integration points

## Related Tasks

**Depends On**: None (Wave 1 parallel starter)
**Blocks**: TASK-BDD-003 (flag implementation depends on these findings)
**Parallel With**: TASK-BDD-002 (documentation), TASK-BDD-006 (RequireKit)

## References

- [Implementation Guide](./IMPLEMENTATION-GUIDE.md)
- [TASK-2E9E Architectural Review](./../../../.claude/reviews/TASK-2E9E-architectural-review-FINAL.md)
- [BDD Restoration Guide](../../../docs/research/restoring-bdd-feature.md)
- `installer/core/commands/task-work.md`
- `installer/core/lib/feature_detection.py`

## Notes

- This is pure research - don't implement anything yet
- Focus on understanding existing TDD pattern
- Document everything with line numbers
- Keep findings concise but complete
- This unblocks Wave 2 implementation tasks
