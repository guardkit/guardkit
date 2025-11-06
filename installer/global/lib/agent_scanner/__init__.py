"""
Multi-Source Agent Scanner

Scans multiple agent sources in priority order:
1. User's custom agents (.claude/agents/) - HIGHEST priority
2. Template agents (from template being used/generated) - HIGH priority
3. Global built-in agents (installer/global/agents/) - MEDIUM priority

Key Principle: User's custom agents always take precedence
"""

from .agent_scanner import (
    AgentDefinition,
    AgentInventory,
    MultiSourceAgentScanner
)

__all__ = [
    'AgentDefinition',
    'AgentInventory',
    'MultiSourceAgentScanner'
]
