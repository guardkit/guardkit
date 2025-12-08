# Review Report: TASK-REV-993B

## Executive Summary

The `/template-create` command successfully generates 25 template files but fails to create any agent stubs. **Root cause identified**: The `AgentBridgeInvoker` uses a single cached response for all AI invocations, causing Phase 5 (Agent Recommendation) to receive Phase 1's response instead of its own, resulting in schema validation failures.

**Severity**: High (blocks agent generation feature entirely)
**Impact**: All `/template-create` runs produce templates without agents
**Fix Complexity**: Medium (requires bridge invoker refactoring)

---

## Review Details

| Attribute | Value |
|-----------|-------|
| **Mode** | Code Quality Review |
| **Depth** | Standard |
| **Duration** | ~45 minutes |
| **Reviewer** | code-reviewer agent |
| **Files Analyzed** | 6 |

---

## Findings

### Finding 1: Single Cached Response Causes Cross-Phase Data Leakage (CRITICAL)

**Location**: [installer/global/lib/agent_bridge/invoker.py:133](installer/global/lib/agent_bridge/invoker.py#L133)

**Evidence**:
```python
class AgentBridgeInvoker:
    def __init__(self, ...):
        # ...
        self._cached_response: Optional[str] = None  # SINGLE cache for ALL invocations

    def invoke(self, agent_name: str, prompt: str, ...) -> str:
        # If we already have a cached response (from --resume), use it
        if self._cached_response is not None:
            return self._cached_response  # Returns Phase 1 response for Phase 5!
```

**Problem**: The bridge uses a single `_cached_response` variable that persists across all `invoke()` calls. When the orchestrator resumes after checkpoint:
1. Phase 1 response is loaded into `_cached_response`
2. Phase 5 calls `invoke()` with a different prompt
3. Phase 5 receives Phase 1's response (codebase analysis JSON)
4. Phase 5 parsing fails because the schema doesn't match

**Impact**: 100% failure rate for agent generation during resume flow

---

### Finding 2: Schema Mismatch Between Phase 1 and Phase 5 Responses

**Location**: [installer/global/lib/agent_generator/agent_generator.py:427-431](installer/global/lib/agent_generator/agent_generator.py#L427-L431)

**Phase 1 Response Schema** (Codebase Analysis):
```json
{
  "metadata": {...},
  "technology": {...},
  "architecture": {...},
  "quality": {...},
  "example_files": [
    {"path": "...", "purpose": "...", "layer": "...", "patterns_used": [...]}
  ]
}
```

**Phase 5 Expected Schema** (Agent Specs):
```json
[
  {
    "name": "agent-name",
    "description": "...",
    "reason": "...",           // REQUIRED - missing in Phase 1 response
    "technologies": ["..."],   // REQUIRED - missing in Phase 1 response
    "priority": 9
  }
]
```

**Evidence from Log**:
```
⚠️  Skipping agent 1: "Missing required fields in agent spec: ['reason', 'technologies']"
⚠️  Skipping agent 2: "Missing required fields in agent spec: ['reason', 'technologies']"
... (6 total - matching the 6 layers in Phase 1 response)
```

The parsing logic attempted to interpret the `layers` array (6 items) as agent specs.

---

### Finding 3: Agent Scanner Reports Zero Agents

**Location**: [installer/global/commands/lib/template_create_orchestrator.py:901-904](installer/global/commands/lib/template_create_orchestrator.py#L901-L904)

**Log Evidence**:
```
Phase 5: Agent Recommendation
------------------------------------------------------------
📦 Scanning agent sources...

📊 Total: 0 agents available
```

**Analysis**: The `MultiSourceAgentScanner` found no existing agents because:
1. This is a fresh template creation (no prior agents exist)
2. Global agents are not being scanned, or
3. The scanner is not configured for this context

This is expected behavior for new templates, but worth noting.

---

### Finding 4: Phase 5 Never Actually Invokes AI

**Location**: [installer/global/lib/agent_bridge/invoker.py:165-167](installer/global/lib/agent_bridge/invoker.py#L165-L167)

**Evidence**: In the resume flow, Phase 5 never writes a new `.agent-request.json` because:
```python
def invoke(self, agent_name: str, prompt: str, ...) -> str:
    # If we already have a cached response (from --resume), use it
    if self._cached_response is not None:
        return self._cached_response  # Returns immediately - no new request
```

The log shows no exit code 42 between Phase 4.5 and Phase 5, confirming Phase 5 used cached data instead of invoking AI.

---

## Root Cause Analysis

```
┌─────────────────────────────────────────────────────────────┐
│              CHECKPOINT-RESUME DATA FLOW                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Phase 1: Codebase Analysis                                 │
│    ├── invoke("architectural-reviewer", CODEBASE_PROMPT)   │
│    ├── Exit 42 → .agent-request.json                       │
│    ├── [Claude invokes agent]                               │
│    ├── .agent-response.json written (CODEBASE FORMAT)      │
│    └── Resume: _cached_response = CODEBASE_DATA            │
│                                                             │
│  Phases 2-4.5: Run normally                                 │
│                                                             │
│  Phase 5: Agent Recommendation                              │
│    ├── invoke("architectural-reviewer", AGENT_PROMPT)      │
│    ├── ⚠️ _cached_response already set!                    │
│    ├── Returns CODEBASE_DATA (not AGENT_DATA)              │
│    └── Parse fails: layers interpreted as agent specs      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Root Cause**: The `AgentBridgeInvoker` was designed for single-invocation workflows but is used in multi-invocation workflows (Phase 1 + Phase 5). The single cache architecture doesn't support this pattern.

---

## Recommendations

### Recommendation 1: Implement Request-Specific Caching (CRITICAL)

**Priority**: P0 (Blocking)
**Effort**: Medium (4-6 hours)

Modify `AgentBridgeInvoker` to cache responses by request key (agent_name + prompt_hash):

```python
class AgentBridgeInvoker:
    def __init__(self, ...):
        self._response_cache: Dict[str, str] = {}  # key: hash(agent+prompt)

    def invoke(self, agent_name: str, prompt: str, ...) -> str:
        cache_key = self._make_cache_key(agent_name, prompt)
        if cache_key in self._response_cache:
            return self._response_cache[cache_key]
        # ... write request and exit 42

    def _make_cache_key(self, agent_name: str, prompt: str) -> str:
        import hashlib
        return hashlib.sha256(f"{agent_name}:{prompt}".encode()).hexdigest()[:16]
```

### Recommendation 2: Alternative - Separate Invoker Instances

**Priority**: P0 (Alternative)
**Effort**: Low (2-3 hours)

Create separate invoker instances for each phase with unique request/response files:

```python
# In orchestrator __init__
self.phase1_invoker = AgentBridgeInvoker(
    request_file=Path(".agent-request-phase1.json"),
    response_file=Path(".agent-response-phase1.json"),
    phase=1, phase_name="codebase_analysis"
)

self.phase5_invoker = AgentBridgeInvoker(
    request_file=Path(".agent-request-phase5.json"),
    response_file=Path(".agent-response-phase5.json"),
    phase=5, phase_name="agent_generation"
)
```

### Recommendation 3: Add Response Validation

**Priority**: P1 (Defensive)
**Effort**: Low (1-2 hours)

Add schema validation in Phase 5 to fail fast with clear error:

```python
def _parse_ai_agent_response(self, response: str, analysis: Any) -> List[CapabilityNeed]:
    # Validate this is agent spec format, not codebase analysis
    if '"example_files"' in response or '"layers"' in response:
        raise ValueError(
            "Received codebase analysis response instead of agent specs. "
            "This usually indicates a caching issue in the resume flow."
        )
    # ... existing parsing logic
```

### Recommendation 4: Add Integration Test

**Priority**: P2 (Prevention)
**Effort**: Medium (3-4 hours)

Create integration test that verifies Phase 5 receives correct response format after resume:

```python
def test_phase5_receives_agent_format_after_resume():
    """Verify Phase 5 doesn't receive Phase 1's cached response."""
    orchestrator = TemplateCreateOrchestrator(config)
    # Simulate checkpoint-resume with Phase 1 response loaded
    orchestrator.agent_invoker._cached_response = PHASE1_RESPONSE

    # Phase 5 should NOT use this cached response
    agents = orchestrator._phase5_agent_recommendation(analysis)

    # Verify agent format, not codebase format
    assert agents or "Agent generation invoked with correct prompt"
```

---

## Impact Assessment

| Aspect | Rating | Notes |
|--------|--------|-------|
| **Severity** | High | Complete feature failure |
| **Scope** | All resume workflows | Affects 100% of checkpoint-resume runs |
| **User Impact** | Templates missing agents | Requires manual agent creation |
| **Workaround Available** | Yes | Run with `--no-agents` flag |

---

## Files Requiring Changes

| File | Change Type | Priority |
|------|-------------|----------|
| [installer/global/lib/agent_bridge/invoker.py](installer/global/lib/agent_bridge/invoker.py) | Major refactor | P0 |
| [installer/global/commands/lib/template_create_orchestrator.py](installer/global/commands/lib/template_create_orchestrator.py) | Minor update | P0 |
| [installer/global/lib/agent_generator/agent_generator.py](installer/global/lib/agent_generator/agent_generator.py) | Validation | P1 |

---

## Decision Required

**Options**:

1. **[I]mplement** - Create implementation task to fix the caching architecture (Recommended)
2. **[A]ccept** - Document as known limitation, use `--no-agents` workaround
3. **[R]evise** - Need deeper analysis of multi-phase invoker patterns
4. **[C]ancel** - Issue not blocking enough to fix now

---

## Appendix: Supporting Evidence

### Execution Log Analysis

**Line 1158**: `📊 Total: 0 agents available` - Scanner found no existing agents
**Lines 1161-1166**: 6 agents skipped - Matches 6 layers in Phase 1 response
**Line 1167**: `AI returned no capability needs` - All parsed items were invalid
**Line 1079**: `WARNING:__main__:No agents directory found to create tasks for` - No agents to create

### Phase 1 Response Excerpt (from log)

```json
{
  "layers": [
    {"name": "Presentation Layer", ...},
    {"name": "Service Layer", ...},
    {"name": "Infrastructure Layer", ...},
    {"name": "State Management", ...},
    {"name": "Utility Layer", ...},
    {"name": "Backend Scripts", ...}
  ]
}
```

This 6-item `layers` array was parsed as agent specs, triggering validation failures for missing `reason` and `technologies` fields.
