"""Unit tests for lib/clarification/core.py

Tests the core dataclasses and persistence functionality for the clarifying questions feature.
"""

import pytest
from datetime import datetime
from pathlib import Path
import tempfile
import yaml

# Import from clarification module (installer/core/commands/lib/clarification)
from clarification.core import (
    Question,
    Decision,
    ClarificationContext,
    ClarificationMode,
    should_clarify,
)


class TestQuestion:
    """Test Question dataclass functionality."""

    def test_question_with_all_fields(self):
        """Test creating a question with all fields populated."""
        q = Question(
            id="scope",
            category="scope",
            text="How comprehensive should the implementation be?",
            options=["[M]inimal", "[S]tandard", "[C]omplete"],
            default="[S]tandard",
            rationale="Standard implementation is typical for most tasks",
        )
        assert q.id == "scope"
        assert q.category == "scope"
        assert q.text == "How comprehensive should the implementation be?"
        assert q.default == "[S]tandard"
        assert len(q.options) == 3
        assert "[M]inimal" in q.options

    def test_question_minimal_fields(self):
        """Test creating a question with only required fields."""
        q = Question(
            id="test",
            category="test",
            text="Test question?",
            options=["[Y]es", "[N]o"],
            default="[Y]es",
            rationale="Yes is the safe default",
        )
        assert q.id == "test"
        assert q.category == "test"
        assert q.default == "[Y]es"
        assert q.rationale == "Yes is the safe default"

    def test_question_validation_default_in_options(self):
        """Test that Question validates default is in options."""
        # Valid: default in options
        q = Question(
            id="test",
            category="scope",
            text="Test question?",
            options=["[Y]es", "[N]o"],
            default="[Y]es",
            rationale="Testing is important",
        )
        assert q.default == "[Y]es"

        # Invalid: default not in options
        with pytest.raises(ValueError, match="Default .* must be in options"):
            Question(
                id="test",
                category="scope",
                text="Test question?",
                options=["[Y]es", "[N]o"],
                default="[M]aybe",
                rationale="Testing is important",
            )

    def test_question_validation_empty_fields(self):
        """Test that Question validates required fields are not empty."""
        # Valid question
        q = Question(
            id="test",
            category="test",
            text="Test?",
            options=["A", "B"],
            default="A",
            rationale="A is default",
        )
        assert q.id == "test"

        # Invalid: empty ID
        with pytest.raises(ValueError, match="Question ID cannot be empty"):
            Question(
                id="",
                category="test",
                text="Test?",
                options=["A", "B"],
                default="A",
                rationale="A is default",
            )

        # Invalid: empty text
        with pytest.raises(ValueError, match="Question text cannot be empty"):
            Question(
                id="test",
                category="test",
                text="",
                options=["A", "B"],
                default="A",
                rationale="A is default",
            )

        # Invalid: no options
        with pytest.raises(ValueError, match="Question must have at least one option"):
            Question(
                id="test",
                category="test",
                text="Test?",
                options=[],
                default="A",
                rationale="A is default",
            )


class TestDecision:
    """Test Decision dataclass functionality."""

    def test_decision_with_default(self):
        """Test decision created from default selection."""
        d = Decision(
            question_id="scope",
            category="scope",
            question_text="How comprehensive?",
            answer="standard",
            answer_display="Standard - With error handling",
            default_used=True,
            rationale="Default selected - user didn't override",
        )
        assert d.question_id == "scope"
        assert d.category == "scope"
        assert d.default_used is True
        assert "Default selected" in d.rationale

    def test_decision_without_default(self):
        """Test decision with explicit user choice."""
        d = Decision(
            question_id="scope",
            category="scope",
            question_text="How comprehensive?",
            answer="complete",
            answer_display="Complete - Production-ready with full error handling",
            default_used=False,
            rationale="User explicitly chose complete implementation",
        )
        assert d.question_id == "scope"
        assert d.answer == "complete"
        assert d.default_used is False
        assert "explicitly chose" in d.rationale

    def test_decision_properties(self):
        """Test Decision backward compatibility properties."""
        d = Decision(
            question_id="testing",
            category="quality",
            question_text="What testing level?",
            answer="integration",
            answer_display="Integration - E2E tests",
            default_used=False,
            rationale="High-risk feature needs integration tests",
        )

        # Test backward compatibility properties
        assert d.is_default == d.default_used
        assert d.question == d.question_text

        # Test with default_used=True
        d2 = Decision(
            question_id="scope",
            category="scope",
            question_text="How comprehensive?",
            answer="standard",
            answer_display="Standard",
            default_used=True,
            rationale="Default selected",
        )
        assert d2.is_default is True
        assert d2.question == "How comprehensive?"

    def test_decision_confidence_validation(self):
        """Test Decision validates confidence is 0-1."""
        # Valid: confidence in range
        d = Decision(
            question_id="test",
            category="test",
            question_text="Test?",
            answer="yes",
            answer_display="Yes",
            default_used=False,
            rationale="Test",
            confidence=0.8,
        )
        assert d.confidence == 0.8

        # Invalid: confidence > 1
        with pytest.raises(ValueError, match="Confidence must be between 0 and 1"):
            Decision(
                question_id="test",
                category="test",
                question_text="Test?",
                answer="yes",
                answer_display="Yes",
                default_used=False,
                rationale="Test",
                confidence=1.5,
            )

        # Invalid: confidence < 0
        with pytest.raises(ValueError, match="Confidence must be between 0 and 1"):
            Decision(
                question_id="test",
                category="test",
                question_text="Test?",
                answer="yes",
                answer_display="Yes",
                default_used=False,
                rationale="Test",
                confidence=-0.1,
            )


