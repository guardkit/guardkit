---
id: TASK-ENH-D960
title: Implement full AI agent invocation in template-create orchestrator
status: backlog
created: 2025-12-07T11:45:00Z
updated: 2025-12-07T11:45:00Z
priority: low
tags: [template-create, ai-integration, enhancement]
complexity: 7
related_tasks: [TASK-REV-7C49]
---

# Task: Implement Full AI Agent Invocation in Template-Create

## Description

The `/template-create` orchestrator currently falls back to heuristics when AI agent invocation fails. Implement proper AI agent invocation for architectural analysis during codebase analysis.

**Source**: Review finding from TASK-REV-7C49

## Current State

From template_create.md log:
```
WARNING:lib.codebase_analyzer.ai_analyzer:Agent invocation failed:
Unexpected error during agent invocation: Agent invocation not yet implemented.
Using fallback heuristics.
```

The bridge protocol works (as evidenced by the agent recommendations phase), but the codebase analysis phase doesn't use it.

## Target State

1. AI agent invocation works for codebase analysis
2. `architectural-reviewer` agent analyzes code patterns
3. Better layer classification from AI analysis
4. Reduced reliance on heuristic fallbacks

## Acceptance Criteria

- [ ] Agent invocation implemented in `lib/codebase_analyzer/ai_analyzer.py`
- [ ] Bridge protocol used for architectural-reviewer agent
- [ ] Fallback to heuristics still works when AI unavailable
- [ ] Analysis confidence improves from 68% to 80%+
- [ ] Integration tests pass

## Files to Modify

- `installer/scripts/lib/codebase_analyzer/ai_analyzer.py`
- `installer/scripts/lib/codebase_analyzer/agent_invoker.py`

## Implementation Notes

The bridge protocol is already implemented for Phase 5 (Agent Recommendation).
Reuse that pattern for Phase 1 (Codebase Analysis).

Current bridge protocol:
1. Write `.agent-request.json` with prompt
2. Exit with code 42 (checkpoint)
3. Claude invokes agent with prompt
4. Claude writes `.agent-response.json`
5. Resume orchestrator with `--resume`

## Estimated Effort

Complex (7-10 complexity) - Requires understanding of orchestrator architecture and bridge protocol.

## Priority Justification

Low priority because:
- Heuristic fallback works reasonably well (68% confidence)
- Bridge protocol is working for other phases
- Current implementation is functional for most use cases
