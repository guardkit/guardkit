"""
Facts module for GuardKit knowledge graph.

This module contains fact entities used in the knowledge graph.
"""

from guardkit.knowledge.facts.role_constraint import (
    RoleConstraintFact,
    PLAYER_CONSTRAINTS,
    COACH_CONSTRAINTS,
)

__all__ = [
    "RoleConstraintFact",
    "PLAYER_CONSTRAINTS",
    "COACH_CONSTRAINTS",
]
