# Design URL Integration - Implementation Guide

**Based on**: [design-url-integration-proposal.md](./design-url-integration-proposal.md)
**Status**: Ready for implementation
**Priority**: High

## Overview

This guide provides a complete implementation roadmap for integrating design URLs (Figma, Zeplin) into the task workflow. All tasks use the `UX` prefix for easy tracking.

## Task Summary

| Task ID | Title | Priority | Type | Method | Dependencies |
|---------|-------|----------|------|--------|--------------|
| TASK-UX-7F1E | Add design URL parameter to task-create | High | Code | /task-work | None |
| TASK-UX-C3A3 | Implement design URL validation | High | Code | /task-work | UX-7F1E |
| TASK-UX-2A61 | Refactor figma-react-orchestrator to figma-orchestrator | High | Code | /task-work | None |
| TASK-UX-EFC3 | Refactor zeplin-maui-orchestrator to zeplin-orchestrator | High | Code | /task-work | None |
| TASK-UX-71BD | Extend react-ui-specialist to handle design contexts | High | Code | /task-work | UX-2A61, UX-EFC3 |
| TASK-UX-92BF | Extend nextjs-ui-specialist to handle design contexts | High | Code | /task-work | UX-2A61, UX-EFC3 |
| TASK-UX-6D04 | Update task-work Phase 1 to load design URL | High | Code | /task-work | UX-7F1E, UX-C3A3 |
| TASK-UX-7E5E | Update task-work Phase 3 to route to orchestrators | High | Code | /task-work | UX-6D04, UX-2A61, UX-EFC3, UX-71BD, UX-92BF |
| TASK-UX-0BBB | Update task-refine for design context awareness | Medium | Code | /task-work | UX-7F1E, UX-6D04 |
| TASK-UX-2DAB | Deprecate old commands (figma-to-react, zeplin-to-maui) | Medium | Code | /task-work | UX-7F1E, UX-6D04, UX-7E5E |
| TASK-UX-602E | Create design-to-code user guide | High | Docs | Manual | All UX tasks |
| TASK-UX-187C | Update CLAUDE.md documentation | High | Docs | Manual | UX-602E |
| TASK-UX-F172 | Create pattern documentation for developers | Medium | Docs | Manual | All UX tasks |

## Implementation Phases

### Phase 1: Core Infrastructure (Sequential)

These tasks must be completed **in order** as they form the foundation:

```bash
# TASK-UX-7F1E: Add design URL parameter to task-create
/task-work TASK-UX-7F1E

# TASK-UX-C3A3: Implement design URL validation (depends on UX-7F1E)
/task-work TASK-UX-C3A3
```

**Deliverables**:
- ✅ `/task-create` accepts `design:URL` parameter
- ✅ Design URL stored in task frontmatter
- ✅ Design source auto-detected (figma/zeplin/sketch)
- ✅ URL validation with fail-fast error handling
- ✅ MCP availability check

**Testing**:
```bash
# Test design URL parameter
/task-create "Test task" design:https://figma.com/design/abc?node-id=2-2

# Test validation
/task-create "Invalid" design:https://invalid-url.com/test
```

**Estimated Duration**: 4-6 hours

---

### Phase 2: Refactor Orchestrators (Parallel)

These tasks refactor existing orchestrators to be technology-agnostic. Can be developed **simultaneously** using Conductor + git worktrees:

#### Worktree Setup
```bash
# Main branch (Figma orchestrator)
conductor start ux-figma-orchestrator main
cd .conductor/ux-figma-orchestrator
/task-work TASK-UX-2A61

# Separate worktree (Zeplin orchestrator)
conductor start ux-zeplin-orchestrator main
cd .conductor/ux-zeplin-orchestrator
/task-work TASK-UX-EFC3
```

#### TASK-UX-2A61: Refactor figma-react-orchestrator
**Source File**: `installer/global/agents/figma-react-orchestrator.md`
**Target File**: `installer/global/agents/figma-orchestrator.md`

**Deliverables**:
- ✅ Remove React-specific naming and references
- ✅ Make orchestrator technology-agnostic (delegates to any UI specialist)
- ✅ Update delegation pattern to accept stack parameter
- ✅ Keep 6-phase Saga pattern intact
- ✅ Update MCP integration (Figma)
- ✅ Update constraint validation to work with any stack

