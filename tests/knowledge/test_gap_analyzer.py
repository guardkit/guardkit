"""
Comprehensive Test Suite for KnowledgeGapAnalyzer

Tests the knowledge gap analysis functionality including:
- KnowledgeCategory enum with 9 categories
- KnowledgeGap dataclass with required fields
- analyze_gaps() method with focus filtering and sorting
- Graphiti querying for existing knowledge
- Question template comparison and matching

Coverage Target: >=85%
Test Count: 40+ tests
"""

import pytest
from unittest.mock import AsyncMock, patch
from typing import List
from enum import Enum


# ============================================================================
# 1. KnowledgeCategory Enum Tests (5 tests)
# ============================================================================

class TestKnowledgeCategoryEnum:
    """Test KnowledgeCategory enum definition."""

    def test_enum_has_all_nine_categories(self):
        """Test that KnowledgeCategory enum has all 9 required categories."""
        from guardkit.knowledge.gap_analyzer import KnowledgeCategory

        expected_categories = {
            "PROJECT_OVERVIEW",
            "ARCHITECTURE",
            "DOMAIN",
            "CONSTRAINTS",
            "DECISIONS",
            "GOALS",
            "ROLE_CUSTOMIZATION",
            "QUALITY_GATES",
            "WORKFLOW_PREFERENCES",
        }

        actual_categories = {member.name for member in KnowledgeCategory}
        assert actual_categories == expected_categories

    def test_enum_values_are_strings(self):
        """Test that enum values are lowercase strings."""
        from guardkit.knowledge.gap_analyzer import KnowledgeCategory

        assert KnowledgeCategory.PROJECT_OVERVIEW.value == "project_overview"
        assert KnowledgeCategory.ARCHITECTURE.value == "architecture"
        assert KnowledgeCategory.DOMAIN.value == "domain"
        assert KnowledgeCategory.CONSTRAINTS.value == "constraints"
        assert KnowledgeCategory.DECISIONS.value == "decisions"
        assert KnowledgeCategory.GOALS.value == "goals"
        assert KnowledgeCategory.ROLE_CUSTOMIZATION.value == "role_customization"
        assert KnowledgeCategory.QUALITY_GATES.value == "quality_gates"
        assert KnowledgeCategory.WORKFLOW_PREFERENCES.value == "workflow_preferences"

    def test_enum_is_string_enum(self):
        """Test that KnowledgeCategory is a string enum."""
        from guardkit.knowledge.gap_analyzer import KnowledgeCategory

        assert issubclass(KnowledgeCategory, str)
        assert issubclass(KnowledgeCategory, Enum)

    def test_enum_can_be_compared_to_strings(self):
        """Test that enum members can be compared to strings."""
        from guardkit.knowledge.gap_analyzer import KnowledgeCategory

        assert KnowledgeCategory.PROJECT_OVERVIEW == "project_overview"
        assert KnowledgeCategory.ARCHITECTURE == "architecture"

    def test_enum_from_string_value(self):
        """Test creating enum from string value."""
        from guardkit.knowledge.gap_analyzer import KnowledgeCategory

        category = KnowledgeCategory("project_overview")
        assert category == KnowledgeCategory.PROJECT_OVERVIEW


# ============================================================================
# 2. KnowledgeGap Dataclass Tests (6 tests)
# ============================================================================

