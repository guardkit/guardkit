"""
Comprehensive Test Suite for Decision Significance Detector

Tests DecisionDetector for analyzing Q&A pairs and extracting decisions.
Tests include significance scoring, context extraction, and ADR creation.

Coverage Target: >=85%
Test Count: 15+ tests

This is a TDD RED phase test file - all tests will FAIL until implementation.
"""

import pytest
from unittest.mock import MagicMock

# EXPECTED TO FAIL - modules don't exist yet (TDD RED phase)
from guardkit.knowledge.decision_detector import DecisionDetector
from guardkit.knowledge.adr import ADREntity, ADRTrigger, ADRStatus


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def detector():
    """Create DecisionDetector instance with default threshold."""
    return DecisionDetector()


@pytest.fixture
def detector_low_threshold():
    """Create DecisionDetector with low significance threshold."""
    return DecisionDetector(significance_threshold=0.2)


@pytest.fixture
def detector_high_threshold():
    """Create DecisionDetector with high significance threshold."""
    return DecisionDetector(significance_threshold=0.7)


# ============================================================================
# 1. DecisionDetector Initialization Tests (3 tests)
# ============================================================================


def test_detector_default_threshold(detector):
    """Test DecisionDetector uses default threshold of 0.4."""
    assert detector.significance_threshold == 0.4


def test_detector_custom_threshold():
    """Test DecisionDetector accepts custom threshold."""
    detector = DecisionDetector(significance_threshold=0.6)
    assert detector.significance_threshold == 0.6


def test_detector_threshold_validation():
    """Test DecisionDetector validates threshold is between 0 and 1."""
    with pytest.raises(ValueError):
        DecisionDetector(significance_threshold=-0.1)

    with pytest.raises(ValueError):
        DecisionDetector(significance_threshold=1.5)


# ============================================================================
# 2. Significance Detection Tests (8 tests)
# ============================================================================


def test_detect_significance_scope_decision(detector):
    """Test high significance for scope-related decisions."""
    question = "Should we implement OAuth2 or JWT authentication?"
    answer = "Let's use JWT with refresh tokens for simplicity"

    significance = detector.detect_significance(question, answer)

    # Scope decisions should have high significance (>0.6)
    assert significance > 0.6


def test_detect_significance_approach_decision(detector):
    """Test high significance for approach-related decisions."""
    question = "Which database should we use for this feature?"
    answer = "PostgreSQL would be best given our ACID requirements"

    significance = detector.detect_significance(question, answer)

    # Approach decisions should have high significance (>0.6)
    assert significance > 0.6


def test_detect_significance_trivial_clarification(detector):
    """Test low significance for trivial clarifications."""
    question = "What should we name this variable?"
    answer = "Let's call it 'userCount'"

    significance = detector.detect_significance(question, answer)

    # Trivial clarifications should have low significance (<0.3)
    assert significance < 0.3


def test_detect_significance_yes_no_answer(detector):
    """Test low significance for simple yes/no answers."""
    question = "Should we add a comment here?"
    answer = "Yes"

    significance = detector.detect_significance(question, answer)

    # Simple yes/no should have low significance (<0.3)
    assert significance < 0.3


def test_detect_significance_architecture_decision(detector):
    """Test high significance for architectural decisions."""
    question = "How should we structure the authentication module?"
    answer = "Use a service layer pattern with dependency injection for testability"

    significance = detector.detect_significance(question, answer)

    # Architecture decisions should have high significance (>0.7)
    assert significance > 0.7


def test_detect_significance_returns_float(detector):
    """Test detect_significance returns a float between 0 and 1."""
    question = "Test question?"
    answer = "Test answer"

    significance = detector.detect_significance(question, answer)

    assert isinstance(significance, float)
    assert 0.0 <= significance <= 1.0


def test_detect_significance_empty_inputs(detector):
    """Test detect_significance handles empty inputs gracefully."""
    # Empty question
    sig1 = detector.detect_significance("", "Some answer")
    assert sig1 == 0.0

    # Empty answer
    sig2 = detector.detect_significance("Some question?", "")
    assert sig2 == 0.0

    # Both empty
    sig3 = detector.detect_significance("", "")
    assert sig3 == 0.0


def test_detect_significance_threshold_boundary(detector):
    """Test significance scoring around threshold boundary."""
    # Create Q&A pairs with medium significance
    question = "Should we add logging to this function?"
    answer = "Yes, add INFO level logging for debugging"

    significance = detector.detect_significance(question, answer)

    # Medium significance should be around threshold (0.3-0.6)
    assert 0.3 <= significance <= 0.6


# ============================================================================
# 3. Context Extraction Tests (4 tests)
# ============================================================================


def test_extract_decision_context_basic(detector):
    """Test extract_decision_context extracts decision from Q&A."""
    question = "Which authentication method should we use?"
    answer = "JWT with refresh tokens because it's stateless and scalable"

    context = detector.extract_decision_context(question, answer)

    assert isinstance(context, dict)
    assert "question" in context
    assert "answer" in context
    assert context["question"] == question
    assert context["answer"] == answer


