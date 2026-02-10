---
complexity: 4
created: 2026-02-10 11:40:00+00:00
dependencies:
- TASK-SC-005
feature_id: FEAT-SC-001
id: TASK-SC-011
implementation_mode: task-work
parent_review: TASK-REV-AEA7
priority: medium
status: design_approved
tags:
- documentation
- docs-site
- guides
task_type: documentation
title: Create docs site guides for system context commands
updated: 2026-02-10 11:40:00+00:00
wave: 4
---

# Task: Create docs site guides for system context commands

## Description

Create user-facing documentation guides for the 3 new system context commands on the GitHub Pages docs site. These are the human-readable versions of the command specs — focused on walkthroughs, use cases, and integration examples rather than Claude Code execution instructions.

## Key Implementation Details

### Files to Create

1. **`docs/guides/system-overview-guide.md`** — /system-overview user guide
2. **`docs/guides/impact-analysis-guide.md`** — /impact-analysis user guide
3. **`docs/guides/context-switch-guide.md`** — /context-switch user guide

### Guide Structure (follow existing pattern from graphiti-commands.md)

Each guide should include:

1. **Quick Start** — one-line command + example output
2. **What It Does** — 2-3 sentence explanation
3. **Prerequisites** — what needs to be set up (Graphiti, /system-plan, etc.)
4. **Usage** — syntax, flags, arguments table
5. **Examples** — 3-5 real-world use cases with expected output
6. **Integration** — how it works with other commands (/system-plan, /task-work, /feature-build)
7. **Graceful Degradation** — what happens when Graphiti is down or no context exists
8. **Troubleshooting** — common issues and solutions

### /system-overview Guide Content

```markdown
# System Overview Command

Get a one-screen summary of your project's architecture.

## Quick Start
/system-overview

## What It Does
Displays a condensed view of your project's bounded contexts, ADRs,
cross-cutting concerns, and tech stack — all pulled from Graphiti's
knowledge graph. Think of it as "remind me where I am" for architecture.

## Prerequisites
- Run /system-plan at least once to capture architecture context
- (Optional) Graphiti stack running for live queries

## Usage
/system-overview [--verbose] [--section=SECTION] [--format=FORMAT]

[... flags table, examples, integration ...]
```

### /impact-analysis Guide Content

Focus on the practical workflow:
- "Before starting a complex task, check what it affects"
- Show the risk score visualization
- Walk through the [P]roceed/[R]eview/[S]ystem-plan/[C]ancel decision
- Show how [P]roceed feeds context into /task-work

### /context-switch Guide Content

Focus on multi-project navigation:
- "Switch between projects without losing context"
- Show --list output
- Walk through a switch and what changes (Graphiti namespace only)
- Emphasize what it does NOT do (no git/filesystem changes)

## Acceptance Criteria

- [ ] 3 guide files created in `docs/guides/`
- [ ] Each guide follows the Quick Start → Usage → Examples → Troubleshooting pattern
- [ ] Examples show realistic output matching spec display formats
- [ ] Integration section references related commands
- [ ] Graceful degradation documented (no context, Graphiti down)
- [ ] Guides are understandable without reading the command specs
- [ ] No CRITICAL EXECUTION INSTRUCTIONS (those are in command specs only)

## Test Requirements

No automated tests — documentation is verified by manual review.

## Implementation Notes

- Follow the style of `docs/guides/graphiti-commands.md` (concise, focused)
- Do NOT duplicate the full command spec — guides are user-facing summaries
- Use Mermaid diagrams if helpful (mkdocs has superfences/mermaid support)
- Keep each guide to ~100-200 lines (not 1000+ like feature-build.md)