"""
Comprehensive tests for /task-review --capture-knowledge integration.

These tests verify that knowledge capture can be triggered after task review
completion, with context-specific questions generated from review findings.

Test Coverage:
- Flag parsing and defaults
- Capture session triggering
- Context-specific question generation
- Abbreviated session behavior
- Task context linking
- Review mode compatibility
- Integration class methods

Status: RED phase (tests written before implementation)
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, call
from pathlib import Path

# Module under test
from guardkit.knowledge.review_knowledge_capture import (
    ReviewKnowledgeCapture,
    ReviewCaptureConfig,
    format_review_for_graphiti,
    generate_review_questions,
    run_review_capture
)
from guardkit.knowledge.interactive_capture import InteractiveCaptureSession
from guardkit.knowledge.gap_analyzer import KnowledgeGap, KnowledgeCategory


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def mock_task_context():
    """Mock task context with review metadata."""
    return {
        'task_id': 'TASK-TEST-001',
        'title': 'Review authentication architecture',
        'task_type': 'review',
        'review_mode': 'architectural',
        'stack': ['python', 'fastapi']
    }


@pytest.fixture
def mock_review_findings():
    """Mock review findings from architectural review."""
    return {
        'mode': 'architectural',
        'findings': [
            {
                'category': 'SOLID_VIOLATION',
                'severity': 'high',
                'description': 'Authentication service violates Single Responsibility Principle'
            },
            {
                'category': 'DRY_VIOLATION',
                'severity': 'medium',
                'description': 'Token validation duplicated across 3 modules'
            }
        ],
        'score': 65,
        'recommendations': [
            'Split authentication service into smaller components',
            'Create shared token validation utility'
        ]
    }


@pytest.fixture
def mock_capture_session():
    """Mock InteractiveCaptureSession for testing."""
    session = Mock(spec=InteractiveCaptureSession)
    session.run_abbreviated = AsyncMock(return_value={
        'captured_items': [
            {
                'question': 'What did you learn about architectural review from this review?',
                'answer': 'Authentication services should follow SRP strictly',
                'category': 'ARCHITECTURAL_PATTERN'
            }
        ],
        'task_id': 'TASK-TEST-001',
        'review_mode': 'architectural'
    })
    return session


# ============================================================================
# Test 1: Flag Parsing
# ============================================================================

class TestFlagParsing:
    """Test command-line flag parsing for --capture-knowledge."""

    def test_capture_knowledge_flag_parsing(self):
        """Verify --capture-knowledge flag is recognized and parsed correctly."""
        # This would be called by the CLI argument parser
        config = ReviewCaptureConfig.from_args(['--capture-knowledge'])

        assert config.capture_knowledge is True
        assert config.enabled is True

    def test_capture_knowledge_default_false(self):
        """Verify --capture-knowledge flag defaults to False when not provided."""
        config = ReviewCaptureConfig.from_args([])

        assert config.capture_knowledge is False
        assert config.enabled is False

    def test_capture_knowledge_short_flag(self):
        """Verify short flag -ck also works."""
        config = ReviewCaptureConfig.from_args(['-ck'])

        assert config.capture_knowledge is True


# ============================================================================
# Test 2: Capture Session Triggering
# ============================================================================

class TestCaptureSessionTriggering:
    """Test that capture session is triggered correctly based on flag."""

    @pytest.mark.asyncio
    async def test_capture_knowledge_triggers_session(
        self,
        mock_task_context,
        mock_review_findings,
        mock_capture_session
    ):
        """Verify capture_knowledge=True triggers capture session after review."""
        with patch('guardkit.knowledge.review_knowledge_capture.InteractiveCaptureSession',
                   return_value=mock_capture_session):

            result = await run_review_capture(
                task_context=mock_task_context,
                review_findings=mock_review_findings,
                capture_knowledge=True
            )

            # Verify capture session was created and run
            assert mock_capture_session.run_abbreviated.called
            assert result['capture_executed'] is True

    @pytest.mark.asyncio
    async def test_capture_knowledge_skipped_when_false(
        self,
        mock_task_context,
        mock_review_findings,
        mock_capture_session
    ):
        """Verify capture_knowledge=False skips capture session."""
        with patch('guardkit.knowledge.review_knowledge_capture.InteractiveCaptureSession',
                   return_value=mock_capture_session):

            result = await run_review_capture(
                task_context=mock_task_context,
                review_findings=mock_review_findings,
                capture_knowledge=False
            )

            # Verify capture session was NOT run
            assert not mock_capture_session.run_abbreviated.called
            assert result['capture_executed'] is False


# ============================================================================
# Test 3: Context-Specific Question Generation
# ============================================================================

class TestContextSpecificQuestions:
    """Test generation of context-specific questions from review findings."""

    def test_review_context_questions_generated(self, mock_review_findings, mock_task_context):
        """Verify questions are generated from review findings."""
        questions = generate_review_questions(
            review_findings=mock_review_findings,
            task_context=mock_task_context
        )

        assert len(questions) > 0
        assert isinstance(questions, list)
        assert all(isinstance(q, str) for q in questions)

    def test_questions_include_task_type(self, mock_review_findings, mock_task_context):
        """Verify questions include the task type context."""
        questions = generate_review_questions(
            review_findings=mock_review_findings,
            task_context=mock_task_context
        )

        # At least one question should mention "review" or the task type
        task_type_mentioned = any(
            'review' in q.lower() or mock_task_context['task_type'] in q.lower()
            for q in questions
        )
        assert task_type_mentioned, "Questions should reference task type"

    def test_questions_include_review_mode(self, mock_review_findings, mock_task_context):
        """Verify questions include the review mode (architectural, code-quality, etc)."""
        questions = generate_review_questions(
            review_findings=mock_review_findings,
            task_context=mock_task_context
        )

        # At least one question should mention the review mode
        review_mode = mock_review_findings['mode']
        mode_mentioned = any(review_mode in q.lower() for q in questions)

        assert mode_mentioned, f"Questions should reference review mode: {review_mode}"

    def test_questions_reference_specific_findings(self, mock_review_findings, mock_task_context):
        """Verify questions reference specific findings from the review."""
        questions = generate_review_questions(
            review_findings=mock_review_findings,
            task_context=mock_task_context
        )

        # Should have questions about SOLID violations, DRY violations, etc.
        findings_categories = [f['category'] for f in mock_review_findings['findings']]

        # At least one question should be about findings
        assert len(questions) >= 1
        # Could check for keywords like 'violation', 'recommendation', etc.
        finding_keywords = any(
            keyword in ' '.join(questions).lower()
            for keyword in ['violation', 'recommendation', 'finding', 'issue']
        )
        assert finding_keywords, "Questions should reference review findings"


# ============================================================================
# Test 4: Abbreviated Session Behavior
# ============================================================================

class TestAbbreviatedSession:
    """Test abbreviated capture session behavior (3-5 questions max)."""

    @pytest.mark.asyncio
    async def test_abbreviated_session_max_questions(
        self,
        mock_task_context,
        mock_review_findings
    ):
        """Verify abbreviated session is limited to 3-5 questions."""
        questions = generate_review_questions(
            review_findings=mock_review_findings,
            task_context=mock_task_context
        )

        assert 3 <= len(questions) <= 5, \
            f"Abbreviated session should have 3-5 questions, got {len(questions)}"

    @pytest.mark.asyncio
    async def test_abbreviated_session_accepts_custom_questions(
        self,
        mock_capture_session
    ):
        """Verify abbreviated session can accept custom questions."""
        custom_questions = [
            "What architectural patterns were identified?",
            "Were there any security concerns?",
            "What would you do differently next time?"
        ]

        with patch('guardkit.knowledge.review_knowledge_capture.InteractiveCaptureSession',
                   return_value=mock_capture_session):

            capture = ReviewKnowledgeCapture(
                task_context={'task_id': 'TEST-001'},
                review_findings={'mode': 'architectural'}
            )

            await capture.run_abbreviated_capture(custom_questions=custom_questions)

            # Verify custom questions were passed to session
            mock_capture_session.run_abbreviated.assert_called_once()
            call_args = mock_capture_session.run_abbreviated.call_args

            # The questions parameter should match our custom questions
            assert call_args is not None
            assert 'questions' in call_args.kwargs or len(call_args.args) > 0


# ============================================================================
# Test 5: Task Context Linking
# ============================================================================

class TestTaskContextLinking:
    """Test that captured knowledge is properly linked to task context."""

    @pytest.mark.asyncio
    async def test_captured_knowledge_linked_to_task(
        self,
        mock_task_context,
        mock_review_findings,
        mock_capture_session
    ):
        """Verify captured knowledge includes task_id and context."""
        with patch('guardkit.knowledge.review_knowledge_capture.InteractiveCaptureSession',
                   return_value=mock_capture_session):

            result = await run_review_capture(
                task_context=mock_task_context,
                review_findings=mock_review_findings,
                capture_knowledge=True
            )

            # Verify result includes task context
            assert result['task_id'] == mock_task_context['task_id']
            assert 'task_context' in result

    @pytest.mark.asyncio
    async def test_captured_knowledge_includes_review_mode(
        self,
        mock_task_context,
        mock_review_findings,
        mock_capture_session
    ):
        """Verify captured knowledge includes review mode."""
        with patch('guardkit.knowledge.review_knowledge_capture.InteractiveCaptureSession',
                   return_value=mock_capture_session):

            result = await run_review_capture(
                task_context=mock_task_context,
                review_findings=mock_review_findings,
                capture_knowledge=True
            )

            # Verify review mode is preserved
            assert result['review_mode'] == mock_review_findings['mode']

    @pytest.mark.asyncio
    async def test_captured_knowledge_includes_findings_summary(
        self,
        mock_task_context,
        mock_review_findings,
        mock_capture_session
    ):
        """Verify captured knowledge includes summary of review findings."""
        with patch('guardkit.knowledge.review_knowledge_capture.InteractiveCaptureSession',
                   return_value=mock_capture_session):

            result = await run_review_capture(
                task_context=mock_task_context,
                review_findings=mock_review_findings,
                capture_knowledge=True
            )

            # Should include findings metadata
            assert 'findings_count' in result or 'findings_summary' in result


# ============================================================================
# Test 6: Review Mode Compatibility
# ============================================================================

class TestReviewModeCompatibility:
    """Test compatibility with all review modes."""

    @pytest.mark.asyncio
    async def test_works_with_architectural_mode(self, mock_capture_session):
        """Verify knowledge capture works with architectural review mode."""
        findings = {'mode': 'architectural', 'findings': [], 'score': 75}
        task_ctx = {'task_id': 'TEST-001', 'review_mode': 'architectural'}

        with patch('guardkit.knowledge.review_knowledge_capture.InteractiveCaptureSession',
                   return_value=mock_capture_session):

            result = await run_review_capture(
                task_context=task_ctx,
                review_findings=findings,
                capture_knowledge=True
            )

            assert result['review_mode'] == 'architectural'
            assert result['capture_executed'] is True

    @pytest.mark.asyncio
    async def test_works_with_code_quality_mode(self, mock_capture_session):
        """Verify knowledge capture works with code-quality review mode."""
        findings = {'mode': 'code-quality', 'findings': [], 'complexity_score': 6}
        task_ctx = {'task_id': 'TEST-002', 'review_mode': 'code-quality'}

        with patch('guardkit.knowledge.review_knowledge_capture.InteractiveCaptureSession',
                   return_value=mock_capture_session):

            result = await run_review_capture(
                task_context=task_ctx,
                review_findings=findings,
                capture_knowledge=True
            )

            assert result['review_mode'] == 'code-quality'
            assert result['capture_executed'] is True

    @pytest.mark.asyncio
    async def test_works_with_decision_mode(self, mock_capture_session):
        """Verify knowledge capture works with decision review mode."""
        findings = {
            'mode': 'decision',
            'options': [{'name': 'Option A'}, {'name': 'Option B'}],
            'recommendation': 'Option A'
        }
        task_ctx = {'task_id': 'TEST-003', 'review_mode': 'decision'}

        with patch('guardkit.knowledge.review_knowledge_capture.InteractiveCaptureSession',
                   return_value=mock_capture_session):

            result = await run_review_capture(
                task_context=task_ctx,
                review_findings=findings,
                capture_knowledge=True
            )

            assert result['review_mode'] == 'decision'
            assert result['capture_executed'] is True

    @pytest.mark.asyncio
    async def test_works_with_technical_debt_mode(self, mock_capture_session):
        """Verify knowledge capture works with technical-debt review mode."""
        findings = {
            'mode': 'technical-debt',
            'debt_items': [{'type': 'code_smell', 'severity': 'medium'}],
            'total_debt_score': 42
        }
        task_ctx = {'task_id': 'TEST-004', 'review_mode': 'technical-debt'}

        with patch('guardkit.knowledge.review_knowledge_capture.InteractiveCaptureSession',
                   return_value=mock_capture_session):

            result = await run_review_capture(
                task_context=task_ctx,
                review_findings=findings,
                capture_knowledge=True
            )

            assert result['review_mode'] == 'technical-debt'
            assert result['capture_executed'] is True

    @pytest.mark.asyncio
    async def test_works_with_security_mode(self, mock_capture_session):
        """Verify knowledge capture works with security review mode."""
        findings = {
            'mode': 'security',
            'vulnerabilities': [{'cwe': 'CWE-89', 'severity': 'high'}],
            'risk_score': 8.5
        }
        task_ctx = {'task_id': 'TEST-005', 'review_mode': 'security'}

        with patch('guardkit.knowledge.review_knowledge_capture.InteractiveCaptureSession',
                   return_value=mock_capture_session):

            result = await run_review_capture(
                task_context=task_ctx,
                review_findings=findings,
                capture_knowledge=True
            )

            assert result['review_mode'] == 'security'
            assert result['capture_executed'] is True


# ============================================================================
# Test 7: Integration Class Methods
# ============================================================================

class TestReviewKnowledgeCaptureClass:
    """Test ReviewKnowledgeCapture integration class."""

    def test_review_knowledge_capture_class_exists(self):
        """Verify ReviewKnowledgeCapture class can be instantiated."""
        capture = ReviewKnowledgeCapture(
            task_context={'task_id': 'TEST-001'},
            review_findings={'mode': 'architectural'}
        )

        assert capture is not None
        assert hasattr(capture, 'task_context')
        assert hasattr(capture, 'review_findings')

    def test_generate_review_questions_method(self):
        """Verify generate_review_questions method exists and works."""
        capture = ReviewKnowledgeCapture(
            task_context={'task_id': 'TEST-001', 'review_mode': 'architectural'},
            review_findings={
                'mode': 'architectural',
                'findings': [{'category': 'SOLID_VIOLATION'}]
            }
        )

        questions = capture.generate_questions()

        assert hasattr(capture, 'generate_questions')
        assert isinstance(questions, list)
        assert len(questions) > 0
        assert 3 <= len(questions) <= 5

    @pytest.mark.asyncio
    async def test_run_abbreviated_capture_method(self, mock_capture_session):
        """Verify run_abbreviated_capture method exists and executes session."""
        with patch('guardkit.knowledge.review_knowledge_capture.InteractiveCaptureSession',
                   return_value=mock_capture_session):

            capture = ReviewKnowledgeCapture(
                task_context={'task_id': 'TEST-001'},
                review_findings={'mode': 'architectural'}
            )

            result = await capture.run_abbreviated_capture()

            assert hasattr(capture, 'run_abbreviated_capture')
            assert mock_capture_session.run_abbreviated.called
            assert result is not None

    def test_class_has_task_context_property(self):
        """Verify class exposes task_context as property."""
        task_ctx = {'task_id': 'TEST-001', 'title': 'Test Review'}
        capture = ReviewKnowledgeCapture(
            task_context=task_ctx,
            review_findings={'mode': 'architectural'}
        )

        assert capture.task_context == task_ctx

    def test_class_has_review_findings_property(self):
        """Verify class exposes review_findings as property."""
        findings = {'mode': 'architectural', 'score': 75}
        capture = ReviewKnowledgeCapture(
            task_context={'task_id': 'TEST-001'},
            review_findings=findings
        )

        assert capture.review_findings == findings

    def test_class_validates_required_fields(self):
        """Verify class validates required fields in task_context and review_findings."""
        # Missing task_id should raise error
        with pytest.raises((ValueError, KeyError)):
            ReviewKnowledgeCapture(
                task_context={},  # Missing task_id
                review_findings={'mode': 'architectural'}
            )

        # Missing mode should raise error
        with pytest.raises((ValueError, KeyError)):
            ReviewKnowledgeCapture(
                task_context={'task_id': 'TEST-001'},
                review_findings={}  # Missing mode
            )


# ============================================================================
# Test 8: Question Quality and Relevance
# ============================================================================

class TestQuestionQuality:
    """Test quality and relevance of generated questions."""

    def test_questions_are_open_ended(self, mock_review_findings, mock_task_context):
        """Verify generated questions are open-ended (not yes/no)."""
        questions = generate_review_questions(
            review_findings=mock_review_findings,
            task_context=mock_task_context
        )

        # Open-ended questions typically start with What, How, Why, etc.
        open_ended_starters = ['what', 'how', 'why', 'which', 'when', 'where', 'describe']

        open_ended_count = sum(
            1 for q in questions
            if any(q.lower().startswith(starter) for starter in open_ended_starters)
        )

        # At least 50% should be open-ended
        assert open_ended_count >= len(questions) / 2

    def test_questions_avoid_duplicates(self, mock_review_findings, mock_task_context):
        """Verify generated questions don't contain duplicates."""
        questions = generate_review_questions(
            review_findings=mock_review_findings,
            task_context=mock_task_context
        )

        # All questions should be unique
        assert len(questions) == len(set(questions))

    def test_questions_include_decision_prompt(self, mock_review_findings, mock_task_context):
        """Verify questions include decision/warning prompts."""
        questions = generate_review_questions(
            review_findings=mock_review_findings,
            task_context=mock_task_context
        )

        # Should have questions about decisions or warnings
        decision_keywords = ['decision', 'warning', 'learn', 'remember', 'future']
        has_decision_question = any(
            any(keyword in q.lower() for keyword in decision_keywords)
            for q in questions
        )

        assert has_decision_question, "Should include questions about decisions/warnings"