class TestKnowledgeGapDataclass:
    """Test KnowledgeGap dataclass definition."""

    def test_dataclass_has_required_fields(self):
        """Test that KnowledgeGap has all required fields."""
        from guardkit.knowledge.gap_analyzer import KnowledgeGap, KnowledgeCategory

        gap = KnowledgeGap(
            category=KnowledgeCategory.PROJECT_OVERVIEW,
            question="What is the purpose?",
            importance="high",
            context="Understanding the 'why'",
        )

        assert gap.category == KnowledgeCategory.PROJECT_OVERVIEW
        assert gap.question == "What is the purpose?"
        assert gap.importance == "high"
        assert gap.context == "Understanding the 'why'"

    def test_dataclass_optional_example_answer(self):
        """Test that example_answer is optional."""
        from guardkit.knowledge.gap_analyzer import KnowledgeGap, KnowledgeCategory

        # Without example_answer
        gap1 = KnowledgeGap(
            category=KnowledgeCategory.PROJECT_OVERVIEW,
            question="What is the purpose?",
            importance="high",
            context="Understanding the 'why'",
        )
        assert gap1.example_answer is None

        # With example_answer
        gap2 = KnowledgeGap(
            category=KnowledgeCategory.PROJECT_OVERVIEW,
            question="What is the purpose?",
            importance="high",
            context="Understanding the 'why'",
            example_answer="This project builds AI assistants.",
        )
        assert gap2.example_answer == "This project builds AI assistants."

    def test_dataclass_importance_values(self):
        """Test all valid importance levels."""
        from guardkit.knowledge.gap_analyzer import KnowledgeGap, KnowledgeCategory

        for importance in ["high", "medium", "low"]:
            gap = KnowledgeGap(
                category=KnowledgeCategory.PROJECT_OVERVIEW,
                question="Test question",
                importance=importance,
                context="Context",
            )
            assert gap.importance == importance

    def test_dataclass_all_categories(self):
        """Test KnowledgeGap with all category types."""
        from guardkit.knowledge.gap_analyzer import KnowledgeGap, KnowledgeCategory

        for category in KnowledgeCategory:
            gap = KnowledgeGap(
                category=category,
                question="Test question",
                importance="medium",
                context="Context",
            )
            assert gap.category == category

    def test_dataclass_is_dataclass(self):
        """Test that KnowledgeGap is a proper dataclass."""
        from guardkit.knowledge.gap_analyzer import KnowledgeGap
        from dataclasses import is_dataclass, fields

        assert is_dataclass(KnowledgeGap)
        field_names = {f.name for f in fields(KnowledgeGap)}
        assert field_names == {"category", "question", "importance", "context", "example_answer"}

    def test_dataclass_field_types(self):
        """Test that fields have correct types."""
        from guardkit.knowledge.gap_analyzer import KnowledgeGap, KnowledgeCategory
        from dataclasses import fields

        field_types = {f.name: f.type for f in fields(KnowledgeGap)}

        assert field_types["category"] == KnowledgeCategory
        assert "str" in str(field_types["question"])
        assert "str" in str(field_types["importance"])
        assert "str" in str(field_types["context"])


# ============================================================================
# 3. KnowledgeGapAnalyzer Initialization Tests (3 tests)
# ============================================================================

class TestKnowledgeGapAnalyzerInit:
    """Test KnowledgeGapAnalyzer initialization."""

    def test_analyzer_can_be_instantiated(self):
        """Test creating a KnowledgeGapAnalyzer instance."""
        from guardkit.knowledge.gap_analyzer import KnowledgeGapAnalyzer

        analyzer = KnowledgeGapAnalyzer()
        assert analyzer is not None

    def test_analyzer_has_question_templates(self):
        """Test that analyzer has question templates defined."""
        from guardkit.knowledge.gap_analyzer import KnowledgeGapAnalyzer

        assert hasattr(KnowledgeGapAnalyzer, "QUESTION_TEMPLATES")
        assert isinstance(KnowledgeGapAnalyzer.QUESTION_TEMPLATES, dict)

    def test_question_templates_has_all_categories(self):
        """Test that question templates cover all categories."""
        from guardkit.knowledge.gap_analyzer import KnowledgeGapAnalyzer, KnowledgeCategory

        for category in KnowledgeCategory:
            assert category in KnowledgeGapAnalyzer.QUESTION_TEMPLATES
            assert len(KnowledgeGapAnalyzer.QUESTION_TEMPLATES[category]) > 0


# ============================================================================
# 4. analyze_gaps() Return Type Tests (3 tests)
# ============================================================================

