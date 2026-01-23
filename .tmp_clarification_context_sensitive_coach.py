#!/usr/bin/env python3
"""
Clarification for Context-Sensitive Coach Feature Review
"""

import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, '/Users/richardwoollcott/.agentecflow/lib')
sys.path.insert(0, '/Users/richardwoollcott/Projects/appmilla_github/guardkit/installer/core/commands/lib')

from clarification.core import (
    ClarificationContext,
    ClarificationMode,
    Question,
    Decision
)

def generate_questions():
    """Generate review scope clarification questions."""

    questions = [
        Question(
            id="review_focus",
            category="scope",
            question_text="What should be the primary focus of this architectural review?",
            options=[
                "A - Architecture and design patterns (tier strategy, plugin system)",
                "T - Technical implementation (tree-sitter, AST analysis, caching)",
                "P - Performance and optimization (latency budget, incremental analysis)",
                "I - Integration and compatibility (multi-language support, fallback)",
                "B - Balanced (equal attention to all aspects)"
            ],
            default="B",
            rationale="Feature involves complex multi-tier architecture, performance-critical analysis, and language-agnostic design. Balanced review recommended."
        ),
        Question(
            id="tradeoff_priority",
            category="implementation",
            question_text="If trade-offs are needed, what should be prioritized?",
            options=[
                "S - Speed (minimize latency, aggressive caching)",
                "Q - Quality (thorough analysis, deeper insights)",
                "C - Cost (minimize complexity, fewer dependencies)",
                "M - Maintainability (clear abstractions, extensible)",
                "B - Balanced (context-dependent trade-offs)"
            ],
            default="M",
            rationale="This is infrastructure code that will be extended with language plugins. Maintainability and extensibility are critical."
        ),
        Question(
            id="language_plugin_scope",
            category="scope",
            question_text="Should the initial implementation include language-specific plugins?",
            options=[
                "Y - Yes, implement Python + TypeScript plugins (Tier 3)",
                "P - Python only (most critical for current use)",
                "N - No, Tier 1 + Tier 2 (universal + tree-sitter) only",
                "R - Recommend based on effort/value"
            ],
            default="R",
            rationale="Proposal includes 3-tier strategy. Tier 3 plugins are optional but provide deep pattern recognition."
        ),
        Question(
            id="performance_constraints",
            category="technical",
            question_text="How strict should the latency budget be enforced?",
            options=[
                "S - Strict (<1 second total, fail if exceeded)",
                "R - Relaxed (1-2 seconds acceptable for complex changes)",
                "O - Optimize for typical case (fast for simple, slower for complex)",
                "D - Default (follow proposal's tiered approach)"
            ],
            default="D",
            rationale="Proposal already defines tiered latency budgets (Tier 1: <100ms, Tier 2: <500ms, Tier 3: <300ms)."
        ),
        Question(
            id="validation_concerns",
            category="scope",
            question_text="Are there specific validation or edge cases that need extra attention?",
            options=[
                "E - Edge cases (very large diffs, many files, complex patterns)",
                "F - Fallback behavior (when tree-sitter or plugins fail)",
                "C - Classification accuracy (scope detection thresholds)",
                "I - Integration (how to integrate with existing Coach)",
                "N - None, general review is sufficient"
            ],
            default="F",
            rationale="Language-agnostic design requires robust fallback when advanced analysis unavailable."
        )
    ]

    return questions


def collect_responses(questions: list) -> ClarificationContext:
    """Collect user responses with full mode (complexity=8)."""

    print("\n" + "="*80)
    print("Review Scope Clarification")
    print("="*80)
    print("\nFeature: Context-Sensitive Coach (Adaptive Quality Gates)")
    print("Complexity: 8/10 (multi-tier architecture, performance-critical)")
    print("\nPlease answer the following questions to guide the architectural review.")
    print("Press Enter to accept the default answer shown in [brackets].\n")

    responses = {}

    for i, q in enumerate(questions, 1):
        print(f"\nQuestion {i}/{len(questions)}: {q.question_text}")
        print("\nOptions:")
        for option in q.options:
            option_code = option.split(" - ")[0]
            if option_code == q.default:
                print(f"  {option} [DEFAULT]")
            else:
                print(f"  {option}")

        print(f"\nDefault: {q.default}")

        while True:
            answer = input(f"\nYour answer [{q.default}]: ").strip().upper()

            if not answer:
                answer = q.default
                print(f"Using default: {answer}")
                break

            # Validate answer
            valid_options = [opt.split(" - ")[0] for opt in q.options]
            if answer in valid_options:
                break
            else:
                print(f"Invalid answer. Please choose from: {', '.join(valid_options)}")

        responses[q.id] = answer

    # Process responses into decisions
    explicit_decisions = []
    assumed_defaults = []

    for q in questions:
        answer = responses.get(q.id, q.default)
        answer_option = next(
            (opt for opt in q.options if opt.startswith(answer + " - ")),
            answer
        )
        answer_display = answer_option.split(" - ", 1)[1] if " - " in answer_option else answer

        decision = Decision(
            question_id=q.id,
            category=q.category,
            question_text=q.question_text,
            answer=answer,
            answer_display=answer_display,
            default_used=(answer == q.default),
            rationale=q.rationale if answer == q.default else f"User selected: {answer_display}"
        )

        if answer == q.default:
            assumed_defaults.append(decision)
        else:
            explicit_decisions.append(decision)

    # Create context
    context = ClarificationContext(
        context_type="review_scope",
        explicit_decisions=explicit_decisions,
        assumed_defaults=assumed_defaults,
        not_applicable=[],
        total_questions=len(questions),
        answered_count=len(responses),
        skipped_count=0,
        mode="full",
        timestamp=datetime.now().isoformat()
    )

    return context


