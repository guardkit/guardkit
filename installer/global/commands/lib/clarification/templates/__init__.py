"""Question templates for clarification contexts.

This package contains question templates for different clarification contexts:
- review_scope: Questions for task-review scope clarification (Context A)
- implementation_prefs: Questions for implementation preferences (Context B)
- implementation_planning: Templates for implementation planning (Context C)
"""

from .review_scope import (
    REVIEW_FOCUS_QUESTIONS,
    ANALYSIS_DEPTH_QUESTIONS,
    TRADEOFF_PRIORITY_QUESTIONS,
    SPECIFIC_CONCERNS_QUESTIONS,
    EXTENSIBILITY_QUESTIONS,
)
from .implementation_prefs import (
    APPROACH_PREFERENCE_QUESTIONS,
    CONSTRAINT_QUESTIONS,
    PARALLELIZATION_QUESTIONS,
    TESTING_DEPTH_QUESTIONS,
    WORKSPACE_NAMING_QUESTIONS,
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
    # Context A: Review Scope
    "REVIEW_FOCUS_QUESTIONS",
    "ANALYSIS_DEPTH_QUESTIONS",
    "TRADEOFF_PRIORITY_QUESTIONS",
    "SPECIFIC_CONCERNS_QUESTIONS",
    "EXTENSIBILITY_QUESTIONS",
    # Context B: Implementation Preferences
    "APPROACH_PREFERENCE_QUESTIONS",
    "CONSTRAINT_QUESTIONS",
    "PARALLELIZATION_QUESTIONS",
    "TESTING_DEPTH_QUESTIONS",
    "WORKSPACE_NAMING_QUESTIONS",
    # Context C: Implementation Planning
    "SCOPE_QUESTIONS",
    "USER_QUESTIONS",
    "TECHNOLOGY_QUESTIONS",
    "INTEGRATION_QUESTIONS",
    "TRADEOFF_QUESTIONS",
    "EDGE_CASE_QUESTIONS",
]
