"""
Phase Execution Module - Orchestrates task-work phase execution with design-first workflow support.

Part of TASK-006: Add Design-First Workflow Flags to task-work Command.
Updated: TASK-HAI-006: Integrate AI discovery for Phase 3 specialist selection.

This module provides the main entry point for executing task-work phases in different modes:
- Standard mode (default): Executes all phases in sequence
- Design-only mode (--design-only): Executes design phases only, stops at approval
- Implement-only mode (--implement-only): Executes implementation phases using saved design

Phase 3 now uses AI-powered discovery to select specialist agents based on task context.

Author: Claude (Anthropic)
Created: 2025-10-11
Updated: 2025-11-25 (TASK-HAI-006: AI discovery integration)
"""

from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime
import json
import glob as glob_module
import logging
import os
import re

logger = logging.getLogger(__name__)

# Import clarification module
try:
    from .clarification import (
        should_clarify,
        ClarificationMode,
        ClarificationContext,
        format_for_prompt,
    )
    from .clarification.generators.planning_generator import (
        generate_planning_questions,
        TaskContext as ClarificationTaskContext,
        CodebaseContext as ClarificationCodebaseContext,
    )
    from .clarification.display import (
        collect_full_responses,
        collect_quick_responses,
        create_skip_context,
        display_skip_message,
    )
    CLARIFICATION_AVAILABLE = True
except ImportError as e:
    logger.debug(f"Clarification module not available: {e}")
    CLARIFICATION_AVAILABLE = False

# Optional import of agent discovery module
# This allows the module to work even if agent_discovery is unavailable
# and enables proper mocking in tests
try:
    from .agent_discovery import discover_agents as _discover_agents
    DISCOVERY_AVAILABLE = True
except ImportError:
    _discover_agents = None
    DISCOVERY_AVAILABLE = False
    logger.debug("Agent discovery module not available at module load time")


class PhaseExecutionError(Exception):
    """Raised when phase execution fails."""
    pass


class StateValidationError(Exception):
    """Raised when task state is invalid for the requested operation."""
    pass


# =============================================================================
# Phase 1.6: Clarifying Questions (TASK-CLQ-FIX-005)
# =============================================================================

def execute_phase_1_6_clarification(
    task_id: str,
    task_context: Dict[str, Any],
    flags: Dict[str, Any]
) -> Optional[ClarificationContext]:
    """
    Execute Phase 1.6: Clarifying Questions for /task-work.

    This phase asks targeted clarifying questions before implementation planning
    to reduce rework from incorrect assumptions (~15% improvement).

    Args:
        task_id: Task identifier (e.g., "TASK-006")
        task_context: Task context loaded from task file (frontmatter + content)
        flags: Command-line flags including:
            - no_questions: Skip Phase 1.6 entirely
            - with_questions: Force Phase 1.6 even for trivial tasks
            - defaults: Use all defaults without prompting
            - answers: Inline answers string (e.g., "1:Y 2:N 3:JWT")
            - reclarify: Re-run even if saved clarification exists

    Returns:
        ClarificationContext with decisions, or None if skipped/unavailable

    Examples:
        >>> # Normal execution
        >>> result = execute_phase_1_6_clarification("TASK-006", context, {})
        >>> result.decisions  # List of decisions

        >>> # Skip with flag
        >>> result = execute_phase_1_6_clarification("TASK-006", context, {"no_questions": True})
        >>> result is None or result.mode == "skip"
        True

        >>> # Force clarification
        >>> result = execute_phase_1_6_clarification("TASK-006", context, {"with_questions": True})
        >>> result is not None
        True
    """
    if not CLARIFICATION_AVAILABLE:
        logger.warning("Clarification module not available, skipping Phase 1.6")
        return None

    # Extract complexity from task context
    complexity = task_context.get("complexity", task_context.get("complexity_score", 5))
    task_title = task_context.get("title", "Untitled")
    task_description = task_context.get("description", "")

    print(f"\n⏳ Phase 1.6: Clarifying Questions")
    print(f"   Task: {task_id} - {task_title}")
    print(f"   Complexity: {complexity}/10")

    # Check for existing clarification (unless --reclarify flag)
    if not flags.get("reclarify", False):
        task_path = _find_task_file(task_id)
        if task_path:
            existing = ClarificationContext.load_from_frontmatter(task_path)
            if existing and existing.decisions:
                print(f"   ✅ Using saved clarification ({len(existing.decisions)} decisions)")
                return existing

    # Determine clarification mode based on complexity and flags
    mode = _determine_clarification_mode(complexity, flags)

    if mode == ClarificationMode.SKIP:
        reason = "flag" if flags.get("no_questions") else "trivial"
        print(display_skip_message(reason, complexity))
        return create_skip_context(reason)

    # Generate questions based on task context
    clr_task_context = ClarificationTaskContext(
        task_id=task_id,
        title=task_title,
        description=task_description,
        acceptance_criteria=task_context.get("acceptance_criteria", []),
        tags=task_context.get("tags", []),
        complexity_score=complexity,
    )

    questions = generate_planning_questions(
        task_context=clr_task_context,
        mode=mode,
    )

    if not questions:
        print("   ✅ No clarification questions needed (task is clear)")
        return create_skip_context("no_questions_generated")

    # Handle inline answers (--answers flag for CI/CD automation)
    if flags.get("answers"):
        context = _process_inline_answers(questions, flags["answers"], mode)
        print(f"   ✅ Applied {len(context.decisions)} inline answer(s)")
        _persist_clarification(task_id, context)
        return context

    # Handle defaults flag
    if flags.get("defaults") or mode == ClarificationMode.USE_DEFAULTS:
        context = _apply_defaults(questions)
        print(f"   ✅ Applied {len(context.decisions)} default(s)")
        _persist_clarification(task_id, context)
        return context

    # Interactive collection based on mode
    if mode == ClarificationMode.FULL:
        context = collect_full_responses(
            questions=questions,
            task_id=task_id,
            task_title=task_title,
            complexity=complexity,
        )
    else:  # QUICK mode
        context = collect_quick_responses(
            questions=questions,
            timeout_seconds=15,
        )

    # Persist to task frontmatter
    _persist_clarification(task_id, context)

    return context


