"""Question templates for clarification contexts.

This package contains question templates for different clarification contexts:
- review_scope: Questions for task-review scope clarification
- (Future) implementation_prefs: Questions for implementation preferences
- (Future) planning: Questions for implementation planning
"""

from .review_scope import (
    REVIEW_FOCUS_QUESTIONS,
    ANALYSIS_DEPTH_QUESTIONS,
    TRADEOFF_PRIORITY_QUESTIONS,
    SPECIFIC_CONCERNS_QUESTIONS,
    EXTENSIBILITY_QUESTIONS,
)

__all__ = [
    "REVIEW_FOCUS_QUESTIONS",
    "ANALYSIS_DEPTH_QUESTIONS",
    "TRADEOFF_PRIORITY_QUESTIONS",
    "SPECIFIC_CONCERNS_QUESTIONS",
    "EXTENSIBILITY_QUESTIONS",
]
