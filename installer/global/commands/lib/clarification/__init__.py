"""Unified clarification module for GuardKit.

This module provides infrastructure for interactive clarification prompts across
multiple contexts: review scope decisions, implementation preferences, and
implementation planning clarifications.

Key Components:
    Core Infrastructure (from core.py):
    - ClarificationContext: Context passed to agents with user decisions
    - Decision: Individual decision with confidence and rationale
    - Question: Question template with defaults
    - ClarificationMode: Mode for clarification (skip/quick/full/defaults)

    Detection Algorithms (from detection.py):
    - ScopeAmbiguity, TechChoice, IntegrationPoint, etc.: Detection result types
    - detect_scope_ambiguity(), detect_technology_choices(), etc.: Detection functions

Main Functions:
    - should_clarify(): Determine clarification mode based on complexity
    - process_responses(): Parse user input into decisions
    - format_for_prompt(): Format context for agent prompts
    - parse_frontmatter(): Parse YAML frontmatter from markdown
    - serialize_frontmatter(): Serialize frontmatter to YAML
    - get_clarification_summary(): Generate human-readable summary
    - detect_*(): Various ambiguity detection functions

ClarificationContext Methods:
    - persist_to_frontmatter(): Save context to task metadata
    - load_from_frontmatter(): Load context from task metadata

Usage:
    >>> from lib.clarification import should_clarify, ClarificationMode
    >>> mode = should_clarify("planning", complexity=6, flags={})
    >>> mode == ClarificationMode.FULL
    True

    >>> from lib.clarification import detect_scope_ambiguity, TaskContext
    >>> task = TaskContext(task_id="T1", title="Add auth", description="Implement login")
    >>> result = detect_scope_ambiguity(task)
    >>> result.feature
    'auth'
"""

# Core infrastructure
from .core import (
    # Enums
    ClarificationMode,
    # Dataclasses
    Question,
    Decision,
    ClarificationContext,
    # Functions
    should_clarify,
    process_responses,
    format_for_prompt,
    parse_frontmatter,
    serialize_frontmatter,
    get_clarification_summary,
)

# Detection algorithms
from .detection import (
    # Dataclasses for task/codebase context
    TaskContext,
    CodebaseContext,
    # Detection result types
    ScopeAmbiguity,
    TechChoice,
    TechChoices,
    IntegrationPoint,
    UserAmbiguity,
    TradeoffNeed,
    EdgeCase,
    # Detection functions
    detect_scope_ambiguity,
    detect_technology_choices,
    detect_integration_points,
    detect_user_ambiguity,
    detect_tradeoff_needs,
    detect_unhandled_edge_cases,
)

__all__ = [
    # Core - Enums
    "ClarificationMode",
    # Core - Dataclasses
    "Question",
    "Decision",
    "ClarificationContext",
    # Core - Functions
    "should_clarify",
    "process_responses",
    "format_for_prompt",
    "parse_frontmatter",
    "serialize_frontmatter",
    "get_clarification_summary",
    # Detection - Context types
    "TaskContext",
    "CodebaseContext",
    # Detection - Result types
    "ScopeAmbiguity",
    "TechChoice",
    "TechChoices",
    "IntegrationPoint",
    "UserAmbiguity",
    "TradeoffNeed",
    "EdgeCase",
    # Detection - Functions
    "detect_scope_ambiguity",
    "detect_technology_choices",
    "detect_integration_points",
    "detect_user_ambiguity",
    "detect_tradeoff_needs",
    "detect_unhandled_edge_cases",
]

__version__ = "0.1.0"
