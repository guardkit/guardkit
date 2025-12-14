#!/usr/bin/env python3
"""Execute review scope clarification for feature planning."""

import sys
sys.path.insert(0, '/Users/richardwoollcott/.agentecflow/lib')
sys.path.insert(0, '/Users/richardwoollcott/Projects/appmilla_github/guardkit/installer/core/commands/lib')

from clarification.core import ClarificationMode, should_clarify
from clarification.generators.review_generator import generate_review_questions
from clarification.display import collect_full_responses

# Context for this feature planning task
task_context = {
    "task_id": "FEATURE-INFRA",
    "title": "Build out the application infrastructure for a FastAPI Python backend",
    "description": "Set up full infrastructure for greenfield FastAPI project",
    "feature_areas": [
        "Database configuration and models",
        "API structure and routing",
        "Authentication system",
        "Testing infrastructure"
    ]
}

# Flags from user request
flags = {
    "no_questions": False,
    "with_questions": False,
    "defaults": False,
    "answers": None,
    "reclarify": False
}

# Configuration
complexity = 8
review_mode = "architectural"  # For infrastructure review
context_type = "review_scope"

# Determine mode (complexity 8 = FULL mode)
mode = should_clarify("review", complexity=complexity, flags=flags)
print(f"Clarification mode: {mode.name}\n")

# Generate questions
questions = generate_review_questions(
    task_context=task_context,
    review_mode=review_mode,
    complexity=complexity
)

print(f"Generated {len(questions)} questions\n")
print("=" * 80)
print("INFRASTRUCTURE CLARIFYING QUESTIONS")
print("=" * 80)
print()

# Collect responses
context = collect_full_responses(
    questions=questions,
    task_id="FEATURE-INFRA",
    task_title=task_context["title"],
    complexity=complexity
)

context.context_type = context_type

# Output results
print("\n" + "=" * 80)
print("CLARIFICATION SUMMARY")
print("=" * 80)
print(f"\nContext Type: {context.context_type}")
print(f"Mode: {context.mode}")
print(f"Total Questions: {context.total_questions}")
print(f"Explicit Decisions: {len(context.explicit_decisions)}")
print(f"Defaults Used: {len(context.assumed_defaults)}")
print()

if context.explicit_decisions:
    print("USER DECISIONS:")
    for decision in context.explicit_decisions:
        print(f"  • {decision['question_text']}")
        print(f"    → {decision['answer_display']}")
        print()

if context.assumed_defaults:
    print("DEFAULTS APPLIED:")
    for default in context.assumed_defaults:
        print(f"  • {default['question_text']}")
        print(f"    → {default['answer_display']}")
        print()
