"""Generator for Context B: Implementation Preferences questions.

This module generates clarifying questions for `/task-review` [I]mplement
decision handler. Questions help determine how subtasks should be created
and executed after review completion.

Typically 3-5 questions focused on execution preferences.
"""

from typing import List, Dict, Any
from ..core import Question
from ..templates.implementation_prefs import (
    APPROACH_PREFERENCE_QUESTIONS,
    CONSTRAINT_QUESTIONS,
    PARALLELIZATION_QUESTIONS,
    TESTING_DEPTH_QUESTIONS,
    WORKSPACE_NAMING_QUESTIONS,
)


def generate_implement_questions(
    review_findings: Dict[str, Any],
    num_subtasks: int,
    complexity: int
) -> List[Question]:
    """Generate clarifying questions for task-review [I]mplement handler.

    Args:
        review_findings: Review report data including recommendations
        num_subtasks: Number of subtasks that will be created
        complexity: Task complexity score (0-10)

    Returns:
        List of Question objects (3-5 questions)

    Examples:
        >>> generate_implement_questions({"recommendations": [...]}, 5, 7)
        # Returns approach, parallelization, testing questions

        >>> generate_implement_questions({"recommendations": [...]}, 2, 3)
        # Returns minimal questions (approach only)

        >>> generate_implement_questions({"recommendations": [...]}, 8, 9)
        # Returns full questions (all 5)
    """
    questions = []

    # 1. APPROACH PREFERENCE - Always ask if review provided multiple options
    # Determines which recommended approach subtasks should follow
    num_approaches = len(review_findings.get("recommendations", []))
    if num_approaches > 1:
        # Customize question with actual approach count
        approach_q = APPROACH_PREFERENCE_QUESTIONS[0]
        approach_q.text = f"The review identified {num_approaches} recommended approaches. Which should subtasks follow?"
        questions.append(approach_q)
    elif num_approaches == 1:
        # Single recommendation - confirm or allow override
        questions.append(APPROACH_PREFERENCE_QUESTIONS[0])

    # 2. PARALLELIZATION - Ask if multiple subtasks exist
    # Critical for Conductor workflow optimization
    if num_subtasks >= 3:
        questions.extend(PARALLELIZATION_QUESTIONS)

        # Add workspace naming if parallel execution possible
        if num_subtasks >= 4:  # Threshold for meaningful parallelization
            questions.extend(WORKSPACE_NAMING_QUESTIONS)

    # 3. TESTING DEPTH - Ask for complex implementations
    # Determines /task-work --mode flag for each subtask
    if complexity >= 6:
        questions.extend(TESTING_DEPTH_QUESTIONS)

    # 4. CONSTRAINTS - Ask if high complexity or many subtasks
    # Helps scope implementation effort
    if complexity >= 7 or num_subtasks >= 6:
        questions.extend(CONSTRAINT_QUESTIONS)

    # Limit to 5 questions max (keep implementation clarification lightweight)
    return questions[:5]


def get_question_priorities(
    num_subtasks: int,
    complexity: int,
    has_parallel_potential: bool = True
) -> List[str]:
    """Get prioritized list of question categories for implementation.

    This helps determine which questions to ask first if we need to
    limit to QUICK mode (2-3 questions).

    Args:
        num_subtasks: Number of subtasks to be created
        complexity: Task complexity score (0-10)
        has_parallel_potential: Whether tasks can be parallelized

    Returns:
        List of question category IDs in priority order

    Examples:
        >>> get_question_priorities(5, 7, True)
        ['execution_preference', 'approach_selection', 'testing_preference']

        >>> get_question_priorities(2, 3, False)
        ['approach_selection', 'testing_preference']
    """
    priorities = []

    # Priority 1: Parallelization (if applicable)
    if num_subtasks >= 3 and has_parallel_potential:
        priorities.append("execution_preference")

    # Priority 2: Approach selection (always important)
    priorities.append("approach_selection")

    # Priority 3: Testing depth (if complex)
    if complexity >= 6:
        priorities.append("testing_preference")

    # Priority 4: Workspace naming (if using Conductor)
    if num_subtasks >= 4 and has_parallel_potential:
        priorities.append("workspace_naming")

    # Priority 5: Constraints (if very complex)
    if complexity >= 7 or num_subtasks >= 6:
        priorities.append("implementation_constraints")

    return priorities


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
        >>> questions = generate_implement_questions({...}, 5, 7)
        >>> priorities = get_question_priorities(5, 7, True)
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


def customize_question_text(
    question: Question,
    context: Dict[str, Any]
) -> Question:
    """Customize question text based on specific context.

    This allows dynamic question text that reflects actual review findings.

    Args:
        question: Base question to customize
        context: Context data (review findings, counts, etc.)

    Returns:
        Question with customized text

    Examples:
        >>> q = APPROACH_PREFERENCE_QUESTIONS[0]
        >>> context = {"num_approaches": 3, "recommended": "JWT"}
        >>> customized = customize_question_text(q, context)
        >>> print(customized.text)
        "The review identified 3 approaches. Recommended: JWT. Which should subtasks follow?"
    """
    # Clone question to avoid modifying original
    custom_q = Question(
        id=question.id,
        category=question.category,
        text=question.text,
        options=question.options,
        default=question.default,
        rationale=question.rationale,
    )

    # Customize based on question type
    if question.id == "approach_selection":
        num_approaches = context.get("num_approaches", 1)
        recommended = context.get("recommended_approach", "")
        if num_approaches > 1 and recommended:
            custom_q.text = (
                f"The review identified {num_approaches} approaches. "
                f"Recommended: {recommended}. Which should subtasks follow?"
            )

    elif question.id == "execution_preference":
        num_subtasks = context.get("num_subtasks", 0)
        if num_subtasks > 0:
            custom_q.text = (
                f"How should {num_subtasks} subtasks be executed?"
            )

    elif question.id == "workspace_naming":
        feature_slug = context.get("feature_slug", "feature")
        custom_q.text = (
            f"Workspace naming for '{feature_slug}' parallel execution?"
        )

    return custom_q


# Export public API
__all__ = [
    "generate_implement_questions",
    "get_question_priorities",
    "filter_questions_by_priority",
    "customize_question_text",
]