**Key Changes**:
- Rename file: `figma-react-orchestrator.md` → `figma-orchestrator.md`
- Update agent name: `figma-react-orchestrator` → `figma-orchestrator`
- Change delegation from `react-component-generator` to `{stack}-ui-specialist`
- Remove React-specific code examples, make them generic

**Dependencies**: None (can start immediately)

#### TASK-UX-EFC3: Refactor zeplin-maui-orchestrator
**Source File**: `installer/global/agents/zeplin-maui-orchestrator.md`
**Target File**: `installer/global/agents/zeplin-orchestrator.md`

**Deliverables**:
- ✅ Remove MAUI-specific naming and references
- ✅ Make orchestrator technology-agnostic (delegates to any UI specialist)
- ✅ Update delegation pattern to accept stack parameter
- ✅ Keep 6-phase Saga pattern intact
- ✅ Update MCP integration (Zeplin)
- ✅ Update constraint validation to work with any stack

**Key Changes**:
- Rename file: `zeplin-maui-orchestrator.md` → `zeplin-orchestrator.md`
- Update agent name: `zeplin-maui-orchestrator` → `zeplin-orchestrator`
- Change delegation from `maui-ux-specialist` to `{stack}-ui-specialist`
- Remove MAUI-specific code examples, make them generic

**Dependencies**: None (can start immediately)

**Estimated Duration**: 6-8 hours (parallel)

---

### Phase 3: Extend UI Specialists (Parallel) + Task-Work Integration

These tasks extend existing UI specialists and update task-work:

#### Parallel Development (UX-71BD, UX-92BF)
```bash
# Terminal 1: Extend react-ui-specialist
conductor start ux-react-specialist main
cd .conductor/ux-react-specialist
/task-work TASK-UX-71BD

# Terminal 2: Extend nextjs-ui-specialist
conductor start ux-nextjs-specialist main
cd .conductor/ux-nextjs-specialist
/task-work TASK-UX-92BF
```

#### TASK-UX-71BD: Extend react-ui-specialist
**File**: `installer/global/templates/react-typescript/agents/react-ui-specialist.md`

**Deliverables**:
- ✅ Detect design context from orchestrator
- ✅ Handle design-driven implementation when context present
- ✅ Generate components matching design specifications
- ✅ Run visual regression tests (Playwright)
- ✅ Return results to orchestrator for validation
- ✅ Graceful fallback to standard UI implementation when no design context

**Key Changes**:
```markdown
## Design Context Handling

if task.design_context:
    # Received from figma-orchestrator
    designElements = task.design_context.elements
    prohibitions = task.design_context.prohibitions
    visualReference = task.design_context.visualReference

    # Generate component matching design exactly
    generate_react_component(designElements, prohibitions)

    # Run visual regression tests
    visual_fidelity = run_playwright_tests(visualReference)

    # Return to orchestrator for validation
    return { generated_files, visual_fidelity, constraint_violations }
else:
    # Standard UI implementation
    implement_standard_react_ui(task)
```

**Dependencies**: UX-2A61, UX-EFC3 (orchestrators must be refactored first)

#### TASK-UX-92BF: Extend nextjs-ui-specialist
**File**: `installer/global/templates/nextjs-fullstack/agents/nextjs-ui-specialist.md`

**Deliverables**:
- ✅ Detect design context from orchestrator
- ✅ Handle design-driven implementation when context present
- ✅ Generate Next.js components matching design specifications
- ✅ Run visual regression tests
- ✅ Return results to orchestrator for validation
- ✅ Graceful fallback to standard UI implementation when no design context

**Dependencies**: UX-2A61, UX-EFC3 (orchestrators must be refactored first)

**Estimated Duration**: 6-8 hours (parallel)

---

#### Sequential Tasks (UX-6D04, UX-7E5E)
```bash
# TASK-UX-6D04: Update task-work Phase 1
/task-work TASK-UX-6D04

# TASK-UX-7E5E: Update task-work Phase 3 (depends on UX-6D04)
/task-work TASK-UX-7E5E
```

#### TASK-UX-6D04: Update task-work Phase 1
**File**: `installer/global/commands/task-work.md` (Phase 1 section)

**Deliverables**:
- ✅ Load `design_url` from task frontmatter
- ✅ Parse design source (figma/zeplin/sketch)
- ✅ Verify MCP server availability
- ✅ Store design context for Phase 3

