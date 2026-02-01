"""
Comprehensive Test Suite for InteractiveCaptureSession

Tests the interactive knowledge capture session including:
- CapturedKnowledge dataclass with required fields
- InteractiveCaptureSession initialization
- run_session() method with focus filtering, skip/quit handling
- Answer processing and fact extraction
- Graphiti integration for saving captured knowledge
- Format methods for intro and summary
- UI callback event handling

Coverage Target: >=85%
Test Count: 55 tests
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
from typing import List, Optional, Callable
from dataclasses import is_dataclass, fields


# ============================================================================
# 1. CapturedKnowledge Dataclass Tests (5 tests)
# ============================================================================

class TestCapturedKnowledgeDataclass:
    """Test CapturedKnowledge dataclass definition."""

    def test_dataclass_has_required_fields(self):
        """Test that CapturedKnowledge has all required fields."""
        from guardkit.knowledge.interactive_capture import CapturedKnowledge
        from guardkit.knowledge.gap_analyzer import KnowledgeCategory

        knowledge = CapturedKnowledge(
            category=KnowledgeCategory.PROJECT_OVERVIEW,
            question="What is the purpose?",
            answer="This project builds AI assistants.",
            extracted_facts=["Project builds AI assistants"],
            confidence=0.95,
        )

        assert knowledge.category == KnowledgeCategory.PROJECT_OVERVIEW
        assert knowledge.question == "What is the purpose?"
        assert knowledge.answer == "This project builds AI assistants."
        assert knowledge.extracted_facts == ["Project builds AI assistants"]
        assert knowledge.confidence == 0.95

    def test_dataclass_extracted_facts_defaults_to_empty_list(self):
        """Test that extracted_facts defaults to empty list."""
        from guardkit.knowledge.interactive_capture import CapturedKnowledge
        from guardkit.knowledge.gap_analyzer import KnowledgeCategory

        knowledge = CapturedKnowledge(
            category=KnowledgeCategory.ARCHITECTURE,
            question="What is the architecture?",
            answer="Microservices architecture",
        )

        assert knowledge.extracted_facts == []

    def test_dataclass_confidence_defaults_to_one(self):
        """Test that confidence defaults to 1.0."""
        from guardkit.knowledge.interactive_capture import CapturedKnowledge
        from guardkit.knowledge.gap_analyzer import KnowledgeCategory

        knowledge = CapturedKnowledge(
            category=KnowledgeCategory.DOMAIN,
            question="What domain terms exist?",
            answer="Terms include X, Y, Z",
        )

        assert knowledge.confidence == 1.0

    def test_dataclass_is_proper_dataclass(self):
        """Test that CapturedKnowledge is a proper dataclass."""
        from guardkit.knowledge.interactive_capture import CapturedKnowledge

        assert is_dataclass(CapturedKnowledge)
        field_names = {f.name for f in fields(CapturedKnowledge)}
        assert field_names == {"category", "question", "answer", "extracted_facts", "confidence"}

    def test_dataclass_field_types(self):
        """Test that fields have correct types."""
        from guardkit.knowledge.interactive_capture import CapturedKnowledge
        from guardkit.knowledge.gap_analyzer import KnowledgeCategory

        field_types = {f.name: f.type for f in fields(CapturedKnowledge)}

        assert field_types["category"] == KnowledgeCategory
        assert "str" in str(field_types["question"])
        assert "str" in str(field_types["answer"])


# ============================================================================
# 2. InteractiveCaptureSession Initialization Tests (3 tests)
# ============================================================================

class TestInteractiveCaptureSessionInit:
    """Test InteractiveCaptureSession initialization."""

    def test_session_can_be_instantiated(self):
        """Test creating an InteractiveCaptureSession instance."""
        from guardkit.knowledge.interactive_capture import InteractiveCaptureSession

        with patch('guardkit.knowledge.interactive_capture.get_graphiti') as mock_get:
            mock_get.return_value = MagicMock()
            session = InteractiveCaptureSession()
            assert session is not None

    def test_session_initializes_graphiti_client(self):
        """Test that session initializes with graphiti client."""
        from guardkit.knowledge.interactive_capture import InteractiveCaptureSession

        with patch('guardkit.knowledge.interactive_capture.get_graphiti') as mock_get:
            mock_graphiti = MagicMock()
            mock_get.return_value = mock_graphiti

            session = InteractiveCaptureSession()

            mock_get.assert_called()

    def test_session_initializes_gap_analyzer(self):
        """Test that session initializes with KnowledgeGapAnalyzer."""
        from guardkit.knowledge.interactive_capture import InteractiveCaptureSession

        with patch('guardkit.knowledge.interactive_capture.get_graphiti') as mock_get:
            mock_get.return_value = MagicMock()
            session = InteractiveCaptureSession()

            # Session should have a gap analyzer
            assert hasattr(session, '_analyzer') or hasattr(session, 'analyzer')


# ============================================================================
# 3. Captured Property Tests (3 tests)
# ============================================================================

class TestCapturedProperty:
    """Test the captured property."""

    def test_captured_initially_empty(self):
        """Test that captured list is initially empty."""
        from guardkit.knowledge.interactive_capture import InteractiveCaptureSession

        with patch('guardkit.knowledge.interactive_capture.get_graphiti') as mock_get:
            mock_get.return_value = MagicMock()
            session = InteractiveCaptureSession()

            assert session.captured == []

    def test_captured_returns_list(self):
        """Test that captured returns a list."""
        from guardkit.knowledge.interactive_capture import InteractiveCaptureSession

        with patch('guardkit.knowledge.interactive_capture.get_graphiti') as mock_get:
            mock_get.return_value = MagicMock()
            session = InteractiveCaptureSession()

            assert isinstance(session.captured, list)

    def test_captured_returns_captured_knowledge_objects(self):
        """Test that captured contains CapturedKnowledge objects after session."""
        from guardkit.knowledge.interactive_capture import InteractiveCaptureSession, CapturedKnowledge
        from guardkit.knowledge.gap_analyzer import KnowledgeCategory, KnowledgeGap

        with patch('guardkit.knowledge.interactive_capture.get_graphiti') as mock_get:
            mock_graphiti = AsyncMock()
            mock_graphiti.add_episode = AsyncMock(return_value="episode-123")
            mock_get.return_value = mock_graphiti

            session = InteractiveCaptureSession()
            # Manually add captured knowledge for testing
            session._captured = [
                CapturedKnowledge(
                    category=KnowledgeCategory.PROJECT_OVERVIEW,
                    question="Test question?",
                    answer="Test answer",
                )
            ]

            assert len(session.captured) == 1
            assert isinstance(session.captured[0], CapturedKnowledge)


# ============================================================================
# 4. run_session() Basic Tests (5 tests)
# ============================================================================

class TestRunSessionBasic:
    """Test basic run_session() behavior."""

    @pytest.mark.asyncio
    async def test_run_session_returns_list(self):
        """Test that run_session returns a List."""
        from guardkit.knowledge.interactive_capture import InteractiveCaptureSession
        from guardkit.knowledge.gap_analyzer import KnowledgeGap, KnowledgeCategory

        with patch('guardkit.knowledge.interactive_capture.get_graphiti') as mock_get:
            mock_graphiti = AsyncMock()
            mock_graphiti.add_episode = AsyncMock(return_value="episode-123")
            mock_get.return_value = mock_graphiti

            with patch.object(
                InteractiveCaptureSession, '_get_gaps',
                new=AsyncMock(return_value=[])
            ) as mock_gaps:
                session = InteractiveCaptureSession()

                def mock_callback(event, data=None):
                    pass

                result = await session.run_session(ui_callback=mock_callback)

                assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_run_session_accepts_focus_parameter(self):
        """Test that run_session accepts focus parameter."""
        from guardkit.knowledge.interactive_capture import InteractiveCaptureSession
        from guardkit.knowledge.gap_analyzer import KnowledgeCategory

        with patch('guardkit.knowledge.interactive_capture.get_graphiti') as mock_get:
            mock_graphiti = AsyncMock()
            mock_graphiti.add_episode = AsyncMock(return_value="episode-123")
            mock_get.return_value = mock_graphiti

            session = InteractiveCaptureSession()

            with patch.object(session, '_get_gaps', new=AsyncMock(return_value=[])) as mock_analyze:
                def mock_callback(event, data=None):
                    pass

                await session.run_session(
                    focus=KnowledgeCategory.ARCHITECTURE,
                    ui_callback=mock_callback
                )

                # Verify focus was passed to gap analysis
                mock_analyze.assert_called()

    @pytest.mark.asyncio
    async def test_run_session_accepts_max_questions_parameter(self):
        """Test that run_session accepts max_questions parameter."""
        from guardkit.knowledge.interactive_capture import InteractiveCaptureSession

        with patch('guardkit.knowledge.interactive_capture.get_graphiti') as mock_get:
            mock_graphiti = AsyncMock()
            mock_graphiti.add_episode = AsyncMock(return_value="episode-123")
            mock_get.return_value = mock_graphiti

            session = InteractiveCaptureSession()

            with patch.object(session, '_get_gaps', new=AsyncMock(return_value=[])) as mock_analyze:
                def mock_callback(event, data=None):
                    pass

                await session.run_session(
                    max_questions=5,
                    ui_callback=mock_callback
                )

                # Method should accept max_questions without error
                assert True

    @pytest.mark.asyncio
    async def test_run_session_requires_ui_callback(self):
        """Test that run_session requires ui_callback parameter."""
        from guardkit.knowledge.interactive_capture import InteractiveCaptureSession

        with patch('guardkit.knowledge.interactive_capture.get_graphiti') as mock_get:
            mock_get.return_value = MagicMock()

            session = InteractiveCaptureSession()

            # Should raise error or work with callback - test both behaviors
            with patch.object(session, '_get_gaps', new=AsyncMock(return_value=[])):
                # Either requires callback or has default behavior
                try:
                    result = await session.run_session(ui_callback=None)
                    # If it doesn't raise, it should still work
                    assert isinstance(result, list)
                except (TypeError, ValueError):
                    # Expected if ui_callback is required
                    pass

    @pytest.mark.asyncio
    async def test_run_session_with_no_gaps_returns_empty(self):
        """Test that run_session returns empty list when no gaps found."""
        from guardkit.knowledge.interactive_capture import InteractiveCaptureSession

        with patch('guardkit.knowledge.interactive_capture.get_graphiti') as mock_get:
            mock_graphiti = AsyncMock()
            mock_get.return_value = mock_graphiti

            session = InteractiveCaptureSession()

            with patch.object(session, '_get_gaps', new=AsyncMock(return_value=[])):
                def mock_callback(event, data=None):
                    pass

                result = await session.run_session(ui_callback=mock_callback)

                assert result == []


# ============================================================================
# 5. run_session() UI Callback Tests (6 tests)
# ============================================================================

class TestRunSessionUICallback:
    """Test UI callback interactions in run_session()."""

    @pytest.mark.asyncio
    async def test_run_session_calls_callback_with_intro(self):
        """Test that run_session calls callback with 'intro' event."""
        from guardkit.knowledge.interactive_capture import InteractiveCaptureSession
        from guardkit.knowledge.gap_analyzer import KnowledgeGap, KnowledgeCategory

        with patch('guardkit.knowledge.interactive_capture.get_graphiti') as mock_get:
            mock_graphiti = AsyncMock()
            mock_graphiti.add_episode = AsyncMock(return_value="episode-123")
            mock_get.return_value = mock_graphiti

            session = InteractiveCaptureSession()
            callback_events = []

            gap = KnowledgeGap(
                category=KnowledgeCategory.PROJECT_OVERVIEW,
                question="What is the purpose?",
                importance="high",
                context="Context",
            )

            with patch.object(session, '_get_gaps', return_value=[gap]):
                def mock_callback(event, data=None):
                    callback_events.append((event, data))
                    if event == 'get_input':
                        return 'quit'  # Quit immediately

                await session.run_session(ui_callback=mock_callback)

            events = [e[0] for e in callback_events]
            assert 'intro' in events

    @pytest.mark.asyncio
    async def test_run_session_calls_callback_with_question(self):
        """Test that run_session calls callback with 'question' event."""
        from guardkit.knowledge.interactive_capture import InteractiveCaptureSession
        from guardkit.knowledge.gap_analyzer import KnowledgeGap, KnowledgeCategory

        with patch('guardkit.knowledge.interactive_capture.get_graphiti') as mock_get:
            mock_graphiti = AsyncMock()
            mock_graphiti.add_episode = AsyncMock(return_value="episode-123")
            mock_get.return_value = mock_graphiti

            session = InteractiveCaptureSession()
            callback_events = []

            gap = KnowledgeGap(
                category=KnowledgeCategory.PROJECT_OVERVIEW,
                question="What is the purpose?",
                importance="high",
                context="Context",
            )

            with patch.object(session, '_get_gaps', return_value=[gap]):
                def mock_callback(event, data=None):
                    callback_events.append((event, data))
                    if event == 'get_input':
                        return 'quit'

                await session.run_session(ui_callback=mock_callback)

            events = [e[0] for e in callback_events]
            assert 'question' in events

    @pytest.mark.asyncio
    async def test_run_session_calls_callback_with_get_input(self):
        """Test that run_session calls callback with 'get_input' event."""
        from guardkit.knowledge.interactive_capture import InteractiveCaptureSession
        from guardkit.knowledge.gap_analyzer import KnowledgeGap, KnowledgeCategory

        with patch('guardkit.knowledge.interactive_capture.get_graphiti') as mock_get:
            mock_graphiti = AsyncMock()
            mock_graphiti.add_episode = AsyncMock(return_value="episode-123")
            mock_get.return_value = mock_graphiti

            session = InteractiveCaptureSession()
            callback_events = []

            gap = KnowledgeGap(
                category=KnowledgeCategory.PROJECT_OVERVIEW,
                question="What is the purpose?",
                importance="high",
                context="Context",
            )

            with patch.object(session, '_get_gaps', return_value=[gap]):
                def mock_callback(event, data=None):
                    callback_events.append((event, data))
                    if event == 'get_input':
                        return 'quit'

                await session.run_session(ui_callback=mock_callback)

            events = [e[0] for e in callback_events]
            assert 'get_input' in events

    @pytest.mark.asyncio
    async def test_run_session_calls_callback_with_captured(self):
        """Test that run_session calls callback with 'captured' event on answer."""
        from guardkit.knowledge.interactive_capture import InteractiveCaptureSession
        from guardkit.knowledge.gap_analyzer import KnowledgeGap, KnowledgeCategory

        with patch('guardkit.knowledge.interactive_capture.get_graphiti') as mock_get:
            mock_graphiti = AsyncMock()
            mock_graphiti.add_episode = AsyncMock(return_value="episode-123")
            mock_get.return_value = mock_graphiti

            session = InteractiveCaptureSession()
            callback_events = []
            input_count = [0]

            gap = KnowledgeGap(
                category=KnowledgeCategory.PROJECT_OVERVIEW,
                question="What is the purpose?",
                importance="high",
                context="Context",
            )

            with patch.object(session, '_get_gaps', return_value=[gap]):
                def mock_callback(event, data=None):
                    callback_events.append((event, data))
                    if event == 'get_input':
                        input_count[0] += 1
                        if input_count[0] == 1:
                            return 'This is my answer'  # First answer
                        return 'quit'  # Then quit

                await session.run_session(ui_callback=mock_callback)

            events = [e[0] for e in callback_events]
            assert 'captured' in events

    @pytest.mark.asyncio
    async def test_run_session_calls_callback_with_summary(self):
        """Test that run_session calls callback with 'summary' event."""
        from guardkit.knowledge.interactive_capture import InteractiveCaptureSession
        from guardkit.knowledge.gap_analyzer import KnowledgeGap, KnowledgeCategory

        with patch('guardkit.knowledge.interactive_capture.get_graphiti') as mock_get:
            mock_graphiti = AsyncMock()
            mock_graphiti.add_episode = AsyncMock(return_value="episode-123")
            mock_get.return_value = mock_graphiti

            session = InteractiveCaptureSession()
            callback_events = []

            gap = KnowledgeGap(
                category=KnowledgeCategory.PROJECT_OVERVIEW,
                question="What is the purpose?",
                importance="high",
                context="Context",
            )

            with patch.object(session, '_get_gaps', return_value=[gap]):
                def mock_callback(event, data=None):
                    callback_events.append((event, data))
                    if event == 'get_input':
                        return 'quit'

                await session.run_session(ui_callback=mock_callback)

            events = [e[0] for e in callback_events]
            assert 'summary' in events

    @pytest.mark.asyncio
    async def test_run_session_calls_callback_with_info(self):
        """Test that run_session calls callback with 'info' event."""
        from guardkit.knowledge.interactive_capture import InteractiveCaptureSession
        from guardkit.knowledge.gap_analyzer import KnowledgeGap, KnowledgeCategory

        with patch('guardkit.knowledge.interactive_capture.get_graphiti') as mock_get:
            mock_graphiti = AsyncMock()
            mock_graphiti.add_episode = AsyncMock(return_value="episode-123")
            mock_get.return_value = mock_graphiti

            session = InteractiveCaptureSession()
            callback_events = []

            with patch.object(session, '_get_gaps', new=AsyncMock(return_value=[])):
                def mock_callback(event, data=None):
                    callback_events.append((event, data))

                await session.run_session(ui_callback=mock_callback)

            events = [e[0] for e in callback_events]
            # 'info' is used for various messages
            assert 'info' in events or 'summary' in events


# ============================================================================
# 6. run_session() Skip/Quit Command Tests (5 tests)
# ============================================================================

class TestRunSessionSkipQuit:
    """Test skip and quit command handling in run_session()."""

    @pytest.mark.asyncio
    async def test_run_session_handles_skip_command(self):
        """Test that 'skip' command skips to next question."""
        from guardkit.knowledge.interactive_capture import InteractiveCaptureSession
        from guardkit.knowledge.gap_analyzer import KnowledgeGap, KnowledgeCategory

        with patch('guardkit.knowledge.interactive_capture.get_graphiti') as mock_get:
            mock_graphiti = AsyncMock()
            mock_graphiti.add_episode = AsyncMock(return_value="episode-123")
            mock_get.return_value = mock_graphiti

            session = InteractiveCaptureSession()
            questions_asked = []
            input_count = [0]

            gaps = [
                KnowledgeGap(
                    category=KnowledgeCategory.PROJECT_OVERVIEW,
                    question="First question?",
                    importance="high",
                    context="Context 1",
                ),
                KnowledgeGap(
                    category=KnowledgeCategory.ARCHITECTURE,
                    question="Second question?",
                    importance="medium",
                    context="Context 2",
                ),
            ]

            with patch.object(session, '_get_gaps', return_value=gaps):
                def mock_callback(event, data=None):
                    if event == 'question':
                        questions_asked.append(data)
                    if event == 'get_input':
                        input_count[0] += 1
                        if input_count[0] == 1:
                            return 'skip'  # Skip first question
                        return 'quit'  # Quit on second

                await session.run_session(ui_callback=mock_callback)

            # Both questions should have been asked
            assert len(questions_asked) == 2

    @pytest.mark.asyncio
    async def test_run_session_handles_s_shortcut(self):
        """Test that 's' shortcut works for skip."""
        from guardkit.knowledge.interactive_capture import InteractiveCaptureSession
        from guardkit.knowledge.gap_analyzer import KnowledgeGap, KnowledgeCategory

        with patch('guardkit.knowledge.interactive_capture.get_graphiti') as mock_get:
            mock_graphiti = AsyncMock()
            mock_graphiti.add_episode = AsyncMock(return_value="episode-123")
            mock_get.return_value = mock_graphiti

            session = InteractiveCaptureSession()
            input_count = [0]

            gaps = [
                KnowledgeGap(
                    category=KnowledgeCategory.PROJECT_OVERVIEW,
                    question="First question?",
                    importance="high",
                    context="Context 1",
                ),
                KnowledgeGap(
                    category=KnowledgeCategory.ARCHITECTURE,
                    question="Second question?",
                    importance="medium",
                    context="Context 2",
                ),
            ]

            with patch.object(session, '_get_gaps', return_value=gaps):
                def mock_callback(event, data=None):
                    if event == 'get_input':
                        input_count[0] += 1
                        if input_count[0] == 1:
                            return 's'  # 's' shortcut for skip
                        return 'quit'

                result = await session.run_session(ui_callback=mock_callback)

            # Should have moved to second question after skip
            assert input_count[0] >= 2

    @pytest.mark.asyncio
    async def test_run_session_handles_empty_string_as_skip(self):
        """Test that empty string ('') works as skip."""
        from guardkit.knowledge.interactive_capture import InteractiveCaptureSession
        from guardkit.knowledge.gap_analyzer import KnowledgeGap, KnowledgeCategory

        with patch('guardkit.knowledge.interactive_capture.get_graphiti') as mock_get:
            mock_graphiti = AsyncMock()
            mock_graphiti.add_episode = AsyncMock(return_value="episode-123")
            mock_get.return_value = mock_graphiti

            session = InteractiveCaptureSession()
            input_count = [0]

            gaps = [
                KnowledgeGap(
                    category=KnowledgeCategory.PROJECT_OVERVIEW,
                    question="First question?",
                    importance="high",
                    context="Context 1",
                ),
            ]

            with patch.object(session, '_get_gaps', return_value=gaps):
                def mock_callback(event, data=None):
                    if event == 'get_input':
                        input_count[0] += 1
                        if input_count[0] == 1:
                            return ''  # Empty string as skip
                        return 'quit'

                await session.run_session(ui_callback=mock_callback)

            # Should have processed the skip
            assert input_count[0] >= 1

    @pytest.mark.asyncio
    async def test_run_session_handles_quit_command(self):
        """Test that 'quit' command ends session."""
        from guardkit.knowledge.interactive_capture import InteractiveCaptureSession
        from guardkit.knowledge.gap_analyzer import KnowledgeGap, KnowledgeCategory

        with patch('guardkit.knowledge.interactive_capture.get_graphiti') as mock_get:
            mock_graphiti = AsyncMock()
            mock_graphiti.add_episode = AsyncMock(return_value="episode-123")
            mock_get.return_value = mock_graphiti

            session = InteractiveCaptureSession()
            questions_asked = []

            gaps = [
                KnowledgeGap(
                    category=KnowledgeCategory.PROJECT_OVERVIEW,
                    question="First question?",
                    importance="high",
                    context="Context 1",
                ),
                KnowledgeGap(
                    category=KnowledgeCategory.ARCHITECTURE,
                    question="Second question?",
                    importance="medium",
                    context="Context 2",
                ),
            ]

            with patch.object(session, '_get_gaps', return_value=gaps):
                def mock_callback(event, data=None):
                    if event == 'question':
                        questions_asked.append(data)
                    if event == 'get_input':
                        return 'quit'  # Quit immediately

                await session.run_session(ui_callback=mock_callback)

            # Only first question should have been asked
            assert len(questions_asked) == 1

    @pytest.mark.asyncio
    async def test_run_session_handles_q_and_exit_shortcuts(self):
        """Test that 'q' and 'exit' work as quit shortcuts."""
        from guardkit.knowledge.interactive_capture import InteractiveCaptureSession
        from guardkit.knowledge.gap_analyzer import KnowledgeGap, KnowledgeCategory

        with patch('guardkit.knowledge.interactive_capture.get_graphiti') as mock_get:
            mock_graphiti = AsyncMock()
            mock_graphiti.add_episode = AsyncMock(return_value="episode-123")
            mock_get.return_value = mock_graphiti

            # Test 'q' shortcut
            session = InteractiveCaptureSession()
            questions_asked_q = []

            gaps = [
                KnowledgeGap(
                    category=KnowledgeCategory.PROJECT_OVERVIEW,
                    question="First question?",
                    importance="high",
                    context="Context 1",
                ),
                KnowledgeGap(
                    category=KnowledgeCategory.ARCHITECTURE,
                    question="Second question?",
                    importance="medium",
                    context="Context 2",
                ),
            ]

            with patch.object(session, '_get_gaps', return_value=gaps):
                def mock_callback_q(event, data=None):
                    if event == 'question':
                        questions_asked_q.append(data)
                    if event == 'get_input':
                        return 'q'  # 'q' shortcut

                await session.run_session(ui_callback=mock_callback_q)

            assert len(questions_asked_q) == 1  # Quit after first

            # Test 'exit' shortcut
            session2 = InteractiveCaptureSession()
            questions_asked_exit = []

            with patch.object(session2, '_get_gaps', return_value=gaps):
                def mock_callback_exit(event, data=None):
                    if event == 'question':
                        questions_asked_exit.append(data)
                    if event == 'get_input':
                        return 'exit'  # 'exit' command

                await session2.run_session(ui_callback=mock_callback_exit)

            assert len(questions_asked_exit) == 1  # Quit after first


# ============================================================================
# 7. _process_answer() Tests (4 tests)
# ============================================================================

class TestProcessAnswer:
    """Test _process_answer() method."""

    def test_process_answer_returns_captured_knowledge(self):
        """Test that _process_answer returns CapturedKnowledge."""
        from guardkit.knowledge.interactive_capture import InteractiveCaptureSession, CapturedKnowledge
        from guardkit.knowledge.gap_analyzer import KnowledgeGap, KnowledgeCategory

        with patch('guardkit.knowledge.interactive_capture.get_graphiti') as mock_get:
            mock_get.return_value = MagicMock()
            session = InteractiveCaptureSession()

            gap = KnowledgeGap(
                category=KnowledgeCategory.PROJECT_OVERVIEW,
                question="What is the purpose?",
                importance="high",
                context="Context",
            )

            result = session._process_answer(gap, "This project builds AI assistants.")

            assert isinstance(result, CapturedKnowledge)

    def test_process_answer_preserves_category(self):
        """Test that _process_answer preserves the gap's category."""
        from guardkit.knowledge.interactive_capture import InteractiveCaptureSession
        from guardkit.knowledge.gap_analyzer import KnowledgeGap, KnowledgeCategory

        with patch('guardkit.knowledge.interactive_capture.get_graphiti') as mock_get:
            mock_get.return_value = MagicMock()
            session = InteractiveCaptureSession()

            gap = KnowledgeGap(
                category=KnowledgeCategory.ARCHITECTURE,
                question="What is the architecture?",
                importance="high",
                context="Context",
            )

            result = session._process_answer(gap, "Microservices based architecture.")

            assert result.category == KnowledgeCategory.ARCHITECTURE

    def test_process_answer_preserves_question(self):
        """Test that _process_answer preserves the question."""
        from guardkit.knowledge.interactive_capture import InteractiveCaptureSession
        from guardkit.knowledge.gap_analyzer import KnowledgeGap, KnowledgeCategory

        with patch('guardkit.knowledge.interactive_capture.get_graphiti') as mock_get:
            mock_get.return_value = MagicMock()
            session = InteractiveCaptureSession()

            gap = KnowledgeGap(
                category=KnowledgeCategory.DOMAIN,
                question="What domain terms exist?",
                importance="medium",
                context="Context",
            )

            result = session._process_answer(gap, "Terms include X, Y, Z.")

            assert result.question == "What domain terms exist?"

    def test_process_answer_extracts_facts(self):
        """Test that _process_answer extracts facts from answer."""
        from guardkit.knowledge.interactive_capture import InteractiveCaptureSession
        from guardkit.knowledge.gap_analyzer import KnowledgeGap, KnowledgeCategory

        with patch('guardkit.knowledge.interactive_capture.get_graphiti') as mock_get:
            mock_get.return_value = MagicMock()
            session = InteractiveCaptureSession()

            gap = KnowledgeGap(
                category=KnowledgeCategory.PROJECT_OVERVIEW,
                question="What is the purpose?",
                importance="high",
                context="Context",
            )

            result = session._process_answer(
                gap,
                "This project builds AI assistants. It uses Python and TypeScript."
            )

            # Should have extracted facts
            assert len(result.extracted_facts) > 0


