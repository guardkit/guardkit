---
id: TASK-REV-993B
title: Analyze template-create agent stub generation failure
status: review_complete
created: 2025-12-08T06:30:00Z
updated: 2025-12-08T06:30:00Z
priority: high
tags: [template-create, agent-generation, debugging, review]
task_type: review
complexity: 5
related_tasks: [TASK-IMP-D93B, TASK-FIX-29C1]
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Analyze template-create agent stub generation failure

## Description

Following the implementation of TASK-IMP-D93B, the `/template-create` command successfully generates template files but fails to create any agent stubs. This review task will analyze the root cause and recommend fixes.

## Context

**Execution Log**: [template_create.md](docs/reviews/progressive-disclosure/template_create.md)
**Output Location**: [kartlog template](docs/reviews/progressive-disclosure/kartlog/)

### Observed Behavior

1. **Template generation succeeded**: 25 template files created across 7 layers
2. **Agent generation failed**: 0 agents created, no `agents/` directory
3. **Error messages in log**:
   - `WARNING:__main__:No agents directory found to create tasks for` (line 1079)
   - Phase 5 showed 6 agents being skipped: `"Missing required fields in agent spec: ['reason', 'technologies']"` (lines 1161-1166)
   - `AI returned no capability needs` (line 1167)

### Phase 5 Output Analysis

```
Phase 5: Agent Recommendation
------------------------------------------------------------
📦 Scanning agent sources...

📊 Total: 0 agents available

🤖 Determining agent needs...
    ⚠️  Skipping agent 1: "Missing required fields in agent spec: ['reason', 'technologies']"
    ⚠️  Skipping agent 2: "Missing required fields in agent spec: ['reason', 'technologies']"
    ⚠️  Skipping agent 3: "Missing required fields in agent spec: ['reason', 'technologies']"
    ⚠️  Skipping agent 4: "Missing required fields in agent spec: ['reason', 'technologies']"
    ⚠️  Skipping agent 5: "Missing required fields in agent spec: ['reason', 'technologies']"
    ⚠️  Skipping agent 6: "Missing required fields in agent spec: ['reason', 'technologies']"
  ⚠️  AI returned no capability needs
  ✓ Identified 0 capability needs
  ✓ All capabilities covered by existing agents
  All capabilities covered by existing agents
```

### Expected vs Actual

| Aspect | Expected | Actual |
|--------|----------|--------|
| Template files | Generated | ✅ 25 files created |
| agents/ directory | Created with stubs | ❌ Not created |
| Agent stub files | 6-10 based on tech stack | ❌ 0 files |
| Enhancement tasks | Created if --create-agent-tasks | ❌ N/A (no agents) |

### Technology Stack Detected

The AI correctly identified the technology stack:
- Svelte 5 + Vite 7 + Firebase 10 + SMUI 8
- OpenAI integration + AlasSQL
- PWA support
- pytest/deepeval for testing

Expected agent stubs for this stack would include:
1. `svelte5-component-specialist.md`
2. `firebase-firestore-specialist.md`
3. `openai-chat-specialist.md`
4. `alasql-in-memory-database-specialist.md`
5. `pwa-vite-specialist.md`
6. `external-api-integration-specialist.md`

## Acceptance Criteria

- [ ] Root cause identified for agent stub generation failure
- [ ] Determine if issue is in AI response parsing or agent stub creation logic
- [ ] Assess if the "Missing required fields" error is from AI response format mismatch
- [ ] Recommend code fixes with specific file locations
- [ ] Verify completeness validator is not blocking agent creation
- [ ] Provide implementation task if fixes are needed

## Investigation Areas

### 1. AI Response Format
- Does the AI return agent recommendations in the expected JSON structure?
- Is `example_files` properly populated but agent specs missing `reason`/`technologies`?

### 2. Agent Stub Generation Logic
- Check `installer/core/commands/lib/template_create_orchestrator.py`
- Check agent recommendation/creation functions
- Verify the expected JSON schema for agent specs

### 3. Phase 5 Implementation
- Why does it report "0 agents available" when scanning?
- Why are all 6 returned agents being skipped?
- Is the AI prompt asking for the right fields?

### 4. Schema Validation
- What fields are required: `['reason', 'technologies']`
- What fields is the AI returning?
- Is there a schema version mismatch?

## Files to Review

- `installer/core/commands/lib/template_create_orchestrator.py`
- `installer/core/commands/lib/codebase_analyzer/`
- `installer/core/commands/lib/template_generator/`
- Agent-related prompts and response parsers

## Test Requirements

- [ ] Unit test for agent stub generation with mock AI response
- [ ] Integration test for full template-create with agent generation
- [ ] Test with valid agent spec format

## Implementation Notes

### REVISED: This is a REGRESSION from main branch

**CRITICAL FINDING**: TASK-ENH-D960 changed the Phase 1 architecture in a way that breaks the proven design on `main`.

