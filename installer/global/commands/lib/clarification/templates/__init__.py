"""Question templates for clarification contexts.

This package contains template definitions for different clarification contexts:
- implementation_planning: Templates for /task-work Phase 1.5 (Context C)
"""

from .implementation_planning import (
    SCOPE_QUESTIONS,
    USER_QUESTIONS,
    TECHNOLOGY_QUESTIONS,
    INTEGRATION_QUESTIONS,
    TRADEOFF_QUESTIONS,
    EDGE_CASE_QUESTIONS,
)

__all__ = [
    "SCOPE_QUESTIONS",
    "USER_QUESTIONS",
    "TECHNOLOGY_QUESTIONS",
    "INTEGRATION_QUESTIONS",
    "TRADEOFF_QUESTIONS",
    "EDGE_CASE_QUESTIONS",
]
