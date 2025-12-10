"""Question generators for clarification contexts.

This package contains generator functions that create context-appropriate
clarifying questions based on task characteristics, complexity, and mode.

Modules:
- review_generator: Generates questions for task-review scope clarification
- (Future) implementation_generator: Generates questions for implementation preferences
- (Future) planning_generator: Generates questions for implementation planning
"""

from .review_generator import (
    generate_review_questions,
    get_question_priorities,
    filter_questions_by_priority,
)

__all__ = [
    "generate_review_questions",
    "get_question_priorities",
    "filter_questions_by_priority",
]
