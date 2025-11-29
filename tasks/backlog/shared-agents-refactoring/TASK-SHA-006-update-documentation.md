---
id: TASK-SHA-006
title: Update documentation in all three repositories
status: backlog
created: 2025-11-28T21:00:00Z
updated: 2025-11-28T21:00:00Z
priority: medium
tags: [shared-agents, documentation, lean]
complexity: 2
estimated_effort: 1h
depends_on: [TASK-SHA-005]
blocks: []
parent_task: TASK-ARCH-DC05
task_type: implementation
---

# Task: Update Documentation

## Context

Update documentation in all three repos (shared-agents, TaskWright, RequireKit) to explain the new shared-agents architecture. Keep it brief and user-focused.

## Acceptance Criteria

- [ ] shared-agents README explains purpose and usage
- [ ] TaskWright CLAUDE.md mentions shared-agents
- [ ] RequireKit CLAUDE.md mentions shared-agents (if applicable)
- [ ] CHANGELOG updated in all repos
- [ ] Users understand what changed and why

## Implementation

### 1. shared-agents README (Already done in TASK-SHA-002)

Verify README covers:
- What shared-agents is
- How it's used (automatic installation)
- How to update (version pinning file)

### 2. Update TaskWright CLAUDE.md

Add section:

```markdown
## Shared Agents

Universal agents (code-reviewer, test-orchestrator, etc.) are maintained in the [shared-agents](https://github.com/taskwright-dev/shared-agents) repository and shared with RequireKit.

**For users**: No action required. Agents are automatically downloaded during installation.

**For maintainers**:
- Version pinning: `installer/shared-agents-version.txt`
- Update: Change version, re-run installer
- Agents installed to: `.claude/agents/universal/`
```

### 3. Update RequireKit CLAUDE.md (if applicable)

Same as TaskWright, adjusted for RequireKit context.

### 4. Update CHANGELOG in shared-agents

```markdown
## [1.0.0] - 2025-11-28

### Added
- Initial release of shared agents
- Universal agents: code-reviewer, test-orchestrator, [others from verified list]
- Manifest.json for agent listing
- Basic README and documentation

[1.0.0]: https://github.com/taskwright-dev/shared-agents/releases/tag/v1.0.0
```

### 5. Update CHANGELOG in TaskWright

```markdown
## [Unreleased]

### Changed
- Universal agents now sourced from shared-agents repository
- Agents installed to `.claude/agents/universal/` instead of `installer/global/agents/`
- Version pinning via `installer/shared-agents-version.txt`

### Removed
- Duplicate agents moved to shared-agents: code-reviewer, test-orchestrator, [others]
```

### 6. Update CHANGELOG in RequireKit

Same pattern as TaskWright.

## Test Requirements

- [ ] READMEs render correctly on GitHub
- [ ] Links work
- [ ] Information is accurate
- [ ] No spelling/grammar errors
- [ ] Users can understand what changed

## Estimated Effort

**1 hour**
- Write documentation: 30 minutes
- Review and polish: 20 minutes
- Verify links: 10 minutes

## Success Criteria

- [ ] All three repos have updated documentation
- [ ] CHANGELOGs reflect the changes
- [ ] Documentation is clear and concise
- [ ] No broken links
- [ ] **Ready to announce** 📣

## Notes

**Keep it brief**: Users don't need to know all implementation details. Just:
- What changed (agents are now shared)
- Why it changed (eliminate duplication)
- What they need to do (nothing - automatic)

**What NOT to document** (keep it simple):
- ❌ Detailed technical architecture (overkill)
- ❌ Migration procedures (users don't migrate, we do)
- ❌ Rollback procedures (internal concern)
- ❌ Testing methodology (internal concern)

**Focus**: User-facing documentation. Internal details stay in code comments and task files.
