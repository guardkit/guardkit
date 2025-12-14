# Review Report: TASK-REV-0614

## Clarifying Questions Regression in Feature-Plan Command

**Review Mode**: technical-debt
**Review Depth**: standard
**Date**: 2025-12-13
**Reviewer**: Automated Review Analysis

---

## Executive Summary

**Root Cause Identified**: The clarifying questions feature was **designed and documented** but **not implemented** in the actual Python orchestrators.

The clarification modules (`lib/clarification/`) contain well-structured code for:
- Question generation (`generators/review_generator.py`)
- Display formatting (`display.py`)
- Mode detection (`core.py` - `should_clarify()`)
- Persistence (`core.py` - `ClarificationContext`)

However, **the `task_review_orchestrator.py` does NOT call any clarification functions**. The orchestrator proceeds directly from Phase 1 (Load Context) to Phase 2 (Execute Analysis) without ever invoking clarification.

**Impact**: High - The feature exists only in documentation and unit tests, not in production workflow.

**Recommended Fix**: Medium complexity (4-6 hours) - Wire up existing modules to orchestrator.

---

## Technical Debt Inventory

### TD-001: Clarification Module Not Integrated with Orchestrator

**Severity**: Critical
**Location**: `installer/core/commands/lib/task_review_orchestrator.py`
**Type**: Missing Integration

**Evidence**:
- `task_review_orchestrator.py` imports are limited to:
  ```python
  from task_utils import (read_task_file, update_task_frontmatter, ...)
  from git_state_helper import get_git_root
  ```
- No imports from `lib/clarification/` module
- `load_review_context()` function (Phase 1) does NOT call:
  - `should_clarify()` to determine clarification mode
  - `generate_review_questions()` to create questions
  - `display_full_questions()` or `display_quick_questions()`
  - `process_responses()` to handle user input

**Root Cause**: The orchestrator was likely implemented before the clarification module was fully designed, and the integration step was never completed.

---

### TD-002: Test-Only Implementation Pattern

**Severity**: High
**Location**: `tests/integration/lib/clarification/test_feature_plan_clarification.py`

**Evidence**:
The integration tests mock the entire workflow rather than testing actual integration:
```python
def execute_feature_plan(feature_desc, flags=None):
    """Mock function representing feature-plan workflow."""
    # Step 2: Context A - Review scope clarification
    review_clarification = None
    if not flags.get("no_questions", False):
        questions = generate_review_questions(feature_desc, mode='decision')
        with patch('builtins.input', return_value=''):
            review_clarification = display_questions_full(...)
```

This test shows what SHOULD happen but doesn't verify it actually happens in the real orchestrator.

---

### TD-003: Documentation-Reality Mismatch

**Severity**: High
**Location**: Multiple documentation files

**Files Affected**:
1. `CLAUDE.md` - Describes clarification flow that doesn't execute
2. `installer/core/commands/feature-plan.md` - Documents Context A/B questions
3. `installer/core/commands/task-review.md` - Documents Phase 1 clarification

**Evidence from Documentation** (feature-plan.md lines 64-75):
```markdown
### Context A: Review Scope Clarification
**When**: During Step 2 (Execute Task Review), before analysis begins.
**Gating**: Context A triggers for decision mode tasks (which feature-plan uses)
unless `--no-questions` is specified.
```

This is documented but never implemented.

---

### TD-004: Complexity Gating Logic Exists But Unused

**Severity**: Medium
**Location**: `installer/core/commands/lib/clarification/core.py`

**Evidence**:
The `should_clarify()` function is fully implemented:
```python
def should_clarify(
    context_type: Literal["review", "implement_prefs", "planning"],
    complexity: int,
    flags: Dict[str, Any]
) -> ClarificationMode:
    """Determine clarification mode based on context and complexity."""
    # ... correctly implements gating logic
```

But it's never called from any orchestrator.

---

### TD-005: Feature-Plan Relies on Markdown Instructions Only

**Severity**: Medium
**Location**: `installer/core/commands/feature-plan.md`

**Evidence**:
The feature-plan command is a **markdown-only** specification (no Python orchestrator):
```markdown
### Implementation Notes

### Markdown Orchestration (No SDK Required)

This command uses **markdown instruction expansion** - the slash command file
contains instructions that Claude Code interprets and executes.
```

This means:
1. Claude must read and follow the markdown instructions
2. Claude doesn't automatically call Python clarification modules
3. There's no enforcement mechanism for the clarification flow

---

## Gap Analysis

### What Exists (Complete)

| Component | Location | Status |
|-----------|----------|--------|
| Question templates | `lib/clarification/templates/review_scope.py` | Complete |
| Question generator | `lib/clarification/generators/review_generator.py` | Complete |
| Display formatting | `lib/clarification/display.py` | Complete |
| Mode detection | `lib/clarification/core.py` | Complete |
| Persistence | `ClarificationContext.persist_to_frontmatter()` | Complete |
| Unit tests | `tests/unit/lib/clarification/` | Complete |

### What's Missing (Integration Gap)

