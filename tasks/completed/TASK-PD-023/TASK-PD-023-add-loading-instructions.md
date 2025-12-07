---
id: TASK-PD-023
title: Add loading instructions to all core agent files
status: completed
created: 2025-12-06T10:00:00Z
updated: 2025-12-06T15:10:00Z
completed: 2025-12-06T15:10:00Z
priority: medium
tags: [progressive-disclosure, phase-6, content-migration, loading-instructions]
complexity: 3
blocked_by: [TASK-PD-022]
blocks: [TASK-PD-024]
review_task: TASK-REV-PD-CONTENT
test_results:
  status: passed
  coverage: null
  last_run: 2025-12-06T15:10:00Z
---

# Task: Add loading instructions to all core agent files

## Phase

**Phase 6: Content Migration** (Task 4 of 5)

## Description

Ensure all 14 core agent files have the `## Extended Reference` section with clear instructions for loading extended content when needed.

## Completion Summary

All 14 core agent files already have the `## Extended Reference` section with correct loading instructions. The migration script (`scripts/migrate-agent-content.py`) automatically adds this section during content migration.

### Loading Instruction Format

Each core agent file includes:

```markdown
## Extended Reference

For detailed examples, best practices, and troubleshooting:

```bash
cat agents/{agent-name}-ext.md
```

The extended file includes:
- Additional Quick Start examples
- Detailed code examples with explanations
- Best practices with rationale
- Anti-patterns to avoid
- Technology-specific guidance
- Troubleshooting common issues
```

### Verification Results

| Agent | Has Loading Instruction | Path Correct |
|-------|------------------------|--------------|
| task-manager | ✅ | ✅ |
| devops-specialist | ✅ | ✅ |
| git-workflow-manager | ✅ | ✅ |
| security-specialist | ✅ | ✅ |
| database-specialist | ✅ | ✅ |
| architectural-reviewer | ✅ | ✅ |
| agent-content-enhancer | ✅ | ✅ |
| code-reviewer | ✅ | ✅ |
| debugging-specialist | ✅ | ✅ |
| test-verifier | ✅ | ✅ |
| test-orchestrator | ✅ | ✅ |
| pattern-advisor | ✅ | ✅ |
| complexity-evaluator | ✅ | ✅ |
| build-validator | ✅ | ✅ |

**Total**: 14/14 agents with correct loading instructions

### Validation

- ✅ All 6 integration tests pass
- ✅ All agents have `## Extended Reference` section
- ✅ All paths correctly reference `agents/{agent-name}-ext.md`

## Acceptance Criteria

- [x] All 14 core agent files have `## Extended Reference` section
- [x] Loading instruction includes correct path to ext file
- [x] "Load when" guidance is present (via extended file includes list)
- [x] Validation script confirms all files updated

## Estimated Effort

**0.5 days** (Actual: Already complete from TASK-PD-022 migration)

## Dependencies

- TASK-PD-022 (all agents migrated) ✅ Complete

## Next Steps

- TASK-PD-024: Final validation and metrics (now unblocked)
