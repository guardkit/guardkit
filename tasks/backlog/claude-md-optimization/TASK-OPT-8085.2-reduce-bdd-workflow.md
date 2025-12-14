---
id: TASK-OPT-8085.2
title: Reduce BDD Workflow section in CLAUDE.md
status: backlog
created: 2025-12-14T10:35:00Z
updated: 2025-12-14T10:35:00Z
priority: high
tags: [optimization, documentation, claude-md]
complexity: 2
parent_review: TASK-REV-BFC1
implementation_mode: direct
---

# Task: Reduce BDD Workflow section in CLAUDE.md

## Objective

Reduce the "BDD Workflow (Agentic Systems)" section from 4,740 chars to ~500 chars by linking to the comprehensive existing guide.

## Current State

- Section size: 4,740 chars (8.3% of file)
- Contains: When to use, prerequisites, complete workflow, example code, benefits, error scenarios

## Target State

~500 chars containing:
- When to use BDD (1 sentence)
- Command example
- Link to detailed guide

## Implementation

### Keep in CLAUDE.md

```markdown
## BDD Workflow (Agentic Systems)

For LangGraph state machines, multi-agent coordination, and safety-critical workflows requiring formal behavior specifications, use BDD mode with RequireKit.

```bash
/task-work TASK-XXX --mode=bdd
```

**Requires**: RequireKit installation (`~/.agentecflow/require-kit.marker.json`)

**See**: [BDD Workflow for Agentic Systems](docs/guides/bdd-workflow-for-agentic-systems.md) for complete setup, EARS notation, Gherkin generation, and examples.
```

### Remove from CLAUDE.md

- "When to Use BDD Mode" detailed list
- "Prerequisites" section with installation commands
- "Complete Workflow" step-by-step
- "What Happens in BDD Mode" numbered list
- "Example: LangGraph Orchestration" (40+ lines of code)
- "Benefits for Agentic Systems" checklist
- "Error Scenarios" examples

## Verification

1. New section is ~500 chars
2. Link to docs/guides/bdd-workflow-for-agentic-systems.md is valid
3. Guide contains all removed content (it does - 36KB file)

## Acceptance Criteria

- [ ] Section reduced from 4,740 to ~500 chars
- [ ] "See:" link points to valid guide
- [ ] No information permanently lost
- [ ] CLAUDE.md still parseable
