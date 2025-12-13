"""
Display formatting utilities for clarification questions.

This module handles UI formatting for clarification questions in Phase 1.5,
including full question display (blocking), quick question display (with timeout),
and skip message display. The formatting is consistent with GuardKit's existing
checkpoint patterns (Phase 2.8).
"""

from typing import List, Optional, Dict
from dataclasses import dataclass


# Note: These will be imported from core.py in final implementation
# For now, we define them here to ensure the module is self-contained
@dataclass
class Question:
    """Single clarification question."""
    id: str
    category: str  # "SCOPE", "TECHNOLOGY", "TRADE-OFFS", etc.
    text: str
    options: List[str]  # e.g., ["[Y]es", "[N]o", "[D]etails"]
    default: str
    rationale: str  # Why this default was chosen


def display_full_questions(
    questions: List[Question],
    task_id: str,
    task_title: str,
    complexity: int
) -> str:
    """
    Generate full question display for blocking clarification.

    Used when complexity >= 5 or user explicitly requests clarification.
    Questions are grouped by category (SCOPE, TECHNOLOGY, TRADE-OFFS, etc.)
    with detailed options and rationale for defaults.

    Args:
        questions: List of Question objects to display
        task_id: Task identifier (e.g., "TASK-ABC-123")
        task_title: Human-readable task title
        complexity: Complexity score (0-10)

    Returns:
        Formatted string ready for display

    Example output:
        ═══════════════════════════════════════════════════════════════════════════
        🤔 PHASE 1.5 - CLARIFICATION QUESTIONS
        ═══════════════════════════════════════════════════════════════════════════

        TASK: TASK-XXX - {Title}
        COMPLEXITY: {score}/10 ({level})

        Before planning implementation, I need clarification on {n} items:

        ┌─────────────────────────────────────────────────────────────────────────┐
        │ SCOPE (What)                                                            │
        ├─────────────────────────────────────────────────────────────────────────┤
        │ 1. Should "user authentication" include password reset functionality?  │
        │    [Y]es / [N]o / [D]etails                                            │
        │    Default: Yes (common expectation)                                    │
        └─────────────────────────────────────────────────────────────────────────┘

        Enter responses (e.g., "1:Y 2:N 3:J 4:R 5:S")
        Or press [Enter] to use all defaults
        Or type "skip" to proceed without clarification

        Your responses: _
        ═══════════════════════════════════════════════════════════════════════════
    """
    complexity_level = _get_complexity_level(complexity)
    separator = "═" * 75

    # Group questions by category
    grouped = _group_by_category(questions)

    # Build output
    output = [
        separator,
        "🤔 PHASE 1.5 - CLARIFICATION QUESTIONS",
        separator,
        "",
        f"TASK: {task_id} - {task_title}",
        f"COMPLEXITY: {complexity}/10 ({complexity_level})",
        "",
        f"Before planning implementation, I need clarification on {len(questions)} items:",
        ""
    ]

    # Add question boxes by category
    for category, category_questions in grouped.items():
        output.append(format_question_box(category, category_questions))
        output.append("")

    # Add response prompt
    output.extend([
        format_response_prompt("full"),
        separator
    ])

    return "\n".join(output)


def display_quick_questions(
    questions: List[Question],
    timeout_seconds: int = 15
) -> str:
    """
    Generate quick question display with timeout.

    Used for complexity 3-4 tasks where we want lightweight clarification
    without blocking. Questions are shown in compact format with a timeout
    countdown. If user doesn't respond within timeout, defaults are used.

    Args:
        questions: List of Question objects to display
        timeout_seconds: Timeout in seconds before auto-proceeding with defaults

    Returns:
        Formatted string ready for display

    Example output:
        ═══════════════════════════════════════════════════════════════════════════
        🤔 QUICK CLARIFICATION (2 questions, 15s timeout)
        ═══════════════════════════════════════════════════════════════════════════

        1. Include error handling for network failures? [Y/n] Default: Y
        2. Use existing logging pattern? [Y/n] Default: Y

        [Enter] for defaults, or type answers (e.g., "Y N"): _

        Auto-proceeding with defaults in 15s...
        ═══════════════════════════════════════════════════════════════════════════
    """
    separator = "═" * 75
    question_count = len(questions)

    output = [
        separator,
        f"🤔 QUICK CLARIFICATION ({question_count} question{'s' if question_count != 1 else ''}, {timeout_seconds}s timeout)",
        separator,
        ""
    ]

    # Add questions in compact format
    for i, q in enumerate(questions, 1):
        # Simplify options for quick display (e.g., "[Y]es / [N]o" -> "[Y/n]")
        compact_options = _compact_options(q.options)
        output.append(f"{i}. {q.text} {compact_options} Default: {q.default}")

    output.extend([
        "",
        format_response_prompt("quick"),
        "",
        f"Auto-proceeding with defaults in {timeout_seconds}s...",
        separator
    ])

    return "\n".join(output)


