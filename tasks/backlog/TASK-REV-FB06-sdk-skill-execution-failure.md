---
id: TASK-REV-FB06
title: "Review: SDK Skill Execution Failure in Feature-Build"
status: in_review
created: 2026-01-11T18:00:00Z
updated: 2026-01-11T18:45:00Z
priority: critical
task_type: review
review:
  mode: decision
  depth: comprehensive
  focus: sdk-skill-integration
tags:
  - feature-build
  - sdk
  - skill-execution
  - critical
  - debugging
complexity: 7
parent_reviews:
  - TASK-REV-FB01
  - TASK-REV-fb02
  - TASK-REV-fb03
  - TASK-REV-FB04
  - TASK-REV-FB05
related_fixes:
  - TASK-FB-FIX-001  # TaskWorkInterface SDK integration
  - TASK-FB-FIX-002  # Plan validation in pre-loop
  - TASK-FB-FIX-003  # Centralized path logic
  - TASK-FB-FIX-004  # (unknown)
  - TASK-FB-FIX-005  # ContentBlock parsing fix (completed)
---

# TASK-REV-FB06: SDK Skill Execution Failure in Feature-Build

## Executive Summary

After 5 previous reviews and 5 fix implementations, the feature-build command still fails. **TASK-FB-FIX-005 fixed ContentBlock parsing but that was NOT the root cause.** The SDK executes for only 1 turn and the `/task-work --design-only` skill produces no output.

## Problem Statement

The feature-build command fails with `PRE_LOOP_BLOCKED`:
```
ERROR: Quality gate 'plan_generation' blocked: Design phase did not return plan path for TASK-INFRA-001
```

**Despite**:
- ContentBlock parsing fix applied (TASK-FB-FIX-005)
- SDK invocation works (connects, executes, returns)
- Worktree is created correctly

## Critical Evidence

### From failure_after_task_rev_fb05.md

```
INFO:guardkit.orchestrator.quality_gates.task_work_interface:Executing via SDK: /task-work TASK-INFRA-001 --design-only
INFO:guardkit.orchestrator.quality_gates.task_work_interface:Working directory: .../.guardkit/worktrees/FEAT-3DEB
INFO:claude_agent_sdk._internal.transport.subprocess_cli:Using bundled Claude Code CLI: ...
INFO:guardkit.orchestrator.quality_gates.task_work_interface:SDK completed: turns=1
INFO:guardkit.orchestrator.quality_gates.task_work_interface:SDK execution completed for design phase
ERROR:guardkit.orchestrator.autobuild:Pre-loop quality gate blocked: Design phase did not return plan path
```

**Key Observation: `turns=1` means the skill invocation returned almost immediately without doing any actual work.**

### From task_work_interface.py (lines 339-372)

The SDK invocation code is correct:
```python
options = ClaudeAgentOptions(
    cwd=str(self.worktree_path),
    allowed_tools=["Read", "Write", "Edit", "Bash", "Grep", "Glob", "Task", "Skill"],
    permission_mode="acceptEdits",
    max_turns=50,  # Design phases can take many turns
    setting_sources=["project"],  # Load CLAUDE.md from worktree
)

collected_output: List[str] = []
async with asyncio.timeout(self.sdk_timeout_seconds):
    async for message in query(prompt=prompt, options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    collected_output.append(block.text)
```

### Missing Pieces

1. **Skill Not Available**: The `/task-work` skill may not be registered in the test repository
2. **Worktree Context Missing**: The worktree may lack required CLAUDE.md or skill configuration
3. **SDK Silent Failure**: The SDK returns "1 turn completed" but no actual execution happened

## Review Objectives

1. **Understand why SDK completes in 1 turn** without executing the skill
2. **Verify skill availability** in the worktree context
3. **Examine SDK debug logging** to see what the first turn actually does
4. **Identify the actual root cause** after 5 failed attempts

## Investigation Plan

### Phase 1: SDK Execution Analysis

1. Add debug logging to capture the actual response content from the 1-turn execution
2. Check if the SDK is returning an error or empty response
3. Verify the `prompt` being sent: `/task-work TASK-INFRA-001 --design-only`

### Phase 2: Skill Availability Check

1. Verify `/task-work` skill exists in test repository
2. Check if skill is in `~/.agentecflow/commands/` and symlinked correctly
3. Verify the worktree has access to skills (not sandboxed away)

### Phase 3: Worktree Context Check

