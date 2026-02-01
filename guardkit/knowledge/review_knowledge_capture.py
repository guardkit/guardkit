"""Review Knowledge Capture Integration for /task-review --capture-knowledge.

This module provides integration between the task review workflow and knowledge
capture, enabling context-specific questions to be generated from review findings.

The module supports all review modes:
- architectural: SOLID/DRY/YAGNI compliance review
- code-quality: Maintainability and complexity assessment
- decision: Technical decision analysis with options evaluation
- technical-debt: Debt inventory and prioritization
- security: Security audit and vulnerability assessment

Example Usage:
    # Using the function interface
    result = await run_review_capture(
        task_context={'task_id': 'TASK-001', 'review_mode': 'architectural'},
        review_findings={'mode': 'architectural', 'findings': [...]},
        capture_knowledge=True
    )

    # Using the class interface
    capture = ReviewKnowledgeCapture(
        task_context={'task_id': 'TASK-001'},
        review_findings={'mode': 'architectural'}
    )
    questions = capture.generate_questions()
    result = await capture.run_abbreviated_capture()

    # Flag parsing
    config = ReviewCaptureConfig.from_args(['--capture-knowledge'])
    assert config.capture_knowledge is True
"""

from dataclasses import dataclass
from typing import List, Dict, Optional, Any

from .interactive_capture import InteractiveCaptureSession


@dataclass
class ReviewCaptureConfig:
    """Configuration for review knowledge capture.

    Attributes:
        capture_knowledge: Whether to trigger knowledge capture after review
        enabled: Alias for capture_knowledge (for compatibility)
    """

    capture_knowledge: bool = False

    @property
    def enabled(self) -> bool:
        """Return whether capture is enabled."""
        return self.capture_knowledge

    @classmethod
    def from_args(cls, args: List[str]) -> "ReviewCaptureConfig":
        """Parse command-line arguments to create config.

        Supported flags:
            --capture-knowledge: Enable knowledge capture
            -ck: Short form of --capture-knowledge

        Args:
            args: List of command-line arguments

        Returns:
            ReviewCaptureConfig with parsed settings
        """
        capture_knowledge = "--capture-knowledge" in args or "-ck" in args
        return cls(capture_knowledge=capture_knowledge)


# Mode-specific question templates
_MODE_QUESTIONS: Dict[str, List[str]] = {
    "architectural": [
        "What architectural patterns were identified during this review?",
        "Which SOLID violations were discovered that should be addressed?",
        "What architectural decisions should be remembered for future reviews?",
    ],
    "code-quality": [
        "What code quality issues were most significant in this review?",
        "What refactoring opportunities were identified?",
        "How should similar code quality concerns be handled in the future?",
    ],
    "decision": [
        "What decision was made during this review?",
        "What alternatives were considered before reaching this decision?",
        "Why was this decision chosen over the alternatives?",
    ],
    "technical-debt": [
        "What technical debt items were identified in this review?",
        "What should be prioritized when addressing this technical debt?",
        "How can similar technical debt be prevented in the future?",
    ],
    "security": [
        "What security concerns were identified during this review?",
        "Which vulnerabilities should be addressed immediately?",
        "How should security reviews be conducted for similar components?",
    ],
}

# Generic questions applicable to all review modes
_GENERIC_QUESTIONS: List[str] = [
    "What did you learn about {review_mode} from this review?",
    "What decisions were made that should be remembered?",
    "What warnings should be noted for similar future tasks?",
]


def generate_review_questions(
    review_findings: Dict[str, Any],
    task_context: Dict[str, Any]
) -> List[str]:
    """Generate context-specific questions from review findings.

    Creates 3-5 targeted questions based on the review mode and findings.
    Questions are designed to be open-ended (What, How, Why) and reference
    the specific review context.

    Args:
        review_findings: Dictionary containing review results with 'mode' key
        task_context: Dictionary containing task metadata

    Returns:
        List of 3-5 unique questions tailored to the review

    Raises:
        ValueError: If review_findings is missing 'mode' key
        KeyError: If review_findings is missing 'mode' key
    """
    # Validate required fields
    if "mode" not in review_findings:
        raise ValueError("review_findings must contain 'mode' key")

    review_mode = review_findings["mode"]
    questions: List[str] = []

    # Add mode-specific questions (up to 2)
    mode_questions = _MODE_QUESTIONS.get(review_mode, [])
    questions.extend(mode_questions[:2])

    # Add generic questions with mode substitution
    for generic_q in _GENERIC_QUESTIONS:
        formatted = generic_q.format(review_mode=review_mode)
        if formatted not in questions:
            questions.append(formatted)

    # Add findings-specific question if findings present
    findings = review_findings.get("findings", [])
    if findings:
        questions.append(
            f"What recommendations emerged from the {len(findings)} finding(s) in this review?"
        )

    # Ensure we have 3-5 questions
    if len(questions) < 3:
        # Add more generic questions
        questions.append(f"How should {review_mode} reviews be improved in the future?")

    # Deduplicate while preserving order
    seen = set()
    unique_questions = []
    for q in questions:
        if q not in seen:
            seen.add(q)
            unique_questions.append(q)

    # Return 3-5 questions
    return unique_questions[:5] if len(unique_questions) > 5 else unique_questions


