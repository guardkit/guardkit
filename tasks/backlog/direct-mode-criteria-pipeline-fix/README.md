# FEAT-DMCP: Direct Mode Criteria Pipeline Fix

## Problem

Direct mode autobuild runs stall with UNRECOVERABLE_STALL because the Coach validator cannot read the Player's requirements data. The Player correctly reports all criteria as addressed, but the data is lost in the pipeline between Player report and Coach validation.

**Parent Review**: TASK-REV-CECA (Analyse autobuild logging feature stall)

## Root Cause

Three cascading bugs in the direct mode data pipeline:

1. `_write_direct_mode_results` drops `requirements_addressed` from `task_work_results.json`
2. Coach text matching reads `requirements_met` (wrong field name — Player writes `requirements_addressed`)
3. `_write_player_report_for_direct_mode` drops `_synthetic` flag, disabling synthetic fallback
4. Synthetic report path uses YAML-only parser, can't load acceptance criteria from markdown body

## Solution

4 targeted bug fixes, organized in 2 waves:

### Wave 1 (Parallel — No Dependencies)

| Task | Fix | Effort |
|------|-----|--------|
| TASK-FIX-DMCP-001 | Copy `requirements_addressed` to `task_work_results.json` | 2 lines |
| TASK-FIX-DMCP-002 | Fix Coach text matching field name | 1 line |
| TASK-FIX-DMCP-003 | Propagate `_synthetic` flag | 2 lines |

### Wave 2 (Depends on Wave 1)

| Task | Fix | Effort |
|------|-----|--------|
| TASK-FIX-DMCP-004 | Fix synthetic report acceptance criteria loading | ~10 lines |

**DMCP-001 + DMCP-002 alone would have prevented the original stall.**

## Verification

After fixes, the preserved worktree can be used to verify:
```bash
cd api_test/.guardkit/worktrees/FEAT-3CC2
guardkit autobuild task TASK-LOG-001 --resume
```
