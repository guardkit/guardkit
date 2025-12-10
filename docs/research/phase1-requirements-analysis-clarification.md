# Phase 1 Requirements Analysis - Clarification and Decision Summary

**Date**: 2025-11-03
**Context**: Documentation audit for GuardKit/RequireKit separation
**Related Tasks**: TASK-022 (completed), TASK-023, TASK-024, TASK-025 (backlog)

## Executive Summary

There has been confusion about "Phase 1" in GuardKit due to two different concepts using the same name:

1. **"Phase 1: Requirements Analysis"** - A RequireKit-only feature (EARS, BDD) that was correctly removed
2. **"Phase 1: Load Task Context"** - Actual GuardKit implementation (file operations) that still exists

**Decision**: Keep the current implementation (Phase 1 is task loading only). Fix documentation to eliminate confusion about requirements analysis being part of GuardKit core.

## The Two "Phase 1" Concepts

### Phase 1A: Requirements Analysis (RequireKit-only) ❌

**What it was:**
- Invoked the `requirements-analyst` agent
- Performed EARS notation analysis
- Generated BDD/Gherkin scenarios
- Created formal requirements documentation

**Status:**
- **Removed in TASK-003** (guardkit/require-kit split)
- **Fixed in TASK-022** (removed broken references)
- **Never coming back** to GuardKit core

**Why removed:**
- Contradicts GuardKit's lightweight positioning
- Adds unnecessary complexity for simple task workflows
- Task descriptions + acceptance criteria are sufficient
- Formal requirements belong in RequireKit

### Phase 1B: Load Task Context (GuardKit core) ✅

**What it does:**
- Parse and validate task ID
- Multi-state file search (backlog → in_progress → in_review → blocked → completed)
- Automatic state transitions
- Load task markdown content
- Extract task metadata and acceptance criteria

**Status:**
- **Still exists and works correctly**
- **Essential for all task workflows**
- **Not related to requirements analysis**

**Implementation:** See `installer/core/commands/task-work.md` lines 547-723

**Substeps:**
```
Phase 1.1: Parse and Validate Task ID
Phase 1.2: Multi-State File Search
Phase 1.3: Handle Search Results
Phase 1.4: Automatic State Transition (if needed)
Phase 1.5: Load Task Context
```

This is purely **file and state management**, not requirements analysis.

## Historical Context: What TASK-022 Fixed

### The Problem

After TASK-003 removed `requirements-analyst` agent, the `/task-work` command was completely broken:

```
Phase 1: Requirements Analysis

⏺ requirements-analyst(Analyze requirements for TASK-001)
  ⎿  Error: Agent type 'requirements-analyst' not found.
```

**Impact**: ALL task execution failed for every user.

**Root Cause**: `task-manager.md` still tried to invoke the deleted `requirements-analyst` agent.

### The Solution (TASK-022)

**Completed**: 2025-11-02
**Duration**: 1 hour (estimated 2 hours)
**Priority**: CRITICAL

**Changes Made:**

1. **Removed Requirements-Analyst References**
   - Deleted invocation from task-manager.md
   - Updated integration sections to clarify GuardKit vs RequireKit
   - Cleaned up leftover agent files

2. **Documentation Alignment**
   - Marked Phase 1 as "require-kit only" in CLAUDE.md
   - Added skip explanation in task-work.md
   - Maintained consistency across all references

3. **Bonus Fix: Empty Project Handling**
   - Added Rule #0 in test-orchestrator.md
   - Graceful handling of empty projects (prevents false failures)

**Files Modified:**
- `installer/core/agents/task-manager.md` - Removed Phase 1 invocation
- `installer/core/agents/test-orchestrator.md` - Added empty project detection

**Files Deleted:**
- `.claude/agents/requirements-analyst.md` - Leftover cleanup
- `installer/core/templates/maui-navigationpage/agents/requirements-analyst.md` - Template cleanup

