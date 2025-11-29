---
id: TASK-D3A1
title: "Review template initialization architecture and agent sourcing strategy"
status: backlog
created: 2025-11-26T09:30:00Z
updated: 2025-11-26T09:30:00Z
priority: high
tags: [architecture-review, template-init, agent-sourcing, design-decision]
complexity: 6
estimated_hours: 2
task_type: review
decision_required: true
related_tasks: [TASK-C2F8, TASK-BAA5]
---

# Task: Review Template Initialization Architecture and Agent Sourcing Strategy

## Problem Statement

During TASK-C2F8 implementation, a fundamental architectural question arose: **Should cross-stack agents be duplicated into every template, or sourced from a single global location?**

**Update (2025-11-27)**: taskwright-python template has been removed (TASK-G6D4) as Taskwright's `.claude/` directory is git-managed and should not use template initialization. This review task remains relevant for understanding the architectural decision.

**Original confusion**:
1. TASK-C2F8 "fixed" the issue by copying 5 cross-stack agents into `taskwright-python` template
2. This created duplication - same agents existed in:
   - `installer/global/agents/` (source of truth)
   - `installer/global/templates/taskwright-python/agents/` (duplicate)
3. This pattern would have needed to repeat for EVERY template (react-typescript, fastapi-python, etc.)

**Fundamental question**: Is this duplication the right design?

## Context

### Scenario A: Taskwright Repo Itself
- `.claude/` directory is checked into git
- Users clone repo and get pre-configured agents
- **Resolution (TASK-G6D4)**: `taskwright init` should NOT be run on Taskwright repo
- **TASK-BAA5 Issue**: Running init on Taskwright caused agent deletion (the problem that led to removal)

### Scenario B: User's Python CLI Project
- User has their own Python CLI project (NOT Taskwright)
- **Resolution (TASK-G6D4)**: User should use `fastapi-python` template or `/template-create` for custom templates
- **Rationale**: taskwright-python was specific to Taskwright's architecture, not general Python CLI projects
- For Python CLI projects, better options:
  - Use `fastapi-python` template as foundation
  - Create custom template via `/template-create` based on their architecture

### Historical Template Structure (taskwright-python - Now Removed)

**Before TASK-C2F8**:
```
installer/global/templates/taskwright-python/agents/
├── python-architecture-specialist.md
├── python-cli-specialist.md
└── python-testing-specialist.md
```

**After TASK-C2F8** (temporary fix, later removed):
```
installer/global/templates/taskwright-python/agents/
├── architectural-reviewer.md          ← DUPLICATED from global
├── code-reviewer.md                   ← DUPLICATED from global
├── python-architecture-specialist.md
├── python-cli-specialist.md
├── python-testing-specialist.md
├── task-manager.md                    ← DUPLICATED from global
├── test-orchestrator.md               ← DUPLICATED from global
└── test-verifier.md                   ← DUPLICATED from global
```

**After TASK-G6D4** (final resolution):
- Template removed entirely
- Taskwright's `.claude/` managed via git

## Review Objectives

### 1. Architectural Decision: Agent Sourcing Strategy

**Option A: Duplication (Current TASK-C2F8 Fix)**
- Every template includes copies of cross-stack agents
- Pros: Self-contained templates, no dependency on global directory
- Cons: Duplication, maintenance burden, version drift risk

**Option B: Global Sourcing (Proposed Alternative)**
- Templates only include template-specific agents
- Init script copies cross-stack agents from `installer/global/agents/`
- Pros: Single source of truth, no duplication, easier maintenance
- Cons: Init script needs to know which agents are cross-stack vs template-specific

