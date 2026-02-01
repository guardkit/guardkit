"""Question templates for clarification contexts.

This package contains question templates for different clarification contexts:
- review_scope: Questions for task-review scope clarification (Context A)
- implementation_prefs: Questions for implementation preferences (Context B)
- implementation_planning: Templates for implementation planning (Context C)
- autobuild_workflow: Questions for AutoBuild workflow customization (Context D)
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
from .autobuild_workflow import (
    ROLE_CUSTOMIZATION_QUESTIONS,
    QUALITY_GATE_QUESTIONS,
    WORKFLOW_PREFERENCE_QUESTIONS,
    get_group_id_for_category,
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
    # Context D: AutoBuild Workflow Customization
    "ROLE_CUSTOMIZATION_QUESTIONS",
    "QUALITY_GATE_QUESTIONS",
    "WORKFLOW_PREFERENCE_QUESTIONS",
    "get_group_id_for_category",
]
