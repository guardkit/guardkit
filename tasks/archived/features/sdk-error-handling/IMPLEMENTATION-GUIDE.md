# Implementation Guide: SDK Error Handling

## Wave Breakdown

### Wave 1: Core Fixes (Parallel)

These tasks can be executed in parallel as they modify different files.

| Task | Title | Method | Workspace |
|------|-------|--------|-----------|
| TASK-SDK-001 | Improve SDK error message | task-work | sdk-error-wave1-1 |
| TASK-SDK-002 | Add SDK pre-flight check | task-work | sdk-error-wave1-2 |

**Execution**:
```bash
# Option 1: Sequential (simpler)
/task-work TASK-SDK-001
/task-work TASK-SDK-002

# Option 2: Parallel with Conductor (faster)
conductor workspace create sdk-error-wave1-1
conductor workspace create sdk-error-wave1-2
# Run in separate terminals
```

### Wave 2: Extensions (Parallel)

Depends on Wave 1 completion for consistent error handling patterns.

| Task | Title | Method | Workspace |
|------|-------|--------|-----------|
| TASK-SDK-003 | Add guardkit doctor | task-work | sdk-error-wave2-1 |
| TASK-SDK-004 | Update documentation | direct | sdk-error-wave2-2 |

**Execution**:
```bash
# TASK-SDK-003: Full implementation
/task-work TASK-SDK-003

# TASK-SDK-004: Quick documentation update
# Direct edit - no formal task-work needed
```

## File Modifications

### Wave 1 Files

**TASK-SDK-001** (agent_invoker.py):
- `guardkit/orchestrator/agent_invoker.py:730-780`
- Modify `_invoke_with_role` exception handling

**TASK-SDK-002** (autobuild.py):
- `guardkit/cli/autobuild.py`
- Add `_check_sdk_available()` helper
- Call check in `task()` command before orchestrator init

### Wave 2 Files

**TASK-SDK-003** (new file + main.py):
- Create `guardkit/cli/doctor.py`
- Register in `guardkit/cli/main.py`

**TASK-SDK-004** (docs):
- `README.md`
- `docs/guides/guardkit-workflow.md`

## Testing Strategy

### Unit Tests

```bash
# Run after each wave
pytest tests/unit/test_agent_invoker.py -v
pytest tests/unit/test_cli_autobuild.py -v
```

### Integration Tests

```bash
# After Wave 2
pytest tests/integration/ -v -k "sdk or doctor"
```

### Manual Verification

```bash
# Test improved error message (simulate missing SDK)
python3 -c "import sys; sys.modules['claude_agent_sdk'] = None; from guardkit.orchestrator.agent_invoker import AgentInvoker"

# Test doctor command
guardkit doctor
```

## Estimated Effort

| Wave | Tasks | Estimated Time |
|------|-------|----------------|
| 1 | 2 | 2-3 hours |
| 2 | 2 | 2-3 hours |
| **Total** | **4** | **4-6 hours** |

## Risk Assessment

- **Low Risk**: All changes are additive or improve error handling
- **No Breaking Changes**: Error message improvements don't change behavior
- **Easy Rollback**: Each task is independently revertible
