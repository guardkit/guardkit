---
id: TASK-PD-021
title: Migrate high-priority agents (task-manager, devops-specialist)
status: completed
created: 2025-12-06T10:00:00Z
updated: 2025-12-06T12:43:00Z
completed: 2025-12-06T12:43:00Z
priority: high
tags: [progressive-disclosure, phase-6, content-migration, high-priority]
complexity: 5
blocked_by: [TASK-PD-020]
blocks: [TASK-PD-022]
review_task: TASK-REV-PD-CONTENT
test_results:
  status: passed
  coverage: null
  last_run: 2025-12-06T12:43:00Z
---

# Task: Migrate high-priority agents

## Phase

**Phase 6: Content Migration** (Task 2 of 5)

## Description

Migrate content for the two largest agents first to validate the migration approach and achieve the biggest token reduction wins.

## Completion Summary

### Migration Results

| Agent | Original | Core | Extended | Reduction | Target Met |
|-------|----------|------|----------|-----------|------------|
| task-manager | 72,096 bytes | 12,601 bytes | 60,086 bytes | 82.5% | ✅ (≤25KB) |
| devops-specialist | 57,457 bytes | 2,984 bytes | 55,076 bytes | 94.8% | ✅ (≤20KB) |
| **Combined** | 129,553 bytes | 15,585 bytes | - | **88.0%** | ✅ |

### Files Created/Modified

**task-manager**:
- `installer/global/agents/task-manager.md` - Core file (12.6KB)
- `installer/global/agents/task-manager-ext.md` - Extended file (60.1KB)
- `installer/global/agents/task-manager.md.bak` - Backup retained

**devops-specialist**:
- `installer/global/agents/devops-specialist.md` - Core file (2.9KB)
- `installer/global/agents/devops-specialist-ext.md` - Extended file (55.1KB)
- `installer/global/agents/devops-specialist.md.bak` - Backup retained

### Validation Results

- ✅ Agent discovery works (both agents found)
- ✅ No `-ext.md` files in discovery
- ✅ All 6 integration tests pass
- ✅ Backups retained for TASK-PD-024 validation

## Acceptance Criteria

- [x] **Backup created for each agent before migration** (task-manager.md.bak, devops-specialist.md.bak)
- [x] task-manager.md reduced to ≤25KB (actual: 12.6KB)
- [x] task-manager-ext.md contains moved content (~50KB) (actual: 60.1KB)
- [x] devops-specialist.md reduced to ≤20KB (actual: 2.9KB)
- [x] devops-specialist-ext.md contains moved content (~40KB) (actual: 55.1KB)
- [x] No content lost (total ≈ original, verified against backup)
- [x] Agent discovery still works
- [x] Integration tests still pass
- [x] Backups retained for TASK-PD-024 validation

## Estimated Effort

**1 day** (Actual: ~15 minutes)

## Dependencies

- TASK-PD-020 (migration rules defined) ✅ Complete

## Next Steps

- TASK-PD-022: Migrate remaining 12 agents (unblocked by this task)
- TASK-REV-PD-CONTENT: Review migration quality before proceeding