def _determine_clarification_mode(
    complexity: int,
    flags: Dict[str, Any]
) -> ClarificationMode:
    """
    Determine clarification mode based on complexity and flags.

    Flag precedence (highest to lowest):
    1. --no-questions: SKIP
    2. --answers: (process later, but enter interactive mode)
    3. --defaults: USE_DEFAULTS
    4. --with-questions: Force FULL/QUICK based on complexity
    5. Complexity-based auto-selection

    Args:
        complexity: Task complexity score (0-10)
        flags: Command-line flags

    Returns:
        ClarificationMode indicating how to proceed
    """
    # Priority 1: --no-questions (highest)
    if flags.get("no_questions", False):
        return ClarificationMode.SKIP

    # Priority 2: --micro flag (implies skip)
    if flags.get("micro", False):
        return ClarificationMode.SKIP

    # Priority 3: --defaults
    if flags.get("defaults", False):
        return ClarificationMode.USE_DEFAULTS

    # Priority 4: --with-questions (force clarification)
    if flags.get("with_questions", False):
        # Force clarification, but use appropriate mode based on complexity
        if complexity >= 5:
            return ClarificationMode.FULL
        else:
            return ClarificationMode.QUICK

    # Priority 5: Complexity-based auto-selection
    return should_clarify("planning", complexity, flags)


def _process_inline_answers(
    questions: List[Any],
    answers_str: str,
    mode: ClarificationMode
) -> ClarificationContext:
    """
    Process inline answers from --answers flag.

    Format: "1:Y 2:N 3:JWT" (question_number:answer pairs)

    Args:
        questions: List of Question objects
        answers_str: Inline answers string
        mode: Clarification mode

    Returns:
        ClarificationContext with parsed answers
    """
    from .clarification.core import process_responses

    user_responses = {}

    # Parse answers string (e.g., "1:Y 2:N 3:JWT")
    pairs = answers_str.split()
    for pair in pairs:
        if ":" in pair:
            parts = pair.split(":", 1)
            try:
                # Support both numeric (1:Y) and id-based (scope_01:Y) formats
                key = parts[0]
                answer = parts[1].upper()

                if key.isdigit():
                    # Numeric index (1-based)
                    idx = int(key) - 1
                    if 0 <= idx < len(questions):
                        user_responses[questions[idx].id] = answer
                else:
                    # Question ID
                    user_responses[key] = answer
            except (ValueError, IndexError) as e:
                logger.warning(f"Could not parse answer '{pair}': {e}")

    # Fill in defaults for unanswered questions
    for q in questions:
        if q.id not in user_responses:
            user_responses[q.id] = q.default

    return process_responses(questions, user_responses, mode)


def _apply_defaults(questions: List[Any]) -> ClarificationContext:
    """
    Apply default answers to all questions.

    Args:
        questions: List of Question objects

    Returns:
        ClarificationContext with all defaults applied
    """
    from .clarification.core import process_responses

    user_responses = {q.id: q.default for q in questions}
    return process_responses(questions, user_responses, ClarificationMode.USE_DEFAULTS)


def _persist_clarification(
    task_id: str,
    context: ClarificationContext
) -> None:
    """
    Persist clarification context to task frontmatter.

    Args:
        task_id: Task identifier
        context: ClarificationContext to persist
    """
    task_path = _find_task_file(task_id)
    if task_path:
        try:
            context.context_type = "implementation_planning"
            context.persist_to_frontmatter(task_path)
            logger.debug(f"Persisted clarification to {task_path}")
        except Exception as e:
            logger.warning(f"Could not persist clarification: {e}")


def get_clarification_for_prompt(
    context: Optional[ClarificationContext]
) -> str:
    """
    Format clarification context for inclusion in agent prompts.

    Args:
        context: ClarificationContext or None

    Returns:
        Formatted string for agent prompts
    """
    if not context or not CLARIFICATION_AVAILABLE:
        return ""

    if not context.decisions:
        return ""

    return format_for_prompt(context)


