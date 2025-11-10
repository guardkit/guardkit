---
id: TASK-052
title: Implement agent download and integration
status: backlog
created: 2025-11-01T16:18:00Z
priority: medium
complexity: 4
estimated_hours: 4
tags: [agent-discovery, download, integration]
epic: EPIC-001
feature: agent-discovery
dependencies: [TASK-051]
blocks: [TASK-047, TASK-060]
---

# TASK-052: Implement Agent Download and Integration

## Objective

Download agent specifications and integrate into template:
- Download agent markdown files from source URLs
- Save to template agents/ directory
- Update manifest.json with agent list
- Validate agent format
- Handle download errors gracefully

## Acceptance Criteria

- [ ] Downloads agent files from URLs
- [ ] Saves to {template}/agents/
- [ ] Updates manifest.json agents array
- [ ] Validates agent markdown format
- [ ] Handles HTTP errors (404, timeout)
- [ ] Retries failed downloads (max 3)
- [ ] Returns download report
- [ ] Unit tests passing (>85% coverage)

## Implementation

```python
class AgentDownloader:
    def download_agents(self, selected_agents, template_path):
        agents_dir = template_path / "agents"
        agents_dir.mkdir(exist_ok=True)

        downloaded = []
        failed = []

        for agent in selected_agents:
            try:
                content = self._download_agent(agent['agent'].source_url)
                filename = f"{agent['agent'].name}.md"

                with open(agents_dir / filename, 'w') as f:
                    f.write(content)

                downloaded.append(agent['agent'].name)

            except Exception as e:
                failed.append({'agent': agent['agent'].name, 'error': str(e)})

        return {'downloaded': downloaded, 'failed': failed}
```

**Estimated Time**: 4 hours | **Complexity**: 4/10 | **Priority**: MEDIUM