**Option C: Hybrid**
- Templates reference cross-stack agents via manifest (don't copy)
- Init script assembles agents from multiple sources
- Pros: Best of both worlds
- Cons: More complex init logic

### 2. Template Application Scope

**Question 1**: Should Taskwright repo's `.claude/` directory even be modified by `taskwright init`?
- **Current**: `.claude/` is checked into git
- **Implication**: Running `taskwright init` would overwrite checked-in configuration
- **Decision needed**: Is this intended behavior or a misuse case?

**Question 2 - RESOLVED**: taskwright-python template was intended for Taskwright development, but this was the wrong approach:
- **Decision (TASK-G6D4)**: Template removed
- **Rationale**: Taskwright's `.claude/` is git-managed, not template-initialized
- **For users**: Use `fastapi-python` or `/template-create` instead

### 3. Init Script Behavior

Current `init-project.sh` logic (from TASK-C2F8):
1. Copies all agents from `template/agents/` directory
2. Checks `protected-agents.json` to avoid overwriting certain agents
3. Merges CLAUDE.md

**Question**: Should it instead:
1. Copy template-specific agents from `template/agents/`
2. Copy cross-stack agents from `installer/global/agents/`
3. Use manifest to declare which agents are needed (not copy them into template)

## Analysis Required

### A. Agent Categorization

**Cross-Stack Agents** (used by all templates):
- architectural-reviewer.md (Phase 2.5A)
- code-reviewer.md (Phase 5)
- task-manager.md (workflow orchestration)
- test-orchestrator.md (Phase 4)
- test-verifier.md (test verification)
- build-validator.md
- debugging-specialist.md
- git-workflow-manager.md
- pattern-advisor.md
- security-specialist.md
- devops-specialist.md
- database-specialist.md
- (and more...)

**Stack-Specific Agents** (vary by template):
- Python: python-api-specialist, python-testing-specialist, python-architecture-specialist
- React: react-state-specialist
- .NET: dotnet-domain-specialist
- (etc.)

**Question**: How should init script know which is which?

### B. Template Manifest Design

Should templates declare dependencies instead of including files?

**Example manifest.json**:
```json
{
  "template": "taskwright-python",
  "agents": {
    "template_specific": [
      "python-testing-specialist.md",
      "python-cli-specialist.md",
      "python-architecture-specialist.md"
    ],
    "cross_stack_required": [
      "architectural-reviewer.md",
      "code-reviewer.md",
      "task-manager.md",
      "test-orchestrator.md",
      "test-verifier.md"
    ]
  }
}
```

Init script would:
1. Copy `template_specific` agents from template
2. Copy `cross_stack_required` agents from global

### C. Use Case Validation

**Use Case 1: Fresh Python CLI Project**
```bash
mkdir my-python-cli
cd my-python-cli
taskwright init taskwright-python
```

**Expected result**:
- Get 3 Python-specific agents
- Get ~15 cross-stack agents
- Get CLAUDE.md with Python CLI context
- Total: ~18 agents

**Use Case 2: Existing Project with Custom Agents**
```bash
cd existing-project  # Already has .claude/ with customizations
taskwright init taskwright-python
```

**Expected result**:
- Add 3 Python-specific agents (if not present)
- Preserve existing cross-stack agents (don't overwrite customizations)
- Merge CLAUDE.md (preserve project context, add template sections)

**Use Case 3: Taskwright Development (This Repo)**
```bash
cd ~/Projects/taskwright  # .claude/ already in git
taskwright init taskwright-python  # Should this even be run?
```

**Expected result**: ???
- Is this a valid use case?
- Or should `.claude/` just be managed via git?

## Decision Framework

After analysis, recommend one of the following:

### Decision 1: Duplication Model (Keep TASK-C2F8 Fix)
- Accept that every template includes copies of cross-stack agents
- Document maintenance burden (must update 6 templates when cross-stack agent changes)
- Update all other templates (react-typescript, fastapi-python, etc.) to also include cross-stack agents

### Decision 2: Global Sourcing Model (Revert TASK-C2F8, Redesign Init)
- Remove duplicated agents from taskwright-python template
- Modify `init-project.sh` to copy cross-stack agents from `installer/global/agents/`
- Add manifest field to declare which cross-stack agents are required

### Decision 3: Manifest-Based Assembly (New Design)
- Templates declare agent dependencies in manifest
- Init script assembles agents from multiple sources
- No duplication, clear dependency tracking

### Decision 4: Deprecate Template Init on Taskwright Repo
- Document that `taskwright init` should NOT be run on Taskwright repo itself
- `.claude/` directory is managed via git for Taskwright development
- Templates are only for USER projects

## Acceptance Criteria

- [ ] Architectural decision made on agent sourcing strategy
- [ ] Use case validation completed
- [ ] Init script behavior documented
- [ ] If duplication model: Update all templates
- [ ] If global sourcing model: Redesign init script
- [ ] If manifest model: Implement manifest-based assembly
- [ ] Decision documented in ADR
- [ ] TASK-C2F8 fix validated or reverted based on decision

## Risk Assessment

| Risk | Probability | Impact | Severity |
|------|------------|--------|----------|
| Choosing duplication: 6 templates to maintain | High | High | 🔴 High |
| Choosing global sourcing: Complex init logic | Medium | Medium | 🟡 Medium |
| Choosing manifest: Significant redesign | Low | High | 🟡 Medium |
| No decision: Technical debt accumulates | High | High | 🔴 High |

## References

- **TASK-C2F8**: Fix taskwright-python template (implemented duplication)
- **TASK-BAA5**: Review of template application (identified deletion issue)
- **Current init script**: installer/scripts/init-project.sh
- **Template directory**: installer/global/templates/
- **Global agents**: installer/global/agents/

## Questions for Review

1. **Primary Question**: Should cross-stack agents be duplicated into every template, or sourced from global?
2. **Scope Question**: Is `taskwright init` intended for Taskwright repo itself, or only for user projects?
3. **Maintenance Question**: Can we maintain 6 templates with duplicated cross-stack agents?
4. **Design Question**: Should templates be self-contained or dependency-based?

---

## User's Analysis and Recommended Path Forward

**User's Assessment** (2025-11-26):

### Root Cause Identified

**User's mistake**: Running `taskwright init taskwright-python` on the Taskwright repo itself was the wrong action. The Taskwright repo's `.claude/` directory is managed via git and should NOT be modified by template initialization.

**Key insight**: This revealed unnecessary complexity in the current approach.

### Recommended Actions

**1. Revert Uncommitted Changes on Main**

Keep only:
- ✅ This review task (TASK-D3A1)
- ✅ Previous review task (TASK-BAA5)
- ✅ Review reports (useful history)

Revert:
- ❌ TASK-C2F8 implementation (agent duplication fix)
- ❌ Modified protected-agents.json
- ❌ Copied cross-stack agents to template
- ❌ Modified README.md
- ❌ All other uncommitted changes

**2. Restore Taskwright Repo's `.claude/` Directory**

Use git to restore the original `.claude/` directory to its checked-in state.

**3. Analyze Current `.claude/` Directory**

Once restored, analyze what's actually in `.claude/` and determine:
- Are agents up to date with latest standards?
- Do agents have discovery metadata (frontmatter with stack/phase/capabilities/keywords)?
- Do agents have boundary sections (ALWAYS/NEVER/ASK per GitHub best practices)?
- Are there Taskwright-specific agents that need enhancement?
- Does CLAUDE.md need updates for agent discovery?

**4. Consider Removing taskwright-python Template**

**Rationale**:
- Taskwright repo manages `.claude/` via git (not template init)
- The template was created for Taskwright development, not user projects
- User projects needing Python CLI patterns should use `fastapi-python` template or create custom templates via `/template-create`
- Removing this template eliminates confusion and maintenance burden

**Question for review**: Should `taskwright-python` template be:
- A) Removed entirely (Taskwright uses git-managed `.claude/`)
- B) Repurposed for user Python CLI projects (not Taskwright itself)
- C) Kept as reference implementation of Taskwright's architecture

**5. Update Taskwright Agents to Current Standards**

If analysis reveals gaps, create tasks to:
- Add discovery metadata to Taskwright-specific agents
- Add boundary sections to agents missing them
- Update CLAUDE.md with agent discovery guidance
- Ensure all agents follow GitHub best practices from 2,500+ repo analysis

### Expected Outcome

**Clean state**:
- Taskwright repo's `.claude/` managed via git (no template init)
- User projects use appropriate templates (fastapi-python, react-typescript, etc.)
- Taskwright agents enhanced to current standards (discovery metadata, boundaries)
- Reduced complexity (no taskwright-python template maintenance)
- Clear documentation on when to use template init vs git-managed configuration

### Learning

**Positive outcome from mistake**:
- Discovered that taskwright-python template adds unnecessary complexity
- Identified that Taskwright's `.claude/` should be git-managed, not template-initialized
- Opportunity to enhance Taskwright's own agents to current standards
- Clearer separation of concerns (Taskwright development vs user project templates)

---

**Next Steps**:
1. Run `/task-review TASK-D3A1 --mode=architectural --depth=comprehensive` to validate this approach
2. If approved, execute revert and analysis plan
3. Create follow-up tasks for agent enhancement if needed
