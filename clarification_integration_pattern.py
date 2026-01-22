#!/usr/bin/env python3
"""
Complete clarification integration pattern for /task-work Phase 1.6.

This file shows how to integrate clarification into the task-work command.
Copy-paste the relevant sections into your command implementation.
"""

import sys
from pathlib import Path
from typing import Dict, Any, Optional

# Add library paths
sys.path.insert(0, '/Users/richardwoollcott/.agentecflow/lib')
sys.path.insert(0, '/Users/richardwoollcott/Projects/appmilla_github/guardkit/installer/core/commands/lib')

from clarification.core import (
    ClarificationContext,
    ClarificationMode,
    should_clarify,
    format_for_prompt,
    parse_frontmatter,
)
from clarification.generators.planning_generator import (
    generate_planning_questions,
    TaskContext,
    CodebaseContext,
)
from clarification.display import (
    collect_full_responses,
    collect_quick_responses,
    create_skip_context,
    display_skip_message,
)


# =============================================================================
# PATTERN 1: Complete Execute Function (Recommended)
# =============================================================================

def execute_clarification(
    context_type: str,
    task_id: str,
    task_title: str,
    complexity: int,
    flags: Dict[str, Any],
    **context_kwargs
) -> ClarificationContext:
    """Execute clarification workflow for given context type.

    This is the complete, production-ready implementation.
    Use this pattern for new commands.

    Args:
        context_type: "review_scope", "implementation_prefs", or "implementation_planning"
        task_id: Task identifier (e.g., "TASK-ABC-123")
        task_title: Human-readable task title
        complexity: Complexity score (0-10)
        flags: Command-line flags dict
        **context_kwargs: Context-specific arguments

    Returns:
        ClarificationContext with collected decisions

    Example:
        >>> flags = {"no_questions": False, "with_questions": False}
        >>> ctx = execute_clarification(
        ...     context_type="implementation_planning",
        ...     task_id="TASK-001",
        ...     task_title="Add user auth",
        ...     complexity=4,
        ...     flags=flags,
        ...     task_context={"description": "...", "acceptance_criteria": []}
        ... )
        >>> ctx.context_type
        'implementation_planning'
    """
    # Step 1: Check for saved clarification (unless --reclarify)
    if not flags.get("reclarify"):
        task_path = find_task_path(task_id)
        if task_path:
            saved = ClarificationContext.load_from_frontmatter(task_path)
            if saved and saved.context_type == context_type:
                print(f"✓ Using saved clarification from {saved.timestamp}")
                return saved

    # Step 2: Determine clarification mode
    context_map = {
        "review_scope": "review",
        "implementation_prefs": "implement_prefs",
        "implementation_planning": "planning",
    }
    mode = should_clarify(
        context_type=context_map[context_type],
        complexity=complexity,
        flags=flags
    )

    # Step 3: Handle skip/defaults modes
    if mode == ClarificationMode.SKIP:
        reason = "flag" if flags.get("no_questions") else "trivial"
        print(display_skip_message(reason, complexity))
        return create_skip_context(reason)

    # Step 4: Generate questions based on context type
    questions = generate_questions_for_context(
        context_type, complexity, context_kwargs
    )

    if not questions:
        print(display_skip_message("no_questions_needed"))
        return create_skip_context("no_questions_needed")

    # Step 5: Handle --answers flag (inline answers)
    if flags.get("answers"):
        responses = parse_inline_answers(flags["answers"], questions)
        from clarification.core import process_responses
        context = process_responses(questions, responses, mode)
        context.context_type = context_type
        context.user_override = "inline_answers"
        return context

    # Step 6: Handle --defaults flag
    if mode == ClarificationMode.USE_DEFAULTS:
        context = apply_defaults_to_questions(questions)
        context.context_type = context_type
        return context

    # Step 7: Collect responses based on mode
    if mode == ClarificationMode.QUICK:
        context = collect_quick_responses(questions, timeout_seconds=15)
    else:  # FULL
        context = collect_full_responses(questions, task_id, task_title, complexity)

    context.context_type = context_type

    # Step 8: Persist to task frontmatter
    task_path = find_task_path(task_id)
    if task_path:
        context.persist_to_frontmatter(task_path)

    return context