**Dependencies**: UX-7F1E, UX-C3A3

#### TASK-UX-7E5E: Update task-work Phase 3
**File**: `installer/global/commands/task-work.md` (Phase 3 section)

**Deliverables**:
- ✅ Detect presence of design_url in task
- ✅ Auto-detect project stack (React, Next.js, MAUI, Flutter, etc.)
- ✅ Route to appropriate orchestrator based on design source
- ✅ Orchestrator delegates to stack-specific UI specialist
- ✅ Graceful fallback if no design URL
- ✅ Pass design context from orchestrator to UI specialist

**Routing Logic**:
```python
if task.design_url:
    stack = detect_stack()  # react-typescript, nextjs-fullstack, maui, etc.
    design_source = task.design_source  # figma, zeplin, sketch

    # Select orchestrator based on design source
    if design_source == "figma":
        orchestrator = "figma-orchestrator"
    elif design_source == "zeplin":
        orchestrator = "zeplin-orchestrator"

    # Orchestrator handles MCP extraction, then delegates to UI specialist
    invoke_orchestrator(orchestrator, task, target_specialist=f"{stack}-ui-specialist")
else:
    # Standard implementation without design extraction
    invoke_standard_implementation(task)
```

**Dependencies**: UX-6D04, UX-2A61, UX-EFC3, UX-71BD, UX-92BF

**Estimated Duration**: 4-6 hours

---

### Phase 4: Supporting Features (Parallel-capable)

This task supports design URL updates:

```bash
/task-work TASK-UX-0BBB  # task-refine support
```

#### TASK-UX-0BBB: Update task-refine for design context awareness
**File**: `installer/global/commands/task-refine.md`

**Deliverables**:
- ✅ Detect design context from task frontmatter
- ✅ Enforce constraint boundaries during refinements
- ✅ Warn about staying within design boundaries
- ✅ Re-validate prohibition checklist after refinements
- ✅ Block refinements that violate constraints

**Usage**:
```bash
/task-refine TASK-001 "Update button hover color to blue-700"
```

**Dependencies**: UX-7F1E, UX-6D04

**Estimated Duration**: 2-3 hours

---

### Phase 5: Deprecation (Sequential)

This task should only run **after** Phase 3 is complete and tested:

```bash
# After UX-7E5E is completed and tested
/task-work TASK-UX-2DAB
```

#### TASK-UX-2DAB: Deprecate old commands (figma-to-react, zeplin-to-maui)
**Files**:
- `installer/global/commands/figma-to-react.md`
- `installer/global/commands/zeplin-to-maui.md`

**Deliverables**:
- ✅ Add deprecation warnings to command headers
- ✅ Redirect users to new workflow
- ✅ Keep commands functional for backward compatibility
- ✅ Update command documentation

**Deprecation Warning**:
```markdown
> ⚠️ **DEPRECATED**: This command is deprecated in favor of the integrated workflow.
>
> **New approach**:
> ```bash
> /task-create "Implement login form" design:https://figma.com/design/abc?node-id=2-2
> /task-work TASK-001
> ```
>
> This command will be removed in a future version.
```

**Dependencies**: UX-7F1E, UX-6D04, UX-7E5E (must be fully tested)

**Estimated Duration**: 2-3 hours

---

### Phase 6: Documentation (Manual)

These tasks are **manual documentation**:

#### TASK-UX-602E: Create design-to-code user guide
**File**: `docs/guides/design-to-code-user-guide.md`

**Content**:
- Overview of design URL integration
- Supported design tools (Figma, Zeplin)
- Two-tier architecture (Orchestrators + UI Specialists)
- Stack-specific workflows (React, Next.js, Future stacks)
- Example usage for each stack
- MCP setup requirements
- Troubleshooting common issues

**Method**: Manual writing (no `/task-work`)

**Dependencies**: All UX tasks (for accurate documentation)

#### TASK-UX-187C: Update CLAUDE.md documentation
**File**: `CLAUDE.md`

**Updates**:
- Add design URL workflow to "Essential Commands"
- Update UX Design Integration section with two-tier architecture
- Add examples showing orchestrator → UI specialist flow
- Update migration notes
- Remove references to deprecated standalone commands

**Method**: Manual editing (no `/task-work`)

**Dependencies**: UX-602E (user guide should be completed first)