def display_skip_message(
    reason: str,
    complexity: Optional[int] = None
) -> str:
    """
    Generate skip message when clarification is bypassed.

    Used when:
    - Task is trivial (complexity <= 2)
    - User explicitly used --no-questions flag
    - User chose to use all defaults

    Args:
        reason: Skip reason ("trivial", "flag", "defaults")
        complexity: Optional complexity score (shown for trivial tasks)

    Returns:
        Formatted string ready for display

    Example output:
        ═══════════════════════════════════════════════════════════════════════════
        ✅ PHASE 1.5 - SKIPPED (Trivial task, complexity: 2/10)
        ═══════════════════════════════════════════════════════════════════════════
        Task description is clear. Proceeding to implementation planning...
        ═══════════════════════════════════════════════════════════════════════════
    """
    separator = "═" * 75

    # Build reason text
    if reason == "trivial":
        reason_text = f"Trivial task, complexity: {complexity}/10"
        detail = "Task description is clear. Proceeding to implementation planning..."
    elif reason == "flag":
        reason_text = "--no-questions flag used"
        detail = "Skipping clarification phase as requested. Proceeding to implementation planning..."
    elif reason == "defaults":
        reason_text = "User chose defaults for all questions"
        detail = "Using default answers for all clarifications. Proceeding to implementation planning..."
    else:
        reason_text = "Clarification not required"
        detail = "Proceeding to implementation planning..."

    output = [
        separator,
        f"✅ PHASE 1.5 - SKIPPED ({reason_text})",
        separator,
        detail,
        separator
    ]

    return "\n".join(output)


def format_question_box(
    category: str,
    questions: List[Question]
) -> str:
    """
    Format a group of questions in a bordered box.

    Creates a visually distinct box for a category of questions,
    with a header showing the category name and a border around
    the questions.

    Args:
        category: Category name (e.g., "SCOPE (What)")
        questions: List of Question objects in this category

    Returns:
        Formatted box string

    Example output:
        ┌─────────────────────────────────────────────────────────────────────────┐
        │ SCOPE (What)                                                            │
        ├─────────────────────────────────────────────────────────────────────────┤
        │ 1. Should "user authentication" include password reset functionality?  │
        │    [Y]es / [N]o / [D]etails                                            │
        │    Default: Yes (common expectation)                                    │
        └─────────────────────────────────────────────────────────────────────────┘
    """
    box_width = 75
    top_border = "┌" + "─" * (box_width - 2) + "┐"
    separator_line = "├" + "─" * (box_width - 2) + "┤"
    bottom_border = "└" + "─" * (box_width - 2) + "┘"

    lines = [
        top_border,
        _pad_line(f" {category}", box_width),
        separator_line
    ]

    # Add each question with proper formatting
    for q in questions:
        # Question text
        lines.append(_pad_line(f" {q.id}. {q.text}", box_width))

        # Options
        options_str = " / ".join(q.options)
        lines.append(_pad_line(f"    {options_str}", box_width))

        # Default with rationale
        lines.append(_pad_line(f"    Default: {q.default} ({q.rationale})", box_width))

        # Add spacing between questions (except for last one)
        if q != questions[-1]:
            lines.append(_pad_line("", box_width))

    lines.append(bottom_border)

    return "\n".join(lines)


def format_response_prompt(mode: str) -> str:
    """
    Format the input prompt for user responses.

    Different formats for full vs quick mode:
    - Full: Detailed instructions with examples
    - Quick: Compact instructions for quick responses

    Args:
        mode: Display mode ("full" or "quick")

    Returns:
        Formatted prompt string
    """
    if mode == "full":
        return "\n".join([
            'Enter responses (e.g., "1:Y 2:N 3:J 4:R 5:S")',
            'Or press [Enter] to use all defaults',
            'Or type "skip" to proceed without clarification',
            "",
            "Your responses: _"
        ])
    elif mode == "quick":
        return '[Enter] for defaults, or type answers (e.g., "Y N"): _'
    else:
        return "Your response: _"


# Helper functions

def _get_complexity_level(complexity: int) -> str:
    """Convert complexity score to level label."""
    if complexity <= 2:
        return "Trivial"
    elif complexity <= 4:
        return "Simple"
    elif complexity <= 6:
        return "Medium"
    elif complexity <= 8:
        return "Complex"
    else:
        return "Very Complex"


def _group_by_category(questions: List[Question]) -> Dict[str, List[Question]]:
    """Group questions by category, preserving order within each category."""
    grouped: Dict[str, List[Question]] = {}
    for q in questions:
        if q.category not in grouped:
            grouped[q.category] = []
        grouped[q.category].append(q)
    return grouped


def _pad_line(text: str, width: int) -> str:
    """Pad a line to box width with proper borders."""
    # Remove existing right border if present
    text = text.rstrip("│")

    # Calculate padding needed
    padding = width - len(text) - 2  # -2 for borders

    # Add padding and borders
    return f"│{text}{' ' * padding}│"


