# Shared Agents Refactoring - ARCHIVED

**Archived Date**: 2025-12-03
**Reason**: Original scope invalidated by TASK-SHA-001 findings

## Summary

The "shared agents refactoring" initiative was based on the assumption that agents were duplicated between GuardKit and RequireKit, requiring consolidation into a shared repository.

**TASK-SHA-001 discovered this assumption was incorrect:**

1. **No true duplicates exist** - All 5 "shared" agents have <80% similarity (they've diverged)
2. **RequireKit doesn't use them** - The 5 agents in RequireKit are vestigial copies, never invoked by any commands
3. **Simple solution** - Just remove the unused agents from RequireKit

## Archived Tasks

These tasks are no longer needed:

| Task | Original Purpose | Status |
|------|------------------|--------|
| TASK-SHA-002 | Create shared-agents repository | CANCELLED - Not needed |
| TASK-SHA-003 | Update GuardKit to use shared repo | CANCELLED - Not needed |
| TASK-SHA-004 | Update RequireKit to use shared repo | REPLACED - Just remove unused agents |
| TASK-SHA-005 | Test both tools | CANCELLED - Not needed |
| TASK-SHA-006 | Update documentation | CANCELLED - Not needed |

## New Action

Instead of the original 6-task plan, a single task in RequireKit is needed:

**Remove 5 unused agents from RequireKit:**
- `installer/global/agents/architectural-reviewer.md`
- `installer/global/agents/test-orchestrator.md`
- `installer/global/agents/task-manager.md`
- `installer/global/agents/code-reviewer.md`
- `installer/global/agents/test-verifier.md`

## Evidence

- **Verification Script**: [scripts/verify-duplication.sh](../../../scripts/verify-duplication.sh)
- **Verification Report**: [docs/verified-agents-for-migration.md](../../../docs/verified-agents-for-migration.md)
- **RequireKit Review**: `/Users/richardwoollcott/Projects/appmilla_github/require-kit/.claude/reviews/TASK-3E70-review-report.md`

## Files in This Archive

- `README.md` - Original initiative description
- `IMPLEMENTATION-PLAN-LEAN.md` - Original lean implementation plan
- `TASK-SHA-002-create-shared-repo.md` - Cancelled
- `TASK-SHA-003-update-guardkit.md` - Cancelled
- `TASK-SHA-004-update-requirekit.md` - To be replaced with simple removal task
- `TASK-SHA-005-test-both-tools.md` - Cancelled
- `TASK-SHA-006-update-documentation.md` - Cancelled
- `archive/` - Previously archived files
