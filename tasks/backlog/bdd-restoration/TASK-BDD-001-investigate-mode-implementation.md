---
id: TASK-BDD-001
title: Investigate task-work mode implementation mechanism
status: backlog
created: 2025-11-28T15:27:39.493246+00:00
updated: 2025-11-28T15:27:39.493246+00:00
priority: high
tags: [bdd-restoration, investigation, research, wave1]
complexity: 2
task_type: research
estimated_effort: 30 minutes
wave: 1
parallel: true
implementation_method: claude-code-direct
parent_epic: bdd-restoration
test_results:
  status: pending
  coverage: null
  last_run: null
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

- [ ] **Document where mode flag is parsed**
  - File path and line numbers
  - Mechanism (spec-driven vs script-driven)
  - How flags reach workflow logic

- [ ] **Map TDD mode workflow**
  - Phase-by-phase execution differences
  - Agent selection logic
  - State transitions specific to TDD

- [ ] **Identify integration points**
  - Where to add BDD validation
  - Where to load scenarios
  - Where to invoke bdd-generator
  - Where to run BDD tests

- [ ] **Create architecture diagram**
  - Mode flag → validation → routing → execution
  - Show TDD path (existing)
  - Show where BDD path should go

- [ ] **Document findings**
  - Create `TASK-BDD-001-investigation-findings.md`
  - Include code references with line numbers
  - Include integration point recommendations

### Questions to Answer

- [ ] Is task-work a pure slash command (prompt-based)?
- [ ] Or is there Python orchestration code?
- [ ] Where does `--mode=tdd` actually affect behavior?
- [ ] How do we add `--mode=bdd` in the same pattern?
- [ ] Where should we call `supports_bdd()`?

## Investigation Approach

### Step 1: Trace --mode=tdd References

```bash
# Search for mode flag references
grep -r "mode=tdd" installer/global/commands/
grep -r "mode.*tdd" .claude/commands/

# Find Python scripts
find installer/global/commands/lib -name "*.py" | xargs grep -l "mode"

# Check command spec
head -n 200 installer/global/commands/task-work.md
```

### Step 2: Analyze Command Structure

- Read task-work.md thoroughly
- Identify how flags are documented
- Look for mode-specific workflow descriptions
- Find agent selection logic

### Step 3: Find Agent Invocation

```bash
# Search for agent invocation patterns
grep -r "invoke_agent" installer/global/
grep -r "bdd-generator" installer/global/
grep -r "task-manager" installer/global/
```

### Step 4: Trace Feature Detection

```bash
# Find supports_bdd() usage
grep -r "supports_bdd" installer/global/
grep -r "require-kit.marker" installer/global/

# Read feature detection
cat installer/global/lib/feature_detection.py
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

- [ ] Clear understanding of mode implementation
- [ ] Specific file paths and line numbers identified
- [ ] Integration points documented with rationale
- [ ] Architecture diagram showing BDD path
- [ ] Ready for TASK-BDD-003 implementation

## Related Tasks

**Depends On**: None (Wave 1 parallel starter)
**Blocks**: TASK-BDD-003 (flag implementation depends on these findings)
**Parallel With**: TASK-BDD-002 (documentation), TASK-BDD-006 (RequireKit)

## References

- [Implementation Guide](./IMPLEMENTATION-GUIDE.md)
- [TASK-2E9E Architectural Review](./../../../.claude/reviews/TASK-2E9E-architectural-review-FINAL.md)
- [BDD Restoration Guide](../../../docs/research/restoring-bdd-feature.md)
- `installer/global/commands/task-work.md`
- `installer/global/lib/feature_detection.py`

## Notes

- This is pure research - don't implement anything yet
- Focus on understanding existing TDD pattern
- Document everything with line numbers
- Keep findings concise but complete
- This unblocks Wave 2 implementation tasks