**Net Result:**
- Added: 88 lines (empty project detection logic)
- Removed: 388 lines (requirements-analyst cleanup)
- Net: -300 lines (simplified system)

### After TASK-022

✅ `/task-work` command works correctly
✅ Workflow proceeds directly from task loading → Phase 2 Planning
✅ No errors about missing agents
✅ Clear distinction between GuardKit and RequireKit workflows

## Should We Bring Back Requirements-Analyst?

### Question Posed

"Should we bring in the requirements-analyst subagent and rename/refine it for GuardKit?"

### Recommendation: NO ❌

**Reasons:**

#### 1. Already Solved Correctly
TASK-022 made the right architectural decision. The fix aligns with GuardKit's core value proposition.

#### 2. Contradicts Positioning
GuardKit is **intentionally lightweight**:
- No formal requirements gathering
- No EARS notation
- No BDD generation
- Task descriptions + acceptance criteria = enough

Adding requirements-analyst would undo this positioning.

#### 3. Task Descriptions Suffice
For GuardKit workflows, we have:
```yaml
---
title: Add user authentication
description: Implement JWT-based authentication
---

## Acceptance Criteria
- [ ] User can log in with email/password
- [ ] Session tokens are secure
- [ ] Failed attempts are rate-limited
```

This is **sufficient** for GuardKit's use case.

#### 4. RequireKit Integration Available
Users who need formal requirements can:
- Install RequireKit separately
- Use EARS notation for requirements
- Generate BDD scenarios
- Link requirements to GuardKit tasks

**Best of both worlds**: Lightweight core + optional power features.

#### 5. Avoids Feature Creep
Once we add basic requirements analysis, users will ask for:
- EARS notation support
- BDD generation
- Requirements traceability
- Epic/feature hierarchy
- PM tool synchronization

This leads us right back to rebuilding RequireKit inside GuardKit.

### What We SHOULD Do Instead

The real issue is **documentation confusion**, not missing functionality.

**Solution**: Complete documentation audit tasks (TASK-023, 024, 025) to:

1. **Remove confusing references**
   - Strike "Phase 1: Requirements Analysis" from GuardKit docs
   - Clarify "Phase 1: Load Task Context" is just file operations
   - Make phase separation crystal clear

2. **Add clear integration points**
   - "Need formal requirements?" callouts
   - Link to RequireKit where appropriate
   - Show how to use both together

3. **Resolve phase numbering**
   - Choose naming strategy (see options below)
   - Apply consistently across all docs

## Phase Numbering Strategy

### Option A: Renumber Everything (Simplest)

Remove Phase 1 numbering entirely, start from Phase 1 with planning:

```
GuardKit Phases:
├─ Phase 1: Implementation Planning
├─ Phase 1.5: Architectural Review (SOLID/DRY/YAGNI)
├─ Phase 1.7: Complexity Evaluation (0-10 scale)
├─ Phase 1.8: Human Checkpoint (design approval)
├─ Phase 2: Implementation
├─ Phase 3: Testing
├─ Phase 3.5: Test Enforcement Loop (auto-fix)
├─ Phase 4: Code Review
└─ Phase 4.5: Plan Audit (scope creep detection)
```

**Pros:**
- Eliminates confusion
- Clean numbering
- No "missing" Phase 1

**Cons:**
- Breaks backward compatibility
- Requires updating all documentation
- Users familiar with old numbering get confused
- Phase numbers in existing task files become wrong

### Option B: Keep Numbering, Clarify Separation (Recommended) ⭐

Keep current numbering, explicitly show RequireKit vs GuardKit phases:

```
┌─────────────────────────────────────────┐
│ RequireKit (Optional Integration)       │
├─────────────────────────────────────────┤
│ Phase 1: Requirements Analysis          │
│   - EARS notation                       │
│   - BDD/Gherkin scenarios               │
│   - Epic/feature hierarchy              │
│   - Requirements traceability           │
└─────────────┬───────────────────────────┘
              │
              ↓ (optional link)
┌─────────────────────────────────────────┐
│ GuardKit Core Workflow                │
├─────────────────────────────────────────┤
│ Phase 1: Load Task Context (internal)   │
│   - File operations                     │
│   - State transitions                   │
│   - Load task markdown                  │
│                                         │
│ Phase 2: Implementation Planning        │
│ Phase 2.5: Architectural Review         │
│ Phase 2.7: Complexity Evaluation        │
│ Phase 2.8: Human Checkpoint             │
│ Phase 3: Implementation                 │
│ Phase 4: Testing                        │
│ Phase 4.5: Test Enforcement Loop        │
│ Phase 5: Code Review                    │
│ Phase 5.5: Plan Audit                   │
└─────────────────────────────────────────┘
```

**Pros:**
- Maintains backward compatibility
- Clear separation of concerns
- Phase numbers in existing files remain valid
- Shows how RequireKit integrates
- Users understand which phases are which product

**Cons:**
- Slightly more complex explanation needed
- "Phase 1" appears twice (different contexts)

### Recommendation: Option B

**Rationale:**
1. Backward compatibility with existing documentation
2. Clear product separation (GuardKit vs RequireKit)
3. Shows integration story naturally
4. Minimal documentation changes needed
5. Phase numbers in existing task files remain accurate

## Current Workflow (Post-TASK-022)

### Standard Mode

```bash
/task-work TASK-001
```

**Phases Executed:**
1. ~~Phase 1: Requirements Analysis~~ **[SKIPPED - RequireKit only]**
2. Phase 2: Implementation Planning
3. Phase 2.5A: Pattern Suggestion (if design-patterns MCP available)
4. Phase 2.5B: Architectural Review (SOLID/DRY/YAGNI scoring)
5. Phase 2.7: Complexity Evaluation (0-10 scale)
6. Phase 2.8: Human Checkpoint (if complexity ≥7 or manual review requested)
7. Phase 3: Implementation
8. Phase 4: Testing (compilation + coverage)
9. Phase 4.5: Test Enforcement Loop (auto-fix up to 3 attempts)
10. Phase 5: Code Review
11. Phase 5.5: Plan Audit (scope creep detection)

**Task State Transitions:**
```
backlog → in_progress (Phase 1)
in_progress → in_review (Phase 5 if tests pass)
in_progress → blocked (Phase 4.5 if tests fail after 3 attempts)
in_review → completed (after human approval)
```

### Design-First Mode

```bash
/task-work TASK-001 --design-only
# [Human reviews and approves plan]
/task-work TASK-001 --implement-only
```

**Design Phase (--design-only):**
1. ~~Phase 1: Requirements Analysis~~ **[SKIPPED]**
2. Phase 2: Implementation Planning
3. Phase 2.5A: Pattern Suggestion
4. Phase 2.5B: Architectural Review
5. Phase 2.7: Complexity Evaluation
6. Phase 2.8: Human Checkpoint → **STOP HERE**

**Implementation Phase (--implement-only):**
1. Phase 3: Implementation (uses saved plan)
2. Phase 4: Testing
3. Phase 4.5: Test Enforcement Loop
4. Phase 5: Code Review
5. Phase 5.5: Plan Audit

## Integration with RequireKit

### How It Works

Users can optionally install RequireKit for formal requirements:

```bash
# Install RequireKit
git clone https://github.com/requirekit/require-kit.git
cd require-kit
./installer/scripts/install.sh

# Use RequireKit for requirements
/req-create "User must be able to log in" type:ears
/bdd-generate REQ-001
/epic-create "User Management" export:jira

# Link requirements to GuardKit task
/task-create "Implement login" requirements:[REQ-001] epic:EPIC-001

# GuardKit workflow continues as normal
/task-work TASK-001  # Phases 2-5.5 only
```

### Data Flow