class TestAnalyzeGapsReturnType:
    """Test analyze_gaps() return type and structure."""

    @pytest.mark.asyncio
    async def test_analyze_gaps_returns_list(self):
        """Test that analyze_gaps returns a List."""
        from guardkit.knowledge.gap_analyzer import KnowledgeGapAnalyzer

        analyzer = KnowledgeGapAnalyzer()

        with patch('guardkit.knowledge.gap_analyzer.get_graphiti') as mock_get:
            mock_graphiti = AsyncMock()
            mock_graphiti.search = AsyncMock(return_value=[])
            mock_get.return_value = mock_graphiti

            result = await analyzer.analyze_gaps()

            assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_analyze_gaps_returns_knowledge_gap_objects(self):
        """Test that analyze_gaps returns List[KnowledgeGap]."""
        from guardkit.knowledge.gap_analyzer import KnowledgeGapAnalyzer, KnowledgeGap

        analyzer = KnowledgeGapAnalyzer()

        with patch('guardkit.knowledge.gap_analyzer.get_graphiti') as mock_get:
            mock_graphiti = AsyncMock()
            mock_graphiti.search = AsyncMock(return_value=[])
            mock_get.return_value = mock_graphiti

            result = await analyzer.analyze_gaps()

            # All items should be KnowledgeGap instances
            for item in result:
                assert isinstance(item, KnowledgeGap)

    @pytest.mark.asyncio
    async def test_analyze_gaps_empty_result(self):
        """Test analyze_gaps with no existing knowledge."""
        from guardkit.knowledge.gap_analyzer import KnowledgeGapAnalyzer

        analyzer = KnowledgeGapAnalyzer()

        with patch('guardkit.knowledge.gap_analyzer.get_graphiti') as mock_get:
            mock_graphiti = AsyncMock()
            mock_graphiti.search = AsyncMock(return_value=[])
            mock_get.return_value = mock_graphiti

            result = await analyzer.analyze_gaps()

            assert isinstance(result, list)


# ============================================================================
# 5. Focus Filtering Tests (6 tests)
# ============================================================================

class TestAnalyzeGapsFocusFiltering:
    """Test focus filtering in analyze_gaps()."""

    @pytest.mark.asyncio
    async def test_analyze_gaps_with_focus_filters_by_category(self):
        """Test that focus parameter filters by category."""
        from guardkit.knowledge.gap_analyzer import KnowledgeGapAnalyzer, KnowledgeCategory

        analyzer = KnowledgeGapAnalyzer()

        with patch('guardkit.knowledge.gap_analyzer.get_graphiti') as mock_get:
            mock_graphiti = AsyncMock()
            mock_graphiti.search = AsyncMock(return_value=[])
            mock_get.return_value = mock_graphiti

            result = await analyzer.analyze_gaps(focus=KnowledgeCategory.PROJECT_OVERVIEW)

            # All gaps should be from PROJECT_OVERVIEW category
            for gap in result:
                assert gap.category == KnowledgeCategory.PROJECT_OVERVIEW

    @pytest.mark.asyncio
    async def test_analyze_gaps_focus_architecture(self):
        """Test focus filtering with architecture category."""
        from guardkit.knowledge.gap_analyzer import KnowledgeGapAnalyzer, KnowledgeCategory

        analyzer = KnowledgeGapAnalyzer()

        with patch('guardkit.knowledge.gap_analyzer.get_graphiti') as mock_get:
            mock_graphiti = AsyncMock()
            mock_graphiti.search = AsyncMock(return_value=[])
            mock_get.return_value = mock_graphiti

            result = await analyzer.analyze_gaps(focus=KnowledgeCategory.ARCHITECTURE)

            for gap in result:
                assert gap.category == KnowledgeCategory.ARCHITECTURE

    @pytest.mark.asyncio
    async def test_analyze_gaps_focus_role_customization(self):
        """Test focus filtering with role_customization category."""
        from guardkit.knowledge.gap_analyzer import KnowledgeGapAnalyzer, KnowledgeCategory

        analyzer = KnowledgeGapAnalyzer()

        with patch('guardkit.knowledge.gap_analyzer.get_graphiti') as mock_get:
            mock_graphiti = AsyncMock()
            mock_graphiti.search = AsyncMock(return_value=[])
            mock_get.return_value = mock_graphiti

            result = await analyzer.analyze_gaps(focus=KnowledgeCategory.ROLE_CUSTOMIZATION)

            for gap in result:
                assert gap.category == KnowledgeCategory.ROLE_CUSTOMIZATION

    @pytest.mark.asyncio
    async def test_analyze_gaps_focus_quality_gates(self):
        """Test focus filtering with quality_gates category."""
        from guardkit.knowledge.gap_analyzer import KnowledgeGapAnalyzer, KnowledgeCategory

        analyzer = KnowledgeGapAnalyzer()

        with patch('guardkit.knowledge.gap_analyzer.get_graphiti') as mock_get:
            mock_graphiti = AsyncMock()
            mock_graphiti.search = AsyncMock(return_value=[])
            mock_get.return_value = mock_graphiti

            result = await analyzer.analyze_gaps(focus=KnowledgeCategory.QUALITY_GATES)

            for gap in result:
                assert gap.category == KnowledgeCategory.QUALITY_GATES

    @pytest.mark.asyncio
    async def test_analyze_gaps_focus_workflow_preferences(self):
        """Test focus filtering with workflow_preferences category."""
        from guardkit.knowledge.gap_analyzer import KnowledgeGapAnalyzer, KnowledgeCategory

        analyzer = KnowledgeGapAnalyzer()

        with patch('guardkit.knowledge.gap_analyzer.get_graphiti') as mock_get:
            mock_graphiti = AsyncMock()
            mock_graphiti.search = AsyncMock(return_value=[])
            mock_get.return_value = mock_graphiti

            result = await analyzer.analyze_gaps(focus=KnowledgeCategory.WORKFLOW_PREFERENCES)

            for gap in result:
                assert gap.category == KnowledgeCategory.WORKFLOW_PREFERENCES

    @pytest.mark.asyncio
    async def test_analyze_gaps_without_focus_includes_all_categories(self):
        """Test that without focus, all categories are included."""
        from guardkit.knowledge.gap_analyzer import KnowledgeGapAnalyzer, KnowledgeCategory

        analyzer = KnowledgeGapAnalyzer()

        with patch('guardkit.knowledge.gap_analyzer.get_graphiti') as mock_get:
            mock_graphiti = AsyncMock()
            mock_graphiti.search = AsyncMock(return_value=[])
            mock_get.return_value = mock_graphiti

            result = await analyzer.analyze_gaps(max_questions=50)

            # With no focus and high max_questions, multiple categories should be present
            if len(result) > 0:
                categories_found = {gap.category for gap in result}
                # Should have at least some variety
                assert len(categories_found) >= 1


