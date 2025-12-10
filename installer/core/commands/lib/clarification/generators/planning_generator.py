"""Question generator for implementation planning clarification (Context C).

This module generates contextualized questions for /task-work Phase 1.5 based on
task complexity, detected ambiguities, and codebase context. Uses the 5W1H framework
to systematically identify what needs clarification before implementation begins.

The generator:
1. Detects various types of ambiguity in the task
2. Selects relevant question templates
3. Instantiates templates with task-specific context
4. Prioritizes and limits to 7 questions max
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import re

from ..core import Question, ClarificationMode
from ..templates.implementation_planning import (
    SCOPE_QUESTIONS,
    USER_QUESTIONS,
    TECHNOLOGY_QUESTIONS,
    INTEGRATION_QUESTIONS,
    TRADEOFF_QUESTIONS,
    EDGE_CASE_QUESTIONS,
)


@dataclass
class TaskContext:
    """Context about the task being planned."""
    task_id: str
    title: str
    description: str
    acceptance_criteria: List[str] = None
    tags: List[str] = None
    complexity_score: int = 5

    def __post_init__(self):
        """Initialize default values."""
        if self.acceptance_criteria is None:
            self.acceptance_criteria = []
        if self.tags is None:
            self.tags = []


@dataclass
class CodebaseContext:
    """Context about the codebase (optional, for advanced detection)."""
    project_type: Optional[str] = None  # "web", "cli", "library", etc.
    tech_stack: List[str] = None  # ["python", "react", "fastapi"]
    existing_patterns: Dict[str, Any] = None  # Detected patterns
    has_database: bool = False
    has_api: bool = False

    def __post_init__(self):
        """Initialize default values."""
        if self.tech_stack is None:
            self.tech_stack = []
        if self.existing_patterns is None:
            self.existing_patterns = {}


@dataclass
class DetectionResult:
    """Result of ambiguity detection."""
    detected: bool
    context: Dict[str, Any]  # Context-specific data for template instantiation


# =============================================================================
# DETECTION FUNCTIONS
# =============================================================================

def detect_scope_ambiguity(task_context: TaskContext) -> Optional[DetectionResult]:
    """Detect if task scope needs clarification.

    Looks for:
    - Vague or broad language (e.g., "support", "handle", "manage")
    - Missing acceptance criteria
    - Multiple concerns in title

    Args:
        task_context: Task information

    Returns:
        DetectionResult if ambiguity detected, None otherwise
    """
    # Check for vague language
    vague_terms = ["support", "handle", "manage", "deal with", "work with", "improve"]
    title_lower = task_context.title.lower()
    desc_lower = task_context.description.lower()

    has_vague_language = any(term in title_lower or term in desc_lower for term in vague_terms)

    # Check for missing or minimal acceptance criteria
    has_minimal_criteria = len(task_context.acceptance_criteria) < 2

    # Check for multiple concerns (multiple "and" or "+" in title)
    has_multiple_concerns = title_lower.count(" and ") > 1 or title_lower.count("+") > 0

    if has_vague_language or has_minimal_criteria or has_multiple_concerns:
        # Extract potential feature name from title
        feature = task_context.title.split(":")[0] if ":" in task_context.title else task_context.title

        return DetectionResult(
            detected=True,
            context={
                "feature": feature.strip(),
                "related_capability": "additional features or edge cases",
                "has_vague_language": has_vague_language,
                "has_minimal_criteria": has_minimal_criteria,
                "has_multiple_concerns": has_multiple_concerns,
            }
        )

    return None


def detect_user_ambiguity(task_context: TaskContext) -> Optional[DetectionResult]:
    """Detect if user/persona needs clarification.

    Looks for:
    - No mention of users or personas
    - Generic "users" without specificity
    - Multiple potential user types

    Args:
        task_context: Task information

    Returns:
        DetectionResult if ambiguity detected, None otherwise
    """
    text = (task_context.title + " " + task_context.description).lower()

    # User-related keywords
    user_keywords = ["user", "developer", "admin", "operator", "customer", "persona"]
    has_user_mention = any(keyword in text for keyword in user_keywords)

    # Generic "user" without specificity
    has_generic_user = "user" in text and not any(
        specific in text for specific in ["end user", "developer", "admin", "customer"]
    )

    # Multiple user types mentioned
    user_types = ["developer", "admin", "end user", "customer", "operator"]
    mentioned_types = [utype for utype in user_types if utype in text]
    has_multiple_types = len(mentioned_types) > 1

    if not has_user_mention or has_generic_user or has_multiple_types:
        return DetectionResult(
            detected=True,
            context={
                "has_user_mention": has_user_mention,
                "has_generic_user": has_generic_user,
                "mentioned_types": mentioned_types,
                "needs_persona": not has_user_mention or has_generic_user,
            }
        )

    return None


def detect_technology_choices(
    task_context: TaskContext,
    codebase_context: Optional[CodebaseContext] = None
) -> Optional[DetectionResult]:
    """Detect if technology choices need clarification.

    Looks for:
    - Multiple possible implementation approaches
    - New patterns vs existing patterns
    - Async vs sync decisions

    Args:
        task_context: Task information
        codebase_context: Optional codebase information

    Returns:
        DetectionResult if choices detected, None otherwise
    """
    text = (task_context.title + " " + task_context.description).lower()

    # Keywords suggesting implementation choices
    choice_keywords = ["implement", "add", "create", "build", "integrate"]
    has_implementation = any(keyword in text for keyword in choice_keywords)

    # Patterns that might need decisions
    pattern_keywords = ["api", "service", "handler", "processor", "manager"]
    has_pattern_concern = any(keyword in text for keyword in pattern_keywords)

    # Async indicators
    async_keywords = ["async", "background", "queue", "worker", "job"]
    has_async_concern = any(keyword in text for keyword in async_keywords)

    if has_implementation and (has_pattern_concern or has_async_concern):
        component = "component"
        if has_pattern_concern:
            # Try to extract component type
            for keyword in pattern_keywords:
                if keyword in text:
                    component = keyword
                    break

        return DetectionResult(
            detected=True,
            context={
                "component": component,
                "option_a": "Approach A (recommended)",
                "option_b": "Approach B (alternative)",
                "pattern": component if has_pattern_concern else "pattern",
                "needs_async_decision": has_async_concern,
            }
        )

    return None


def detect_integration_points(
    task_context: TaskContext,
    codebase_context: Optional[CodebaseContext] = None
) -> Optional[DetectionResult]:
    """Detect if integration points need clarification.

    Looks for:
    - Database mentions
    - External API references
    - Component interactions

    Args:
        task_context: Task information
        codebase_context: Optional codebase information

    Returns:
        DetectionResult if integration points detected, None otherwise
    """
    text = (task_context.title + " " + task_context.description).lower()

    # Database indicators
    db_keywords = ["database", "db", "table", "schema", "migration", "query"]
    has_database = any(keyword in text for keyword in db_keywords)

    # API indicators
    api_keywords = ["api", "endpoint", "rest", "graphql", "external", "third-party"]
    has_api = any(keyword in text for keyword in api_keywords)

    # Component interaction indicators
    integration_keywords = ["integrate", "connect", "interface", "interact", "communicate"]
    has_integration = any(keyword in text for keyword in integration_keywords)

    if has_database or has_api or has_integration:
        components = []
        if codebase_context and codebase_context.existing_patterns:
            components = list(codebase_context.existing_patterns.keys())

        api_name = "external service"
        # Try to extract API name from text
        if has_api:
            words = text.split()
            for i, word in enumerate(words):
                if word in ["api", "service"]:
                    if i > 0:
                        api_name = f"{words[i-1]} {word}"
                    break

        return DetectionResult(
            detected=True,
            context={
                "has_database": has_database,
                "has_api": has_api,
                "api_name": api_name,
                "components": ", ".join(components) if components else "existing components",
            }
        )

    return None


def detect_unhandled_edge_cases(task_context: TaskContext) -> Optional[DetectionResult]:
    """Detect if edge cases need clarification.

    Looks for:
    - Missing error handling discussion
    - No mention of edge cases
    - High complexity suggesting edge cases exist

    Args:
        task_context: Task information

    Returns:
        DetectionResult if edge cases need clarification, None otherwise
    """
    text = (task_context.title + " " + task_context.description).lower()

    # Error handling indicators
    error_keywords = ["error", "exception", "failure", "edge case", "invalid", "null", "empty"]
    has_error_handling = any(keyword in text for keyword in error_keywords)

    # High complexity suggests edge cases exist
    is_complex = task_context.complexity_score >= 7

    if not has_error_handling and is_complex:
        return DetectionResult(
            detected=True,
            context={
                "needs_error_handling": True,
                "complexity_suggests_edges": is_complex,
            }
        )

    return None


# =============================================================================
# QUESTION INSTANTIATION AND PRIORITIZATION
# =============================================================================

def instantiate_questions(
    templates: List[Question],
    detection_context: DetectionResult
) -> List[Question]:
    """Instantiate question templates with detection context.

    Replaces placeholders like {feature}, {component} with actual values
    from detection results.

    Args:
        templates: Question templates to instantiate
        detection_context: Context from detection

    Returns:
        List of instantiated questions
    """
    instantiated = []

    for template in templates:
        # Create a copy of the question
        question = Question(
            id=template.id,
            category=template.category,
            text=template.text,
            options=template.options[:],  # Copy list
            default=template.default,
            rationale=template.rationale,
        )

        # Replace placeholders in text
        text = question.text
        for key, value in detection_context.context.items():
            placeholder = f"{{{key}}}"
            if placeholder in text:
                text = text.replace(placeholder, str(value))
        question.text = text

        # Replace placeholders in options
        for i, option in enumerate(question.options):
            for key, value in detection_context.context.items():
                placeholder = f"{{{key}}}"
                if placeholder in option:
                    question.options[i] = option.replace(placeholder, str(value))

        # Replace placeholders in rationale
        rationale = question.rationale
        for key, value in detection_context.context.items():
            placeholder = f"{{{key}}}"
            if placeholder in rationale:
                rationale = rationale.replace(placeholder, str(value))
        question.rationale = rationale

        instantiated.append(question)

    return instantiated


def prioritize_questions(
    questions: List[Question],
    max_questions: int = 7
) -> List[Question]:
    """Prioritize and limit questions to avoid overwhelming users.

    Priority order:
    1. Scope questions (always most important)
    2. Technology questions (implementation critical)
    3. Integration questions (system-wide impact)
    4. User questions (context important)
    5. Trade-off questions (nice to have)
    6. Edge case questions (can be inferred)

    Args:
        questions: All generated questions
        max_questions: Maximum number of questions to return

    Returns:
        Prioritized and limited list of questions
    """
    # Category priority weights
    priority_weights = {
        "scope": 100,
        "technology": 90,
        "integration": 80,
        "user": 70,
        "tradeoff": 60,
        "edge_case": 50,
    }

    # Sort by priority
    sorted_questions = sorted(
        questions,
        key=lambda q: priority_weights.get(q.category, 0),
        reverse=True
    )

    # Limit to max_questions
    return sorted_questions[:max_questions]


# =============================================================================
# MAIN GENERATOR FUNCTION
# =============================================================================

def generate_planning_questions(
    task_context: TaskContext,
    complexity_score: Optional[int] = None,
    codebase_context: Optional[CodebaseContext] = None,
    mode: ClarificationMode = ClarificationMode.FULL
) -> List[Question]:
    """Generate clarifying questions for task-work Phase 1.5.

    Uses detection functions to identify ambiguities, then generates
    contextualized questions from templates. Applies the 5W1H framework
    systematically.

    Args:
        task_context: Task information
        complexity_score: Optional complexity override (uses task_context.complexity_score if None)
        codebase_context: Optional codebase information for advanced detection
        mode: Clarification mode (FULL, QUICK, SKIP, USE_DEFAULTS)

    Returns:
        List of prioritized questions (max 7)

    Examples:
        >>> task = TaskContext(
        ...     task_id="TASK-001",
        ...     title="Add user authentication",
        ...     description="Implement login and registration",
        ...     complexity_score=6
        ... )
        >>> questions = generate_planning_questions(task)
        >>> len(questions) <= 7
        True
        >>> any(q.category == "scope" for q in questions)
        True
    """
    # Handle skip/defaults modes
    if mode == ClarificationMode.SKIP:
        return []

    # Use complexity from task_context if not overridden
    if complexity_score is None:
        complexity_score = task_context.complexity_score

    questions = []

    # 1. Scope Questions (What) - always check
    if scope_result := detect_scope_ambiguity(task_context):
        questions.extend(
            instantiate_questions(SCOPE_QUESTIONS, scope_result)
        )

    # 2. User Questions (Who) - if user ambiguity detected
    if user_result := detect_user_ambiguity(task_context):
        questions.extend(
            instantiate_questions(USER_QUESTIONS, user_result)
        )

    # 3. Technology Questions (How) - if choices detected
    if tech_result := detect_technology_choices(task_context, codebase_context):
        questions.extend(
            instantiate_questions(TECHNOLOGY_QUESTIONS, tech_result)
        )

    # 4. Integration Questions (Where) - if integration points detected
    if integration_result := detect_integration_points(task_context, codebase_context):
        questions.extend(
            instantiate_questions(INTEGRATION_QUESTIONS, integration_result)
        )

    # 5. Trade-off Questions (Why) - only for medium+ complexity
    if complexity_score >= 5:
        # Trade-off questions don't need context, use them directly
        questions.extend(TRADEOFF_QUESTIONS)

    # 6. Edge Case Questions - only for complex tasks
    if complexity_score >= 7:
        if edge_result := detect_unhandled_edge_cases(task_context):
            questions.extend(
                instantiate_questions(EDGE_CASE_QUESTIONS, edge_result)
            )

    # Adjust max questions based on mode
    max_questions = 3 if mode == ClarificationMode.QUICK else 7

    # Prioritize and limit
    return prioritize_questions(questions, max_questions=max_questions)
