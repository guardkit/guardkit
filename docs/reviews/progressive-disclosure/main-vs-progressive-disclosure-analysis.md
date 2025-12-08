# Main vs Progressive-Disclosure Branch Analysis

## Executive Summary

**CRITICAL FINDING**: The `progressive-disclosure` branch has fundamentally changed the Phase 1 architecture from the working `main` branch pattern. This change introduced a regression where Phase 5 agent generation no longer works.

**Root Cause**: TASK-ENH-D960 enabled AI agent invocation in Phase 1, but the single `AgentBridgeInvoker` instance cannot handle multiple AI invocations across different phases (Phase 1 for codebase analysis + Phase 5 for agent generation).

---

## Working Pattern (main branch)

### Phase 1: Codebase Analysis

**Location**: [template_create_orchestrator.py:634-639](installer/global/commands/lib/template_create_orchestrator.py#L634-L639)

```python
# TASK-CHECKPOINT-FIX: Don't pass bridge_invoker here - Phase 1 uses heuristic analysis
# (Agent invocation only happens in Phase 5, where checkpoint is saved BEFORE invocation)
analyzer = CodebaseAnalyzer(
    max_files=10,
    bridge_invoker=None  # Heuristic fallback for Phase 1
)
```

**Key Point**: On main, Phase 1 explicitly uses `bridge_invoker=None`, meaning:
- Phase 1 uses **heuristic analysis** (no AI invocation)
- No checkpoint-resume needed for Phase 1
- The `HeuristicAnalyzer` generates basic analysis from file patterns

### Phase 5: Agent Recommendation

**Location**: [template_create_orchestrator.py:828-832](installer/global/commands/lib/template_create_orchestrator.py#L828-L832)

```python
# CRITICAL: Pass AgentBridgeInvoker to generator (TASK-BRIDGE-002)
generator = AIAgentGenerator(
    inventory,
    ai_invoker=self.agent_invoker  # ← BRIDGE INTEGRATION
)
```

**Key Point**: On main, only Phase 5 uses the `AgentBridgeInvoker`:
- Phase 5 is the ONLY phase that invokes AI via bridge
- Checkpoint is saved at `templates_generated` (Phase 4)
- Exit code 42 triggers Claude to invoke agent
- Resume continues from Phase 5 with cached response

### Workflow on main

```
Phase 1: Heuristic Analysis (NO AI)
    └── Uses file patterns, no bridge invoker

Phase 2-4: Manifest, Settings, Templates
    └── All deterministic, no AI

Phase 4: Save checkpoint "templates_generated"

Phase 5: Agent Recommendation (AI INVOCATION)
    └── AgentBridgeInvoker.invoke() → Exit 42
    └── Claude invokes architectural-reviewer
    └── Resume: Cached response used by Phase 5

Phase 6-9: Complete workflow
```

---

## Changed Pattern (progressive-disclosure branch)

### TASK-ENH-D960 Changes

**Key Change #1**: Bridge invoker now passed to Phase 1

```python
# TASK-ENH-D960: Enable AI agent invocation in Phase 1
# Save checkpoint before analysis (may exit with code 42)
self._save_checkpoint("pre_ai_analysis", phase=WorkflowPhase.PHASE_1)

analyzer = CodebaseAnalyzer(
    max_files=10,
    bridge_invoker=self.agent_invoker  # Enable AI invocation for Phase 1
)
```

**Key Change #2**: New resume path for Phase 1

```python
if phase == WorkflowPhase.PHASE_1:
    return self._run_from_phase_1()  # NEW!
elif phase == WorkflowPhase.PHASE_7:
    return self._run_from_phase_7()
else:
    # Default to Phase 5 (backward compatibility)
    return self._run_from_phase_5()
```

**Key Change #3**: Phase metadata changed

```python
# BEFORE (main):
self.agent_invoker = AgentBridgeInvoker(
    phase=WorkflowPhase.PHASE_6,
    phase_name="agent_generation"
)

# AFTER (progressive-disclosure):
self.agent_invoker = AgentBridgeInvoker(
    phase=WorkflowPhase.PHASE_1,  # First use in Phase 1 (also used in Phase 6)
    phase_name="ai_analysis"
)
```

### Broken Workflow on progressive-disclosure

```
Phase 1: AI Codebase Analysis (NEW - AI INVOCATION)
    └── AgentBridgeInvoker.invoke() → Exit 42
    └── Claude invokes architectural-reviewer
    └── Resume: Cached response stored in _cached_response

Phase 2-4: Manifest, Settings, Templates
    └── Uses analysis from Phase 1

Phase 4: Save checkpoint "templates_generated"

Phase 5: Agent Recommendation (AI INVOCATION BROKEN!)
    └── AgentBridgeInvoker.invoke() called
    └── _cached_response already has Phase 1 data!
    └── Returns Phase 1 codebase analysis JSON
    └── Phase 5 parser fails: "Missing required fields: ['reason', 'technologies']"
```

---

## Technical Root Cause

The `AgentBridgeInvoker` class has a single `_cached_response` variable:

```python
class AgentBridgeInvoker:
    def __init__(self, ...):
        self._cached_response: Optional[str] = None  # SINGLE CACHE

    def invoke(self, agent_name: str, prompt: str, ...) -> str:
        # If we already have a cached response (from --resume), use it
        if self._cached_response is not None:
            return self._cached_response  # Returns Phase 1 response for ALL invocations!
```

When `progressive-disclosure` enabled AI in Phase 1:
1. Phase 1 invokes AI → Response cached
2. Resume loads the response into `_cached_response`
3. Phase 5 tries to invoke AI with a **different prompt**
4. Phase 5 receives Phase 1's cached response (wrong format!)
5. Parsing fails because codebase analysis JSON ≠ agent specs JSON

---

## Why This Matters

### Design Intent on main

The design on `main` was intentional:

```python
# TASK-CHECKPOINT-FIX: Don't pass bridge_invoker here - Phase 1 uses heuristic analysis
# (Agent invocation only happens in Phase 5, where checkpoint is saved BEFORE invocation)
```

This comment explicitly states:
- Phase 1 should use heuristic analysis
- Agent invocation should only happen in Phase 5
- The checkpoint-resume pattern was designed for single-phase AI invocation

### Breaking Change in progressive-disclosure

TASK-ENH-D960 broke this design by:
1. Enabling AI in Phase 1 (violates "only Phase 5")
2. Using the same `AgentBridgeInvoker` instance for both phases
3. Not considering that the cache would persist across phases

---

## Comparison Summary

| Aspect | main (Working) | progressive-disclosure (Broken) |
|--------|---------------|--------------------------------|
| Phase 1 Analysis | Heuristic (no AI) | AI via bridge invoker |
| Phase 1 Checkpoint | None | `pre_ai_analysis` |
| Phase 5 AI | Works (only AI invocation) | Broken (uses Phase 1 cache) |
| Agent Generation | Working | Fails (0 agents) |
| Resume Paths | Phase 5, Phase 7 | Phase 1, Phase 5, Phase 7 |
| Bridge Usage | Single phase | Multi-phase (broken) |

---

## REVISED Recommendation

### Quality Analysis: AI vs Heuristic Phase 1

| Aspect | Heuristic (main) | AI (progressive-disclosure) |
|--------|-----------------|----------------------------|
| Confidence Score | 75% (fixed) | 98% (dynamic) |
| Patterns Detected | Basic (folder names) | 9 detailed patterns |
| Layers | Generic detection | 6 layers with descriptions |
| Example Files | Simple selection | 20 files with patterns & concepts |
| Quality Assessment | 70/100 (fixed) | 78/100 with specific issues |
| Code Smells | None detected | 4 specific issues identified |

**Conclusion**: AI-powered Phase 1 analysis produces **significantly richer** results that lead to better templates.

### Recommended Fix: Clear Cache at Phase 5 Entry

**Option A: Clear cache before Phase 5** (RECOMMENDED - Minimal change)

Add a `clear_cache()` method to `AgentBridgeInvoker` and call it at Phase 5 entry:

```python
# In AgentBridgeInvoker class:
def clear_cache(self) -> None:
    """Clear cached response to allow new AI invocation."""
    self._cached_response = None

# In _phase5_agent_recommendation():
def _phase5_agent_recommendation(self, analysis: Any) -> List[Any]:
    self._print_phase_header("Phase 5: Agent Recommendation")

    # TASK-FIX-CACHE: Clear Phase 1 cached response before Phase 5 invocation
    self.agent_invoker.clear_cache()

    # ... rest of the method
```

**Benefits:**
- Minimal code change (~5 lines)
- Preserves AI-powered Phase 1 (quality improvement)
- Fixes Phase 5 agent generation
- Low risk of introducing new bugs

**Option B: Revert to main pattern** (NOT recommended)
- Would lose the quality improvement from AI analysis
- The heuristic analysis is significantly weaker

**Option C: Separate invoker instances** (Overkill)
- More complex than needed
- The issue is just cache persistence, not architectural

---

## Files to Review

1. **[installer/global/commands/lib/template_create_orchestrator.py](installer/global/commands/lib/template_create_orchestrator.py)**
   - Lines 634-639 (Phase 1 bridge_invoker change)
   - Lines 707-713 (checkpoint save before Phase 1)
   - Lines 254-257 (new Phase 1 resume path)

2. **[installer/global/lib/agent_bridge/invoker.py](installer/global/lib/agent_bridge/invoker.py)**
   - Lines 133, 165-167 (single _cached_response)

3. **[installer/global/lib/codebase_analyzer/agent_invoker.py](installer/global/lib/codebase_analyzer/agent_invoker.py)**
   - Lines 117-126 (bridge_invoker usage)

---

## Test Plan for Verification

If reverting to main pattern:
1. Run `/template-create` on a fresh codebase
2. Verify Phase 1 uses heuristic analysis (no exit 42)
3. Verify Phase 5 invokes AI (exit 42, then resume)
4. Verify agents are generated (non-zero count)
5. Verify agent files are created in `agents/` directory
