#!/usr/bin/env python3
"""
Execute clarification for TASK-FBSDK-020.

This script demonstrates the clarification workflow using quick mode
(15-second timeout) based on complexity score of 4.
"""

import sys
from pathlib import Path

# Add library paths
sys.path.insert(0, '/Users/richardwoollcott/.agentecflow/lib')
sys.path.insert(0, '/Users/richardwoollcott/Projects/appmilla_github/guardkit/installer/core/commands/lib')

from clarification.core import (
    ClarificationMode,
    ClarificationContext,
    should_clarify,
    format_for_prompt,
)
from clarification.generators.planning_generator import (
    generate_planning_questions,
    TaskContext,
)
from clarification.display import (
    collect_quick_responses,
    display_skip_message,
)


def main():
    """Execute clarification workflow for TASK-FBSDK-020."""

    # Task context
    task_id = "TASK-FBSDK-020"
    task_title = "Define task type schema and quality gate profiles"
    complexity = 4

    task_context = TaskContext(
        task_id=task_id,
        title=task_title,
        description=(
            "Create a formal schema for task types and their associated quality gate profiles. "
            "Different task types (scaffolding, feature, infrastructure, documentation) require "
            "different validation approaches."
        ),
        acceptance_criteria=[
            "TaskType enum defined with 4 types: scaffolding, feature, infrastructure, documentation",
            "QualityGateProfile dataclass with configurable gates per type",
            "Default profiles defined matching the decision matrix",
            "Schema supports custom profiles via configuration",
            "Unit tests verify profile application",
            "Documentation updated with task type descriptions",
        ],
        complexity_score=complexity,
        tags=["python", "schema", "quality-gates"],
    )

    # Command flags (no special flags)
    flags = {
        "no_questions": False,
        "with_questions": False,
        "defaults": False,
        "answers": None,
        "reclarify": False,
    }

    print("\n" + "="*80)
    print("CLARIFICATION WORKFLOW - TASK-FBSDK-020")
    print("="*80 + "\n")

    # Step 1: Determine clarification mode
    print("Step 1: Determining clarification mode...")
    mode = should_clarify(
        context_type="planning",
        complexity=complexity,
        flags=flags
    )
    print(f"   Mode: {mode.value}")
    print(f"   Reason: Complexity {complexity}/10 triggers QUICK mode (15s timeout)\n")

    # Step 2: Generate questions
    print("Step 2: Generating planning questions...")
    questions = generate_planning_questions(
        task_context=task_context,
        complexity_score=complexity,
        codebase_context=None,
        mode=mode
    )
    print(f"   Generated: {len(questions)} question(s)")

    if questions:
        for i, q in enumerate(questions, 1):
            print(f"   {i}. [{q.category}] {q.text[:60]}...")
    print()

    # Step 3: Handle based on mode
    if mode == ClarificationMode.SKIP:
        print("Step 3: Skipping clarification (complexity too low)")
        print(display_skip_message("trivial", complexity))
        context = ClarificationContext(
            context_type="implementation_planning",
            mode="skip",
            total_questions=0,
            answered_count=0,
            user_override="skip",
        )

    elif not questions:
        print("Step 3: No questions needed")
        print(display_skip_message("no_questions_needed"))
        context = ClarificationContext(
            context_type="implementation_planning",
            mode="skip",
            total_questions=0,
            answered_count=0,
            user_override="no_questions_needed",
        )

    else:
        print("Step 3: Collecting responses (QUICK mode - 15s timeout)")
        print()
        context = collect_quick_responses(questions, timeout_seconds=15)
        context.context_type = "implementation_planning"

    # Step 4: Display results
    print("\n" + "="*80)
    print("CLARIFICATION RESULTS")
    print("="*80 + "\n")

    print(f"Context Type: {context.context_type}")
    print(f"Mode: {context.mode}")
    print(f"Total Questions: {context.total_questions}")
    print(f"Answered: {context.answered_count}")
    print(f"Skipped: {context.skipped_count}")
    print(f"User Override: {context.user_override or 'None'}")
    print()

    if context.has_explicit_decisions:
        print("Explicit Decisions:")
        for d in context.explicit_decisions:
            print(f"  - [{d.category}] {d.question_text}")
            print(f"    Answer: {d.answer_display}")
            print(f"    Rationale: {d.rationale}")
            print()

    if context.assumed_defaults:
        print("Assumed Defaults:")
        for d in context.assumed_defaults:
            print(f"  - [{d.category}] {d.question_text}")
            print(f"    Default: {d.answer_display}")
            print(f"    Rationale: {d.rationale}")
            print()

    # Step 5: Format for agent prompt
    print("\n" + "="*80)
    print("FORMATTED FOR AGENT PROMPT")
    print("="*80 + "\n")

    formatted = format_for_prompt(context)
    print(formatted)

    print("\n" + "="*80)
    print("WORKFLOW COMPLETE")
    print("="*80 + "\n")

    return context


if __name__ == "__main__":
    try:
        context = main()
        sys.exit(0)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
