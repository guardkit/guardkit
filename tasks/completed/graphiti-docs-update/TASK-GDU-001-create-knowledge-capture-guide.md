---
id: TASK-GDU-001
title: Create graphiti-knowledge-capture.md guide
status: completed
created: 2026-02-01T23:45:00Z
updated: 2026-02-02T00:15:00Z
completed: 2026-02-02T00:15:00Z
priority: high
tags: [documentation, graphiti, github-pages]
complexity: 3
parent_review: TASK-REV-BBE7
feature_id: FEAT-GDU
wave: 1
implementation_mode: direct
conductor_workspace: graphiti-docs-wave1-1
---

# Task: Create graphiti-knowledge-capture.md Guide

## Description

Create a new public documentation page for the Interactive Knowledge Capture feature (FEAT-GR-004).

## Source Content

Primary source: `CLAUDE.md` lines 794-901 (Interactive Knowledge Capture section)

Additional sources:
- `docs/research/graphiti-refinement/FEAT-GR-004-interactive-knowledge-capture.md`
- `guardkit/knowledge/gap_analyzer.py`
- `guardkit/knowledge/interactive_capture.py`

## Requirements

Create `docs/guides/graphiti-knowledge-capture.md` with:

1. **Overview** - What interactive knowledge capture is and why it matters
2. **Quick Start** - Basic command usage
3. **Focus Categories** explained:
   - project-overview
   - architecture
   - domain
   - constraints
   - decisions
   - goals
   - role-customization (AutoBuild)
   - quality-gates (AutoBuild)
   - workflow-preferences (AutoBuild)
4. **Session Flow** - Diagram showing the capture workflow
5. **AutoBuild Customization Examples** - Role constraints, quality gates examples
6. **CLI Reference** - All `guardkit graphiti capture` options
7. **Benefits** - Why use interactive capture
8. **See Also** - Links to related docs

## Acceptance Criteria

- [x] Document created at `docs/guides/graphiti-knowledge-capture.md`
- [x] All 9 focus categories documented with examples
- [x] AutoBuild customization section includes concrete examples
- [x] Session flow diagram included (Mermaid or ASCII)
- [x] Follows existing GuardKit documentation style
- [x] Builds successfully with MkDocs (`mkdocs build`)

## Estimated Effort

2 hours

## Implementation Notes

Completed 2026-02-02. Created comprehensive guide with:
- Overview section explaining the problem and benefits (table format)
- Quick Start with 3 example commands
- All 9 focus categories documented in two tables (Project Knowledge + AutoBuild Customization)
- Session flow ASCII diagram with 6 steps
- 3 detailed AutoBuild customization examples (role-customization, quality-gates, workflow-preferences)
- Full CLI reference table with all options
- Complete session example showing typical interaction
- Knowledge storage mapping table
- Integration section for /feature-plan and /feature-build
- Best practices and troubleshooting sections
- See Also links to related documentation

MkDocs build passes (only INFO message about link to excluded research doc).
