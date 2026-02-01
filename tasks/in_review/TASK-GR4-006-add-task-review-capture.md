---
complexity: 4
dependencies:
- TASK-GR4-005
estimate_hours: 2
feature_id: FEAT-0F4A
id: TASK-GR4-006
implementation_mode: task-work
parallel_group: wave1-gr004
parent_review: TASK-REV-0CD7
status: in_review
sub_feature: GR-004
task_type: feature
title: Add /task-review --capture-knowledge integration
wave: 1
---

# Add /task-review --capture-knowledge integration

## Description

Integrate knowledge capture into the `/task-review` command so insights from reviews can be captured and persisted.

## Acceptance Criteria

- [x] `--capture-knowledge` flag triggers post-review capture
- [x] Context-specific questions based on review findings
- [x] Abbreviated session (3-5 questions max)
- [x] Captured decisions/warnings linked to task context
- [x] Works with all review modes

## Technical Details

**Integration Point**: After review completion, before decision checkpoint

**Context-Specific Questions**:
- "What did you learn about {task_type} from this review?"
- "Were there any decisions made that should be remembered?"
- "Are there any warnings for similar future tasks?"

**Reference**: See FEAT-GR-004 task-review integration section.

## Implementation Summary

### Files Implemented/Updated

1. **`guardkit/knowledge/review_knowledge_capture.py`** - Core implementation
   - `ReviewCaptureConfig`: Flag parsing with `from_args()` method
   - `generate_review_questions()`: Context-specific question generation for all 5 review modes
   - `ReviewKnowledgeCapture`: Class interface for review capture integration
   - `run_review_capture()`: Main entry point for command integration

2. **`installer/core/commands/task-review.md`** - Command documentation
   - Added `--capture-knowledge` to command syntax
   - Added flag to Available Flags table
   - Added dedicated `### --capture-knowledge` section with full documentation
   - Added `### Phase 4.5: Knowledge Capture` workflow section
   - Updated Flag Priority list

3. **`tests/test_task_review_knowledge_capture.py`** - Test coverage
   - 33 comprehensive tests covering all acceptance criteria
   - 96% code coverage

### Test Results

```
tests/test_task_review_knowledge_capture.py ... 33 passed in 1.70s
Coverage: 96% for guardkit/knowledge/review_knowledge_capture.py
```

### Review Modes Supported

All 5 review modes have mode-specific question templates:
- `architectural`: SOLID/DRY/YAGNI patterns, violations, decisions
- `code-quality`: Quality issues, refactoring opportunities, future handling
- `decision`: Decision made, alternatives considered, rationale
- `technical-debt`: Debt items, prioritization, prevention strategies
- `security`: Security concerns, immediate vulnerabilities, review approach

## Quality Gate Results

| Gate | Threshold | Result |
|------|-----------|--------|
| Compilation | 100% | ✅ Pass |
| Tests Pass | 100% | ✅ 33/33 Pass |
| Line Coverage | ≥80% | ✅ 96% |
| Branch Coverage | ≥75% | ✅ 85% |
