# Python↔Claude Agent Invocation Bridge - Architecture Design

**Date**: 2025-01-11
**Status**: PROPOSAL
**Priority**: CRITICAL
**Author**: AI Analysis

---

## Executive Summary

**Problem**: Python orchestrator (`template_create_orchestrator.py`) cannot invoke Claude Code agents because it runs as an isolated subprocess with no access to Claude's internal agent system.

**Impact**: AI-powered agent generation (TASK-TMPL-4E89) is non-functional, resulting in ZERO agents being created during `/template-create` execution.

**Solution**: Implement a bridge mechanism enabling Python subprocess to request agent invocations from the parent Claude Code process.

---

## Current Architecture Analysis

### Execution Flow
```
User types: /template-create
           ↓
Claude Code reads: ~/.agentecflow/commands/template-create.md
           ↓
Claude executes: python3 -m installer.global.commands.lib.template_create_orchestrator
           ↓
Python subprocess runs in isolation
           ↓
Phase 6: Needs AI agent invocation
           ↓
❌ DefaultAgentInvoker raises NotImplementedError
           ↓
Falls back to hard-coded detection (returns [])
           ↓
Result: ZERO agents created
```

### Key Constraints

1. **Process Isolation**: Python runs as subprocess via Bash tool
2. **No Shared Memory**: Python cannot access Claude's internal state
3. **No Network API**: Claude Code doesn't expose HTTP/RPC endpoints
4. **Single Direction**: Python → Claude communication needed
5. **Reliability**: Must handle timeouts, errors, crashes gracefully

---

## Proposed Solutions

## Option 1: File-Based IPC with Checkpoint Resume ⭐ **RECOMMENDED**

### Architecture
```
/template-create (Claude)
        ↓
    [Phases 1-5] Python runs normally
        ↓
    [Phase 6] Python needs AI:
        ├─ Save state: .template-state.json
        ├─ Write request: .agent-request.json
        └─ Exit with code 42 (NEED_AGENT)
        ↓
    Claude detects exit code 42:
        ├─ Read: .agent-request.json
        ├─ Invoke agent via Task tool
        └─ Write: .agent-response.json
        ↓
    Claude re-runs Python with --resume:
        ├─ Load state: .template-state.json
        ├─ Read response: .agent-response.json
        ├─ Continue Phase 6
        └─ Complete Phases 7-8
        ↓
    Exit code 0 (SUCCESS)
```

### Implementation Details

#### Request Format (`.agent-request.json`)
```json
{
  "request_id": "uuid-v4",
  "phase": 6,
  "agent_name": "architectural-reviewer",
  "prompt": "Analyze this codebase...",
  "timeout_seconds": 120,
  "created_at": "2025-01-11T10:30:00Z"
}
```

#### Response Format (`.agent-response.json`)
```json
{
  "request_id": "uuid-v4",
  "status": "success|error|timeout",
  "response": "Agent response text...",
  "error_message": null,
  "completed_at": "2025-01-11T10:32:15Z"
}
```

#### State Format (`.template-state.json`)
```json
{
  "phase": 6,
  "qa_answers": {...},
  "analysis": {...},
  "manifest": {...},
  "settings": {...},
  "templates": [...],
  "agent_inventory": {...},
  "checkpoint": "agent_generation"
}
```

### Pros
- ✅ Simple file I/O (no complex IPC)
- ✅ Reliable (no race conditions)
- ✅ Debuggable (can inspect files)
- ✅ Resumable (state persisted)
- ✅ No polling overhead
- ✅ Clean error handling
- ✅ Works on all platforms

### Cons
- ⚠️ Multiple Python invocations
- ⚠️ State serialization overhead
- ⚠️ Disk I/O latency (~50-100ms)

### Estimated Complexity
**Files to Modify**: 3
**New Files**: 2
**Lines of Code**: ~400
**Development Time**: 6-8 hours
**Risk**: Low

---

## Option 2: File-Based IPC with Background Monitoring

