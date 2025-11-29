# Implementation Plan: TASK-BRIDGE-001

**Task**: Implement Agent Bridge Infrastructure (Python)
**Status**: in_progress
**Created**: 2025-11-11
**Estimated Duration**: 3-4 hours

---

## Overview

Create the core Python infrastructure for file-based IPC between Python orchestrator and Claude Code's agent system. This implements the checkpoint-resume pattern that enables Python to request agent invocations via exit code 42.

---

## Architecture

```
Python Orchestrator
    ↓
[Save State] → .template-create-state.json
    ↓
[Write Request] → .agent-request.json
    ↓
[Exit with code 42]
    ↓
Claude detects exit code 42
    ↓
[Invoke Agent via Task tool]
    ↓
[Write Response] → .agent-response.json
    ↓
[Re-run Python with --resume]
    ↓
[Load State] ← .template-create-state.json
    ↓
[Load Response] ← .agent-response.json
    ↓
[Continue execution]
```

---

## Components to Implement

### 1. AgentBridgeInvoker Class
**File**: `installer/global/lib/agent_bridge/invoker.py`
**Lines**: ~250

**Responsibilities**:
- Write agent request to `.agent-request.json`
- Exit with code 42 to signal NEED_AGENT
- Load agent response from `.agent-response.json`
- Cache response for subsequent calls
- Handle errors and timeouts

**Key Methods**:
- `__init__(request_file, response_file, phase, phase_name)` - Initialize with file paths
- `invoke(agent_name, prompt, timeout_seconds, context)` - Request agent invocation (exits with 42)
- `load_response()` - Load and validate agent response
- `has_pending_request()` - Check if request file exists
- `has_response()` - Check if response file exists

**Data Classes**:
- `AgentRequest` - Request format (request_id, version, phase, agent_name, prompt, etc.)
- `AgentResponse` - Response format (request_id, status, response, error_message, etc.)

**Exception**:
- `AgentInvocationError` - Raised when agent invocation fails

### 2. StateManager Class
**File**: `installer/global/lib/agent_bridge/state_manager.py`
**Lines**: ~150

**Responsibilities**:
- Save orchestrator state to `.template-create-state.json`
- Load state for resume operations
- Preserve created_at timestamp across updates
- Cleanup state on successful completion

**Key Methods**:
- `__init__(state_file)` - Initialize with state file path
- `save_state(checkpoint, phase, config, phase_data, agent_request_pending)` - Save current state
- `load_state()` - Load and deserialize state
- `has_state()` - Check if state file exists
- `cleanup()` - Delete state file

**Data Class**:
- `TemplateCreateState` - Complete state (version, checkpoint, phase, timestamps, config, phase_data)

### 3. Package Structure
**Files**:
- `installer/global/lib/agent_bridge/__init__.py` - Package exports
- `tests/unit/lib/agent_bridge/__init__.py` - Test package init

---

## File Structure

```
installer/global/lib/agent_bridge/
├── __init__.py                    # Package exports
├── invoker.py                     # AgentBridgeInvoker
└── state_manager.py               # StateManager

tests/unit/lib/agent_bridge/
├── __init__.py                    # Test package
├── test_invoker.py               # AgentBridgeInvoker tests (8+ tests)
└── test_state_manager.py         # StateManager tests (6+ tests)
```

---

## Implementation Steps

### Step 1: Create Package Structure (10 min)
- Create `installer/global/lib/agent_bridge/` directory
- Create `installer/global/lib/agent_bridge/__init__.py`
- Export main classes: `AgentBridgeInvoker`, `StateManager`, `AgentInvocationError`
- Create `tests/unit/lib/agent_bridge/` directory structure
- Create test `__init__.py` files

### Step 2: Implement AgentBridgeInvoker (90 min)

#### 2.1: Define Data Classes (20 min)
- `AgentRequest` dataclass with all required fields
- `AgentResponse` dataclass with all required fields
- Add type hints and field validation

#### 2.2: Implement __init__ and Helper Methods (15 min)
- `__init__()` - Initialize file paths and cache
- `has_pending_request()` - Check request file exists
- `has_response()` - Check response file exists

#### 2.3: Implement invoke() Method (30 min)
- Check if response already cached (from --resume)
- If cached, return immediately
- Otherwise:
  - Generate UUID for request_id
  - Create AgentRequest object
  - Serialize to JSON with proper formatting
  - Write to `.agent-request.json`
  - Print status messages
  - Exit with code 42

#### 2.4: Implement load_response() Method (25 min)
- Check response file exists (raise FileNotFoundError if not)
- Read and parse JSON
- Deserialize to AgentResponse
- Check status:
  - `success` → cache response, cleanup file, return
  - `timeout` → raise AgentInvocationError
  - `error` → raise AgentInvocationError with details
- Handle malformed JSON gracefully

### Step 3: Implement StateManager (60 min)

#### 3.1: Define TemplateCreateState Dataclass (10 min)
- All required fields with types
- Optional agent_request_pending field

#### 3.2: Implement __init__ and Helper Methods (10 min)
- `__init__()` - Initialize state file path
- `has_state()` - Check state file exists
- `cleanup()` - Delete state file safely

#### 3.3: Implement save_state() Method (25 min)
- Check if state file exists
- If exists, load and preserve `created_at`
- If not, generate new `created_at` timestamp
- Create TemplateCreateState object
- Serialize to JSON with indent=2
- Write to `.template-create-state.json`
- Set proper encoding (utf-8)