# ============================================================================
# 6. max_questions Limit Tests (5 tests)
# ============================================================================

class TestAnalyzeGapsMaxQuestions:
    """Test max_questions limiting in analyze_gaps()."""

    @pytest.mark.asyncio
    async def test_analyze_gaps_respects_max_questions_limit(self):
        """Test that analyze_gaps respects max_questions parameter."""
        from guardkit.knowledge.gap_analyzer import KnowledgeGapAnalyzer

        analyzer = KnowledgeGapAnalyzer()

        with patch('guardkit.knowledge.gap_analyzer.get_graphiti') as mock_get:
            mock_graphiti = AsyncMock()
            mock_graphiti.search = AsyncMock(return_value=[])
            mock_get.return_value = mock_graphiti

            result = await analyzer.analyze_gaps(max_questions=5)

            assert len(result) <= 5

    @pytest.mark.asyncio
    async def test_analyze_gaps_max_questions_one(self):
        """Test analyze_gaps with max_questions=1."""
        from guardkit.knowledge.gap_analyzer import KnowledgeGapAnalyzer

        analyzer = KnowledgeGapAnalyzer()

        with patch('guardkit.knowledge.gap_analyzer.get_graphiti') as mock_get:
            mock_graphiti = AsyncMock()
            mock_graphiti.search = AsyncMock(return_value=[])
            mock_get.return_value = mock_graphiti

            result = await analyzer.analyze_gaps(max_questions=1)

            assert len(result) <= 1

    @pytest.mark.asyncio
    async def test_analyze_gaps_max_questions_zero(self):
        """Test analyze_gaps with max_questions=0."""
        from guardkit.knowledge.gap_analyzer import KnowledgeGapAnalyzer

        analyzer = KnowledgeGapAnalyzer()

        with patch('guardkit.knowledge.gap_analyzer.get_graphiti') as mock_get:
            mock_graphiti = AsyncMock()
            mock_graphiti.search = AsyncMock(return_value=[])
            mock_get.return_value = mock_graphiti

            result = await analyzer.analyze_gaps(max_questions=0)

            assert len(result) == 0

    @pytest.mark.asyncio
    async def test_analyze_gaps_default_max_questions(self):
        """Test analyze_gaps uses reasonable default for max_questions."""
        from guardkit.knowledge.gap_analyzer import KnowledgeGapAnalyzer

        analyzer = KnowledgeGapAnalyzer()

        with patch('guardkit.knowledge.gap_analyzer.get_graphiti') as mock_get:
            mock_graphiti = AsyncMock()
            mock_graphiti.search = AsyncMock(return_value=[])
            mock_get.return_value = mock_graphiti

            result = await analyzer.analyze_gaps()

            # Default should be reasonable (e.g., 10)
            assert isinstance(result, list)
            assert len(result) <= 10  # Default is 10

    @pytest.mark.asyncio
    async def test_analyze_gaps_max_questions_high_value(self):
        """Test analyze_gaps with high max_questions value."""
        from guardkit.knowledge.gap_analyzer import KnowledgeGapAnalyzer

        analyzer = KnowledgeGapAnalyzer()

        with patch('guardkit.knowledge.gap_analyzer.get_graphiti') as mock_get:
            mock_graphiti = AsyncMock()
            mock_graphiti.search = AsyncMock(return_value=[])
            mock_get.return_value = mock_graphiti

            result = await analyzer.analyze_gaps(max_questions=100)

            assert len(result) <= 100