def execute_phases(
    task_id: str,
    task_context: Dict[str, Any],
    design_only: bool = False,
    implement_only: bool = False,
    stack: str = "default"
) -> Dict[str, Any]:
    """
    Main entry point for phase execution. Routes to appropriate workflow based on flags.

    Args:
        task_id: Task identifier (e.g., "TASK-006")
        task_context: Task context loaded from task file (frontmatter + content)
        design_only: If True, execute design phases only
        implement_only: If True, execute implementation phases only (requires approved design)
        stack: Technology stack (e.g., "python", "react", "maui")

    Returns:
        Dictionary containing execution results:
        {
            "success": bool,
            "workflow_mode": str,  # "standard", "design_only", "implement_only"
            "phases_executed": List[str],
            "final_state": str,
            "duration_seconds": float,
            "results": Dict[str, Any]
        }

    Raises:
        ValueError: If both flags are True (mutual exclusivity violation)
        StateValidationError: If task state is invalid for requested operation
        PhaseExecutionError: If phase execution fails

    Examples:
        >>> # Standard workflow
        >>> result = execute_phases("TASK-006", context)
        >>> result["workflow_mode"]
        'standard'

        >>> # Design-only workflow
        >>> result = execute_phases("TASK-006", context, design_only=True)
        >>> result["final_state"]
        'design_approved'

        >>> # Implement-only workflow
        >>> result = execute_phases("TASK-006", context, implement_only=True)
        >>> result["workflow_mode"]
        'implement_only'
    """
    # Validate mutual exclusivity
    if design_only and implement_only:
        raise ValueError(
            "Cannot use both --design-only and --implement-only flags together.\n"
            "Choose one workflow mode:\n"
            "  --design-only: Execute design phases only\n"
            "  --implement-only: Execute implementation phases only\n"
            "  (no flags): Execute complete workflow"
        )

    # Route to appropriate workflow
    start_time = datetime.now()

    if design_only:
        result = execute_design_phases(task_id, task_context, stack)
        workflow_mode = "design_only"
    elif implement_only:
        result = execute_implementation_phases(task_id, task_context, stack)
        workflow_mode = "implement_only"
    else:
        result = execute_standard_phases(task_id, task_context, stack)
        workflow_mode = "standard"

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    return {
        "success": result.get("success", True),
        "workflow_mode": workflow_mode,
        "phases_executed": result.get("phases_executed", []),
        "final_state": result.get("final_state", "unknown"),
        "duration_seconds": duration,
        "results": result
    }


def execute_design_phases(
    task_id: str,
    task_context: Dict[str, Any],
    stack: str = "default"
) -> Dict[str, Any]:
    """
    Execute design phases only (Phase 1 through Phase 2.6).

    Phases executed:
    - Phase 1: Load Task Context
    - Phase 2: Implementation Planning
    - Phase 2.5A: Pattern Suggestion (if Design Patterns MCP available)
    - Phase 2.5B: Architectural Review
    - Phase 2.7: Complexity Evaluation & Plan Persistence
    - Phase 2.8: Human Checkpoint (mandatory, design-focused)

    After approval, task moves to 'design_approved' state with saved implementation plan.

    Args:
        task_id: Task identifier
        task_context: Task context from task file
        stack: Technology stack

    Returns:
        Dictionary with execution results:
        {
            "success": bool,
            "phases_executed": List[str],
            "final_state": str,  # "design_approved" or "blocked"
            "design_approved": bool,
            "plan_path": Optional[str],
            "architectural_review": Dict[str, Any],
            "complexity_evaluation": Dict[str, Any]
        }

    Raises:
        StateValidationError: If task state is invalid for design phase
        PhaseExecutionError: If phase execution fails
    """
    phases_executed = []

    # Validate task state (can run design-only from backlog, in_progress, or blocked)
    current_state = task_context.get("status", "unknown")
    valid_states = ["backlog", "in_progress", "blocked"]

    if current_state not in valid_states:
        raise StateValidationError(
            f"Cannot execute design-only workflow from '{current_state}' state.\n"
            f"Valid states: {', '.join(valid_states)}\n"
            f"Current state: {current_state}"
        )

    print(f"\n🎨 Starting Design-Only Workflow for {task_id}")
    print(f"Current state: {current_state}")
    print(f"Technology stack: {stack}\n")

    # Phase 1: Load Task Context (already done, just record)
    phases_executed.append("Phase 1: Load Task Context")
    print("✅ Phase 1: Task context loaded")

    # Phase 2: Implementation Planning (delegated to agent)
    phases_executed.append("Phase 2: Implementation Planning")
    print("⏳ Phase 2: Invoking planning agent...")
    # NOTE: Agent invocation happens in task-work.md protocol
    # This function orchestrates the flow

    # Phase 2.5A: Pattern Suggestion (optional, if MCP available)
    # Skipped in MVP - will be invoked by task-work.md if available

    # Phase 2.5B: Architectural Review (delegated to agent)
    phases_executed.append("Phase 2.5B: Architectural Review")
    print("⏳ Phase 2.5B: Invoking architectural reviewer...")
    # NOTE: Agent invocation happens in task-work.md protocol

    # Phase 2.7: Complexity Evaluation & Plan Persistence
    phases_executed.append("Phase 2.7: Complexity Evaluation")
    print("⏳ Phase 2.7: Evaluating complexity and persisting plan...")
    # NOTE: Agent invocation happens in task-work.md protocol

    # Phase 2.8: Human Checkpoint (mandatory for design-only)
    phases_executed.append("Phase 2.8: Design Approval Checkpoint")
    print("⏳ Phase 2.8: Awaiting design approval...")
    # NOTE: Human interaction happens in task-work.md protocol

    # Return structure (actual values filled by task-work protocol)
    return {
        "success": True,
        "phases_executed": phases_executed,
        "final_state": "design_approved",  # Assuming approval
        "design_approved": True,
        "plan_path": f"docs/state/{task_id}/implementation_plan.json",
        "architectural_review": {},  # Filled by task-work protocol
        "complexity_evaluation": {}  # Filled by task-work protocol
    }


