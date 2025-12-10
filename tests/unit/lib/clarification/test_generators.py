"""Unit tests for lib/clarification/generators/*.py

Tests the question generation logic for all three contexts.
"""

import pytest
from lib.clarification.generators.planning_generator import generate_planning_questions
from lib.clarification.generators.review_generator import generate_review_questions
from lib.clarification.generators.implement_generator import generate_implement_questions
from lib.clarification.core import Question
from lib.clarification.detection import detect_scope_ambiguity, detect_technology_ambiguity


class TestPlanningGenerator:
    """Test implementation planning question generation (Context C)."""

    def test_generate_basic_planning_questions(self):
        """Test generating basic planning questions."""
        task_desc = "Add user authentication to the application"

        questions = generate_planning_questions(task_desc, complexity=5)

        # Should return a list of Question objects
        assert isinstance(questions, list)
        assert all(isinstance(q, Question) for q in questions)

        # Should have multiple questions for complexity 5
        assert len(questions) >= 3

        # Should include common categories
        categories = [q.category for q in questions]
        assert "scope" in categories or "implementation" in categories

    def test_planning_questions_for_high_complexity(self):
        """Test more questions for high complexity tasks."""
        task_desc = "Refactor entire authentication system with new architecture"

        questions_high = generate_planning_questions(task_desc, complexity=8)
        questions_medium = generate_planning_questions(task_desc, complexity=4)

        # High complexity should have more or equal questions
        assert len(questions_high) >= len(questions_medium)

    def test_planning_questions_adapt_to_task(self):
        """Test that questions adapt to task description."""
        # Task mentions performance
        perf_task = "Optimize database queries for better performance"
        perf_questions = generate_planning_questions(perf_task, complexity=5)

        # Should include performance-related questions
        perf_categories = [q.category for q in perf_questions]
        assert "performance" in perf_categories or "optimization" in perf_categories

    def test_planning_questions_include_defaults(self):
        """Test that questions include sensible defaults."""
        task_desc = "Add email validation to registration form"

        questions = generate_planning_questions(task_desc, complexity=4)

        # At least some questions should have defaults
        questions_with_defaults = [q for q in questions if q.default is not None]
        assert len(questions_with_defaults) > 0

    def test_planning_questions_for_ambiguous_scope(self):
        """Test question generation for tasks with ambiguous scope."""
        task_desc = "Improve the system"  # Very vague

        detection = detect_scope_ambiguity(task_desc)
        assert detection.is_ambiguous is True

        questions = generate_planning_questions(task_desc, complexity=5)

        # Should definitely ask scope clarification
        scope_questions = [q for q in questions if q.category == "scope"]
        assert len(scope_questions) >= 1

    def test_planning_questions_categories(self):
        """Test that all 6 expected categories are covered."""
        task_desc = "Build a new user authentication system with role-based access control"

        questions = generate_planning_questions(task_desc, complexity=7)

        categories = {q.category for q in questions}

        # Should cover most of these categories
        expected_categories = {
            "scope",
            "technology",
            "testing",
            "error_handling",
            "performance",
            "documentation",
        }

        # Should have at least 4 of the 6 categories
        overlap = categories.intersection(expected_categories)
        assert len(overlap) >= 4


