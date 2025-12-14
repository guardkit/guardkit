---
id: TASK-OPT-8085.5
title: Reduce Incremental Enhancement section in CLAUDE.md
status: backlog
created: 2025-12-14T10:35:00Z
updated: 2025-12-14T10:35:00Z
priority: high
tags: [optimization, documentation, claude-md]
complexity: 2
parent_review: TASK-REV-BFC1
implementation_mode: direct
---

# Task: Reduce Incremental Enhancement section in CLAUDE.md

## Objective

Reduce "Incremental Enhancement Workflow" section from 3,343 chars to ~400 chars by linking to existing workflow documentation.

## Current State

- Section size: 3,343 chars (5.9% of file)
- Contains: When to use, workflow options (task-based and direct), enhancement strategies (AI/static/hybrid), best practices

## Target State

~400 chars containing:
- Brief explanation
- Command example
- Link to detailed workflow

## Implementation

### Keep in CLAUDE.md

```markdown
## Incremental Enhancement Workflow

Phase 8 of `/template-create` enables incremental agent enhancement - improve agent files over time instead of all at once.

```bash
# Task-based (recommended)
/template-create --name my-template --create-agent-tasks
/task-work TASK-AGENT-XXX

# Direct
/agent-enhance AGENT_FILE TEMPLATE_DIR [--strategy=ai|static|hybrid]
```

**See**: [Incremental Enhancement Workflow](docs/workflows/incremental-enhancement-workflow.md) for when to use, strategies, and best practices.
```

### Remove from CLAUDE.md

- "When to Use" section with bullet lists
- "Workflow Options" with Option A and Option B details
- Full command examples for both options
- "Enhancement Strategies" section (AI/Static/Hybrid details)
- "Best Practices" numbered list

## Verification

1. New section is ~400 chars
2. Link to docs/workflows/incremental-enhancement-workflow.md is valid
3. Workflow guide exists with detailed content

## Acceptance Criteria

- [ ] Section reduced from 3,343 to ~400 chars
- [ ] "See:" link points to valid workflow doc
- [ ] No information permanently lost
- [ ] CLAUDE.md still parseable
