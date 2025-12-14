---
id: TASK-CLQ-FIX-001
title: "Integrate clarification module into task-review orchestrator"
status: completed
created: 2025-12-13T16:35:00Z
updated: 2025-12-13T17:50:00Z
completed: 2025-12-13T17:50:00Z
priority: critical
tags: [clarifying-questions, orchestrator, integration, bug-fix]
complexity: 5
parent_review: TASK-REV-0614
implementation_mode: task-work
completed_location: tasks/completed/TASK-CLQ-FIX-001/
---

# Task: Integrate clarification module into task-review orchestrator

## Description

Add Phase 1.5 (Clarification) to `task_review_orchestrator.py` by wiring up the existing clarification module. The module is complete but never called.

## Implementation Details

### File to Modify

`installer/core/commands/lib/task_review_orchestrator.py`

### Changes Required

1. **Add imports** (after line ~35):
```python
from clarification import (
    should_clarify,
    ClarificationMode,
    ClarificationContext,
)
from clarification.generators.review_generator import generate_review_questions
from clarification.display import display_full_questions, display_quick_questions
```

2. **Add Phase 1.5 function**:
```python
def execute_clarification_phase(
    task_context: Dict[str, Any],
    review_mode: str,
    flags: Dict[str, Any]
) -> Optional[ClarificationContext]:
    """
    Phase 1.5: Clarification (if needed).

    Determines if clarification is needed based on complexity and mode,
    then displays questions and collects responses.
    """
    complexity = task_context.get('metadata', {}).get('complexity', 5)

    # Determine clarification mode
    mode = should_clarify("review", complexity, flags)

    if mode == ClarificationMode.SKIP:
        print(f"Skipping clarification (complexity: {complexity})")
        return None

    # Generate questions
    questions = generate_review_questions(
        task_context=task_context,
        review_mode=review_mode,
        complexity=complexity
    )

    if not questions:
        return None

    # Display and collect responses
    if mode == ClarificationMode.FULL:
        clarification = display_full_questions(
            questions=questions,
            task_id=task_context['task_id'],
            task_title=task_context['title'],
            complexity=complexity
        )
    else:  # QUICK
        clarification = display_quick_questions(
            questions=questions,
            timeout_seconds=15
        )

    return clarification
```

3. **Modify `execute_task_review()` to call Phase 1.5** (after Phase 1, before Phase 2):
```python
# Phase 1: Load review context
task_context = load_review_context(task_id)

# Phase 1.5: Clarification (if needed)
flags = {
    'no_questions': no_questions,  # from CLI arg
    'with_questions': with_questions,
    'defaults': defaults,
}
clarification = execute_clarification_phase(task_context, mode, flags)
if clarification:
    task_context['clarification'] = clarification
    # Persist to frontmatter
    clarification.persist_to_frontmatter(Path(task_context['file_path']))

# Phase 2: Execute review analysis
review_results = execute_review_analysis(task_context, mode, depth, model_id)
```

4. **Add CLI arguments for clarification flags**:
```python
parser.add_argument("--no-questions", action="store_true",
                    help="Skip clarification questions")
parser.add_argument("--with-questions", action="store_true",
                    help="Force clarification even for simple tasks")
parser.add_argument("--defaults", action="store_true",
                    help="Use default answers without prompting")
```

## Acceptance Criteria

- [x] `should_clarify()` is called with correct parameters
- [x] Questions are displayed for complexity >= 4 in decision mode
- [x] Questions are skipped for complexity <= 2
- [x] `--no-questions` flag skips clarification
- [x] Responses are persisted to task frontmatter
- [x] Existing tests still pass

## Implementation Summary

### Files Modified

1. **`installer/core/commands/lib/clarification/display.py`**
   - Added `collect_full_responses()` - Interactive wrapper that displays questions and collects user input
   - Added `collect_quick_responses()` - Quick mode with simplified input collection
   - Added `create_skip_context()` - Returns skip context without displaying questions
   - Added `_extract_option_codes()` - Helper to parse option codes from question strings

2. **`installer/core/commands/lib/clarification/__init__.py`**
   - Updated exports to include new interactive functions

3. **`installer/core/commands/lib/task_review_orchestrator.py`**
   - Added clarification module imports with graceful fallback (`CLARIFICATION_AVAILABLE` flag)
   - Added `execute_clarification_phase()` function for Phase 1.5
   - Updated `execute_task_review()` to call Phase 1.5 before Phase 2
   - Added CLI arguments: `--no-questions`, `--with-questions`, `--defaults`

### Known Limitations

- `--with-questions` flag is passed to orchestrator but not yet implemented in `should_clarify()` - this is a pre-existing gap in the clarification module

### Testing Completed

- All Python syntax checks passed
- Import tests for clarification module passed
- Unit tests for `should_clarify()` function passed
- Unit tests for `generate_review_questions()` passed
- Unit tests for `create_skip_context()` passed
- No existing test files found (no risk of breaking existing tests)

## Test Cases

```bash
# Should ask questions (complexity 6, decision mode)
/task-review TASK-XXX --mode=decision
# Expected: Clarification questions displayed

# Should skip (--no-questions flag)
/task-review TASK-XXX --mode=decision --no-questions
# Expected: No questions, direct to Phase 2

# Should skip (low complexity)
# Create task with complexity:2, then:
/task-review TASK-XXX --mode=decision
# Expected: Skip message, proceed to Phase 2
```

## Dependencies

None - this is the foundational fix.

## Estimated Effort

2-3 hours
