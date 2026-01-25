---
id: TASK-REV-6d41
title: "Review: /feature-build Implementation Gap Analysis"
type: review
status: backlog
priority: high
created: 2025-01-05
tags: [review, autobuild, adversarial-cooperation, feature-build]
---

# /feature-build Implementation Gap Analysis

## Summary

When testing `/feature-build`, Claude only invokes the Player agent (via Task tool with `autobuild-player`) without invoking the Coach agent. This contradicts the documented adversarial cooperation pattern and raises questions about what's actually wired up vs planned.

## Background

Significant work has been completed on the AutoBuild system:

### Implemented Components (Python)

1. **`guardkit/orchestrator/autobuild.py`** (1223 lines)
   - `AutoBuildOrchestrator` class with full Player-Coach loop
   - `orchestrate()` method that calls both Player AND Coach
   - `_execute_turn()` with proper dialectical flow
   - `_display_criteria_progress()` for promise-based verification

2. **`guardkit/orchestrator/agent_invoker.py`** (1568 lines)
   - `invoke_player()` with task-work delegation support
   - `invoke_coach()` with honesty verification
   - Promise-based verification methods
   - Acceptance criteria extraction

3. **`guardkit/orchestrator/schemas.py`** (347 lines)
   - `CompletionPromise` dataclass
   - `CriterionVerification` dataclass
   - `CriterionStatus` and `VerificationResult` enums
   - Utility functions for progress calculation

4. **`guardkit/cli/autobuild.py`** (597 lines)
   - `guardkit autobuild task TASK-XXX` command
   - `guardkit autobuild feature FEAT-XXX` command
   - Full CLI integration with options

5. **Agent Definitions**
   - `.claude/agents/autobuild-player.md` - With completion promises
   - `.claude/agents/autobuild-coach.md` - With promise verification

### The Gap

The `/feature-build` skill (`~/.agentecflow/commands/feature-build.md`) documents:

1. **Step 2a**: If CLI available → `guardkit autobuild task TASK-XXX` (uses Python)
2. **Step 2b**: If CLI NOT available → Use Task tool with `autobuild-player` and `autobuild-coach`

**Problem**: When Claude executes `/feature-build`, it appears to:
- Skip CLI check (or CLI not found)
- Use Task tool fallback
- Only invoke `autobuild-player` (NOT `autobuild-coach`)

This means the adversarial loop is broken when using the skill/command interface.

## Investigation Areas

### 1. CLI Availability
- Is `guardkit autobuild` in PATH when running from VS Code extension?
- Does the CLI check in the skill actually work?

### 2. Skill Execution
- How does Claude interpret the skill instructions?
- Is the Task tool fallback logic being followed correctly?
- Why is only Player invoked and not Coach?

### 3. Architecture Questions
- **Skill vs CLI**: Should `/feature-build` REQUIRE the CLI rather than have Task tool fallback?
- **Task tool limitations**: Can the Task tool properly orchestrate a multi-turn loop?
- **State management**: How does state persist between Player and Coach invocations in Task tool mode?

## Key Files to Review

1. `~/.agentecflow/commands/feature-build.md` - Skill definition (installed)
2. `installer/core/commands/feature-build.md` - Source skill definition
3. `guardkit/cli/autobuild.py` - CLI implementation
4. `guardkit/orchestrator/autobuild.py` - Python orchestrator
5. `guardkit/orchestrator/agent_invoker.py` - Agent invocation

## Related Backlog

These backlog directories exist but their relationship to current implementation is unclear:

1. `tasks/backlog/feature-build/` - Original feature-build planning
2. `tasks/backlog/feature-build-cli-native/` - Native CLI implementation
3. `tasks/backlog/autobuild-task-work-delegation/` - Task-work delegation (TWD tasks)

## Completed TWD Tasks

The following tasks were completed but may not be fully integrated:

- TASK-TWD-001: Task-work delegation in AgentInvoker
- TASK-TWD-002: Task state bridging for design_approved
- TASK-TWD-003: Feedback integration (marked complete)
- TASK-TWD-004: CLI mode parameter
- TASK-TWD-005: Integration tests
- TASK-TWD-006: Documentation updates
- TASK-TWD-007: Escape hatch pattern
- TASK-TWD-008: Honesty verification
- TASK-TWD-009: Promise-based completion verification

## Acceptance Criteria

1. Document the exact code path when `/feature-build TASK-XXX` is invoked
2. Identify why Coach agent is not being invoked
3. Determine if this is a skill definition bug or Claude interpretation issue
4. Recommend concrete fix(es) to restore adversarial loop
5. Verify that `guardkit autobuild task` CLI works correctly (Python path)
6. Clarify relationship between skill and CLI execution paths

## Recommendations (Preliminary)

Based on initial analysis:

1. **Option A: Require CLI** - Remove Task tool fallback from skill, require `guardkit autobuild` CLI
   - Pro: Uses fully tested Python orchestrator
   - Con: Requires guardkit CLI to be in PATH

2. **Option B: Fix Skill** - Ensure Task tool fallback properly invokes both Player AND Coach in a loop
   - Pro: Works without CLI
   - Con: Complex state management in skill definition

3. **Option C: Hybrid** - Try CLI first, if not available show error with installation instructions
   - Pro: Clear expectations
   - Con: Less flexible

## References

- Ralph Wiggum Analysis: Adversarial cooperation pattern from Block AI Research (g3)
- Review Report: `.claude/reviews/TASK-REV-RW01-review-report.md`
- AutoBuild Documentation: `CLAUDE.md` AutoBuild section
