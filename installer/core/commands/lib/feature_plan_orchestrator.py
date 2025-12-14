"""
Feature Plan Orchestrator

Orchestrates the /feature-plan workflow with proper clarification integration:

Phase 1: Create review task automatically
Phase 2: Execute task review with Context A clarification
Phase 3: Handle [I]mplement decision with Context B clarification
Phase 4: Generate feature structure with subtasks

This module integrates with task_review_orchestrator for Context A and
implements Context B (implementation preferences) clarification.
"""

import sys
import re
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime, timezone

# Add lib directory to path for imports
lib_path = Path(__file__).parent
if str(lib_path) not in sys.path:
    sys.path.insert(0, str(lib_path))

# Import from existing modules
from task_review_orchestrator import execute_task_review
from task_utils import (
    create_task_frontmatter,
    write_task_frontmatter,
    read_task_file,
)
from git_state_helper import get_git_root

# Import clarification infrastructure
try:
    from clarification import (
        ClarificationContext,
        ClarificationMode,
        should_clarify,
        process_responses,
    )
    from clarification.generators.implement_generator import generate_implement_questions
    from clarification.display import (
        collect_full_responses,
        collect_quick_responses,
        create_skip_context,
        display_skip_message,
    )
    CLARIFICATION_AVAILABLE = True
except ImportError:
    CLARIFICATION_AVAILABLE = False
    ClarificationContext = None
    ClarificationMode = None


