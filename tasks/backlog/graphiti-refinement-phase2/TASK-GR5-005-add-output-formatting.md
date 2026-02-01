---
id: TASK-GR5-005
title: Add output formatting utilities
status: in_review
task_type: feature
parent_review: TASK-REV-0CD7
feature_id: FEAT-0F4A
sub_feature: GR-005
wave: 2
implementation_mode: direct
complexity: 3
estimate_hours: 1
dependencies:
- TASK-GR5-001
autobuild_state:
  current_turn: 1
  max_turns: 15
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0F4A
  base_branch: main
  started_at: '2026-02-01T14:23:22.805020'
  last_updated: '2026-02-01T14:27:28.052617'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-02-01T14:23:22.805020'
    player_summary: "Created comprehensive output formatting utilities for Graphiti\
      \ query commands in guardkit/cli/graphiti_query_commands.py. The module provides:\n\
      \n1. **_format_detail()** - Formats detailed output for single search results\
      \ with specialized formatting for different knowledge types (feature, ADR, pattern,\
      \ default)\n\n2. **JSON parsing** - Parses structured facts stored as JSON and\
      \ displays them in readable format with appropriate fields for each knowledge\
      \ type\n\n3. **Color coding by relevance score**:\n "
    player_success: true
    coach_success: true
---

# Add output formatting utilities

## Description

Create shared output formatting utilities for the query commands.

## Acceptance Criteria

- [ ] `_format_detail(result, knowledge_type)` for detailed output
- [ ] JSON parsing for structured facts
- [ ] Color coding by relevance score (>0.8 green, >0.5 yellow, else white)
- [ ] Truncation helpers for long text
- [ ] Box-drawing characters for status display

## Technical Details

**Location**: `guardkit/cli/graphiti_query_commands.py`

**Color Coding**:
- Score > 0.8: Green (high relevance)
- Score > 0.5: Yellow (medium relevance)
- Score <= 0.5: White (low relevance)