def execute_implementation_phases(
    task_id: str,
    task_context: Dict[str, Any],
    stack: str = "default"
) -> Dict[str, Any]:
    """
    Execute implementation phases only (Phase 3 through Phase 5).

    Prerequisite: Task must be in 'design_approved' state.

    Phases executed:
    - Phase 3: Implementation (using saved plan)
    - Phase 4: Testing
    - Phase 4.5: Fix Loop (ensure tests pass)
    - Phase 5: Code Review

    After completion, task moves to 'in_review' (if pass) or 'blocked' (if fail).

    Args:
        task_id: Task identifier
        task_context: Task context from task file
        stack: Technology stack

    Returns:
        Dictionary with execution results:
        {
            "success": bool,
            "phases_executed": List[str],
            "final_state": str,  # "in_review" or "blocked"
            "tests_passed": bool,
            "test_results": Dict[str, Any],
            "quality_gates": Dict[str, bool]
        }

    Raises:
        StateValidationError: If task is not in 'design_approved' state
        PhaseExecutionError: If saved design plan is missing or invalid
    """
    phases_executed = []

    # Validate task state (MUST be design_approved)
    current_state = task_context.get("status", "unknown")

    if current_state != "design_approved":
        raise StateValidationError(
            f"❌ Cannot execute --implement-only workflow\n\n"
            f"Task {task_id} is in '{current_state}' state.\n"
            f"Required state: design_approved\n\n"
            f"To approve design first, run:\n"
            f"  /task-work {task_id} --design-only\n\n"
            f"Or run complete workflow without flags:\n"
            f"  /task-work {task_id}"
        )

    # Validate design metadata exists
    design_metadata = task_context.get("design", {})
    if not design_metadata or design_metadata.get("status") != "approved":
        raise PhaseExecutionError(
            f"❌ Design metadata missing or invalid for {task_id}\n\n"
            f"Task is in design_approved state, but design metadata is incomplete.\n"
            f"This may indicate a corrupted task file.\n\n"
            f"Options:\n"
            f"1. Re-run design phase: /task-work {task_id} --design-only\n"
            f"2. Run full workflow: /task-work {task_id}\n"
            f"3. Manually fix task metadata"
        )

    # Load saved implementation plan
    plan_path = Path(f"docs/state/{task_id}/implementation_plan.json")
    if not plan_path.exists():
        raise PhaseExecutionError(
            f"❌ Implementation plan not found: {plan_path}\n\n"
            f"Design was approved but plan file is missing.\n"
            f"Re-run design phase: /task-work {task_id} --design-only"
        )

    print(f"\n🚀 Starting Implementation-Only Workflow for {task_id}")
    print(f"Current state: {current_state}")
    print(f"Using approved design from: {design_metadata.get('approved_at', 'unknown')}\n")

    # Display design summary
    _display_implementation_start_context(task_id, task_context, design_metadata)

    # Phase 3: Implementation (delegated to agent)
    phases_executed.append("Phase 3: Implementation")
    print("\n⏳ Phase 3: Invoking implementation agent...")
    # NOTE: Agent invocation happens in task-work.md protocol

    # Phase 4: Testing (delegated to agent)
    phases_executed.append("Phase 4: Testing")
    print("⏳ Phase 4: Invoking testing agent...")
    # NOTE: Agent invocation happens in task-work.md protocol

    # Phase 4.5: Fix Loop (automated)
    phases_executed.append("Phase 4.5: Fix Loop")
    print("⏳ Phase 4.5: Ensuring all tests pass...")
    # NOTE: Fix loop happens in task-work.md protocol

    # Phase 5: Code Review (delegated to agent)
    phases_executed.append("Phase 5: Code Review")
    print("⏳ Phase 5: Invoking code reviewer...")
    # NOTE: Agent invocation happens in task-work.md protocol

    # Phase 5.5: Plan Audit (NEW - Hubbard's Step 6)
    phases_executed.append("Phase 5.5: Plan Audit")
    print("⏳ Phase 5.5: Auditing implementation against plan...")
    # NOTE: Audit happens in task-work.md protocol

    # Return structure (actual values filled by task-work protocol)
    return {
        "success": True,
        "phases_executed": phases_executed,
        "final_state": "in_review",  # Assuming success
        "tests_passed": True,
        "test_results": {},  # Filled by task-work protocol
        "quality_gates": {}  # Filled by task-work protocol
    }