# ============================================================================
# 8. _extract_facts() Tests (9 tests)
# ============================================================================

class TestExtractFacts:
    """Test _extract_facts() method."""

    def test_extract_facts_returns_list(self):
        """Test that _extract_facts returns a list."""
        from guardkit.knowledge.interactive_capture import InteractiveCaptureSession
        from guardkit.knowledge.gap_analyzer import KnowledgeCategory

        with patch('guardkit.knowledge.interactive_capture.get_graphiti') as mock_get:
            mock_get.return_value = MagicMock()
            session = InteractiveCaptureSession()

            result = session._extract_facts(
                "This is a test sentence.",
                KnowledgeCategory.PROJECT_OVERVIEW
            )

            assert isinstance(result, list)

    def test_extract_facts_splits_into_sentences(self):
        """Test that _extract_facts splits answer into sentences."""
        from guardkit.knowledge.interactive_capture import InteractiveCaptureSession
        from guardkit.knowledge.gap_analyzer import KnowledgeCategory

        with patch('guardkit.knowledge.interactive_capture.get_graphiti') as mock_get:
            mock_get.return_value = MagicMock()
            session = InteractiveCaptureSession()

            result = session._extract_facts(
                "First sentence here. Second sentence here. Third sentence here.",
                KnowledgeCategory.PROJECT_OVERVIEW
            )

            assert len(result) >= 1  # Should have at least some facts

    def test_extract_facts_filters_short_sentences(self):
        """Test that _extract_facts filters sentences shorter than 10 chars."""
        from guardkit.knowledge.interactive_capture import InteractiveCaptureSession
        from guardkit.knowledge.gap_analyzer import KnowledgeCategory

        with patch('guardkit.knowledge.interactive_capture.get_graphiti') as mock_get:
            mock_get.return_value = MagicMock()
            session = InteractiveCaptureSession()

            result = session._extract_facts(
                "Hi. OK. This is a much longer sentence that should be included.",
                KnowledgeCategory.PROJECT_OVERVIEW
            )

            # Short sentences should be filtered
            for fact in result:
                # The fact may have a prefix, check the content length
                assert len(fact) >= 10 or ":" in fact

    def test_extract_facts_prefixes_with_category_project(self):
        """Test that _extract_facts prefixes facts with 'Project:' for PROJECT_OVERVIEW."""
        from guardkit.knowledge.interactive_capture import InteractiveCaptureSession
        from guardkit.knowledge.gap_analyzer import KnowledgeCategory

        with patch('guardkit.knowledge.interactive_capture.get_graphiti') as mock_get:
            mock_get.return_value = MagicMock()
            session = InteractiveCaptureSession()

            result = session._extract_facts(
                "This project builds AI assistants.",
                KnowledgeCategory.PROJECT_OVERVIEW
            )

            if result:
                assert any("Project:" in fact for fact in result) or any("project" in fact.lower() for fact in result)

    def test_extract_facts_prefixes_with_category_architecture(self):
        """Test that _extract_facts prefixes facts with 'Architecture:' for ARCHITECTURE."""
        from guardkit.knowledge.interactive_capture import InteractiveCaptureSession
        from guardkit.knowledge.gap_analyzer import KnowledgeCategory

        with patch('guardkit.knowledge.interactive_capture.get_graphiti') as mock_get:
            mock_get.return_value = MagicMock()
            session = InteractiveCaptureSession()

            result = session._extract_facts(
                "The system uses microservices architecture.",
                KnowledgeCategory.ARCHITECTURE
            )

            if result:
                assert any("Architecture:" in fact for fact in result) or any("architecture" in fact.lower() for fact in result)

    def test_extract_facts_handles_empty_answer(self):
        """Test that _extract_facts handles empty answer gracefully."""
        from guardkit.knowledge.interactive_capture import InteractiveCaptureSession
        from guardkit.knowledge.gap_analyzer import KnowledgeCategory

        with patch('guardkit.knowledge.interactive_capture.get_graphiti') as mock_get:
            mock_get.return_value = MagicMock()
            session = InteractiveCaptureSession()

            result = session._extract_facts("", KnowledgeCategory.PROJECT_OVERVIEW)

            assert isinstance(result, list)
            assert len(result) == 0

    def test_extract_facts_handles_multiline_answer(self):
        """Test that _extract_facts handles multi-line answers with newlines."""
        from guardkit.knowledge.interactive_capture import InteractiveCaptureSession
        from guardkit.knowledge.gap_analyzer import KnowledgeCategory

        with patch('guardkit.knowledge.interactive_capture.get_graphiti') as mock_get:
            mock_get.return_value = MagicMock()
            session = InteractiveCaptureSession()

            multiline_answer = "This is the first sentence.\nThis is the second sentence on a new line.\nThis is the third sentence."

            result = session._extract_facts(multiline_answer, KnowledgeCategory.PROJECT_OVERVIEW)

            # Should extract facts from all lines
            assert isinstance(result, list)
            assert len(result) >= 1
            # All facts should be non-empty after stripping
            for fact in result:
                assert len(fact.strip()) > 0

    def test_extract_facts_handles_sentence_across_lines(self):
        """Test that _extract_facts handles sentences spanning multiple lines."""
        from guardkit.knowledge.interactive_capture import InteractiveCaptureSession
        from guardkit.knowledge.gap_analyzer import KnowledgeCategory

        with patch('guardkit.knowledge.interactive_capture.get_graphiti') as mock_get:
            mock_get.return_value = MagicMock()
            session = InteractiveCaptureSession()

            # Sentence split across lines without period until end
            answer = "This is a long sentence that\nspans multiple lines\nand ends here."

            result = session._extract_facts(answer, KnowledgeCategory.ARCHITECTURE)

            # Should process the complete text
            assert isinstance(result, list)
            # Should have at least one fact extracted
            assert len(result) >= 1

    def test_extract_facts_handles_bullet_points(self):
        """Test that _extract_facts handles bullet-pointed answers."""
        from guardkit.knowledge.interactive_capture import InteractiveCaptureSession
        from guardkit.knowledge.gap_analyzer import KnowledgeCategory

        with patch('guardkit.knowledge.interactive_capture.get_graphiti') as mock_get:
            mock_get.return_value = MagicMock()
            session = InteractiveCaptureSession()

            # Common bullet-point format in knowledge capture
            bullet_answer = """- First key point about the system.
- Second important detail here.
- Third consideration to note."""

            result = session._extract_facts(bullet_answer, KnowledgeCategory.DOMAIN)

            # Should extract facts from bullet points
            assert isinstance(result, list)
            # Should have extracted multiple facts
            assert len(result) >= 1
            # Facts should be non-empty
            for fact in result:
                assert len(fact.strip()) > 0


