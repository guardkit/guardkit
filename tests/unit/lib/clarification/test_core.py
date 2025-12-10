"""Unit tests for lib/clarification/core.py

Tests the core dataclasses and persistence functionality for the clarifying questions feature.
"""

import pytest
from datetime import datetime
from pathlib import Path
import tempfile
import yaml

# These imports will work once the clarification module is implemented
from lib.clarification.core import Question, Decision, ClarificationContext


class TestQuestion:
    """Test Question dataclass functionality."""

    def test_question_with_all_fields(self):
        """Test creating a question with all fields populated."""
        q = Question(
            id="scope",
            category="scope",
            text="How comprehensive should the implementation be?",
            options=["[M]inimal", "[S]tandard", "[C]omplete"],
            default="S",
            rationale="Standard implementation is typical for most tasks",
        )
        assert q.id == "scope"
        assert q.category == "scope"
        assert q.text == "How comprehensive should the implementation be?"
        assert q.default == "S"
        assert len(q.options) == 3
        assert "[M]inimal" in q.options

    def test_question_minimal_fields(self):
        """Test creating a question with only required fields."""
        q = Question(
            id="test",
            category="test",
            text="Test question?",
            options=["[Y]es", "[N]o"],
        )
        assert q.id == "test"
        assert q.category == "test"
        assert q.default is None
        assert q.rationale is None

    def test_question_serialization(self):
        """Test question serialization to dict and back."""
        q = Question(
            id="test",
            category="scope",
            text="Test question?",
            options=["[Y]es", "[N]o"],
            default="Y",
            rationale="Testing is important",
        )
        data = q.to_dict()

        # Verify dict structure
        assert data["id"] == "test"
        assert data["category"] == "scope"
        assert data["text"] == "Test question?"
        assert data["options"] == ["[Y]es", "[N]o"]
        assert data["default"] == "Y"
        assert data["rationale"] == "Testing is important"

        # Verify deserialization
        restored = Question.from_dict(data)
        assert restored.id == q.id
        assert restored.category == q.category
        assert restored.text == q.text
        assert restored.options == q.options
        assert restored.default == q.default
        assert restored.rationale == q.rationale

    def test_question_serialization_partial(self):
        """Test serialization with optional fields missing."""
        q = Question(
            id="test",
            category="test",
            text="Test?",
            options=["A", "B"],
        )
        data = q.to_dict()
        restored = Question.from_dict(data)

        assert restored.id == q.id
        assert restored.default is None
        assert restored.rationale is None


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

    def test_decision_serialization(self):
        """Test decision serialization to dict and back."""
        d = Decision(
            question_id="testing",
            category="quality",
            question_text="What testing level?",
            answer="integration",
            answer_display="Integration - E2E tests",
            default_used=False,
            rationale="High-risk feature needs integration tests",
        )
        data = d.to_dict()

        # Verify dict structure
        assert data["question_id"] == "testing"
        assert data["category"] == "quality"
        assert data["answer"] == "integration"
        assert data["default_used"] is False

        # Verify deserialization
        restored = Decision.from_dict(data)
        assert restored.question_id == d.question_id
        assert restored.category == d.category
        assert restored.answer == d.answer
        assert restored.default_used == d.default_used

    def test_decision_with_timestamp(self):
        """Test decision timestamp handling."""
        now = datetime.now()
        d = Decision(
            question_id="test",
            category="test",
            question_text="Test?",
            answer="yes",
            answer_display="Yes",
            default_used=False,
            rationale="Test",
            timestamp=now,
        )
        assert d.timestamp == now

        # Serialize and restore
        data = d.to_dict()
        restored = Decision.from_dict(data)
        assert restored.timestamp is not None


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
            decisions=[
                Decision(
                    question_id="scope",
                    category="scope",
                    question_text="How comprehensive?",
                    answer="standard",
                    answer_display="Standard - With error handling",
                    default_used=True,
                    rationale="Default selected",
                ),
                Decision(
                    question_id="testing",
                    category="quality",
                    question_text="What testing level?",
                    answer="unit",
                    answer_display="Unit tests only",
                    default_used=False,
                    rationale="User chose unit tests",
                ),
            ],
        )

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
  timestamp: 2025-12-08T14:30:00
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

        # Verify first decision
        scope_decision = ctx.decisions[0]
        assert scope_decision.question_id == "scope"
        assert scope_decision.category == "scope"
        assert scope_decision.answer == "standard"
        assert scope_decision.default_used is True

        # Verify second decision
        testing_decision = ctx.decisions[1]
        assert testing_decision.question_id == "testing"
        assert testing_decision.category == "quality"
        assert testing_decision.answer == "unit"
        assert testing_decision.default_used is False

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

    def test_context_equality(self):
        """Test ClarificationContext equality comparison."""
        ctx1 = ClarificationContext(
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
            ],
        )

        ctx2 = ClarificationContext(
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
            ],
        )

        assert ctx1 == ctx2

    def test_context_modes(self):
        """Test different clarification modes."""
        # Skip mode
        ctx_skip = ClarificationContext(
            context_type="implementation_planning",
            mode="skip",
            decisions=[],
        )
        assert ctx_skip.mode == "skip"
        assert len(ctx_skip.decisions) == 0

        # Quick mode
        ctx_quick = ClarificationContext(
            context_type="implementation_planning",
            mode="quick",
            decisions=[],
        )
        assert ctx_quick.mode == "quick"

        # Full mode
        ctx_full = ClarificationContext(
            context_type="implementation_planning",
            mode="full",
            decisions=[],
        )
        assert ctx_full.mode == "full"

    def test_multiple_persist_cycles(self, temp_task_file):
        """Test persisting multiple times doesn't corrupt data."""
        # First persist
        ctx1 = ClarificationContext(
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
            ],
        )
        ctx1.persist_to_frontmatter(temp_task_file)

        # Second persist with updated context
        ctx2 = ClarificationContext(
            context_type="implementation_planning",
            mode="full",
            decisions=[
                Decision(
                    question_id="scope",
                    category="scope",
                    question_text="How comprehensive?",
                    answer="complete",
                    answer_display="Complete",
                    default_used=False,
                    rationale="User updated",
                )
            ],
        )
        ctx2.persist_to_frontmatter(temp_task_file)

        # Load and verify latest persisted
        loaded = ClarificationContext.load_from_frontmatter(temp_task_file)
        assert loaded is not None
        assert loaded.decisions[0].answer == "complete"
        assert loaded.decisions[0].default_used is False
