# Implementation Guide: File Tracking Fix

## Wave Breakdown

### Wave 1: Parallel Execution (2 tasks)

Both tasks can be executed in parallel as they modify the same file but different sections.

| Task | Title | Mode | Workspace |
|------|-------|------|-----------|
| TASK-FTF-001 | Fix file tracking in agent_invoker.py | task-work | file-tracking-fix-wave1-1 |
| TASK-FTF-002 | Add test count extraction | direct | file-tracking-fix-wave1-2 |

## Execution Strategy

### For Conductor Users

```bash
# Wave 1 - Run in parallel
conductor workspace create file-tracking-fix-wave1-1
conductor workspace create file-tracking-fix-wave1-2

# In workspace 1:
/task-work TASK-FTF-001

# In workspace 2 (parallel):
# Direct implementation - no /task-work needed
```

### For Sequential Execution

```bash
# Task 1
/task-work TASK-FTF-001

# Task 2 (direct - simpler implementation)
# Implement directly in agent_invoker.py
```

## Key Files

| File | Purpose |
|------|---------|
| `guardkit/orchestrator/agent_invoker.py` | Main implementation target |
| `tests/unit/test_agent_invoker.py` | Unit tests |

## Testing

After implementation:

```bash
# Run unit tests
pytest tests/unit/test_agent_invoker.py -v

# Integration test
guardkit autobuild task TASK-XXX --max-turns 3
# Verify file counts display correctly
```

## Merge Order

1. Merge TASK-FTF-001 first (primary fix)
2. Merge TASK-FTF-002 (enhancement)
3. Run integration test to verify

## Success Metrics

- [ ] "0 files created" no longer appears when files are created
- [ ] Test counts reflect actual tests
- [ ] All existing tests pass
- [ ] No regression in AutoBuild functionality
