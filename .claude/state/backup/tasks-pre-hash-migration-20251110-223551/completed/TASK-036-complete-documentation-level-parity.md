---
id: TASK-036
title: Complete Documentation Level Parity with ai-engineer (Commands & Templates)
status: completed
created: 2025-11-01T00:00:00Z
updated: 2025-11-01T20:30:00Z
completed_at: 2025-11-01T20:30:00Z
priority: medium
complexity: 4
estimated_time: 3-4 hours
actual_time: 2 hours
tags: [documentation, optimization, task-work, commands, templates, parity]
epic: null
feature: null
parent_task: TASK-035
related_tasks:
  - TASK-035 (completed) - Agent updates for documentation levels
requirements: []
bdd_scenarios: []
test_results:
  status: passed
  coverage: N/A
  last_run: 2025-11-01T20:30:00Z
completion_metrics:
  total_duration: 2 hours
  implementation_time: 1.5 hours
  testing_time: 0.5 hours
  files_created: 3
  files_modified: 1
  lines_added: 887
  documentation_reduction: 67%
  acceptance_criteria_met: 6/6
---

# Task: Complete Documentation Level Parity with ai-engineer

## Overview

Complete the documentation level implementation by updating commands and templates to match ai-engineer's TASK-035, achieving full parity for documentation generation control.

**Reference Document**: `TASK-035-COMPARISON-WITH-AI-ENGINEER.md`

**Strategic Context**: This work enables significant time and token reduction during development in taskwright and require-kit repos, which will be used to refine the approach before backporting improvements to ai-engineer.

## Context from TASK-035 Comparison

TASK-035 successfully updated 5 global agents with documentation level awareness, achieving equivalent functionality to ai-engineer. However, the comparison identified gaps in commands and templates:

### What TaskWright Currently Has ✅
- ✅ 5 global agents updated (architectural-reviewer, test-orchestrator, code-reviewer, task-manager, test-verifier)
- ✅ Template settings.json with documentation configuration
- ✅ Agent pattern consistency (100%)
- ✅ Quality gate preservation (100%)

### What ai-engineer Has (That TaskWright Doesn't) ⚠️

From `TASK-035-COMPARISON-WITH-AI-ENGINEER.md`:

**Commands & Documentation**:
1. **`installer/global/commands/task-work.md`** updates (450+ lines)
   - Step 0: Parse `--docs` flag
   - Step 2.5: Determine documentation level
   - Documentation levels section
   - Configuration hierarchy
   - Agent invocation examples with `<AGENT_CONTEXT>` blocks

2. **`installer/global/instructions/context-parameter-format.md`** (292 lines)
   - Standard format for `<AGENT_CONTEXT>` blocks
   - Parsing guidelines with examples
   - Validation rules
   - Versioning support
   - Graceful degradation logic

3. **`docs/guides/documentation-levels-guide.md`** (439 lines)
   - User guide for documentation levels
   - Command syntax and examples
   - Auto-selection logic
   - Configuration hierarchy
   - Troubleshooting

4. **`installer/global/templates/documentation/minimal-summary-template.md`** (271 lines)
   - Template for minimal mode summaries (~200 lines target)
   - Section structure with examples

5. **`installer/global/templates/documentation/comprehensive-checklist.md`** (336 lines)
   - Checklist for comprehensive mode (13+ files)
   - Core documents specification
   - Conditional documents

**Total Gap**: ~1,788 lines of commands, instructions, and templates

## Scope for This Task

### Primary Goal
Update TaskWright's command and template infrastructure to support documentation level control with **reduced verbosity** compared to ai-engineer (use learnings from TASK-035 implementation).

### Key Principle: Reduce Documentation Where Possible
Following the insight that documentation level control **drastically reduces time and tokens**, this task should:
1. ✅ Enable the `--docs` flag and auto-selection logic
2. ✅ Provide essential instructions for context parameter format
3. ⚠️ **MINIMIZE** verbose documentation (prioritize code over docs)
4. ⚠️ **SIMPLIFY** templates (lean toward minimal examples)
5. ⚠️ **DEFER** comprehensive guides until proven needed

## Acceptance Criteria

### AC1: Command Specification Updates

**File**: `installer/global/commands/task-work.md`

- [ ] Add `--docs` flag specification (minimal|standard|comprehensive|auto)
- [ ] Add Step 0: Parse documentation level flag
- [ ] Add Step 2.5: Determine documentation level (auto-detection logic)
- [ ] Document `<AGENT_CONTEXT>` block format for agent invocations
- [ ] Add examples of agent invocations with context blocks
- [ ] Keep total additions to **~200-250 lines** (vs 450+ in ai-engineer)

**Simplification Strategy**:
- Focus on flag syntax and auto-detection logic
- Use concise examples (1-2 per mode)
- Defer verbose explanations to agent docs (already complete)
- Cross-reference agent files instead of duplicating content

### AC2: Context Parameter Format Instructions (OPTIONAL)

**Decision Point**: Do we need a separate instruction file?