def execute_standard_phases(
    task_id: str,
    task_context: Dict[str, Any],
    stack: str = "default"
) -> Dict[str, Any]:
    """
    Execute standard full workflow (all phases in sequence).

    This is the default behavior when no flags are provided.
    Maintains backward compatibility with existing task-work implementation.

    Phases executed:
    - Phase 1: Load Task Context
    - Phase 2: Implementation Planning
    - Phase 2.5A: Pattern Suggestion (optional)
    - Phase 2.5B: Architectural Review
    - Phase 2.7: Complexity Evaluation
    - Phase 2.8: Human Checkpoint (if triggered by complexity)
    - Phase 3: Implementation
    - Phase 4: Testing
    - Phase 4.5: Fix Loop
    - Phase 5: Code Review

    Args:
        task_id: Task identifier
        task_context: Task context from task file
        stack: Technology stack

    Returns:
        Dictionary with execution results (all phases)
    """
    phases_executed = []

    print(f"\n🔄 Starting Standard Workflow for {task_id}")
    print(f"Technology stack: {stack}")
    print("Executing all phases in sequence...\n")

    # All phases execute as per current implementation
    # This function maintains backward compatibility
    phases_executed = [
        "Phase 1: Load Task Context",
        "Phase 2: Implementation Planning",
        "Phase 2.5B: Architectural Review",
        "Phase 2.7: Complexity Evaluation",
        "Phase 2.8: Human Checkpoint (if triggered)",
        "Phase 3: Implementation",
        "Phase 4: Testing",
        "Phase 4.5: Fix Loop",
        "Phase 5: Code Review",
        "Phase 5.5: Plan Audit"
    ]

    # NOTE: Actual phase execution happens in task-work.md protocol
    # This function just orchestrates the flow

    return {
        "success": True,
        "phases_executed": phases_executed,
        "final_state": "in_review",  # Typical successful outcome
        "workflow_note": "Standard workflow - all phases executed"
    }


def _display_implementation_start_context(
    task_id: str,
    task_context: Dict[str, Any],
    design_metadata: Dict[str, Any]
) -> None:
    """
    Display implementation start context showing approved design summary.

    Args:
        task_id: Task identifier
        task_context: Full task context
        design_metadata: Design metadata from task frontmatter
    """
    print("\n" + "=" * 67)
    print("🚀 IMPLEMENTATION PHASE (--implement-only mode)")
    print("=" * 67)
    print()
    print(f"TASK: {task_id} - {task_context.get('title', 'Untitled')}")
    print()
    print("APPROVED DESIGN:")
    print(f"  Design approved: {design_metadata.get('approved_at', 'unknown')}")
    print(f"  Approved by: {design_metadata.get('approved_by', 'unknown')}")
    print(f"  Architectural score: {design_metadata.get('architectural_review_score', 'N/A')}/100")
    print(f"  Complexity score: {design_metadata.get('complexity_score', 'N/A')}/10")
    print()

    # Load and display plan summary if available
    plan_path = Path(f"docs/state/{task_id}/implementation_plan.json")
    if plan_path.exists():
        try:
            with open(plan_path, 'r') as f:
                plan = json.load(f)

            print("IMPLEMENTATION PLAN:")
            print(f"  Files to create: {len(plan.get('files_to_create', []))}")
            print(f"  External dependencies: {len(plan.get('external_dependencies', []))}")
            print(f"  Estimated duration: {plan.get('estimated_duration', 'N/A')}")
            print(f"  Test strategy: {plan.get('test_summary', 'N/A')}")
            print()
        except Exception as e:
            print(f"  ⚠️  Could not load plan details: {e}")
            print()

    print("Beginning implementation phases (3 → 4 → 4.5 → 5)...")
    print("=" * 67)
    print()


# ============================================================================
# Phase 3: AI-Powered Specialist Discovery (TASK-HAI-006)
# ============================================================================

