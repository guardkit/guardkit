---
id: TASK-BAA5
title: "Review taskwright-python template initialization changes"
status: backlog
created: 2025-11-26T08:03:00Z
updated: 2025-11-26T08:03:00Z
priority: high
tags: [template-init, regression-check, quality-assurance, cleanup]
complexity: 4
estimated_hours: 2
task_type: review
decision_required: true
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Review taskwright-python Template Initialization Changes

## Problem Statement

After running `taskwright init taskwright-python` on the Taskwright repository, we need to review the changes to ensure:
1. No regressions were introduced
2. The latest template with discovery frontmatter metadata was applied correctly
3. Unstaged changes are cleaned up appropriately

## Context

**Command Executed**: `taskwright init taskwright-python`

**Changes Detected**: ~1,020 files modified/deleted/added

**Key Changes Observed**:
- `.claude/CLAUDE.md` modified
- Multiple `.claude/agents/*.md` files modified/deleted
- Multiple `.claude/commands/*.md` files modified/deleted
- Backup files deleted
- Quick reference files deleted

**Template Applied**: taskwright-python (with discovery metadata frontmatter)

## Review Objectives

### 1. Regression Detection
- [ ] Verify no critical functionality was removed
- [ ] Check that existing agents still have required capabilities
- [ ] Ensure commands are still executable and functional
- [ ] Validate that workflow phases are intact

### 2. Template Quality Assessment
- [ ] Confirm discovery metadata (stack, phase, capabilities, keywords) present in agents
- [ ] Verify boundary sections (ALWAYS/NEVER/ASK) are properly formatted
- [ ] Check that agent frontmatter follows the correct format
- [ ] Validate that commands follow taskwright-python template structure

### 3. Change Classification

**Expected Changes** (from taskwright-python template):
- Agent frontmatter with discovery metadata
- Boundary sections in agents
- Updated command specifications
- Cleanup of backup files

**Unexpected Changes** (potential regressions):
- Deletion of critical agents (e.g., software-architect, qa-tester)
- Removal of essential commands
- Loss of custom configurations

### 4. Cleanup Requirements
- [ ] Identify which deletions are intentional (backups, deprecated files)
- [ ] Identify which deletions need to be reverted (critical functionality)
- [ ] Stage appropriate changes
- [ ] Revert inappropriate deletions

## Analysis Approach

### Phase 1: File Classification (15 min)
```bash
# Categorize changes by type
git status --porcelain | grep "^M" | wc -l  # Modified
git status --porcelain | grep "^D" | wc -l  # Deleted
git status --porcelain | grep "^A" | wc -l  # Added
git status --porcelain | grep "^T" | wc -l  # Type changed

# Focus areas
git status --porcelain | grep ".claude/agents/"
git status --porcelain | grep ".claude/commands/"
git status --porcelain | grep "CLAUDE.md"
```

### Phase 2: Critical File Review (30 min)
1. **Deleted Agents**: Review each deleted agent
   - software-architect.md (CRITICAL for design phase)
   - qa-tester.md (CRITICAL for testing)
   - Should these be restored?

2. **Modified Agents**: Verify improvements
   - code-reviewer.md
   - task-manager.md
   - test-orchestrator.md
   - test-verifier.md

3. **Deleted Commands**: Assess impact
   - execute-tests.md
   - formalize-ears.md
   - gather-requirements.md
   - generate-bdd.md
   - task-work-specification.md

### Phase 3: Discovery Metadata Validation (20 min)
Check modified agents for proper frontmatter:
```yaml
---
stack: [python, cli]
phase: implementation
capabilities: [task-management, workflow-orchestration]
keywords: [python, taskwright, orchestrator]
---
```

### Phase 4: Boundary Sections Validation (15 min)
Verify agents have proper boundary sections:
```markdown
## Boundaries

### ALWAYS
- ✅ [action] ([rationale])

### NEVER
- ❌ [action] ([rationale])

### ASK
- ⚠️ [scenario] ([rationale])
```

### Phase 5: Diff Analysis (20 min)
```bash
# Review specific critical changes
git diff .claude/CLAUDE.md
git diff .claude/agents/code-reviewer.md
git diff .claude/agents/task-manager.md
git diff .claude/commands/task-work.md
```

### Phase 6: Decision & Cleanup (20 min)
Based on findings, decide:
1. What to keep (template improvements)
2. What to revert (critical functionality)
3. What to stage and commit
4. What cleanup commands to run

## Acceptance Criteria

- [ ] All 1,020 changes reviewed and categorized
- [ ] Critical agents identified (keep vs revert decision)
- [ ] Discovery metadata validated in modified agents
- [ ] Boundary sections validated in modified agents
- [ ] Regressions identified (if any)
- [ ] Cleanup plan documented
- [ ] Git staging strategy defined
- [ ] Recommended actions documented

## Potential Issues to Watch For

### High Risk Deletions
- `software-architect.md` - Used in architectural review (Phase 2.5A)
- `qa-tester.md` - Used in testing workflows
- Require-kit commands (formalize-ears, gather-requirements, generate-bdd)

### Configuration Changes
- `.claude/CLAUDE.md` - Core instructions file
- Command specifications that might break existing workflows

### Template Conflicts
- Taskwright repo is not a typical taskwright-python project
- Template might have removed Taskwright-specific customizations
- May need selective restoration

## Decision Framework

After review, choose one of:

1. **Accept All Changes**
   - Stage and commit all 1,020 changes
   - Template applied cleanly, no regressions

2. **Selective Acceptance**
   - Keep template improvements (metadata, boundaries)
   - Revert critical deletions (agents, commands)
   - Stage only safe changes

3. **Reject Template Application**
   - Revert all changes (`git reset --hard`)
   - Template not suitable for Taskwright repo
   - Need custom template or manual updates

4. **Hybrid Approach**
   - Extract good patterns from template
   - Manually apply to existing structure
   - Avoid wholesale replacement

## Estimated Effort

**Total**: 2 hours

- Phase 1 (Classification): 15 min
- Phase 2 (Critical Review): 30 min
- Phase 3 (Metadata Validation): 20 min
- Phase 4 (Boundary Validation): 15 min
- Phase 5 (Diff Analysis): 20 min
- Phase 6 (Decision & Cleanup): 20 min

## Output Deliverables

1. **Review Report**: Classification of all changes
2. **Regression Assessment**: List of any functionality lost
3. **Quality Assessment**: Template application quality
4. **Cleanup Commands**: Git commands to execute
5. **Decision Record**: What to keep/revert and why

## Next Steps After Review

Based on decision:

**If Accept/Selective**:
```bash
# Stage appropriate changes
git add [files-to-keep]

# Commit with clear message
git commit -m "feat: Apply taskwright-python template with discovery metadata

Applied template improvements:
- Discovery metadata in agents (stack, phase, capabilities, keywords)
- Boundary sections (ALWAYS/NEVER/ASK)
- Updated command specifications

Reverted critical functionality:
- [list any reverted files]

Template application reviewed in TASK-BAA5"
```

**If Reject**:
```bash
# Revert all changes
git reset --hard HEAD

# Consider manual updates instead
```

## References

- **Template**: installer/global/templates/taskwright-python/
- **Tag**: v0.96 (pre-template-init baseline)
- **Agent Discovery**: docs/guides/agent-discovery-guide.md
- **Boundary Sections**: CLAUDE.md - Agent Enhancement with Boundary Sections