**Option A** (Recommended - Lean):
- ❌ Skip separate `context-parameter-format.md` file
- ✅ Document format inline in `task-work.md` command (~50 lines)
- ✅ Reference agent files for detailed examples

**Option B** (If needed later):
- Create minimal `context-parameter-format.md` (~100 lines vs 292 in ai-engineer)
- Focus on format specification only
- Omit verbose parsing guidelines

**Acceptance**: Decide during implementation based on clarity of inline documentation.

### AC3: User Guide (SIMPLIFIED or DEFERRED)

**Decision Point**: Is a user guide needed now, or can we defer?

**Option A** (Recommended - Defer):
- ❌ Skip user guide for now
- ✅ Rely on command specification in `task-work.md`
- ✅ Add user guide only if users request it

**Option B** (Minimal if needed):
- Create minimal guide (~150 lines vs 439 in ai-engineer)
- Focus on quick start and examples
- Omit troubleshooting (add when issues arise)

**Acceptance**: User guide is **optional** for this task. Defer unless clearly needed.

### AC4: Templates (ESSENTIAL - But Simplified)

**File 1**: `installer/global/templates/documentation/minimal-summary-template.md`

- [ ] Create template for minimal mode summaries
- [ ] Keep to **~100-150 lines** (vs 271 in ai-engineer)
- [ ] Focus on structure, not verbose examples
- [ ] Emphasize JSON/structured data format

**File 2**: `installer/global/templates/documentation/comprehensive-checklist.md`

- [ ] Create checklist for comprehensive mode
- [ ] Keep to **~150-200 lines** (vs 336 in ai-engineer)
- [ ] List core documents (required)
- [ ] List conditional documents (optional)
- [ ] Omit verbose descriptions

**Total Templates**: ~250-350 lines (vs 607 in ai-engineer - **42% reduction**)

### AC5: Backward Compatibility

- [ ] No flag defaults to auto/standard mode (existing behavior)
- [ ] All existing tasks run without changes
- [ ] Command syntax remains compatible

### AC6: Integration Testing

- [ ] Test `--docs minimal` with simple task (complexity 1-3)
- [ ] Test `--docs standard` with medium task (complexity 4-6)
- [ ] Test `--docs comprehensive` with complex task (complexity 7-10)
- [ ] Test auto-detection (no flag) with various complexity levels
- [ ] Verify agents receive correct context parameters

## Implementation Plan

### Phase 1: Command Specification (2 hours)

**Step 1.1**: Update `installer/global/commands/task-work.md`
- Add `--docs` flag specification to usage section
- Add Step 0: Parse `--docs` flag (10-20 lines)
- Add Step 2.5: Determine documentation level (30-50 lines)
  - Auto-detection logic based on complexity
  - Force-comprehensive triggers (security, compliance, etc.)
  - Flag precedence hierarchy
- Add `<AGENT_CONTEXT>` format specification (40-60 lines)
  - Format structure
  - Example for each phase (1-2, 2.5, 4, 4.5, 5)
- Add examples section (40-60 lines)
  - Minimal mode example
  - Standard mode example
  - Comprehensive mode example

**Target**: ~200-250 lines total additions

**Step 1.2**: Decide on context-parameter-format.md
- Review inline documentation clarity
- If sufficient: Skip separate file
- If needed: Create minimal version (~100 lines)

### Phase 2: Templates (1 hour)

**Step 2.1**: Create minimal-summary-template.md
- Template structure (YAML frontmatter + sections)
- Section specifications (minimal = JSON/structured data)
- 1-2 concrete examples
- Usage notes

**Target**: ~100-150 lines

**Step 2.2**: Create comprehensive-checklist.md
- Core documents list (required files)
- Conditional documents (when to include)
- File naming conventions
- Brief descriptions (1 line each)

**Target**: ~150-200 lines

### Phase 3: Testing & Validation (1 hour)

**Step 3.1**: Manual testing
```bash
# Test minimal mode
/task-work TASK-XXX --docs minimal

# Test standard mode (default)
/task-work TASK-YYY

# Test comprehensive mode
/task-work TASK-ZZZ --docs comprehensive

# Test auto-detection
/task-work TASK-AAA  # complexity 2 → minimal
/task-work TASK-BBB  # complexity 5 → standard
/task-work TASK-CCC  # complexity 8 → comprehensive
```

**Step 3.2**: Verify context parameter passing
- Check task-manager passes context to agents
- Verify agents receive correct documentation_level
- Confirm output format matches expected mode

**Step 3.3**: Cross-check with TASK-035 agents
- Ensure command invocations match agent expectations
- Verify format consistency
- Test graceful degradation

## Files to Create/Modify

### Required Updates (3-4 files)
1. **`installer/global/commands/task-work.md`** (~200-250 lines added)
2. **`installer/global/templates/documentation/minimal-summary-template.md`** (NEW, ~100-150 lines)
3. **`installer/global/templates/documentation/comprehensive-checklist.md`** (NEW, ~150-200 lines)

### Optional (Defer if not needed)
4. **`installer/global/instructions/context-parameter-format.md`** (OPTIONAL, ~100 lines)
5. **`docs/guides/documentation-levels-guide.md`** (OPTIONAL, ~150 lines)