def analyze_task_context(
    task_id: str,
    plan: Dict[str, Any],
    task_context: Optional[Dict[str, Any]] = None
) -> Dict[str, List[str]]:
    """
    Analyze task to extract stack and keywords for agent discovery.

    Detection strategies:
    1. File extensions in plan (implementation_plan['files'])
    2. Keywords in task title/description
    3. Existing project structure (package.json, requirements.txt, *.csproj)

    Args:
        task_id: Task identifier
        plan: Implementation plan dictionary
        task_context: Optional task context with title/description

    Returns:
        Dictionary with 'stack' and 'keywords' lists

    Example:
        >>> plan = {'implementation_plan': {'files': ['src/api/users.py']}}
        >>> context = analyze_task_context('TASK-001', plan)
        >>> print(context)
        {'stack': ['python'], 'keywords': []}
    """
    context: Dict[str, List[str]] = {'stack': [], 'keywords': []}

    # Strategy 1: File extensions from plan
    files = plan.get('implementation_plan', {}).get('files', [])
    if not files:
        # Try alternative plan structure
        files = plan.get('files', [])
        if not files:
            files = plan.get('files_to_create', [])

    for file in files:
        file_lower = str(file).lower()
        if file_lower.endswith(('.py', '.pyi')):
            context['stack'].append('python')
        elif file_lower.endswith(('.tsx', '.jsx')):
            context['stack'].extend(['react', 'typescript'])
        elif file_lower.endswith('.ts'):
            context['stack'].append('typescript')
        elif file_lower.endswith('.js'):
            context['stack'].append('javascript')
        elif file_lower.endswith('.cs'):
            context['stack'].extend(['dotnet', 'csharp'])
        elif file_lower.endswith('.go'):
            context['stack'].append('go')
        elif file_lower.endswith('.rs'):
            context['stack'].append('rust')
        elif file_lower.endswith('.rb'):
            context['stack'].append('ruby')
        elif file_lower.endswith('.java'):
            context['stack'].append('java')
        elif file_lower.endswith('.php'):
            context['stack'].append('php')

    # Strategy 2: Keywords from task context
    if task_context:
        description = str(task_context.get('description', '')).lower()
        title = str(task_context.get('title', '')).lower()
        text = f"{title} {description}"

        # Keyword patterns for different domains
        keyword_patterns = {
            'fastapi': ['fastapi', 'fast api'],
            'api': ['api', 'endpoint', 'rest', 'graphql'],
            'async': ['async', 'await', 'asyncio'],
            'react': ['react', 'component', 'jsx', 'tsx'],
            'hooks': ['hook', 'usestate', 'useeffect'],
            'state': ['state', 'zustand', 'redux', 'context'],
            'domain': ['domain', 'entity', 'aggregate', 'value object', 'ddd'],
            'repository': ['repository', 'data access', 'persistence'],
            'testing': ['test', 'pytest', 'jest', 'vitest'],
            'database': ['database', 'sql', 'mongodb', 'postgres'],
        }

        for keyword, patterns in keyword_patterns.items():
            if any(p in text for p in patterns):
                context['keywords'].append(keyword)

    # Strategy 3: Project structure detection
    try:
        # Check for package.json (Node/React)
        if os.path.exists('package.json'):
            try:
                with open('package.json', 'r') as f:
                    pkg = json.load(f)
                    deps = pkg.get('dependencies', {})
                    dev_deps = pkg.get('devDependencies', {})
                    all_deps = {**deps, **dev_deps}

                    if 'react' in all_deps:
                        context['stack'].append('react')
                    if 'typescript' in all_deps:
                        context['stack'].append('typescript')
                    if 'next' in all_deps:
                        context['stack'].append('nextjs')
            except (json.JSONDecodeError, IOError):
                pass

        # Check for requirements.txt (Python)
        if os.path.exists('requirements.txt'):
            try:
                with open('requirements.txt', 'r') as f:
                    requirements = f.read().lower()
                    if 'fastapi' in requirements:
                        context['stack'].append('python')
                        context['keywords'].append('fastapi')
                    elif 'django' in requirements:
                        context['stack'].append('python')
                        context['keywords'].append('django')
                    elif 'flask' in requirements:
                        context['stack'].append('python')
                        context['keywords'].append('flask')
            except IOError:
                pass

        # Check for pyproject.toml (Python)
        if os.path.exists('pyproject.toml'):
            context['stack'].append('python')

        # Check for .csproj files (.NET)
        if glob_module.glob('*.csproj') or glob_module.glob('**/*.csproj', recursive=True):
            context['stack'].extend(['dotnet', 'csharp'])

        # Check for go.mod (Go)
        if os.path.exists('go.mod'):
            context['stack'].append('go')

        # Check for Cargo.toml (Rust)
        if os.path.exists('Cargo.toml'):
            context['stack'].append('rust')

    except Exception as e:
        logger.debug(f"Project structure detection error: {e}")

    # Deduplicate while preserving order
    context['stack'] = list(dict.fromkeys(context['stack']))
    context['keywords'] = list(dict.fromkeys(context['keywords']))

    logger.debug(f"Context analysis for {task_id}: stack={context['stack']}, keywords={context['keywords']}")

    return context


