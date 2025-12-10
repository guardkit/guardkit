"""Question templates for clarification contexts.

This package contains question templates for different clarification contexts:
- review_scope: Questions for task-review scope clarification (Context A)
- implementation_planning: Templates for implementation planning (Context C)
- (Future) implementation_prefs: Questions for implementation preferences (Context B)
"""

from .review_scope import (
    REVIEW_FOCUS_QUESTIONS,
    ANALYSIS_DEPTH_QUESTIONS,
    TRADEOFF_PRIORITY_QUESTIONS,
    SPECIFIC_CONCERNS_QUESTIONS,
    EXTENSIBILITY_QUESTIONS,
)
from .implementation_planning import (
    SCOPE_QUESTIONS,
    USER_QUESTIONS,
    TECHNOLOGY_QUESTIONS,
    INTEGRATION_QUESTIONS,
    TRADEOFF_QUESTIONS,
    EDGE_CASE_QUESTIONS,
)

__all__ = [
    "REVIEW_FOCUS_QUESTIONS",
    "ANALYSIS_DEPTH_QUESTIONS",
    "TRADEOFF_PRIORITY_QUESTIONS",
    "SPECIFIC_CONCERNS_QUESTIONS",
    "EXTENSIBILITY_QUESTIONS",
    "SCOPE_QUESTIONS",
    "USER_QUESTIONS",
    "TECHNOLOGY_QUESTIONS",
    "INTEGRATION_QUESTIONS",
    "TRADEOFF_QUESTIONS",
    "EDGE_CASE_QUESTIONS",
]
