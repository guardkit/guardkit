---
description: Clarifying questions system for task planning
paths: installer/core/commands/*.md, installer/core/agents/clarification-questioner.md
---

# Clarifying Questions

GuardKit asks targeted clarifying questions before making assumptions during planning, reducing rework by ~15%.

## How It Works

All commands use the `clarification-questioner` subagent to collect user preferences:

| Command | Context Type | When | Purpose |
|---------|--------------|------|---------|
| `/task-work` | implementation_planning | Phase 1.6 | Guide implementation scope and approach |
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

## Agent Invocation

All commands invoke the same agent:

```
subagent_type: "clarification-questioner"
prompt: "Execute clarification...
  CONTEXT TYPE: {review_scope|implementation_prefs|implementation_planning}
  ..."
```

## Command-Line Flags

All commands support:

| Flag | Effect |
|------|--------|
| `--no-questions` | Skip clarification entirely |
| `--with-questions` | Force clarification even for simple tasks |
| `--defaults` | Use defaults without prompting |
| `--answers="1:Y 2:N 3:JWT"` | Inline answers for automation |

## Example: task-work Clarification

```bash
/task-work TASK-a3f8

Phase 1: Loading context...
Phase 1.5: Clarifying Questions (complexity: 5)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 CLARIFYING QUESTIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Q1. Implementation Scope
    How comprehensive should this implementation be?

    [M]inimal - Core functionality only
    [S]tandard - With error handling (DEFAULT)
    [C]omplete - Production-ready with edge cases

    Your choice [M/S/C]: S

Q2. Testing Approach
    What testing strategy?

    [U]nit tests only
    [I]ntegration tests included (DEFAULT)
    [F]ull coverage (unit + integration + e2e)

    Your choice [U/I/F]: I

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ Recorded 2 decisions
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Phase 2: Planning implementation with clarifications...
```

## Example: Skip Clarification

```bash
# For CI/CD automation
/task-work TASK-a3f8 --no-questions

# Or use inline answers
/task-work TASK-a3f8 --answers="scope:standard testing:integration"
```

## Persistence

Clarification decisions are persisted to task frontmatter:

```yaml
clarification:
  context: implementation_planning
  timestamp: 2025-12-08T14:30:00Z
  mode: full
  decisions:
    - question_id: scope
      answer: standard
      default_used: true
```

This enables:
- Task resumption without re-asking questions
- Audit trail of planning decisions
- Reproducibility of AI behavior

## Troubleshooting

**Questions not appearing?**
- Check task complexity (must be ≥3 for task-work)
- Verify not using `--no-questions` flag
- Check if previous clarification exists in frontmatter

**Want to re-ask questions?**
```bash
/task-work TASK-a3f8 --reclarify
```

**Want to see previous decisions?**
Check the `clarification` section in task frontmatter.

## Clarification Agent

The `clarification-questioner` agent handles all clarification contexts:
- Location: `~/.agentecflow/agents/clarification-questioner.md`
- Installed by: GuardKit installer
- Uses: `lib/clarification/*` Python modules

The agent is invoked via the Task tool at appropriate points in each command's workflow.
