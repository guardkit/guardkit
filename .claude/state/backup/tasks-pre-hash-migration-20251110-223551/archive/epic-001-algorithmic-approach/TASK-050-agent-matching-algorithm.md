---
id: TASK-050
title: Implement agent matching algorithm
status: backlog
created: 2025-11-01T16:16:00Z
priority: high
complexity: 6
estimated_hours: 7
tags: [agent-discovery, matching-algorithm, scoring]
epic: EPIC-001
feature: agent-discovery
dependencies: [TASK-037, TASK-038, TASK-048, TASK-048B, TASK-048C, TASK-049]
blocks: [TASK-051]
---

# TASK-050: Implement Agent Matching Algorithm

## Objective

Score and rank agents based on project characteristics:
- Technology stack match (40% weight)
- Architecture pattern match (30% weight)
- Tool compatibility (20% weight)
- Community validation (10% weight)
- **Source priority bonus** (0-20 points, local agents preferred)
- Filter by threshold (≥60)
- Return ranked agent list with source information

## Acceptance Criteria

- [ ] Scores agents 0-100
- [ ] Technology stack matching working (exact and partial)
- [ ] Architecture pattern matching working
- [ ] Tool compatibility check working
- [ ] Community score calculation working
- [ ] **Source priority bonus applied (local agents get +20)**
- [ ] **Integration with TASK-048B (local agents) and TASK-048C (source registry)**
- [ ] Filters agents by threshold (≥60)
- [ ] Returns ranked list with source attribution
- [ ] Unit tests passing (>85% coverage)

## Implementation

```python
from local_agent_scanner import discover_local_agents, LocalAgentMetadata
from agent_source_manager import AgentSourceManager

class AgentMatcher:
    def match_agents(self, agents, stack_result, arch_result):
        """
        Match and score agents based on project characteristics

        Args:
            agents: List of agents (from all sources: local + external)
            stack_result: Stack detection result from TASK-037
            arch_result: Architecture analysis from TASK-038

        Returns:
            List of scored agents, sorted by score (descending)
        """
        scored_agents = []

        for agent in agents:
            # Base score (0-100)
            score = 0

            # Technology match (40%)
            score += self._score_technology(agent, stack_result) * 0.4

            # Pattern match (30%)
            score += self._score_patterns(agent, arch_result) * 0.3

            # Tool compatibility (20%)
            score += self._score_tools(agent) * 0.2

            # Community validation (10%)
            score += self._score_community(agent) * 0.1

            # Source priority bonus (0-20 points)
            # Local agents get higher priority
            bonus = self._get_source_bonus(agent)
            score += bonus

            # Note: Total score can exceed 100 due to bonus (max 120)
            # This intentionally prioritizes local agents

            if score >= 60:
                scored_agents.append({
                    'agent': agent,
                    'score': int(score),
                    'source': agent.source,  # Track source
                    'bonus_applied': bonus
                })

        return sorted(scored_agents, key=lambda x: x['score'], reverse=True)

    def _get_source_bonus(self, agent) -> int:
        """
        Get bonus score based on agent source

        Returns:
            Bonus score (0-20 points)
        """
        # If agent has priority_bonus attribute (LocalAgentMetadata)
        if hasattr(agent, 'priority_bonus'):
            return agent.priority_bonus

        # If agent has source attribute, look up bonus from config
        if hasattr(agent, 'source'):
            manager = AgentSourceManager()
            source_config = manager.get_source(agent.source)
            if source_config:
                return source_config.bonus_score

        # No bonus for agents without source information
        return 0

    def discover_all_agents(self, stack_result, arch_result):
        """
        Discover agents from all configured sources and score them

        Returns:
            Ranked list of agents from all sources (local + external)
        """
        all_agents = []

        # 1. Discover local agents (TASK-048B)
        local_agents = discover_local_agents()
        all_agents.extend(local_agents)

        # 2. Discover from external sources (TASK-048, TASK-049)
        # Note: TASK-048 and TASK-049 implementation would go here
        # external_agents = discover_external_agents()
        # all_agents.extend(external_agents)

        # 3. Score and rank all agents
        return self.match_agents(all_agents, stack_result, arch_result)
```

**Estimated Time**: 7 hours | **Complexity**: 6/10 | **Priority**: HIGH
