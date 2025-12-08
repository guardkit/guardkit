---
id: TASK-CLQ-012
title: Testing & user acceptance
status: backlog
created: 2025-12-08T14:00:00Z
updated: 2025-12-08T14:00:00Z
priority: high
tags: [clarifying-questions, testing, acceptance, wave-4]
complexity: 5
parent_feature: clarifying-questions
wave: 4
conductor_workspace: clarifying-questions-wave4-testing
implementation_method: task-work
---

# Task: Testing & user acceptance

## Description

Implement comprehensive testing for the clarifying questions feature including unit tests, integration tests, and user acceptance testing. Ensure all three contexts work correctly and edge cases are handled.

## Acceptance Criteria

### Unit Tests
- [ ] Test Question dataclass serialization/deserialization
- [ ] Test Decision dataclass with all fields
- [ ] Test ClarificationContext persistence to frontmatter
- [ ] Test ClarificationContext loading from frontmatter
- [ ] Test each detection function in detection.py
- [ ] Test question generation for all 3 contexts
- [ ] Test display formatting functions

### Integration Tests
- [ ] Test task-work Phase 1.5 flow (skip, quick, full modes)
- [ ] Test task-review Context A flow (review scope)
- [ ] Test task-review Context B flow ([I]mplement handler)
- [ ] Test feature-plan clarification propagation
- [ ] Test command-line flag handling
- [ ] Test timeout behavior in quick mode
- [ ] Test inline answers parsing

### User Acceptance Tests
- [ ] Create test scenarios document
- [ ] Execute 3 real task-work workflows with clarification
- [ ] Execute 2 real task-review workflows with clarification
- [ ] Execute 1 real feature-plan workflow end-to-end
- [ ] Document feedback and issues found
- [ ] Verify rework rate reduction (baseline vs with clarification)

## Technical Specification

### Unit Test Structure

```python
# tests/unit/lib/clarification/test_core.py

import pytest
from lib.clarification.core import Question, Decision, ClarificationContext
from datetime import datetime
from pathlib import Path


class TestQuestion:
    def test_question_with_all_fields(self):
        q = Question(
            id="scope",
            category="scope",
            text="How comprehensive?",
            options=["[M]inimal", "[S]tandard", "[C]omplete"],
            default="S",
            rationale="Standard is typical",
        )
        assert q.id == "scope"
        assert q.default == "S"
        assert len(q.options) == 3

    def test_question_serialization(self):
        q = Question(id="test", category="test", text="Test?", options=["Y", "N"], default="Y")
        data = q.to_dict()
        restored = Question.from_dict(data)
        assert restored.id == q.id
        assert restored.text == q.text


class TestDecision:
    def test_decision_with_default(self):
        d = Decision(
            question_id="scope",
            category="scope",
            question_text="How comprehensive?",
            answer="standard",
            answer_display="Standard - With error handling",
            default_used=True,
            rationale="Default selected",
        )
        assert d.default_used is True

    def test_decision_without_default(self):
        d = Decision(
            question_id="scope",
            category="scope",
            question_text="How comprehensive?",
            answer="complete",
            answer_display="Complete - Production-ready",
            default_used=False,
            rationale="User explicitly chose complete",
        )
        assert d.default_used is False


class TestClarificationContext:
    def test_persist_to_frontmatter(self, tmp_path):
        # Create test task file
        task_file = tmp_path / "TASK-test.md"
        task_file.write_text("""---
id: TASK-test
title: Test task
status: backlog
complexity: 5
---

# Test Task
""")

        # Create clarification context
        ctx = ClarificationContext(
            context_type="implementation_planning",
            mode="full",
            decisions=[
                Decision(
                    question_id="scope",
                    category="scope",
                    question_text="How comprehensive?",
                    answer="standard",
                    answer_display="Standard",
                    default_used=True,
                    rationale="Default",
                )
            ]
        )

        # Persist
        ctx.persist_to_frontmatter(task_file)

        # Verify
        content = task_file.read_text()
        assert "clarification:" in content
        assert "context: implementation_planning" in content
        assert "question_id: scope" in content

    def test_load_from_frontmatter(self, tmp_path):
        task_file = tmp_path / "TASK-test.md"
        task_file.write_text("""---
id: TASK-test
title: Test task
clarification:
  context: implementation_planning
  timestamp: 2025-12-08T14:30:00
  mode: full
  decisions:
    - question_id: scope
      category: scope
      question: How comprehensive?
      answer: standard
      answer_text: Standard
      default_used: true
      rationale: Default
---

# Test Task
""")

        ctx = ClarificationContext.load_from_frontmatter(task_file)

        assert ctx is not None
        assert ctx.context_type == "implementation_planning"
        assert ctx.mode == "full"
        assert len(ctx.decisions) == 1
        assert ctx.decisions[0].question_id == "scope"

    def test_load_from_frontmatter_no_clarification(self, tmp_path):
        task_file = tmp_path / "TASK-test.md"
        task_file.write_text("""---
id: TASK-test
title: Test task
---

# Test Task
""")

        ctx = ClarificationContext.load_from_frontmatter(task_file)
        assert ctx is None


# tests/unit/lib/clarification/test_detection.py

class TestDetection:
    def test_detect_scope_ambiguity_vague_description(self):
        from lib.clarification.detection import detect_scope_ambiguity

        # Vague task description
        task_desc = "improve the system"
        result = detect_scope_ambiguity(task_desc)
        assert result.is_ambiguous is True
        assert "scope" in result.reason.lower()

    def test_detect_scope_ambiguity_specific_description(self):
        from lib.clarification.detection import detect_scope_ambiguity

        task_desc = "Add JWT authentication to /api/login endpoint with refresh token support"
        result = detect_scope_ambiguity(task_desc)
        assert result.is_ambiguous is False

    def test_detect_technology_ambiguity(self):
        from lib.clarification.detection import detect_technology_ambiguity

        # Multiple tech options mentioned
        task_desc = "Add authentication (could use JWT, sessions, or OAuth)"
        result = detect_technology_ambiguity(task_desc)
        assert result.is_ambiguous is True

    def test_detect_tradeoff_ambiguity(self):
        from lib.clarification.detection import detect_tradeoff_ambiguity

        task_desc = "Optimize database queries for better performance"
        result = detect_tradeoff_ambiguity(task_desc)
        # Should detect performance vs complexity tradeoff
        assert result.is_ambiguous is True
```

