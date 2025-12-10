"""
Multi-Source Agent Scanner

Scans multiple agent sources in priority order:
1. User's custom agents (.claude/agents/) - HIGHEST priority
2. Template agents (from template being used/generated) - HIGH priority
3. Global built-in agents (installer/core/agents/) - MEDIUM priority

Key Principle: User's custom agents always take precedence

TASK-PD-004: Extended files (-ext.md) are excluded from discovery
"""

from .agent_scanner import (
    AgentDefinition,
    AgentInventory,
    MultiSourceAgentScanner,
    is_extended_file
)

__all__ = [
    'AgentDefinition',
    'AgentInventory',
    'MultiSourceAgentScanner',
    'is_extended_file'
]