### Architecture
```
/template-create (Claude)
        ↓
    Launch Python in background (Bash tool with run_in_background=true)
        ↓
    Enter monitoring loop:
        while Python running:
            ├─ Check for .agent-request-*.json
            ├─ If found:
            │   ├─ Invoke agent
            │   └─ Write .agent-response-*.json
            └─ Sleep 500ms
        ↓
    Wait for Python exit
        ↓
    Return results
```

### Implementation Details

#### Python Side - Non-Blocking Request
```python
class AgentBridgeInvoker:
    def invoke(self, agent_name: str, prompt: str) -> str:
        request_id = str(uuid.uuid4())
        request_file = Path(f"/tmp/.agent-request-{request_id}.json")
        response_file = Path(f"/tmp/.agent-response-{request_id}.json")

        # Write request
        request_file.write_text(json.dumps({
            "request_id": request_id,
            "agent_name": agent_name,
            "prompt": prompt,
            "timeout_seconds": 120
        }))

        # Poll for response
        start_time = time.time()
        while time.time() - start_time < 120:
            if response_file.exists():
                response = json.loads(response_file.read_text())
                request_file.unlink(missing_ok=True)
                response_file.unlink(missing_ok=True)
                return response["response"]
            time.sleep(0.5)

        raise TimeoutError("Agent invocation timed out")
```

#### Claude Side - Monitoring Loop (in template-create.md)
```markdown
## Execution

1. Launch Python orchestrator in background:
   - Use Bash tool with run_in_background=true
   - Store bash_id for monitoring

2. Enter agent request monitoring loop:
   - Check /tmp/.agent-request-*.json every 500ms
   - When found, invoke agent and write response
   - Continue until Python exits

3. Collect results and display summary
```

### Pros
- ✅ Single Python invocation
- ✅ Real-time agent invocation
- ✅ No state serialization needed
- ✅ Faster overall execution

### Cons
- ❌ Complex monitoring loop in markdown command
- ❌ Polling overhead (CPU cycles)
- ❌ Race conditions possible
- ❌ Error handling more complex
- ❌ Harder to debug
- ❌ Temporary file cleanup needed

### Estimated Complexity
**Files to Modify**: 4
**New Files**: 3
**Lines of Code**: ~600
**Development Time**: 10-12 hours
**Risk**: Medium-High

---

## Option 3: Refactor to Claude-Orchestrated

### Architecture
```
/template-create (Claude) orchestrates ALL phases:
    ├─ Phase 1: Q&A
    │   └─ Call Python helper: qa_session.py
    ├─ Phase 2: AI Analysis
    │   ├─ Call Python helper: file_collector.py
    │   ├─ Invoke architectural-reviewer agent (directly)
    │   └─ Call Python helper: parse_analysis.py
    ├─ Phase 3-5: Manifest/Settings/Templates
    │   └─ Call Python helpers
    ├─ Phase 6: Agent Recommendation
    │   ├─ Call Python helper: identify_patterns.py
    │   ├─ Invoke architectural-reviewer agent (directly)
    │   └─ Call Python helper: generate_agents.py
    ├─ Phase 7-8: CLAUDE.md/Assembly
    │   └─ Call Python helpers
    └─ Display results
```

### Pros
- ✅ Direct agent access (no bridge needed)
- ✅ Full control in Claude
- ✅ No IPC complexity
- ✅ Simpler error handling

### Cons
- ❌ Major refactor (move orchestration to markdown)
- ❌ Lose Python's flexibility
- ❌ Markdown commands become huge
- ❌ Hard to test orchestration logic
- ❌ Mixing concerns (UI + logic)

### Estimated Complexity
**Files to Modify**: 12+
**New Files**: 8+
**Lines of Code**: ~1500
**Development Time**: 20-30 hours
**Risk**: High

---

## Comparison Matrix

