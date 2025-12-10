"""
AI Agent Generator

Generates project-specific AI agents based on codebase analysis,
filling capability gaps identified by comparing needed capabilities
with existing agents.

Key Principle: AI creates tailored agents from actual code examples
(not generic templates)
"""

from .agent_generator import (
    CapabilityNeed,
    GeneratedAgent,
    AIAgentGenerator,
    AgentInvoker,
    DefaultAgentInvoker
)

__all__ = [
    'CapabilityNeed',
    'GeneratedAgent',
    'AIAgentGenerator',
    'AgentInvoker',
    'DefaultAgentInvoker'
]
