"""Question generators for clarification contexts.

This package contains generator functions that create context-appropriate
clarifying questions based on task characteristics, complexity, and mode.

Modules:
- review_generator: Generates questions for task-review scope clarification (Context A)
- planning_generator: Generates questions for implementation planning (Context C)
- (Future) implementation_generator: Generates questions for implementation preferences (Context B)
"""

from .review_generator import (
    generate_review_questions,
    get_question_priorities,
    filter_questions_by_priority,
)
from .planning_generator import generate_planning_questions

__all__ = [
    "generate_review_questions",
    "get_question_priorities",
    "filter_questions_by_priority",
    "generate_planning_questions",
]