# =============================================================================
# PATTERN 2: Helper Functions
# =============================================================================

def generate_questions_for_context(
    context_type: str,
    complexity: int,
    context_kwargs: Dict[str, Any]
) -> list:
    """Generate questions based on context type.

    Args:
        context_type: Which context to use
        complexity: Task complexity score
        context_kwargs: Context-specific arguments

    Returns:
        List of Question objects
    """
    if context_type == "review_scope":
        from clarification.generators.review_generator import generate_review_questions
        return generate_review_questions(
            task_context=context_kwargs.get("task_context", {}),
            review_mode=context_kwargs.get("review_mode", "architectural"),
            complexity=complexity
        )

    elif context_type == "implementation_prefs":
        from clarification.generators.implement_generator import generate_implement_questions
        return generate_implement_questions(
            review_findings=context_kwargs.get("review_findings", {}),
            num_subtasks=context_kwargs.get("num_subtasks", 1),
            complexity=complexity
        )

    elif context_type == "implementation_planning":
        task_context = context_kwargs.get("task_context")
        if isinstance(task_context, dict):
            task_context = TaskContext(
                task_id=task_context.get("task_id", "TASK-XXX"),
                title=task_context.get("title", ""),
                description=task_context.get("description", ""),
                acceptance_criteria=task_context.get("acceptance_criteria", []),
                complexity_score=complexity
            )

        return generate_planning_questions(
            task_context=task_context,
            complexity_score=complexity,
            codebase_context=context_kwargs.get("codebase_context"),
            mode=ClarificationMode.FULL
        )

    return []


def find_task_path(task_id: str) -> Optional[Path]:
    """Find task file path across all state directories.

    Args:
        task_id: Task identifier (e.g., "TASK-ABC-123")

    Returns:
        Path to task file if found, None otherwise
    """
    base = Path.cwd() / "tasks"
    for state in ["in_progress", "backlog", "blocked", "in_review"]:
        pattern = f"{task_id}*.md"
        matches = list((base / state).glob(pattern))
        if matches:
            return matches[0]
    return None


def parse_inline_answers(answers_str: str, questions: list) -> dict:
    """Parse --answers="1:Y 2:N 3:JWT" into responses dict.

    Args:
        answers_str: Space-separated "question_num:answer" pairs
        questions: List of Question objects

    Returns:
        Dict mapping question_id to answer

    Example:
        >>> questions = [Question(id="q1", ...), Question(id="q2", ...)]
        >>> parse_inline_answers("1:Y 2:N", questions)
        {'q1': 'Y', 'q2': 'N'}
    """
    responses = {}
    pairs = answers_str.split()

    for pair in pairs:
        if ':' in pair:
            num_str, answer = pair.split(':', 1)
            try:
                idx = int(num_str) - 1  # Convert to 0-indexed
                if 0 <= idx < len(questions):
                    responses[questions[idx].id] = answer.upper()
            except ValueError:
                # Treat as question_id
                responses[num_str] = answer.upper()

    # Fill remaining with defaults
    for q in questions:
        if q.id not in responses:
            responses[q.id] = q.default

    return responses


def apply_defaults_to_questions(questions: list) -> ClarificationContext:
    """Apply defaults without prompting.

    Args:
        questions: List of Question objects

    Returns:
        ClarificationContext with all defaults applied
    """
    from clarification.core import process_responses
    responses = {q.id: q.default for q in questions}
    context = process_responses(questions, responses, ClarificationMode.USE_DEFAULTS)
    context.user_override = "defaults"
    return context


# =============================================================================
# PATTERN 3: Inline Integration (Minimal)
# =============================================================================

