---
id: TASK-SHA-001
title: Verify which agents are truly duplicated between repos
status: completed
created: 2025-11-28T21:00:00Z
updated: 2025-12-03T16:35:00Z
completed: 2025-12-03T16:35:00Z
priority: critical
tags: [shared-agents, verification, lean]
complexity: 2
estimated_effort: 1h
actual_effort: 1h
depends_on: []
blocks: [TASK-SHA-002]
parent_task: TASK-ARCH-DC05
task_type: implementation
outcome: "No true duplicates found. RequireKit agents are vestigial - should be removed from RequireKit, not consolidated."
---

# Task: Verify Agent Duplication

## Context

Before migrating agents to a shared repository, we need to verify which agents actually exist in BOTH GuardKit and RequireKit. The proposal assumes certain agents are duplicated, but we need to confirm this.

**Why critical**: Migrating wrong agents would break one or both tools.

## Acceptance Criteria

- [x] Comparison script created and executed
- [x] List of truly duplicated agents documented
- [x] Similarity check performed (files should be >80% similar)
- [x] Verified list approved for migration

## Verification Results

### Summary (2025-12-03)

| Category | Count |
|----------|-------|
| Truly Duplicated (≥80%) | **0** |
| Manual Review (50-80%) | 4 |
| Low Similarity (<50%) | 1 |
| GuardKit-Only | 14 |
| RequireKit-Only | 2 |

### Agents Present in Both Repos (but diverged)

| Agent | Similarity | Status |
|-------|------------|--------|
| architectural-reviewer | 72% | Diverged - different purposes |
| test-orchestrator | 74% | Diverged - different purposes |
| task-manager | 64% | Diverged - different purposes |
| code-reviewer | 61% | Diverged - different purposes |
| test-verifier | 47% | Significantly diverged |

### Key Finding: NO TRUE DUPLICATES

**None of the 5 shared agents have ≥80% similarity.**

More importantly, the RequireKit review (TASK-3E70) discovered that **RequireKit does NOT actually use these 5 agents**:

- RequireKit commands do NOT invoke `task-manager`, `code-reviewer`, `test-orchestrator`, `test-verifier`, or `architectural-reviewer`
- These agents are **vestigial copies** from shared development history
- RequireKit only uses 2 agents: `bdd-generator` and `requirements-analyst`

### Recommendation

**No migration needed from GuardKit perspective.**

Instead, the 5 unused agents should be **removed from RequireKit**:
- `installer/global/agents/architectural-reviewer.md`
- `installer/global/agents/test-orchestrator.md`
- `installer/global/agents/task-manager.md`
- `installer/global/agents/code-reviewer.md`
- `installer/global/agents/test-verifier.md`

### Agent Ownership After Cleanup

| Repository | Agents |
|------------|--------|
| **GuardKit** | 19 agents (task-manager, code-reviewer, architectural-reviewer, test-orchestrator, test-verifier, + 14 specialists) |
| **RequireKit** | 2 agents (bdd-generator, requirements-analyst) |

## Deliverables

1. **Script**: `scripts/verify-duplication.sh` (395 lines)
2. **Report**: `docs/verified-agents-for-migration.md` (auto-generated)
3. **RequireKit Review**: `/Users/richardwoollcott/Projects/appmilla_github/require-kit/.claude/reviews/TASK-3E70-review-report.md`

## Impact on Parent Task (TASK-ARCH-DC05)

The original goal of "shared agents refactoring" is **no longer necessary** because:
1. No agents are truly duplicated (≥80% similarity)
2. RequireKit doesn't use the shared agents anyway
3. The solution is simpler: remove unused agents from RequireKit

**New scope**: Just clean up RequireKit by removing the 5 unused agents.

## Next Steps

1. ✅ TASK-SHA-001 complete (this task)
2. Create task in RequireKit to remove unused agents
3. Close TASK-ARCH-DC05 or update its scope