### Integration Test Structure

```python
# tests/integration/lib/clarification/test_task_work_clarification.py

import pytest
from unittest.mock import patch, MagicMock


class TestTaskWorkClarification:
    def test_phase_15_skip_low_complexity(self):
        """Complexity 1-2 should skip clarification."""
        task = create_test_task(complexity=2)

        with patch('lib.clarification.display_questions_full') as mock_display:
            result = execute_task_work_phase_15(task, flags={})

        mock_display.assert_not_called()
        assert result.clarification is None

    def test_phase_15_quick_medium_complexity(self):
        """Complexity 3-4 should use quick mode with timeout."""
        task = create_test_task(complexity=4)

        with patch('lib.clarification.display_questions_quick') as mock_display:
            mock_display.return_value = ClarificationContext(
                context_type="implementation_planning",
                mode="quick",
                decisions=[],
            )
            result = execute_task_work_phase_15(task, flags={})

        mock_display.assert_called_once()
        call_args = mock_display.call_args
        assert call_args.kwargs.get('timeout') == 15

    def test_phase_15_full_high_complexity(self):
        """Complexity 5+ should use full blocking mode."""
        task = create_test_task(complexity=6)

        with patch('lib.clarification.display_questions_full') as mock_display:
            mock_display.return_value = ClarificationContext(
                context_type="implementation_planning",
                mode="full",
                decisions=[],
            )
            result = execute_task_work_phase_15(task, flags={})

        mock_display.assert_called_once()

    def test_no_questions_flag(self):
        """--no-questions should skip clarification regardless of complexity."""
        task = create_test_task(complexity=8)

        with patch('lib.clarification.display_questions_full') as mock_display:
            result = execute_task_work_phase_15(task, flags={'no_questions': True})

        mock_display.assert_not_called()
        assert result.clarification is None

    def test_with_questions_flag(self):
        """--with-questions should force clarification for low complexity."""
        task = create_test_task(complexity=1)

        with patch('lib.clarification.display_questions_full') as mock_display:
            mock_display.return_value = ClarificationContext(
                context_type="implementation_planning",
                mode="full",
                decisions=[],
            )
            result = execute_task_work_phase_15(task, flags={'with_questions': True})

        mock_display.assert_called_once()

    def test_inline_answers(self):
        """--answers should parse and apply inline answers."""
        task = create_test_task(complexity=5)

        result = execute_task_work_phase_15(
            task,
            flags={'answers': 'scope:standard testing:integration'}
        )

        assert result.clarification is not None
        assert len(result.clarification.decisions) >= 2

        scope_decision = next(d for d in result.clarification.decisions if d.question_id == 'scope')
        assert scope_decision.answer == 'standard'


# tests/integration/lib/clarification/test_task_review_clarification.py

class TestTaskReviewClarification:
    def test_context_a_review_scope(self):
        """Context A should ask review scope questions."""
        task = create_test_task(task_type='review', complexity=5)

        with patch('lib.clarification.display_questions_full') as mock_display:
            mock_display.return_value = ClarificationContext(
                context_type="review_scope",
                mode="full",
                decisions=[],
            )
            result = execute_task_review_phase_1(task, mode='decision', flags={})

        mock_display.assert_called_once()

    def test_context_b_implement_handler(self):
        """Context B should ask implementation prefs at [I]mplement."""
        findings = create_test_findings(options=3)

        with patch('lib.clarification.display_questions_full') as mock_display:
            mock_display.return_value = ClarificationContext(
                context_type="implementation_prefs",
                mode="full",
                decisions=[],
            )
            result = handle_implement_decision(findings, flags={})

        mock_display.assert_called_once()
```

