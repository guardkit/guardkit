---
id: TASK-ENF5
title: Update agent selection table in task-work
status: blocked
created: 2025-11-27T12:50:00Z
updated: 2025-11-27T17:20:00Z
priority: medium
tags: [documentation, agent-discovery, task-work, maintenance]
task_type: implementation
epic: null
feature: agent-invocation-enforcement
requirements: []
dependencies: []
complexity: 2
related_to: TASK-8D3F
blocked_reason: "Replaced by TASK-ENF5-v2 with dynamic discovery approach after TASK-REV-9A4E architectural review"
superseded_by: TASK-ENF5-v2
---

# Task: Update Agent Selection Table in task-work

## ⚠️ TASK BLOCKED - SUPERSEDED BY TASK-ENF5-v2

**Status**: This task has been superseded by TASK-ENF5-v2 after TASK-REV-9A4E architectural review.

**Why Blocked**:
TASK-REV-9A4E architectural review (Finding #3) identified that this approach of maintaining a static agent selection table is fundamentally wrong. The static table:
1. Hardcodes global agent names only (ignores local template overrides)
2. Cannot accommodate template customizations (user creates custom specialist)
3. Requires manual maintenance as templates evolve
4. Contradicts the dynamic agent discovery system design

**New Approach**: TASK-ENF5-v2 (Wave 2) will implement dynamic agent discovery based on metadata matching, allowing templates to override global agents and eliminating the need for static tables.

**Timeline**: TASK-ENF5-v2 is blocked until Phase 0 foundation fixes (TASK-ENF-P0-1 through P0-4) are complete. Do not proceed with this task.

**References**:
- Architectural Review: `.claude/reviews/TASK-REV-9A4E-review-report.md` (Finding #3)
- Implementation Guide: `tasks/backlog/agent-invocation-enforcement/IMPLEMENTATION-GUIDE.md` (Wave 2)

---

## Original Context (For Reference Only)

**From TASK-8D3F Review**: The agent selection table in `task-work.md` (lines 968-973) contains references to agents that don't exist:
- `maui-usecase-specialist` - Referenced for MAUI stack but doesn't exist in `installer/global/agents/`
- `engine-domain-logic-specialist` - Reported in MyDrive TASK-ROE-007g but not a global agent

This creates confusion about:
1. Which agents should actually be invoked for each stack
2. Whether agent discovery is working correctly
3. What to do when the referenced agent doesn't exist

**Priority**: MEDIUM - Doesn't prevent protocol violations but reduces confusion and improves documentation accuracy.

## Objective

Update the agent selection table to:
1. Reference only agents that actually exist in `installer/global/agents/`
2. Clearly indicate when fallback to `task-manager` is used
3. Add a "Notes" column explaining agent selection decisions
4. Consider creating missing specialists if MAUI requires specialized handling

## Requirements

### R1: Audit Current Agent Table

**Requirement**: Verify which agents in the table actually exist

**Current Table** (lines 968-973):
```markdown
| Stack | Analysis | Planning | Arch Review | Implementation | Testing | Review |
|-------|----------|----------|-------------|----------------|---------|--------|
| **maui** | requirements-analyst | maui-usecase-specialist | architectural-reviewer | maui-usecase-specialist | dotnet-testing-specialist | code-reviewer |
| **react** | requirements-analyst | react-state-specialist | architectural-reviewer | react-state-specialist | react-testing-specialist | code-reviewer |
| **python** | requirements-analyst | python-api-specialist | architectural-reviewer | python-api-specialist | python-testing-specialist | code-reviewer |
| **python-mcp** | requirements-analyst | python-mcp-specialist | architectural-reviewer | python-mcp-specialist | python-testing-specialist | code-reviewer |
```

**Audit Results** (from TASK-8D3F review):
- ✅ `react-state-specialist` - EXISTS
- ✅ `python-api-specialist` - EXISTS
- ✅ `dotnet-domain-specialist` - EXISTS (but not in table)
- ✅ `architectural-reviewer` - EXISTS
- ✅ `code-reviewer` - EXISTS
- ❌ `maui-usecase-specialist` - DOES NOT EXIST
- ❌ `python-mcp-specialist` - NOT VERIFIED
- ❌ `react-testing-specialist` - NOT VERIFIED
- ❌ `python-testing-specialist` - NOT VERIFIED
- ❌ `dotnet-testing-specialist` - NOT VERIFIED

**Acceptance Criteria**:
- [ ] All agents in table verified to exist or marked as non-existent
- [ ] Agent files checked in `installer/global/agents/`
- [ ] Metadata verified (stack, phase, capabilities)
- [ ] Audit results documented

### R2: Update Agent Table with Accurate References

**Requirement**: Replace non-existent agent references with actual agents or fallback

**Option A: Use dotnet-domain-specialist for MAUI**

If MAUI can use general .NET domain specialist:

```markdown
| Stack | Planning | Arch Review | Implementation | Testing | Review | Notes |
|-------|----------|-------------|----------------|---------|--------|-------|
| **maui** | dotnet-domain-specialist | architectural-reviewer | dotnet-domain-specialist | task-manager (fallback) | code-reviewer | Uses .NET domain specialist; testing specialist pending |
| **react** | react-state-specialist | architectural-reviewer | react-state-specialist | task-manager (fallback) | code-reviewer | ✅ Verified |
| **python** | python-api-specialist | architectural-reviewer | python-api-specialist | task-manager (fallback) | code-reviewer | ✅ Verified |
| **dotnet** | dotnet-domain-specialist | architectural-reviewer | dotnet-domain-specialist | task-manager (fallback) | code-reviewer | ✅ Verified |
```

**Option B: Create maui-usecase-specialist**

If MAUI requires specialized handling beyond general .NET patterns:

See R3 for creating new specialist agent.

**Acceptance Criteria**:
- [ ] Table references only existing agents
- [ ] Fallback to `task-manager` clearly indicated
- [ ] Notes column explains agent selection decisions
- [ ] Verification status shown (✅ for tested, ⚠️ for fallback)

### R3: Decide on MAUI Specialist Strategy

**Requirement**: Determine if MAUI needs a dedicated specialist or can use dotnet-domain-specialist

**Evaluation Criteria**:

**Use dotnet-domain-specialist if**:
- MAUI tasks primarily involve domain logic (entities, value objects, repositories)
- No MAUI-specific patterns beyond standard .NET
- MVVM, data binding handled by existing .NET knowledge

**Create maui-usecase-specialist if**:
- MAUI tasks require XAML-specific knowledge
- Navigation patterns are unique to MAUI
- Platform-specific implementations (iOS/Android) need specialization
- MVVM patterns differ significantly from standard .NET

**Decision Process**:
1. Review existing MAUI tasks in MyDrive or other projects
2. Identify if MAUI-specific patterns are common
3. Check if `dotnet-domain-specialist` capabilities cover MAUI needs
4. Make recommendation: Use existing vs Create new

**Acceptance Criteria**:
- [ ] MAUI task patterns analyzed
- [ ] Decision documented (use dotnet-domain-specialist OR create maui-usecase-specialist)
- [ ] Rationale provided for decision
- [ ] If creating new: Metadata and capabilities defined

### R4: Create maui-usecase-specialist (If Needed)

**Requirement**: If decision is to create MAUI specialist, implement it

**Implementation** (Optional - Only if R3 decision is "Create new"):

```bash
# Create agent file
touch installer/global/agents/maui-usecase-specialist.md
```

**Frontmatter Metadata**:
```yaml
---
name: maui-usecase-specialist
description: .NET MAUI use case and MVVM pattern implementation specialist
tools: [Read, Write, Edit, Bash, Grep]
model: haiku
model_rationale: "MAUI use case implementation follows MVVM patterns. Haiku provides fast, cost-effective implementation at 90% quality."

# Discovery metadata
stack: [maui, dotnet]
phase: implementation
capabilities:
  - MVVM pattern implementation
  - Use case orchestration with MediatR
  - XAML view and ViewModel binding
  - Navigation service implementation
  - Platform-specific implementations (iOS/Android)
  - Data binding and ICommand patterns
  - Dependency injection for ViewModels
keywords: [maui, xaml, mvvm, viewmodel, navigation, data-binding, use-case, mediatr, mobile]

collaborates_with:
  - dotnet-domain-specialist
  - dotnet-testing-specialist
  - architectural-reviewer
---
```

**Agent Content**:
- Quick Start examples for MVVM ViewModels
- Use case implementation with MediatR
- Navigation service patterns
- Data binding best practices
- Platform-specific code examples

**Acceptance Criteria** (If creating):
- [ ] Agent file created in `installer/global/agents/`
- [ ] Frontmatter metadata complete and correct
- [ ] Capabilities cover MAUI-specific patterns
- [ ] Quick Start examples provided
- [ ] Collaborates_with field references related agents

### R5: Add Notes Column to Agent Table

**Requirement**: Add "Notes" column to explain agent selection decisions

**Updated Table Format**:
```markdown
| Stack | Planning | Implementation | Testing | Review | Notes |
|-------|----------|----------------|---------|--------|-------|
| **maui** | dotnet-domain-specialist | dotnet-domain-specialist | task-manager | code-reviewer | Uses .NET domain specialist; testing specialist pending |
| **react** | react-state-specialist | react-state-specialist | task-manager | code-reviewer | ✅ Verified; testing specialist pending |
| **python** | python-api-specialist | python-api-specialist | task-manager | code-reviewer | ✅ Verified; testing specialist pending |
```

**Notes Guidance**:
- "✅ Verified" - Agent exists and has been tested
- "Uses X specialist" - Stack uses another stack's specialist
- "Testing specialist pending" - No dedicated testing specialist yet
- "Fallback to task-manager" - No specialist available

**Acceptance Criteria**:
- [ ] Notes column added to table
- [ ] Each stack has explanatory note
- [ ] Verification status clear
- [ ] Pending work clearly indicated

## Implementation Plan

### Phase 1: Audit Current State

**Tasks**:
1. Check existence of all agents in table
2. Verify agent metadata (stack, phase, capabilities)
3. Document audit results
4. Identify gaps (missing agents)

**Duration**: 1 hour

### Phase 2: Make MAUI Specialist Decision

**Tasks**:
1. Review MAUI task patterns
2. Compare with dotnet-domain-specialist capabilities
3. Make recommendation
4. Document decision and rationale

**Duration**: 30 minutes

### Phase 3: Update Agent Table

**Tasks**:
1. Replace non-existent agent references
2. Add "Notes" column
3. Update stack rows with accurate information
4. Add verification status

**Duration**: 30 minutes

### Phase 4: Create MAUI Specialist (Optional)

**Tasks** (Only if decision is "Create new"):
1. Create `maui-usecase-specialist.md` file
2. Write frontmatter metadata
3. Add Quick Start examples
4. Add MVVM and use case patterns
5. Test agent with sample MAUI task

**Duration**: 2-3 hours (if needed)

### Phase 5: Testing

**Tasks**:
1. Verify all table references are valid
2. Test agent selection for each stack
3. Confirm fallback behavior when specialist not found
4. Update documentation if needed

**Duration**: 30 minutes

## Success Criteria

### SC1: Table Accuracy

- [ ] All agents in table actually exist
- [ ] No references to non-existent agents
- [ ] Fallback clearly indicated when specialist not available

### SC2: MAUI Strategy Clear

- [ ] Decision documented (use dotnet-domain-specialist OR create maui-usecase-specialist)
- [ ] Rationale provided
- [ ] Implementation complete (if creating new specialist)

### SC3: Documentation Improved

- [ ] Notes column provides context for agent selection
- [ ] Verification status clear
- [ ] Users understand which agents will be invoked

### SC4: No Breaking Changes

- [ ] Agent discovery continues to work
- [ ] Existing tasks unaffected
- [ ] Fallback behavior preserved

## Estimated Effort

**Without creating new specialist**: 1-2 hours
- Phase 1: 1 hour
- Phase 2: 30 minutes
- Phase 3: 30 minutes
- Phase 5: 30 minutes

**With creating new specialist**: 4-5 hours
- Add Phase 4: 2-3 hours

## Related Tasks

- TASK-8D3F - Review task that identified this gap
- TASK-ENF2 - Agent invocation tracking (uses agent metadata)
- Agent Discovery Guide - Documents metadata schema

## Notes

**Low Priority but High Value**: This task doesn't prevent protocol violations but significantly improves documentation accuracy and reduces confusion.

**Decision Required**: Need to decide in R3 whether to create `maui-usecase-specialist` or use `dotnet-domain-specialist` for MAUI stack.

**Future Work**: Consider creating dedicated testing specialists for each stack (react-testing-specialist, python-testing-specialist, etc.) to replace task-manager fallback.

**Testing**: After updating table, test agent selection for MAUI stack to confirm correct agent is invoked (either dotnet-domain-specialist or maui-usecase-specialist).
