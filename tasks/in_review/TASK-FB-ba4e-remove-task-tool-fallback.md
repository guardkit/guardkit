---
id: TASK-FB-ba4e
title: "Remove Task Tool Fallback from /feature-build Skill"
status: in_review
priority: high
created: 2025-01-05
tags: [feature-build, autobuild, skill, cli]
complexity: 4
---

# Remove Task Tool Fallback from /feature-build Skill

## Description

The `/feature-build` skill currently has a fragile "Task tool fallback" that attempts to orchestrate Player-Coach loops using the Task tool with `autobuild-player` and `autobuild-coach` agents when the CLI is not available. This fallback is broken - Claude only invokes the Player agent without the Coach, breaking the adversarial cooperation pattern.

**Solution**: Implement Option C - require the CLI and remove the Task tool fallback entirely. The Python orchestrator (`guardkit autobuild task`) is fully implemented and tested (149+ tests). The skill should check CLI availability and display clear installation instructions if not found.

## Root Cause

The skill definition (lines 646-720 of `feature-build.md`) documents a loop that Claude should execute:
```
For turn = 1 to max_turns:
    1. INVOKE Task tool: subagent_type: "autobuild-player"
    2. WAIT for player completion
    3. INVOKE Task tool: subagent_type: "autobuild-coach"
    4. WAIT for coach completion
    5. IF approve: BREAK
```

However, Claude:
1. Does not interpret this as a loop it should execute
2. Only invokes the first agent (Player) and stops
3. Never invokes the Coach agent

This is a fundamental limitation of using skill markdown to describe complex multi-turn orchestration logic.

## Requirements

1. **Remove Task Tool Fallback**: Delete the "Step 2b: If CLI Not Available" section from the skill
2. **Require CLI**: The skill MUST use `guardkit autobuild task` CLI command
3. **Clear Error Message**: If CLI not available, show installation instructions instead of broken fallback
4. **Update Documentation**: Remove references to Task tool fallback in skill documentation

## Acceptance Criteria

- [ ] Task tool fallback section removed from `installer/core/commands/feature-build.md`
- [ ] Task tool fallback section removed from `~/.agentecflow/commands/feature-build.md`
- [ ] CLI availability check retained with clear error message
- [ ] Error message includes installation instructions: `pip install guardkit` or equivalent
- [ ] No references to `autobuild-player` subagent_type in skill execution instructions
- [ ] No references to `autobuild-coach` subagent_type in skill execution instructions
- [ ] Skill still documents the Player-Coach pattern (for understanding, not for Task tool execution)
- [ ] Tests pass for CLI-based execution path

## Implementation Notes

### Files to Modify

1. **`installer/core/commands/feature-build.md`** (source)
   - Remove lines ~646-720 (Task tool fallback loop)
   - Update "Step 2b" to show error message instead of fallback
   - Keep CLI execution path (Step 2a) as the only execution path

2. **Re-install to update user location**
   - After modifying source, run installer to update `~/.agentecflow/commands/feature-build.md`

### Error Message Template

```
══════════════════════════════════════════════════════════════
ERROR: GuardKit CLI Required
══════════════════════════════════════════════════════════════

The /feature-build command requires the GuardKit CLI to be installed.

The CLI provides the fully-tested Player-Coach adversarial loop with:
  • Promise-based completion verification
  • Honesty verification
  • Quality gate enforcement
  • State persistence and resume

Installation:
  pip install guardkit

  Or from source:
  cd ~/Projects/guardkit
  pip install -e .

After installation, verify:
  guardkit autobuild --help

Then retry:
  /feature-build TASK-XXX
══════════════════════════════════════════════════════════════
```

### What to Keep

- CLI execution path (`guardkit autobuild task TASK-XXX`)
- Feature mode execution (`guardkit autobuild feature FEAT-XXX`)
- All documentation about Player-Coach pattern (for user understanding)
- State persistence documentation
- Troubleshooting section (update as needed)

### What to Remove

- All "Step 2b" Task tool fallback code
- References to invoking `autobuild-player` via Task tool
- References to invoking `autobuild-coach` via Task tool
- The pseudo-code loop showing Task tool orchestration
- Any suggestion that the skill can work without CLI

## Related Files

- Review task: `tasks/backlog/TASK-REV-6d41-feature-build-implementation-gap.md`
- CLI implementation: `guardkit/cli/autobuild.py`
- Python orchestrator: `guardkit/orchestrator/autobuild.py`
- Agent invoker: `guardkit/orchestrator/agent_invoker.py`

## Testing

1. Verify `/feature-build TASK-XXX` works when CLI is available
2. Verify clear error message when CLI is NOT available
3. Verify no attempt to use Task tool fallback
4. Run existing integration tests: `python -m pytest tests/integration/test_autobuild_delegation.py -v`