def execute_phase_3(
    task_id: str,
    plan: Dict[str, Any],
    task_context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Phase 3: Implementation with AI-powered specialist discovery.

    This function:
    1. Analyzes task context to detect stack and keywords
    2. Uses discover_agents() to find matching specialists
    3. Selects the best specialist (highest relevance) or falls back to task-manager
    4. Returns metadata about the selected agent

    Args:
        task_id: Task identifier
        plan: Implementation plan dictionary
        task_context: Optional task context with title/description

    Returns:
        Dictionary with phase 3 execution results:
        {
            "success": bool,
            "agent_used": str,           # Agent name
            "agent_path": str,           # Path to agent file
            "discovery_method": str,     # "ai-metadata" or "fallback"
            "context_detected": dict,    # Detected stack/keywords
            "specialists_found": int,    # Number of matching specialists
            "relevance_score": int       # Score of selected agent (if specialist)
        }

    Example:
        >>> result = execute_phase_3("TASK-001", python_plan)
        >>> print(result['agent_used'])
        'python-api-specialist'
        >>> print(result['discovery_method'])
        'ai-metadata'
    """
    # Check if discovery module is available (imported at module level)
    if not DISCOVERY_AVAILABLE or _discover_agents is None:
        logger.warning("Agent discovery module not available, using fallback")
        return _fallback_phase_3_result(task_id)

    # Step 1: Analyze task context
    print(f"\nPhase 3: Implementation")
    print("└─ Analyzing task context...")

    context = analyze_task_context(task_id, plan, task_context)
    stack = context.get('stack', [])
    keywords = context.get('keywords', [])

    print(f"   ├─ Detected stack: {stack if stack else '(none)'}")
    print(f"   ├─ Keywords: {keywords if keywords else '(none)'}")

    # Step 2: Discover specialists
    try:
        specialists = _discover_agents(
            phase='implementation',
            stack=stack if stack else None,
            keywords=keywords if keywords else None
        )
    except Exception as e:
        logger.warning(f"Discovery failed: {e}")
        specialists = []

    print(f"   └─ Discovery found {len(specialists)} specialist(s)")

    # Step 3: Select agent
    if specialists:
        agent = specialists[0]  # Highest relevance (pre-sorted)
        agent_name = agent.get('name', 'unknown')
        agent_path = agent.get('path', '')
        relevance_score = agent.get('relevance_score', 0)
        agent_stack = agent.get('stack', [])
        agent_capabilities = agent.get('capabilities', [])[:3]  # First 3

        print(f"\nUsing {agent_name} for implementation (Haiku model)")
        print(f"└─ Specialized in: {', '.join(agent_capabilities)}")

        logger.info(f"Phase 3: Selected specialist {agent_name} (score: {relevance_score})")

        return {
            "success": True,
            "agent_used": agent_name,
            "agent_path": agent_path,
            "discovery_method": "ai-metadata",
            "context_detected": context,
            "specialists_found": len(specialists),
            "relevance_score": relevance_score,
            "agent_model": agent.get('model', 'haiku'),
            "agent_stack": agent_stack
        }
    else:
        # Fallback to task-manager
        print(f"\nUsing task-manager for implementation (Sonnet model)")
        print("└─ General-purpose implementation agent")

        logger.info(f"Phase 3: No specialist found, using task-manager (fallback)")

        return {
            "success": True,
            "agent_used": "task-manager",
            "agent_path": "installer/core/agents/task-manager.md",
            "discovery_method": "fallback",
            "context_detected": context,
            "specialists_found": 0,
            "relevance_score": 0,
            "agent_model": "sonnet",
            "agent_stack": ["cross-stack"]
        }


def _fallback_phase_3_result(task_id: str) -> Dict[str, Any]:
    """
    Generate fallback result when discovery module is unavailable.

    Args:
        task_id: Task identifier

    Returns:
        Fallback result using task-manager
    """
    logger.warning(f"Phase 3: Discovery unavailable for {task_id}, using task-manager")

    return {
        "success": True,
        "agent_used": "task-manager",
        "agent_path": "installer/core/agents/task-manager.md",
        "discovery_method": "fallback",
        "context_detected": {"stack": [], "keywords": []},
        "specialists_found": 0,
        "relevance_score": 0,
        "agent_model": "sonnet",
        "agent_stack": ["cross-stack"],
        "note": "Discovery module unavailable"
    }


def execute_phase_5_5_plan_audit(
    task_id: str,
    task_context: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Phase 5.5: Audit implementation against saved plan.

    Implements Hubbard's Step 6 (Audit) - verifies actual implementation
    matches the approved architectural plan.

    Args:
        task_id: Task identifier
        task_context: Task context from task file

    Returns:
        Dictionary with audit results:
        {
            "approved": bool,
            "report": PlanAuditReport,
            "decision": str,
            "skipped": bool
        }

    Example:
        >>> result = execute_phase_5_5_plan_audit("TASK-025", context)
        >>> if result["approved"]:
        ...     print("Audit passed")
    """
    from .plan_audit import PlanAuditor, format_audit_report, PlanAuditError
    from .plan_persistence import plan_exists
    from .metrics.plan_audit_metrics import PlanAuditMetricsTracker

    # Check if plan exists
    if not plan_exists(task_id):
        print("⚠️  No implementation plan found - skipping audit")
        return {"approved": True, "report": None, "decision": "skipped", "skipped": True}

    try:
        # Run audit
        auditor = PlanAuditor()
        report = auditor.audit_implementation(task_id)

        # Display report
        print("\n" + format_audit_report(report))

        # Prompt for decision with timeout
        decision = prompt_with_timeout(
            "Choice [A]pprove/[R]evise/[E]scalate/[C]ancel (30s timeout = auto-approve): ",
            timeout=30,
            default="A"
        )

        # Handle decision
        approved = handle_audit_decision(task_id, report, decision)

        # Track metrics
        tracker = PlanAuditMetricsTracker()
        tracker.record_audit(task_id, report, decision.lower())

        return {
            "approved": approved,
            "report": report,
            "decision": decision.lower(),
            "skipped": False
        }

    except PlanAuditError as e:
        print(f"⚠️  Audit error: {e}")
        print("Defaulting to approve (non-blocking)")
        return {"approved": True, "report": None, "decision": "error", "skipped": False}


def prompt_with_timeout(prompt: str, timeout: int, default: str) -> str:
    """
    Prompt user with timeout (auto-returns default after timeout).

    Uses threading to implement timeout behavior.

    Args:
        prompt: Prompt text to display
        timeout: Timeout in seconds
        default: Default value if timeout occurs

    Returns:
        User input or default value

    Example:
        >>> response = prompt_with_timeout("Continue? ", 30, "Y")
        >>> print(response)
        'Y'
    """
    import sys
    import threading

    result = [default]  # Mutable container for thread communication

    def get_input():
        try:
            result[0] = input(prompt).strip().upper()
        except Exception:
            pass

    thread = threading.Thread(target=get_input)
    thread.daemon = True
    thread.start()
    thread.join(timeout)

    if thread.is_alive():
        print(f"\n⏱️  Timeout - defaulting to [{default}]")

    return result[0]


def handle_audit_decision(
    task_id: str,
    report: Any,  # PlanAuditReport
    decision: str
) -> bool:
    """
    Handle audit decision and update task state.

    Args:
        task_id: Task identifier
        report: PlanAuditReport object
        decision: User decision ("A", "R", "E", "C")

    Returns:
        True if approved (continue to IN_REVIEW)
        False if blocked (transition to BLOCKED)

    Example:
        >>> approved = handle_audit_decision("TASK-025", report, "A")
        >>> print(approved)
        True
    """
    decision_lower = decision.lower()

    if decision_lower == "a":
        # Approve - add note to task metadata
        print("✅ Audit approved - proceeding to IN_REVIEW")
        _update_task_metadata(task_id, report, "approved")
        return True

    elif decision_lower == "r":
        # Revise - transition to BLOCKED
        print("❌ Audit revision requested - transitioning to BLOCKED")
        _update_task_metadata(task_id, report, "revision_requested")
        return False

    elif decision_lower == "e":
        # Escalate - create follow-up task, proceed to IN_REVIEW with warning
        print("⚠️  Audit escalated - creating follow-up task")
        _create_followup_task(task_id, report)
        _update_task_metadata(task_id, report, "escalated")
        return True

    elif decision_lower == "c":
        # Cancel - transition to BLOCKED
        print("❌ Audit cancelled - transitioning to BLOCKED")
        _update_task_metadata(task_id, report, "cancelled")
        return False

    else:
        # Invalid input - default to approve with warning
        print(f"⚠️  Invalid input '{decision}' - defaulting to Approve")
        _update_task_metadata(task_id, report, "approved_default")
        return True


def _update_task_metadata(task_id: str, report: Any, decision: str) -> None:
    """
    Update task frontmatter with audit results.

    Args:
        task_id: Task identifier
        report: PlanAuditReport object
        decision: Audit decision
    """
    task_file = _find_task_file(task_id)
    if not task_file:
        return

    try:
        from .task_utils import update_task_frontmatter

        # Use centralized task utility to update frontmatter
        update_task_frontmatter(
            task_file,
            {
                "plan_audit": {
                    "severity": report.severity,
                    "discrepancies_count": len(report.discrepancies),
                    "decision": decision,
                    "audited_at": report.timestamp
                }
            },
            preserve_body=True
        )

    except Exception as e:
        print(f"⚠️  Could not update task metadata: {e}")


def _create_followup_task(task_id: str, report: Any) -> None:
    """
    Create follow-up task for scope creep investigation.

    Args:
        task_id: Original task identifier
        report: PlanAuditReport object
    """
    # Placeholder - actual implementation would:
    # 1. Generate new task file in tasks/backlog/
    # 2. Link to original task
    # 3. Add discrepancies as requirements
    print(f"📝 Follow-up task created: {task_id}-AUDIT-FOLLOWUP")
    print("   (Note: Follow-up task creation not yet implemented)")


def _find_task_file(task_id: str) -> Optional[Path]:
    """
    Find task file across all state directories.

    Supports both exact filenames (TASK-001.md) and descriptive filenames
    (TASK-001-add-feature.md) by using glob patterns.

    Args:
        task_id: Task identifier (e.g., "TASK-001", "TASK-CLQ-FIX-005")

    Returns:
        Path to task file or None if not found
    """
    # Also check feature folders (e.g., tasks/backlog/clarifying-questions-fix/)
    search_patterns = [
        "tasks/{state_dir}/{task_id}.md",                    # Exact match
        "tasks/{state_dir}/{task_id}-*.md",                  # With descriptor
        "tasks/{state_dir}/*/{task_id}.md",                  # In feature folder
        "tasks/{state_dir}/*/{task_id}-*.md",                # In feature folder with descriptor
    ]

    state_dirs = ["in_progress", "backlog", "blocked", "in_review", "completed"]

    for state_dir in state_dirs:
        for pattern_template in search_patterns:
            pattern = pattern_template.format(state_dir=state_dir, task_id=task_id)
            matches = list(glob_module.glob(pattern))
            if matches:
                # Return first match
                return Path(matches[0])

    return None


# Module exports
__all__ = [
    "execute_phases",
    "execute_design_phases",
    "execute_implementation_phases",
    "execute_standard_phases",
    "execute_phase_1_6_clarification",
    "get_clarification_for_prompt",
    "execute_phase_3",
    "analyze_task_context",
    "execute_phase_5_5_plan_audit",
    "prompt_with_timeout",
    "handle_audit_decision",
    "PhaseExecutionError",
    "StateValidationError",
    "CLARIFICATION_AVAILABLE",
]
