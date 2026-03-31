# Implementation Guide: FEAT-PFI Post-Fix Improvements

## Wave Execution Strategy

### Wave 1 (1 task -- can start immediately)

| Task | Title | Mode | Est. Complexity |
|------|-------|------|----------------|
| TASK-PFI-A1B2 | Suppress CancelledError WARNING on recovery | direct | 1 |

**No dependencies.** Modify log level in `agent_invoker.py` and `autobuild.py`.

### Wave 2 (2 tasks -- parallel, no dependencies on Wave 1)

| Task | Title | Mode | Est. Complexity |
|------|-------|------|----------------|
| TASK-PFI-C3D4 | Investigate VID-002 SDK turn variance | task-work (review) | 3 |
| TASK-PFI-E5F6 | FalkorDB shutdown handler | direct | 2 |

**TASK-PFI-C3D4** is a review/investigation task. It may produce follow-up implementation tasks.

**TASK-PFI-E5F6** modifies `graphiti_client.py` -- no file conflicts with other tasks.

## Execution Commands

```bash
# Wave 1
/task-work TASK-PFI-A1B2

# Wave 2 (parallel via Conductor or sequential)
/task-review TASK-PFI-C3D4
/task-work TASK-PFI-E5F6
```

## File Conflict Analysis

No file conflicts between any tasks:
- TASK-PFI-A1B2: `agent_invoker.py`, `autobuild.py`
- TASK-PFI-C3D4: Read-only analysis
- TASK-PFI-E5F6: `graphiti_client.py`