class ReviewKnowledgeCapture:
    """Integration class for review knowledge capture.

    Provides methods to generate review-specific questions and run
    abbreviated capture sessions after task reviews complete.

    Attributes:
        task_context: Task metadata including task_id
        review_findings: Review results including mode and findings
    """

    def __init__(self, task_context: Dict[str, Any], review_findings: Dict[str, Any]):
        """Initialize ReviewKnowledgeCapture.

        Args:
            task_context: Dictionary with task metadata (must include 'task_id')
            review_findings: Dictionary with review results (must include 'mode')

        Raises:
            ValueError: If task_context missing 'task_id' or review_findings missing 'mode'
            KeyError: If task_context missing 'task_id' or review_findings missing 'mode'
        """
        # Validate required fields
        if "task_id" not in task_context:
            raise KeyError("task_context must contain 'task_id'")
        if "mode" not in review_findings:
            raise KeyError("review_findings must contain 'mode'")

        self._task_context = task_context
        self._review_findings = review_findings

    @property
    def task_context(self) -> Dict[str, Any]:
        """Get the task context."""
        return self._task_context

    @property
    def review_findings(self) -> Dict[str, Any]:
        """Get the review findings."""
        return self._review_findings

    def generate_questions(self) -> List[str]:
        """Generate context-specific questions for this review.

        Returns:
            List of 3-5 questions tailored to the review mode and findings
        """
        return generate_review_questions(self._review_findings, self._task_context)

    async def run_abbreviated_capture(
        self,
        custom_questions: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Run an abbreviated knowledge capture session.

        Args:
            custom_questions: Optional list of custom questions to use
                instead of auto-generated questions

        Returns:
            Dictionary with capture results
        """
        # Create session
        session = InteractiveCaptureSession()

        # Determine questions to use
        questions = custom_questions if custom_questions else self.generate_questions()

        # Run abbreviated session
        result = await session.run_abbreviated(
            questions=questions,
            task_context=self._task_context
        )

        return result


async def run_review_capture(
    task_context: Dict[str, Any],
    review_findings: Dict[str, Any],
    capture_knowledge: bool
) -> Dict[str, Any]:
    """Run review knowledge capture if enabled.

    Main entry point for integrating knowledge capture with task reviews.
    When capture_knowledge is True, generates context-specific questions
    and runs an abbreviated capture session.

    Args:
        task_context: Task metadata including task_id
        review_findings: Review results including mode and findings
        capture_knowledge: Whether to run the capture session

    Returns:
        Dictionary with:
            - capture_executed: bool - Whether capture was run
            - task_id: str - The task ID
            - task_context: Dict - The task context
            - review_mode: str - The review mode
            - findings_count: int - Number of findings (if capture executed)
            - error: str - Error message (if capture failed)
    """
    result: Dict[str, Any] = {
        "capture_executed": False,
        "task_id": task_context.get("task_id", ""),
        "task_context": task_context,
        "review_mode": review_findings.get("mode", "unknown"),
    }

    # Calculate findings count
    findings = review_findings.get("findings", [])
    result["findings_count"] = len(findings) if isinstance(findings, list) else 0

    # Skip if capture not requested
    if not capture_knowledge:
        return result

    try:
        # Create capture instance
        capture = ReviewKnowledgeCapture(
            task_context=task_context,
            review_findings=review_findings
        )

        # Generate questions
        questions = capture.generate_questions()

        # Create session and run
        session = InteractiveCaptureSession()

        # Run abbreviated session with questions
        await session.run_abbreviated(
            questions=questions,
            task_context=task_context
        )

        result["capture_executed"] = True

    except Exception as e:
        result["capture_executed"] = False
        result["error"] = str(e)

    return result
