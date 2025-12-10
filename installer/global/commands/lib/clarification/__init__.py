"""Unified clarification module for GuardKit.

This module provides infrastructure for interactive clarification prompts across
multiple contexts: review scope decisions, implementation preferences, and
implementation planning clarifications.

Key Components:
    - ClarificationContext: Context passed to agents with user decisions
    - Decision: Individual decision with confidence and rationale
    - Question: Question template with defaults
    - ClarificationMode: Mode for clarification (skip/quick/full/defaults)

Main Functions:
    - should_clarify(): Determine clarification mode based on complexity
    - process_responses(): Parse user input into decisions
    - format_for_prompt(): Format context for agent prompts
    - parse_frontmatter(): Parse YAML frontmatter from markdown
    - serialize_frontmatter(): Serialize frontmatter to YAML
    - get_clarification_summary(): Generate human-readable summary

ClarificationContext Methods:
    - persist_to_frontmatter(): Save context to task metadata
    - load_from_frontmatter(): Load context from task metadata

Usage:
    >>> from lib.clarification import should_clarify, ClarificationMode
    >>> mode = should_clarify("planning", complexity=6, flags={})
    >>> mode == ClarificationMode.FULL
    True
"""

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

__all__ = [
    # Enums
    "ClarificationMode",
    # Dataclasses
    "Question",
    "Decision",
    "ClarificationContext",
    # Functions
    "should_clarify",
    "process_responses",
    "format_for_prompt",
    "parse_frontmatter",
    "serialize_frontmatter",
    "get_clarification_summary",
]

__version__ = "0.1.0"
