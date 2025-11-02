---
id: TASK-009
title: AI-Powered Agent Recommendation
status: backlog
created: 2025-11-01T20:45:00Z
priority: medium
complexity: 4
estimated_hours: 4
tags: [agent-discovery, ai-recommendation]
epic: EPIC-001
feature: agent-discovery
dependencies: [TASK-002, TASK-003, TASK-004]
blocks: [TASK-010]
---

# TASK-009: AI-Powered Agent Recommendation

## Objective

Use `pattern-advisor` agent to recommend relevant agents based on project analysis.

## Implementation

```python
def recommend_agents(analysis: CodebaseAnalysis, available_agents: List[Agent]):
    """Ask AI which agents are relevant for this project"""
    prompt = f"""
    Given project with:
    - Architecture: {analysis.architecture_pattern}
    - Language: {analysis.language}
    - Patterns: {analysis.layers}

    Which of these agents are most relevant? {available_agents}
    Rank by relevance.
    """
    
    return pattern_advisor.execute(prompt)
```

**Replaces**: Complex scoring algorithm with AI recommendation

**Estimated Time**: 4 hours | **Complexity**: 4/10 | **Priority**: MEDIUM
