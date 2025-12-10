"""Question templates for Context B: Implementation Preferences.

This context is used in `/task-review` [I]mplement decision handler to
clarify how subtasks should be created and executed after review completion.

These questions help determine:
- Which recommended approach to follow
- Implementation constraints
- Parallelization preference
- Testing depth for subtasks
"""

from typing import List
from ..core import Question


APPROACH_PREFERENCE_QUESTIONS: List[Question] = [
    Question(
        id="approach_selection",
        category="approach",
        text="Which recommended approach should subtasks follow?",
        options=[
            "[1-3] Select specific option from review",
            "[R]ecommended (use review's top choice)",
            "[C]ustom (specify your own approach)"
        ],
        default="[R]ecommended (use review's top choice)",
        rationale="Following review's recommended approach ensures consistency",
    ),
]


CONSTRAINT_QUESTIONS: List[Question] = [
    Question(
        id="implementation_constraints",
        category="constraints",
        text="Any implementation constraints to consider?",
        options=[
            "[T]ime limit",
            "[R]esource limit",
            "[S]cope limit",
            "[N]one",
            "[C]ustom"
        ],
        default="[N]one",
        rationale="No constraints allows full implementation flexibility",
    ),
]


PARALLELIZATION_QUESTIONS: List[Question] = [
    Question(
        id="execution_preference",
        category="parallelization",
        text="How should subtasks be executed?",
        options=[
            "[M]aximize parallel (use Conductor workspaces)",
            "[S]equential (simpler execution)",
            "[D]etect automatically (recommended)"
        ],
        default="[D]etect automatically (recommended)",
        rationale="Auto-detection analyzes file conflicts to determine optimal execution",
    ),
]


TESTING_DEPTH_QUESTIONS: List[Question] = [
    Question(
        id="testing_preference",
        category="testing",
        text="What testing depth for subtasks?",
        options=[
            "[F]ull TDD (test-first for all subtasks)",
            "[S]tandard (quality gates only)",
            "[M]inimal (compilation only)",
            "[D]efault (based on complexity)"
        ],
        default="[D]efault (based on complexity)",
        rationale="Default adapts testing depth to each subtask's complexity",
    ),
]


WORKSPACE_NAMING_QUESTIONS: List[Question] = [
    Question(
        id="workspace_naming",
        category="conductor",
        text="Workspace naming preference for parallel execution?",
        options=[
            "[A]uto-generated (feature-slug-wave-N)",
            "[C]ustom prefix",
            "[N]o workspaces (sequential only)"
        ],
        default="[A]uto-generated (feature-slug-wave-N)",
        rationale="Auto-generated names provide clear wave-based organization",
    ),
]


# Export all question lists for easy import
__all__ = [
    "APPROACH_PREFERENCE_QUESTIONS",
    "CONSTRAINT_QUESTIONS",
    "PARALLELIZATION_QUESTIONS",
    "TESTING_DEPTH_QUESTIONS",
    "WORKSPACE_NAMING_QUESTIONS",
]
