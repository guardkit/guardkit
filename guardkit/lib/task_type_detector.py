"""Task type detection based on keyword analysis.

Provides automatic task type classification for feature planning workflow.
Analyzes task titles and descriptions to assign appropriate task types
(SCAFFOLDING, DOCUMENTATION, INFRASTRUCTURE, INTEGRATION, TESTING, REFACTOR, FEATURE)
based on keyword matching.

The detector uses a priority-based classification system:
1. INFRASTRUCTURE - DevOps, deployment, CI/CD (checked first for specificity)
2. INTEGRATION - Wiring, connecting, hooking up services/endpoints
3. TESTING - Test frameworks, test types, test infrastructure
4. REFACTOR - Code restructuring, migration, modernization
5. DOCUMENTATION - Docs, guides, tutorials
6. SCAFFOLDING - Configuration, boilerplate, setup tasks
7. FEATURE - Default for implementation tasks

This module supports the /feature-plan workflow by automatically determining
which quality gate profile should be applied to each subtask.

Usage:
    from guardkit.lib.task_type_detector import detect_task_type
    from guardkit.models.task_types import TaskType

    task_type = detect_task_type("Add Docker configuration")
    # Returns: TaskType.INFRASTRUCTURE

    task_type = detect_task_type("Update README with API docs")
    # Returns: TaskType.DOCUMENTATION

    task_type = detect_task_type("Implement user authentication")
    # Returns: TaskType.FEATURE
"""

from typing import Optional
from guardkit.models.task_types import TaskType


# Keyword mappings for task type classification
# Priority order: INFRASTRUCTURE → INTEGRATION → TESTING → REFACTOR → DOCUMENTATION → SCAFFOLDING → FEATURE
# Infrastructure gets priority to avoid "config" matching before "docker config"
# Integration uses verb forms ("integrate", "wire", "connect") to avoid overlap with "integration test"
KEYWORD_MAPPINGS = {
    TaskType.INFRASTRUCTURE: [
        # Containerization (check these first - more specific than "config")
        "docker",
        "dockerfile",
        "docker-compose",
        "container",
        # CI/CD
        "ci/cd",
        "pipeline",
        "github actions",
        "gitlab ci",
        "jenkins",
        "circleci",
        # Deployment
        "deploy",
        "deployment",
        "kubernetes",
        "k8s",
        "helm",
        # Infrastructure as Code
        "terraform",
        "ansible",
        "cloudformation",
        # Monitoring and logging
        "monitoring",
        "logging",
        "prometheus",
        "grafana",
        # Cloud providers
        "aws",
        "azure",
        "gcp",
        "cloud",
    ],
    TaskType.INTEGRATION: [
        # Wiring verbs (NOT "integration" to avoid overlap with "integration test")
        "integrate",
        "wire up",
        "wiring",
        "connect",
        "hook up",
        "hookup",
    ],
    TaskType.DOCUMENTATION: [
        # Documentation files
        "readme",
        "docs",
        "documentation",
        "guide",
        "tutorial",
        "how-to",
        "howto",
        # API documentation
        "api doc",
        "swagger",
        "openapi",
        "jsdoc",
        "docstring",
        # Comments and explanations
        "comment",
        "explain",
        "clarify",
        # Changelog and notes
        "changelog",
        "release notes",
        # Content reduction (TASK-REV-D4B1)
        "trim",
        "reduce",
        "compress",
        "condense",
        "shorten",
    ],
    TaskType.TESTING: [
        # Test frameworks
        "pytest",
        "unittest",
        "jest",
        "vitest",
        "mocha",
        "jasmine",
        # Test types
        "test",
        "testing",
        "spec",
        "e2e",
        "end-to-end",
        "integration test",
        "unit test",
        # Test infrastructure
        "test fixture",
        "test setup",
        "mock",
        "stub",
    ],
    TaskType.REFACTOR: [
        # Refactoring
        "refactor",
        "refactoring",
        "restructure",
        # Migration
        "migrate",
        "migration",
        "upgrade",
        # Modernization
        "modernize",
        "modernization",
        # Cleanup
        "cleanup",
        "clean up",
        "clean-up",
    ],
    TaskType.SCAFFOLDING: [
        # Configuration files (more generic, checked after infrastructure)
        "config",
        "configuration",
        "settings",
        ".env",
        "environment",
        # Project setup
        "scaffold",
        "boilerplate",
        "template",
        "setup",
        "initialize",
        "init",
        # Package management
        "package.json",
        "requirements.txt",
        "pyproject.toml",
        "gemfile",
        "composer.json",
        # Build configuration
        "webpack",
        "vite",
        "rollup",
        "tsconfig",
        "babel",
        "eslint",
        "prettier",
    ],
    # FEATURE is the default - no keywords needed
}