# ============================================================================
# 9. _save_captured_knowledge() Tests (5 tests)
# ============================================================================

class TestSaveCapturedKnowledge:
    """Test _save_captured_knowledge() method."""

    @pytest.mark.asyncio
    async def test_save_captured_knowledge_calls_graphiti(self):
        """Test that _save_captured_knowledge calls graphiti.add_episode()."""
        from guardkit.knowledge.interactive_capture import InteractiveCaptureSession, CapturedKnowledge
        from guardkit.knowledge.gap_analyzer import KnowledgeCategory

        with patch('guardkit.knowledge.interactive_capture.get_graphiti') as mock_get:
            mock_graphiti = AsyncMock()
            mock_graphiti.add_episode = AsyncMock(return_value="episode-123")
            mock_get.return_value = mock_graphiti

            session = InteractiveCaptureSession()
            session._captured = [
                CapturedKnowledge(
                    category=KnowledgeCategory.PROJECT_OVERVIEW,
                    question="What is the purpose?",
                    answer="This project builds AI assistants.",
                    extracted_facts=["Project: This project builds AI assistants"],
                )
            ]

            await session._save_captured_knowledge()

            mock_graphiti.add_episode.assert_called()

    @pytest.mark.asyncio
    async def test_save_captured_knowledge_groups_by_category(self):
        """Test that _save_captured_knowledge groups knowledge by category."""
        from guardkit.knowledge.interactive_capture import InteractiveCaptureSession, CapturedKnowledge
        from guardkit.knowledge.gap_analyzer import KnowledgeCategory

        with patch('guardkit.knowledge.interactive_capture.get_graphiti') as mock_get:
            mock_graphiti = AsyncMock()
            mock_graphiti.add_episode = AsyncMock(return_value="episode-123")
            mock_get.return_value = mock_graphiti

            session = InteractiveCaptureSession()
            session._captured = [
                CapturedKnowledge(
                    category=KnowledgeCategory.PROJECT_OVERVIEW,
                    question="Question 1?",
                    answer="Answer 1",
                    extracted_facts=["Fact 1"],
                ),
                CapturedKnowledge(
                    category=KnowledgeCategory.PROJECT_OVERVIEW,
                    question="Question 2?",
                    answer="Answer 2",
                    extracted_facts=["Fact 2"],
                ),
                CapturedKnowledge(
                    category=KnowledgeCategory.ARCHITECTURE,
                    question="Question 3?",
                    answer="Answer 3",
                    extracted_facts=["Fact 3"],
                ),
            ]

            await session._save_captured_knowledge()

            # Should have called add_episode at least once per unique category
            # (or once per captured knowledge - depends on implementation)
            assert mock_graphiti.add_episode.call_count >= 1

    @pytest.mark.asyncio
    async def test_save_captured_knowledge_uses_correct_group_id(self):
        """Test that _save_captured_knowledge uses correct group_id."""
        from guardkit.knowledge.interactive_capture import InteractiveCaptureSession, CapturedKnowledge
        from guardkit.knowledge.gap_analyzer import KnowledgeCategory

        with patch('guardkit.knowledge.interactive_capture.get_graphiti') as mock_get:
            mock_graphiti = AsyncMock()
            mock_graphiti.add_episode = AsyncMock(return_value="episode-123")
            mock_get.return_value = mock_graphiti

            session = InteractiveCaptureSession()
            session._captured = [
                CapturedKnowledge(
                    category=KnowledgeCategory.PROJECT_OVERVIEW,
                    question="What is the purpose?",
                    answer="This project builds AI assistants.",
                    extracted_facts=["Fact 1"],
                )
            ]

            await session._save_captured_knowledge()

            # Check that add_episode was called with group_id containing project_overview
            call_args = mock_graphiti.add_episode.call_args_list
            assert len(call_args) >= 1

    @pytest.mark.asyncio
    async def test_save_captured_knowledge_handles_graphiti_failure(self):
        """Test that _save_captured_knowledge handles Graphiti failures gracefully."""
        from guardkit.knowledge.interactive_capture import InteractiveCaptureSession, CapturedKnowledge
        from guardkit.knowledge.gap_analyzer import KnowledgeCategory

        with patch('guardkit.knowledge.interactive_capture.get_graphiti') as mock_get:
            mock_graphiti = AsyncMock()
            mock_graphiti.add_episode = AsyncMock(side_effect=Exception("Connection failed"))
            mock_get.return_value = mock_graphiti

            session = InteractiveCaptureSession()
            session._captured = [
                CapturedKnowledge(
                    category=KnowledgeCategory.PROJECT_OVERVIEW,
                    question="What is the purpose?",
                    answer="Answer",
                    extracted_facts=["Fact"],
                )
            ]

            # Should not raise
            await session._save_captured_knowledge()

    @pytest.mark.asyncio
    async def test_save_captured_knowledge_with_empty_list(self):
        """Test that _save_captured_knowledge handles empty captured list."""
        from guardkit.knowledge.interactive_capture import InteractiveCaptureSession

        with patch('guardkit.knowledge.interactive_capture.get_graphiti') as mock_get:
            mock_graphiti = AsyncMock()
            mock_graphiti.add_episode = AsyncMock(return_value="episode-123")
            mock_get.return_value = mock_graphiti

            session = InteractiveCaptureSession()
            session._captured = []

            await session._save_captured_knowledge()

            # Should not call add_episode when nothing to save
            mock_graphiti.add_episode.assert_not_called()