def minimal_integration_example(task_id: str, task_context: dict, flags: dict):
    """Minimal clarification integration - use in existing commands.

    This is the smallest integration pattern. Use when you need to add
    clarification to an existing command quickly.

    Args:
        task_id: Task identifier
        task_context: Task information dict
        flags: Command-line flags
    """
    from clarification.core import should_clarify
    from clarification.generators.planning_generator import generate_planning_questions, TaskContext
    from clarification.display import collect_quick_responses

    # Determine mode
    complexity = task_context.get("complexity", 5)
    mode = should_clarify("planning", complexity, flags)

    if mode == ClarificationMode.SKIP:
        # Skip clarification
        clarification = None
    else:
        # Generate and collect
        task_ctx = TaskContext(
            task_id=task_id,
            title=task_context["title"],
            description=task_context["description"],
            acceptance_criteria=task_context.get("acceptance_criteria", []),
            complexity_score=complexity
        )
        questions = generate_planning_questions(task_ctx, complexity)

        if mode == ClarificationMode.QUICK:
            clarification = collect_quick_responses(questions)
        else:
            from clarification.display import collect_full_responses
            clarification = collect_full_responses(
                questions, task_id, task_context["title"], complexity
            )

        clarification.context_type = "implementation_planning"

    # Use in prompt
    if clarification and clarification.has_explicit_decisions:
        from clarification.core import format_for_prompt
        prompt_context = format_for_prompt(clarification)
        # Add to Phase 2 prompt
        phase_2_prompt = f"""
        {prompt_context}

        Plan implementation for {task_id}...
        """
    else:
        # No clarification context
        phase_2_prompt = f"Plan implementation for {task_id}..."

    return clarification


# =============================================================================
# PATTERN 4: Integration into /task-work Command
# =============================================================================

def task_work_phase_1_6_example(task_id: str, task_context: dict, cmd_flags: dict):
    """Example of Phase 1.6 integration in /task-work command.

    This shows where to insert clarification in the existing workflow.

    Args:
        task_id: Task identifier
        task_context: Task information from Phase 1.5
        cmd_flags: Command-line flags

    Returns:
        Tuple of (clarification_context, phase_2_prompt_addition)
    """
    print("\n" + "="*80)
    print("PHASE 1.6 - CLARIFICATION")
    print("="*80 + "\n")

    # Execute clarification
    clarification = execute_clarification(
        context_type="implementation_planning",
        task_id=task_id,
        task_title=task_context["title"],
        complexity=task_context.get("complexity", 5),
        flags=cmd_flags,
        task_context=task_context,
    )

    # Format for Phase 2
    if clarification.has_explicit_decisions:
        prompt_addition = f"""
CLARIFICATION CONTEXT:
{format_for_prompt(clarification)}

Based on these explicit decisions and assumed defaults, plan implementation...
"""
    else:
        prompt_addition = ""

    print(f"✓ Clarification complete ({len(clarification.decisions)} decisions)\n")

    return clarification, prompt_addition


# =============================================================================
# PATTERN 5: Error Handling (Fail-Safe)
# =============================================================================

def safe_clarification_wrapper(
    context_type: str,
    task_id: str,
    task_title: str,
    complexity: int,
    flags: Dict[str, Any],
    **context_kwargs
) -> ClarificationContext:
    """Fail-safe clarification execution - never blocks workflow.

    This wrapper ensures that clarification errors NEVER fail the task.
    Use this pattern for production commands.

    Args:
        Same as execute_clarification()

    Returns:
        ClarificationContext (empty if error occurred)
    """
    try:
        return execute_clarification(
            context_type=context_type,
            task_id=task_id,
            task_title=task_title,
            complexity=complexity,
            flags=flags,
            **context_kwargs
        )
    except Exception as e:
        print(f"⚠️  Clarification error: {e}")
        print("   Continuing with workflow (no clarification context)")

        # Return empty context - workflow continues
        return ClarificationContext(
            context_type=context_type,
            mode="skip",
            total_questions=0,
            answered_count=0,
            user_override="error",
        )


# =============================================================================
# PATTERN 6: Resume Support
# =============================================================================