# ============================================================================
# Test 9: Error Handling
# ============================================================================

class TestErrorHandling:
    """Test error handling in knowledge capture integration."""

    @pytest.mark.asyncio
    async def test_handles_capture_session_failure_gracefully(
        self,
        mock_task_context,
        mock_review_findings
    ):
        """Verify graceful handling when capture session fails."""
        failing_session = Mock(spec=InteractiveCaptureSession)
        failing_session.run_abbreviated = AsyncMock(
            side_effect=Exception("Session failed")
        )

        with patch('guardkit.knowledge.review_knowledge_capture.InteractiveCaptureSession',
                   return_value=failing_session):

            # Should not raise, should return error state
            result = await run_review_capture(
                task_context=mock_task_context,
                review_findings=mock_review_findings,
                capture_knowledge=True
            )

            assert result['capture_executed'] is False
            assert 'error' in result

    @pytest.mark.asyncio
    async def test_handles_empty_review_findings(self, mock_task_context, mock_capture_session):
        """Verify handling when review findings are empty."""
        empty_findings = {'mode': 'architectural', 'findings': []}

        # Should still generate generic questions
        questions = generate_review_questions(
            review_findings=empty_findings,
            task_context=mock_task_context
        )

        assert len(questions) >= 3  # Should have at least generic questions

    @pytest.mark.asyncio
    async def test_handles_missing_review_mode(self, mock_task_context):
        """Verify handling when review mode is missing."""
        invalid_findings = {'findings': []}  # Missing 'mode'

        # Should raise or return empty questions
        with pytest.raises((ValueError, KeyError)):
            generate_review_questions(
                review_findings=invalid_findings,
                task_context=mock_task_context
            )


