"""Generator for Context A: Review Scope Clarification questions.

This module generates clarifying questions for `/task-review` Phase 1 and
`/feature-plan` Step 2. Questions help guide what the review should focus on
and what trade-offs to prioritize.

Lighter weight than planning questions - max 4-5 questions.
"""

from typing import List, Dict, Any
from ..core import Question
from ..templates.review_scope import (
    REVIEW_FOCUS_QUESTIONS,
    ANALYSIS_DEPTH_QUESTIONS,
    TRADEOFF_PRIORITY_QUESTIONS,
    SPECIFIC_CONCERNS_QUESTIONS,
    EXTENSIBILITY_QUESTIONS,
)


def generate_review_questions(
    task_context: Dict[str, Any],
    review_mode: str,
    complexity: int
) -> List[Question]:
    """Generate clarifying questions for task-review Phase 1.

    Lighter weight than planning questions - max 4-5 questions.

    Args:
        task_context: Context about the task being reviewed
        review_mode: Review mode - "architectural", "code-quality", "decision",
                     "technical-debt", "security"
        complexity: Task complexity score (0-10)

    Returns:
        List of Question objects (max 5)

    Examples:
        >>> generate_review_questions({}, "architectural", 7)
        # Returns focus, depth, extensibility questions

        >>> generate_review_questions({}, "decision", 5)
        # Returns focus, depth, tradeoff questions

        >>> generate_review_questions({}, "security", 3)
        # Returns depth question only
    """
    questions = []

    # 1. REVIEW FOCUS - Ask for architectural and decision modes
    # These modes benefit from knowing what aspects to focus on
    if review_mode in ["architectural", "decision"]:
        questions.extend(REVIEW_FOCUS_QUESTIONS)

    # 2. ANALYSIS DEPTH - Ask for all modes except quick reviews
    # Everyone benefits from clarifying depth expectations
    if complexity >= 4:
        questions.extend(ANALYSIS_DEPTH_QUESTIONS)

    # 3. TRADE-OFF PRIORITIES - Critical for decision mode
    # Also useful for architectural reviews
    if review_mode == "decision":
        questions.extend(TRADEOFF_PRIORITY_QUESTIONS)
    elif review_mode == "architectural" and complexity >= 6:
        questions.extend(TRADEOFF_PRIORITY_QUESTIONS)

    # 4. SPECIFIC CONCERNS - Ask for complex reviews
    # Allows user to highlight particular areas of concern
    if complexity >= 6:
        questions.extend(SPECIFIC_CONCERNS_QUESTIONS)

    # 5. EXTENSIBILITY - Ask for architectural reviews
    # Long-term thinking is important for architecture decisions
    if review_mode == "architectural":
        questions.extend(EXTENSIBILITY_QUESTIONS)

    # Limit to 5 questions max (reviews are lighter weight)
    return questions[:5]


def get_question_priorities(review_mode: str, complexity: int) -> List[str]:
    """Get prioritized list of question categories for given mode.

    This helps determine which questions to ask first if we need to
    limit to QUICK mode (2-3 questions).

    Args:
        review_mode: Review mode
        complexity: Task complexity score (0-10)

    Returns:
        List of question category IDs in priority order

    Examples:
        >>> get_question_priorities("decision", 5)
        ['tradeoff_priority', 'review_aspects', 'analysis_depth']

        >>> get_question_priorities("architectural", 7)
        ['review_aspects', 'future_extensibility', 'analysis_depth']
    """
    priorities = {
        "architectural": [
            "review_aspects",
            "future_extensibility",
            "analysis_depth",
            "tradeoff_priority",
            "specific_concerns",
        ],
        "code-quality": [
            "analysis_depth",
            "specific_concerns",
            "review_aspects",
        ],
        "decision": [
            "tradeoff_priority",
            "review_aspects",
            "analysis_depth",
            "specific_concerns",
        ],
        "technical-debt": [
            "analysis_depth",
            "tradeoff_priority",
            "specific_concerns",
        ],
        "security": [
            "analysis_depth",
            "specific_concerns",
            "review_aspects",
        ],
    }

    # Return mode-specific priorities or default
    return priorities.get(review_mode, priorities["architectural"])


def filter_questions_by_priority(
    questions: List[Question],
    priorities: List[str],
    max_count: int = 3
) -> List[Question]:
    """Filter questions to top priority items for QUICK mode.

    Args:
        questions: Full list of questions
        priorities: Priority order of question IDs
        max_count: Maximum number of questions to return

    Returns:
        Filtered list of questions in priority order

    Examples:
        >>> questions = generate_review_questions({}, "decision", 5)
        >>> priorities = get_question_priorities("decision", 5)
        >>> quick_questions = filter_questions_by_priority(questions, priorities, 3)
        >>> len(quick_questions)
        3
    """
    # Create dict for fast lookup
    question_map = {q.id: q for q in questions}

    # Get questions in priority order
    filtered = []
    for priority_id in priorities:
        if priority_id in question_map:
            filtered.append(question_map[priority_id])
            if len(filtered) >= max_count:
                break

    return filtered


# Export public API
__all__ = [
    "generate_review_questions",
    "get_question_priorities",
    "filter_questions_by_priority",
]
