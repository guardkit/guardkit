# TASK-BRIDGE-001: Implement Agent Bridge Infrastructure (Python)

**Status**: backlog
**Priority**: high
**Estimated Duration**: 3-4 hours
**Tags**: #bridge #ai-integration #core #python

---

## Description

Create the core Python infrastructure for file-based IPC between Python orchestrator and Claude Code's agent system. This implements the checkpoint-resume pattern that enables Python to request agent invocations.

**Part of**: Python↔Claude Agent Invocation Bridge (Critical Feature)
**See**: `docs/proposals/python-claude-bridge-technical-spec.md`

---

## Context

Currently, the Python orchestrator (`template_create_orchestrator.py`) cannot invoke Claude agents because it runs as an isolated subprocess. This task implements the bridge infrastructure that enables agent requests via file-based IPC with exit code 42.

---

## Acceptance Criteria

- [ ] `AgentBridgeInvoker` class created in `installer/global/lib/agent_bridge/invoker.py`
  - [ ] `invoke()` method writes request to `.agent-request.json` and exits with code 42
  - [ ] `load_response()` method reads `.agent-response.json` and caches result
  - [ ] Proper error handling for missing/malformed files
  - [ ] Type hints and docstrings for all public methods

- [ ] `StateManager` class created in `installer/global/lib/agent_bridge/state_manager.py`
  - [ ] `save_state()` method writes orchestrator state to `.template-create-state.json`
  - [ ] `load_state()` method reads and deserializes state
  - [ ] Proper validation of state format
  - [ ] Cleanup method for successful completion

- [ ] `AgentInvocationError` exception class defined

- [ ] Unit tests created in `tests/unit/lib/agent_bridge/`
  - [ ] `test_invoker.py` - AgentBridgeInvoker tests (8+ test methods)
  - [ ] `test_state_manager.py` - StateManager tests (6+ test methods)
  - [ ] Test coverage ≥ 85% for new code
  - [ ] All tests pass

- [ ] Integration tests pass
  - [ ] Request file format validation
  - [ ] Response file format validation
  - [ ] State serialization round-trip
  - [ ] Error scenarios handled correctly

---

## Implementation Plan

### Files to Create

1. `installer/global/lib/agent_bridge/__init__.py`
2. `installer/global/lib/agent_bridge/invoker.py` (~250 lines)
3. `installer/global/lib/agent_bridge/state_manager.py` (~150 lines)
4. `tests/unit/lib/agent_bridge/__init__.py`
5. `tests/unit/lib/agent_bridge/test_invoker.py` (~200 lines)
6. `tests/unit/lib/agent_bridge/test_state_manager.py` (~150 lines)

### Implementation Steps

#### Step 1: Create Package Structure (15 min)
- Create `installer/global/lib/agent_bridge/` directory
- Create `__init__.py` with exports
- Create test directory structure

#### Step 2: Implement AgentBridgeInvoker (90 min)
- Define `AgentRequest` and `AgentResponse` dataclasses
- Implement `__init__()` with file path configuration
- Implement `invoke()`:
  - Create request object with UUID
  - Serialize to JSON
  - Write to `.agent-request.json`
  - Print status messages
  - Exit with code 42
- Implement `load_response()`:
  - Read `.agent-response.json`
  - Deserialize and validate
  - Check status (success/error/timeout)
  - Cache response
  - Cleanup file
  - Raise error if needed
- Implement helper methods:
  - `has_pending_request()`
  - `has_response()`

#### Step 3: Implement StateManager (60 min)
- Define `TemplateCreateState` dataclass
- Implement `__init__()` with file path
- Implement `save_state()`:
  - Handle existing vs new state (preserve created_at)
  - Create state object
  - Serialize to JSON with indent
  - Write to file
- Implement `load_state()`:
  - Read and deserialize JSON
  - Validate format
  - Return state object
- Implement helper methods:
  - `has_state()`
  - `cleanup()`

#### Step 4: Write Unit Tests (60 min)
- Test `AgentBridgeInvoker`:
  - Test `invoke()` writes request and exits with 42
  - Test `load_response()` reads success response
  - Test `load_response()` handles error response
  - Test `load_response()` handles timeout response
  - Test `load_response()` raises on missing file
  - Test cached response reuse
  - Test file cleanup
  - Test helper methods
- Test `StateManager`:
  - Test `save_state()` creates new state
  - Test `save_state()` updates existing state
  - Test `load_state()` round-trip
  - Test `load_state()` raises on missing file
  - Test `cleanup()`
  - Test helper methods

#### Step 5: Integration Testing (30 min)
- Test request/response file formats match spec
- Test state serialization with real data
- Test error scenarios
- Run all tests and verify coverage

---

## Technical Details

### Request Format
```json
{
  "request_id": "uuid-v4",
  "version": "1.0",
  "phase": 6,
  "phase_name": "agent_generation",
  "agent_name": "architectural-reviewer",
  "prompt": "...",
  "timeout_seconds": 120,
  "created_at": "ISO 8601",
  "context": {...}
}
```

### Response Format
```json
{
  "request_id": "uuid-v4",
  "version": "1.0",
  "status": "success|error|timeout",
  "response": "...",
  "error_message": null,
  "error_type": null,
  "created_at": "ISO 8601",
  "duration_seconds": 5.234,
  "metadata": {...}
}
```

### State Format
```json
{
  "version": "1.0",
  "checkpoint": "templates_generated",
  "phase": 5,
  "created_at": "ISO 8601",
  "updated_at": "ISO 8601",
  "config": {...},
  "phase_data": {...}
}
```

---

## Dependencies

- **None** - This is the foundation task

---

## Testing

```bash
# Run unit tests
pytest tests/unit/lib/agent_bridge/ -v --cov=installer/global/lib/agent_bridge --cov-report=term

# Expected: 85%+ coverage, all tests pass
```

---

## Definition of Done

- [ ] All acceptance criteria met
- [ ] Unit tests written and passing (≥85% coverage)
- [ ] Integration tests passing
- [ ] Code reviewed for quality
- [ ] Type hints complete
- [ ] Docstrings complete
- [ ] No linting errors

---

## Related Tasks

- TASK-BRIDGE-002: Orchestrator Integration
- TASK-BRIDGE-003: Command Integration
- TASK-BRIDGE-004: End-to-End Testing

---

## References

- [Python↔Claude Bridge Architecture](../../docs/proposals/python-claude-bridge-architecture.md)
- [Technical Specification](../../docs/proposals/python-claude-bridge-technical-spec.md)
- [TASK-TMPL-4E89 Implementation Plan](../../.claude/task-plans/TASK-TMPL-4E89-implementation-plan.md)
