---
id: TASK-049
title: Implement GitHub agent repository parsers
status: backlog
created: 2025-11-01T16:15:00Z
priority: high
complexity: 7
estimated_hours: 8
tags: [agent-discovery, github-api, parsing]
epic: EPIC-001
feature: agent-discovery
dependencies: []
blocks: [TASK-050]
---

# TASK-049: Implement GitHub Agent Repository Parsers

## Objective

Parse agent definitions from GitHub repositories:
- github:wshobson/agents (63 plugins)
- github:VoltAgent/awesome-claude-code-subagents (116 agents)
- Extract agent metadata from markdown/JSON
- Normalize metadata across sources
- Implement caching

## Acceptance Criteria

- [ ] Parses wshobson/agents repository
- [ ] Parses VoltAgent/awesome-claude-code-subagents
- [ ] Extracts agent metadata (name, description, tools, category)
- [ ] Normalizes metadata to AgentMetadata format
- [ ] Implements caching (15-minute TTL)
- [ ] Handles GitHub API rate limits
- [ ] Returns >100 agents total
- [ ] Unit tests passing (>85% coverage)

## Implementation

```python
class GitHubAgentParser:
    def __init__(self, repo_url, cache_ttl=15):
        self.repo_url = repo_url
        self.github_client = Github(token)  # PyGithub

    def parse_agents(self) -> List[AgentMetadata]:
        # Fetch repository contents via GitHub API
        # Parse markdown/JSON files
        # Extract agent definitions
        # Normalize to AgentMetadata
        # Cache results
        pass

    def _parse_wshobson_agents(self):
        # Parse plugin architecture
        # Extract from JSON specs
        pass

    def _parse_voltagent_agents(self):
        # Parse awesome-list format
        # Extract from markdown
        pass
```

**Estimated Time**: 8 hours | **Complexity**: 7/10 | **Priority**: HIGH
