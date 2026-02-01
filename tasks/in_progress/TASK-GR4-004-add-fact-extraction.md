---
complexity: 4
dependencies:
- TASK-GR4-002
estimate_hours: 2
feature_id: FEAT-0F4A
id: TASK-GR4-004
implementation_mode: task-work
parallel_group: wave1-gr004
parent_review: TASK-REV-0CD7
status: design_approved
sub_feature: GR-004
task_type: feature
title: Add fact extraction logic
wave: 1
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