---
id: TASK-OPT-8085.3
title: Consolidate duplicate Boundaries sections in CLAUDE.md
status: cancelled
created: 2025-12-14T10:35:00Z
updated: 2025-12-14T13:55:00Z
priority: high
tags: [optimization, documentation, claude-md]
complexity: 2
parent_review: TASK-REV-BFC1
implementation_mode: direct
previous_state: in_progress
state_transition_reason: "No duplicate sections exist - code blocks mistaken for duplicates"
cancelled_at: 2025-12-14T13:55:00Z
cancelled_by: user
cancellation_reason: "Investigation revealed no actual duplicate Boundaries sections. Lines 1427 and 1452 are markdown code block examples, not duplicate documentation."
---

# Task: Consolidate duplicate Boundaries sections in CLAUDE.md

## Objective

Remove duplicate "Boundaries" sections (total 4,690 chars) and consolidate into one concise section (~1,200 chars).

## Current State

Two sections named "## Boundaries" exist:
1. First occurrence: 3,657 chars (line ~1400)
2. Second occurrence: 1,033 chars (line ~1449)

Combined: 4,690 chars

## Target State

Single consolidated section (~1,200 chars) explaining:
- What boundaries are
- Format (ALWAYS/NEVER/ASK)
- Where to find detailed examples

## Implementation

### Keep in CLAUDE.md (single section)

```markdown
## Agent Boundaries

All agents include **ALWAYS/NEVER/ASK boundary sections** that explicitly define behavior:

- **ALWAYS** (5-7 rules): Non-negotiable actions (e.g., "✅ Run build verification before tests")
- **NEVER** (5-7 rules): Prohibited actions (e.g., "❌ Never approve code with failing tests")
- **ASK** (3-5 scenarios): Situations requiring human escalation (e.g., "⚠️ Coverage 70-79%: Ask if acceptable")

**Format**: `[emoji] [action] ([brief rationale])`

Boundaries are validated during `/agent-enhance` and `/template-create`.

**See**: [Agent Enhancement with Boundary Sections](#agent-enhancement-with-boundary-sections) in the Core AI Agents section or individual agent files in `installer/core/agents/*.md`.
```

### Remove from CLAUDE.md

- First "Boundaries" section with full example blocks
- Second "Boundaries" section
- Detailed Testing Agent Boundaries example
- Detailed Repository Agent Boundaries example
- "How to Interpret Boundary Rules" subsection
- "Validation During Enhancement" subsection

## Verification

1. Only ONE "Boundaries" or "Agent Boundaries" section exists
2. New section is ~1,200 chars
3. Internal link is valid

## Acceptance Criteria

- [ ] Single consolidated section (~1,200 chars)
- [ ] No duplicate ## Boundaries headings
- [ ] Clear explanation of ALWAYS/NEVER/ASK format
- [ ] CLAUDE.md still parseable