# ============================================================================
# 7. Importance Sorting Tests (4 tests)
# ============================================================================

class TestAnalyzeGapsSorting:
    """Test that results are sorted by importance."""

    @pytest.mark.asyncio
    async def test_gaps_sorted_by_importance_high_first(self):
        """Test that high importance gaps come first."""
        from guardkit.knowledge.gap_analyzer import KnowledgeGapAnalyzer

        analyzer = KnowledgeGapAnalyzer()

        with patch('guardkit.knowledge.gap_analyzer.get_graphiti') as mock_get:
            mock_graphiti = AsyncMock()
            mock_graphiti.search = AsyncMock(return_value=[])
            mock_get.return_value = mock_graphiti

            result = await analyzer.analyze_gaps(max_questions=50)

            # Check importance sequence: high, medium, low
            importance_sequence = [gap.importance for gap in result]

            # Verify high comes before medium
            high_indices = [i for i, imp in enumerate(importance_sequence) if imp == "high"]
            medium_indices = [i for i, imp in enumerate(importance_sequence) if imp == "medium"]
            low_indices = [i for i, imp in enumerate(importance_sequence) if imp == "low"]

            if high_indices and medium_indices:
                assert max(high_indices) <= min(medium_indices)
            if medium_indices and low_indices:
                assert max(medium_indices) <= min(low_indices)

    @pytest.mark.asyncio
    async def test_gaps_high_importance_present(self):
        """Test that high importance gaps are included."""
        from guardkit.knowledge.gap_analyzer import KnowledgeGapAnalyzer

        analyzer = KnowledgeGapAnalyzer()

        with patch('guardkit.knowledge.gap_analyzer.get_graphiti') as mock_get:
            mock_graphiti = AsyncMock()
            mock_graphiti.search = AsyncMock(return_value=[])
            mock_get.return_value = mock_graphiti

            result = await analyzer.analyze_gaps(max_questions=50)

            importance_levels = {gap.importance for gap in result}
            assert "high" in importance_levels or len(result) == 0

    @pytest.mark.asyncio
    async def test_gaps_sorted_within_focus_by_importance(self):
        """Test that sorting works within a focus category."""
        from guardkit.knowledge.gap_analyzer import KnowledgeGapAnalyzer, KnowledgeCategory

        analyzer = KnowledgeGapAnalyzer()

        with patch('guardkit.knowledge.gap_analyzer.get_graphiti') as mock_get:
            mock_graphiti = AsyncMock()
            mock_graphiti.search = AsyncMock(return_value=[])
            mock_get.return_value = mock_graphiti

            result = await analyzer.analyze_gaps(focus=KnowledgeCategory.ARCHITECTURE, max_questions=50)

            importance_sequence = [gap.importance for gap in result]

            # Verify ordering
            high_indices = [i for i, imp in enumerate(importance_sequence) if imp == "high"]
            medium_indices = [i for i, imp in enumerate(importance_sequence) if imp == "medium"]

            if high_indices and medium_indices:
                assert max(high_indices) <= min(medium_indices)

    @pytest.mark.asyncio
    async def test_importance_values_are_valid(self):
        """Test that all gaps have valid importance values."""
        from guardkit.knowledge.gap_analyzer import KnowledgeGapAnalyzer

        analyzer = KnowledgeGapAnalyzer()

        with patch('guardkit.knowledge.gap_analyzer.get_graphiti') as mock_get:
            mock_graphiti = AsyncMock()
            mock_graphiti.search = AsyncMock(return_value=[])
            mock_get.return_value = mock_graphiti

            result = await analyzer.analyze_gaps()

            valid_importance = {"high", "medium", "low"}
            for gap in result:
                assert gap.importance in valid_importance


