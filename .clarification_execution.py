#!/usr/bin/env python3
"""Execute clarification for TASK-FBSDK-002."""

import sys
sys.path.insert(0, '/Users/richardwoollcott/Projects/appmilla_github/guardkit/installer/core/commands/lib')

from clarification.core import ClarificationMode, ClarificationContext, process_responses
from clarification.generators.planning_generator import TaskContext, generate_planning_questions
from clarification.display import create_skip_context, display_quick_questions

def execute_clarification():
    """Execute implementation planning clarification for TASK-FBSDK-002."""

    # Task context
    task_context = TaskContext(
        task_id="TASK-FBSDK-002",
        title="Write task_work_results.json after SDK parse in AgentInvoker",
        description=(
            "When AgentInvoker.invoke_player() delegates to task-work via SDK, "
            "it parses the stream output using TaskWorkStreamParser but never "
            "persists the parsed results to disk. The CoachValidator expects to "
            "read quality gate results from .guardkit/autobuild/{task_id}/task_work_results.json, "
            "but this file is never created."
        ),
        acceptance_criteria=[
            "task_work_results.json is created after successful SDK execution",
            "task_work_results.json contains quality gate data (tests, coverage, arch review)",
            "CoachValidator can read and parse the results file",
            "File is created even on timeout (with partial data)",
            "Unit tests verify file creation",
            "Integration test confirms Coach validation succeeds",
        ],
        complexity_score=5,
    )

    # Complexity 5 = Quick mode (15s timeout) per thresholds table
    mode = ClarificationMode.QUICK

    print("\n" + "="*80)
    print("Implementation Planning Clarification")
    print("="*80)
    print(f"Task: {task_context.task_id}")
    print(f"Title: {task_context.title}")
    print(f"Complexity: {task_context.complexity_score}/10")
    print(f"Mode: QUICK (15s timeout)")
    print("="*80 + "\n")

    # Generate questions
    questions = generate_planning_questions(
        task_context=task_context,
        complexity_score=5,
        codebase_context=None,
        mode=mode
    )

    if not questions:
        print("No clarification questions needed for this task.")
        context = create_skip_context("no_questions_needed")
        context.context_type = "implementation_planning"
        return context

    print(f"Generated {len(questions)} questions based on task analysis.\n")

    # Display questions for visibility
    print(display_quick_questions(questions, timeout_seconds=15))

    # Since we're in automated execution (Claude agent), apply defaults
    # In interactive mode, this would collect user input with timeout
    print("\n⏱️  Auto-proceeding with defaults (automated execution)")

    user_responses = {}
    for question in questions:
        user_responses[question.id] = question.default

    # Process responses into context
    context = process_responses(questions, user_responses, mode)
    context.context_type = "implementation_planning"
    context.mode = "quick"

    print(f"\n✓ Recorded {len(context.explicit_decisions) + len(context.assumed_defaults)} decision(s)")

    return context


if __name__ == "__main__":
    try:
        context = execute_clarification()

        print("\n" + "="*80)
        print("Clarification Complete")
        print("="*80)
        print(f"Context Type: {context.context_type}")
        print(f"Mode: {context.mode}")
        print(f"Total Questions: {context.total_questions}")
        print(f"Answered: {context.answered_count}")
        print(f"Skipped: {context.skipped_count}")

        if context.explicit_decisions:
            print("\nExplicit Decisions:")
            for decision in context.explicit_decisions:
                print(f"  - {decision.question_text}")
                print(f"    Answer: {decision.answer_display}")
                print(f"    Rationale: {decision.rationale}")

        if context.assumed_defaults:
            print("\nAssumed Defaults:")
            for decision in context.assumed_defaults:
                print(f"  - {decision.question_text}")
                print(f"    Answer: {decision.answer_display}")

        print("="*80 + "\n")

        # Output structured YAML for integration
        print("="*80)
        print("YAML Output (for integration with task-work):")
        print("="*80)
        print("clarification_context:")
        print(f"  context_type: {context.context_type}")
        print(f"  mode: {context.mode}")
        print(f"  total_questions: {context.total_questions}")
        print(f"  answered_count: {context.answered_count}")
        print(f"  skipped_count: {context.skipped_count}")

        if context.explicit_decisions:
            print("  explicit_decisions:")
            for d in context.explicit_decisions:
                print(f"    - question_id: {d.question_id}")
                print(f"      category: {d.category}")
                print(f"      question_text: \"{d.question_text}\"")
                print(f"      answer: {d.answer}")
                print(f"      answer_display: \"{d.answer_display}\"")
                print(f"      default_used: {d.default_used}")
                print(f"      rationale: \"{d.rationale}\"")

        if context.assumed_defaults:
            print("  assumed_defaults:")
            for d in context.assumed_defaults:
                print(f"    - question_id: {d.question_id}")
                print(f"      category: {d.category}")
                print(f"      question_text: \"{d.question_text}\"")
                print(f"      answer: {d.answer}")
                print(f"      answer_display: \"{d.answer_display}\"")
                print(f"      default_used: {d.default_used}")
                print(f"      rationale: \"{d.rationale}\"")

        print("="*80 + "\n")

        # Return exit code 0 for success
        sys.exit(0)

    except Exception as e:
        import traceback
        print(f"\n⚠️  Clarification error: {e}")
        print(traceback.format_exc())
        print("\nReturning empty context to allow workflow to continue.")

        # Create error context (fail-safe strategy)
        context = ClarificationContext(
            context_type="implementation_planning",
            explicit_decisions=[],
            assumed_defaults=[],
            not_applicable=[],
            total_questions=0,
            answered_count=0,
            skipped_count=0,
            mode="skip",
            timestamp="",
            user_override="error",
        )

        sys.exit(0)