class TestClarificationContext:
    """Test ClarificationContext functionality."""

    @pytest.fixture
    def temp_task_file(self):
        """Create a temporary task file for testing."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write("""---
id: TASK-test
title: Test task
status: backlog
complexity: 5
---

# Test Task

This is a test task.
""")
            temp_path = Path(f.name)

        yield temp_path

        # Cleanup
        if temp_path.exists():
            temp_path.unlink()

    def test_persist_to_frontmatter(self, temp_task_file):
        """Test persisting clarification context to task frontmatter."""
        # Create clarification context
        ctx = ClarificationContext(
            context_type="implementation_planning",
            mode="full",
        )

        # Add decisions
        ctx.add_decision(Decision(
            question_id="scope",
            category="scope",
            question_text="How comprehensive?",
            answer="standard",
            answer_display="Standard - With error handling",
            default_used=True,
            rationale="Default selected",
        ))
        ctx.add_decision(Decision(
            question_id="testing",
            category="quality",
            question_text="What testing level?",
            answer="unit",
            answer_display="Unit tests only",
            default_used=False,
            rationale="User chose unit tests",
        ))

        # Persist to frontmatter
        ctx.persist_to_frontmatter(temp_task_file)

        # Verify file was updated
        content = temp_task_file.read_text()
        assert "clarification:" in content
        assert "context: implementation_planning" in content
        assert "mode: full" in content
        assert "question_id: scope" in content
        assert "question_id: testing" in content
        assert "default_used: true" in content

        # Verify YAML is valid
        lines = content.split('\n')
        frontmatter_lines = []
        in_frontmatter = False
        frontmatter_count = 0

        for line in lines:
            if line.strip() == '---':
                frontmatter_count += 1
                if frontmatter_count == 1:
                    in_frontmatter = True
                    continue
                elif frontmatter_count == 2:
                    break
            if in_frontmatter:
                frontmatter_lines.append(line)

        frontmatter_yaml = '\n'.join(frontmatter_lines)
        parsed = yaml.safe_load(frontmatter_yaml)
        assert 'clarification' in parsed
        assert parsed['clarification']['context'] == 'implementation_planning'

    def test_load_from_frontmatter(self, temp_task_file):
        """Test loading clarification context from task frontmatter."""
        # Write task file with clarification data
        temp_task_file.write_text("""---
id: TASK-test
title: Test task
complexity: 5
clarification:
  context: implementation_planning
  timestamp: '2025-12-08T14:30:00'
  mode: full
  decisions:
    - question_id: scope
      category: scope
      question: How comprehensive?
      answer: standard
      answer_text: Standard - With error handling
      default_used: true
      rationale: Default selected
    - question_id: testing
      category: quality
      question: What testing level?
      answer: unit
      answer_text: Unit tests only
      default_used: false
      rationale: User chose unit tests
---

# Test Task

This is a test task.
""")

        # Load context
        ctx = ClarificationContext.load_from_frontmatter(temp_task_file)

        # Verify loaded correctly
        assert ctx is not None
        assert ctx.context_type == "implementation_planning"
        assert ctx.mode == "full"
        assert len(ctx.decisions) == 2

        # Decisions are ordered: explicit first, then defaults
        # "testing" is explicit (default_used=false), "scope" is default (default_used=true)
        testing_decision = ctx.decisions[0]
        assert testing_decision.question_id == "testing"
        assert testing_decision.category == "quality"
        assert testing_decision.answer == "unit"
        assert testing_decision.default_used is False

        scope_decision = ctx.decisions[1]
        assert scope_decision.question_id == "scope"
        assert scope_decision.category == "scope"
        assert scope_decision.answer == "standard"
        assert scope_decision.default_used is True

    def test_load_from_frontmatter_no_clarification(self, temp_task_file):
        """Test loading from frontmatter when no clarification exists."""
        # Task file without clarification field
        temp_task_file.write_text("""---