def test_extract_decision_context_extracts_rationale(detector):
    """Test extract_decision_context identifies rationale from answer."""
    question = "Should we use GraphQL or REST?"
    answer = "REST API is better here because we have simple CRUD operations and the team knows it well"

    context = detector.extract_decision_context(question, answer)

    # Should extract "because..." as rationale
    assert "rationale" in context
    assert "simple CRUD" in context["rationale"] or "team knows it" in context["rationale"]


def test_extract_decision_context_identifies_alternatives(detector):
    """Test extract_decision_context identifies mentioned alternatives."""
    question = "Database choice?"
    answer = "PostgreSQL over MySQL or MongoDB because we need strong ACID guarantees"

    context = detector.extract_decision_context(question, answer)

    # Should identify alternatives mentioned
    assert "alternatives" in context
    alternatives = context["alternatives"]
    assert any("MySQL" in alt for alt in alternatives)
    assert any("MongoDB" in alt for alt in alternatives)


def test_extract_decision_context_empty_inputs(detector):
    """Test extract_decision_context handles empty inputs gracefully."""
    context = detector.extract_decision_context("", "")

    assert isinstance(context, dict)
    assert context["question"] == ""
    assert context["answer"] == ""


# ============================================================================
# 4. ADR Creation from Decision Tests (5 tests)
# ============================================================================


def test_create_adr_from_decision_basic(detector):
    """Test create_adr_from_decision creates ADREntity from Q&A."""
    question = "Which caching strategy should we use?"
    answer = "Redis for session storage because it's fast and supports TTL"

    adr = detector.create_adr_from_decision(
        question=question,
        answer=answer,
        trigger=ADRTrigger.CLARIFYING_QUESTION,
        source_task_id="TASK-GI-004"
    )

    assert isinstance(adr, ADREntity)
    assert adr.trigger == ADRTrigger.CLARIFYING_QUESTION
    assert adr.source_task_id == "TASK-GI-004"


def test_create_adr_from_decision_sets_context(detector):
    """Test create_adr_from_decision sets context field."""
    question = "Should we use TypeScript or JavaScript?"
    answer = "TypeScript for type safety and better IDE support"

    adr = detector.create_adr_from_decision(
        question=question,
        answer=answer,
        trigger=ADRTrigger.TASK_REVIEW
    )

    assert adr.context != ""
    assert "TypeScript or JavaScript" in adr.context or question in adr.context


def test_create_adr_from_decision_generates_title(detector):
    """Test create_adr_from_decision generates meaningful title."""
    question = "Which testing framework should we use?"
    answer = "pytest because it has better fixtures and plugins"

    adr = detector.create_adr_from_decision(
        question=question,
        answer=answer,
        trigger=ADRTrigger.IMPLEMENTATION_CHOICE
    )

    # Title should be derived from question or decision
    assert adr.title != ""
    assert len(adr.title) > 0
    # Title might contain key terms from question
    assert "test" in adr.title.lower() or "pytest" in adr.title.lower()


def test_create_adr_from_decision_sets_default_status(detector):
    """Test create_adr_from_decision sets status to ACCEPTED by default."""
    question = "Use Docker for deployment?"
    answer = "Yes, use Docker for consistent environments"

    adr = detector.create_adr_from_decision(
        question=question,
        answer=answer,
        trigger=ADRTrigger.MANUAL
    )

    assert adr.status == ADRStatus.ACCEPTED


def test_create_adr_from_decision_with_feature_id(detector):
    """Test create_adr_from_decision includes feature_id if provided."""
    question = "Authentication approach?"
    answer = "OAuth2 with PKCE flow"

    adr = detector.create_adr_from_decision(
        question=question,
        answer=answer,
        trigger=ADRTrigger.CLARIFYING_QUESTION,
        source_feature_id="FEAT-GI"
    )

    assert adr.source_feature_id == "FEAT-GI"


# ============================================================================
# 5. Integration Tests (3 tests)
# ============================================================================


def test_full_workflow_high_significance(detector):
    """Test complete workflow: detect high significance and create ADR."""
    question = "Should we use microservices or monolith architecture?"
    answer = "Monolith initially because we're a small team and don't need the complexity yet"

    # 1. Detect significance
    significance = detector.detect_significance(question, answer)
    assert significance > detector.significance_threshold

    # 2. Extract context
    context = detector.extract_decision_context(question, answer)
    assert "rationale" in context

    # 3. Create ADR
    adr = detector.create_adr_from_decision(
        question=question,
        answer=answer,
        trigger=ADRTrigger.TASK_REVIEW
    )
    assert adr is not None
    assert isinstance(adr, ADREntity)


def test_full_workflow_low_significance_skips_adr(detector):
    """Test low significance decisions should not create ADRs."""
    question = "What color for the error message?"
    answer = "Red"

    # Low significance should skip ADR creation
    significance = detector.detect_significance(question, answer)
    assert significance < detector.significance_threshold


def test_detector_with_different_triggers():
    """Test detector works with all ADRTrigger types."""
    detector = DecisionDetector()
    question = "Database choice?"
    answer = "PostgreSQL for ACID compliance"

    for trigger in ADRTrigger:
        adr = detector.create_adr_from_decision(
            question=question,
            answer=answer,
            trigger=trigger
        )

        assert adr.trigger == trigger
