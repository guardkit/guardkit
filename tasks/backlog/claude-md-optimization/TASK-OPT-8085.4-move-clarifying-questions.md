---
id: TASK-OPT-8085.4
title: Move Clarifying Questions details to rules/
status: backlog
created: 2025-12-14T10:35:00Z
updated: 2025-12-14T10:35:00Z
priority: high
tags: [optimization, documentation, claude-md]
complexity: 3
parent_review: TASK-REV-BFC1
implementation_mode: task-work
---

# Task: Move Clarifying Questions details to rules/

## Objective

Reduce "Clarifying Questions" section from 3,668 chars to ~600 chars by moving detailed tables and examples to `.claude/rules/`.

## Current State

- Section size: 3,668 chars (6.4% of file)
- Contains: How it works table, complexity gating table, agent invocation, command-line flags, full example, persistence YAML, troubleshooting

## Target State

~600 chars in CLAUDE.md containing:
- Brief explanation
- Flag reference (one line each)
- Link to rules file for details

## Implementation

### Step 1: Create rules file

Create `.claude/rules/clarifying-questions.md`:

```markdown
---
description: Clarifying questions system for task planning
---

# Clarifying Questions

GuardKit asks targeted clarifying questions before making assumptions during planning, reducing rework by ~15%.

## Command Integration

| Command | Context Type | When | Purpose |
|---------|--------------|------|---------|
| `/task-work` | implementation_planning | Phase 1.6 | Guide implementation scope |
| `/feature-plan` | review_scope | Before review | Guide what to analyze |
| `/feature-plan` | implementation_prefs | At [I]mplement | Guide subtask creation |
| `/task-review` | review_scope | Phase 1 | Guide review focus |

## Complexity Gating

| Complexity | task-work | task-review | feature-plan |
|------------|-----------|-------------|--------------|
| 1-2 | Skip | Skip | Skip |
| 3-4 | Quick (15s timeout) | Skip | Quick |
| 5-6 | Full (blocking) | Quick | Full |
| 7+ | Full (blocking) | Full | Full |

## Example: task-work Clarification

[Include full example from current CLAUDE.md]

## Persistence

Decisions are saved to task frontmatter:

```yaml
clarification:
  context: implementation_planning
  timestamp: 2025-12-08T14:30:00Z
  mode: full
  decisions:
    - question_id: scope
      answer: standard
```

## Troubleshooting

- **Questions not appearing?** Check complexity (must be ≥3), verify no `--no-questions` flag
- **Re-ask questions?** Use `--reclarify` flag
- **View previous decisions?** Check `clarification` in task frontmatter
```

### Step 2: Update CLAUDE.md

```markdown
## Clarifying Questions

GuardKit asks targeted questions before making assumptions during planning (~15% rework reduction).

**Flags** (all commands):
- `--no-questions` - Skip clarification
- `--with-questions` - Force clarification
- `--defaults` - Use defaults without prompting
- `--answers="..."` - Inline answers for automation

**Agent**: `clarification-questioner` at `~/.agentecflow/agents/`

**See**: `.claude/rules/clarifying-questions.md` for complexity gating, examples, and troubleshooting.
```

## Verification

1. New CLAUDE.md section is ~600 chars
2. Rules file created with full content
3. Rules file loads conditionally

## Acceptance Criteria

- [ ] Section reduced from 3,668 to ~600 chars
- [ ] `.claude/rules/clarifying-questions.md` created
- [ ] No information lost
- [ ] CLAUDE.md still parseable
