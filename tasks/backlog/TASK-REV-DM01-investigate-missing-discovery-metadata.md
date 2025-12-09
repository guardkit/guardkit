---
id: TASK-REV-DM01
title: Investigate missing discovery metadata in agent-enhance output
status: review_complete
task_type: review
review_mode: code-quality
created: 2025-12-09
priority: high
tags: [review, agent-enhance, discovery-metadata, progressive-disclosure, root-cause]
related_tasks: [TASK-REV-A36C, TASK-ENH-DM01]
estimated_complexity: 4
review_results:
  mode: code-quality
  depth: standard
  findings_count: 6
  recommendations_count: 5
  decision: implement
  report_path: .claude/reviews/TASK-REV-DM01-review-report.md
  completed_at: 2025-12-09T20:00:00Z
---

# TASK-REV-DM01: Investigate Missing Discovery Metadata in Agent-Enhance Output

## Summary

The `/agent-enhance` command is not generating discovery metadata (`stack`, `phase`, `capabilities`, `keywords`) in agent frontmatter. This review task investigates the root cause by analyzing:
1. The agent-enhance command implementation
2. The agent-content-enhancer agent prompt
3. The orchestrator logic
4. The actual command output logs

## Review Context

### Evidence from TASK-REV-A36C

- 6/7 kartlog agents missing all discovery metadata fields
- Only `svelte-list-view-specialist` has complete metadata (possibly added manually)
- All agents have correct boundaries and extended content
- Issue is specifically in frontmatter generation, not content generation

### Source Directories

**Generated Agent Files** (final output):
- Location: `docs/reviews/progressive-disclosure/kartlog/agents/`
- Contains: 7 agent pairs (core + extended)
- Issue: Missing `stack`, `phase`, `capabilities`, `keywords` in frontmatter

**Command Output Logs** (enhancement session transcripts):
- Location: `docs/reviews/progressive-disclosure/agent-enhance-output/`
- Contains: 7 session logs showing the enhancement process
- Purpose: Analyze what the agent-content-enhancer actually returned

## Review Objectives

### Primary Questions

1. **Is discovery metadata requested in the agent-content-enhancer prompt?**
   - Check `installer/global/agents/agent-content-enhancer.md`
   - Look for instructions to generate `stack`, `phase`, `capabilities`, `keywords`

2. **Does the AgentResponse schema include discovery metadata fields?**
   - Check response format expectations
   - Verify if fields are defined but not populated vs not defined at all

3. **Is the orchestrator stripping or ignoring metadata?**
   - Check `installer/global/lib/agent_enhancement/orchestrator.py`
   - Look for frontmatter handling logic

4. **What does the agent-content-enhancer actually return?**
   - Analyze command output logs in `agent-enhance-output/`
   - Check if AI returns metadata that gets lost, or never generates it

### Secondary Questions

5. **Why does svelte-list-view-specialist have complete metadata?**
   - Was it manually added?
   - Was there a different code path?

6. **Is there a timing/order dependency?**
   - Does metadata generation depend on other enhancement phases?

## Files to Review

### Primary Investigation Targets

| File | Purpose |
|------|---------|
| `installer/global/agents/agent-content-enhancer.md` | Agent prompt - check for metadata instructions |
| `installer/global/lib/agent_enhancement/orchestrator.py` | Orchestration logic - check frontmatter handling |
| `installer/global/lib/agent_bridge/invoker.py` | Request/response handling |
| `installer/global/commands/agent-enhance.md` | Command specification |

### Evidence Sources

| File | Purpose |
|------|---------|
| `docs/reviews/progressive-disclosure/agent-enhance-output/*.md` | Command session logs |
| `docs/reviews/progressive-disclosure/kartlog/agents/*.md` | Final output files |

### Reference Files

| File | Purpose |
|------|---------|
| `docs/reviews/progressive-disclosure/kartlog/agents/svelte-list-view-specialist.md` | Agent WITH complete metadata (control) |
| `docs/reviews/progressive-disclosure/kartlog/agents/firestore-repository-specialist.md` | Agent WITHOUT metadata (example) |

## Acceptance Criteria

### AC1: Root Cause Identified
- [ ] Determine exactly where metadata generation fails
- [ ] Document the code path from request to final file
- [ ] Identify if this is a prompt issue, schema issue, or processing issue

### AC2: Evidence Collected
- [ ] Analyze agent-enhance-output logs for metadata presence/absence
- [ ] Compare svelte-list-view-specialist vs other agents
- [ ] Document what the AI actually returns

### AC3: Fix Location Identified
- [ ] Identify specific file(s) to modify
- [ ] Determine if fix is in prompt, schema, or orchestrator
- [ ] Assess complexity of fix

### AC4: Recommendations Documented
- [ ] Provide specific fix recommendations with code locations
- [ ] Estimate implementation complexity
- [ ] Identify any related issues discovered

## Review Checklist

### Phase 1: Prompt Analysis
- [ ] Read agent-content-enhancer.md fully
- [ ] Search for "stack", "phase", "capabilities", "keywords" mentions
- [ ] Check if frontmatter generation is specified
- [ ] Document findings

### Phase 2: Schema Analysis
- [ ] Check AgentResponse schema definition
- [ ] Check if discovery fields are defined
- [ ] Check request format for metadata requirements
- [ ] Document findings

### Phase 3: Orchestrator Analysis
- [ ] Trace frontmatter handling in orchestrator.py
- [ ] Check if metadata is passed through or filtered
- [ ] Check final file writing logic
- [ ] Document findings

### Phase 4: Output Log Analysis
- [ ] Read 2-3 agent-enhance-output logs
- [ ] Check if AI mentions/returns discovery metadata
- [ ] Compare against final generated files
- [ ] Document discrepancies

### Phase 5: Control Comparison
- [ ] Analyze how svelte-list-view-specialist got its metadata
- [ ] Check git history if available
- [ ] Identify any different code path

## Recommended Review Mode

```bash
/task-review TASK-REV-DM01 --mode=code-quality --depth=standard
```

## Expected Outcomes

1. **Root cause identification** - Specific location where metadata generation fails
2. **Fix recommendation** - Concrete changes to implement
3. **Updated TASK-ENH-DM01** - Implementation task updated with findings

## Definition of Done

- [ ] Root cause clearly identified with evidence
- [ ] Code path documented (request → AI → response → file)
- [ ] Specific fix location(s) identified
- [ ] TASK-ENH-DM01 updated with implementation details
- [ ] Review report generated
