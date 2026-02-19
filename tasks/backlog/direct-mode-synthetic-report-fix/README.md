# Direct Mode Synthetic Report Fix (FEAT-DM-FIX)

**Source**: TASK-REV-F248 (Analyse RequireKit v2 Refinement Commands autobuild failure)
**Status**: Ready for implementation
**Priority**: Critical

## Summary

Direct mode autobuild tasks with acceptance criteria always stall because the synthetic report path produces empty `requirements_met` and no `completion_promises`. The Coach validator sees 0/N criteria met on every turn, triggering UNRECOVERABLE_STALL.

This was predicted as Q1 ("direct mode + Coach rejection") in the SFT-001 diagnostic diagrams and confirmed by the FEAT-498F RequireKit failure.

## Tasks

| Task | Wave | Description | Complexity | Status |
|------|------|-------------|-----------|--------|
| TASK-FIX-D1A3 | 1 | Unify synthetic report builders + add file-existence promises | 6 | **completed** |
| TASK-FIX-D1A4 | 2 | Add AC count guard to mode assignment | 3 | backlog |
| TASK-TEST-D1A5 | 2 | Integration tests for direct mode criteria matching | 4 | backlog |

## Quick Workaround

Change TASK-RK01-003 `implementation_mode: direct` → `task-work` in RequireKit feature YAML and re-run.