id: TASK-test
title: Test task
status: backlog
---

# Test Task
""")

        ctx = ClarificationContext.load_from_frontmatter(temp_task_file)
        assert ctx is None

    def test_load_from_frontmatter_empty_decisions(self, temp_task_file):
        """Test loading from frontmatter with empty decisions list."""
        temp_task_file.write_text("""---
id: TASK-test
title: Test task
clarification:
  context: implementation_planning
  timestamp: '2025-12-08T14:30:00'
  mode: quick
  decisions: []
---

# Test Task
""")

        ctx = ClarificationContext.load_from_frontmatter(temp_task_file)
        assert ctx is not None
        assert ctx.context_type == "implementation_planning"
        assert ctx.mode == "quick"
        assert len(ctx.decisions) == 0

    def test_context_add_decision(self):
        """Test adding decisions to ClarificationContext."""
        ctx = ClarificationContext(
            context_type="implementation_planning",
            mode="full",
        )

        # Add explicit decision
        explicit = Decision(
            question_id="scope",
            category="scope",
            question_text="How comprehensive?",
            answer="standard",
            answer_display="Standard",
            default_used=False,
            rationale="User chose standard",
        )
        ctx.add_decision(explicit)

        # Add default decision
        default = Decision(
            question_id="testing",
            category="quality",
            question_text="What testing level?",
            answer="unit",
            answer_display="Unit tests",
            default_used=True,
            rationale="Default selected",
        )
        ctx.add_decision(default)

        # Verify decisions are categorized correctly
        assert len(ctx.explicit_decisions) == 1
        assert len(ctx.assumed_defaults) == 1
        assert ctx.answered_count == 2
        assert ctx.explicit_decisions[0] == explicit
        assert ctx.assumed_defaults[0] == default

    def test_context_modes(self):
        """Test different clarification modes."""
        # Skip mode
        ctx_skip = ClarificationContext(
            context_type="implementation_planning",
            mode="skip",
        )
        assert ctx_skip.mode == "skip"
        assert len(ctx_skip.decisions) == 0

        # Quick mode
        ctx_quick = ClarificationContext(
            context_type="implementation_planning",
            mode="quick",
        )
        assert ctx_quick.mode == "quick"

        # Full mode
        ctx_full = ClarificationContext(
            context_type="implementation_planning",
            mode="full",
        )
        assert ctx_full.mode == "full"

    def test_multiple_persist_cycles(self, temp_task_file):
        """Test persisting multiple times doesn't corrupt data."""
        # First persist
        ctx1 = ClarificationContext(
            context_type="implementation_planning",
            mode="full",
        )
        ctx1.add_decision(Decision(
            question_id="scope",
            category="scope",
            question_text="How comprehensive?",
            answer="standard",
            answer_display="Standard",
            default_used=True,
            rationale="Default",
        ))
        ctx1.persist_to_frontmatter(temp_task_file)

        # Second persist with updated context
        ctx2 = ClarificationContext(
            context_type="implementation_planning",
            mode="full",
        )
        ctx2.add_decision(Decision(
            question_id="scope",
            category="scope",
            question_text="How comprehensive?",
            answer="complete",
            answer_display="Complete",
            default_used=False,
            rationale="User updated",
        ))
        ctx2.persist_to_frontmatter(temp_task_file)

        # Load and verify latest persisted
        loaded = ClarificationContext.load_from_frontmatter(temp_task_file)
        assert loaded is not None
        assert loaded.decisions[0].answer == "complete"
        assert loaded.decisions[0].default_used is False


