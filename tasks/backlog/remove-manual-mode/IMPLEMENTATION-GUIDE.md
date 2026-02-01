# Implementation Guide: Remove Manual Implementation Mode

## Wave Breakdown

### Wave 1: Code Changes (Parallel)

These tasks modify code and can run in parallel (no file conflicts).

| Task | Files | Method |
|------|-------|--------|
| TASK-RMM-001 | `installer/core/lib/implementation_mode_analyzer.py` | task-work |
| TASK-RMM-002 | `guardkit/orchestrator/agent_invoker.py` | task-work |

**Conductor Workspaces:**
- `remove-manual-mode-wave1-analyzer`
- `remove-manual-mode-wave1-invoker`

### Wave 2: Migration & Docs (Parallel)

These tasks depend on Wave 1 completion but can run in parallel with each other.

| Task | Files | Method |
|------|-------|--------|
| TASK-RMM-003 | Feature YAMLs, task files | direct |
| TASK-RMM-004 | CLAUDE.md, command specs | direct |

**Conductor Workspaces:**
- `remove-manual-mode-wave2-migration`
- `remove-manual-mode-wave2-docs`

## Execution Strategy

```bash
# Wave 1 (parallel)
/task-work TASK-RMM-001 &
/task-work TASK-RMM-002 &
wait

# Wave 2 (parallel, after Wave 1)
/task-work TASK-RMM-003 &
/task-work TASK-RMM-004 &
wait
```

Or use Conductor for automatic parallel execution.

## Key Code Changes

### TASK-RMM-001: implementation_mode_analyzer.py

**Remove:**
- `MANUAL_KEYWORDS` list (lines 38-49)
- `is_manual_task()` method (lines 166-186)
- Manual check in `assign_mode()` (lines 236-238)

**Update:**
- `assign_mode()` should only return `"task-work"` or `"direct"`
- `get_mode_summary()` should only track `task-work` and `direct`

### TASK-RMM-002: agent_invoker.py

**Remove:**
- Any references to `manual` in `_get_implementation_mode()` return values
- Any `if impl_mode == "manual"` conditional branches

**Verify:**
- Default behavior routes unknown modes to `task-work`

### TASK-RMM-003: Task Migration

**Files to update:**
- `.guardkit/features/FEAT-GR-MVP.yaml` - change `implementation_mode: manual` to `task-work`
- Any task files in `tasks/` with `implementation_mode: manual`

### TASK-RMM-004: Documentation

**Files to update:**
- Root `CLAUDE.md` - update implementation_mode table
- `installer/core/commands/feature-plan.md` - update mode documentation
- `.claude/rules/autobuild.md` - update mode references

## Testing

After Wave 1:
```bash
pytest tests/unit/test_implementation_mode_analyzer.py -v
pytest tests/unit/test_state_bridge.py -v  # May need fixture updates
```

After Wave 2:
```bash
# Verify no manual mode references remain
grep -r "implementation_mode.*manual" tasks/ .guardkit/
grep -r "MANUAL_KEYWORDS" guardkit/ installer/
```