| Gap | Location | Required Work |
|-----|----------|---------------|
| Orchestrator integration | `task_review_orchestrator.py` | Add imports and calls |
| Phase 1.5 insertion | `execute_task_review()` | Add clarification phase |
| Flag handling | CLI argument parsing | Wire `--no-questions`, etc. |
| Feature-plan awareness | Claude instruction | Explicit orchestrator call |

---

## Recommendations

### REC-001: Integrate Clarification into Task-Review Orchestrator

**Priority**: Critical
**Effort**: 2-3 hours

Modify `task_review_orchestrator.py`:

1. Add imports:
```python
from clarification import (
    should_clarify,
    ClarificationMode,
    generate_review_questions,
    display_full_questions,
    display_quick_questions,
    process_responses,
    ClarificationContext,
)
```

2. Add Phase 1.5 after `load_review_context()`:
```python
# Phase 1.5: Clarification (if needed)
mode = should_clarify("review", complexity, flags)
if mode != ClarificationMode.SKIP:
    questions = generate_review_questions(task_context, review_mode, complexity)
    if mode == ClarificationMode.FULL:
        clarification = display_full_questions(questions, ...)
    else:  # QUICK
        clarification = display_quick_questions(questions, ...)
    task_context['clarification'] = clarification
```

---

### REC-002: Add Explicit Feature-Plan Orchestrator

**Priority**: High
**Effort**: 2-3 hours

Create `feature_plan_orchestrator.py` that:
1. Creates review task (calls task creation logic)
2. Invokes `task_review_orchestrator.execute_task_review()` with proper flags
3. Handles [I]mplement flow with Context B clarification

This ensures feature-plan always executes clarification rather than relying on markdown interpretation.

---

### REC-003: Update Integration Tests to Test Real Integration

**Priority**: Medium
**Effort**: 1-2 hours

Replace mocked tests with actual orchestrator calls:
```python
def test_feature_plan_clarification():
    # Actually call the orchestrator, not a mock
    result = feature_plan_orchestrator.execute(
        "add dark mode",
        flags={}
    )
    assert result['clarification'] is not None
```

---

### REC-004: Add Clarification Smoke Test

**Priority**: Medium
**Effort**: 1 hour

Create a simple end-to-end test that:
1. Creates a review task
2. Runs task-review with decision mode
3. Verifies clarification questions are displayed
4. Verifies responses are persisted to frontmatter

---

## Test Cases for Regression Prevention

### TC-001: Basic Clarification Trigger
```bash
/task-create "Review authentication architecture" task_type:review complexity:6
/task-review TASK-XXX --mode=decision
# EXPECTED: Context A clarification questions displayed
# ACTUAL: Questions should be asked (currently skipped)
```

### TC-002: Feature-Plan Clarification
```bash
/feature-plan "lets create the base application infrastructure"
# EXPECTED: Ambiguous input triggers clarification
# ACTUAL: Should ask about technology, scope, priorities
```

### TC-003: Skip Flag Honored
```bash
/task-review TASK-XXX --mode=decision --no-questions
# EXPECTED: No clarification questions
# ACTUAL: Should proceed directly (but this path isn't even reached now)
```

### TC-004: Complexity Gating
```bash
/task-work TASK-XXX  # complexity: 2
# EXPECTED: Skip clarification (too simple)

/task-work TASK-YYY  # complexity: 6
# EXPECTED: Full clarification mode
```

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Integration breaks existing workflow | Low | High | Add `--no-questions` as fallback |
| Questions are annoying to users | Medium | Medium | Complexity gating works correctly |
| Timeout handling fails | Low | Medium | Test quick mode thoroughly |
| Persistence corrupts frontmatter | Low | High | Unit tests already validate YAML |

---

## Timeline Estimate

| Task | Effort | Dependencies |
|------|--------|--------------|
| REC-001: Orchestrator integration | 2-3 hours | None |
| REC-002: Feature-plan orchestrator | 2-3 hours | REC-001 |
| REC-003: Update integration tests | 1-2 hours | REC-001 |
| REC-004: Smoke test | 1 hour | REC-001 |

**Total**: 6-9 hours (1-1.5 days)

---

## Decision Support

### Option A: Full Fix (Recommended)
- Implement REC-001 through REC-004
- Timeline: 1-1.5 days
- Result: Clarification fully working as documented

### Option B: Minimal Fix
- Implement REC-001 only (orchestrator integration)
- Timeline: 3-4 hours
- Result: Basic clarification working, some edge cases may not work

### Option C: Documentation Update
- Update documentation to match current behavior
- Timeline: 1 hour
- Result: No user-facing improvement, just accurate docs

---

## Appendix: Evidence from User Test

From `/docs/reviews/clarifying-questions/feature-plan-test.md`:

**Input**: `/feature-plan lets create the base application infrastructure`

**What Happened**:
1. Task TASK-REV-07FC created automatically
2. **No clarification questions asked**
3. System assumed FastAPI + Python (major assumption)
4. Proceeded directly to full technical analysis
5. Generated 5 technical options without user input

**What Should Have Happened**:
1. Task created
2. **Context A clarification**:
   - "What technology stack are you using?"
   - "What type of application?" (web, API, CLI, etc.)
   - "What is your trade-off priority?" (speed, quality, cost)
3. Execute review based on clarified scope
4. Present decision checkpoint