1. Verify CLAUDE.md exists in worktree
2. Check if skills are loaded via `setting_sources=["project"]`
3. Test manual `/task-work` execution in worktree

### Phase 4: SDK vs Manual Comparison

1. Run `/task-work TASK-INFRA-001 --design-only` manually in worktree
2. Compare output to SDK execution
3. Identify any differences in environment/context

## Previous Review Analysis

| Review | Finding | Fix | Outcome |
|--------|---------|-----|---------|
| FB01 | Architecture OK | N/A | Approved |
| fb02 | task_work_results missing | Unknown | Incomplete |
| fb03 | CLI command doesn't exist | Unknown | Incomplete |
| FB04 | Design phase gap | TASK-FB-FIX-001-004 | Incomplete |
| FB05 | ContentBlock parsing | TASK-FB-FIX-005 | Applied but issue persists |

**Pattern**: Each review identified a symptom, not the root cause.

## Hypotheses to Test

### H1: Skill Not Registered
The `/task-work` skill may not be available in the bundled Claude Code CLI that the SDK uses.

**Test**: Check what skills are available via SDK introspection.

### H2: Permission Mode Blocks Skill
The `permission_mode="acceptEdits"` may not allow skill invocation.

**Test**: Try `permission_mode="acceptAll"` or check skill permissions.

### H3: Worktree Isolation
The worktree may be missing the skill registration that exists in the main repo.

**Test**: Compare skill availability between main repo and worktree.

### H4: SDK Max Turns Misconfigured
Despite setting `max_turns=50`, the SDK may have a lower internal limit for skill execution.

**Test**: Check SDK documentation for skill-specific turn limits.

### H5: Prompt Not Recognized as Skill
The prompt `/task-work TASK-INFRA-001 --design-only` may not be recognized as a skill invocation.

**Test**: Check if the SDK expects a different format (e.g., without leading `/`).

## ROOT CAUSE IDENTIFIED

### The Issue

The SDK is configured with `setting_sources=["project"]` but should be `setting_sources=["user", "project"]`.

**Current Code** (`task_work_interface.py:344`):
```python
setting_sources=["project"],  # Only loads from .claude/ in worktree
```

**Required Fix**:
```python
setting_sources=["user", "project"],  # Load from ~/.claude/ AND .claude/
```

### Why This Matters

1. **Skills are at `~/.claude/commands/`** - symlinked from `~/.agentecflow/commands/`
2. **SDK only loads project settings** - misses user-level skills entirely
3. **Model can't invoke `/task-work`** - skill not available in context
4. **Execution completes in 1 turn** - model responds but can't use skill

### Secondary Issue

The SDK expects skills in `~/.claude/skills/*/SKILL.md` format, but GuardKit uses:
- `~/.claude/commands/task-work.md` (file, not directory)

This may require either:
1. Converting commands to skill format (`~/.claude/skills/task-work/SKILL.md`)
2. OR verifying the SDK can read commands as skills

## Required Actions

1. **Fix setting_sources** to include `"user"` (HIGH PRIORITY)
2. Verify skill format compatibility
3. Add debug logging to capture actual SDK response content
4. Test fix in actual feature-build

## Success Criteria

- [x] Root cause definitively identified (setting_sources missing "user")
- [x] Fix implemented in task_work_interface.py (line 346)
- [ ] Fix verified in actual feature-build test
- [ ] 100% confidence this is the last fix needed

## Fix Applied

TASK-FB-FIX-006 has been implemented:

```python
# guardkit/orchestrator/quality_gates/task_work_interface.py:344-346
# TASK-FB-FIX-006: Include "user" to load skills from ~/.claude/commands/
# Without "user", the SDK can't find /task-work skill
setting_sources=["user", "project"],
```

Also added debug logging (lines 374-380) to capture output length and preview for future debugging.

## Evidence Files

- `docs/reviews/feature-build/failure_after_task_rev_fb05.md` - Latest failure output
- `docs/reviews/feature-build/previous_review_and_tasks.md` - Review history
- `.claude/reviews/TASK-REV-FB05-review-report.md` - ContentBlock fix analysis
- `guardkit/orchestrator/quality_gates/task_work_interface.py` - Current implementation

## Notes

This is review #6 on the same issue. The focus must be on finding the ACTUAL root cause, not another symptom. The ContentBlock parsing fix (FB-FIX-005) was technically correct but addressed a downstream issue - the upstream issue is that the SDK isn't executing the skill at all.