class TestShouldClarify:
    """Test should_clarify() function for mode determination."""

    def test_no_questions_flag_skips(self):
        """--no-questions flag should always skip clarification."""
        assert should_clarify("planning", 10, {"no_questions": True}) == ClarificationMode.SKIP
        assert should_clarify("review", 8, {"no_questions": True}) == ClarificationMode.SKIP
        assert should_clarify("implement_prefs", 6, {"no_questions": True}) == ClarificationMode.SKIP

    def test_micro_flag_skips(self):
        """--micro flag should always skip clarification."""
        assert should_clarify("planning", 10, {"micro": True}) == ClarificationMode.SKIP
        assert should_clarify("review", 8, {"micro": True}) == ClarificationMode.SKIP

    def test_defaults_flag_uses_defaults(self):
        """--defaults flag should use defaults mode."""
        assert should_clarify("planning", 10, {"defaults": True}) == ClarificationMode.USE_DEFAULTS
        assert should_clarify("review", 8, {"defaults": True}) == ClarificationMode.USE_DEFAULTS

    def test_with_questions_forces_full(self):
        """--with-questions flag should force FULL mode regardless of complexity."""
        # Trivial task (complexity 1) should normally skip
        assert should_clarify("planning", 1, {}) == ClarificationMode.SKIP

        # With --with-questions, should force FULL
        assert should_clarify("planning", 1, {"with_questions": True}) == ClarificationMode.FULL
        assert should_clarify("planning", 2, {"with_questions": True}) == ClarificationMode.FULL

        # Should work for all context types
        assert should_clarify("review", 1, {"with_questions": True}) == ClarificationMode.FULL
        assert should_clarify("review", 2, {"with_questions": True}) == ClarificationMode.FULL
        assert should_clarify("implement_prefs", 1, {"with_questions": True}) == ClarificationMode.FULL

    def test_no_questions_takes_precedence_over_with_questions(self):
        """--no-questions should take precedence over --with-questions."""
        # When both flags are present, no_questions wins
        assert should_clarify("planning", 1, {"with_questions": True, "no_questions": True}) == ClarificationMode.SKIP
        assert should_clarify("planning", 5, {"with_questions": True, "no_questions": True}) == ClarificationMode.SKIP
        assert should_clarify("review", 8, {"with_questions": True, "no_questions": True}) == ClarificationMode.SKIP

    def test_micro_takes_precedence_over_with_questions(self):
        """--micro should take precedence over --with-questions."""
        assert should_clarify("planning", 1, {"with_questions": True, "micro": True}) == ClarificationMode.SKIP

    def test_defaults_takes_precedence_over_with_questions(self):
        """--defaults should take precedence over --with-questions."""
        assert should_clarify("planning", 1, {"with_questions": True, "defaults": True}) == ClarificationMode.USE_DEFAULTS

    def test_complexity_based_routing_planning(self):
        """Test complexity-based routing for 'planning' context."""
        # Complexity 1-2: SKIP
        assert should_clarify("planning", 1, {}) == ClarificationMode.SKIP
        assert should_clarify("planning", 2, {}) == ClarificationMode.SKIP

        # Complexity 3-4: QUICK
        assert should_clarify("planning", 3, {}) == ClarificationMode.QUICK
        assert should_clarify("planning", 4, {}) == ClarificationMode.QUICK

        # Complexity 5+: FULL
        assert should_clarify("planning", 5, {}) == ClarificationMode.FULL
        assert should_clarify("planning", 10, {}) == ClarificationMode.FULL

    def test_complexity_based_routing_review(self):
        """Test complexity-based routing for 'review' context.

        Thresholds: skip ≤2, quick 3-4, full ≥5
        """
        # Complexity 1-2: SKIP
        assert should_clarify("review", 1, {}) == ClarificationMode.SKIP
        assert should_clarify("review", 2, {}) == ClarificationMode.SKIP

        # Complexity 3-4: QUICK
        assert should_clarify("review", 3, {}) == ClarificationMode.QUICK
        assert should_clarify("review", 4, {}) == ClarificationMode.QUICK

        # Complexity 5+: FULL (threshold is 4 for quick)
        assert should_clarify("review", 5, {}) == ClarificationMode.FULL
        assert should_clarify("review", 6, {}) == ClarificationMode.FULL
        assert should_clarify("review", 10, {}) == ClarificationMode.FULL

    def test_complexity_based_routing_implement_prefs(self):
        """Test complexity-based routing for 'implement_prefs' context.

        Thresholds: skip ≤3, quick 4-5, full ≥6
        """
        # Complexity 1-3: SKIP
        assert should_clarify("implement_prefs", 1, {}) == ClarificationMode.SKIP
        assert should_clarify("implement_prefs", 3, {}) == ClarificationMode.SKIP

        # Complexity 4-5: QUICK
        assert should_clarify("implement_prefs", 4, {}) == ClarificationMode.QUICK
        assert should_clarify("implement_prefs", 5, {}) == ClarificationMode.QUICK

        # Complexity 6+: FULL (threshold is 5 for quick)
        assert should_clarify("implement_prefs", 6, {}) == ClarificationMode.FULL
        assert should_clarify("implement_prefs", 7, {}) == ClarificationMode.FULL
        assert should_clarify("implement_prefs", 10, {}) == ClarificationMode.FULL

    def test_unknown_context_uses_review_thresholds(self):
        """Unknown context should fall back to review thresholds."""
        assert should_clarify("unknown", 2, {}) == ClarificationMode.SKIP
        assert should_clarify("unknown", 4, {}) == ClarificationMode.QUICK
        assert should_clarify("unknown", 7, {}) == ClarificationMode.FULL