class TestReviewGenerator:
    """Test review scope question generation (Context A)."""

    def test_generate_basic_review_questions(self):
        """Test generating basic review questions."""
        review_desc = "Review the authentication system architecture"

        questions = generate_review_questions(review_desc, mode="decision")

        assert isinstance(questions, list)
        assert all(isinstance(q, Question) for q in questions)

        # Should have multiple questions
        assert len(questions) >= 3

        # Should include review-specific categories
        categories = [q.category for q in questions]
        assert "review_focus" in categories or "depth" in categories

    def test_review_questions_for_decision_mode(self):
        """Test review questions for decision mode."""
        review_desc = "Should we migrate to microservices?"

        questions = generate_review_questions(review_desc, mode="decision")

        # Decision mode should ask about options, tradeoffs, criteria
        categories = [q.category for q in questions]
        assert any(cat in ["options", "criteria", "tradeoffs"] for cat in categories)

    def test_review_questions_for_architectural_mode(self):
        """Test review questions for architectural mode."""
        review_desc = "Review API architecture for SOLID compliance"

        questions = generate_review_questions(review_desc, mode="architectural")

        # Should ask about specific architectural aspects
        categories = [q.category for q in questions]
        # Might ask about SOLID principles, patterns, etc.
        assert len(categories) >= 3

    def test_review_questions_for_security_mode(self):
        """Test review questions for security mode."""
        review_desc = "Security audit of authentication endpoints"

        questions = generate_review_questions(review_desc, mode="security")

        # Should ask about security-specific concerns
        categories = [q.category for q in questions]
        assert "security_focus" in categories or "vulnerabilities" in categories or "scope" in categories

    def test_review_questions_adapt_to_description(self):
        """Test that review questions adapt to description."""
        # Broad review
        broad_desc = "Review the entire codebase"
        broad_questions = generate_review_questions(broad_desc, mode="code-quality")

        # Should ask about focus area
        focus_questions = [q for q in broad_questions if "focus" in q.text.lower() or "area" in q.text.lower()]
        assert len(focus_questions) >= 1

    def test_review_questions_include_defaults(self):
        """Test that review questions include defaults."""
        review_desc = "Review authentication logic"

        questions = generate_review_questions(review_desc, mode="decision")

        # Should have some defaults
        questions_with_defaults = [q for q in questions if q.default is not None]
        assert len(questions_with_defaults) > 0


class TestImplementGenerator:
    """Test implementation preference question generation (Context B)."""

    def test_generate_basic_implement_questions(self):
        """Test generating basic implementation preference questions."""
        findings = {
            "recommendations": [
                "Add JWT token validation",
                "Implement refresh token rotation",
                "Add rate limiting to auth endpoints",
            ],
            "options": [
                {"id": 1, "title": "Minimal - JWT validation only"},
                {"id": 2, "title": "Standard - JWT + refresh tokens"},
                {"id": 3, "title": "Complete - All security features"},
            ],
        }

        questions = generate_implement_questions(findings)

        assert isinstance(questions, list)
        assert all(isinstance(q, Question) for q in questions)

        # Should have multiple questions
        assert len(questions) >= 2

        # Should include implementation-specific categories
        categories = [q.category for q in questions]
        assert "implementation_scope" in categories or "approach" in categories

    def test_implement_questions_for_multiple_recommendations(self):
        """Test questions when multiple recommendations exist."""
        findings = {
            "recommendations": [
                "Recommendation 1",
                "Recommendation 2",
                "Recommendation 3",
                "Recommendation 4",
                "Recommendation 5",
            ],
        }

        questions = generate_implement_questions(findings)

        # Should ask about prioritization or batching
        categories = [q.category for q in questions]
        assert "prioritization" in categories or "batching" in categories or "implementation_scope" in categories

    def test_implement_questions_for_single_recommendation(self):
        """Test questions for single recommendation."""
        findings = {
            "recommendations": [
                "Add email validation to registration form",
            ],
        }

        questions = generate_implement_questions(findings)

        # Even single recommendation should have questions
        assert len(questions) >= 1

        # Should ask about implementation details
        categories = [q.category for q in questions]
        assert "implementation_approach" in categories or "testing" in categories or "implementation_scope" in categories

    def test_implement_questions_with_options(self):
        """Test that questions reference provided options."""
        findings = {
            "recommendations": ["Add auth"],
            "options": [
                {"id": 1, "title": "Minimal"},
                {"id": 2, "title": "Standard"},
                {"id": 3, "title": "Complete"},
            ],
        }

        questions = generate_implement_questions(findings)

        # Should have a question about which option to implement
        scope_questions = [q for q in questions if q.category == "implementation_scope"]
        assert len(scope_questions) >= 1

        # Question should reference the options
        scope_q = scope_questions[0]
        assert len(scope_q.options) >= 2

    def test_implement_questions_without_options(self):
        """Test questions when no options provided (custom implementation)."""
        findings = {
            "recommendations": [
                "Refactor authentication module",
            ],
            "options": [],  # No predefined options
        }

        questions = generate_implement_questions(findings)

        # Should still generate questions
        assert len(questions) >= 1

        # Might ask about implementation approach, testing strategy, etc.
        categories = [q.category for q in questions]
        assert len(categories) > 0

    def test_implement_questions_include_defaults(self):
        """Test that implementation questions include defaults."""
        findings = {
            "recommendations": ["Add feature X"],
            "options": [
                {"id": 1, "title": "Minimal"},
                {"id": 2, "title": "Standard"},
            ],
        }

        questions = generate_implement_questions(findings)

        # Should have defaults
        questions_with_defaults = [q for q in questions if q.default is not None]
        assert len(questions_with_defaults) > 0


