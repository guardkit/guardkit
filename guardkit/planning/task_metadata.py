"""
Task metadata enrichment for GuardKit feature planning.

Enriches task definitions with budgets and target-specific metadata,
then renders to markdown format for AutoBuild consumption.

Coverage Target: >=85%
"""

from dataclasses import dataclass
from typing import Optional

from guardkit.planning.spec_parser import TaskDefinition
from guardkit.planning.target_mode import TargetConfig, TargetMode


# Turn budgets by complexity level
TURN_BUDGETS = {
    "low": {"expected": 1, "max": 3},
    "medium": {"expected": 2, "max": 5},
    "high": {"expected": 3, "max": 5},
}

# Graphiti context budgets by complexity level (tokens)
CONTEXT_BUDGETS = {
    "low": 2000,
    "medium": 4000,
    "high": 6000,
}


@dataclass
class EnrichedTask:
    """Task definition enriched with budgets and target configuration.

    Attributes:
        task_definition: The original task definition.
        feature_id: Feature identifier this task belongs to.
        turn_budget: Expected and max turn counts for AutoBuild.
        graphiti_context_budget: Token budget for Graphiti context retrieval.
        target_config: Target mode configuration (interactive vs local model).
        enriched_notes: Additional implementation notes added for target mode.
    """

    task_definition: TaskDefinition
    feature_id: Optional[str]
    turn_budget: dict[str, int]
    graphiti_context_budget: int
    target_config: TargetConfig
    enriched_notes: str = ""


def enrich_task(
    task: TaskDefinition,
    target_config: TargetConfig,
    feature_id: Optional[str],
) -> EnrichedTask:
    """Enrich a task definition with budgets and target-specific metadata.

    Args:
        task: The task definition to enrich.
        target_config: Target mode configuration.
        feature_id: Feature identifier this task belongs to.

    Returns:
        EnrichedTask with budgets and enriched notes.
    """
    # Look up budgets based on complexity (default to medium if invalid)
    turn_budget = TURN_BUDGETS.get(task.complexity, TURN_BUDGETS["medium"])
    graphiti_context_budget = CONTEXT_BUDGETS.get(task.complexity, CONTEXT_BUDGETS["medium"])

    # Generate enriched notes for local models
    enriched_notes = ""
    if target_config.mode == TargetMode.LOCAL_MODEL:
        enriched_notes = _generate_local_model_guidance(task)

    return EnrichedTask(
        task_definition=task,
        feature_id=feature_id,
        turn_budget=turn_budget,
        graphiti_context_budget=graphiti_context_budget,
        target_config=target_config,
        enriched_notes=enriched_notes,
    )


def _generate_local_model_guidance(task: TaskDefinition) -> str:
    """Generate additional implementation guidance for local models.

    Local models benefit from explicit import paths and type hints.

    Args:
        task: The task definition.

    Returns:
        Additional guidance text.
    """
    guidance_parts = []

    # Import guidance
    if task.files_to_create or task.files_to_modify:
        guidance_parts.append(
            "**Import Guidance**: Include full import paths for all dependencies. "
            "For example: `from guardkit.planning.spec_parser import TaskDefinition`"
        )

    # Type hint guidance
    guidance_parts.append(
        "**Type Hints**: Use explicit type hints for all function signatures and class attributes. "
        "Include return types and parameter types."
    )

    return "\n\n".join(guidance_parts)


def render_task_markdown(enriched_task: EnrichedTask) -> str:
    """Render an enriched task to markdown format for AutoBuild.

    Generates YAML frontmatter with metadata and markdown sections for
    description, acceptance criteria, validation commands, constraints,
    and implementation notes.

    Args:
        enriched_task: The enriched task to render.

    Returns:
        Markdown string with YAML frontmatter and sections.
    """
    task = enriched_task.task_definition

    # Extract task ID from name (format: "TASK ID: Title")
    task_id = _extract_task_id(task.name)

    # Build YAML frontmatter
    frontmatter = _build_frontmatter(enriched_task, task_id)

    # Build markdown sections
    sections = []

    # Description section
    sections.append(_build_description_section(task))

    # Acceptance Criteria section
    sections.append(_build_acceptance_criteria_section(task))

    # Coach Validation Commands section
    sections.append(_build_coach_validation_section(task))

    # Player Constraints section
    sections.append(_build_player_constraints_section(task))

    # Implementation Notes section
    sections.append(_build_implementation_notes_section(task, enriched_task))

    # Combine all parts
    markdown_body = "\n\n".join(sections)

    return f"---\n{frontmatter}---\n\n{markdown_body}\n"


def _extract_task_id(task_name: str) -> str:
    """Extract task ID from task name.

    Args:
        task_name: Task name in format "TASK ID: Title" or "TASK-XXX: Title".

    Returns:
        Extracted task ID or the full name if no colon found.
    """
    if ":" in task_name:
        return task_name.split(":", 1)[0].strip()
    return task_name


