---
id: TASK-FIX-1584
title: Sync _cmd_seed() display list with actual seeded categories
status: completed
created: 2026-02-12T00:00:00Z
updated: 2026-02-12T00:00:00Z
completed: 2026-02-12T00:00:00Z
priority: medium
tags: [graphiti, cli, falkordb]
parent_review: TASK-REV-3ECA
complexity: 1
---

# Task: Sync _cmd_seed() display list with actual seeded categories

## Description

The `_cmd_seed()` success display lists 13 categories but `seed_all_system_context()` actually seeds 18. Add the 5 missing categories to the display list.

## Context

- Parent review: TASK-REV-3ECA (FINDING-2)
- The categories were added by TASK-CR-005, TASK-GE-004, TASK-GE-005, TASK-CR-006-FIX but the display wasn't updated

## Missing Categories

Add these 5 to the `categories` list at `graphiti.py:127-141`:

1. `project_overview`
2. `project_architecture`
3. `failed_approaches`
4. `quality_gate_configs`
5. `pattern_examples`

## Acceptance Criteria

- [x] AC-001: `_cmd_seed()` display lists all 18 categories (13 existing + 5 new)
- [x] AC-002: Category order matches `seed_all_system_context()` order in `seeding.py`

## Files to Change

- `guardkit/cli/graphiti.py` - Add 5 categories to display list (lines 127-141)