### User Acceptance Test Scenarios

```markdown
# User Acceptance Test Scenarios

## Scenario 1: task-work with Full Clarification

**Setup**: Create task with complexity 6
**Steps**:
1. Run `/task-work TASK-XXX`
2. Verify Phase 1.5 triggers
3. Answer 3-4 questions
4. Verify answers recorded in frontmatter
5. Verify Phase 2 uses clarification context

**Expected**: Planning reflects user's answers, not defaults

## Scenario 2: task-work with Quick Timeout

**Setup**: Create task with complexity 4
**Steps**:
1. Run `/task-work TASK-XXX`
2. Verify quick mode triggers (15s timeout shown)
3. Let timeout expire
4. Verify defaults applied
5. Check frontmatter shows default_used: true

**Expected**: Workflow continues after timeout with defaults

## Scenario 3: task-review with Review Scope

**Setup**: Create review task
**Steps**:
1. Run `/task-review TASK-XXX --mode=decision`
2. Answer review scope questions
3. Verify review focuses on specified area
4. At checkpoint, choose [I]mplement
5. Answer implementation preference questions
6. Verify subtasks reflect preferences

**Expected**: Both Context A and B flow correctly

## Scenario 4: feature-plan End-to-End

**Setup**: None (feature-plan creates task)
**Steps**:
1. Run `/feature-plan "add dark mode"`
2. Answer review scope questions (Context A)
3. Review findings
4. Choose [I]mplement
5. Answer implementation preference questions (Context B)
6. Verify generated subtasks match preferences

**Expected**: Full clarification flow through feature-plan

## Scenario 5: Skip Clarification

**Setup**: Create task with complexity 8
**Steps**:
1. Run `/task-work TASK-XXX --no-questions`
2. Verify Phase 1.5 skipped
3. Verify planning uses defaults
4. Check frontmatter has no clarification section

**Expected**: Clarification completely bypassed

## Scenario 6: Inline Answers (CI/CD)

**Setup**: Create task with complexity 5
**Steps**:
1. Run `/task-work TASK-XXX --answers="scope:minimal testing:unit"`
2. Verify no interactive prompts
3. Verify answers applied correctly
4. Check frontmatter reflects inline answers

**Expected**: Non-interactive execution for automation
```

## Files to Create

1. `tests/unit/lib/clarification/test_core.py`
2. `tests/unit/lib/clarification/test_detection.py`
3. `tests/unit/lib/clarification/test_display.py`
4. `tests/unit/lib/clarification/test_generators.py`
5. `tests/integration/lib/clarification/test_task_work_clarification.py`
6. `tests/integration/lib/clarification/test_task_review_clarification.py`
7. `tests/integration/lib/clarification/test_feature_plan_clarification.py`
8. `docs/testing/clarification-uat-scenarios.md`

## Why /task-work Method

- Comprehensive testing requires quality gates
- Multiple test files and scenarios
- Integration tests need careful architecture
- Higher complexity (5/10)
- User acceptance testing documentation

## Dependencies

- Wave 1-3: All modules must be implemented
- TASK-CLQ-010: Persistence must work for frontmatter tests

## Related Tasks

- TASK-CLQ-010 (persistence - parallel)
- TASK-CLQ-011 (documentation - parallel)

## Success Metrics

After testing completion:
- [ ] 100% unit test pass rate
- [ ] 100% integration test pass rate
- [ ] 6 UAT scenarios executed successfully
- [ ] No critical bugs found
- [ ] Rework rate baseline established (measure 5 tasks without clarification, 5 with)

## Reference

See [Review Report Section: Testing Strategy](./../../../.claude/reviews/TASK-REV-B130-review-report.md#testing-strategy).
