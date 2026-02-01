---
id: TASK-GR4-004
title: Add fact extraction logic
status: in_review
task_type: feature
parent_review: TASK-REV-0CD7
feature_id: FEAT-0F4A
sub_feature: GR-004
wave: 1
parallel_group: wave1-gr004
implementation_mode: task-work
complexity: 4
estimate_hours: 2
dependencies:
- TASK-GR4-002
autobuild_state:
  current_turn: 1
  max_turns: 15
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0F4A
  base_branch: main
  started_at: '2026-02-01T13:09:05.712301'
  last_updated: '2026-02-01T13:15:22.792466'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-02-01T13:09:05.712301'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
---

# Add fact extraction logic

## Description

Implement the fact extraction logic that parses user answers and extracts structured facts for storage in Graphiti.

## Acceptance Criteria

- [ ] `_extract_facts(answer, category)` returns `List[str]`
- [ ] Splits answers by sentences
- [ ] Prefixes facts with category context
- [ ] Handles multi-line answers
- [ ] Filters out short/noise sentences

## Technical Details

**Extraction Rules**:
- Split by period (.)
- Filter sentences < 10 characters
- Prefix with category: "Project: ...", "Architecture: ...", etc.

**Future Enhancement**: LLM-powered extraction for more structured data.

**Reference**: See FEAT-GR-004 fact extraction section.