#### TASK-UX-F172: Create pattern documentation for developers
**File**: `docs/patterns/design-to-code-architecture.md`

**Content**:
- Two-tier architecture overview (Orchestrators + UI Specialists)
- Shared 6-phase Saga pattern (in orchestrators)
- UI specialist interface contract
- How orchestrators delegate to UI specialists
- Template integration guidelines
- How to add new stack support via `/template-create`

**Method**: Manual writing (no `/task-work`)

**Dependencies**: All UX tasks (for accurate technical documentation)

**Estimated Duration**: 4-6 hours (parallel)

---

## Execution Strategy

### Sequential Execution (Safe)
Execute all tasks in order for guaranteed correctness:

```bash
/task-work TASK-UX-7F1E  # 2-3h - Add design URL parameter
/task-work TASK-UX-C3A3  # 2-3h - Implement validation
/task-work TASK-UX-2A61  # 3-4h - Refactor figma orchestrator
/task-work TASK-UX-EFC3  # 3-4h - Refactor zeplin orchestrator
/task-work TASK-UX-71BD  # 4-6h - Extend react-ui-specialist
/task-work TASK-UX-92BF  # 4-6h - Extend nextjs-ui-specialist
/task-work TASK-UX-6D04  # 5-7h - Update task-work Phase 1
/task-work TASK-UX-7E5E  # 6-8h - Update task-work Phase 3
/task-work TASK-UX-0BBB  # 4-5h - Update task-refine
/task-work TASK-UX-2DAB  # 3-4h - Deprecate old commands

# Manual documentation
# TASK-UX-602E (6-8h), UX-187C (3-4h), UX-F172 (8-10h)

# Total: ~54-72 hours
```

### Parallel Execution (Faster with Conductor)

**Day 1** (Phase 1):
```bash
/task-work TASK-UX-7F1E  # Add design URL parameter
/task-work TASK-UX-C3A3  # Implement validation
```

**Day 2** (Phase 2 - Parallel):
```bash
# Terminal 1
conductor start ux-figma-orchestrator main
cd .conductor/ux-figma-orchestrator
/task-work TASK-UX-2A61  # Refactor figma orchestrator

# Terminal 2
conductor start ux-zeplin-orchestrator main
cd .conductor/ux-zeplin-orchestrator
/task-work TASK-UX-EFC3  # Refactor zeplin orchestrator
```

**Day 3** (Phase 3 - Parallel):
```bash
# Terminal 1
conductor start ux-react-specialist main
cd .conductor/ux-react-specialist
/task-work TASK-UX-71BD  # Extend react-ui-specialist

# Terminal 2
conductor start ux-nextjs-specialist main
cd .conductor/ux-nextjs-specialist
/task-work TASK-UX-92BF  # Extend nextjs-ui-specialist
```

**Day 4** (Phase 4):
```bash
/task-work TASK-UX-6D04  # Update task-work Phase 1
/task-work TASK-UX-7E5E  # Update task-work Phase 3
```

**Day 5** (Phase 5 + Documentation):
```bash
/task-work TASK-UX-0BBB  # Update task-refine
/task-work TASK-UX-2DAB  # Deprecate old commands

# Start manual documentation
# TASK-UX-602E, UX-187C, UX-F172
```

**Total: ~5-7 days (with parallelization)**

---

## Testing Strategy

### Integration Testing

After Phase 4 (TASK-UX-7E5E), test the complete workflow:

#### React + Figma
```bash
cd ~/test-react-project
/task-create "Login form" design:https://figma.com/design/abc?node-id=2-2 priority:high prefix:TEST
/task-work TASK-TEST-001

# Expected:
# ✅ Detects React stack
# ✅ Detects Figma design URL
# ✅ Routes to figma-orchestrator
# ✅ Orchestrator delegates to react-ui-specialist
# ✅ Generates TypeScript React + Tailwind
# ✅ Runs Playwright visual tests
# ✅ Visual fidelity >95%
```

#### Next.js + Zeplin
```bash
cd ~/test-nextjs-project
/task-create "User profile" design:https://app.zeplin.io/project/abc/screen/def priority:high prefix:TEST
/task-work TASK-TEST-002

# Expected:
# ✅ Detects Next.js stack
# ✅ Detects Zeplin design URL
# ✅ Routes to zeplin-orchestrator
# ✅ Orchestrator delegates to nextjs-ui-specialist
# ✅ Generates Next.js component (Server/Client as appropriate)
# ✅ Runs Playwright visual tests
# ✅ Visual fidelity >95%
```

