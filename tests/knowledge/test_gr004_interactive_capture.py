"""
Comprehensive Test Suite for GR-004 Interactive Knowledge Capture

Tests the KnowledgeGapAnalyzer and InteractiveCaptureSession classes for
interactive knowledge capture with Graphiti persistence.

Coverage Target: >=80%
Test Count: 30+ tests

Test Categories:
1. KnowledgeGapAnalyzer Tests (gap detection, category filtering)
2. InteractiveCaptureSession Tests (session flow, edge cases)
3. Fact Extraction Tests (category prefixes, sentence parsing)
4. Persistence Tests (Graphiti integration, category mapping)
5. AutoBuild Category Tests (role_customization, quality_gates, workflow_preferences)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

# Import components under test
try:
    from guardkit.knowledge.gap_analyzer import (
        KnowledgeGapAnalyzer,
        KnowledgeCategory,
        KnowledgeGap
    )
    from guardkit.knowledge.interactive_capture import (
        InteractiveCaptureSession,
        CapturedKnowledge
    )
    IMPORTS_AVAILABLE = True
except ImportError:
    IMPORTS_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not IMPORTS_AVAILABLE,
    reason="GR-004 knowledge capture modules not yet implemented"
)


# ============================================================================
# 1. KnowledgeGapAnalyzer Tests (10 tests)
# ============================================================================

class TestKnowledgeGapAnalyzer:
    """Test the KnowledgeGapAnalyzer class."""

    @pytest.mark.asyncio
    async def test_gap_analyzer_finds_missing_knowledge(self):
        """Should identify gaps based on question templates."""
        analyzer = KnowledgeGapAnalyzer()

        # Mock Graphiti to return empty knowledge
        with patch('guardkit.knowledge.gap_analyzer.get_graphiti') as mock_get_graphiti:
            mock_client = MagicMock()
            mock_client.enabled = True
            mock_client.search = AsyncMock(return_value=[])
            mock_get_graphiti.return_value = mock_client

            gaps = await analyzer.analyze_gaps(max_questions=5)

            # Should find gaps when no knowledge exists
            assert len(gaps) > 0
            assert len(gaps) <= 5
            assert all(isinstance(gap, KnowledgeGap) for gap in gaps)

    @pytest.mark.asyncio
    async def test_gap_analyzer_focuses_on_category(self):
        """Should only return gaps for focused category."""
        analyzer = KnowledgeGapAnalyzer()

        with patch('guardkit.knowledge.gap_analyzer.get_graphiti') as mock_get_graphiti:
            mock_client = MagicMock()
            mock_client.enabled = True
            mock_client.search = AsyncMock(return_value=[])
            mock_get_graphiti.return_value = mock_client

            gaps = await analyzer.analyze_gaps(
                focus=KnowledgeCategory.ARCHITECTURE,
                max_questions=10
            )

            # All gaps should be for ARCHITECTURE category
            assert all(gap.category == KnowledgeCategory.ARCHITECTURE for gap in gaps)

    @pytest.mark.asyncio
    async def test_gap_analyzer_respects_max_questions(self):
        """Should limit number of questions returned."""
        analyzer = KnowledgeGapAnalyzer()

        with patch('guardkit.knowledge.gap_analyzer.get_graphiti') as mock_get_graphiti:
            mock_client = MagicMock()
            mock_client.enabled = True
            mock_client.search = AsyncMock(return_value=[])
            mock_get_graphiti.return_value = mock_client

            # Request only 3 questions
            gaps = await analyzer.analyze_gaps(max_questions=3)

            assert len(gaps) <= 3

    @pytest.mark.asyncio
    async def test_gap_analyzer_handles_zero_max_questions(self):
        """Should return empty list when max_questions is 0."""
        analyzer = KnowledgeGapAnalyzer()

        gaps = await analyzer.analyze_gaps(max_questions=0)

        assert gaps == []

    @pytest.mark.asyncio
    async def test_gap_analyzer_handles_negative_max_questions(self):
        """Should return empty list when max_questions is negative."""
        analyzer = KnowledgeGapAnalyzer()

        gaps = await analyzer.analyze_gaps(max_questions=-5)

        assert gaps == []

    @pytest.mark.asyncio
    async def test_gap_analyzer_sorts_by_importance(self):
        """Should sort gaps by importance (high > medium > low)."""
        analyzer = KnowledgeGapAnalyzer()

        with patch('guardkit.knowledge.gap_analyzer.get_graphiti') as mock_get_graphiti:
            mock_client = MagicMock()
            mock_client.enabled = True
            mock_client.search = AsyncMock(return_value=[])
            mock_get_graphiti.return_value = mock_client

            gaps = await analyzer.analyze_gaps(max_questions=20)

            # Check that high priority comes before medium/low
            if len(gaps) > 1:
                importance_values = [gap.importance for gap in gaps]
                # High should appear before medium/low
                if 'high' in importance_values and 'medium' in importance_values:
                    high_idx = importance_values.index('high')
                    medium_idx = importance_values.index('medium')
                    assert high_idx < medium_idx

    @pytest.mark.asyncio
    async def test_gap_analyzer_handles_disabled_graphiti(self):
        """Should gracefully handle disabled Graphiti."""
        analyzer = KnowledgeGapAnalyzer()

        with patch('guardkit.knowledge.gap_analyzer.get_graphiti') as mock_get_graphiti:
            mock_client = MagicMock()
            mock_client.enabled = False
            mock_get_graphiti.return_value = mock_client

            # Should not raise exception
            gaps = await analyzer.analyze_gaps(max_questions=5)

            # Should return gaps despite Graphiti being disabled
            assert isinstance(gaps, list)

    @pytest.mark.asyncio
    async def test_gap_analyzer_handles_none_graphiti(self):
        """Should gracefully handle None Graphiti client."""
        analyzer = KnowledgeGapAnalyzer()

        with patch('guardkit.knowledge.gap_analyzer.get_graphiti') as mock_get_graphiti:
            mock_get_graphiti.return_value = None

            # Should not raise exception
            gaps = await analyzer.analyze_gaps(max_questions=5)

            # Should return gaps despite Graphiti being None
            assert isinstance(gaps, list)

    @pytest.mark.asyncio
    async def test_autobuild_categories_included(self):
        """Should include role_customization, quality_gates, workflow_preferences."""
        analyzer = KnowledgeGapAnalyzer()

        with patch('guardkit.knowledge.gap_analyzer.get_graphiti') as mock_get_graphiti:
            mock_client = MagicMock()
            mock_client.enabled = True
            mock_client.search = AsyncMock(return_value=[])
            mock_get_graphiti.return_value = mock_client

            # Get gaps for all categories
            gaps = await analyzer.analyze_gaps(max_questions=100)

            categories = {gap.category for gap in gaps}

            # Verify AutoBuild categories are included
            assert KnowledgeCategory.ROLE_CUSTOMIZATION in categories
            assert KnowledgeCategory.QUALITY_GATES in categories
            assert KnowledgeCategory.WORKFLOW_PREFERENCES in categories

    @pytest.mark.asyncio
    async def test_gap_analyzer_all_nine_categories(self):
        """Should support all 9 KnowledgeCategory values."""
        analyzer = KnowledgeGapAnalyzer()

        with patch('guardkit.knowledge.gap_analyzer.get_graphiti') as mock_get_graphiti:
            mock_client = MagicMock()
            mock_client.enabled = True
            mock_client.search = AsyncMock(return_value=[])
            mock_get_graphiti.return_value = mock_client

            # Get gaps for all categories
            gaps = await analyzer.analyze_gaps(max_questions=100)

            categories = {gap.category for gap in gaps}

            # Verify all 9 categories
            expected_categories = {
                KnowledgeCategory.PROJECT_OVERVIEW,
                KnowledgeCategory.ARCHITECTURE,
                KnowledgeCategory.DOMAIN,
                KnowledgeCategory.CONSTRAINTS,
                KnowledgeCategory.DECISIONS,
                KnowledgeCategory.GOALS,
                KnowledgeCategory.ROLE_CUSTOMIZATION,
                KnowledgeCategory.QUALITY_GATES,
                KnowledgeCategory.WORKFLOW_PREFERENCES,
            }

            assert categories == expected_categories


# ============================================================================
# 2. InteractiveCaptureSession Tests (12 tests)
# ============================================================================

class TestInteractiveCaptureSession:
    """Test the InteractiveCaptureSession class."""

    @pytest.mark.asyncio
    async def test_capture_session_skip_command(self):
        """Should handle 'skip' command."""
        session = InteractiveCaptureSession()

        # Mock dependencies
        with patch('guardkit.knowledge.interactive_capture.get_graphiti') as mock_get_graphiti, \
             patch.object(session._analyzer, 'analyze_gaps') as mock_analyze:

            mock_client = MagicMock()
            mock_client.add_episode = AsyncMock()
            mock_get_graphiti.return_value = mock_client

            # Return one gap
            mock_analyze.return_value = [
                KnowledgeGap(
                    category=KnowledgeCategory.ARCHITECTURE,
                    question="What is the architecture?",
                    importance="high",
                    context="Context"
                )
            ]

            # Mock UI callback that returns 'skip'
            def ui_callback(event, data=None):
                if event == 'get_input':
                    return 'skip'

            captured = await session.run_session(ui_callback=ui_callback)

            # Should have skipped, no knowledge captured
            assert len(captured) == 0

    @pytest.mark.asyncio
    async def test_capture_session_skip_s_shorthand(self):
        """Should handle 's' shorthand for skip."""
        session = InteractiveCaptureSession()

        with patch('guardkit.knowledge.interactive_capture.get_graphiti') as mock_get_graphiti, \
             patch.object(session._analyzer, 'analyze_gaps') as mock_analyze:

            mock_client = MagicMock()
            mock_client.add_episode = AsyncMock()
            mock_get_graphiti.return_value = mock_client

            mock_analyze.return_value = [
                KnowledgeGap(
                    category=KnowledgeCategory.ARCHITECTURE,
                    question="What is the architecture?",
                    importance="high",
                    context="Context"
                )
            ]

            def ui_callback(event, data=None):
                if event == 'get_input':
                    return 's'

            captured = await session.run_session(ui_callback=ui_callback)

            assert len(captured) == 0

    @pytest.mark.asyncio
    async def test_capture_session_skip_empty_input(self):
        """Should handle empty input as skip."""
        session = InteractiveCaptureSession()

        with patch('guardkit.knowledge.interactive_capture.get_graphiti') as mock_get_graphiti, \
             patch.object(session._analyzer, 'analyze_gaps') as mock_analyze:

            mock_client = MagicMock()
            mock_client.add_episode = AsyncMock()
            mock_get_graphiti.return_value = mock_client

            mock_analyze.return_value = [
                KnowledgeGap(
                    category=KnowledgeCategory.ARCHITECTURE,
                    question="What is the architecture?",
                    importance="high",
                    context="Context"
                )
            ]

            def ui_callback(event, data=None):
                if event == 'get_input':
                    return ''

            captured = await session.run_session(ui_callback=ui_callback)

            assert len(captured) == 0

    @pytest.mark.asyncio
    async def test_capture_session_quit_command(self):
        """Should handle 'quit' command."""
        session = InteractiveCaptureSession()

        with patch('guardkit.knowledge.interactive_capture.get_graphiti') as mock_get_graphiti, \
             patch.object(session._analyzer, 'analyze_gaps') as mock_analyze:

            mock_client = MagicMock()
            mock_client.add_episode = AsyncMock()
            mock_get_graphiti.return_value = mock_client

            mock_analyze.return_value = [
                KnowledgeGap(
                    category=KnowledgeCategory.ARCHITECTURE,
                    question="Question 1",
                    importance="high",
                    context="Context"
                ),
                KnowledgeGap(
                    category=KnowledgeCategory.DOMAIN,
                    question="Question 2",
                    importance="high",
                    context="Context"
                )
            ]

            def ui_callback(event, data=None):
                if event == 'get_input':
                    return 'quit'

            captured = await session.run_session(ui_callback=ui_callback)

            # Should quit immediately, no knowledge captured
            assert len(captured) == 0

    @pytest.mark.asyncio
    async def test_capture_session_quit_q_shorthand(self):
        """Should handle 'q' shorthand for quit."""
        session = InteractiveCaptureSession()

        with patch('guardkit.knowledge.interactive_capture.get_graphiti') as mock_get_graphiti, \
             patch.object(session._analyzer, 'analyze_gaps') as mock_analyze:

            mock_client = MagicMock()
            mock_get_graphiti.return_value = mock_client

            mock_analyze.return_value = [
                KnowledgeGap(
                    category=KnowledgeCategory.ARCHITECTURE,
                    question="Question",
                    importance="high",
                    context="Context"
                )
            ]

            def ui_callback(event, data=None):
                if event == 'get_input':
                    return 'q'

            captured = await session.run_session(ui_callback=ui_callback)

            assert len(captured) == 0

    @pytest.mark.asyncio
    async def test_capture_session_quit_exit_command(self):
        """Should handle 'exit' command."""
        session = InteractiveCaptureSession()

        with patch('guardkit.knowledge.interactive_capture.get_graphiti') as mock_get_graphiti, \
             patch.object(session._analyzer, 'analyze_gaps') as mock_analyze:

            mock_client = MagicMock()
            mock_get_graphiti.return_value = mock_client

            mock_analyze.return_value = [
                KnowledgeGap(
                    category=KnowledgeCategory.ARCHITECTURE,
                    question="Question",
                    importance="high",
                    context="Context"
                )
            ]

            def ui_callback(event, data=None):
                if event == 'get_input':
                    return 'exit'

            captured = await session.run_session(ui_callback=ui_callback)

            assert len(captured) == 0

    @pytest.mark.asyncio
    async def test_capture_session_with_answer(self):
        """Should capture knowledge when answer provided."""
        session = InteractiveCaptureSession()

        with patch('guardkit.knowledge.interactive_capture.get_graphiti') as mock_get_graphiti, \
             patch.object(session._analyzer, 'analyze_gaps') as mock_analyze:

            mock_client = MagicMock()
            mock_client.add_episode = AsyncMock()
            mock_get_graphiti.return_value = mock_client

            mock_analyze.return_value = [
                KnowledgeGap(
                    category=KnowledgeCategory.ARCHITECTURE,
                    question="What is the architecture?",
                    importance="high",
                    context="Context"
                )
            ]

            def ui_callback(event, data=None):
                if event == 'get_input':
                    return 'The project uses a microservices architecture'

            captured = await session.run_session(ui_callback=ui_callback)

            # Should have captured the answer
            assert len(captured) == 1
            assert captured[0].category == KnowledgeCategory.ARCHITECTURE
            assert captured[0].answer == 'The project uses a microservices architecture'

    @pytest.mark.asyncio
    async def test_capture_session_no_gaps(self):
        """Should handle case with no knowledge gaps."""
        session = InteractiveCaptureSession()

        with patch.object(session._analyzer, 'analyze_gaps') as mock_analyze:
            mock_analyze.return_value = []

            def ui_callback(event, data=None):
                pass

            captured = await session.run_session(ui_callback=ui_callback)

            assert len(captured) == 0

    @pytest.mark.asyncio
    async def test_capture_session_clears_captured_list(self):
        """Should clear captured list at start of new session."""
        session = InteractiveCaptureSession()

        # Manually add item to captured list
        session._captured.append(
            CapturedKnowledge(
                category=KnowledgeCategory.ARCHITECTURE,
                question="Old question",
                answer="Old answer"
            )
        )

        with patch.object(session._analyzer, 'analyze_gaps') as mock_analyze:
            mock_analyze.return_value = []

            captured = await session.run_session()

            # Should have cleared the old item
            assert len(captured) == 0

    @pytest.mark.asyncio
    async def test_capture_session_handles_none_callback_answer(self):
        """Should handle None return from callback."""
        session = InteractiveCaptureSession()

        with patch('guardkit.knowledge.interactive_capture.get_graphiti') as mock_get_graphiti, \
             patch.object(session._analyzer, 'analyze_gaps') as mock_analyze:

            mock_client = MagicMock()
            mock_get_graphiti.return_value = mock_client

            mock_analyze.return_value = [
                KnowledgeGap(
                    category=KnowledgeCategory.ARCHITECTURE,
                    question="Question",
                    importance="high",
                    context="Context"
                )
            ]

            def ui_callback(event, data=None):
                if event == 'get_input':
                    return None  # Simulate no input

            captured = await session.run_session(ui_callback=ui_callback)

            # Should treat None as empty string (skip)
            assert len(captured) == 0

    @pytest.mark.asyncio
    async def test_capture_session_mixed_skip_and_answer(self):
        """Should handle mix of skip and answer responses."""
        session = InteractiveCaptureSession()

        with patch('guardkit.knowledge.interactive_capture.get_graphiti') as mock_get_graphiti, \
             patch.object(session._analyzer, 'analyze_gaps') as mock_analyze:

            mock_client = MagicMock()
            mock_client.add_episode = AsyncMock()
            mock_get_graphiti.return_value = mock_client

            mock_analyze.return_value = [
                KnowledgeGap(
                    category=KnowledgeCategory.ARCHITECTURE,
                    question="Question 1",
                    importance="high",
                    context="Context"
                ),
                KnowledgeGap(
                    category=KnowledgeCategory.DOMAIN,
                    question="Question 2",
                    importance="high",
                    context="Context"
                ),
                KnowledgeGap(
                    category=KnowledgeCategory.CONSTRAINTS,
                    question="Question 3",
                    importance="high",
                    context="Context"
                )
            ]

            # Skip first, answer second, skip third
            responses = ['skip', 'This is my answer', 's']
            response_idx = 0

            def ui_callback(event, data=None):
                nonlocal response_idx
                if event == 'get_input':
                    response = responses[response_idx]
                    response_idx += 1
                    return response

            captured = await session.run_session(ui_callback=ui_callback)

            # Should have captured only the second answer
            assert len(captured) == 1
            assert captured[0].answer == 'This is my answer'

    @pytest.mark.asyncio
    async def test_capture_session_property(self):
        """Should expose captured property."""
        session = InteractiveCaptureSession()

        # Initially empty
        assert session.captured == []

        # Manually add item
        item = CapturedKnowledge(
            category=KnowledgeCategory.ARCHITECTURE,
            question="Question",
            answer="Answer"
        )
        session._captured.append(item)

        # Should be accessible via property
        assert len(session.captured) == 1
        assert session.captured[0] == item


# ============================================================================
# 3. Fact Extraction Tests (6 tests)
# ============================================================================

class TestFactExtraction:
    """Test fact extraction from answers."""

    def test_fact_extraction_prefixes_correctly(self):
        """Should prefix facts with category context."""
        session = InteractiveCaptureSession()

        # Test different categories
        test_cases = [
            (KnowledgeCategory.ARCHITECTURE, "Architecture: "),
            (KnowledgeCategory.PROJECT_OVERVIEW, "Project: "),
            (KnowledgeCategory.DOMAIN, "Domain: "),
            (KnowledgeCategory.CONSTRAINTS, "Constraint: "),
            (KnowledgeCategory.DECISIONS, "Decision: "),
            (KnowledgeCategory.ROLE_CUSTOMIZATION, "Role: "),
            (KnowledgeCategory.QUALITY_GATES, "Quality gate: "),
            (KnowledgeCategory.WORKFLOW_PREFERENCES, "Workflow: "),
        ]

        for category, expected_prefix in test_cases:
            facts = session._extract_facts("This is a test sentence", category)

            assert len(facts) > 0
            assert facts[0].startswith(expected_prefix)

    def test_fact_extraction_splits_sentences(self):
        """Should split answer into multiple facts by sentence."""
        session = InteractiveCaptureSession()

        answer = "First sentence here. Second sentence here. Third sentence here."
        facts = session._extract_facts(answer, KnowledgeCategory.ARCHITECTURE)

        # Should have extracted 3 facts
        assert len(facts) == 3
        assert all(fact.startswith("Architecture: ") for fact in facts)

    def test_fact_extraction_filters_short_sentences(self):
        """Should filter out sentences shorter than minimum length."""
        session = InteractiveCaptureSession()

        # Mix of long and short sentences
        answer = "Short. This is a longer sentence that should be kept. Tiny."
        facts = session._extract_facts(answer, KnowledgeCategory.ARCHITECTURE)

        # Should only keep the longer sentence
        assert len(facts) == 1
        assert "longer sentence" in facts[0]

    def test_fact_extraction_handles_empty_answer(self):
        """Should return empty list for empty answer."""
        session = InteractiveCaptureSession()

        facts = session._extract_facts("", KnowledgeCategory.ARCHITECTURE)

        assert facts == []

    def test_fact_extraction_handles_none_answer(self):
        """Should return empty list for None answer."""
        session = InteractiveCaptureSession()

        facts = session._extract_facts(None, KnowledgeCategory.ARCHITECTURE)

        assert facts == []

    def test_fact_extraction_minimum_fact_length(self):
        """Should respect minimum fact length constant."""
        session = InteractiveCaptureSession()

        # Get the minimum length
        min_length = session._MIN_FACT_LENGTH

        # Create sentence just under minimum
        short_sentence = "x" * (min_length - 1)
        # Create sentence at minimum
        min_sentence = "y" * min_length

        answer = f"{short_sentence}. {min_sentence}."
        facts = session._extract_facts(answer, KnowledgeCategory.ARCHITECTURE)

        # Should only keep the minimum-length sentence
        assert len(facts) == 1
        assert "y" * min_length in facts[0]


# ============================================================================
# 4. Persistence Tests (8 tests)
# ============================================================================

class TestPersistence:
    """Test Graphiti persistence integration."""

    @pytest.mark.asyncio
    async def test_persistence_maps_categories_correctly(self):
        """Should map categories to correct group_ids."""
        session = InteractiveCaptureSession()

        # Test category to group_id mapping
        test_cases = [
            (KnowledgeCategory.PROJECT_OVERVIEW, "project_overview"),
            (KnowledgeCategory.GOALS, "project_overview"),
            (KnowledgeCategory.ARCHITECTURE, "project_architecture"),
            (KnowledgeCategory.DOMAIN, "domain_knowledge"),
            (KnowledgeCategory.CONSTRAINTS, "project_constraints"),
            (KnowledgeCategory.DECISIONS, "project_decisions"),
            (KnowledgeCategory.ROLE_CUSTOMIZATION, "role_constraints"),
            (KnowledgeCategory.QUALITY_GATES, "quality_gate_configs"),
            (KnowledgeCategory.WORKFLOW_PREFERENCES, "implementation_modes"),
        ]

        for category, expected_group_id in test_cases:
            group_id = session._category_to_group_id(category)
            assert group_id == expected_group_id

    @pytest.mark.asyncio
    async def test_persistence_saves_to_graphiti(self):
        """Should save captured knowledge to Graphiti."""
        session = InteractiveCaptureSession()

        with patch('guardkit.knowledge.interactive_capture.get_graphiti') as mock_get_graphiti:
            mock_client = MagicMock()
            mock_client.add_episode = AsyncMock()
            mock_get_graphiti.return_value = mock_client
            session._graphiti = mock_client

            # Add captured knowledge
            session._captured.append(
                CapturedKnowledge(
                    category=KnowledgeCategory.ARCHITECTURE,
                    question="What is the architecture?",
                    answer="Microservices architecture",
                    extracted_facts=["Architecture: Microservices architecture"]
                )
            )

            await session._save_captured_knowledge()

            # Should have called add_episode
            mock_client.add_episode.assert_called_once()
            call_args = mock_client.add_episode.call_args

            # Verify episode structure
            assert call_args.kwargs['group_id'] == 'project_architecture'
            assert 'Interactive Capture' in call_args.kwargs['name']
            assert 'Microservices architecture' in call_args.kwargs['episode_body']

    @pytest.mark.asyncio
    async def test_persistence_handles_none_graphiti(self):
        """Should gracefully handle None Graphiti client."""
        session = InteractiveCaptureSession()
        session._graphiti = None

        # Add captured knowledge
        session._captured.append(
            CapturedKnowledge(
                category=KnowledgeCategory.ARCHITECTURE,
                question="Question",
                answer="Answer"
            )
        )

        # Should not raise exception
        await session._save_captured_knowledge()

    @pytest.mark.asyncio
    async def test_persistence_handles_empty_captured(self):
        """Should handle empty captured list gracefully."""
        session = InteractiveCaptureSession()

        with patch('guardkit.knowledge.interactive_capture.get_graphiti') as mock_get_graphiti:
            mock_client = MagicMock()
            mock_client.add_episode = AsyncMock()
            mock_get_graphiti.return_value = mock_client
            session._graphiti = mock_client

            # Clear captured list
            session._captured = []

            await session._save_captured_knowledge()

            # Should not have called add_episode
            mock_client.add_episode.assert_not_called()

    @pytest.mark.asyncio
    async def test_persistence_groups_by_category(self):
        """Should group captured knowledge by category before saving."""
        session = InteractiveCaptureSession()

        with patch('guardkit.knowledge.interactive_capture.get_graphiti') as mock_get_graphiti:
            mock_client = MagicMock()
            mock_client.add_episode = AsyncMock()
            mock_get_graphiti.return_value = mock_client
            session._graphiti = mock_client

            # Add multiple items from different categories
            session._captured.extend([
                CapturedKnowledge(
                    category=KnowledgeCategory.ARCHITECTURE,
                    question="Question 1",
                    answer="Answer 1",
                    extracted_facts=["Architecture: Answer 1"]
                ),
                CapturedKnowledge(
                    category=KnowledgeCategory.ARCHITECTURE,
                    question="Question 2",
                    answer="Answer 2",
                    extracted_facts=["Architecture: Answer 2"]
                ),
                CapturedKnowledge(
                    category=KnowledgeCategory.DOMAIN,
                    question="Question 3",
                    answer="Answer 3",
                    extracted_facts=["Domain: Answer 3"]
                )
            ])

            await session._save_captured_knowledge()

            # Should have called add_episode twice (once per category)
            assert mock_client.add_episode.call_count == 2

    @pytest.mark.asyncio
    async def test_persistence_includes_metadata_header(self):
        """Should include structured metadata header in episode body."""
        session = InteractiveCaptureSession()

        with patch('guardkit.knowledge.interactive_capture.get_graphiti') as mock_get_graphiti:
            mock_client = MagicMock()
            mock_client.add_episode = AsyncMock()
            mock_get_graphiti.return_value = mock_client
            session._graphiti = mock_client

            session._captured.append(
                CapturedKnowledge(
                    category=KnowledgeCategory.ARCHITECTURE,
                    question="Question",
                    answer="Answer",
                    extracted_facts=["Architecture: Answer"]
                )
            )

            await session._save_captured_knowledge()

            call_args = mock_client.add_episode.call_args
            episode_body = call_args.kwargs['episode_body']

            # Verify metadata header
            assert 'entity_type: captured_knowledge' in episode_body
            assert 'category: architecture' in episode_body
            assert 'source: interactive_capture' in episode_body
            assert 'captured_at:' in episode_body

    @pytest.mark.asyncio
    async def test_persistence_includes_qa_pairs_and_facts(self):
        """Should include both Q&A pairs and facts in episode body."""
        session = InteractiveCaptureSession()

        with patch('guardkit.knowledge.interactive_capture.get_graphiti') as mock_get_graphiti:
            mock_client = MagicMock()
            mock_client.add_episode = AsyncMock()
            mock_get_graphiti.return_value = mock_client
            session._graphiti = mock_client

            session._captured.append(
                CapturedKnowledge(
                    category=KnowledgeCategory.ARCHITECTURE,
                    question="What is the architecture?",
                    answer="Microservices",
                    extracted_facts=["Architecture: Microservices"]
                )
            )

            await session._save_captured_knowledge()

            call_args = mock_client.add_episode.call_args
            episode_body = call_args.kwargs['episode_body']

            # Verify Q&A pairs section
            assert 'QA Pairs:' in episode_body
            assert 'Q: What is the architecture?' in episode_body
            assert 'A: Microservices' in episode_body

            # Verify facts section
            assert 'Facts:' in episode_body
            assert '- Architecture: Microservices' in episode_body

    @pytest.mark.asyncio
    async def test_persistence_handles_graphiti_errors(self):
        """Should gracefully handle Graphiti errors during save."""
        session = InteractiveCaptureSession()

        with patch('guardkit.knowledge.interactive_capture.get_graphiti') as mock_get_graphiti:
            mock_client = MagicMock()
            # Simulate Graphiti error
            mock_client.add_episode = AsyncMock(side_effect=Exception("Graphiti error"))
            mock_get_graphiti.return_value = mock_client
            session._graphiti = mock_client

            session._captured.append(
                CapturedKnowledge(
                    category=KnowledgeCategory.ARCHITECTURE,
                    question="Question",
                    answer="Answer"
                )
            )

            # Should not raise exception
            await session._save_captured_knowledge()


# ============================================================================
# 5. Integration Tests (4 tests)
# ============================================================================

class TestIntegration:
    """Integration tests for complete workflows."""

    @pytest.mark.asyncio
    async def test_full_capture_workflow(self):
        """Test complete capture workflow from gaps to persistence."""
        session = InteractiveCaptureSession()

        with patch('guardkit.knowledge.interactive_capture.get_graphiti') as mock_get_graphiti, \
             patch.object(session._analyzer, 'analyze_gaps') as mock_analyze:

            mock_client = MagicMock()
            mock_client.add_episode = AsyncMock()
            mock_get_graphiti.return_value = mock_client
            session._graphiti = mock_client

            # Mock gaps
            mock_analyze.return_value = [
                KnowledgeGap(
                    category=KnowledgeCategory.ARCHITECTURE,
                    question="What is the architecture?",
                    importance="high",
                    context="Context"
                ),
                KnowledgeGap(
                    category=KnowledgeCategory.DOMAIN,
                    question="What are the domain terms?",
                    importance="medium",
                    context="Context"
                )
            ]

            # Mock UI callback with answers
            responses = [
                'Microservices architecture with API gateway',
                'User, Order, Payment are key entities'
            ]
            response_idx = 0

            def ui_callback(event, data=None):
                nonlocal response_idx
                if event == 'get_input':
                    response = responses[response_idx]
                    response_idx += 1
                    return response

            captured = await session.run_session(ui_callback=ui_callback)

            # Verify captured knowledge
            assert len(captured) == 2
            assert captured[0].category == KnowledgeCategory.ARCHITECTURE
            assert captured[1].category == KnowledgeCategory.DOMAIN

            # Verify persistence was called
            assert mock_client.add_episode.call_count >= 1

    @pytest.mark.asyncio
    async def test_autobuild_category_capture(self):
        """Test capturing AutoBuild category knowledge."""
        session = InteractiveCaptureSession()

        with patch('guardkit.knowledge.interactive_capture.get_graphiti') as mock_get_graphiti, \
             patch.object(session._analyzer, 'analyze_gaps') as mock_analyze:

            mock_client = MagicMock()
            mock_client.add_episode = AsyncMock()
            mock_get_graphiti.return_value = mock_client
            session._graphiti = mock_client

            # Mock AutoBuild category gaps
            mock_analyze.return_value = [
                KnowledgeGap(
                    category=KnowledgeCategory.ROLE_CUSTOMIZATION,
                    question="What should Player ask before implementing?",
                    importance="high",
                    context="Prevents autonomous changes"
                ),
                KnowledgeGap(
                    category=KnowledgeCategory.QUALITY_GATES,
                    question="What coverage threshold?",
                    importance="medium",
                    context="Quality gate config"
                )
            ]

            responses = [
                'Always ask before modifying auth code',
                '80% for features, 60% for scaffolding'
            ]
            response_idx = 0

            def ui_callback(event, data=None):
                nonlocal response_idx
                if event == 'get_input':
                    response = responses[response_idx]
                    response_idx += 1
                    return response

            captured = await session.run_session(ui_callback=ui_callback)

            # Verify AutoBuild categories captured
            assert len(captured) == 2
            assert captured[0].category == KnowledgeCategory.ROLE_CUSTOMIZATION
            assert captured[1].category == KnowledgeCategory.QUALITY_GATES

            # Verify correct group_ids used
            assert mock_client.add_episode.call_count >= 1

            # Check group_ids in calls
            group_ids_used = [
                call.kwargs['group_id']
                for call in mock_client.add_episode.call_args_list
            ]
            assert 'role_constraints' in group_ids_used
            assert 'quality_gate_configs' in group_ids_used

    @pytest.mark.asyncio
    async def test_focus_on_autobuild_categories(self):
        """Test focusing on AutoBuild categories specifically."""
        session = InteractiveCaptureSession()

        with patch('guardkit.knowledge.interactive_capture.get_graphiti') as mock_get_graphiti, \
             patch.object(session._analyzer, 'analyze_gaps') as mock_analyze:

            mock_client = MagicMock()
            mock_client.add_episode = AsyncMock()
            mock_get_graphiti.return_value = mock_client
            session._graphiti = mock_client

            mock_analyze.return_value = [
                KnowledgeGap(
                    category=KnowledgeCategory.WORKFLOW_PREFERENCES,
                    question="Implementation mode preference?",
                    importance="medium",
                    context="Workflow preference"
                )
            ]

            def ui_callback(event, data=None):
                if event == 'get_input':
                    return 'Prefer task-work for complex tasks'

            captured = await session.run_session(
                focus=KnowledgeCategory.WORKFLOW_PREFERENCES,
                ui_callback=ui_callback
            )

            # Should have captured workflow preference
            assert len(captured) == 1
            assert captured[0].category == KnowledgeCategory.WORKFLOW_PREFERENCES

    @pytest.mark.asyncio
    async def test_all_nine_categories_can_be_captured(self):
        """Test that all 9 categories can be captured successfully."""
        session = InteractiveCaptureSession()

        with patch('guardkit.knowledge.interactive_capture.get_graphiti') as mock_get_graphiti, \
             patch.object(session._analyzer, 'analyze_gaps') as mock_analyze:

            mock_client = MagicMock()
            mock_client.add_episode = AsyncMock()
            mock_get_graphiti.return_value = mock_client
            session._graphiti = mock_client

            # Create gaps for all 9 categories
            all_categories = [
                KnowledgeCategory.PROJECT_OVERVIEW,
                KnowledgeCategory.ARCHITECTURE,
                KnowledgeCategory.DOMAIN,
                KnowledgeCategory.CONSTRAINTS,
                KnowledgeCategory.DECISIONS,
                KnowledgeCategory.GOALS,
                KnowledgeCategory.ROLE_CUSTOMIZATION,
                KnowledgeCategory.QUALITY_GATES,
                KnowledgeCategory.WORKFLOW_PREFERENCES,
            ]

            mock_analyze.return_value = [
                KnowledgeGap(
                    category=cat,
                    question=f"Question for {cat.value}",
                    importance="high",
                    context="Context"
                )
                for cat in all_categories
            ]

            # Answer all questions with a simple counter
            counter = 0

            def ui_callback(event, data=None):
                nonlocal counter
                if event == 'get_input':
                    counter += 1
                    return f"Answer number {counter}"

            captured = await session.run_session(ui_callback=ui_callback)

            # Should have captured all 9 categories
            assert len(captured) == 9
            captured_categories = {item.category for item in captured}
            assert captured_categories == set(all_categories)
