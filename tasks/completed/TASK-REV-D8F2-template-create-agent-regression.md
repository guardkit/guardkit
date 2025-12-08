---
id: TASK-REV-D8F2
title: Review template-create agent generation regression post TASK-FIX-B016
status: completed
created: 2025-12-08T18:00:00Z
updated: 2025-12-08T19:30:00Z
priority: critical
task_type: review
tags: [template-create, regression, progressive-disclosure, agent-generation, ai-analysis]
complexity: 7
estimated_hours: 4-6
related_tasks: [TASK-FIX-B016, TASK-ENH-D960]
review_mode: decision
decision_required: true
review_results:
  mode: decision
  depth: standard
  score: 85
  findings_count: 4
  recommendations_count: 3
  decision: implement_option_b
  report_path: .claude/reviews/TASK-REV-D8F2-review-report.md
  completed_at: 2025-12-08T19:30:00Z
---

# Review: Template-Create Agent Generation Regression

## Context

Following the implementation of TASK-FIX-B016 (fix settings deserialization), the `/template-create` command now completes without errors but shows a **critical regression**: no AI agents are being generated.

### Evidence

**Previous Output** (before TASK-FIX-B016 - worked around error):
- Phase 5 executed successfully with AI invocation
- Generated 9 specialized agents (firebase-firestore-specialist, svelte5-component-specialist, etc.)
- Proper checkpoint-resume flow for both Phase 1 and Phase 5
- Template package included agents with boundary sections

**Current Output** (post TASK-FIX-B016):
```
Phase 5: Agent Recommendation
  💾 State saved (checkpoint: phase5_agent_request)
  ⚠️  Using heuristic agent generation (AI unavailable after 3 attempts)
  No agents generated (insufficient analysis data)

WARNING:__main__:No agents directory found to create tasks for
```

### Key Observations

1. **Maximum resume attempts reached**: "Maximum resume attempts reached (3)" → Falls back to heuristic
2. **Heuristic fallback produces nothing**: "No agents generated (insufficient analysis data)"
3. **Phase 1 AI works**: The codebase analysis completes with 91.67% confidence and 20 example files
4. **Phase 5 AI fails**: Agent generation falls back to heuristics and produces 0 agents

## Problem Analysis

From [main-vs-progressive-disclosure-analysis.md](docs/reviews/progressive-disclosure/main-vs-progressive-disclosure-analysis.md):

### Root Cause: Single AgentBridgeInvoker Cache for Multiple Phases

The `progressive-disclosure` branch enabled AI invocation in Phase 1 (TASK-ENH-D960), but the `AgentBridgeInvoker` has a **single `_cached_response` variable** that gets populated in Phase 1 and then incorrectly reused in Phase 5.

**Key Technical Issue**:
```python
class AgentBridgeInvoker:
    def __init__(self, ...):
        self._cached_response: Optional[str] = None  # SINGLE CACHE

    def invoke(self, agent_name: str, prompt: str, ...) -> str:
        # If we already have a cached response (from --resume), use it
        if self._cached_response is not None:
            return self._cached_response  # Returns Phase 1 response for Phase 5!
```

### Why the Regression Occurred

1. TASK-FIX-B016 fixed deserialization so Phase 9 no longer crashes
2. But Phase 5 now silently fails because:
   - The cache from Phase 1 is returned for the Phase 5 prompt
   - Phase 5 parser expects agent specs JSON but receives codebase analysis JSON
   - Parsing fails, triggers heuristic fallback
   - Heuristic has "insufficient analysis data" and generates 0 agents

### Comparison with Working `main` Branch

| Aspect | main (Working) | progressive-disclosure (Broken) |
|--------|---------------|--------------------------------|
| Phase 1 Analysis | Heuristic (no AI) | AI via bridge invoker |
| Phase 5 AI | Works (only AI invocation) | Broken (uses Phase 1 cache) |
| Agent Generation | Working | Fails (0 agents) |
| Resume attempts | 1 (for Phase 5) | 3 max (exhausted by Phase 1) |

## Scope of Review

### Critical Questions to Answer

