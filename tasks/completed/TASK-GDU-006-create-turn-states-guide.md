---
id: TASK-GDU-006
title: Create graphiti-turn-states.md guide
status: completed
created: 2026-02-01T23:45:00Z
updated: 2026-02-02T00:15:00Z
completed: 2026-02-02T00:15:00Z
priority: medium
tags: [documentation, graphiti, autobuild]
complexity: 2
parent_review: TASK-REV-BBE7
feature_id: FEAT-GDU
wave: 3
implementation_mode: direct
conductor_workspace: graphiti-docs-wave3-1
---

# Task: Create graphiti-turn-states.md Guide

## Description

Create a new public documentation page for Turn State Tracking in AutoBuild workflows.

## Source Content

Primary sources:
- `CLAUDE.md` lines 960-1001 (Turn State Tracking section)
- `docs/research/graphiti-refinement/FEAT-GR-005-knowledge-query-command.md`
- `guardkit/knowledge/turn_state_operations.py`

## Requirements

Create `docs/guides/graphiti-turn-states.md` with:

1. **Overview** - What turn states are and why they matter for AutoBuild
2. **What Gets Captured** per turn:
   - Player decisions and actions
   - Coach feedback and approval status
   - Files modified
   - Acceptance criteria status
   - Blockers encountered
   - Progress summary
3. **Turn State Schema** - Full field documentation
4. **Querying Turn States**:
   - `guardkit graphiti search "turn FEAT-XXX" --group turn_states`
   - `guardkit graphiti search "turn TASK-XXX" --group turn_states --limit 5`
5. **Cross-Turn Learning** - How Turn N+1 uses Turn N's knowledge
6. **Mode Tracking** - FRESH_START, RECOVERING_STATE, CONTINUING_WORK
7. **Benefits** - Prevent repeated mistakes, track progress, audit trail

## Acceptance Criteria

- [x] Document created at `docs/guides/graphiti-turn-states.md`
- [x] Turn state schema fully documented
- [x] Query examples included
- [x] Cross-turn learning explained
- [x] Follows existing GuardKit documentation style
- [x] Builds successfully with MkDocs

## Estimated Effort

1 hour

## Completion Notes

**Completed**: 2026-02-01

Created comprehensive guide at `docs/guides/graphiti-turn-states.md` with:
- Overview explaining cross-turn learning problem and solution
- Complete "What Gets Captured" section (Player actions, Coach feedback, Quality metrics, Context, Timing)
- Full turn state schema reference with all fields documented in tables
- Mode tracking section explaining FRESH_START, CONTINUING_WORK, RECOVERING_STATE
- Query examples with CLI commands and expected output
- Cross-turn learning section with context format examples
- Complete turn history example (3 turns from FRESH_START to approval)
- AutoBuild integration section
- Debugging patterns and best practices
- Troubleshooting section

Source content from:
- CLAUDE.md lines 960-1001
- FEAT-GR-005-knowledge-query-command.md
- guardkit/knowledge/turn_state_operations.py
- guardkit/knowledge/entities/turn_state.py

MkDocs build passes (pre-existing warnings unrelated to this guide).
