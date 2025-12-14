---
id: TASK-OPT-8085.1
title: Reduce Core AI Agents section in CLAUDE.md
status: completed
created: 2025-12-14T10:35:00Z
updated: 2025-12-14T15:40:00Z
completed: 2025-12-14T15:40:00Z
priority: high
tags: [optimization, documentation, claude-md]
complexity: 3
parent_review: TASK-REV-BFC1
implementation_mode: direct
previous_state: in_review
state_transition_reason: "Task completed successfully - all acceptance criteria met"
completed_location: tasks/completed/claude-md-optimization/TASK-OPT-8085.1/
organized_files: ["TASK-OPT-8085.1.md"]
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

- [x] Section reduced from 5,496 to ~800 chars (actual: 661 chars)
- [x] "See:" link points to valid guide (docs/guides/agent-discovery-guide.md)
- [x] No information permanently lost (content exists in agent-discovery-guide.md and other docs)
- [x] CLAUDE.md still parseable (no broken markdown)

## Implementation Summary

Successfully reduced the "Core AI Agents" section from 5,496 characters to 661 characters (88% reduction).

**Changes:**
- Removed: Detailed Agent Discovery System explanation
- Removed: How Agents Are Installed and Discovered section
- Removed: Adding Custom Agents code examples
- Removed: Stack-Specific Implementation Agents detailed list
- Removed: Agent Enhancement with Boundary Sections (entire subsection)
- Removed: Example boundary markdown blocks
- Kept: Brief overview, agent categories list, link to guide

**Information Preservation:**
- Agent discovery details → docs/guides/agent-discovery-guide.md
- Installation process → Installer documentation
- Boundary sections → agent-content-enhancer.md, template-create.md
- Stack-specific agents → docs/guides/agent-discovery-guide.md ("Available Specialists")

**Verification:**
- New section: 661 chars (target: ~800 chars) ✅
- Guide link valid: docs/guides/agent-discovery-guide.md exists ✅
- Markdown parseable: No syntax errors ✅
- No broken internal links ✅
