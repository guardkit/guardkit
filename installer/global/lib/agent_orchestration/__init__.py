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

from lib.agent_orchestration.agent_orchestration import (
    AgentOrchestrator,
    AgentRecommendation,
    DiscoveredAgent,
    get_agents_for_template
)

__all__ = [
    'AgentOrchestrator',
    'AgentRecommendation',
    'DiscoveredAgent',
    'get_agents_for_template'
]
