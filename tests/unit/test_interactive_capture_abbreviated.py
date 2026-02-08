"""
Tests for InteractiveCaptureSession.run_abbreviated() implementation.

Verifies Q&A loop, skip/quit handling, Graphiti storage, graceful degradation,
category mapping, fact extraction, and UI callback interaction.

Coverage Target: >=85%
Test Count: 14 tests
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from guardkit.knowledge.interactive_capture import (
    InteractiveCaptureSession,
    CapturedKnowledge,
)
from guardkit.knowledge.gap_analyzer import KnowledgeCategory


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def session():
    """Create an InteractiveCaptureSession with mocked Graphiti."""
    with patch("guardkit.knowledge.interactive_capture.get_graphiti") as mock_get:
        mock_get.return_value = None  # Default: Graphiti unavailable
        sess = InteractiveCaptureSession()
        yield sess


@pytest.fixture
def session_with_graphiti():
    """Create session with a mock Graphiti client."""
    mock_client = MagicMock()
    mock_client.add_episode = AsyncMock(return_value="episode-uuid")

    with patch("guardkit.knowledge.interactive_capture.get_graphiti") as mock_get:
        mock_get.return_value = mock_client
        sess = InteractiveCaptureSession()
        yield sess, mock_client


def make_callback(answers):
    """Create a ui_callback that returns answers in sequence.

    Args:
        answers: List of answer strings to return for each get_input call.

    Returns:
        Callable that tracks question events and returns answers.
    """
    state = {"idx": 0, "questions": [], "captured": []}

    def callback(event, data=None):
        if event == "question":
            state["questions"].append(data)
        elif event == "get_input":
            if state["idx"] < len(answers):
                ans = answers[state["idx"]]
                state["idx"] += 1
                return ans
            return ""
        elif event == "captured":
            state["captured"].append(data)
        elif event == "summary":
            state["summary"] = data

    callback.state = state
    return callback


# ============================================================================
# Q&A Loop Tests
# ============================================================================


class TestQALoop:
    """Test the Q&A loop iterates through all questions."""

    @pytest.mark.asyncio
    async def test_iterates_all_questions(self, session):
        """Verify all questions are presented to the callback."""
        questions = ["Q1?", "Q2?", "Q3?"]
        cb = make_callback(["Answer one here", "Answer two here", "Answer three here"])

        result = await session.run_abbreviated(
            questions=questions, ui_callback=cb
        )

        assert result["questions_asked"] == 3
        assert result["answers_captured"] == 3
        assert len(cb.state["questions"]) == 3

    @pytest.mark.asyncio
    async def test_question_data_includes_number_and_total(self, session):
        """Verify question events include number and total."""
        cb = make_callback(["My answer text"])

        await session.run_abbreviated(
            questions=["Only question?"], ui_callback=cb
        )

        q_data = cb.state["questions"][0]
        assert q_data["number"] == 1
        assert q_data["total"] == 1
        assert q_data["question"] == "Only question?"

    @pytest.mark.asyncio
    async def test_question_data_includes_review_mode(self, session):
        """Verify question events include the review mode."""
        cb = make_callback(["My answer text"])

        await session.run_abbreviated(
            questions=["Q1?"],
            task_context={"review_mode": "security"},
            ui_callback=cb,
        )

        assert cb.state["questions"][0]["review_mode"] == "security"

    @pytest.mark.asyncio
    async def test_no_callback_skips_all(self, session):
        """Verify no callback means no answers captured (empty string → skip)."""
        result = await session.run_abbreviated(
            questions=["Q1?", "Q2?"],
            ui_callback=None,
        )

        assert result["questions_asked"] == 2
        assert result["answers_captured"] == 0

    @pytest.mark.asyncio
    async def test_captured_event_fired(self, session):
        """Verify 'captured' event is fired for each answered question."""
        cb = make_callback(["Answer one here", "Answer two here"])

        await session.run_abbreviated(
            questions=["Q1?", "Q2?"],
            task_context={"review_mode": "architectural"},
            ui_callback=cb,
        )

        assert len(cb.state["captured"]) == 2
        assert cb.state["captured"][0]["question"] == "Q1?"
        assert "facts_count" in cb.state["captured"][0]


# ============================================================================
# Skip/Quit Handling Tests
# ============================================================================


class TestSkipQuitHandling:
    """Test skip and quit command handling."""

    @pytest.mark.asyncio
    async def test_skip_command(self, session):
        """Verify 'skip' skips the question."""
        cb = make_callback(["Answer one here", "skip", "Answer three here"])

        result = await session.run_abbreviated(
            questions=["Q1?", "Q2?", "Q3?"], ui_callback=cb
        )

        assert result["answers_captured"] == 2
        items = result["captured_items"]
        assert items[0]["question"] == "Q1?"
        assert items[1]["question"] == "Q3?"

    @pytest.mark.asyncio
    async def test_s_shortcut(self, session):
        """Verify 's' shortcut skips the question."""
        cb = make_callback(["s", "Answer two here"])

        result = await session.run_abbreviated(
            questions=["Q1?", "Q2?"], ui_callback=cb
        )

        assert result["answers_captured"] == 1
        assert result["captured_items"][0]["question"] == "Q2?"

    @pytest.mark.asyncio
    async def test_empty_answer_skips(self, session):
        """Verify empty answer skips the question."""
        cb = make_callback(["", "Answer two here"])

        result = await session.run_abbreviated(
            questions=["Q1?", "Q2?"], ui_callback=cb
        )

        assert result["answers_captured"] == 1

    @pytest.mark.asyncio
    async def test_quit_command(self, session):
        """Verify 'quit' stops the session."""
        cb = make_callback(["Answer one here", "quit", "Should not reach"])

        result = await session.run_abbreviated(
            questions=["Q1?", "Q2?", "Q3?"], ui_callback=cb
        )

        assert result["answers_captured"] == 1
        assert result["captured_items"][0]["question"] == "Q1?"

    @pytest.mark.asyncio
    async def test_q_shortcut(self, session):
        """Verify 'q' shortcut stops the session."""
        cb = make_callback(["q"])

        result = await session.run_abbreviated(
            questions=["Q1?", "Q2?"], ui_callback=cb
        )

        assert result["answers_captured"] == 0

    @pytest.mark.asyncio
    async def test_exit_command(self, session):
        """Verify 'exit' stops the session."""
        cb = make_callback(["exit"])

        result = await session.run_abbreviated(
            questions=["Q1?"], ui_callback=cb
        )

        assert result["answers_captured"] == 0


# ============================================================================
# Category Mapping Tests
# ============================================================================


class TestCategoryMapping:
    """Test review mode to KnowledgeCategory mapping."""

    @pytest.mark.asyncio
    async def test_architectural_maps_to_architecture(self, session):
        cb = make_callback(["Architecture uses microservices pattern"])

        result = await session.run_abbreviated(
            questions=["Q?"],
            task_context={"review_mode": "architectural"},
            ui_callback=cb,
        )

        assert result["captured_items"][0]["category"] == "architecture"

    @pytest.mark.asyncio
    async def test_security_maps_to_constraints(self, session):
        cb = make_callback(["SQL injection risk found"])

        result = await session.run_abbreviated(
            questions=["Q?"],
            task_context={"review_mode": "security"},
            ui_callback=cb,
        )

        assert result["captured_items"][0]["category"] == "constraints"

    @pytest.mark.asyncio
    async def test_decision_maps_to_decisions(self, session):
        cb = make_callback(["Chose JWT over sessions"])

        result = await session.run_abbreviated(
            questions=["Q?"],
            task_context={"review_mode": "decision"},
            ui_callback=cb,
        )

        assert result["captured_items"][0]["category"] == "decisions"

    @pytest.mark.asyncio
    async def test_unknown_mode_defaults_to_domain(self, session):
        cb = make_callback(["Some answer text here"])

        result = await session.run_abbreviated(
            questions=["Q?"],
            task_context={"review_mode": "unknown-mode"},
            ui_callback=cb,
        )

        assert result["captured_items"][0]["category"] == "domain"

    @pytest.mark.asyncio
    async def test_no_review_mode_defaults_to_general(self, session):
        cb = make_callback(["Some answer text here"])

        result = await session.run_abbreviated(
            questions=["Q?"],
            ui_callback=cb,
        )

        assert result["review_mode"] == "general"
        assert result["captured_items"][0]["category"] == "domain"


# ============================================================================
# Fact Extraction Tests
# ============================================================================


class TestFactExtraction:
    """Test fact extraction from answers."""

    @pytest.mark.asyncio
    async def test_extracts_facts_from_sentences(self, session):
        """Verify facts are extracted from multi-sentence answers."""
        cb = make_callback([
            "Authentication uses JWT tokens. "
            "Tokens expire after one hour. "
            "Refresh tokens are rotated on each use."
        ])

        result = await session.run_abbreviated(
            questions=["How does auth work?"],
            task_context={"review_mode": "architectural"},
            ui_callback=cb,
        )

        facts = result["captured_items"][0]["facts"]
        assert len(facts) == 3
        assert all("Architecture:" in f for f in facts)

    @pytest.mark.asyncio
    async def test_short_sentences_filtered(self, session):
        """Verify sentences shorter than minimum are filtered out."""
        cb = make_callback(["Yes. It works well and is fully tested."])

        result = await session.run_abbreviated(
            questions=["Q?"],
            task_context={"review_mode": "architectural"},
            ui_callback=cb,
        )

        facts = result["captured_items"][0]["facts"]
        # "Yes" is too short (< 10 chars), should be filtered
        assert not any("Yes" in f and len(f) < 15 for f in facts)


# ============================================================================
# Graphiti Storage Tests
# ============================================================================


class TestGraphitiStorage:
    """Test Graphiti storage integration."""

    @pytest.mark.asyncio
    async def test_stores_to_graphiti(self, session_with_graphiti):
        """Verify captured knowledge is stored to Graphiti."""
        sess, mock_client = session_with_graphiti
        cb = make_callback(["Architecture uses clean architecture pattern"])

        await sess.run_abbreviated(
            questions=["What patterns?"],
            task_context={"review_mode": "architectural"},
            ui_callback=cb,
        )

        assert mock_client.add_episode.called
        call_kwargs = mock_client.add_episode.call_args
        episode_body = call_kwargs.kwargs.get(
            "episode_body", call_kwargs.args[1] if len(call_kwargs.args) > 1 else ""
        )
        assert "captured_knowledge" in episode_body
        assert "QA Pairs:" in episode_body

    @pytest.mark.asyncio
    async def test_graceful_degradation_no_graphiti(self, session):
        """Verify capture works locally when Graphiti is unavailable."""
        cb = make_callback(["Answer that should be captured locally"])

        result = await session.run_abbreviated(
            questions=["Q?"],
            ui_callback=cb,
        )

        # Should still return captured items even without Graphiti
        assert result["answers_captured"] == 1
        assert len(result["captured_items"]) == 1
        assert result["captured_items"][0]["answer"] == "Answer that should be captured locally"


# ============================================================================
# Result Structure Tests
# ============================================================================


class TestResultStructure:
    """Test the returned result dictionary structure."""

    @pytest.mark.asyncio
    async def test_result_has_required_keys(self, session):
        """Verify result dict has all required keys."""
        cb = make_callback(["Test answer text"])

        result = await session.run_abbreviated(
            questions=["Q?"],
            task_context={"task_id": "TASK-001", "review_mode": "architectural"},
            ui_callback=cb,
        )

        assert "captured_items" in result
        assert "task_id" in result
        assert "review_mode" in result
        assert "questions_asked" in result
        assert "answers_captured" in result

    @pytest.mark.asyncio
    async def test_result_preserves_task_id(self, session):
        """Verify task_id from context is preserved in result."""
        cb = make_callback(["Test answer text"])

        result = await session.run_abbreviated(
            questions=["Q?"],
            task_context={"task_id": "TASK-XYZ", "review_mode": "decision"},
            ui_callback=cb,
        )

        assert result["task_id"] == "TASK-XYZ"

    @pytest.mark.asyncio
    async def test_captured_item_structure(self, session):
        """Verify each captured item has question, answer, category, facts."""
        cb = make_callback(["This is my detailed answer"])

        result = await session.run_abbreviated(
            questions=["What happened?"],
            task_context={"review_mode": "architectural"},
            ui_callback=cb,
        )

        item = result["captured_items"][0]
        assert "question" in item
        assert "answer" in item
        assert "category" in item
        assert "facts" in item
        assert item["question"] == "What happened?"
        assert item["answer"] == "This is my detailed answer"

    @pytest.mark.asyncio
    async def test_clears_captured_on_new_session(self, session):
        """Verify _captured list is cleared at start of each run."""
        cb = make_callback(["First run answer"])

        await session.run_abbreviated(
            questions=["Q?"], ui_callback=cb
        )

        # Run again
        cb2 = make_callback(["Second run answer"])
        result = await session.run_abbreviated(
            questions=["Q?"], ui_callback=cb2
        )

        # Should only have items from second run
        assert result["answers_captured"] == 1
        assert result["captured_items"][0]["answer"] == "Second run answer"
        assert len(session.captured) == 1


# ============================================================================
# _process_answer_from_text Tests
# ============================================================================


class TestProcessAnswerFromText:
    """Test the _process_answer_from_text helper method."""

    def test_returns_captured_knowledge(self, session):
        """Verify returns CapturedKnowledge dataclass."""
        result = session._process_answer_from_text(
            "What patterns?", "Uses repository pattern", "architectural"
        )

        assert isinstance(result, CapturedKnowledge)
        assert result.question == "What patterns?"
        assert result.answer == "Uses repository pattern"
        assert result.category == KnowledgeCategory.ARCHITECTURE
        assert result.confidence == 0.8

    def test_code_quality_maps_to_domain(self, session):
        result = session._process_answer_from_text(
            "Q?", "Some quality answer", "code-quality"
        )
        assert result.category == KnowledgeCategory.DOMAIN

    def test_technical_debt_maps_to_domain(self, session):
        result = session._process_answer_from_text(
            "Q?", "Some debt answer", "technical-debt"
        )
        assert result.category == KnowledgeCategory.DOMAIN

    def test_extracts_facts(self, session):
        result = session._process_answer_from_text(
            "Q?",
            "Authentication is critical. Sessions must be validated.",
            "security",
        )
        assert len(result.extracted_facts) == 2
        assert all("Constraint:" in f for f in result.extracted_facts)
