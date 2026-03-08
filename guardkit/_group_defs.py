"""Group definitions for Graphiti knowledge graph.

Single source of truth for project and system group IDs and descriptions.
This module is intentionally at the guardkit package level to avoid circular
imports between guardkit.knowledge.graphiti_client and
guardkit.integrations.graphiti.

Both modules import from here:
- guardkit.integrations.graphiti.constants re-exports these for public API
- guardkit.knowledge.graphiti_client uses the lists for group scoping
"""

from typing import Dict, List

# Project-specific group IDs with descriptions
PROJECT_GROUPS: Dict[str, str] = {
    "project_overview": "High-level project purpose and goals",
    "project_architecture": "System architecture and patterns",
    "feature_specs": "Feature specifications and requirements",
    "project_decisions": "Architecture Decision Records (ADRs)",
    "project_constraints": "Constraints and limitations",
    "domain_knowledge": "Domain terminology and concepts",
    "bdd_scenarios": "BDD Gherkin scenarios for behavior specifications",
    "task_outcomes": "Task completion outcomes and lessons learned",
    "turn_states": "Feature-build turn state history for cross-turn learning",
}

# System-level group IDs with descriptions
SYSTEM_GROUPS: Dict[str, str] = {
    "guardkit_templates": "GuardKit template definitions and configurations",
    "guardkit_patterns": "GuardKit internal design patterns",
    "guardkit_workflows": "GuardKit workflow definitions and orchestration",
    "product_knowledge": "Product domain knowledge and terminology",
    "command_workflows": "Command execution workflows and pipelines",
    "quality_gate_phases": "Quality gate phase configurations and thresholds",
    "technology_stack": "Technology stack information and dependencies",
    "feature_build_architecture": "Feature build architecture and structure",
    "architecture_decisions": "Architecture decision records and rationale",
    "failure_patterns": "Known failure patterns and mitigations",
    "component_status": "Component health and operational status",
    "integration_points": "Integration touchpoints and external connections",
    "templates": "Template library and project scaffolding definitions",
    "agents": "Agent definitions and operational capabilities",
    "patterns": "Design pattern library and recommendations",
    "rules": "Rule definitions and enforcement policies",
    "failed_approaches": "Failed approaches and lessons learned",
    "quality_gate_configs": "Task-type specific quality thresholds",
    "role_constraints": "Player/Coach role boundaries",
    "implementation_modes": "Direct vs task-work patterns",
}

# Derived lists for GraphitiClient group scoping
PROJECT_GROUP_NAMES: List[str] = list(PROJECT_GROUPS.keys())
SYSTEM_GROUP_IDS: List[str] = list(SYSTEM_GROUPS.keys())
