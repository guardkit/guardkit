---
id: TASK-GR4-004
title: Add fact extraction logic
status: backlog
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