**Total Lines**: ~450-600 lines (vs ~1,788 in ai-engineer - **67% reduction**)

## Simplification Strategies

### 1. Inline Over Separate Files
- Document `<AGENT_CONTEXT>` format in task-work.md instead of separate file
- Reduces file proliferation
- Easier to maintain

### 2. Examples Over Explanations
- Show 1-2 concrete examples per mode
- Avoid verbose explanations (agents already documented)
- Trust users to understand from examples

### 3. Cross-Reference Over Duplicate
- Reference agent files for detailed behavior
- Avoid duplicating agent-specific documentation
- Command file focuses on **orchestration**, not agent internals

### 4. Minimal Templates
- Templates show structure, not content
- Users already have agent docs for content guidance
- Keep templates DRY (Don't Repeat Yourself)

### 5. Defer User Guides
- Command specification should be sufficient
- Add guide only when users request it
- Avoid premature documentation

## Success Metrics

### Implementation Metrics
- ✅ Command updated with `--docs` flag support (~200-250 lines)
- ✅ Templates created (2 files, ~250-350 lines total)
- ✅ Context format documented (inline or separate file)
- ✅ **67% documentation reduction** compared to ai-engineer

### Functional Metrics
- ✅ `--docs` flag works (minimal/standard/comprehensive)
- ✅ Auto-detection works (complexity-based)
- ✅ Agents receive correct context parameters
- ✅ Output format matches selected mode
- ✅ Backward compatible (no flag = auto/standard)

### Quality Metrics
- ✅ Documentation is clear and concise
- ✅ Examples are concrete and runnable
- ✅ Cross-references work correctly
- ✅ No duplicate content between files

## Strategic Value

### Immediate Benefits
1. **Time Reduction**: 50-78% faster for simple tasks (8-12 min vs 36 min)
2. **Token Reduction**: 50-67% fewer tokens for simple tasks (100-150k vs 250-500k)
3. **Feature Parity**: TaskWright matches ai-engineer's documentation control
4. **Workflow Efficiency**: Users can choose appropriate documentation level

### Long-Term Benefits
1. **Taskwright Development**: Fast iteration with minimal documentation overhead
2. **Require-kit Development**: Same benefits during split and setup
3. **Learnings for ai-engineer**: Refined approach can be backported
4. **User Experience**: Faster feedback loop for simple tasks

## Dependencies

**Blocked by**: None (TASK-035 completed - agents ready)
**Blocks**: None (independent improvement)

## Related Documentation

- **TASK-035 Implementation**: `TASK-035-TASKWRIGHT-IMPLEMENTATION-SUMMARY.md`
- **Comparison Analysis**: `TASK-035-COMPARISON-WITH-AI-ENGINEER.md`
- **ai-engineer Reference**: `/Users/richardwoollcott/Projects/appmilla_github/ai-engineer/docs/requirements/TASK-035-FINAL-IMPLEMENTATION-SUMMARY.md`
- **Agent Files (Already Updated)**:
  - `installer/global/agents/architectural-reviewer.md`
  - `installer/global/agents/test-orchestrator.md`
  - `installer/global/agents/code-reviewer.md`
  - `installer/global/agents/task-manager.md`
  - `installer/global/agents/test-verifier.md`

## Timeline Estimate

**Total Time**: 3-4 hours
- Phase 1 (Command Specification): 2 hours
- Phase 2 (Templates): 1 hour
- Phase 3 (Testing): 1 hour

**Complexity**: 4/10 (Medium)
- Clear reference implementation (ai-engineer)
- Agents already updated (integration points known)
- Mainly documentation work
- Some decisions on simplification

**Priority**: Medium
- Not blocking other work
- Valuable for taskwright/require-kit development
- Can be completed incrementally

## Definition of Done

- ✅ `installer/global/commands/task-work.md` updated with `--docs` flag and documentation level logic
- ✅ Templates created for minimal and comprehensive modes
- ✅ Context parameter format documented (inline or separate file)
- ✅ Manual testing completed (minimal, standard, comprehensive modes)
- ✅ Agents receive correct context parameters
- ✅ Output format matches selected mode
- ✅ Backward compatible (no breaking changes)
- ✅ Documentation is clear, concise, and non-redundant
- ✅ Implementation summary created
- ✅ Ready for use in taskwright and require-kit development

---

**Priority Justification**: MEDIUM
- Completes documentation level implementation (builds on TASK-035)
- Enables significant time/token savings for taskwright and require-kit
- Not blocking other work (agents already functional)
- Provides valuable learnings for ai-engineer refinement

**Complexity Justification**: 4/10 (Medium)
- Reference implementation available (ai-engineer)
- Agent integration points well-defined (TASK-035)
- Mainly documentation and template work
- Requires thoughtful simplification decisions

**Estimated Time Justification**: 3-4 hours
- Command updates: 2 hours (careful integration with existing structure)
- Templates: 1 hour (structure + minimal examples)
- Testing: 1 hour (verify all modes and auto-detection)
- Buffer for simplification decisions and refinement
