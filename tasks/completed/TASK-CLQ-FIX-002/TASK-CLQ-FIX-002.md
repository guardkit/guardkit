---
id: TASK-CLQ-FIX-002
title: "Create feature-plan Python orchestrator for clarification enforcement"
status: completed
created: 2025-12-13T16:35:00Z
updated: 2025-12-13T18:30:00Z
completed: 2025-12-13T18:30:00Z
priority: high
tags: [clarifying-questions, orchestrator, feature-plan, integration]
complexity: 5
parent_review: TASK-REV-0614
implementation_mode: task-work
dependencies: [TASK-CLQ-FIX-001]
code_review_score: 8.2
test_count: 39
test_pass_rate: 100%
---

# Task: Create feature-plan Python orchestrator

## Description

Create `feature_plan_orchestrator.py` to enforce the clarification flow for `/feature-plan` commands. Currently, feature-plan relies entirely on markdown instructions which Claude may or may not follow consistently.

## Why This Is Needed

The current approach:
1. `/feature-plan` is a markdown-only command
2. Claude reads `feature-plan.md` and follows instructions
3. No enforcement of clarification flow
4. Inconsistent behavior depending on Claude's interpretation

The fix:
1. Create Python orchestrator that enforces the flow
2. Orchestrator calls `task_review_orchestrator.execute_task_review()` with proper flags
3. Handles Context B (implementation preferences) after [I]mplement decision

## Implementation Details

### New File

`installer/core/commands/lib/feature_plan_orchestrator.py`

### Key Functions

```python
def execute_feature_plan(
    feature_description: str,
    flags: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Main orchestrator for /feature-plan command.

    Steps:
    1. Create review task automatically
    2. Execute task-review with --mode=decision (includes Context A clarification)
    3. Present decision checkpoint
    4. If [I]mplement: Execute Context B clarification
    5. Generate feature structure with subtasks
    """

def create_review_task(feature_description: str) -> str:
    """Create the review task and return task ID."""

def execute_context_b_clarification(
    review_findings: Dict[str, Any],
    num_subtasks: int
) -> ClarificationContext:
    """Ask implementation preference questions (Context B)."""

def generate_feature_structure(
    feature_slug: str,
    recommendations: List[Dict],
    clarification: ClarificationContext
) -> Path:
    """Create the feature folder with README, guide, and subtasks."""
```

### Integration with task-review orchestrator

```python
from task_review_orchestrator import execute_task_review

def execute_feature_plan(feature_description: str, flags: Dict[str, Any]):
    # Step 1: Create review task
    task_id = create_review_task(feature_description)
    print(f"Created review task: {task_id}")

    # Step 2: Execute task-review with decision mode
    # This now includes Context A clarification (from TASK-CLQ-FIX-001)
    review_result = execute_task_review(
        task_id=task_id,
        mode="decision",
        depth="standard",
        no_questions=flags.get('no_questions', False),
        with_questions=flags.get('with_questions', False)
    )

    # Step 3: Present decision checkpoint
    decision = review_result.get('decision', 'accept')

    if decision == 'implement':
        # Step 4: Context B clarification
        if not flags.get('no_questions'):
            impl_clarification = execute_context_b_clarification(
                review_result.get('findings', {}),
                num_subtasks=len(review_result.get('recommendations', []))
            )
        else:
            impl_clarification = None

        # Step 5: Generate feature structure
        feature_path = generate_feature_structure(
            feature_slug=extract_feature_slug(feature_description),
            recommendations=review_result.get('recommendations', []),
            clarification=impl_clarification
        )

        return {
            "status": "success",
            "review_task": task_id,
            "feature_path": str(feature_path),
            "subtasks_created": True
        }

    return {
        "status": "success",
        "review_task": task_id,
        "decision": decision
    }
```

## Acceptance Criteria

- [x] Orchestrator creates review task automatically
- [x] Calls task-review orchestrator with correct flags
- [x] Context B clarification triggers after [I]mplement
- [x] `--no-questions` skips both Context A and B
- [x] Feature structure is generated correctly
- [x] Existing feature-plan.md still works (backward compatible)

## Test Cases

```bash
# Full flow with clarification
/feature-plan "add user authentication"
# Expected: Context A questions, then [I]mplement triggers Context B

# Skip clarification
/feature-plan "add user authentication" --no-questions
# Expected: No questions, use defaults throughout

# Ambiguous input
/feature-plan "lets create the base application infrastructure"
# Expected: Technology/scope questions before proceeding
```

## Dependencies

- TASK-CLQ-FIX-001 (task-review orchestrator integration)

## Estimated Effort

2-3 hours