# ============================================================================
# Test 10: Integration with InteractiveCaptureSession
# ============================================================================

class TestInteractiveCaptureSessionIntegration:
    """Test integration with InteractiveCaptureSession."""

    @pytest.mark.asyncio
    async def test_passes_task_context_to_session(
        self,
        mock_task_context,
        mock_review_findings,
        mock_capture_session
    ):
        """Verify task context is passed to capture session."""
        with patch('guardkit.knowledge.review_knowledge_capture.InteractiveCaptureSession',
                   return_value=mock_capture_session):

            await run_review_capture(
                task_context=mock_task_context,
                review_findings=mock_review_findings,
                capture_knowledge=True
            )

            # Verify session was called with task_context
            call_args = mock_capture_session.run_abbreviated.call_args
            assert 'task_context' in call_args.kwargs or 'task_context' in str(call_args)

    @pytest.mark.asyncio
    async def test_session_receives_generated_questions(
        self,
        mock_task_context,
        mock_review_findings,
        mock_capture_session
    ):
        """Verify generated questions are passed to session."""
        with patch('guardkit.knowledge.review_knowledge_capture.InteractiveCaptureSession',
                   return_value=mock_capture_session):

            await run_review_capture(
                task_context=mock_task_context,
                review_findings=mock_review_findings,
                capture_knowledge=True
            )

            # Verify questions were passed
            call_args = mock_capture_session.run_abbreviated.call_args
            assert call_args is not None
            # Should have questions parameter
            assert 'questions' in call_args.kwargs or len(call_args.args) > 0