def _build_frontmatter(enriched_task: EnrichedTask, task_id: str) -> str:
    """Build YAML frontmatter for the task.

    Args:
        enriched_task: The enriched task.
        task_id: The extracted task ID.

    Returns:
        YAML frontmatter string (without delimiters).
    """
    task = enriched_task.task_definition

    lines = [
        f"id: {task_id}",
        f"feature_id: {enriched_task.feature_id}",
        f"complexity: {task.complexity}",
        f"complexity_score: {task.complexity_score}",
        f"type: {task.task_type}",
    ]

    # Add lists (handle empty lists)
    lines.append(_format_yaml_list("domain_tags", task.domain_tags))
    lines.append(_format_yaml_list("files_to_create", task.files_to_create))
    lines.append(_format_yaml_list("files_to_modify", task.files_to_modify))
    lines.append(_format_yaml_list("files_not_to_touch", task.files_not_to_touch))
    lines.append(_format_yaml_list("dependencies", task.dependencies))
    lines.append(_format_yaml_list("relevant_decisions", task.relevant_decisions))

    # Add turn budget
    lines.append("turn_budget:")
    lines.append(f"  expected: {enriched_task.turn_budget['expected']}")
    lines.append(f"  max: {enriched_task.turn_budget['max']}")

    # Add graphiti context budget
    lines.append(f"graphiti_context_budget: {enriched_task.graphiti_context_budget}")

    return "\n".join(lines) + "\n"


def _format_yaml_list(key: str, items: list) -> str:
    """Format a list as YAML.

    Args:
        key: The YAML key name.
        items: The list items.

    Returns:
        YAML formatted list string.
    """
    if not items:
        return f"{key}: []"

    # Single line for short lists, multi-line for longer ones
    if len(items) <= 3 and all(len(str(item)) < 50 for item in items):
        # Single line format
        items_str = ", ".join(str(item) for item in items)
        return f"{key}: [{items_str}]"
    else:
        # Multi-line format
        lines = [f"{key}:"]
        for item in items:
            lines.append(f"  - {item}")
        return "\n".join(lines)


def _build_description_section(task: TaskDefinition) -> str:
    """Build the Description section.

    Args:
        task: The task definition.

    Returns:
        Markdown description section.
    """
    # Extract title from name (after the colon)
    title = task.name.split(":", 1)[1].strip() if ":" in task.name else task.name

    lines = [
        "## Description",
        "",
        title,
        "",
        f"**Inputs**: {task.inputs}",
        f"**Outputs**: {task.outputs}",
    ]

    return "\n".join(lines)


def _build_acceptance_criteria_section(task: TaskDefinition) -> str:
    """Build the Acceptance Criteria section.

    Args:
        task: The task definition.

    Returns:
        Markdown acceptance criteria section.
    """
    lines = [
        "## Acceptance Criteria",
        "",
    ]

    for i, criterion in enumerate(task.acceptance_criteria, start=1):
        lines.append(f"{i}. {criterion}")

    return "\n".join(lines)


def _build_coach_validation_section(task: TaskDefinition) -> str:
    """Build the Coach Validation Commands section.

    Args:
        task: The task definition.

    Returns:
        Markdown coach validation section.
    """
    lines = [
        "## Coach Validation Commands",
        "",
    ]

    if task.coach_validation_commands:
        for cmd in task.coach_validation_commands:
            lines.append("```bash")
            lines.append(cmd)
            lines.append("```")
            lines.append("")
    else:
        lines.append("No specific validation commands provided.")

    return "\n".join(lines).rstrip()


def _build_player_constraints_section(task: TaskDefinition) -> str:
    """Build the Player Constraints section.

    Args:
        task: The task definition.

    Returns:
        Markdown player constraints section.
    """
    lines = [
        "## Player Constraints",
        "",
    ]

    # Add explicit constraints from task
    if task.player_constraints:
        for constraint in task.player_constraints:
            lines.append(f"- {constraint}")
        lines.append("")

    # Add files not to touch
    if task.files_not_to_touch:
        lines.append("**Files not to modify:**")
        for file_path in task.files_not_to_touch:
            lines.append(f"- {file_path}")

    # If no constraints at all, add a default message
    if not task.player_constraints and not task.files_not_to_touch:
        lines.append("Follow standard implementation guidelines.")

    return "\n".join(lines)


def _build_implementation_notes_section(
    task: TaskDefinition,
    enriched_task: EnrichedTask,
) -> str:
    """Build the Implementation Notes section.

    Args:
        task: The task definition.
        enriched_task: The enriched task with additional notes.

    Returns:
        Markdown implementation notes section.
    """
    lines = [
        "## Implementation Notes",
        "",
    ]

    # Add original implementation notes
    if task.implementation_notes:
        lines.append(task.implementation_notes)

    # Add enriched notes for local models
    if enriched_task.enriched_notes:
        if task.implementation_notes:
            lines.append("")
            lines.append("---")
            lines.append("")
        lines.append(enriched_task.enriched_notes)

    # If no notes at all, add a default message
    if not task.implementation_notes and not enriched_task.enriched_notes:
        lines.append("No additional implementation notes.")

    return "\n".join(lines)
