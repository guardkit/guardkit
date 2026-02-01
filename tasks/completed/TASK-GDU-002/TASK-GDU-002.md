---
id: TASK-GDU-002
title: Create graphiti-query-commands.md guide
status: completed
created: 2026-02-01T23:45:00Z
updated: 2026-02-02T08:45:00Z
completed: 2026-02-02T08:50:00Z
priority: high
tags: [documentation, graphiti, github-pages]
complexity: 3
parent_review: TASK-REV-BBE7
feature_id: FEAT-GDU
wave: 1
implementation_mode: direct
conductor_workspace: graphiti-docs-wave1-2
completed_location: tasks/completed/TASK-GDU-002/
organized_files:
  - TASK-GDU-002.md
deliverables:
  - docs/guides/graphiti-query-commands.md
  - mkdocs.yml (updated)
---

# Task: Create graphiti-query-commands.md Guide

## Description

Create a new public documentation page for the Knowledge Query Commands (FEAT-GR-005).

## Source Content

Primary source: `CLAUDE.md` lines 903-1001 (Knowledge Query Commands section)

Additional sources:
- `docs/research/graphiti-refinement/FEAT-GR-005-knowledge-query-command.md`
- `guardkit/cli/graphiti.py`
- `guardkit/cli/graphiti_query_commands.py`

## Requirements

Create `docs/guides/graphiti-query-commands.md` with:

1. **Overview** - Purpose of query commands
2. **Commands Reference**:
   - `guardkit graphiti show <knowledge_id>` - Display detailed information
   - `guardkit graphiti search <query>` - Search across knowledge
   - `guardkit graphiti list <category>` - List items by category
   - `guardkit graphiti status` - Show knowledge graph health
3. **Knowledge Groups** explained:
   - System Knowledge (product_knowledge, command_workflows, patterns, agents)
   - Project Knowledge (project_overview, project_architecture, feature_specs)
   - Decisions (project_decisions, architecture_decisions)
   - Learning (task_outcomes, failure_patterns, successful_fixes)
   - Turn States (turn_states)
4. **Example Queries** with actual output
5. **Output Formatting** - Color coding by relevance
6. **Troubleshooting** - Common issues and solutions

## Acceptance Criteria

- [x] Document created at `docs/guides/graphiti-query-commands.md`
- [x] All 4 commands documented with options and examples
- [x] Knowledge groups table included
- [x] Example outputs shown (can use code blocks)
- [x] Follows existing GuardKit documentation style
- [x] Builds successfully with MkDocs

## Estimated Effort

2 hours