# ============================================================================
# Test 11: Graphiti Formatting (TASK-GMR-008)
# ============================================================================

class TestFormatReviewForGraphiti:
    """Test format_review_for_graphiti produces correct Graphiti episodes."""

    def test_returns_findings_and_outcome_episodes(
        self, mock_task_context, mock_review_findings
    ):
        """Verify two episodes are returned: findings and outcome."""
        result = format_review_for_graphiti(mock_task_context, mock_review_findings)

        assert "findings" in result
        assert "outcome" in result
        assert isinstance(result["findings"], dict)
        assert isinstance(result["outcome"], dict)

    def test_findings_episode_has_correct_group_id(
        self, mock_task_context, mock_review_findings
    ):
        """Verify findings episode targets project_decisions group."""
        result = format_review_for_graphiti(mock_task_context, mock_review_findings)
        assert result["findings"]["group_id"] == "guardkit__project_decisions"

    def test_outcome_episode_has_correct_group_id(
        self, mock_task_context, mock_review_findings
    ):
        """Verify outcome episode targets task_outcomes group."""
        result = format_review_for_graphiti(mock_task_context, mock_review_findings)
        assert result["outcome"]["group_id"] == "guardkit__task_outcomes"

    def test_findings_episode_contains_task_id(
        self, mock_task_context, mock_review_findings
    ):
        """Verify findings episode references the task ID."""
        result = format_review_for_graphiti(mock_task_context, mock_review_findings)
        assert "TASK-TEST-001" in result["findings"]["name"]
        assert "TASK-TEST-001" in result["findings"]["content"]

    def test_outcome_episode_contains_task_id(
        self, mock_task_context, mock_review_findings
    ):
        """Verify outcome episode references the task ID."""
        result = format_review_for_graphiti(mock_task_context, mock_review_findings)
        assert "TASK-TEST-001" in result["outcome"]["name"]
        assert "TASK-TEST-001" in result["outcome"]["content"]

    def test_findings_episode_includes_review_mode(
        self, mock_task_context, mock_review_findings
    ):
        """Verify findings episode includes the review mode."""
        result = format_review_for_graphiti(mock_task_context, mock_review_findings)
        assert "architectural" in result["findings"]["name"]
        assert "architectural" in result["findings"]["content"]

    def test_findings_episode_includes_score(
        self, mock_task_context, mock_review_findings
    ):
        """Verify findings episode includes the review score."""
        result = format_review_for_graphiti(mock_task_context, mock_review_findings)
        assert "65/100" in result["findings"]["content"]

    def test_outcome_episode_includes_score(
        self, mock_task_context, mock_review_findings
    ):
        """Verify outcome episode includes the review score."""
        result = format_review_for_graphiti(mock_task_context, mock_review_findings)
        assert "65/100" in result["outcome"]["content"]

    def test_findings_episode_includes_finding_descriptions(
        self, mock_task_context, mock_review_findings
    ):
        """Verify findings episode includes descriptions from review findings."""
        result = format_review_for_graphiti(mock_task_context, mock_review_findings)
        content = result["findings"]["content"]
        assert "Single Responsibility" in content
        assert "Token validation" in content

    def test_findings_episode_includes_severity(
        self, mock_task_context, mock_review_findings
    ):
        """Verify findings episode includes severity levels."""
        result = format_review_for_graphiti(mock_task_context, mock_review_findings)
        content = result["findings"]["content"]
        assert "[HIGH]" in content
        assert "[MEDIUM]" in content

    def test_outcome_episode_includes_recommendations(
        self, mock_task_context, mock_review_findings
    ):
        """Verify outcome episode includes recommendation text."""
        result = format_review_for_graphiti(mock_task_context, mock_review_findings)
        content = result["outcome"]["content"]
        assert "Split authentication" in content
        assert "shared token validation" in content

    def test_each_episode_has_required_keys(
        self, mock_task_context, mock_review_findings
    ):
        """Verify each episode has group_id, name, and content."""
        result = format_review_for_graphiti(mock_task_context, mock_review_findings)
        for key in ("findings", "outcome"):
            episode = result[key]
            assert "group_id" in episode
            assert "name" in episode
            assert "content" in episode

    def test_handles_empty_findings(self, mock_task_context):
        """Verify graceful handling when no findings present."""
        findings = {"mode": "architectural", "findings": [], "score": 80}
        result = format_review_for_graphiti(mock_task_context, findings)
        assert "No specific findings" in result["findings"]["content"]

    def test_handles_empty_recommendations(self, mock_task_context):
        """Verify graceful handling when no recommendations present."""
        findings = {"mode": "code-quality", "findings": [], "score": 90}
        result = format_review_for_graphiti(mock_task_context, findings)
        assert "No recommendations" in result["outcome"]["content"]

    def test_handles_string_findings(self, mock_task_context):
        """Verify handling when findings are plain strings instead of dicts."""
        findings = {
            "mode": "decision",
            "findings": ["Use JWT over sessions", "Add rate limiting"],
            "score": 70,
        }
        result = format_review_for_graphiti(mock_task_context, findings)
        assert "Use JWT over sessions" in result["findings"]["content"]
        assert "Add rate limiting" in result["findings"]["content"]

    def test_handles_string_recommendations(self, mock_task_context):
        """Verify handling when recommendations are plain strings."""
        findings = {
            "mode": "security",
            "findings": [],
            "score": 55,
            "recommendations": ["Fix SQL injection", "Add CSRF tokens"],
        }
        result = format_review_for_graphiti(mock_task_context, findings)
        assert "Fix SQL injection" in result["outcome"]["content"]
        assert "Add CSRF tokens" in result["outcome"]["content"]

    def test_handles_missing_score(self, mock_task_context):
        """Verify handling when score is not present."""
        findings = {"mode": "technical-debt", "findings": []}
        result = format_review_for_graphiti(mock_task_context, findings)
        assert "N/A/100" in result["findings"]["content"]

    def test_handles_dict_recommendations_with_text_key(self, mock_task_context):
        """Verify handling when recommendations are dicts with text key."""
        findings = {
            "mode": "architectural",
            "findings": [],
            "score": 75,
            "recommendations": [
                {"text": "Implement repository pattern", "priority": "high"},
                {"text": "Add caching layer", "priority": "medium"},
            ],
        }
        result = format_review_for_graphiti(mock_task_context, findings)
        assert "Implement repository pattern" in result["outcome"]["content"]
        assert "Add caching layer" in result["outcome"]["content"]