def clarification_with_resume(
    task_id: str,
    context_type: str,
    complexity: int,
    flags: Dict[str, Any],
    **context_kwargs
) -> ClarificationContext:
    """Execute clarification with automatic resume support.

    Checks for saved clarification in task frontmatter. If found and
    --reclarify flag is not set, uses saved decisions. Otherwise,
    executes fresh clarification.

    Args:
        task_id: Task identifier
        context_type: Context type
        complexity: Complexity score
        flags: Command flags (must include reclarify)
        **context_kwargs: Context-specific arguments

    Returns:
        ClarificationContext (loaded or fresh)
    """
    # Check for saved clarification
    task_path = find_task_path(task_id)
    if task_path and not flags.get("reclarify", False):
        saved = ClarificationContext.load_from_frontmatter(task_path)
        if saved and saved.context_type == context_type:
            print(f"✓ Using saved clarification from {saved.timestamp.isoformat()}")
            return saved

    # No saved clarification or --reclarify flag set
    print("Executing fresh clarification...")
    return execute_clarification(
        context_type=context_type,
        task_id=task_id,
        task_title=context_kwargs.get("task_title", ""),
        complexity=complexity,
        flags=flags,
        **context_kwargs
    )


# =============================================================================
# USAGE EXAMPLES
# =============================================================================

def example_usage_full():
    """Example: Full clarification execution."""
    print("EXAMPLE 1: Full Clarification Execution\n")

    flags = {
        "no_questions": False,
        "with_questions": False,
        "defaults": False,
        "answers": None,
        "reclarify": False,
    }

    task_context = {
        "task_id": "TASK-EXAMPLE-001",
        "title": "Add user authentication",
        "description": "Implement login and registration",
        "acceptance_criteria": [
            "Users can log in with email/password",
            "Users can register new accounts",
            "Failed login attempts are logged",
        ],
        "complexity": 6,
    }

    context = execute_clarification(
        context_type="implementation_planning",
        task_id=task_context["task_id"],
        task_title=task_context["title"],
        complexity=task_context["complexity"],
        flags=flags,
        task_context=task_context,
    )

    print(f"Result: {len(context.decisions)} decisions")
    print(f"Mode: {context.mode}")


def example_usage_inline_answers():
    """Example: Inline answers for automation."""
    print("EXAMPLE 2: Inline Answers (Automation)\n")

    flags = {
        "no_questions": False,
        "answers": "1:Y 2:A 3:S",  # Inline answers
    }

    context = execute_clarification(
        context_type="implementation_planning",
        task_id="TASK-AUTO-001",
        task_title="Automated task",
        complexity=4,
        flags=flags,
        task_context={
            "description": "Test automation",
            "acceptance_criteria": [],
        }
    )

    print(f"Result: {context.user_override}")


def example_usage_skip():
    """Example: Skip clarification for trivial task."""
    print("EXAMPLE 3: Skip Clarification (Trivial)\n")

    flags = {"no_questions": False}

    context = execute_clarification(
        context_type="implementation_planning",
        task_id="TASK-TRIVIAL-001",
        task_title="Fix typo",
        complexity=1,  # Trivial
        flags=flags,
        task_context={
            "description": "Fix typo in README",
            "acceptance_criteria": [],
        }
    )

    print(f"Result: {context.mode}")  # Should be "skip"


if __name__ == "__main__":
    print("="*80)
    print("CLARIFICATION INTEGRATION PATTERNS")
    print("="*80 + "\n")

    print("This file demonstrates 6 integration patterns:\n")
    print("1. Complete Execute Function (Recommended)")
    print("2. Helper Functions")
    print("3. Inline Integration (Minimal)")
    print("4. Integration into /task-work Command")
    print("5. Error Handling (Fail-Safe)")
    print("6. Resume Support\n")

    print("Run examples:")
    print("  python3 clarification_integration_pattern.py\n")

    # Uncomment to run examples:
    # example_usage_full()
    # example_usage_inline_answers()
    # example_usage_skip()
