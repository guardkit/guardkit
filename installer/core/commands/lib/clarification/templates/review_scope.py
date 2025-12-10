"""Question templates for Context A: Review Scope Clarification.

This context is used in `/task-review` Phase 1 and `/feature-plan` Step 2 to
clarify what the review should focus on and what trade-offs to prioritize.

Lighter weight than planning questions - typically 4-5 questions max.
"""

from typing import List
from ..core import Question


REVIEW_FOCUS_QUESTIONS: List[Question] = [
    Question(
        id="review_aspects",
        category="focus",
        text="What aspects should this analysis focus on?",
        options=[
            "[A]ll aspects",
            "[T]echnical only",
            "[R]chitecture",
            "[P]erformance",
            "[S]ecurity"
        ],
        default="[A]ll aspects",
        rationale="All aspects provides comprehensive analysis",
    ),
]


ANALYSIS_DEPTH_QUESTIONS: List[Question] = [
    Question(
        id="analysis_depth",
        category="depth",
        text="How deep should the analysis go?",
        options=[
            "[Q]uick (surface-level)",
            "[S]tandard (recommended)",
            "[D]eep (comprehensive)",
        ],
        default="[S]tandard (recommended)",
        rationale="Standard depth balances thoroughness with time investment",
    ),
]


TRADEOFF_PRIORITY_QUESTIONS: List[Question] = [
    Question(
        id="tradeoff_priority",
        category="priority",
        text="What trade-offs are you optimizing for?",
        options=[
            "[S]peed of delivery",
            "[Q]uality/reliability",
            "[C]ost",
            "[M]aintainability",
            "[B]alanced"
        ],
        default="[B]alanced",
        rationale="Balanced approach considers all factors",
    ),
]


SPECIFIC_CONCERNS_QUESTIONS: List[Question] = [
    Question(
        id="specific_concerns",
        category="concerns",
        text="Are there specific concerns you want addressed? (Enter text or press Enter to skip)",
        options=["[Free-form text input]"],
        default="[Free-form text input]",
        rationale="Free-form input for user-specific concerns",
    ),
]


EXTENSIBILITY_QUESTIONS: List[Question] = [
    Question(
        id="future_extensibility",
        category="scope",
        text="Should the review consider future extensibility?",
        options=[
            "[Y]es (long-term thinking)",
            "[N]o (current needs only)",
            "[D]efault (based on complexity)"
        ],
        default="[D]efault (based on complexity)",
        rationale="Default based on task complexity - higher complexity considers extensibility",
    ),
]


# Export all question lists for easy import
__all__ = [
    "REVIEW_FOCUS_QUESTIONS",
    "ANALYSIS_DEPTH_QUESTIONS",
    "TRADEOFF_PRIORITY_QUESTIONS",
    "SPECIFIC_CONCERNS_QUESTIONS",
    "EXTENSIBILITY_QUESTIONS",
]