def detect_task_type(title: str, description: str = "") -> TaskType:
    """Detect task type based on keyword analysis.

    Analyzes the task title and optional description to determine the most
    appropriate task type classification. Uses case-insensitive substring
    matching with priority-based selection.

    Priority order (first match wins):
    1. INFRASTRUCTURE - DevOps and deployment (most specific keywords)
    2. INTEGRATION - Wiring, connecting, hooking up services/endpoints
    3. TESTING - Test frameworks, test types, test infrastructure
    4. REFACTOR - Code restructuring, migration, modernization
    5. DOCUMENTATION - Documentation and guides
    6. SCAFFOLDING - Configuration and setup tasks (generic keywords)
    7. FEATURE - Default for all other tasks

    Args:
        title: Task title (required, used for primary classification)
        description: Task description (optional, provides additional context)

    Returns:
        TaskType: The detected task type enum value

    Examples:
        Scaffolding tasks (configuration):
        >>> detect_task_type("Add webpack configuration")
        <TaskType.SCAFFOLDING: 'scaffolding'>

        >>> detect_task_type("Initialize package.json")
        <TaskType.SCAFFOLDING: 'scaffolding'>

        Documentation tasks:
        >>> detect_task_type("Update README with API documentation")
        <TaskType.DOCUMENTATION: 'documentation'>

        >>> detect_task_type("Write tutorial for authentication flow")
        <TaskType.DOCUMENTATION: 'documentation'>

        Infrastructure tasks:
        >>> detect_task_type("Add Docker configuration")
        <TaskType.INFRASTRUCTURE: 'infrastructure'>

        >>> detect_task_type("Set up CI/CD pipeline")
        <TaskType.INFRASTRUCTURE: 'infrastructure'>

        Feature tasks (default):
        >>> detect_task_type("Implement user authentication")
        <TaskType.FEATURE: 'feature'>

        >>> detect_task_type("Add validation to login form")
        <TaskType.FEATURE: 'feature'>

        Edge cases:
        >>> detect_task_type("")
        <TaskType.FEATURE: 'feature'>

        >>> detect_task_type("Fix bug in payment processing")
        <TaskType.FEATURE: 'feature'>

        Hybrid tasks (first matching type wins):
        >>> detect_task_type("Add Docker config and update README")
        <TaskType.INFRASTRUCTURE: 'infrastructure'>

    Notes:
        - Case-insensitive matching
        - Substring matching (no word boundaries required)
        - Description is optional but provides additional classification context
        - Empty or None values are handled gracefully (default to FEATURE)
        - First match in priority order wins for hybrid tasks
    """
    # Normalize inputs
    title_lower = (title or "").lower()
    description_lower = (description or "").lower()
    combined_text = f"{title_lower} {description_lower}"

    # Check for empty input
    if not combined_text.strip():
        return TaskType.FEATURE

    # Check each task type in priority order
    # Priority: INFRASTRUCTURE → INTEGRATION → TESTING → REFACTOR → DOCUMENTATION → SCAFFOLDING → FEATURE
    # Infrastructure first to catch "docker config" before "config"
    # Integration before testing to catch "integrate X" before "test" in description
    for task_type in [
        TaskType.INFRASTRUCTURE,
        TaskType.INTEGRATION,
        TaskType.TESTING,
        TaskType.REFACTOR,
        TaskType.DOCUMENTATION,
        TaskType.SCAFFOLDING,
    ]:
        keywords = KEYWORD_MAPPINGS.get(task_type, [])
        for keyword in keywords:
            if keyword in combined_text:
                return task_type

    # Default to FEATURE if no keywords match
    return TaskType.FEATURE


def get_task_type_summary(task_type: TaskType) -> str:
    """Get a human-readable summary of a task type.

    Provides a short description of what each task type represents,
    useful for logging and user feedback.

    Args:
        task_type: The TaskType enum value

    Returns:
        str: Human-readable description of the task type

    Examples:
        >>> get_task_type_summary(TaskType.SCAFFOLDING)
        'Configuration and boilerplate'

        >>> get_task_type_summary(TaskType.FEATURE)
        'Feature implementation'
    """
    summaries = {
        TaskType.SCAFFOLDING: "Configuration and boilerplate",
        TaskType.DOCUMENTATION: "Documentation and guides",
        TaskType.INFRASTRUCTURE: "DevOps and deployment",
        TaskType.INTEGRATION: "Integration and wiring",
        TaskType.TESTING: "Test infrastructure and tests",
        TaskType.REFACTOR: "Code refactoring and migration",
        TaskType.FEATURE: "Feature implementation",
    }
    return summaries.get(task_type, "Unknown task type")