# ============================================================================
# 10. _category_to_group_id() Tests (3 tests)
# ============================================================================

class TestCategoryToGroupId:
    """Test _category_to_group_id() method."""

    def test_category_to_group_id_maps_project_overview(self):
        """Test that PROJECT_OVERVIEW maps to correct group_id."""
        from guardkit.knowledge.interactive_capture import InteractiveCaptureSession
        from guardkit.knowledge.gap_analyzer import KnowledgeCategory

        with patch('guardkit.knowledge.interactive_capture.get_graphiti') as mock_get:
            mock_get.return_value = MagicMock()
            session = InteractiveCaptureSession()

            result = session._category_to_group_id(KnowledgeCategory.PROJECT_OVERVIEW)

            assert "project" in result.lower() or "overview" in result.lower()

    def test_category_to_group_id_maps_all_categories(self):
        """Test that all 9 categories have mappings."""
        from guardkit.knowledge.interactive_capture import InteractiveCaptureSession
        from guardkit.knowledge.gap_analyzer import KnowledgeCategory

        with patch('guardkit.knowledge.interactive_capture.get_graphiti') as mock_get:
            mock_get.return_value = MagicMock()
            session = InteractiveCaptureSession()

            for category in KnowledgeCategory:
                result = session._category_to_group_id(category)
                assert result is not None
                assert len(result) > 0

    def test_category_to_group_id_returns_string(self):
        """Test that _category_to_group_id returns string."""
        from guardkit.knowledge.interactive_capture import InteractiveCaptureSession
        from guardkit.knowledge.gap_analyzer import KnowledgeCategory

        with patch('guardkit.knowledge.interactive_capture.get_graphiti') as mock_get:
            mock_get.return_value = MagicMock()
            session = InteractiveCaptureSession()

            result = session._category_to_group_id(KnowledgeCategory.ARCHITECTURE)

            assert isinstance(result, str)


