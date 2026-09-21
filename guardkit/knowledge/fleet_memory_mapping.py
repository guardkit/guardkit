"""Fleet-memory group_id mapping for Graphiti to fleet-memory migration.

This module provides the authoritative mapping from Graphiti group_ids to
fleet-memory's identity model (payload_type, domain_tags).

It deliberately says NOTHING about which memory a record belongs to: that is a
property of the build emitting it and is passed in (2026-09-21).

Single source of truth for:
- Which groups migrate vs. retire
- How each group maps to fleet-memory payloads
- Identifier derivation conventions

Usage:
    >>> from guardkit.knowledge.fleet_memory_mapping import resolve
    >>> mapping = resolve("task_outcomes")
    >>> if mapping:
    ...     print(f"Migrate to {mapping.payload_type}")

## Group ID Mapping Table

| group_id | payload_type | domain_tags | disposition | identifier_convention | note |
|----------|--------------|-------------|-------------|----------------------|------|
| **Project Groups (9)** |
| task_outcomes | build_outcome | [task] | migrate | task_id | Primary home for task completion data |
| project_decisions | adr | [project] | migrate | decision_id | Project-level ADRs |
| adrs | adr | [decision] | migrate | decision_id | ADRService.create_adr runtime group_id |
| project_architecture | document | [architecture] | migrate | doc_path | System architecture docs |
| project_overview | document | [overview] | migrate | doc_path | High-level project context |
| feature_specs | document | [feature, spec] | migrate | feature_id | Feature specifications |
| domain_knowledge | document | [domain] | migrate | doc_path | Domain terminology and concepts |
| project_constraints | document | [constraints] | migrate | doc_path | Project limitations |
| bdd_scenarios | document | [bdd, behavior] | migrate | scenario_id | Gherkin BDD scenarios |
| turn_states | document | [turn, state] | migrate | turn_id | Feature-build turn state history |
| **System Groups (20)** |
| architecture_decisions | adr | [system] | migrate | decision_id | System-level ADRs |
| failure_patterns | warning | [failure, pattern] | migrate | pattern_id | Known failure patterns and mitigations |
| failed_approaches | warning | [failure, approach] | migrate | approach_id | Failed approaches and lessons |
| guardkit_templates | seed_module | [template] | retire | - | Covered by harvest corpus |
| guardkit_patterns | seed_module | [pattern] | retire | - | Covered by harvest corpus |
| guardkit_workflows | seed_module | [workflow] | retire | - | Covered by harvest corpus |
| product_knowledge | seed_module | [product] | retire | - | Covered by harvest corpus |
| command_workflows | seed_module | [command] | retire | - | Covered by harvest corpus |
| quality_gate_phases | seed_module | [quality] | retire | - | Covered by harvest corpus |
| technology_stack | seed_module | [tech] | retire | - | Covered by harvest corpus |
| feature_build_architecture | seed_module | [architecture] | retire | - | Covered by harvest corpus |
| component_status | seed_module | [status] | retire | - | Covered by harvest corpus |
| integration_points | seed_module | [integration] | retire | - | Covered by harvest corpus |
| templates | seed_module | [template] | retire | - | Covered by harvest corpus |
| agents | seed_module | [agent] | retire | - | Covered by harvest corpus |
| patterns | seed_module | [pattern] | retire | - | Covered by harvest corpus |
| rules | seed_module | [rule] | retire | - | Covered by harvest corpus |
| quality_gate_configs | seed_module | [quality] | retire | - | Covered by harvest corpus |
| role_constraints | seed_module | [role] | retire | - | Covered by harvest corpus |
| implementation_modes | seed_module | [mode] | retire | - | Covered by harvest corpus |
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class GroupMapping:
    """Fleet-memory identity mapping for a Graphiti group_id.

    **A mapping carries no project name (2026-09-21).** It used to carry the
    literal ``"guardkit"``, thirty times over, as the name to use "when no
    explicit project is passed" — which is how every project's build outcomes
    came to be filed under GuardKit's own name. Which memory a record belongs to
    is a property of the build emitting it, not of the group, so it is passed in
    and there is nothing here to fall back to.

    Attributes:
        payload_type: One of the 7 registered fleet-memory payload types
        domain_tags: List of domain-specific tags for categorization
        disposition: Whether to migrate or retire this group
    """
    payload_type: Literal[
        "adr",
        "review_report",
        "build_outcome",
        "pattern",
        "warning",
        "seed_module",
        "document",
    ]
    domain_tags: list[str]
    disposition: Literal["migrate", "retire"]


# Authoritative mapping: every group_id from guardkit/_group_defs.py
GROUP_ID_MAP: dict[str, GroupMapping] = {
    # ========== PROJECT GROUPS (9) ==========
    "task_outcomes": GroupMapping(
        payload_type="build_outcome",
        domain_tags=["task"],
        disposition="migrate",
    ),
    "project_decisions": GroupMapping(
        payload_type="adr",
        domain_tags=["project"],
        disposition="migrate",
    ),
    # ADRService.create_adr writes the literal group_id "adrs" (adr_service.py). Without
    # this entry resolve("adrs") returned None and every ADR dual-write silently no-op'd
    # (DualWriteClient skips unmapped groups). Map it to the adr payload so ADRs migrate.
    "adrs": GroupMapping(
        payload_type="adr",
        domain_tags=["decision"],
        disposition="migrate",
    ),
    "project_architecture": GroupMapping(
        payload_type="document",
        domain_tags=["architecture"],
        disposition="migrate",
    ),
    "project_overview": GroupMapping(
        payload_type="document",
        domain_tags=["overview"],
        disposition="migrate",
    ),
    "feature_specs": GroupMapping(
        payload_type="document",
        domain_tags=["feature", "spec"],
        disposition="migrate",
    ),
    "domain_knowledge": GroupMapping(
        payload_type="document",
        domain_tags=["domain"],
        disposition="migrate",
    ),
    "project_constraints": GroupMapping(
        payload_type="document",
        domain_tags=["constraints"],
        disposition="migrate",
    ),
    "bdd_scenarios": GroupMapping(
        payload_type="document",
        domain_tags=["bdd", "behavior"],
        disposition="migrate",
    ),
    "turn_states": GroupMapping(
        payload_type="document",
        domain_tags=["turn", "state"],
        disposition="migrate",
    ),
    # ========== SYSTEM GROUPS (20) ==========
    # Migrate these 3: runtime failures/lessons
    "architecture_decisions": GroupMapping(
        payload_type="adr",
        domain_tags=["system"],
        disposition="migrate",
    ),
    "failure_patterns": GroupMapping(
        payload_type="warning",
        domain_tags=["failure", "pattern"],
        disposition="migrate",
    ),
    "failed_approaches": GroupMapping(
        payload_type="warning",
        domain_tags=["failure", "approach"],
        disposition="migrate",
    ),
    # Retire these 17: covered by harvest corpus
    "guardkit_templates": GroupMapping(
        payload_type="seed_module",
        domain_tags=["template"],
        disposition="retire",
    ),
    "guardkit_patterns": GroupMapping(
        payload_type="seed_module",
        domain_tags=["pattern"],
        disposition="retire",
    ),
    "guardkit_workflows": GroupMapping(
        payload_type="seed_module",
        domain_tags=["workflow"],
        disposition="retire",
    ),
    "product_knowledge": GroupMapping(
        payload_type="seed_module",
        domain_tags=["product"],
        disposition="retire",
    ),
    "command_workflows": GroupMapping(
        payload_type="seed_module",
        domain_tags=["command"],
        disposition="retire",
    ),
    "quality_gate_phases": GroupMapping(
        payload_type="seed_module",
        domain_tags=["quality"],
        disposition="retire",
    ),
    "technology_stack": GroupMapping(
        payload_type="seed_module",
        domain_tags=["tech"],
        disposition="retire",
    ),
    "feature_build_architecture": GroupMapping(
        payload_type="seed_module",
        domain_tags=["architecture"],
        disposition="retire",
    ),
    "component_status": GroupMapping(
        payload_type="seed_module",
        domain_tags=["status"],
        disposition="retire",
    ),
    "integration_points": GroupMapping(
        payload_type="seed_module",
        domain_tags=["integration"],
        disposition="retire",
    ),
    "templates": GroupMapping(
        payload_type="seed_module",
        domain_tags=["template"],
        disposition="retire",
    ),
    "agents": GroupMapping(
        payload_type="seed_module",
        domain_tags=["agent"],
        disposition="retire",
    ),
    "patterns": GroupMapping(
        payload_type="seed_module",
        domain_tags=["pattern"],
        disposition="retire",
    ),
    "rules": GroupMapping(
        payload_type="seed_module",
        domain_tags=["rule"],
        disposition="retire",
    ),
    "quality_gate_configs": GroupMapping(
        payload_type="seed_module",
        domain_tags=["quality"],
        disposition="retire",
    ),
    "role_constraints": GroupMapping(
        payload_type="seed_module",
        domain_tags=["role"],
        disposition="retire",
    ),
    "implementation_modes": GroupMapping(
        payload_type="seed_module",
        domain_tags=["mode"],
        disposition="retire",
    ),
}


def _normalize_group_id(group_id: str) -> str:
    """Normalize group_id to PEP 503 style (lowercase, underscores only).

    Args:
        group_id: Raw group identifier (may contain hyphens or mixed case)

    Returns:
        Normalized identifier (lowercase, hyphens→underscores)

    Examples:
        >>> _normalize_group_id("task-outcomes")
        'task_outcomes'
        >>> _normalize_group_id("TASK_OUTCOMES")
        'task_outcomes'
    """
    return group_id.lower().replace("-", "_")


def resolve(group_id: str) -> GroupMapping | None:
    """Resolve a group_id to its fleet-memory mapping.

    Args:
        group_id: Graphiti group identifier (normalized before lookup)

    Returns:
        GroupMapping if the group is mapped, None if unknown or retired.
        Fail-open behavior: callers should skip unmapped groups.

    Examples:
        >>> mapping = resolve("task_outcomes")
        >>> mapping.payload_type
        'build_outcome'
        >>> resolve("task-outcomes").payload_type  # Normalizes hyphens
        'build_outcome'
        >>> resolve("unknown_group")  # Returns None for unmapped
    """
    normalized = _normalize_group_id(group_id)
    return GROUP_ID_MAP.get(normalized)