def display_summary(context: ClarificationContext):
    """Display clarification summary."""

    print("\n" + "="*80)
    print("Clarification Summary")
    print("="*80)

    if context.explicit_decisions:
        print("\nExplicit Decisions:")
        for d in context.explicit_decisions:
            print(f"  - {d.question_text}")
            print(f"    Answer: {d.answer_display}")
            print(f"    Rationale: {d.rationale}")

    if context.assumed_defaults:
        print("\nAssumed Defaults:")
        for d in context.assumed_defaults:
            print(f"  - {d.question_text}")
            print(f"    Default: {d.answer_display}")

    print("\n" + "="*80)
    print("Review Focus Areas:")
    print("="*80)

    # Extract focus areas from responses
    focus_areas = []

    for d in context.explicit_decisions + context.assumed_defaults:
        if d.question_id == "review_focus":
            if d.answer == "A":
                focus_areas.append("Architecture and design patterns")
            elif d.answer == "T":
                focus_areas.append("Technical implementation details")
            elif d.answer == "P":
                focus_areas.append("Performance and optimization")
            elif d.answer == "I":
                focus_areas.append("Integration and compatibility")
            else:
                focus_areas.append("All aspects (balanced review)")

        elif d.question_id == "tradeoff_priority":
            if d.answer == "S":
                focus_areas.append("Priority: Speed/performance")
            elif d.answer == "Q":
                focus_areas.append("Priority: Analysis quality")
            elif d.answer == "C":
                focus_areas.append("Priority: Cost/complexity")
            elif d.answer == "M":
                focus_areas.append("Priority: Maintainability")
            else:
                focus_areas.append("Priority: Balanced")

        elif d.question_id == "language_plugin_scope":
            if d.answer == "Y":
                focus_areas.append("Include Python + TypeScript plugins")
            elif d.answer == "P":
                focus_areas.append("Include Python plugin only")
            elif d.answer == "N":
                focus_areas.append("Universal + tree-sitter only (no plugins)")
            else:
                focus_areas.append("Plugin scope: AI recommendation")

        elif d.question_id == "performance_constraints":
            if d.answer == "S":
                focus_areas.append("Strict latency budget (<1s)")
            elif d.answer == "R":
                focus_areas.append("Relaxed latency (1-2s acceptable)")
            elif d.answer == "O":
                focus_areas.append("Optimize for typical case")
            else:
                focus_areas.append("Follow proposal's latency budget")

        elif d.question_id == "validation_concerns":
            if d.answer == "E":
                focus_areas.append("Extra attention: Edge cases")
            elif d.answer == "F":
                focus_areas.append("Extra attention: Fallback behavior")
            elif d.answer == "C":
                focus_areas.append("Extra attention: Classification accuracy")
            elif d.answer == "I":
                focus_areas.append("Extra attention: Integration")

    for area in focus_areas:
        print(f"  - {area}")

    print("\n" + "="*80 + "\n")


def main():
    """Execute clarification workflow."""

    # Generate questions
    questions = generate_questions()

    # Collect responses
    context = collect_responses(questions)

    # Display summary
    display_summary(context)

    # Export context as JSON for next phase
    import json
    output_file = Path("/Users/richardwoollcott/Projects/appmilla_github/guardkit/.tmp_clarification_result.json")
    output_file.write_text(json.dumps(context.to_dict(), indent=2))

    print(f"Clarification context saved to: {output_file}")
    print("\nNext: Use this context to guide architectural review of context-sensitive-coach-proposal.md\n")


if __name__ == "__main__":
    main()
