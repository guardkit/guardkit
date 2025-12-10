# TASK-018: Fix clean-architecture-specialist Agent Documentation Mismatch

**Priority**: High
**Type**: Bug Fix / Investigation
**Epic**: EPIC-001 (AI Template Creation)
**Created**: 2025-01-07
**Closed**: 2025-01-08
**Status**: Closed (Won't Fix)
**Closure Reason**: Template no longer exists; root cause addressed by TASK-042

## Issue Description

During Section 3 analysis of the `ardalis-clean-architecture` template (generated via `/template-create`), we discovered a **critical documentation accuracy issue**:

### The Problem

**CLAUDE.md documents an agent that does not exist:**
- **File**: `installer/core/templates/ardalis-clean-architecture/CLAUDE.md`
- **Lines**: 811-823
- **Agent Name**: `clean-architecture-specialist`

### Evidence

CLAUDE.md references **5 agents** in the "Agent Usage Guidelines" section, but only **4 agents** actually exist in the `agents/` directory:

**Agents that exist:**
- ✅ `cqrs-specialist.md`
- ✅ `ddd-specialist.md`
- ✅ `fastendpoints-specialist.md`
- ✅ `specification-specialist.md`

**Agent documented but missing:**
- ❌ `clean-architecture-specialist.md` (documented in CLAUDE.md lines 811-823 but DOES NOT EXIST)

### Impact

**High Impact:**
1. **User Confusion**: Users reading CLAUDE.md will attempt to invoke `/task-work` expecting the `clean-architecture-specialist` to handle architectural tasks
2. **Workflow Disruption**: The agent doesn't exist, causing task failures
3. **Trust Damage**: Damages confidence in AI-generated template quality (98% confidence score, yet has critical error)
4. **False Advertising**: Template claims to provide functionality it doesn't deliver

## Investigation Questions

### 1. Root Cause Analysis

**Why did the AI document an agent that wasn't created?**

Hypotheses:
- **H1**: Agent was supposed to be created but creation phase failed silently
- **H2**: AI hallucinated the agent based on architectural context and Clean Architecture pattern detection
- **H3**: Mismatch between documentation generation phase (Phase 5) and agent generation phase (Phase 7)
- **H4**: Template creation command has 8 phases - error occurred between phases

**Investigation Tasks:**
- [ ] Review `/template-create` command execution logs (if available)
- [ ] Check if other templates have similar documentation/agent mismatches
- [ ] Review Phase 5 (CLAUDE.md generation) and Phase 7 (agent generation) logic
- [ ] Determine if validation exists to catch doc/agent mismatches

### 2. Scope Assessment

**Is this a one-off issue or systemic?**

**Investigation Tasks:**
- [ ] Audit ALL global templates for similar issues:
  - [ ] `default` template
  - [ ] `react` template
  - [ ] `python` template
  - [ ] `maui-appshell` template
  - [ ] `maui-navigationpage` template
  - [ ] `dotnet-fastendpoints` template
  - [ ] `dotnet-aspnetcontroller` template
  - [ ] `dotnet-minimalapi` template
  - [ ] `typescript-api` template
  - [ ] `fullstack` template
- [ ] Check if `/template-create` has validation to prevent this
- [ ] Review template-create agent's instructions for agent creation logic

### 3. Solution Options

**What's the best fix?**

#### Option A: Remove Documentation (Quick Fix)
**Action**: Delete lines 811-823 from CLAUDE.md

**Pros:**
- Quick fix (1 file edit)
- No code needed
- Aligns documentation with reality

**Cons:**
- Users lose guidance on when to use architectural review
- Doesn't explain why global `architectural-reviewer` should be used instead

**Effort**: Low (5 minutes)

#### Option B: Create the Missing Agent
**Action**: Create `clean-architecture-specialist.md` agent

**Pros:**
- Fulfills documented functionality
- No documentation changes needed
- Provides specialized architectural guidance

**Cons:**
- More work (need to write comprehensive agent)
- Need to define scope vs existing `architectural-reviewer` global agent
- May create confusion (when to use global vs template-specific agent?)
- Requires deep understanding of Ardalis patterns

**Effort**: High (2-4 hours)

**Questions:**
- What's the difference between global `architectural-reviewer` and template-specific `clean-architecture-specialist`?
- Is there value in having BOTH agents?

#### Option C: Merge with Global Agent (Recommended)
**Action**: Update documentation to reference global `architectural-reviewer` agent

**Pros:**
- Leverages existing global agent
- Reduces agent proliferation
- Clearer guidance (one architectural agent)
- Documents relationship between global and template agents

**Cons:**
- Need to verify global agent handles Clean Architecture patterns
- Requires documentation updates

**Effort**: Medium (30 minutes)

**Implementation:**
```markdown
#### When to Use Architectural Review

Use the global **architectural-reviewer** agent for:
- Validating Clean Architecture layer boundaries
- Ensuring dependency flow (Web → UseCases → Core ← Infrastructure)
- Reviewing SOLID principles compliance
- Architectural refactoring tasks

Example:
/task-create "Refactor UserManagement module to Clean Architecture"
/task-work TASK-XXX
# Global agent: architectural-reviewer validates proper layer separation
```

## Acceptance Criteria

- [ ] **AC1**: Root cause identified and documented in this task
- [ ] **AC2**: Decision made on solution (Option A, B, or C)
- [ ] **AC3**: Fix implemented and verified
- [ ] **AC4**: Template updated in `installer/core/templates/ardalis-clean-architecture/`
- [ ] **AC5**: Verification test run: `taskwright init ardalis-clean-architecture` in test directory
- [ ] **AC6**: Updated CLAUDE.md reviewed for accuracy
- [ ] **AC7**: If systemic, validation added to `/template-create` command to prevent recurrence
- [ ] **AC8**: Issue documented in `docs/testing/template-analysis-task.md` Section 3.4 findings

## Files to Modify

```
installer/core/templates/ardalis-clean-architecture/
├── CLAUDE.md (lines 811-823) ← Update or remove agent documentation
├── agents/ ← Create agent (if Option B) or verify global agent works
└── README.md ← Update if agent changes affect README
```

## Context & Background

### Discovery Context
- **Analysis Phase**: Section 3 (Documentation Analysis) of template-analysis-task.md
- **Discovery Date**: 2025-01-07
- **Discovered By**: Template quality audit during EPIC-001 testing
- **Template Analyzed**: `ardalis-clean-architecture` (generated from CleanArchitecture-ardalis repo)

### Interesting Observations

**Only CLAUDE.md has the error:**
- ✅ `manifest.json` correctly lists 4 agents
- ✅ `settings.json` doesn't reference this agent
- ✅ `README.md` doesn't reference this agent
- ❌ `CLAUDE.md` documents non-existent agent

**Conclusion**: Error occurred during CLAUDE.md generation phase (Phase 5), NOT during agent creation phase (Phase 7). This suggests phases are not cross-validated.

### Related Documentation
- **Template Analysis**: `docs/testing/template-analysis-task.md` (Section 3.4)
- **Template Location**: `installer/core/templates/ardalis-clean-architecture/`
- **Source Repository**: `docs/testing/test-repos/CleanArchitecture-ardalis`
- **AI Confidence**: 98/100 (ironically high despite this critical error)

## Testing Plan

### Verification Steps

1. **Before Fix**:
   ```bash
   cd /tmp/test-fix
   taskwright init ardalis-clean-architecture
   grep -n "clean-architecture-specialist" .claude/CLAUDE.md
   ls .claude/agents/ | grep clean-architecture
   ```

2. **After Fix**:
   ```bash
   cd /tmp/test-fix-after
   taskwright init ardalis-clean-architecture
   # Verify fix applied
   grep -n "clean-architecture-specialist" .claude/CLAUDE.md || echo "Fixed!"
   # Verify agents documented match agents installed
   ```

3. **Regression Test** (if systemic):
   - Re-run template creation: `/template-create` on CleanArchitecture-ardalis
   - Verify validation catches mismatch

## Recommended Priority Justification

**Priority: High**

**Rationale:**
1. **User-Facing Bug**: Directly impacts developer experience
2. **Documentation Quality**: Damages trust in AI-generated templates
3. **Easy to Fix**: Low effort for high impact (especially Option C)
4. **Systemic Risk**: May indicate broader quality issue in template generation
5. **EPIC-001 Success Metric**: Template quality is core to EPIC-001 value proposition

**Not Critical because:**
- Doesn't break template functionality (other 4 agents work fine)
- Global `architectural-reviewer` agent provides similar functionality
- Workaround exists (use global agent instead)

## Next Steps

1. **Investigate**: Review `/template-create` agent logic for Phase 5 and Phase 7
2. **Decide**: Choose solution option (A, B, or C)
3. **Implement**: Apply fix to `ardalis-clean-architecture` template
4. **Test**: Verify fix works via `taskwright init`
5. **Audit**: Check other templates for similar issues
6. **Prevent**: Add validation if systemic

## Related Issues

- None yet (this is the first documentation accuracy issue discovered in template analysis)

## Notes

- This is the **first substantive quality issue** found in Sections 1-3 analysis
- Sections 1 (Manifest) and 2 (Settings) had 0 critical issues
- Overall template quality is still excellent (9.7/10 average across Sections 1-3)
- Fix should be straightforward regardless of solution chosen

---

**Created during**: Template Analysis Task (template-analysis-task.md)
**Section**: 3.4 Agent Usage Guidelines
**Overall Template Score**: 9.4/10 (Section 3), 9.7/10 (Sections 1-3 combined)

---

## CLOSURE NOTICE

**Closed Date**: 2025-01-08
**Status**: Won't Fix
**Resolution**: Template Obsolete / Root Cause Addressed

### Reason for Closure

This task is being closed without implementation for the following reasons:

#### 1. Template Does Not Exist
The `ardalis-clean-architecture` template referenced in this task does not exist in the repository:
```bash
$ ls installer/core/templates/ | grep ardalis
# No results
```

**Context**: This template was a **test artifact** created during TASK-020 (template generation quality analysis) and was never part of the official template set.

#### 2. Not in Official Template Strategy
The current template strategy (per [template-strategy-decision.md](../../docs/research/template-strategy-decision.md)) focuses on 4 high-quality reference templates:
- TASK-057: React + TypeScript
- TASK-058: FastAPI
- TASK-059: Next.js
- TASK-062: React + FastAPI Monorepo

The `ardalis-clean-architecture` template was never intended for production distribution.

#### 3. Root Cause Addressed
**TASK-042 (Enhanced AI Prompting)** - Completed 2025-01-07 - directly addresses the root cause of this bug:

**What TASK-042 Added**:
- Validation checklist in CLAUDE.md generation (lines 121-154 of TASK-042)
- Agent validation section ensuring documented agents exist
- Layer symmetry checks preventing documentation/implementation mismatches

**Preventive Measure**:
```markdown
## Template Validation Checklist

**Layer Symmetry**:
- [ ] All UseCases commands have Web endpoints
- [ ] All Web endpoints have UseCases handlers
- [ ] Repository interfaces exist for all operations

**Agent Validation**:
- [ ] All documented agents exist in agents/ directory
- [ ] No broken agent references in CLAUDE.md
```

This validation framework **prevents** the exact type of documentation mismatch identified in TASK-018.

#### 4. Test Templates vs Production Templates
TASK-041 and TASK-042 improved template generation quality through:
- Stratified sampling (TASK-041): Better pattern detection during analysis
- Enhanced AI prompting (TASK-042): Explicit completeness guidance + validation checklists

These improvements ensure future templates (including test templates) won't have this issue.

### Learning Captured

**Bug Pattern**: CLAUDE.md documented `clean-architecture-specialist` agent that didn't exist in `agents/` directory.

**Root Cause**: Phase 5 (CLAUDE.md generation) and Phase 7 (agent generation) were not cross-validated.

**Solution Implemented**: TASK-042 added validation checklist to catch documentation/agent mismatches during generation.

### Related Tasks

- ✅ **TASK-041**: Stratified Sampling (Completed 2025-01-07) - Improves pattern detection
- ✅ **TASK-042**: Enhanced AI Prompting (Completed 2025-01-07) - Adds validation checklists
- **TASK-057-062**: Reference template creation - Uses improved generation with TASK-041/042 enhancements

### No Action Required

No implementation or fix is needed because:
1. Template doesn't exist (no artifact to fix)
2. Root cause addressed by TASK-042 (preventive measure in place)
3. Future templates will have validation checklist preventing this issue

---

**Closed By**: Claude Code
**Approved By**: User
**Tags**: `closed`, `wont-fix`, `test-artifact`, `root-cause-addressed`, `obsolete`