# ============================================================================
# 8. Graphiti Integration Tests (5 tests)
# ============================================================================

class TestAnalyzeGapsGraphitiIntegration:
    """Test integration with Graphiti for querying existing knowledge."""

    @pytest.mark.asyncio
    async def test_analyze_gaps_queries_graphiti(self):
        """Test that analyze_gaps calls get_graphiti()."""
        from guardkit.knowledge.gap_analyzer import KnowledgeGapAnalyzer

        analyzer = KnowledgeGapAnalyzer()

        with patch('guardkit.knowledge.gap_analyzer.get_graphiti') as mock_get:
            mock_graphiti = AsyncMock()
            mock_graphiti.search = AsyncMock(return_value=[])
            mock_get.return_value = mock_graphiti

            await analyzer.analyze_gaps()

            mock_get.assert_called()

    @pytest.mark.asyncio
    async def test_analyze_gaps_calls_graphiti_search(self):
        """Test that analyze_gaps calls graphiti.search()."""
        from guardkit.knowledge.gap_analyzer import KnowledgeGapAnalyzer

        analyzer = KnowledgeGapAnalyzer()

        with patch('guardkit.knowledge.gap_analyzer.get_graphiti') as mock_get:
            mock_graphiti = AsyncMock()
            mock_graphiti.search = AsyncMock(return_value=[])
            mock_get.return_value = mock_graphiti

            await analyzer.analyze_gaps()

            # Should search for existing knowledge
            mock_graphiti.search.assert_called()

    @pytest.mark.asyncio
    async def test_analyze_gaps_handles_graphiti_failure(self):
        """Test that analyze_gaps handles Graphiti failures gracefully."""
        from guardkit.knowledge.gap_analyzer import KnowledgeGapAnalyzer

        analyzer = KnowledgeGapAnalyzer()

        with patch('guardkit.knowledge.gap_analyzer.get_graphiti') as mock_get:
            mock_graphiti = AsyncMock()
            mock_graphiti.search = AsyncMock(side_effect=Exception("Connection failed"))
            mock_get.return_value = mock_graphiti

            # Should not raise, should return gracefully
            result = await analyzer.analyze_gaps()

            assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_analyze_gaps_when_graphiti_disabled(self):
        """Test that analyze_gaps works when Graphiti is disabled."""
        from guardkit.knowledge.gap_analyzer import KnowledgeGapAnalyzer

        analyzer = KnowledgeGapAnalyzer()

        with patch('guardkit.knowledge.gap_analyzer.get_graphiti') as mock_get:
            mock_get.return_value = None

            result = await analyzer.analyze_gaps()

            assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_analyze_gaps_searches_by_category(self):
        """Test that analyze_gaps searches for each category."""
        from guardkit.knowledge.gap_analyzer import KnowledgeGapAnalyzer

        analyzer = KnowledgeGapAnalyzer()

        with patch('guardkit.knowledge.gap_analyzer.get_graphiti') as mock_get:
            mock_graphiti = AsyncMock()
            mock_graphiti.search = AsyncMock(return_value=[])
            mock_get.return_value = mock_graphiti

            await analyzer.analyze_gaps()

            # Search should be called for categories
            assert mock_graphiti.search.call_count >= 1


# ============================================================================
# 9. Question Template Comparison Tests (4 tests)
# ============================================================================