#### 3.4: Implement load_state() Method (15 min)
- Check state file exists (raise FileNotFoundError if not)
- Read and parse JSON
- Deserialize to TemplateCreateState
- Validate required fields present
- Return state object

### Step 4: Write Unit Tests (80 min)

#### 4.1: Test AgentBridgeInvoker (50 min)

**test_invoker.py** - Minimum 8 tests:

1. `test_invoke_writes_request_and_exits_42` - Verify request file written and exit code 42
2. `test_invoke_with_cached_response_returns_immediately` - Verify cached response reuse
3. `test_load_response_success` - Verify successful response loading and cleanup
4. `test_load_response_error` - Verify error response raises exception
5. `test_load_response_timeout` - Verify timeout response raises exception
6. `test_load_response_missing_file` - Verify FileNotFoundError when file missing
7. `test_has_pending_request` - Verify request file detection
8. `test_has_response` - Verify response file detection
9. `test_request_format_validation` - Verify request JSON structure matches spec
10. `test_response_cleanup` - Verify response file deleted after successful load

#### 4.2: Test StateManager (30 min)

**test_state_manager.py** - Minimum 6 tests:

1. `test_save_state_creates_new` - Verify new state creation with created_at
2. `test_save_state_updates_existing` - Verify created_at preserved on update
3. `test_load_state_round_trip` - Verify save/load cycle
4. `test_load_state_missing_file` - Verify FileNotFoundError when missing
5. `test_has_state` - Verify state file detection
6. `test_cleanup` - Verify state file deletion
7. `test_state_format_validation` - Verify state JSON structure matches spec

### Step 5: Integration Testing and Validation (30 min)

#### 5.1: Manual Integration Tests (15 min)
- Test complete request/response cycle
- Verify file formats match specification
- Test error scenarios
- Verify cleanup behavior

#### 5.2: Run Test Suite and Verify Coverage (15 min)
- Run: `pytest tests/unit/lib/agent_bridge/ -v --cov=installer/global/lib/agent_bridge --cov-report=term`
- Verify ≥85% coverage
- Fix any failing tests
- Address coverage gaps

---

## Data Formats

### Request Format (.agent-request.json)
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

### Response Format (.agent-response.json)
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

### State Format (.template-create-state.json)
```json
{
  "version": "1.0",
  "checkpoint": "templates_generated",
  "phase": 5,
  "created_at": "ISO 8601",
  "updated_at": "ISO 8601",
  "config": {...},
  "phase_data": {...},
  "agent_request_pending": {...}
}
```

---

## Quality Gates

### Code Quality
- ✅ All type hints present
- ✅ Complete docstrings (Google style)
- ✅ No linting errors (flake8, pylint)
- ✅ Proper error handling
- ✅ Clean code (SOLID principles)

### Testing
- ✅ All tests passing
- ✅ ≥85% code coverage
- ✅ Edge cases covered
- ✅ Error scenarios tested

### Documentation
- ✅ Clear docstrings
- ✅ Inline comments for complex logic
- ✅ Type hints for maintainability

---

## Dependencies

**Python Standard Library**:
- `json` - JSON serialization
- `sys` - Exit code handling
- `pathlib` - File path operations
- `typing` - Type hints
- `dataclasses` - Data structures
- `datetime` - Timestamp generation
- `uuid` - Request ID generation

**Testing**:
- `pytest` - Test framework
- `pytest-cov` - Coverage reporting

**No External Dependencies** - Uses only Python standard library

---

## Testing Command

```bash
# Run unit tests with coverage
pytest tests/unit/lib/agent_bridge/ -v \
  --cov=installer/global/lib/agent_bridge \
  --cov-report=term \
  --cov-report=json

# Expected output:
# - All tests pass
# - Coverage ≥ 85%
# - No warnings or errors
```

---

## Success Criteria

- ✅ AgentBridgeInvoker class implemented with all methods
- ✅ StateManager class implemented with all methods
- ✅ AgentInvocationError exception defined
- ✅ Package structure created with proper exports
- ✅ Unit tests written (14+ test methods)
- ✅ Test coverage ≥ 85%
- ✅ All tests passing
- ✅ No linting errors
- ✅ Type hints complete
- ✅ Docstrings complete
- ✅ File formats match specification exactly

---

## Risk Mitigation

### Risk 1: Exit code 42 behavior
**Mitigation**: Use `sys.exit(42)` which is standard Python behavior

### Risk 2: File I/O errors
**Mitigation**: Proper error handling with try/except and clear error messages

### Risk 3: JSON serialization issues
**Mitigation**: Use dataclasses with explicit type hints, validate formats

### Risk 4: Race conditions with file cleanup
**Mitigation**: Use `missing_ok=True` for file deletion operations

### Risk 5: Coverage below 85%
**Mitigation**: Write comprehensive tests for all code paths including error scenarios

---

## Related Tasks

- **TASK-BRIDGE-002**: Orchestrator Integration (depends on this)
- **TASK-BRIDGE-003**: Command Integration (depends on TASK-BRIDGE-002)
- **TASK-BRIDGE-004**: End-to-End Testing (depends on TASK-BRIDGE-003)

---

## References

- [Python↔Claude Bridge Technical Specification](../../docs/proposals/python-claude-bridge-technical-spec.md)
- [Python↔Claude Bridge Architecture](../../docs/proposals/python-claude-bridge-architecture.md)
- Python `dataclasses` documentation
- Python `pathlib` documentation
- pytest documentation
