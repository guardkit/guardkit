"""
Task Review Orchestrator

Core orchestrator for /task-review command that provides structured analysis
and decision-making workflows separate from implementation workflows.

Phase 1: Load Review Context
Phase 2: Execute Review Analysis (skeleton)
Phase 3: Synthesize Recommendations (skeleton)
Phase 4: Generate Review Report (skeleton)
Phase 5: Human Decision Checkpoint (skeleton)

Phases 2-5 are skeleton implementations to be enhanced in subsequent tasks.
"""

import sys
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from task_utils import (
    read_task_file,
    update_task_frontmatter,
    parse_task_frontmatter,
    write_task_frontmatter
)


# Valid review modes
VALID_REVIEW_MODES = {
    "architectural",
    "code-quality",
    "decision",
    "technical-debt",
    "security"
}

# Valid review depths
VALID_REVIEW_DEPTHS = {
    "quick",
    "standard",
    "comprehensive"
}

# Valid output formats
VALID_OUTPUT_FORMATS = {
    "summary",
    "detailed",
    "presentation"
}


def validate_review_mode(mode: str) -> None:
    """
    Validate review mode parameter.

    Args:
        mode: Review mode to validate

    Raises:
        ValueError: If mode is not in VALID_REVIEW_MODES
    """
    if mode not in VALID_REVIEW_MODES:
        valid_modes = ", ".join(sorted(VALID_REVIEW_MODES))
        raise ValueError(
            f"Invalid review mode '{mode}'. "
            f"Allowed modes: {valid_modes}"
        )


def validate_review_depth(depth: str) -> None:
    """
    Validate review depth parameter.

    Args:
        depth: Review depth to validate

    Raises:
        ValueError: If depth is not in VALID_REVIEW_DEPTHS
    """
    if depth not in VALID_REVIEW_DEPTHS:
        valid_depths = ", ".join(sorted(VALID_REVIEW_DEPTHS))
        raise ValueError(
            f"Invalid review depth '{depth}'. "
            f"Allowed depths: {valid_depths}"
        )


def validate_output_format(output: str) -> None:
    """
    Validate output format parameter.

    Args:
        output: Output format to validate

    Raises:
        ValueError: If output is not in VALID_OUTPUT_FORMATS
    """
    if output not in VALID_OUTPUT_FORMATS:
        valid_formats = ", ".join(sorted(VALID_OUTPUT_FORMATS))
        raise ValueError(
            f"Invalid output format '{output}'. "
            f"Allowed formats: {valid_formats}"
        )


def find_task_file(task_id: str, base_dir: Path = Path("tasks")) -> Optional[Path]:
    """
    Find task file by ID across all task directories.

    Args:
        task_id: Task ID (e.g., TASK-XXX)
        base_dir: Base tasks directory

    Returns:
        Path to task file if found, None otherwise
    """
    # Check all task state directories
    task_dirs = [
        "backlog",
        "in_progress",
        "in_review",
        "blocked",
        "completed",
        "review_complete"  # New state for completed reviews
    ]

    for dir_name in task_dirs:
        dir_path = base_dir / dir_name
        if not dir_path.exists():
            continue

        # Look for files starting with task_id
        for task_file in dir_path.glob(f"{task_id}*.md"):
            return task_file

    return None


