"""Question generator for AutoBuild workflow customization (Context D).

This module generates contextualized questions for AutoBuild (feature-build)
workflow customization based on task characteristics and user preferences.

Addresses TASK-REV-7549 findings:
- Player-Coach role reversal prevention
- Quality gate threshold configuration
- Workflow preference capture

The generator:
1. Detects AutoBuild-related context in task description
2. Selects relevant question templates
3. Filters by focus area if --focus flag is provided
4. Prioritizes and limits questions based on mode
"""

from dataclasses import dataclass
from typing import List, Optional
import re

from ..core import Question, ClarificationMode
from ..templates.autobuild_workflow import (
    ROLE_CUSTOMIZATION_QUESTIONS,
    QUALITY_GATE_QUESTIONS,
    WORKFLOW_PREFERENCE_QUESTIONS,
)


# =============================================================================
# AUTOBUILD DETECTION KEYWORDS
# =============================================================================

AUTOBUILD_KEYWORDS = [
    "feature-build",
    "feature build",
    "autobuild",
    "auto-build",
    "player-coach",
    "player coach",
    "/feature-build",
]

ROLE_KEYWORDS = [
    "player",
    "coach",
    "role",
    "validator",
    "implementer",
    "autonomous",
]

QUALITY_GATE_KEYWORDS = [
    "coverage",
    "threshold",
    "quality gate",
    "arch review",
    "architectural review",
    "test pass",
]

WORKFLOW_KEYWORDS = [
    "iteration",
    "turn",
    "tdd",
    "bdd",
    "standard mode",
    "implementation mode",
    "max turn",
]


# =============================================================================
# DETECTION
# =============================================================================

@dataclass
class DetectionResult:
    """Result of AutoBuild context detection."""
    detected: bool
    context: dict


def detect_autobuild_context(text: str) -> Optional[DetectionResult]:
    """Detect if text is related to AutoBuild workflow.

    Args:
        text: Task description or title to analyze

    Returns:
        DetectionResult if AutoBuild context detected, None otherwise

    Examples:
        >>> result = detect_autobuild_context("Configure feature-build workflow")
        >>> result.detected
        True
        >>> result = detect_autobuild_context("Fix typo in README")
        >>> result is None
        True
    """
    text_lower = text.lower()

    # Check for direct AutoBuild keywords
    has_autobuild = any(keyword in text_lower for keyword in AUTOBUILD_KEYWORDS)

    # Check for role-related keywords (Player/Coach)
    has_role = any(keyword in text_lower for keyword in ROLE_KEYWORDS)

    # Check for quality gate keywords
    has_quality = any(keyword in text_lower for keyword in QUALITY_GATE_KEYWORDS)

    # Check for workflow keywords
    has_workflow = any(keyword in text_lower for keyword in WORKFLOW_KEYWORDS)

    # Require at least one AutoBuild keyword OR two other category keywords
    is_autobuild_context = (
        has_autobuild or
        (has_role and has_quality) or
        (has_role and has_workflow) or
        (has_quality and has_workflow)
    )

    if is_autobuild_context:
        return DetectionResult(
            detected=True,
            context={
                "has_autobuild": has_autobuild,
                "has_role": has_role,
                "has_quality": has_quality,
                "has_workflow": has_workflow,
            }
        )

    return None


# =============================================================================
# QUESTION GENERATION
# =============================================================================

def prioritize_questions(
    questions: List[Question],
    max_questions: int = 7
) -> List[Question]:
    """Prioritize and limit questions to avoid overwhelming users.

    Priority order for AutoBuild questions:
    1. Role customization (prevent role reversal)
    2. Quality gates (prevent threshold drift)
    3. Workflow preferences (nice to have)

    Args:
        questions: All generated questions
        max_questions: Maximum number of questions to return

    Returns:
        Prioritized and limited list of questions
    """
    # Category priority weights
    priority_weights = {
        "role_customization": 100,
        "quality_gates": 90,
        "workflow_prefs": 80,
    }

    # Sort by priority
    sorted_questions = sorted(
        questions,
        key=lambda q: priority_weights.get(q.category, 0),
        reverse=True
    )

    return sorted_questions[:max_questions]


def generate_autobuild_questions(
    task_description: str,
    mode: ClarificationMode = ClarificationMode.FULL,
    focus: Optional[str] = None,
) -> List[Question]:
    """Generate clarifying questions for AutoBuild workflow customization.

    Args:
        task_description: Task description or title
        mode: Clarification mode (FULL, QUICK, SKIP, USE_DEFAULTS)
        focus: Optional focus area to filter questions:
               - "role-customization": Only role questions
               - "quality-gates": Only quality gate questions
               - "workflow-prefs": Only workflow preference questions

    Returns:
        List of prioritized questions (max 7 for FULL, max 3 for QUICK)

    Examples:
        >>> questions = generate_autobuild_questions(
        ...     "Configure feature-build",
        ...     mode=ClarificationMode.FULL
        ... )
        >>> len(questions) <= 7
        True

        >>> questions = generate_autobuild_questions(
        ...     "Configure feature-build",
        ...     mode=ClarificationMode.FULL,
        ...     focus="role-customization"
        ... )
        >>> all(q.category == "role_customization" for q in questions)
        True
    """
    # Handle skip mode
    if mode == ClarificationMode.SKIP:
        return []

    # Detect AutoBuild context
    detection = detect_autobuild_context(task_description)

    # If no AutoBuild context detected and no focus, return empty
    if detection is None and focus is None:
        return []

    questions: List[Question] = []

    # Apply focus filter if provided
    if focus == "role-customization":
        questions = list(ROLE_CUSTOMIZATION_QUESTIONS)
    elif focus == "quality-gates":
        questions = list(QUALITY_GATE_QUESTIONS)
    elif focus == "workflow-prefs":
        questions = list(WORKFLOW_PREFERENCE_QUESTIONS)
    else:
        # No focus - include all relevant categories based on detection
        if detection:
            # Always include role questions (addresses role reversal finding)
            questions.extend(ROLE_CUSTOMIZATION_QUESTIONS)

            # Always include quality gate questions (addresses threshold drift)
            questions.extend(QUALITY_GATE_QUESTIONS)

            # Include workflow if detected or in FULL mode
            if detection.context.get("has_workflow") or mode == ClarificationMode.FULL:
                questions.extend(WORKFLOW_PREFERENCE_QUESTIONS)
        else:
            # Focus was set to something else, include all
            questions.extend(ROLE_CUSTOMIZATION_QUESTIONS)
            questions.extend(QUALITY_GATE_QUESTIONS)
            questions.extend(WORKFLOW_PREFERENCE_QUESTIONS)

    # Adjust max questions based on mode
    max_questions = 3 if mode == ClarificationMode.QUICK else 7

    # Prioritize and limit
    return prioritize_questions(questions, max_questions=max_questions)


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "DetectionResult",
    "detect_autobuild_context",
    "generate_autobuild_questions",
    "prioritize_questions",
    "AUTOBUILD_KEYWORDS",
    "ROLE_KEYWORDS",
    "QUALITY_GATE_KEYWORDS",
    "WORKFLOW_KEYWORDS",
]
