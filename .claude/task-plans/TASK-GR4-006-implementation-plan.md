# Implementation Plan: TASK-GR4-006

## Task
Add /task-review --capture-knowledge integration

## Plan Status
**COMPLETED** - Implementation verified and documented
Generated: 2026-02-01T13:33:05.833248
Completed: 2026-02-01

## Implementation Summary

### Core Implementation (Already Existed)

The Python implementation was completed in prior work (likely TASK-GR4-002/005):

1. **`guardkit/knowledge/review_knowledge_capture.py`**
   - `ReviewCaptureConfig.from_args()`: Parses `--capture-knowledge` and `-ck` flags
   - `generate_review_questions()`: Generates 3-5 context-specific questions based on review mode
   - `ReviewKnowledgeCapture`: Class wrapper for task context and review findings
   - `run_review_capture()`: Main entry point for `/task-review` integration

2. **Mode-Specific Question Templates**:
   - `architectural`: Patterns, SOLID violations, architectural decisions
   - `code-quality`: Quality issues, refactoring opportunities, future handling
   - `decision`: Decision made, alternatives, rationale
   - `technical-debt`: Debt items, prioritization, prevention
   - `security`: Concerns, vulnerabilities, review approach

### Documentation Added (This Session)

**`installer/core/commands/task-review.md`**:
- Added `--capture-knowledge` to command syntax
- Added flag to Available Flags table
- Added `### --capture-knowledge` dedicated section with:
  - When to Use
  - Behavior description
  - Context-Specific Questions by mode
  - Examples
  - Short flag `-ck` documentation
- Added `### Phase 4.5: Knowledge Capture` workflow section
- Updated Flag Priority list

### Test Coverage

**`tests/test_task_review_knowledge_capture.py`**:
- 33 comprehensive tests
- 96% code coverage
- All tests pass

## Verification Results

```bash
pytest tests/test_task_review_knowledge_capture.py -v
# 33 passed in 1.26s

pytest tests/test_task_review_knowledge_capture.py --cov=guardkit/knowledge/review_knowledge_capture --cov-report=term-missing
# Coverage: 96%
```

## Acceptance Criteria Verification

| Criterion | Status | Evidence |
|-----------|--------|----------|
| `--capture-knowledge` flag triggers post-review capture | ✅ | `ReviewCaptureConfig.from_args()` parses flag |
| Context-specific questions based on review findings | ✅ | Mode-specific templates in `_MODE_QUESTIONS` |
| Abbreviated session (3-5 questions max) | ✅ | `generate_review_questions()` returns 3-5 questions |
| Captured decisions/warnings linked to task context | ✅ | `task_context` passed through to capture session |
| Works with all review modes | ✅ | Templates for all 5 modes + generic questions |

## Notes

The implementation was already complete from earlier tasks in the FEAT-GR-004 feature.
This session focused on:
1. Verifying the implementation exists and tests pass
2. Adding documentation to the `/task-review` command specification
3. Moving the task to `in_review` status