#### No Design URL (Graceful Fallback)
```bash
/task-create "Add validation logic" priority:high prefix:TEST
/task-work TASK-TEST-003

# Expected:
# ✅ Standard implementation workflow
# ✅ No design extraction
# ✅ No UX specialist invocation
```

### Error Handling Tests

```bash
# Test invalid URL
/task-create "Test" design:https://invalid-url.com/test
# Expected: ❌ Validation error with helpful message

# Test missing MCP
/task-create "Test" design:https://figma.com/design/abc?node-id=2-2
# Expected: ❌ Error if figma-dev-mode MCP not installed

# Test refinement with design context
/task-create "Login" design:https://figma.com/design/abc?node-id=2-2
/task-work TASK-TEST-004
/task-complete TASK-TEST-004
/task-refine TASK-TEST-004 "Update button hover color"
# Expected: ✅ Refinement succeeds, constraints validated

# Test refinement that violates constraints
/task-refine TASK-TEST-004 "Add API call to fetch user data"
# Expected: ❌ Error - constraint violation detected
```

---

## Risk Mitigation

### High-Risk Areas

1. **MCP Integration**
   - **Risk**: MCP servers may not be installed or configured
   - **Mitigation**: Validation in UX-002, clear error messages

2. **Stack Detection**
   - **Risk**: May not detect all stacks correctly
   - **Mitigation**: Explicit fallback to standard workflow

3. **Template Agent Discovery**
   - **Risk**: Agents may not be found in template directories
   - **Mitigation**: Installer verification (UX-011)

4. **Breaking Changes**
   - **Risk**: Existing workflows disrupted
   - **Mitigation**: Deprecation warnings (UX-008), backward compatibility

### Rollback Plan

If critical issues arise:
1. Keep deprecated commands (`/figma-to-react`, `/zeplin-to-maui`) functional
2. Add feature flag to disable design URL integration
3. Clear migration documentation

---

## Success Criteria

### Phase 1 Complete When:
- ✅ `/task-create` accepts `design:URL` parameter
- ✅ Design URL stored in frontmatter
- ✅ Validation catches invalid URLs
- ✅ Tests pass

### Phase 2 Complete When:
- ✅ figma-orchestrator refactored (technology-agnostic)
- ✅ zeplin-orchestrator refactored (technology-agnostic)
- ✅ Both orchestrators delegate to UI specialists correctly
- ✅ 6-phase Saga pattern intact

### Phase 3 Complete When:
- ✅ react-ui-specialist handles design contexts
- ✅ nextjs-ui-specialist handles design contexts
- ✅ Visual regression tests run successfully
- ✅ Zero scope creep constraints enforced

### Phase 4 Complete When:
- ✅ task-work routes to correct specialist based on stack + design source
- ✅ Graceful fallback for tasks without design URLs
- ✅ Integration tests pass for React + Figma
- ✅ Integration tests pass for React + Zeplin

### All Phases Complete When:
- ✅ All 13 tasks marked as completed
- ✅ Documentation updated (user guide, CLAUDE.md, pattern docs)
- ✅ Old commands deprecated with migration path
- ✅ Real-world testing successful
- ✅ Integration tests pass for all stacks

---

## Quick Start

### To begin implementation:

```bash
# 1. Check proposal is approved
cat docs/proposals/design-url-integration-proposal.md

# 2. Start with Phase 1
/task-work TASK-UX-7F1E

# 3. Follow this guide phase by phase
```

### For questions or issues:
- Review proposal: `docs/proposals/design-url-integration-proposal.md`
- Check task status: `/task-status TASK-UX-*`
- Review workflow: `docs/guides/guardkit-workflow.md`

---

## Notes

- All task IDs use `UX` prefix for easy tracking (hash-based IDs)
- Use Conductor for parallel development where indicated
- Documentation tasks (UX-602E, UX-187C, UX-F172) are manual
- Test thoroughly after Phase 3 before proceeding to deprecation
- Keep deprecated commands functional for backward compatibility
- Total implementation: 13 tasks across 6 phases
- Estimated duration: 54-72 hours sequential, 5-7 days with parallelization