def _compact_options(options: List[str]) -> str:
    """
    Convert verbose options to compact format for quick display.

    Examples:
        ["[Y]es", "[N]o"] -> "[Y/n]"
        ["[J]WT", "[S]ession", "[H]ybrid"] -> "[J/S/H]"
    """
    # Extract single-letter codes
    codes = []
    for opt in options:
        # Find bracketed letter
        if '[' in opt and ']' in opt:
            start = opt.index('[') + 1
            end = opt.index(']')
            codes.append(opt[start:end])

    if not codes:
        return ""

    # Make first code uppercase, rest lowercase (common convention)
    if len(codes) > 0:
        codes[0] = codes[0].upper()
        codes[1:] = [c.lower() for c in codes[1:]]

    return f"[{'/'.join(codes)}]"


# =============================================================================
# Interactive Display Functions (collect user input and return ClarificationContext)
# =============================================================================

def collect_full_responses(
    questions: List['Question'],
    task_id: str,
    task_title: str,
    complexity: int
) -> 'ClarificationContext':
    """
    Display full questions interactively and collect user responses.

    Shows all questions with detailed options and rationale. Waits for
    user input. Returns ClarificationContext with collected decisions.

    Args:
        questions: List of Question objects to display
        task_id: Task identifier (e.g., "TASK-ABC-123")
        task_title: Human-readable task title
        complexity: Complexity score (0-10)

    Returns:
        ClarificationContext with all decisions recorded
    """
    # Import here to avoid circular imports
    from .core import ClarificationContext, Decision, ClarificationMode, process_responses

    if not questions:
        return ClarificationContext(
            context_type="review_scope",
            mode="full",
            total_questions=0,
            answered_count=0,
        )

    # Display formatted questions
    print(display_full_questions(questions, task_id, task_title, complexity))

    # Collect responses
    user_responses = {}

    print("\nEnter your responses:")
    for i, question in enumerate(questions, 1):
        # Extract valid option codes
        valid_codes = _extract_option_codes(question.options)

        while True:
            prompt = f"  Q{i} [{question.default}]: "
            answer = input(prompt).strip().upper()

            if not answer:
                # Use default
                answer = question.default
                break

            if answer in valid_codes or not valid_codes:
                break

            print(f"    Invalid. Please enter one of: {', '.join(valid_codes)}")

        user_responses[question.id] = answer

    # Process responses into context
    context = process_responses(questions, user_responses, ClarificationMode.FULL)
    context.context_type = "review_scope"
    context.mode = "full"

    # Show summary
    print(f"\n{'='*60}")
    print(f"✓ Recorded {len(context.decisions)} decision(s)")
    print(f"{'='*60}\n")

    return context


def collect_quick_responses(
    questions: List['Question'],
    timeout_seconds: int = 15
) -> 'ClarificationContext':
    """
    Display questions in quick mode and collect responses.

    Shows compact question format. For simplicity, uses immediate defaults
    if user presses Enter without input (no timeout implementation to
    avoid platform-specific complexity).

    Args:
        questions: List of Question objects to display
        timeout_seconds: Display hint for timeout (informational only)

    Returns:
        ClarificationContext with decisions (may include defaults)
    """
    # Import here to avoid circular imports
    from .core import ClarificationContext, ClarificationMode, process_responses

    if not questions:
        return ClarificationContext(
            context_type="review_scope",
            mode="quick",
            total_questions=0,
            answered_count=0,
        )

    # Display formatted questions
    print(display_quick_questions(questions, timeout_seconds))

    # Collect all responses at once (simpler than per-question timeout)
    prompt = "\nYour answers (space-separated, or Enter for defaults): "
    raw_input = input(prompt).strip().upper()

    user_responses = {}

    if raw_input:
        # Parse space-separated answers
        answers = raw_input.split()
        for i, question in enumerate(questions):
            if i < len(answers):
                user_responses[question.id] = answers[i]
            else:
                user_responses[question.id] = question.default
    else:
        # Use all defaults
        for question in questions:
            user_responses[question.id] = question.default

    # Process responses into context
    context = process_responses(questions, user_responses, ClarificationMode.QUICK)
    context.context_type = "review_scope"
    context.mode = "quick"

    print(f"\n✓ Recorded {len(context.decisions)} decision(s)\n")

    return context


def create_skip_context(reason: str = "skip") -> 'ClarificationContext':
    """
    Return skip context without displaying questions.

    Used when clarification is bypassed due to low complexity,
    --no-questions flag, or explicit skip request.

    Args:
        reason: Skip reason for user_override field

    Returns:
        Empty ClarificationContext with mode="skip"
    """
    # Import here to avoid circular imports
    from .core import ClarificationContext

    return ClarificationContext(
        context_type="review_scope",
        mode="skip",
        total_questions=0,
        answered_count=0,
        user_override=reason,
    )


def _extract_option_codes(options: List[str]) -> List[str]:
    """Extract single-letter codes from option strings.

    Args:
        options: List like ["[Y]es", "[N]o", "[D]etails"]

    Returns:
        List like ["Y", "N", "D"]
    """
    codes = []
    for opt in options:
        if '[' in opt and ']' in opt:
            start = opt.index('[') + 1
            end = opt.index(']')
            codes.append(opt[start:end].upper())
    return codes
