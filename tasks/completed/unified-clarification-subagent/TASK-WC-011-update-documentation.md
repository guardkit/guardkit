---
id: TASK-WC-011
title: Update CLAUDE.md documentation
status: completed
task_type: implementation
created: 2025-12-13T22:45:00Z
updated: 2025-12-13T21:25:00Z
completed: 2025-12-13T21:25:00Z
priority: medium
tags: [clarification, documentation, wave-3]
complexity: 3
parent_feature: unified-clarification-subagent
parent_review: TASK-REV-CLQ3
wave: 3
implementation_mode: direct
conductor_workspace: unified-clarification-wave3-3
dependencies:
  - TASK-WC-005
test_results:
  status: not_applicable
  coverage: null
  last_run: null
---

# Task: Update CLAUDE.md Documentation

## Description

Update CLAUDE.md and related documentation files to reflect the unified subagent pattern for clarification, removing references to the never-used Python orchestrators.

## Files to Update

1. `CLAUDE.md` (root) - Clarifying Questions section
2. `.claude/CLAUDE.md` - Clarifying Questions section
3. `docs/workflows/clarification-workflow.md` (if exists, or create if needed)

## Changes Required

### 1. Update Root CLAUDE.md

Find the "Clarifying Questions" section and update:

**REMOVE** any references to:
- Python orchestrators for clarification
- `feature_plan_orchestrator.py`
- `task_review_orchestrator.py`
- Orchestrator symlinks

**UPDATE** to reflect subagent pattern:

```markdown
## Clarifying Questions

GuardKit asks targeted clarifying questions before making assumptions during planning. This reduces rework from incorrect assumptions by ~15%.

### How It Works

All commands use the `clarification-questioner` subagent to collect user preferences:

| Command | Context Type | When | Purpose |
|---------|--------------|------|---------|
| `/task-work` | implementation_planning | Phase 1.6 | Guide implementation scope and approach |
| `/feature-plan` | review_scope | Before review | Guide what to analyze |
| `/feature-plan` | implementation_prefs | At [I]mplement | Guide subtask creation |
| `/task-review` | review_scope | Phase 1 | Guide review focus |

### Complexity Gating

| Complexity | task-work | task-review | feature-plan |
|------------|-----------|-------------|--------------|
| 1-2 | Skip | Skip | Skip |
| 3-4 | Quick (15s timeout) | Skip | Quick |
| 5-6 | Full (blocking) | Quick | Full |
| 7+ | Full (blocking) | Full | Full |

### Agent Invocation

All commands invoke the same agent:

```
subagent_type: "clarification-questioner"
prompt: "Execute clarification...
  CONTEXT TYPE: {review_scope|implementation_prefs|implementation_planning}
  ..."
```

### Command-Line Flags

All commands support:

| Flag | Effect |
|------|--------|
| `--no-questions` | Skip clarification entirely |
| `--with-questions` | Force clarification even for simple tasks |
| `--defaults` | Use defaults without prompting |
| `--answers="1:Y 2:N 3:JWT"` | Inline answers for automation |
```

### 2. Update .claude/CLAUDE.md

Update the clarifying questions section similarly:

```markdown
## Clarifying Questions

GuardKit uses a unified `clarification-questioner` subagent for all clarification needs.

### Three Contexts

1. **review_scope** (Context A) - For /feature-plan and /task-review
2. **implementation_prefs** (Context B) - For /feature-plan [I]mplement
3. **implementation_planning** (Context C) - For /task-work Phase 1.6

### Control Flags

All commands support:
- `--no-questions` - Skip clarification
- `--with-questions` - Force clarification
- `--defaults` - Use defaults without prompting
- `--answers="..."` - Inline answers for automation
- `--reclarify` - Re-run even if saved

### Persistence

Decisions are saved to task frontmatter for audit trail and reproducibility.
```

### 3. Remove Dead References

Search for and remove any references to:
- `feature_plan_orchestrator.py` for clarification
- `task_review_orchestrator.py` for clarification
- Orchestrator symlinks for clarification
- "Integration Code" sections that reference orchestrators

**Note**: Keep orchestrator files themselves - they may be used for other purposes. Just remove documentation that implies they're used for clarification.

### 4. Add Agent Documentation

Add a brief section about the clarification agent:

```markdown
### Clarification Agent

The `clarification-questioner` agent handles all clarification contexts:
- Location: `~/.agentecflow/agents/clarification-questioner.md`
- Installed by: GuardKit installer
- Uses: `lib/clarification/*` Python modules

The agent is invoked via the Task tool at appropriate points in each command's workflow.
```

## Acceptance Criteria

- [x] CLAUDE.md reflects unified subagent pattern
- [x] .claude/CLAUDE.md reflects unified subagent pattern
- [x] No references to orchestrator pattern for clarification
- [x] All three context types documented
- [x] Flags documented consistently
- [x] Complexity gating documented
- [x] Agent location and installation documented

## Testing

1. ✅ Review updated documentation for accuracy - All sections updated correctly
2. ✅ Follow documentation to verify flag behavior - Flag documentation consistent across files
3. ✅ Ensure no contradictory information remains - No orchestrator references found

## Completion Summary

Successfully updated all documentation to reflect the unified `clarification-questioner` subagent pattern:

### Files Updated:
1. **CLAUDE.md** - Added "How It Works", "Agent Invocation", and "Clarification Agent" sections
2. **.claude/CLAUDE.md** - Updated with unified agent pattern and context types
3. **docs/workflows/clarification-workflow.md** - Created comprehensive workflow guide (9.1KB)

### Key Changes:
- Documented unified subagent invocation pattern
- Added command/context type mapping table
- Documented all three context types (review_scope, implementation_prefs, implementation_planning)
- Added agent location and installation details
- Created detailed workflow guide with examples and troubleshooting

### Verification:
- ✅ No orchestrator references in clarification sections
- ✅ All three context types documented with examples
- ✅ Command-line flags documented consistently
- ✅ Complexity gating tables present in all relevant files
- ✅ Agent location documented in both CLAUDE.md files

Commit: c79b0bf