def load_review_context(task_id: str, base_dir: Path = Path("tasks")) -> Dict[str, Any]:
    """
    Phase 1: Load review context from task file.

    Loads task metadata, description, acceptance criteria, and review scope.
    This is a full implementation (not a skeleton).

    Args:
        task_id: Task ID (e.g., TASK-XXX)

    Returns:
        Dictionary containing review context:
        - task_id: Task identifier
        - title: Task title
        - description: Task description
        - acceptance_criteria: List of acceptance criteria
        - review_scope: Review scope from task
        - metadata: Full task frontmatter
        - file_path: Path to task file

    Raises:
        FileNotFoundError: If task file not found
        ValueError: If task file has invalid format
    """
    print(f"\n{'='*60}")
    print(f"Phase 1: Load Review Context")
    print(f"{'='*60}")
    print(f"Task ID: {task_id}")

    # Find task file
    task_file = find_task_file(task_id, base_dir)
    if not task_file:
        raise FileNotFoundError(
            f"Task {task_id} not found in any task directory. "
            f"Check that task exists in tasks/backlog/, tasks/in_progress/, etc."
        )

    print(f"Found task file: {task_file}")

    # Read task file
    try:
        frontmatter, body = read_task_file(task_file)
    except Exception as e:
        raise ValueError(f"Failed to parse task file {task_file}: {e}")

    # Extract sections from body
    sections = _parse_task_body(body)

    # Build review context
    context = {
        "task_id": task_id,
        "title": frontmatter.get("title", ""),
        "description": sections.get("description", ""),
        "acceptance_criteria": sections.get("acceptance_criteria", []),
        "review_scope": sections.get("review_scope", ""),
        "metadata": frontmatter,
        "file_path": str(task_file),
        "body": body
    }

    # Print context summary
    print(f"\nReview Context Loaded:")
    print(f"  Title: {context['title']}")
    print(f"  Status: {frontmatter.get('status', 'unknown')}")
    print(f"  Task Type: {frontmatter.get('task_type', 'not specified')}")
    print(f"  Review Mode: {frontmatter.get('review_mode', 'not specified')}")
    print(f"  Review Depth: {frontmatter.get('review_depth', 'not specified')}")

    return context


def _parse_task_body(body: str) -> Dict[str, Any]:
    """
    Parse task body to extract sections.

    Args:
        body: Markdown body content

    Returns:
        Dictionary with parsed sections
    """
    sections = {
        "description": "",
        "acceptance_criteria": [],
        "review_scope": ""
    }

    # Simple section extraction (can be enhanced later)
    lines = body.split('\n')
    current_section = None

    for line in lines:
        line_stripped = line.strip()

        # Detect section headers
        if line_stripped.startswith('## Description'):
            current_section = "description"
            continue
        elif line_stripped.startswith('## Acceptance Criteria'):
            current_section = "acceptance_criteria"
            continue
        elif line_stripped.startswith('## Review Scope'):
            current_section = "review_scope"
            continue
        elif line_stripped.startswith('##'):
            current_section = None
            continue

        # Accumulate content
        if current_section == "description":
            sections["description"] += line + "\n"
        elif current_section == "acceptance_criteria":
            if line_stripped.startswith('- ['):
                sections["acceptance_criteria"].append(line_stripped[6:])
        elif current_section == "review_scope":
            sections["review_scope"] += line + "\n"

    return sections


def execute_review_analysis(
    task_context: Dict[str, Any],
    mode: str,
    depth: str
) -> Dict[str, Any]:
    """
    Phase 2: Execute review analysis (SKELETON).

    Will be enhanced in Phase 2 task to invoke appropriate agents
    and perform actual analysis.

    Args:
        task_context: Context from Phase 1
        mode: Review mode (architectural, code-quality, etc.)
        depth: Review depth (quick, standard, comprehensive)

    Returns:
        Dictionary containing review findings
    """
    print(f"\n{'='*60}")
    print(f"Phase 2: Execute Review Analysis (SKELETON)")
    print(f"{'='*60}")
    print(f"Mode: {mode}")
    print(f"Depth: {depth}")
    print(f"\n[Skeleton] This phase will be enhanced in future tasks to:")
    print(f"  - Invoke appropriate review agents based on mode")
    print(f"  - Perform analysis using specialized prompts")
    print(f"  - Generate findings with evidence")
    print(f"  - Score/rate based on review criteria")

    return {
        "findings": [],
        "mode": mode,
        "depth": depth,
        "score": None,
        "evidence": []
    }


