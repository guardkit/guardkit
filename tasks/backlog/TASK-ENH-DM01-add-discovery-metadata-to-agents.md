---
id: TASK-ENH-DM01
title: Fix agent-enhance to generate discovery metadata in frontmatter
status: backlog
task_type: implementation
created: 2025-12-09
priority: medium
tags: [bug, agent-enhance, discovery, metadata, progressive-disclosure]
related_tasks: [TASK-REV-A36C]
estimated_complexity: 4
source_review: TASK-REV-A36C
---

# TASK-ENH-DM01: Fix Agent-Enhance Discovery Metadata Generation

## Summary

The `/agent-enhance` command is not generating discovery metadata (`stack`, `phase`, `capabilities`, `keywords`) in agent frontmatter. Only 1 of 7 kartlog agents (`svelte-list-view-specialist`) has this metadata - likely added manually or through a different code path.

This metadata is required for AI-powered agent matching during `/task-work`.

## Root Cause Investigation

The agent-content-enhancer or orchestrator is not:
1. Analyzing the template to infer stack/technologies
2. Generating capabilities from the agent's purpose and boundaries
3. Extracting keywords from the agent's domain
4. Setting the phase based on agent type

## Evidence

From TASK-REV-A36C review:
- 6/7 agents missing all discovery metadata fields
- Only `svelte-list-view-specialist` has complete metadata
- All agents have correct boundaries and extended content, just missing frontmatter fields

## Acceptance Criteria

### AC1: Discovery Metadata Generation
- [ ] `stack` array generated from template technologies and agent technologies field
- [ ] `phase` value inferred from agent type (implementation/testing/review)
- [ ] `capabilities` array generated from agent purpose and boundary analysis
- [ ] `keywords` array generated from agent name, technologies, and domain

### AC2: Metadata Quality
- [ ] Generated stack values match actual technologies
- [ ] Capabilities are specific (not generic phrases)
- [ ] Keywords cover searchable terms for the domain

### AC3: Backward Compatibility
- [ ] Existing metadata in frontmatter is preserved (not overwritten)
- [ ] Enhancement works for agents with partial metadata

## Files to Investigate

Primary (likely location of fix):
- `installer/global/agents/agent-content-enhancer.md` - Agent prompt that generates content
- `installer/global/lib/agent_enhancement/orchestrator.py` - Orchestration logic

Secondary:
- `installer/global/lib/agent_enhancement/` - Supporting modules
- `installer/global/lib/codebase_analyzer/` - Template analysis utilities

## Implementation Approach

### Option A: Enhance agent-content-enhancer prompt
Add instructions to the agent prompt to analyze and generate discovery metadata:
```markdown
## Discovery Metadata Generation

Analyze the agent and template to generate frontmatter metadata:

1. **stack**: Infer from technologies field and template file extensions
2. **phase**: Set based on agent purpose (implementation/testing/review/orchestration)
3. **capabilities**: Extract 5-7 specific capabilities from purpose and boundaries
4. **keywords**: Generate 8-12 searchable terms from agent domain
```

### Option B: Add post-processing in orchestrator
After agent enhancement, analyze the generated content and add metadata programmatically.

**Recommended**: Option A - keeps all generation logic in one place (the agent prompt).

## Testing

1. Run `/agent-enhance` on a test agent without discovery metadata
2. Verify all 4 metadata fields are generated
3. Verify metadata quality matches agent domain
4. Test with agent that has partial metadata (should preserve existing)

## Definition of Done

- [ ] `/agent-enhance` generates all 4 discovery metadata fields
- [ ] Generated metadata is accurate for agent domain
- [ ] Existing metadata is not overwritten
- [ ] Re-running on kartlog agents produces complete metadata
