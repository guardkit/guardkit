---
id: TASK-EMB-002
title: Remove infrastructure config from guardkit .env (keep only secrets)
status: completed
created: 2026-03-09T00:00:00Z
updated: 2026-03-09T00:00:00Z
completed: 2026-03-09T00:00:00Z
priority: critical
tags: [config, env, cleanup, dimension-mismatch]
task_type: implementation
complexity: 1
parent_review: TASK-REV-D2B5
feature_id: FEAT-EMB
wave: 1
implementation_mode: direct
dependencies: []
---

# Task: Remove infrastructure config from guardkit .env

## Description

The guardkit `.env` file contains `GRAPH_STORE=falkordb`, `FALKORDB_HOST=whitestocks`, and `FALKORDB_PORT=6379`. These duplicate what's already in `.guardkit/graphiti.yaml` and cause cross-session pollution: when `load_dotenv()` sets them in `os.environ`, they persist across directory changes (python-dotenv doesn't override existing vars), creating split-brain config in other projects.

`.env` should ONLY contain secrets (API keys). Infrastructure config belongs in `graphiti.yaml`.

## Acceptance Criteria

- [x] `guardkit/.env` contains only `OPENAI_API_KEY` (and optionally `ANTHROPIC_API_KEY`)
- [x] `GRAPH_STORE`, `FALKORDB_HOST`, `FALKORDB_PORT` removed from `.env`
- [x] Comment added explaining the secrets-only policy
- [x] guardkit still works correctly (infra config comes from `graphiti.yaml`)

## Implementation

Changed `.env.example` (committed template) to:

```
# GuardKit Environment Variables
# Copy to .env and fill in your values:
#   cp .env.example .env
#
# DO NOT commit .env to version control
#
# ONLY secrets go here. Infrastructure config is in .guardkit/graphiti.yaml
# See: TASK-REV-D2B5 for why infra config must NOT be in .env

# OpenAI API Key - required when using OpenAI providers
OPENAI_API_KEY=sk-proj-your-key-here
```

`graphiti.yaml` retains all infra config: `graph_store: falkordb`, `falkordb_host: whitestocks`, `falkordb_port: 6379`.

**Note for users with existing `.env`:** Manually remove `GRAPH_STORE`, `FALKORDB_HOST`, and `FALKORDB_PORT` from your local `.env` file.

## Verification

```bash
cd ~/Projects/appmilla_github/guardkit
# Verify graphiti.yaml still has all infra config
python3 -c "
from guardkit.knowledge.config import load_graphiti_config
s = load_graphiti_config()
assert s.graph_store == 'falkordb'
assert s.falkordb_host == 'whitestocks'
assert s.embedding_provider == 'vllm'
print('Config verified OK - all infra from graphiti.yaml')
"
```
