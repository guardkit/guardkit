---
id: TASK-PD6-REV
title: Apply Phase 6 specification revisions from TASK-REV-PD6 review
status: completed
created: 2025-12-06T11:00:00Z
updated: 2025-12-06T11:00:00Z
priority: high
tags: [progressive-disclosure, phase-6, revisions, specifications]
task_type: implementation
complexity: 3
blocked_by: [TASK-REV-PD6]
blocks: [TASK-PD-020]
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Apply Phase 6 Specification Revisions

## Purpose

Apply the 6 required changes identified in the TASK-REV-PD6 architectural review before Phase 6 implementation can proceed.

## Source

Review Report: `.claude/reviews/TASK-REV-PD6-review-report.md`
Overall Score: 76/100
Recommendation: [R]evise

## Required Changes

### Priority 1 (Required Before Implementation)

1. **Fix dependency chain**: Update TASK-PD-020 `blocked_by` to include `TASK-REV-PD6`

2. **Add rollback strategy** to TASK-PD-020:
   - Backup creation process
   - Recovery procedure
   - Backup cleanup criteria

3. **Mandate backups in acceptance criteria** for TASK-PD-021 and TASK-PD-022:
   ```markdown
   - [ ] Backup created for each agent before migration
   ```

4. **Add section decision matrix** to TASK-PD-020 for ambiguous cases

### Priority 2 (Recommended)

5. **Clarify template agent scope**: Add note to README.md that template agents are deferred to Phase 7

6. **Add Quick Start selection criteria** to TASK-PD-020

### Documentation Updates

7. **Update README.md** with template agents scope clarification
8. **Update IMPLEMENTATION-GUIDE.md** with revision notes

## Files to Modify

| File | Changes |
|------|---------|
| `TASK-PD-020-define-content-migration-rules.md` | Add blocked_by, rollback strategy, section matrix, selection criteria |
| `TASK-PD-021-migrate-high-priority-agents.md` | Add backup requirement to acceptance criteria |
| `TASK-PD-022-migrate-remaining-agents.md` | Add backup requirement to acceptance criteria |
| `README.md` | Add template agents scope clarification |
| `IMPLEMENTATION-GUIDE.md` | Add revision notes |

## Acceptance Criteria

- [x] TASK-PD-020 `blocked_by` includes TASK-REV-PD6
- [x] TASK-PD-020 has rollback strategy section
- [x] TASK-PD-020 has section decision matrix
- [x] TASK-PD-020 has Quick Start selection criteria
- [x] TASK-PD-021 acceptance criteria includes backup requirement
- [x] TASK-PD-022 acceptance criteria includes backup requirement
- [x] README.md clarifies template agents deferred to Phase 7
- [x] IMPLEMENTATION-GUIDE.md updated with revision notes

## Estimated Effort

**15-30 minutes**

## Next Steps

After completion:
```bash
/task-complete TASK-PD6-REV
/task-complete TASK-REV-PD6
/task-work TASK-PD-020
```