```
RequireKit Phase 1: Requirements Analysis
├─ EARS notation: REQ-001.md
├─ BDD scenarios: BDD-001.feature
├─ Epic hierarchy: EPIC-001/FEAT-001/TASK-001
└─ External tool IDs: Jira, Linear, etc.
         │
         ↓ (linked via task frontmatter)
         │
GuardKit Phase 2+: Implementation
├─ Reads requirements from linked REQ files
├─ Uses acceptance criteria from EARS
├─ Validates against BDD scenarios
├─ Updates epic progress
└─ Syncs to external tools
```

### Task Frontmatter Example

With RequireKit integration:
```yaml
---
id: TASK-001
title: Implement user login
status: in_progress
requirements: [REQ-001, REQ-002]  # Links to RequireKit
epic: EPIC-001                     # Links to RequireKit
bdd_scenarios: [BDD-001]          # Links to RequireKit
external_ids:
  jira: PROJ-123                   # From RequireKit epic
  linear: PROJECT-456              # From RequireKit epic
---
```

Without RequireKit (GuardKit only):
```yaml
---
id: TASK-001
title: Implement user login
status: in_progress
priority: high
tags: [auth, security]
---

## Acceptance Criteria
- [ ] User can log in with email/password
- [ ] Session tokens are secure
- [ ] Failed attempts are rate-limited
```

Both formats work fine in GuardKit. RequireKit fields are optional.

## Documentation Changes Needed

The following documentation audit tasks (already created) will fix the confusion:

### TASK-023: README.md and CLAUDE.md
- Remove "Phase 1: Requirements Analysis" from main docs
- Add clear "Need requirements management?" section
- Link to RequireKit appropriately
- Fix GitHub URLs

### TASK-024: Core User Guides
- Update GETTING-STARTED.md to show GuardKit-only workflow
- Remove BDD mode references from QUICK_REFERENCE.md
- Clarify guardkit-workflow.md phases

### TASK-025: Workflow and Quick-Reference Docs
- Update 14 workflow files to remove Phase 1 references
- Choose and apply phase numbering strategy (Option B recommended)
- Update workflow diagrams
- Fix quick-reference cards

## Key Messaging for Documentation

### What GuardKit IS

✅ Lightweight task workflow with quality gates
✅ Architectural review before implementation (Phase 2.5)
✅ Test enforcement after implementation (Phase 4.5)
✅ Complexity evaluation and design checkpoints
✅ Simple 3-command workflow (create → work → complete)
✅ Stack-specific templates and AI agents
✅ MCP integration (Context7, design-patterns, Figma, Zeplin)

### What GuardKit is NOT