| Criterion | Option 1: Checkpoint | Option 2: Background | Option 3: Refactor |
|-----------|---------------------|----------------------|-------------------|
| **Complexity** | Low | Medium-High | Very High |
| **Development Time** | 6-8h | 10-12h | 20-30h |
| **Risk** | Low | Medium | High |
| **Maintainability** | High | Medium | Low |
| **Debuggability** | High | Medium | Low |
| **Performance** | Good | Better | Best |
| **Testability** | High | Medium | Low |
| **Reliability** | High | Medium | Medium |
| **Platform Support** | All | All | All |

---

## Recommendation

**CHOOSE OPTION 1: File-Based IPC with Checkpoint Resume**

### Rationale

1. **Lowest Risk**: Simple file I/O, well-understood patterns
2. **High Reliability**: No race conditions, clean state management
3. **Best Debuggability**: Can inspect state files at each checkpoint
4. **Maintainable**: Clear separation of concerns
5. **Testable**: Each component testable independently
6. **Fast Implementation**: 6-8 hours vs 10-30 hours
7. **Proven Pattern**: Similar to job queues, workflow engines

### Trade-offs Accepted

- Multiple Python invocations (2-3 total)
- State serialization overhead (~50-100ms)
- Slightly slower than Option 2 (~1-2 seconds total overhead)

**These trade-offs are acceptable** because:
- Template creation is infrequent (not performance-critical)
- Reliability > Speed for this use case
- Debugging capability is crucial for complex workflows

---

## Implementation Strategy

### Phase 1: Core Bridge Infrastructure (3-4 hours)
- [ ] Create `AgentBridgeInvoker` class (Python)
- [ ] Implement state serialization/deserialization
- [ ] Implement request/response file handling
- [ ] Add exit code constants
- [ ] Unit tests for bridge components

### Phase 2: Orchestrator Integration (2-3 hours)
- [ ] Modify `AIAgentGenerator.__init__()` to accept bridge invoker
- [ ] Update `template_create_orchestrator.py` to pass bridge invoker
- [ ] Add `--resume` flag support to orchestrator
- [ ] Add state checkpoint/restore logic
- [ ] Integration tests

### Phase 3: Command Integration (1-2 hours)
- [ ] Modify `/template-create` command to handle exit code 42
- [ ] Add agent invocation loop
- [ ] Add state file cleanup
- [ ] Error handling and timeouts
- [ ] End-to-end testing

### Phase 4: Documentation & Testing (1 hour)
- [ ] Update architecture documentation
- [ ] Add troubleshooting guide
- [ ] Create test fixtures
- [ ] Verify with user's dotnet-maui-clean-mvvm codebase

---

## Success Metrics

### Before (Current State)
- ❌ Agents created: 0
- ❌ AI invocation: Fails with NotImplementedError
- ❌ Fallback detection: Returns empty list
- ❌ Template usefulness: Low

### After (Target State)
- ✅ Agents created: 7-9 for complex codebases
- ✅ AI invocation: Success via bridge
- ✅ Fallback detection: Only if AI fails
- ✅ Template usefulness: High
- ✅ Detection coverage: 78-100% (vs current 14-30%)

---

## Next Steps

1. **Approval**: Get user confirmation on Option 1
2. **Task Creation**: Break down into 4 implementable tasks
3. **Implementation**: Execute phases 1-4 sequentially
4. **Validation**: Test with user's dotnet-maui-clean-mvvm codebase
5. **Documentation**: Update all related docs

---

## Appendix: Alternative Approaches Considered

### A. HTTP Server
- Rejected: Too complex for simple use case
- Overhead: Server lifecycle, port management, HTTP client

### B. Named Pipes
- Rejected: Platform-specific (Windows vs Unix)
- Complexity: Signal handling, buffering

### C. Shared Memory
- Rejected: Not feasible across language boundaries
- Python subprocess can't access Claude's memory

### D. Message Queue (Redis/RabbitMQ)
- Rejected: External dependency overhead
- Overkill for single-machine IPC
