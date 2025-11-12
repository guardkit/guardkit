"""
Agent System Orchestration

Provides unified orchestration of the agent system:
- Inventory existing agents from multiple sources
- Generate missing agents based on codebase analysis
- Optional external agent discovery (Phase 2)
- Return comprehensive agent recommendations

Example:
    from lib.agent_orchestration import get_agents_for_template

    # Get complete agent recommendation
    agents = get_agents_for_template(analysis)

    # Use recommended agents
    for agent in agents.all_agents():
        save_agent_to_template(agent, template_dir)
"""

import importlib

# Import using importlib to avoid 'global' keyword issue
_agent_orchestration_module = importlib.import_module('installer.global.lib.agent_orchestration.agent_orchestration')

AgentOrchestrator = _agent_orchestration_module.AgentOrchestrator
AgentRecommendation = _agent_orchestration_module.AgentRecommendation
DiscoveredAgent = _agent_orchestration_module.DiscoveredAgent
get_agents_for_template = _agent_orchestration_module.get_agents_for_template

__all__ = [
    'AgentOrchestrator',
    'AgentRecommendation',
    'DiscoveredAgent',
    'get_agents_for_template'
]
