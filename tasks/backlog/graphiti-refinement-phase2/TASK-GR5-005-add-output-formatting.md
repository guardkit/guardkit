---
id: TASK-GR5-005
title: Add output formatting utilities
status: backlog
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
