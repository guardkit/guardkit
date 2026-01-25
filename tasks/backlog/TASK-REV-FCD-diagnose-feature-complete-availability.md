---
id: TASK-REV-FCD
title: Diagnose feature-complete command availability
status: review_complete
created: 2026-01-24T12:00:00Z
updated: 2026-01-24T16:30:00Z
priority: high
tags: [debugging, cli, skill-registration, feature-complete]
task_type: review
complexity: 4
review_results:
  mode: decision
  depth: standard
  findings_count: 4
  recommendations_count: 3
  decision: implement
  report_path: .claude/reviews/TASK-REV-FCD-review-report.md
  completed_at: 2026-01-24T16:30:00Z
---

# Task: Diagnose feature-complete command availability

## Problem Statement

The `/feature-complete` command was implemented earlier today (tasks/backlog/feature-complete/) but is **not available** in either:
1. **CLI**: `guardkit feature complete FEAT-XXX` returns "Unknown command: feature"
2. **Claude Code**: `/feature-complete FEAT-XXX` returns "Unknown skill: feature-complete"

The implementation appears complete:
- Orchestrator: `guardkit/orchestrator/feature_complete.py` exists
- CLI subcommand: `guardkit autobuild complete` exists (autobuild.py:641-722)
- Tests: `tests/orchestrator/test_feature_complete*.py` exist

## Symptoms Observed

```bash
# CLI attempts
guardkit feature complete FEAT-FHE
# Output: Unknown command: feature

guardkit feature-complete FEAT-FHE
# Output: Unknown command: feature-complete

# Claude Code attempt
/feature-complete
# Output: Unknown skill: feature-complete
```

## Root Cause Hypotheses

### H1: CLI Registration Gap
The `complete` command is registered under `autobuild` group but `guardkit help` doesn't show `feature complete` as a top-level command. Users expect:
- `guardkit feature complete FEAT-XXX` (not working)
- Actual: `guardkit autobuild complete FEAT-XXX` (this should work)

**Investigation**: Test if `guardkit autobuild complete FEAT-XXX` works.

### H2: Missing Skill Definition
No `/feature-complete` skill file exists in `installer/core/commands/`:
- `feature-build.md` exists
- `feature-plan.md` exists
- **`feature-complete.md` does NOT exist** (confirmed via Glob)

**Investigation**: Check if skill needs to be created.

### H3: Installation/Symlink Issue
The installation might not have symlinked the command properly to `~/.agentecflow/`.

**Investigation**: Check `~/.agentecflow/commands/` for feature-complete.

## Acceptance Criteria

- [ ] Identify all registration gaps (CLI + Claude Code skill)
- [ ] Document the correct invocation syntax for each interface
- [ ] Provide prioritized fix recommendations
- [ ] Estimate complexity for each fix

## Files to Review

1. `guardkit/cli/autobuild.py` - CLI command registration
2. `guardkit/cli/main.py` - Main CLI entry point
3. `installer/core/commands/*.md` - Skill definitions (feature-complete missing)
4. `installer/scripts/install.sh` - Symlink creation
5. `~/.agentecflow/commands/` - Installed commands

## Review Mode

**Mode**: decision
**Depth**: standard (1-2 hours)

This is a decision task to determine:
1. Should `feature complete` be a top-level CLI command?
2. Should `/feature-complete` be a Claude Code skill?
3. Or should both point to `guardkit autobuild complete`?

## Investigation Results

### Finding 1: CLI Command Works (Under Different Path)
```bash
guardkit autobuild complete FEAT-FHE  # WORKS
guardkit feature complete FEAT-FHE    # FAILS (expected by user)
```

The command is registered under `autobuild` subgroup, not as a top-level command.

### Finding 2: Auto-Completion on Success
The `FeatureOrchestrator` automatically sets `status: completed` when all tasks pass:
```
Status: completed
⚠ Feature already completed
```

This means `/feature-complete` is only needed for:
- Features that failed and need manual completion
- Explicit archival and merge handoff instructions
- Edge cases where auto-completion didn't trigger

### Finding 3: Missing Claude Code Skill
No `feature-complete.md` skill file exists in `installer/core/commands/`.

## Recommended Fixes

### Priority 1: Create `/feature-complete` skill (30 min)
Create `installer/core/commands/feature-complete.md` that:
- Calls `guardkit autobuild complete FEAT-XXX`
- Documents when to use vs auto-completion

### Priority 2: Consider CLI alias (optional)
Add `guardkit feature complete` as an alias to `guardkit autobuild complete` for user convenience.

### Priority 3: Update Documentation
Clarify in `feature-build.md` that successful features are auto-completed.

## Notes

The feature-complete subtasks (TASK-FC-001 through TASK-FC-005) focused on the orchestrator and display logic, but may have missed the CLI/skill registration layer.