def synthesize_recommendations(review_results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Phase 3: Synthesize recommendations (SKELETON).

    Will be enhanced in Phase 3 task to aggregate findings
    and generate actionable recommendations.

    Args:
        review_results: Results from Phase 2

    Returns:
        Dictionary containing recommendations
    """
    print(f"\n{'='*60}")
    print(f"Phase 3: Synthesize Recommendations (SKELETON)")
    print(f"{'='*60}")
    print(f"\n[Skeleton] This phase will be enhanced in future tasks to:")
    print(f"  - Aggregate findings from multiple agents")
    print(f"  - Generate actionable recommendations")
    print(f"  - Identify decision options")
    print(f"  - Prioritize recommendations by impact")

    return {
        "recommendations": [],
        "confidence": "medium",
        "decision_options": []
    }


def generate_review_report(
    review_results: Dict[str, Any],
    recommendations: Dict[str, Any],
    output: str
) -> str:
    """
    Phase 4: Generate review report (SKELETON).

    Will be enhanced in Phase 3 task to create comprehensive
    markdown reports in various formats.

    Args:
        review_results: Results from Phase 2
        recommendations: Recommendations from Phase 3
        output: Output format (summary, detailed, presentation)

    Returns:
        Markdown report string
    """
    print(f"\n{'='*60}")
    print(f"Phase 4: Generate Review Report (SKELETON)")
    print(f"{'='*60}")
    print(f"Output Format: {output}")
    print(f"\n[Skeleton] This phase will be enhanced in future tasks to:")
    print(f"  - Create structured markdown report")
    print(f"  - Include executive summary")
    print(f"  - Document findings with evidence")
    print(f"  - Provide recommendations with rationale")

    return f"""# Review Report (Placeholder)

**Mode**: {review_results.get('mode', 'unknown')}
**Depth**: {review_results.get('depth', 'unknown')}
**Output Format**: {output}

This is a skeleton implementation. Full report generation
will be implemented in Phase 3 task.
"""


def present_decision_checkpoint(
    report: str,
    recommendations: Dict[str, Any]
) -> str:
    """
    Phase 5: Human decision checkpoint (SKELETON).

    Will be enhanced in Phase 4 task to present findings
    and gather human decisions.

    Args:
        report: Generated report from Phase 4
        recommendations: Recommendations from Phase 3

    Returns:
        Decision string (accept, revise, implement, cancel)
    """
    print(f"\n{'='*60}")
    print(f"Phase 5: Human Decision Checkpoint (SKELETON)")
    print(f"{'='*60}")
    print(f"\n[Skeleton] This phase will be enhanced in future tasks to:")
    print(f"  - Present findings to user")
    print(f"  - Offer decision options:")
    print(f"    [A]ccept - Approve findings, mark task REVIEW_COMPLETE")
    print(f"    [R]evise - Request deeper analysis")
    print(f"    [I]mplement - Create implementation task")
    print(f"    [C]ancel - Discard review, return to backlog")
    print(f"\n[Skeleton] Auto-accepting for now (default behavior)")

    return "accept"


def handle_review_decision(
    task_id: str,
    decision: str,
    recommendations: Dict[str, Any]
) -> None:
    """
    Handle user decision after review.

    Args:
        task_id: Task ID
        decision: Decision (accept, revise, implement, cancel)
        recommendations: Recommendations from Phase 3
    """
    print(f"\n{'='*60}")
    print(f"Handling Decision: {decision}")
    print(f"{'='*60}")

    task_file = find_task_file(task_id)
    if not task_file:
        print(f"Warning: Could not find task file to update state")
        return

    if decision == "accept":
        # Move task to review_complete state
        print(f"Moving task to REVIEW_COMPLETE state...")
        _update_task_state(task_file, "review_complete")
    elif decision == "cancel":
        # Return task to backlog
        print(f"Returning task to BACKLOG state...")
        _update_task_state(task_file, "backlog")
    else:
        # For revise and implement, keep in current state
        print(f"Task remains in current state for {decision} action")


def _update_task_state(task_file: Path, new_state: str) -> None:
    """
    Update task state by moving file and updating frontmatter.

    Args:
        task_file: Current task file path
        new_state: New state directory name
    """
    # Read current task
    frontmatter, body = read_task_file(task_file)

    # Update status in frontmatter
    frontmatter['status'] = new_state
    frontmatter['updated'] = datetime.utcnow().isoformat() + 'Z'

    # Determine new path
    base_dir = task_file.parent.parent
    new_dir = base_dir / new_state

    # Create directory if it doesn't exist
    new_dir.mkdir(exist_ok=True)

    new_path = new_dir / task_file.name

    # Write updated task to new location
    content = write_task_frontmatter(frontmatter, body)
    new_path.write_text(content, encoding='utf-8')

    # Remove old file
    task_file.unlink()

    print(f"Moved task from {task_file} to {new_path}")


def execute_task_review(
    task_id: str,
    mode: str = "architectural",
    depth: str = "standard",
    output: str = "detailed"
) -> Dict[str, Any]:
    """
    Main orchestrator for task-review command.

    Executes all 5 phases of the review workflow:
    1. Load review context (full implementation)
    2. Execute review analysis (skeleton)
    3. Synthesize recommendations (skeleton)
    4. Generate review report (skeleton)
    5. Human decision checkpoint (skeleton)

    Args:
        task_id: Task ID (e.g., TASK-XXX)
        mode: Review mode (architectural, code-quality, decision, technical-debt, security)
        depth: Review depth (quick, standard, comprehensive)
        output: Output format (summary, detailed, presentation)

    Returns:
        Review results dictionary containing:
        - status: "success" or "error"
        - review_mode: The mode used
        - review_depth: The depth used
        - task_id: The task ID
        - report: Generated report (if successful)
        - error: Error message (if failed)

    Raises:
        ValueError: If invalid parameters provided
        FileNotFoundError: If task not found
    """
    print(f"\n{'#'*60}")
    print(f"# TASK REVIEW: {task_id}")
    print(f"{'#'*60}")
    print(f"Mode: {mode}")
    print(f"Depth: {depth}")
    print(f"Output: {output}")

    try:
        # Validate inputs
        validate_review_mode(mode)
        validate_review_depth(depth)
        validate_output_format(output)

        # Phase 1: Load review context (FULL IMPLEMENTATION)
        task_context = load_review_context(task_id)

        # Update task metadata with review parameters
        task_file = Path(task_context['file_path'])
        update_task_frontmatter(
            task_file,
            {
                'task_type': 'review',
                'review_mode': mode,
                'review_depth': depth,
                'status': 'in_progress'
            }
        )

        # Phase 2: Execute review analysis (SKELETON)
        review_results = execute_review_analysis(task_context, mode, depth)

        # Phase 3: Synthesize recommendations (SKELETON)
        recommendations = synthesize_recommendations(review_results)

        # Phase 4: Generate review report (SKELETON)
        report = generate_review_report(review_results, recommendations, output)

        # Phase 5: Human decision checkpoint (SKELETON)
        decision = present_decision_checkpoint(report, recommendations)

        # Handle decision
        handle_review_decision(task_id, decision, recommendations)

        print(f"\n{'='*60}")
        print(f"REVIEW COMPLETE")
        print(f"{'='*60}")

        return {
            "status": "success",
            "review_mode": mode,
            "review_depth": depth,
            "task_id": task_id,
            "report": report,
            "decision": decision
        }

    except Exception as e:
        print(f"\n{'='*60}")
        print(f"REVIEW FAILED")
        print(f"{'='*60}")
        print(f"Error: {str(e)}")

        return {
            "status": "error",
            "review_mode": mode,
            "review_depth": depth,
            "task_id": task_id,
            "error": str(e)
        }


if __name__ == "__main__":
    # Simple CLI for testing
    import argparse

    parser = argparse.ArgumentParser(description="Task Review Orchestrator")
    parser.add_argument("task_id", help="Task ID (e.g., TASK-XXX)")
    parser.add_argument("--mode", default="architectural",
                        choices=list(VALID_REVIEW_MODES),
                        help="Review mode")
    parser.add_argument("--depth", default="standard",
                        choices=list(VALID_REVIEW_DEPTHS),
                        help="Review depth")
    parser.add_argument("--output", default="detailed",
                        choices=list(VALID_OUTPUT_FORMATS),
                        help="Output format")

    args = parser.parse_args()

    result = execute_task_review(
        args.task_id,
        mode=args.mode,
        depth=args.depth,
        output=args.output
    )

    print(f"\n{'='*60}")
    print(f"RESULT")
    print(f"{'='*60}")
    print(f"Status: {result['status']}")
    if result['status'] == 'success':
        print(f"Decision: {result['decision']}")
        print(f"\nReport:\n{result['report']}")
    else:
        print(f"Error: {result['error']}")