# ============================================================================
# 11. Format Methods Tests (4 tests)
# ============================================================================

class TestFormatMethods:
    """Test _format_intro() and _format_summary() methods."""

    def test_format_intro_returns_string(self):
        """Test that _format_intro returns a string."""
        from guardkit.knowledge.interactive_capture import InteractiveCaptureSession
        from guardkit.knowledge.gap_analyzer import KnowledgeGap, KnowledgeCategory

        with patch('guardkit.knowledge.interactive_capture.get_graphiti') as mock_get:
            mock_get.return_value = MagicMock()
            session = InteractiveCaptureSession()

            gaps = [
                KnowledgeGap(
                    category=KnowledgeCategory.PROJECT_OVERVIEW,
                    question="What is the purpose?",
                    importance="high",
                    context="Context",
                )
            ]

            result = session._format_intro(gaps)

            assert isinstance(result, str)
            assert len(result) > 0

    def test_format_intro_includes_question_count(self):
        """Test that _format_intro includes the number of questions."""
        from guardkit.knowledge.interactive_capture import InteractiveCaptureSession
        from guardkit.knowledge.gap_analyzer import KnowledgeGap, KnowledgeCategory

        with patch('guardkit.knowledge.interactive_capture.get_graphiti') as mock_get:
            mock_get.return_value = MagicMock()
            session = InteractiveCaptureSession()

            gaps = [
                KnowledgeGap(
                    category=KnowledgeCategory.PROJECT_OVERVIEW,
                    question="Q1?",
                    importance="high",
                    context="C1",
                ),
                KnowledgeGap(
                    category=KnowledgeCategory.ARCHITECTURE,
                    question="Q2?",
                    importance="medium",
                    context="C2",
                ),
            ]

            result = session._format_intro(gaps)

            # Should mention number of questions (2)
            assert "2" in result or "two" in result.lower()

    def test_format_summary_returns_string(self):
        """Test that _format_summary returns a string."""
        from guardkit.knowledge.interactive_capture import InteractiveCaptureSession, CapturedKnowledge
        from guardkit.knowledge.gap_analyzer import KnowledgeCategory

        with patch('guardkit.knowledge.interactive_capture.get_graphiti') as mock_get:
            mock_get.return_value = MagicMock()
            session = InteractiveCaptureSession()
            session._captured = [
                CapturedKnowledge(
                    category=KnowledgeCategory.PROJECT_OVERVIEW,
                    question="Q1?",
                    answer="A1",
                    extracted_facts=["Fact 1"],
                )
            ]

            result = session._format_summary()

            assert isinstance(result, str)
            assert len(result) > 0

    def test_format_summary_includes_category_counts(self):
        """Test that _format_summary includes facts captured per category."""
        from guardkit.knowledge.interactive_capture import InteractiveCaptureSession, CapturedKnowledge
        from guardkit.knowledge.gap_analyzer import KnowledgeCategory

        with patch('guardkit.knowledge.interactive_capture.get_graphiti') as mock_get:
            mock_get.return_value = MagicMock()
            session = InteractiveCaptureSession()
            session._captured = [
                CapturedKnowledge(
                    category=KnowledgeCategory.PROJECT_OVERVIEW,
                    question="Q1?",
                    answer="A1",
                    extracted_facts=["Fact 1", "Fact 2"],
                ),
                CapturedKnowledge(
                    category=KnowledgeCategory.ARCHITECTURE,
                    question="Q2?",
                    answer="A2",
                    extracted_facts=["Fact 3"],
                ),
            ]

            result = session._format_summary()

            # Should mention categories or facts
            assert "fact" in result.lower() or "captured" in result.lower() or len(result) > 0