class TestGeneratorEdgeCases:
    """Test edge cases across all generators."""

    def test_empty_task_description(self):
        """Test handling of empty task description."""
        questions = generate_planning_questions("", complexity=5)

        # Should still return questions (general ones)
        assert isinstance(questions, list)
        assert len(questions) >= 1

    def test_very_long_task_description(self):
        """Test handling of very long task description."""
        long_desc = " ".join(["word"] * 500)

        questions = generate_planning_questions(long_desc, complexity=5)

        # Should handle gracefully
        assert isinstance(questions, list)

    def test_low_complexity_fewer_questions(self):
        """Test that low complexity generates fewer questions."""
        task_desc = "Add a button to the UI"

        questions_low = generate_planning_questions(task_desc, complexity=2)
        questions_high = generate_planning_questions(task_desc, complexity=8)

        # Low complexity should have fewer or equal questions
        assert len(questions_low) <= len(questions_high)

    def test_complexity_zero(self):
        """Test handling of complexity 0."""
        task_desc = "Trivial task"

        questions = generate_planning_questions(task_desc, complexity=0)

        # Should handle gracefully, might return empty list or minimal questions
        assert isinstance(questions, list)

    def test_complexity_beyond_scale(self):
        """Test handling of complexity > 10."""
        task_desc = "Extremely complex task"

        questions = generate_planning_questions(task_desc, complexity=15)

        # Should cap or handle gracefully
        assert isinstance(questions, list)
        # Shouldn't generate infinite questions
        assert len(questions) < 20

    def test_review_with_none_mode(self):
        """Test review generator with None mode."""
        try:
            questions = generate_review_questions("Review code", mode=None)
            # Should either use default mode or raise error
            assert isinstance(questions, list)
        except (ValueError, TypeError):
            # Also acceptable to raise error
            pass

    def test_implement_with_empty_findings(self):
        """Test implement generator with empty findings."""
        findings = {}

        questions = generate_implement_questions(findings)

        # Should handle gracefully
        assert isinstance(questions, list)


class TestQuestionQuality:
    """Test quality of generated questions."""

    def test_questions_have_required_fields(self):
        """Test that all generated questions have required fields."""
        task_desc = "Add user authentication"

        questions = generate_planning_questions(task_desc, complexity=5)

        for q in questions:
            assert q.id is not None and q.id != ""
            assert q.category is not None and q.category != ""
            assert q.text is not None and q.text != ""
            assert q.options is not None and len(q.options) >= 2

    def test_questions_have_unique_ids(self):
        """Test that question IDs are unique."""
        task_desc = "Add user authentication"

        questions = generate_planning_questions(task_desc, complexity=7)

        ids = [q.id for q in questions]
        assert len(ids) == len(set(ids)), "Question IDs should be unique"

    def test_question_options_are_actionable(self):
        """Test that question options are actionable."""
        task_desc = "Add user authentication"

        questions = generate_planning_questions(task_desc, complexity=5)

        for q in questions:
            # Each option should have at least one word
            assert all(len(opt) > 0 for opt in q.options)
            # Options should be distinct
            assert len(q.options) == len(set(q.options))

    def test_questions_relevant_to_task(self):
        """Test that questions are relevant to task description."""
        # Task about authentication should have auth-related questions
        auth_task = "Implement OAuth2 authentication"
        auth_questions = generate_planning_questions(auth_task, complexity=6)

        # At least one question should mention auth/security/tokens
        question_texts = " ".join([q.text.lower() for q in auth_questions])
        assert any(keyword in question_texts for keyword in ["auth", "security", "token", "user", "login"])

    def test_defaults_are_valid_options(self):
        """Test that default values are valid options."""
        task_desc = "Add feature"

        questions = generate_planning_questions(task_desc, complexity=5)

        for q in questions:
            if q.default is not None:
                # Default should match one of the option shortcuts
                option_shortcuts = [opt[1].lower() for opt in q.options if len(opt) > 2 and opt[0] == '[' and opt[2] == ']']
                assert q.default.lower() in option_shortcuts, f"Default '{q.default}' not in options for question: {q.text}"
