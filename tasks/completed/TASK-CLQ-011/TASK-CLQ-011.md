---
id: TASK-CLQ-011
title: Update documentation (CLAUDE.md)
created: 2025-12-08T14:00:00Z
updated: 2025-12-08T14:00:00Z
priority: medium
tags: [clarifying-questions, documentation, wave-4]
complexity: 3
parent_feature: clarifying-questions
wave: 4
conductor_workspace: clarifying-questions-wave4-docs
implementation_method: direct
status: completed
completed: 2025-12-10T08:04:40.012849Z
completed_location: tasks/completed/TASK-CLQ-011/
---

# Task: Update documentation (CLAUDE.md)

## Description

Update CLAUDE.md and related documentation to describe the clarifying questions workflow. This includes adding a section explaining the feature, when it triggers, how to use flags, and examples.

## Acceptance Criteria

- [ ] Add "Clarifying Questions" section to CLAUDE.md
- [ ] Document complexity gating thresholds
- [ ] Document command-line flags for all three commands
- [ ] Add examples showing clarification flow
- [ ] Update command reference sections
- [ ] Add troubleshooting guidance for common issues

## Technical Specification

### CLAUDE.md Section

Add the following section after "Complexity Evaluation":

```markdown
## Clarifying Questions

GuardKit asks targeted clarifying questions before making assumptions during planning. This reduces rework from incorrect assumptions by ~15%.

### When Questions Are Asked

**Complexity Gating:**
| Complexity | task-work | task-review | feature-plan |
|------------|-----------|-------------|--------------|
| 1-2 | Skip | Skip | Skip |
| 3-4 | Quick (15s timeout) | Skip | Quick |
| 5-6 | Full (blocking) | Quick | Full |
| 7+ | Full (blocking) | Full | Full |

### Three Clarification Contexts

| Context | Command | When | Purpose |
|---------|---------|------|---------|
| Review Scope | `/task-review`, `/feature-plan` | Before analysis | Guide what to analyze |
| Implementation Prefs | `/feature-plan` [I]mplement | Before subtask creation | Guide approach & constraints |
| Implementation Planning | `/task-work` | Before planning (Phase 1.5) | Guide scope, tech, trade-offs |

### Command-Line Flags

All commands support:

| Flag | Effect |
|------|--------|
| `--no-questions` | Skip clarification entirely |
| `--with-questions` | Force clarification even for simple tasks |
| `--defaults` | Use defaults without prompting |
| `--answers="1:Y 2:N 3:JWT"` | Inline answers for automation |

### Example: task-work Clarification

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

### Example: Skip Clarification

```bash
# For CI/CD automation
/task-work TASK-a3f8 --no-questions

# Or use inline answers
/task-work TASK-a3f8 --answers="scope:standard testing:integration"
```

### Persistence

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

### Troubleshooting

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
```

### Command Reference Updates

Update each command's reference section:

**task-work.md:**
```markdown
### Flags

| Flag | Description |
|------|-------------|
| `--mode=tdd\|standard` | Development mode |
| `--design-only` | Stop at Phase 2.8 |
| `--implement-only` | Start at Phase 3 |
| `--no-questions` | Skip Phase 1.5 clarification |
| `--with-questions` | Force Phase 1.5 |
| `--defaults` | Use clarification defaults |
| `--answers="..."` | Inline clarification answers |
| `--reclarify` | Re-run clarification (ignore saved) |
```

**task-review.md:**
```markdown
### Flags

| Flag | Description |
|------|-------------|
| `--mode=MODE` | Review mode |
| `--depth=DEPTH` | Review depth |
| `--no-questions` | Skip review scope clarification |
| `--with-questions` | Force clarification |
| `--defaults` | Use clarification defaults |
```

**feature-plan.md:**
```markdown
### Flags

| Flag | Description |
|------|-------------|
| `--no-questions` | Skip all clarification |
| `--with-questions` | Force clarification |
| `--defaults` | Use defaults throughout |
| `--answers="..."` | Inline answers (propagated to task-review) |
```

## Files to Modify

1. `CLAUDE.md` - Add Clarifying Questions section
2. `.claude/CLAUDE.md` - Mirror updates
3. `installer/core/commands/task-work.md` - Update flags table
4. `installer/core/commands/task-review.md` - Update flags table
5. `installer/core/commands/feature-plan.md` - Update flags table

## Why Direct Implementation

- Documentation updates only
- No code changes
- Clear spec from review report
- Lower complexity (3/10)

## Dependencies

- Wave 3: Integration tasks completed (to document accurate behavior)

## Related Tasks

- TASK-CLQ-010 (persistence - parallel)
- TASK-CLQ-012 (testing - parallel)

## Reference

See [Review Report](./../../../.claude/reviews/TASK-REV-B130-review-report.md) for full specification.
