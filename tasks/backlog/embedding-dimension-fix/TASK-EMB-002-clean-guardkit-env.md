---
id: TASK-EMB-002
title: Remove infrastructure config from guardkit .env (keep only secrets)
status: backlog
created: 2026-03-09T00:00:00Z
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

- [ ] `guardkit/.env` contains only `OPENAI_API_KEY` (and optionally `ANTHROPIC_API_KEY`)
- [ ] `GRAPH_STORE`, `FALKORDB_HOST`, `FALKORDB_PORT` removed from `.env`
- [ ] Comment added explaining the secrets-only policy
- [ ] guardkit still works correctly (infra config comes from `graphiti.yaml`)

## Implementation

Change `guardkit/.env` to:

```
# GuardKit Environment Variables
# DO NOT commit this file to version control
#
# ONLY secrets go here. Infrastructure config is in .guardkit/graphiti.yaml
# See: TASK-REV-D2B5 for why infra config must NOT be in .env

# OpenAI API Key - required when using OpenAI providers
OPENAI_API_KEY=sk-proj-...
```

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