### What Changed (TASK-ENH-D960)

| Aspect | main (Working) | progressive-disclosure (Broken) |
|--------|---------------|--------------------------------|
| Phase 1 Analysis | Heuristic (no AI) | AI via bridge invoker |
| Phase 5 AI | Works (only AI invocation) | Broken (uses Phase 1 cache) |
| Agent Generation | Working | Fails (0 agents) |

**On main branch** (working):
```python
# TASK-CHECKPOINT-FIX: Don't pass bridge_invoker here - Phase 1 uses heuristic analysis
# (Agent invocation only happens in Phase 5, where checkpoint is saved BEFORE invocation)
analyzer = CodebaseAnalyzer(
    max_files=10,
    bridge_invoker=None  # Heuristic fallback for Phase 1
)
```

**On progressive-disclosure** (broken):
```python
# TASK-ENH-D960: Enable AI agent invocation in Phase 1
analyzer = CodebaseAnalyzer(
    max_files=10,
    bridge_invoker=self.agent_invoker  # Enable AI invocation for Phase 1
)
```

### Why This Breaks Agent Generation

1. Phase 1 now invokes AI via bridge → Response cached
2. Resume loads response into `_cached_response`
3. Phase 5 tries to invoke AI with **different prompt**
4. Phase 5 receives Phase 1's cached response (wrong format!)
5. Parsing fails: codebase analysis JSON ≠ agent specs JSON

The design on `main` was **intentional** - the comment explicitly states:
> "Agent invocation only happens in Phase 5, where checkpoint is saved BEFORE invocation"

### Files Affected (TASK-ENH-D960 changes)

1. **[installer/core/commands/lib/template_create_orchestrator.py](installer/core/commands/lib/template_create_orchestrator.py)**
   - Lines 707-713: Changed `bridge_invoker=None` to `bridge_invoker=self.agent_invoker`
   - Lines 254-257: Added new Phase 1 resume path

### Quality Analysis: AI vs Heuristic Phase 1

**Important**: AI-powered Phase 1 provides SIGNIFICANT quality improvements:

| Aspect | Heuristic (main) | AI (progressive-disclosure) |
|--------|-----------------|----------------------------|
| Confidence Score | 75% (fixed) | 98% (dynamic) |
| Patterns Detected | Basic (folder names) | 9 detailed patterns |
| Layers | Generic detection | 6 layers with descriptions |
| Example Files | Simple selection | 20 files with patterns & concepts |
| Quality Assessment | 70/100 (fixed) | 78/100 with specific issues |
| Code Smells | None detected | 4 specific issues identified |

**Reverting would lose this quality improvement.**

### Recommended Fix

**Option A: Clear cache before Phase 5** (RECOMMENDED - Minimal change)

Add a `clear_cache()` method to `AgentBridgeInvoker` and call it at Phase 5 entry:

```python
# In AgentBridgeInvoker class (invoker.py):
def clear_cache(self) -> None:
    """Clear cached response to allow new AI invocation."""
    self._cached_response = None

# In _phase5_agent_recommendation() (template_create_orchestrator.py):
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

**Option B: Revert TASK-ENH-D960** (NOT recommended)
- Would lose the quality improvement from AI analysis
- The heuristic analysis is significantly weaker

**Option C: Separate invoker instances** (Overkill)
- More complex than needed
- The issue is just cache persistence, not architectural

### Full Analysis

See: [main-vs-progressive-disclosure-analysis.md](docs/reviews/progressive-disclosure/main-vs-progressive-disclosure-analysis.md)

### Review Report

Full report: [.claude/reviews/TASK-REV-993B-review-report.md](../../.claude/reviews/TASK-REV-993B-review-report.md)

## Decision Points

After review, decision options:
- [A]ccept - Findings approved, document and close
- [I]mplement - Create implementation task to fix the issue
- [R]evise - Need deeper analysis
- [C]ancel - Issue not reproducible or not a bug

---

## Review Outcome

**Decision**: [I]mplement

**Implementation Task Created**: [TASK-FIX-29C1](TASK-FIX-29C1-clear-agent-invoker-cache-phase5.md)

**Architecture Documentation Created**: [template-create-architecture.md](../../docs/architecture/template-create-architecture.md)

### Summary

1. **Root Cause**: AgentBridgeInvoker cache persists Phase 1 response, causing Phase 5 to receive wrong data format
2. **Fix**: Add `clear_cache()` method, call before Phase 5 (~5 lines)
3. **Quality Preserved**: AI-powered Phase 1 maintained (98% confidence vs 75% heuristic)
4. **Architecture Documented**: Evolution from V1 (single-phase AI) to V2 (multi-phase AI)

### Next Steps

1. `/task-work TASK-FIX-29C1` - Implement the cache clear fix
2. Test with kartlog codebase
3. Verify agents are generated
