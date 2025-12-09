---
id: TASK-FIX-PD05
title: Fix /agent-enhance progressive disclosure split bypass
status: backlog
task_type: implementation
created: 2025-12-09
priority: high
tags: [progressive-disclosure, agent-enhance, bug-fix, critical]
related_tasks: [TASK-FIX-PD04, TASK-REV-AB89, TASK-FIX-PD03]
estimated_complexity: 5
---

# TASK-FIX-PD05: Fix /agent-enhance Progressive Disclosure Split Bypass

## Summary

The `/agent-enhance` command is not creating split files (core + extended) because Claude Code interprets the markdown command specification and directly invokes the `agent-content-enhancer` via Task tool, bypassing the Python orchestrator that contains the split logic.

## Root Cause Analysis

### Expected Flow (Python script)
```
/agent-enhance command
    → agent-enhance.py (Python script)
    → AgentEnhanceOrchestrator.run()
    → SingleAgentEnhancer.enhance()
    → AI returns JSON
    → applier.apply_with_split()
    → Creates core.md + extended.md
```

### Actual Flow (Claude Code)
```
/agent-enhance command
    → Claude reads markdown command spec
    → Claude invokes Task tool with agent-content-enhancer
    → agent-content-enhancer reads templates
    → agent-content-enhancer writes DIRECTLY to file (using Write tool)
    → Returns "Done"
    → NO SPLIT HAPPENS
```

### Evidence

From session log:
```
⏺ agent-content-enhancer(Enhance Svelte5 component agent)
  ⎿  Done (0 tool uses · 15.7k tokens · 2m 56s)

⏺ Write(.agentecflow/templates/kartlog/agents/svelte5-component-specialist.md)
  ⎿  Updated with 539 additions and 11 removals
```

The agent wrote directly to the file instead of returning JSON for the orchestrator to process.

## Acceptance Criteria

### AC1: Identify Root Bypass Point
- [ ] Determine why Claude Code bypasses Python script
- [ ] Check if slash command is being interpreted vs executed
- [ ] Verify symlink is correctly set up

### AC2: Option A - Fix Command Invocation
- [ ] Ensure slash command runs Python script, not markdown interpretation
- [ ] Test that Python orchestrator receives control
- [ ] Verify split logic executes

### AC3: Option B - Add Post-Agent Split (Alternative)
- [ ] Modify agent-content-enhancer to return JSON only
- [ ] Add explicit "DO NOT WRITE" instruction in Task prompt
- [ ] Add post-processing step in markdown command to apply split

### AC4: Option C - Inline Split in Command (Alternative)
- [ ] Add split logic to markdown command specification
- [ ] After agent-content-enhancer returns, parse monolithic file
- [ ] Apply split using Python utility or inline logic

### AC5: Verification
- [ ] Run `/agent-enhance template/agent --hybrid`
- [ ] Verify TWO files created: `agent.md` and `agent-ext.md`
- [ ] Verify extended file contains 50+ lines
- [ ] Verify core file has loading instruction pointing to extended

## Investigation Notes

### Key Files
- `installer/global/commands/agent-enhance.md` - Command specification
- `installer/global/commands/agent-enhance.py` - Python script (has correct split logic)
- `installer/global/agents/agent-content-enhancer.md` - Agent definition
- `installer/global/lib/agent_enhancement/orchestrator.py` - Orchestrator with split logic
- `installer/global/lib/agent_enhancement/applier.py` - Applier with EXTENDED_SECTIONS

### agent-content-enhancer Instructions (Ignored)
The agent file clearly states:
```markdown
**CRITICAL: JSON-ONLY RESPONSE**

This agent MUST return enhancement content as a JSON object. It MUST NOT write to files directly.

- **DO**: Return JSON with sections and content
- **DO NOT**: Use Write tool, Edit tool, or any file modification
```

But when spawned via Task tool, Claude Code ignores the `tools: [Read, Grep, Glob]` restriction and uses Write anyway.

### TASK-FIX-PD04 Changes Are Correct But Not Triggered
The changes made in TASK-FIX-PD04 to `applier.py` are correct:
- EXTENDED_SECTIONS now includes `examples` and `related_templates`
- section_order includes new sections
- But these changes never execute because the flow bypasses Python

## Proposed Solutions

### Solution 1: Make Slash Command Run Python (Recommended)

Ensure `/agent-enhance` executes the Python script instead of being interpreted by Claude Code.

This may require:
- Checking how slash commands are registered
- Verifying symlink execution path
- Adding explicit `python3` invocation

### Solution 2: Post-Processing in Command Spec

Add explicit post-processing step to `agent-enhance.md`:

```markdown
## Post-Enhancement Split

AFTER the agent-content-enhancer returns:
1. Check if extended file exists
2. If not, run Python split utility:
   ```bash
   python3 ~/.agentecflow/bin/agent-enhance-split {agent_file}
   ```
```

### Solution 3: Enforce JSON Response via Task Prompt

Modify Task tool prompt to explicitly forbid file writes:

```
IMPORTANT: Return JSON response ONLY. DO NOT use Write or Edit tools.
All file operations are handled by the orchestrator.
```

## Test Command

After fix, run:
```bash
/agent-enhance docs/reviews/progressive-disclosure/kartlog/agents/svelte5-component-specialist.md --hybrid
```

Expected:
- `svelte5-component-specialist.md` - Core file (~150 lines)
- `svelte5-component-specialist-ext.md` - Extended file (~300 lines)

## Priority Justification

HIGH - This bug means progressive disclosure (a key GuardKit feature for context optimization) is completely broken for AI-strategy enhancements. Users expecting token savings are getting monolithic files instead.