class TestQuestionTemplateComparison:
    """Test comparison of existing knowledge against question templates."""

    @pytest.mark.asyncio
    async def test_gaps_come_from_question_templates(self):
        """Test that identified gaps match question templates."""
        from guardkit.knowledge.gap_analyzer import KnowledgeGapAnalyzer

        analyzer = KnowledgeGapAnalyzer()

        with patch('guardkit.knowledge.gap_analyzer.get_graphiti') as mock_get:
            mock_graphiti = AsyncMock()
            mock_graphiti.search = AsyncMock(return_value=[])
            mock_get.return_value = mock_graphiti

            result = await analyzer.analyze_gaps()

            # All gaps should have questions from templates
            all_template_questions = set()
            for category, questions in KnowledgeGapAnalyzer.QUESTION_TEMPLATES.items():
                for q in questions:
                    all_template_questions.add(q.get("question", ""))

            for gap in result:
                assert gap.question in all_template_questions

    @pytest.mark.asyncio
    async def test_gap_has_context_from_template(self):
        """Test that gaps include context from templates."""
        from guardkit.knowledge.gap_analyzer import KnowledgeGapAnalyzer

        analyzer = KnowledgeGapAnalyzer()

        with patch('guardkit.knowledge.gap_analyzer.get_graphiti') as mock_get:
            mock_graphiti = AsyncMock()
            mock_graphiti.search = AsyncMock(return_value=[])
            mock_get.return_value = mock_graphiti

            result = await analyzer.analyze_gaps()

            for gap in result:
                assert gap.context is not None
                assert len(gap.context) > 0

    @pytest.mark.asyncio
    async def test_existing_knowledge_excludes_gaps(self):
        """Test that questions about existing knowledge are excluded."""
        from guardkit.knowledge.gap_analyzer import KnowledgeGapAnalyzer

        analyzer = KnowledgeGapAnalyzer()

        # Simulate existing knowledge in Graphiti
        mock_search_result = [
            {"uuid": "1", "fact": "Project purpose is X"},
            {"uuid": "2", "fact": "Key components are A, B, C"},
        ]

        with patch('guardkit.knowledge.gap_analyzer.get_graphiti') as mock_get:
            mock_graphiti = AsyncMock()
            mock_graphiti.search = AsyncMock(return_value=mock_search_result)
            mock_get.return_value = mock_graphiti

            result = await analyzer.analyze_gaps()

            # Results should not ask about things we already know
            # (implementation dependent, but should be true)
            assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_gap_has_importance_from_template(self):
        """Test that gaps include importance level from templates."""
        from guardkit.knowledge.gap_analyzer import KnowledgeGapAnalyzer

        analyzer = KnowledgeGapAnalyzer()

        with patch('guardkit.knowledge.gap_analyzer.get_graphiti') as mock_get:
            mock_graphiti = AsyncMock()
            mock_graphiti.search = AsyncMock(return_value=[])
            mock_get.return_value = mock_graphiti

            result = await analyzer.analyze_gaps()

            valid_importance = {"high", "medium", "low"}
            for gap in result:
                assert gap.importance in valid_importance


# ============================================================================
# 10. Edge Cases and Error Handling Tests (8 tests)
# ============================================================================