def execute_feature_plan(
    feature_description: str,
    flags: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Main orchestrator for /feature-plan command.

    Executes complete workflow:
    1. Creates review task automatically
    2. Executes task review with Context A clarification
    3. Handles [I]mplement decision with Context B clarification
    4. Generates feature structure with subtasks

    Args:
        feature_description: Natural language description of feature
        flags: Command-line flags including:
            - no_questions: Skip all clarification (Context A + B)
            - with_questions: Force clarification even for simple features
            - defaults: Use defaults without prompting
            - mode: Review mode (default: "architectural")
            - depth: Review depth (default: "standard")

    Returns:
        Dictionary containing:
            - status: "success" or "error"
            - review_task_id: Created review task ID
            - feature_path: Path to feature directory (if implemented)
            - subtasks: List of created subtask IDs (if implemented)
            - error: Error message (if failed)
            - clarification_a: Context A decisions (if any)
            - clarification_b: Context B decisions (if any)

    Raises:
        ValueError: If feature_description is empty or invalid
        RuntimeError: If review execution or feature generation fails
    """
    print(f"\n{'#'*60}")
    print(f"# FEATURE PLAN: {feature_description}")
    print(f"{'#'*60}")

    if not feature_description or not feature_description.strip():
        raise ValueError("Feature description cannot be empty")

    try:
        # Phase 1: Create review task
        print(f"\n{'='*60}")
        print(f"Phase 1: Create Review Task")
        print(f"{'='*60}")

        review_task_id, complexity = create_review_task(feature_description, flags)

        print(f"Created review task: {review_task_id}")
        print(f"Complexity: {complexity}/10")

        # Phase 2: Execute task review with Context A clarification
        print(f"\n{'='*60}")
        print(f"Phase 2: Execute Task Review")
        print(f"{'='*60}")

        review_mode = flags.get("mode", "architectural")
        review_depth = flags.get("depth", "standard")

        review_result = execute_task_review(
            task_id=review_task_id,
            mode=review_mode,
            depth=review_depth,
            no_questions=flags.get("no_questions", False),
            with_questions=flags.get("with_questions", False),
            defaults=flags.get("defaults", False),
        )

        if review_result["status"] != "success":
            raise RuntimeError(
                f"Review execution failed: {review_result.get('error', 'Unknown error')}"
            )

        clarification_a = review_result.get("clarification")

        # Phase 3: Decision checkpoint
        print(f"\n{'='*60}")
        print(f"Phase 3: Decision Checkpoint")
        print(f"{'='*60}")

        decision = _present_decision_checkpoint(review_result)

        if decision != "implement":
            # User chose Accept/Revise/Cancel - return without feature generation
            return {
                "status": "success",
                "review_task_id": review_task_id,
                "decision": decision,
                "clarification_a": clarification_a,
                "message": f"Review {decision}. No feature structure created.",
            }

        # Phase 4: Context B clarification (if implementing)
        print(f"\n{'='*60}")
        print(f"Phase 4: Implementation Preferences")
        print(f"{'='*60}")

        # Extract number of subtasks from recommendations
        recommendations = review_result.get("recommendations", {}).get("recommendations", [])
        num_subtasks = _estimate_subtask_count(recommendations)

        clarification_b = execute_context_b_clarification(
            review_findings=review_result,
            num_subtasks=num_subtasks,
            flags=flags
        )

        # Phase 5: Generate feature structure
        print(f"\n{'='*60}")
        print(f"Phase 5: Generate Feature Structure")
        print(f"{'='*60}")

        feature_slug = extract_feature_slug(feature_description)
        feature_path, created_count = generate_feature_structure(
            feature_slug=feature_slug,
            recommendations=recommendations,
            clarification=clarification_b,
            flags=flags
        )

        print(f"\n{'='*60}")
        print(f"FEATURE PLAN COMPLETE")
        print(f"{'='*60}")
        print(f"Review Task: {review_task_id}")
        print(f"Feature Path: {feature_path}")
        print(f"Subtasks Created: {created_count}")

        return {
            "status": "success",
            "review_task_id": review_task_id,
            "feature_path": str(feature_path),
            "subtasks_created": created_count,
            "decision": "implement",
            "clarification_a": clarification_a,
            "clarification_b": clarification_b,
        }

    except Exception as e:
        print(f"\n{'='*60}")
        print(f"FEATURE PLAN FAILED")
        print(f"{'='*60}")
        print(f"Error: {str(e)}")

        return {
            "status": "error",
            "error": str(e)
        }


def create_review_task(
    feature_description: str,
    flags: Dict[str, Any]
) -> Tuple[str, int]:
    """
    Create review task for feature planning.

    Args:
        feature_description: Natural language description of feature
        flags: Command-line flags (for task metadata)

    Returns:
        Tuple of (task_id, complexity_score)

    Raises:
        ValueError: If task creation fails
    """
    # Generate task ID (simplified hash-based ID)
    task_id = _generate_task_id(feature_description, prefix="REV")

    # Estimate complexity from description
    complexity = _estimate_complexity(feature_description)

    # Create task frontmatter
    frontmatter = create_task_frontmatter(
        task_id=task_id,
        title=f"Review: {feature_description}",
        priority=flags.get("priority", "medium"),
        complexity=complexity,
        task_type="review",
        review_mode=flags.get("mode", "architectural"),
        review_depth=flags.get("depth", "standard"),
    )

    # Create task body
    body = f"""
## Description

Architectural review for feature: {feature_description}

This review will analyze:
- Implementation approach
- Architectural patterns
- Integration points
- Subtask breakdown

## Review Scope

**Feature**: {feature_description}

**Expected Deliverables**:
- Recommended implementation approach
- Subtask breakdown with dependencies
- Risk assessment
- Effort estimation

## Acceptance Criteria

- [ ] Implementation approach recommended
- [ ] Subtasks identified with dependencies
- [ ] Risks documented
- [ ] Decision options presented
"""

    # Write task file
    git_root = get_git_root()
    tasks_dir = git_root / "tasks" / "backlog"
    tasks_dir.mkdir(parents=True, exist_ok=True)

    task_file = tasks_dir / f"{task_id}.md"
    content = write_task_frontmatter(frontmatter, body)
    task_file.write_text(content, encoding="utf-8")

    return task_id, complexity


def execute_context_b_clarification(
    review_findings: Dict[str, Any],
    num_subtasks: int,
    flags: Dict[str, Any]
) -> Optional[ClarificationContext]:
    """
    Handle Context B clarification (implementation preferences).

    Asks questions about how to implement the feature based on review findings:
    - Which recommended approach to follow
    - Parallel vs sequential execution
    - Testing depth preferences
    - Workspace naming for Conductor

    Args:
        review_findings: Review report data from task_review_orchestrator
        num_subtasks: Estimated number of subtasks
        flags: Command-line flags including:
            - no_questions: Skip clarification
            - with_questions: Force clarification
            - defaults: Use defaults without prompting

    Returns:
        ClarificationContext with implementation preferences, or None if skipped

    Raises:
        RuntimeError: If question generation fails
    """
    if not CLARIFICATION_AVAILABLE:
        print("Clarification module not available, skipping Context B...")
        return None

    # Extract complexity from review task
    complexity = review_findings.get("task_context", {}).get("metadata", {}).get("complexity", 5)

    print(f"Subtasks: {num_subtasks}")
    print(f"Complexity: {complexity}")

    # Determine clarification mode
    clarification_mode = should_clarify("implement_prefs", complexity, flags)
    print(f"Clarification Mode: {clarification_mode.value}")

    # Handle SKIP mode
    if clarification_mode == ClarificationMode.SKIP:
        print(display_skip_message("trivial" if complexity <= 3 else "flag", complexity))
        return create_skip_context("skip")

    # Handle USE_DEFAULTS mode
    if clarification_mode == ClarificationMode.USE_DEFAULTS:
        print("Using defaults without prompting (--defaults flag)")
        questions = generate_implement_questions(
            review_findings=review_findings,
            num_subtasks=num_subtasks,
            complexity=complexity
        )
        if not questions:
            return create_skip_context("no_questions")

        # Create context with all defaults
        user_responses = {q.id: q.default for q in questions}
        context = process_responses(questions, user_responses, clarification_mode)
        context.context_type = "implementation_prefs"
        context.mode = "defaults"
        print(f"Applied defaults for {len(questions)} question(s)")
        return context

    # Generate questions
    try:
        questions = generate_implement_questions(
            review_findings=review_findings,
            num_subtasks=num_subtasks,
            complexity=complexity
        )
    except Exception as e:
        raise RuntimeError(f"Failed to generate implementation questions: {e}")

    if not questions:
        print("No implementation preference questions generated")
        return None

    print(f"Generated {len(questions)} implementation question(s)")

    # Get task info for display
    task_id = review_findings.get("task_id", "UNKNOWN")
    task_title = f"Implementation preferences for {num_subtasks} subtasks"

    # Display questions and collect responses based on mode
    if clarification_mode == ClarificationMode.FULL:
        clarification = collect_full_responses(
            questions=questions,
            task_id=task_id,
            task_title=task_title,
            complexity=complexity
        )
    else:  # QUICK mode
        clarification = collect_quick_responses(
            questions=questions,
            timeout_seconds=15
        )

    # Set context type
    if clarification:
        clarification.context_type = "implementation_prefs"

    return clarification


def generate_feature_structure(
    feature_slug: str,
    recommendations: List[Dict[str, Any]],
    clarification: Optional[ClarificationContext],
    flags: Dict[str, Any]
) -> Tuple[Path, int]:
    """
    Generate feature folder with README, implementation guide, and subtasks.

    Creates structure:
        tasks/backlog/{feature_slug}/
        ├── README.md
        ├── IMPLEMENTATION-GUIDE.md
        ├── TASK-{slug}-001-{name}.md
        ├── TASK-{slug}-002-{name}.md
        └── ...

    Args:
        feature_slug: Kebab-case feature identifier (e.g., "user-auth")
        recommendations: List of recommendations from review
        clarification: Context B decisions (implementation preferences)
        flags: Command-line flags

    Returns:
        Tuple of (feature_directory_path, subtask_count)

    Raises:
        ValueError: If feature structure creation fails
    """
    git_root = get_git_root()
    feature_dir = git_root / "tasks" / "backlog" / feature_slug
    feature_dir.mkdir(parents=True, exist_ok=True)

    print(f"Creating feature structure in: {feature_dir}")

    # Generate README.md
    readme_path = feature_dir / "README.md"
    readme_content = _generate_feature_readme(feature_slug, recommendations, clarification)
    readme_path.write_text(readme_content, encoding="utf-8")
    print(f"Created: {readme_path.name}")

    # Generate IMPLEMENTATION-GUIDE.md
    guide_path = feature_dir / "IMPLEMENTATION-GUIDE.md"
    guide_content = _generate_implementation_guide(feature_slug, recommendations, clarification)
    guide_path.write_text(guide_content, encoding="utf-8")
    print(f"Created: {guide_path.name}")

    # Generate subtasks
    subtask_count = 0
    for i, rec in enumerate(recommendations, 1):
        task_name = _extract_task_name(rec)
        task_id = f"TASK-{feature_slug.upper()}-{i:03d}"

        subtask_path = feature_dir / f"{task_id}-{task_name}.md"
        subtask_content = _generate_subtask(task_id, rec, clarification)
        subtask_path.write_text(subtask_content, encoding="utf-8")
        print(f"Created: {subtask_path.name}")
        subtask_count += 1

    return feature_dir, subtask_count


def extract_feature_slug(feature_description: str) -> str:
    """
    Convert feature description to kebab-case slug.

    Args:
        feature_description: Natural language description

    Returns:
        Kebab-case slug suitable for directory names

    Examples:
        >>> extract_feature_slug("Add user authentication")
        'user-authentication'
        >>> extract_feature_slug("Implement dark mode toggle")
        'dark-mode-toggle'
    """
    # Remove common prefixes
    description = feature_description.lower()
    for prefix in ["add ", "implement ", "create ", "build "]:
        if description.startswith(prefix):
            description = description[len(prefix):]

    # Convert to kebab-case
    # Remove special characters, replace spaces with hyphens
    slug = re.sub(r'[^a-z0-9\s-]', '', description)
    slug = re.sub(r'\s+', '-', slug.strip())
    slug = re.sub(r'-+', '-', slug)

    return slug


# =============================================================================
# Private Helper Functions
# =============================================================================

def _generate_task_id(description: str, prefix: str = "TASK") -> str:
    """Generate hash-based task ID."""
    import hashlib
    hash_input = f"{description}{datetime.now(timezone.utc).isoformat()}"
    hash_value = hashlib.sha256(hash_input.encode()).hexdigest()[:4]
    return f"{prefix}-{hash_value}"


def _estimate_complexity(description: str) -> int:
    """Estimate complexity from feature description (simplified)."""
    # Simple heuristic: word count and keyword detection
    words = description.lower().split()
    word_count = len(words)

    complexity = 3  # Base complexity

    # Adjust based on word count
    if word_count > 10:
        complexity += 2
    elif word_count > 5:
        complexity += 1

    # Adjust based on keywords
    high_complexity_keywords = ["integrate", "migrate", "refactor", "architecture"]
    medium_complexity_keywords = ["implement", "add", "create"]

    for keyword in high_complexity_keywords:
        if keyword in words:
            complexity += 2
            break

    for keyword in medium_complexity_keywords:
        if keyword in words:
            complexity += 1
            break

    return min(complexity, 10)  # Cap at 10


def _estimate_subtask_count(recommendations: List[Dict[str, Any]]) -> int:
    """Estimate number of subtasks from recommendations."""
    if not recommendations:
        return 3  # Default estimate

    # Count explicit subtasks in recommendations
    count = len(recommendations)

    # Apply reasonable limits
    return max(1, min(count, 12))  # Between 1-12 subtasks


def _present_decision_checkpoint(review_result: Dict[str, Any]) -> str:
    """
    Present decision checkpoint to user after review.

    Args:
        review_result: Review execution result

    Returns:
        Decision string: "accept", "revise", "implement", "cancel"
    """
    print(f"\n{'='*60}")
    print(f"Decision Options:")
    print(f"{'='*60}")
    print(f"[A]ccept - Approve findings, mark review complete")
    print(f"[R]evise - Request deeper analysis")
    print(f"[I]mplement - Create feature structure with subtasks")
    print(f"[C]ancel - Discard review")
    print(f"{'='*60}")

    while True:
        choice = input("\nYour decision [A/R/I/C]: ").strip().upper()
        if choice in ["A", "ACCEPT"]:
            return "accept"
        elif choice in ["R", "REVISE"]:
            return "revise"
        elif choice in ["I", "IMPLEMENT"]:
            return "implement"
        elif choice in ["C", "CANCEL"]:
            return "cancel"
        else:
            print("Invalid choice. Please enter A, R, I, or C.")


def _generate_feature_readme(
    feature_slug: str,
    recommendations: List[Dict[str, Any]],
    clarification: Optional[ClarificationContext]
) -> str:
    """Generate README.md for feature folder."""
    return f"""# Feature: {feature_slug.replace('-', ' ').title()}

## Overview

This feature was planned using `/feature-plan` with architectural review and implementation preferences.

## Subtasks

{len(recommendations)} subtasks identified:

{chr(10).join(f"{i}. {rec.get('title', 'Subtask')}" for i, rec in enumerate(recommendations, 1))}

## Implementation Approach

{'Parallel execution recommended' if clarification and any(d.answer == 'parallel' for d in clarification.decisions) else 'Sequential execution'}

## Documentation

- [IMPLEMENTATION-GUIDE.md](./IMPLEMENTATION-GUIDE.md) - Detailed implementation guide

## Generated

- Date: {datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')}
- Method: `/feature-plan`
- Review Mode: Architectural
"""


def _generate_implementation_guide(
    feature_slug: str,
    recommendations: List[Dict[str, Any]],
    clarification: Optional[ClarificationContext]
) -> str:
    """Generate IMPLEMENTATION-GUIDE.md for feature folder."""
    return f"""# Implementation Guide: {feature_slug.replace('-', ' ').title()}

## Execution Strategy

### Wave 1

Execute these tasks first:

{chr(10).join(f"- TASK-{feature_slug.upper()}-{i:03d}" for i in range(1, min(4, len(recommendations)+1)))}

### Wave 2

Execute after Wave 1 completes:

{chr(10).join(f"- TASK-{feature_slug.upper()}-{i:03d}" for i in range(4, len(recommendations)+1)) if len(recommendations) > 3 else "N/A"}

## Total Timeline

**Estimated**: {len(recommendations)} * 2-4 hours = {len(recommendations)*2}-{len(recommendations)*4} hours

## Implementation Preferences

{_format_clarification_decisions(clarification) if clarification else "No preferences recorded"}

## Verification

After all tasks complete:

```bash
# Run tests
pytest tests/ -v

# Verify feature works
# TODO: Add feature-specific verification
```
"""


def _generate_subtask(
    task_id: str,
    recommendation: Dict[str, Any],
    clarification: Optional[ClarificationContext]
) -> str:
    """Generate subtask markdown file."""
    title = recommendation.get("title", "Subtask")

    frontmatter = create_task_frontmatter(
        task_id=task_id,
        title=title,
        priority=recommendation.get("priority", "medium"),
        complexity=recommendation.get("complexity", 5),
    )

    body = f"""
## Description

{recommendation.get('description', 'No description provided')}

## Acceptance Criteria

{chr(10).join(f"- [ ] {criterion}" for criterion in recommendation.get('criteria', ['Complete implementation']))}

## Implementation Notes

{recommendation.get('notes', 'No additional notes')}
"""

    return write_task_frontmatter(frontmatter, body)


def _extract_task_name(recommendation: Dict[str, Any]) -> str:
    """Extract kebab-case task name from recommendation."""
    title = recommendation.get("title", "task")
    name = re.sub(r'[^a-z0-9\s-]', '', title.lower())
    name = re.sub(r'\s+', '-', name.strip())
    name = re.sub(r'-+', '-', name)
    return name[:50]  # Limit length


def _format_clarification_decisions(clarification: ClarificationContext) -> str:
    """Format clarification decisions for markdown."""
    if not clarification or not clarification.decisions:
        return "No decisions recorded"

    lines = []
    for decision in clarification.decisions:
        lines.append(f"- **{decision.category}**: {decision.answer_display}")

    return "\n".join(lines)


# =============================================================================
# Main Entry Point (for testing)
# =============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Feature Plan Orchestrator")
    parser.add_argument("description", help="Feature description")
    parser.add_argument("--mode", default="architectural", help="Review mode")
    parser.add_argument("--depth", default="standard", help="Review depth")
    parser.add_argument("--no-questions", action="store_true", help="Skip clarification")
    parser.add_argument("--with-questions", action="store_true", help="Force clarification")
    parser.add_argument("--defaults", action="store_true", help="Use defaults")

    args = parser.parse_args()

    flags = {
        "mode": args.mode,
        "depth": args.depth,
        "no_questions": args.no_questions,
        "with_questions": args.with_questions,
        "defaults": args.defaults,
    }

    result = execute_feature_plan(args.description, flags)

    print(f"\n{'='*60}")
    print(f"RESULT")
    print(f"{'='*60}")
    print(f"Status: {result['status']}")
    if result['status'] == 'success':
        print(f"Review Task: {result.get('review_task_id')}")
        if 'feature_path' in result:
            print(f"Feature Path: {result['feature_path']}")
            print(f"Subtasks: {result['subtasks_created']}")
    else:
        print(f"Error: {result['error']}")
