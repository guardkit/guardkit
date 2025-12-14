---
id: TASK-OPT-8085.1
title: Reduce Core AI Agents section in CLAUDE.md
status: backlog
created: 2025-12-14T10:35:00Z
updated: 2025-12-14T10:35:00Z
priority: high
tags: [optimization, documentation, claude-md]
complexity: 3
parent_review: TASK-REV-BFC1
implementation_mode: direct
---

# Task: Reduce Core AI Agents section in CLAUDE.md

## Objective

Reduce the "Core AI Agents" section from 5,496 chars to ~800 chars by keeping only essential reference content and linking to the detailed guide.

## Current State

- Section size: 5,496 chars (9.6% of file)
- Contains: Agent discovery system details, installation/discovery process, stack-specific agents, boundary sections documentation

## Target State

~800 chars containing:
- Brief overview (1-2 sentences)
- Agent categories list (one line each)
- Link to detailed guide

## Implementation

### Keep in CLAUDE.md

```markdown
## Core AI Agents

GuardKit uses AI-powered agent discovery to match tasks to specialists based on metadata (stack, phase, capabilities).

**Agent Categories:**
- **Orchestration**: task-manager
- **Review**: architectural-reviewer, code-reviewer, software-architect
- **Testing**: test-orchestrator, test-verifier, qa-tester
- **Debugging**: debugging-specialist
- **Infrastructure**: devops-specialist, security-specialist, database-specialist
- **Stack-specific**: Template-based (fastapi-specialist, react-state-specialist, etc.)

**See**: [Agent Discovery Guide](docs/guides/agent-discovery-guide.md) for discovery system, installation, and customization.
```

### Remove from CLAUDE.md

- Agent Discovery System detailed explanation
- How Agents Are Installed and Discovered section
- Adding Custom Agents section
- Stack-Specific Implementation Agents detailed list
- Agent Enhancement with Boundary Sections (entire subsection)
- Example boundary markdown blocks

## Verification

1. New section is ~800 chars
2. Link to docs/guides/agent-discovery-guide.md is valid
3. All removed content exists in the guide

## Acceptance Criteria

- [ ] Section reduced from 5,496 to ~800 chars
- [ ] "See:" link points to valid guide
- [ ] No information permanently lost
- [ ] CLAUDE.md still parseable (no broken markdown)
