"""
Clarification module for GuardKit task workflow.

This module provides ambiguity detection and question generation capabilities
for the clarification phase that runs before implementation planning.
"""

from .detection import (
    ScopeAmbiguity,
    TechChoice,
    TechChoices,
    IntegrationPoint,
    UserAmbiguity,
    TradeoffNeed,
    EdgeCase,
    detect_scope_ambiguity,
    detect_technology_choices,
    detect_integration_points,
    detect_user_ambiguity,
    detect_tradeoff_needs,
    detect_unhandled_edge_cases,
)

__all__ = [
    "ScopeAmbiguity",
    "TechChoice",
    "TechChoices",
    "IntegrationPoint",
    "UserAmbiguity",
    "TradeoffNeed",
    "EdgeCase",
    "detect_scope_ambiguity",
    "detect_technology_choices",
    "detect_integration_points",
    "detect_user_ambiguity",
    "detect_tradeoff_needs",
    "detect_unhandled_edge_cases",
]