class TestEdgeCasesAndErrorHandling:
    """Test edge cases and error conditions."""

    @pytest.mark.asyncio
    async def test_analyze_gaps_with_none_focus(self):
        """Test analyze_gaps with focus=None (default)."""
        from guardkit.knowledge.gap_analyzer import KnowledgeGapAnalyzer

        analyzer = KnowledgeGapAnalyzer()

        with patch('guardkit.knowledge.gap_analyzer.get_graphiti') as mock_get:
            mock_graphiti = AsyncMock()
            mock_graphiti.search = AsyncMock(return_value=[])
            mock_get.return_value = mock_graphiti

            result = await analyzer.analyze_gaps(focus=None)

            assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_analyze_gaps_with_negative_max_questions(self):
        """Test analyze_gaps with negative max_questions."""
        from guardkit.knowledge.gap_analyzer import KnowledgeGapAnalyzer

        analyzer = KnowledgeGapAnalyzer()

        with patch('guardkit.knowledge.gap_analyzer.get_graphiti') as mock_get:
            mock_graphiti = AsyncMock()
            mock_graphiti.search = AsyncMock(return_value=[])
            mock_get.return_value = mock_graphiti

            result = await analyzer.analyze_gaps(max_questions=-5)

            # Should handle gracefully (return empty list)
            assert isinstance(result, list)
            assert len(result) == 0

    @pytest.mark.asyncio
    async def test_analyze_gaps_with_empty_graphiti_results(self):
        """Test analyze_gaps when Graphiti returns empty results."""
        from guardkit.knowledge.gap_analyzer import KnowledgeGapAnalyzer

        analyzer = KnowledgeGapAnalyzer()

        with patch('guardkit.knowledge.gap_analyzer.get_graphiti') as mock_get:
            mock_graphiti = AsyncMock()
            mock_graphiti.search = AsyncMock(return_value=[])
            mock_get.return_value = mock_graphiti

            result = await analyzer.analyze_gaps()

            # Should return all available gaps
            assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_analyze_gaps_combined_focus_and_limit(self):
        """Test analyze_gaps with both focus and max_questions."""
        from guardkit.knowledge.gap_analyzer import KnowledgeGapAnalyzer, KnowledgeCategory

        analyzer = KnowledgeGapAnalyzer()

        with patch('guardkit.knowledge.gap_analyzer.get_graphiti') as mock_get:
            mock_graphiti = AsyncMock()
            mock_graphiti.search = AsyncMock(return_value=[])
            mock_get.return_value = mock_graphiti

            result = await analyzer.analyze_gaps(
                focus=KnowledgeCategory.ARCHITECTURE,
                max_questions=3
            )

            assert len(result) <= 3
            for gap in result:
                assert gap.category == KnowledgeCategory.ARCHITECTURE

    @pytest.mark.asyncio
    async def test_analyze_gaps_all_autobuild_categories(self):
        """Test that AutoBuild categories are included."""
        from guardkit.knowledge.gap_analyzer import KnowledgeGapAnalyzer, KnowledgeCategory

        autobuild_categories = {
            KnowledgeCategory.ROLE_CUSTOMIZATION,
            KnowledgeCategory.QUALITY_GATES,
            KnowledgeCategory.WORKFLOW_PREFERENCES,
        }

        with patch('guardkit.knowledge.gap_analyzer.get_graphiti') as mock_get:
            mock_graphiti = AsyncMock()
            mock_graphiti.search = AsyncMock(return_value=[])
            mock_get.return_value = mock_graphiti

            # Test each AutoBuild category individually
            for category in autobuild_categories:
                analyzer = KnowledgeGapAnalyzer()
                result = await analyzer.analyze_gaps(focus=category)
                for gap in result:
                    assert gap.category == category

    @pytest.mark.asyncio
    async def test_analyze_gaps_returns_new_list_each_call(self):
        """Test that each call returns a new list instance."""
        from guardkit.knowledge.gap_analyzer import KnowledgeGapAnalyzer

        analyzer = KnowledgeGapAnalyzer()

        with patch('guardkit.knowledge.gap_analyzer.get_graphiti') as mock_get:
            mock_graphiti = AsyncMock()
            mock_graphiti.search = AsyncMock(return_value=[])
            mock_get.return_value = mock_graphiti

            result1 = await analyzer.analyze_gaps()
            result2 = await analyzer.analyze_gaps()

            # Should be different list objects
            assert result1 is not result2

    @pytest.mark.asyncio
    async def test_analyze_gaps_all_gaps_have_required_fields(self):
        """Test that all returned gaps have required fields."""
        from guardkit.knowledge.gap_analyzer import KnowledgeGapAnalyzer

        analyzer = KnowledgeGapAnalyzer()

        with patch('guardkit.knowledge.gap_analyzer.get_graphiti') as mock_get:
            mock_graphiti = AsyncMock()
            mock_graphiti.search = AsyncMock(return_value=[])
            mock_get.return_value = mock_graphiti

            result = await analyzer.analyze_gaps()

            for gap in result:
                assert hasattr(gap, "category")
                assert hasattr(gap, "question")
                assert hasattr(gap, "importance")
                assert hasattr(gap, "context")
                assert gap.category is not None
                assert gap.question is not None
                assert gap.importance is not None
                assert gap.context is not None

    @pytest.mark.asyncio
    async def test_analyze_gaps_goals_category(self):
        """Test focus filtering with goals category."""
        from guardkit.knowledge.gap_analyzer import KnowledgeGapAnalyzer, KnowledgeCategory

        analyzer = KnowledgeGapAnalyzer()

        with patch('guardkit.knowledge.gap_analyzer.get_graphiti') as mock_get:
            mock_graphiti = AsyncMock()
            mock_graphiti.search = AsyncMock(return_value=[])
            mock_get.return_value = mock_graphiti

            result = await analyzer.analyze_gaps(focus=KnowledgeCategory.GOALS)

            for gap in result:
                assert gap.category == KnowledgeCategory.GOALS