1. **Cache Management**: How should the AgentBridgeInvoker handle multi-phase AI invocations?
   - Option A: Clear cache at Phase 5 entry (minimal change)
   - Option B: Use phase-specific cache files (implemented in TASK-FIX-7B74 but not working?)
   - Option C: Separate invoker instances per phase

2. **Resume Attempt Counter**: Why is `resume_attempt` reaching 3 when Phase 1 only needs 1?
   - Is the counter not being reset between phases?
   - Is there a bug in the checkpoint-resume logic?

3. **Heuristic Fallback**: Why does heuristic produce "insufficient analysis data"?
   - Phase 1 AI analysis completed successfully (20 example files, 91.67% confidence)
   - This analysis data should be available for heuristic agent generation

4. **Token Savings Goal**: How do we preserve the token savings from Progressive Disclosure?
   - Phase 1 AI analysis: Better quality than heuristic (98% vs 75% confidence)
   - Must NOT revert to heuristic-only Phase 1
   - Goal is AI for both phases, with proper cache isolation

## Files to Investigate

### Primary Files

1. **[installer/global/commands/lib/template_create_orchestrator.py](installer/global/commands/lib/template_create_orchestrator.py)**
   - Phase 1 AI invocation logic (lines ~634-700)
   - Phase 5 agent recommendation (lines ~1200-1350)
   - Resume path routing (lines ~250-270)
   - Checkpoint save/restore logic

2. **[installer/global/lib/agent_bridge/invoker.py](installer/global/lib/agent_bridge/invoker.py)**
   - `_cached_response` handling
   - Phase-specific cache file logic (added in TASK-FIX-7B74)
   - Resume attempt counter

3. **[installer/global/lib/codebase_analyzer/agent_invoker.py](installer/global/lib/codebase_analyzer/agent_invoker.py)**
   - Bridge invoker usage in Phase 1

### Related Commits

```
982c255 Implemented TASK-FIX-E5F6, reviews and new tasks
a10c1b6 Implemented TASK-FIX-7B74 & TASK-FIX-6855
6e9479f Complete TASK-FIX-7B74: Phase-specific cache files for multi-phase AI invocation
8c2b1b4 Clear agent response cache in Phase 5 template-create
6a67215 Fix for resume flow regression
2ad807b Complete TASK-ENH-D960: Implement AI agent invocation in Phase 1
```

## Comparison Evidence

### Previous Output (Worked)

From [template_create_previous.md](docs/reviews/progressive-disclosure/template_create_previous.md):
```
Phase 5: Agent Recommendation
  ✓ AI identified 9 capability needs
  → Generating: firebase-firestore-specialist (confidence: 85%)
  → Generating: svelte5-component-specialist (confidence: 85%)
  ...
  Generated 9 custom agents
```

### Current Output (Broken)

From [template_create.md](docs/reviews/progressive-disclosure/template_create.md):
```
Phase 5: Agent Recommendation
  ⚠️  Using heuristic agent generation (AI unavailable after 3 attempts)
  No agents generated (insufficient analysis data)
```

## Decision Framework

### Option A: Clear Cache at Phase 5 Entry

**Pros**:
- Minimal code change (~5 lines)
- Preserves AI-powered Phase 1
- Low risk

**Cons**:
- Doesn't address root cause (shared state)
- May need similar fixes for future phases

### Option B: Fix Phase-Specific Cache Files (TASK-FIX-7B74)

**Pros**:
- Already partially implemented
- Architecturally clean separation

**Cons**:
- More complex
- Need to understand why it's not working

### Option C: Separate Invoker Instances

**Pros**:
- Complete isolation
- Future-proof

**Cons**:
- More invasive change
- Higher risk of breaking other functionality

## Acceptance Criteria

- [ ] Root cause definitively identified
- [ ] Solution option selected with rationale
- [ ] Impact on token savings assessed
- [ ] Implementation task created if [I]mplement selected
- [ ] Regression test plan documented

## Guiding Principles

**FROM CLAUDE.md**:
> The whole premise of this is to use AI to analyse the codebase and generate templates and subagent definitions and **not to use heuristics**.

**Goal**: AI-powered analysis in both Phase 1 AND Phase 5, with Progressive Disclosure token savings preserved.

---

*Review requested by user*
*Critical priority: Blocks /template-create functionality*
