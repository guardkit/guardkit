---
id: TASK-EMB-001
title: Complete youtube-transcript-mcp graphiti.yaml with full infrastructure config
status: backlog
created: 2026-03-09T00:00:00Z
priority: critical
tags: [graphiti, config, embedding, dimension-mismatch]
task_type: implementation
complexity: 1
parent_review: TASK-REV-D2B5
feature_id: FEAT-EMB
wave: 1
implementation_mode: direct
dependencies: []
---

# Task: Complete youtube-transcript-mcp graphiti.yaml

## Description

The youtube-transcript-mcp project's `.guardkit/graphiti.yaml` only contains `project_id` and `enabled`. All infrastructure config (graph_store, FalkorDB connection, embedding provider, LLM provider) defaults to OpenAI/neo4j, causing a dimension mismatch when searching against FalkorDB vectors seeded with vLLM's nomic-embed-text-v1.5 (768-dim).

## Acceptance Criteria

- [ ] `~/Projects/appmilla_github/youtube-transcript-mcp/.guardkit/graphiti.yaml` contains all infrastructure fields matching guardkit's config
- [ ] Fields include: `graph_store`, `falkordb_host`, `falkordb_port`, `llm_provider`, `llm_base_url`, `llm_model`, `embedding_provider`, `embedding_base_url`, `embedding_model`, `timeout`, `max_concurrent_episodes`
- [ ] Only `project_id` differs from guardkit's config

## Implementation

Replace the contents of `~/Projects/appmilla_github/youtube-transcript-mcp/.guardkit/graphiti.yaml` with:

```yaml
# Graphiti Knowledge Graph Configuration
# Project-specific settings for knowledge capture

# Project ID for namespace prefixing
project_id: youtube-transcript-mcp

# Enable Graphiti integration
enabled: true

# Shared FalkorDB infrastructure (must match guardkit config)
graph_store: falkordb
falkordb_host: whitestocks
falkordb_port: 6379
timeout: 30.0
max_concurrent_episodes: 3

# LLM provider for entity extraction
llm_provider: vllm
llm_base_url: http://promaxgb10-41b1:8000/v1
llm_model: claude-sonnet-4-6

# Embedding provider - MUST match seeding model for shared FalkorDB
embedding_provider: vllm
embedding_base_url: http://promaxgb10-41b1:8001/v1
embedding_model: nomic-embed-text-v1.5
```

## Verification

Run from youtube-transcript-mcp directory:
```bash
cd ~/Projects/appmilla_github/youtube-transcript-mcp
python3 -c "
from guardkit.knowledge.config import load_graphiti_config
s = load_graphiti_config()
assert s.embedding_provider == 'vllm', f'Expected vllm, got {s.embedding_provider}'
assert s.graph_store == 'falkordb', f'Expected falkordb, got {s.graph_store}'
assert s.falkordb_host == 'whitestocks', f'Expected whitestocks, got {s.falkordb_host}'
print('Config verified OK')
"
```