❌ Requirements management system (that's RequireKit)
❌ EARS notation processor (that's RequireKit)
❌ BDD/Gherkin generator (that's RequireKit)
❌ Epic/feature hierarchy manager (that's RequireKit)
❌ PM tool synchronization (that's RequireKit)
❌ Portfolio management (that's Agentecflow full platform)

### How to Position RequireKit

Use this messaging pattern in docs:

```markdown
## Need Formal Requirements Management?

GuardKit uses task descriptions and acceptance criteria for lightweight workflows.

For formal requirements management, install [RequireKit](https://github.com/requirekit/require-kit):
- EARS notation requirements
- BDD/Gherkin scenario generation
- Epic/feature hierarchy
- Requirements traceability
- PM tool synchronization (Jira, Linear, Azure DevOps)

RequireKit integrates seamlessly with GuardKit - requirements link to tasks automatically.
```

## Agent Architecture (Post-TASK-022)

### Core Agents (Global)

All stacks use these agents:

| Phase | Agent | Purpose |
|-------|-------|---------|
| Phase 2 | (stack-specific) | Implementation planning |
| Phase 2.5 | architectural-reviewer | SOLID/DRY/YAGNI review |
| Phase 3 | (stack-specific) | Implementation |
| Phase 4 | (stack-specific) | Testing |
| Phase 5 | code-reviewer | Code quality review |

**Note**: No `requirements-analyst` - it was correctly removed.

### Stack-Specific Agents

Example: dotnet-microservice stack

| Phase | Agent | Purpose |
|-------|-------|---------|
| ~~Phase 1~~ | ~~requirements-analyst~~ | ~~[REMOVED]~~ |
| Phase 2 | dotnet-api-specialist | Plan FastEndpoints API |
| Phase 2.5 | architectural-reviewer | Review architecture |
| Phase 3 | dotnet-domain-specialist | Implement domain logic |
| Phase 4 | dotnet-testing-specialist | Write xUnit tests |
| Phase 5 | code-reviewer | Review code quality |

## Testing Scenarios

### Scenario 1: GuardKit Only (Current Implementation)

```bash
# Initialize project
guardkit-init dotnet-microservice

# Create task
/task-create "Add health check endpoint" priority:high

# Work on task (Phases 2-5.5)
/task-work TASK-001

# Expected: No Phase 1, starts at Phase 2 Planning
```

**Result**: ✅ Works correctly (post-TASK-022)

### Scenario 2: GuardKit + RequireKit Integration

```bash
# Install both systems
./guardkit/installer/scripts/install.sh
./require-kit/installer/scripts/install.sh

# Create requirement in RequireKit
/req-create "System shall respond to health checks within 100ms" type:ears

# Create task linked to requirement
/task-create "Add health check endpoint" requirements:[REQ-001]

# Work on task (GuardKit Phases 2-5.5)
/task-work TASK-001

# Expected: Acceptance criteria pulled from REQ-001
```

**Result**: ✅ Will work when RequireKit is released

### Scenario 3: Verify No Requirements-Analyst Errors

```bash
# Work on any task
/task-work TASK-001

# Expected: No "requirements-analyst not found" errors
```

**Result**: ✅ Fixed by TASK-022

## Conclusion

### Summary

1. **Two Phase 1 concepts existed** - one for requirements (RequireKit), one for task loading (GuardKit)
2. **TASK-022 correctly removed** the requirements-analyst invocation
3. **Current implementation is right** - no code changes needed
4. **Documentation needs fixing** - complete TASK-023, 024, 025
5. **RequireKit is the answer** for users needing formal requirements

### No Further Agent Changes Needed

The `requirements-analyst` agent should **NOT** be brought back to GuardKit. Users needing formal requirements should use RequireKit.

### Path Forward

1. ✅ Complete TASK-023 (README.md, CLAUDE.md)
2. ✅ Complete TASK-024 (Core user guides)
3. ✅ Complete TASK-025 (Workflows and quick-reference)
4. ✅ Apply Option B phase numbering (keep current, clarify separation)
5. ✅ Add clear RequireKit integration messaging throughout docs

### Success Criteria

After documentation audit:
- ✅ No confusion about "Phase 1: Requirements Analysis"
- ✅ Clear separation between GuardKit and RequireKit features
- ✅ Users understand when to use each tool
- ✅ Integration story is clear and compelling
- ✅ All command examples work with GuardKit-only installation

## References

- **TASK-003**: Initial removal of requirements agents (guardkit/require-kit split)
- **TASK-022**: Fix broken task-manager references (completed 2025-11-02)
- **TASK-023**: Audit README.md and CLAUDE.md (backlog)
- **TASK-024**: Audit core user guides (backlog)
- **TASK-025**: Audit workflow documentation (backlog)

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2025-11-02 | Remove requirements-analyst from GuardKit | Contradicts lightweight positioning |
| 2025-11-02 | Skip Phase 1 in task-work workflow | Task descriptions + acceptance criteria sufficient |
| 2025-11-03 | Do NOT bring back requirements-analyst | Would undo correct architectural decision |
| 2025-11-03 | Use Option B for phase numbering | Backward compatibility + clear separation |
| 2025-11-03 | Complete documentation audit (TASK-023, 024, 025) | Fix confusion, clarify integration |

---

**Document Owner**: GuardKit Documentation Team
**Last Updated**: 2025-11-03
**Status**: Final Decision - No Code Changes Needed