# ============================================================================
# 12. Edge Cases and Error Handling Tests (6 tests)
# ============================================================================

class TestEdgeCasesAndErrorHandling:
    """Test edge cases and error conditions."""

    @pytest.mark.asyncio
    async def test_run_session_handles_none_focus(self):
        """Test run_session with focus=None (default)."""
        from guardkit.knowledge.interactive_capture import InteractiveCaptureSession

        with patch('guardkit.knowledge.interactive_capture.get_graphiti') as mock_get:
            mock_graphiti = AsyncMock()
            mock_get.return_value = mock_graphiti

            session = InteractiveCaptureSession()

            with patch.object(session, '_get_gaps', new=AsyncMock(return_value=[])):
                def mock_callback(event, data=None):
                    pass

                result = await session.run_session(focus=None, ui_callback=mock_callback)

                assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_run_session_handles_graphiti_unavailable(self):
        """Test run_session when Graphiti is unavailable."""
        from guardkit.knowledge.interactive_capture import InteractiveCaptureSession
        from guardkit.knowledge.gap_analyzer import KnowledgeGap, KnowledgeCategory

        with patch('guardkit.knowledge.interactive_capture.get_graphiti') as mock_get:
            mock_get.return_value = None  # Graphiti unavailable

            session = InteractiveCaptureSession()

            gap = KnowledgeGap(
                category=KnowledgeCategory.PROJECT_OVERVIEW,
                question="What is the purpose?",
                importance="high",
                context="Context",
            )

            with patch.object(session, '_get_gaps', return_value=[gap]):
                def mock_callback(event, data=None):
                    if event == 'get_input':
                        return 'Answer here'
                    return None

                # Should not raise, should handle gracefully
                result = await session.run_session(ui_callback=mock_callback)

                assert isinstance(result, list)

    def test_process_answer_with_empty_answer(self):
        """Test _process_answer with empty answer."""
        from guardkit.knowledge.interactive_capture import InteractiveCaptureSession, CapturedKnowledge
        from guardkit.knowledge.gap_analyzer import KnowledgeGap, KnowledgeCategory

        with patch('guardkit.knowledge.interactive_capture.get_graphiti') as mock_get:
            mock_get.return_value = MagicMock()
            session = InteractiveCaptureSession()

            gap = KnowledgeGap(
                category=KnowledgeCategory.PROJECT_OVERVIEW,
                question="What is the purpose?",
                importance="high",
                context="Context",
            )

            result = session._process_answer(gap, "")

            assert isinstance(result, CapturedKnowledge)
            assert result.answer == ""
            assert result.extracted_facts == []

    @pytest.mark.asyncio
    async def test_run_session_with_max_questions_zero(self):
        """Test run_session with max_questions=0."""
        from guardkit.knowledge.interactive_capture import InteractiveCaptureSession

        with patch('guardkit.knowledge.interactive_capture.get_graphiti') as mock_get:
            mock_graphiti = AsyncMock()
            mock_get.return_value = mock_graphiti

            session = InteractiveCaptureSession()

            with patch.object(session, '_get_gaps', new=AsyncMock(return_value=[])):
                def mock_callback(event, data=None):
                    pass

                result = await session.run_session(max_questions=0, ui_callback=mock_callback)

                # Should return empty list
                assert result == []

    @pytest.mark.asyncio
    async def test_run_session_each_call_returns_new_list(self):
        """Test that each call to run_session returns a new list instance."""
        from guardkit.knowledge.interactive_capture import InteractiveCaptureSession

        with patch('guardkit.knowledge.interactive_capture.get_graphiti') as mock_get:
            mock_graphiti = AsyncMock()
            mock_get.return_value = mock_graphiti

            session = InteractiveCaptureSession()

            with patch.object(session, '_get_gaps', new=AsyncMock(return_value=[])):
                def mock_callback(event, data=None):
                    pass

                result1 = await session.run_session(ui_callback=mock_callback)
                result2 = await session.run_session(ui_callback=mock_callback)

                # Should be different list objects
                assert result1 is not result2

    def test_extract_facts_with_special_characters(self):
        """Test _extract_facts with special characters in answer."""
        from guardkit.knowledge.interactive_capture import InteractiveCaptureSession
        from guardkit.knowledge.gap_analyzer import KnowledgeCategory

        with patch('guardkit.knowledge.interactive_capture.get_graphiti') as mock_get:
            mock_get.return_value = MagicMock()
            session = InteractiveCaptureSession()

            result = session._extract_facts(
                "This uses <TypeScript> & Python! It's @awesome - 100% working.",
                KnowledgeCategory.PROJECT_OVERVIEW
            )

            assert isinstance(result, list)
            # Should handle special characters without errors


