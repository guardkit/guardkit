---
id: TASK-051
title: Implement interactive agent selection UI
status: backlog
created: 2025-11-01T16:17:00Z
priority: medium
complexity: 5
estimated_hours: 5
tags: [agent-discovery, cli-ui, interactive]
epic: EPIC-001
feature: agent-discovery
dependencies: [TASK-050]
blocks: [TASK-052]
---

# TASK-051: Implement Interactive Agent Selection UI

## Objective

Create interactive CLI UI for agent selection:
- **Display agents grouped by source (local first, then external)**
- Show score, source, description per agent
- Support checkbox selection
- Options: Accept all, Customize, Skip, Preview, Filter
- Return selected agent list

## Acceptance Criteria

- [ ] **Displays agents grouped by source (local → external)**
- [ ] **Source groups shown in priority order (local_global, local_user, subagents_cc, etc.)**
- [ ] Shows agent score, source, description
- [ ] Supports checkbox selection (space to toggle)
- [ ] Supports "Accept all recommended" (score ≥85)
- [ ] Supports "Customize selection"
- [ ] Supports "Skip agent discovery"
- [ ] Supports "Preview agent details"
- [ ] Supports "Filter by score threshold"
- [ ] Returns list of selected agents
- [ ] Clean, readable CLI output with source labels

## Implementation

```python
import inquirer
from collections import defaultdict

class AgentSelectionUI:
    def select_agents(self, matched_agents):
        """
        Display agents grouped by source and allow selection

        Args:
            matched_agents: List of scored agents from TASK-050
                Each agent has: {'agent': ..., 'score': int, 'source': str}

        Returns:
            List of selected agents
        """
        # Group by source
        by_source = self._group_by_source(matched_agents)

        # Display summary
        source_counts = {src: len(agents) for src, agents in by_source.items()}
        total = len(matched_agents)
        print(f"\n✓ Found {total} matching agents from {len(by_source)} sources:\n")

        # Show breakdown by source (in priority order)
        source_order = ['local_global', 'local_user', 'subagents_cc', 'wshobson_agents', 'voltagent']
        for source_id in source_order:
            if source_id in source_counts:
                count = source_counts[source_id]
                source_name = self._get_source_name(source_id)
                print(f"  • {source_name}: {count} agents")
        print()

        # Show options
        action = inquirer.list_input(
            "How would you like to select agents?",
            choices=[
                "Accept all recommended (score ≥85)",
                "Customize selection (review by source)",
                "Skip agent discovery",
                "Preview top 10 agents"
            ]
        )

        if action == "Accept all recommended (score ≥85)":
            return [a for a in matched_agents if a['score'] >= 85]

        elif action == "Customize selection (review by source)":
            return self._interactive_selection_by_source(by_source)

        elif action == "Skip agent discovery":
            return []

        elif action == "Preview top 10 agents":
            self._preview_top_agents(matched_agents[:10])
            return self.select_agents(matched_agents)  # Re-prompt

        return []

    def _group_by_source(self, matched_agents):
        """Group agents by source, preserving priority order"""
        by_source = defaultdict(list)

        for agent_data in matched_agents:
            source = agent_data.get('source', 'unknown')
            by_source[source].append(agent_data)

        return dict(by_source)

    def _interactive_selection_by_source(self, by_source):
        """
        Interactive selection grouped by source

        Shows agents source-by-source (local first)
        """
        selected = []

        # Process sources in priority order (local first)
        source_order = ['local_global', 'local_user', 'subagents_cc', 'wshobson_agents', 'voltagent']

        for source_id in source_order:
            if source_id not in by_source:
                continue

            agents = by_source[source_id]
            source_name = self._get_source_name(source_id)

            print(f"\n─── {source_name} ({len(agents)} agents) ───\n")

            # Create choices for this source
            choices = []
            for agent_data in agents:
                agent = agent_data['agent']
                score = agent_data['score']
                bonus = agent_data.get('bonus_applied', 0)

                # Format: "[95+20] agent-name - Description"
                label = f"[{score-bonus}+{bonus}] {agent.name} - {agent.description[:60]}..."
                choices.append((label, agent))

            # Multi-select for this source
            selected_from_source = inquirer.checkbox(
                message=f"Select agents from {source_name}:",
                choices=[(label, agent) for label, agent in choices]
            )

            selected.extend(selected_from_source)

        return selected

    def _get_source_name(self, source_id: str) -> str:
        """Get human-readable source name"""
        names = {
            'local_global': 'GuardKit Built-in',
            'local_user': 'User Custom Agents',
            'subagents_cc': 'Subagents.cc',
            'wshobson_agents': 'wshobson/agents',
            'voltagent': 'VoltAgent',
        }
        return names.get(source_id, source_id)

    def _preview_top_agents(self, top_agents):
        """Preview top agents"""
        print("\n─── Top 10 Recommended Agents ───\n")

        for i, agent_data in enumerate(top_agents, 1):
            agent = agent_data['agent']
            score = agent_data['score']
            source = agent_data.get('source', 'unknown')
            bonus = agent_data.get('bonus_applied', 0)

            print(f"{i}. {agent.name} (Score: {score}, Source: {self._get_source_name(source)})")
            if bonus > 0:
                print(f"   Base: {score-bonus} + Bonus: {bonus} (local agent)")
            print(f"   {agent.description[:100]}...")
            print()
```

**Estimated Time**: 5 hours | **Complexity**: 5/10 | **Priority**: MEDIUM
