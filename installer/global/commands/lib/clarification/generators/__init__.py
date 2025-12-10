"""Question generators for clarification contexts.

This package contains generator functions that create context-appropriate
clarifying questions based on task characteristics, complexity, and mode.

Modules:
- review_generator: Generates questions for task-review scope clarification (Context A)
- implement_generator: Generates questions for implementation preferences (Context B)
- planning_generator: Generates questions for implementation planning (Context C)
"""

from .review_generator import (
    generate_review_questions,
    get_question_priorities as get_review_question_priorities,
    filter_questions_by_priority as filter_review_questions_by_priority,
)
from .implement_generator import (
    generate_implement_questions,
    get_question_priorities as get_implement_question_priorities,
    filter_questions_by_priority as filter_implement_questions_by_priority,
    customize_question_text,
)
from .planning_generator import generate_planning_questions

__all__ = [
    # Context A: Review Scope
    "generate_review_questions",
    "get_review_question_priorities",
    "filter_review_questions_by_priority",
    # Context B: Implementation Preferences
    "generate_implement_questions",
    "get_implement_question_priorities",
    "filter_implement_questions_by_priority",
    "customize_question_text",
    # Context C: Implementation Planning
    "generate_planning_questions",
]