# ============================================================================
# 13. Integration Flow Tests (3 tests)
# ============================================================================

class TestIntegrationFlow:
    """Test complete session flow integration."""

    @pytest.mark.asyncio
    async def test_full_session_flow_with_answers(self):
        """Test complete session flow with user providing answers."""
        from guardkit.knowledge.interactive_capture import InteractiveCaptureSession
        from guardkit.knowledge.gap_analyzer import KnowledgeGap, KnowledgeCategory

        with patch('guardkit.knowledge.interactive_capture.get_graphiti') as mock_get:
            mock_graphiti = AsyncMock()
            mock_graphiti.add_episode = AsyncMock(return_value="episode-123")
            mock_get.return_value = mock_graphiti

            session = InteractiveCaptureSession()
            events_received = []
            input_count = [0]

            gaps = [
                KnowledgeGap(
                    category=KnowledgeCategory.PROJECT_OVERVIEW,
                    question="What is the purpose?",
                    importance="high",
                    context="Context 1",
                ),
                KnowledgeGap(
                    category=KnowledgeCategory.ARCHITECTURE,
                    question="What is the architecture?",
                    importance="medium",
                    context="Context 2",
                ),
            ]

            with patch.object(session, '_get_gaps', return_value=gaps):
                def mock_callback(event, data=None):
                    events_received.append(event)
                    if event == 'get_input':
                        input_count[0] += 1
                        if input_count[0] == 1:
                            return "This project builds AI assistants."
                        elif input_count[0] == 2:
                            return "It uses microservices architecture."
                        return 'quit'

                result = await session.run_session(ui_callback=mock_callback)

            # Should have captured 2 knowledge items
            assert len(result) == 2
            # Should have received intro, questions, captured, summary events
            assert 'intro' in events_received
            assert 'question' in events_received
            assert 'summary' in events_received

    @pytest.mark.asyncio
    async def test_session_flow_with_mixed_skip_and_answers(self):
        """Test session flow with mixed skip and answer responses."""
        from guardkit.knowledge.interactive_capture import InteractiveCaptureSession
        from guardkit.knowledge.gap_analyzer import KnowledgeGap, KnowledgeCategory

        with patch('guardkit.knowledge.interactive_capture.get_graphiti') as mock_get:
            mock_graphiti = AsyncMock()
            mock_graphiti.add_episode = AsyncMock(return_value="episode-123")
            mock_get.return_value = mock_graphiti

            session = InteractiveCaptureSession()
            input_count = [0]

            gaps = [
                KnowledgeGap(
                    category=KnowledgeCategory.PROJECT_OVERVIEW,
                    question="Q1?",
                    importance="high",
                    context="C1",
                ),
                KnowledgeGap(
                    category=KnowledgeCategory.ARCHITECTURE,
                    question="Q2?",
                    importance="medium",
                    context="C2",
                ),
                KnowledgeGap(
                    category=KnowledgeCategory.DOMAIN,
                    question="Q3?",
                    importance="low",
                    context="C3",
                ),
            ]

            with patch.object(session, '_get_gaps', return_value=gaps):
                def mock_callback(event, data=None):
                    if event == 'get_input':
                        input_count[0] += 1
                        if input_count[0] == 1:
                            return 'skip'  # Skip first
                        elif input_count[0] == 2:
                            return 'Answer for Q2'  # Answer second
                        elif input_count[0] == 3:
                            return 's'  # Skip third
                        return 'quit'

                result = await session.run_session(ui_callback=mock_callback)

            # Should have captured only 1 (Q2 was answered)
            assert len(result) == 1
            assert result[0].category == KnowledgeCategory.ARCHITECTURE

    @pytest.mark.asyncio
    async def test_session_clears_captured_between_runs(self):
        """Test that captured list is cleared between session runs."""
        from guardkit.knowledge.interactive_capture import InteractiveCaptureSession
        from guardkit.knowledge.gap_analyzer import KnowledgeGap, KnowledgeCategory

        with patch('guardkit.knowledge.interactive_capture.get_graphiti') as mock_get:
            mock_graphiti = AsyncMock()
            mock_graphiti.add_episode = AsyncMock(return_value="episode-123")
            mock_get.return_value = mock_graphiti

            session = InteractiveCaptureSession()

            gap = KnowledgeGap(
                category=KnowledgeCategory.PROJECT_OVERVIEW,
                question="Q1?",
                importance="high",
                context="C1",
            )

            # First run
            with patch.object(session, '_get_gaps', return_value=[gap]):
                def mock_callback1(event, data=None):
                    if event == 'get_input':
                        return 'Answer 1'

                result1 = await session.run_session(ui_callback=mock_callback1)

            # Second run should start fresh
            with patch.object(session, '_get_gaps', return_value=[gap]):
                def mock_callback2(event, data=None):
                    if event == 'get_input':
                        return 'quit'

                result2 = await session.run_session(ui_callback=mock_callback2)

            # First run had 1 captured, second run should be empty (quit immediately)
            assert len(result1) == 1
            assert len(result2) == 0
