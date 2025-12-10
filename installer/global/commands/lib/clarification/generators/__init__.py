"""Question generators for clarification contexts.

This package contains generator functions that create contextualized questions
from templates based on detection results and task context:
- planning_generator: Generates questions for /task-work Phase 1.5 (Context C)
"""

from .planning_generator import generate_planning_questions

__all__ = [
    "generate_planning_questions",
]
