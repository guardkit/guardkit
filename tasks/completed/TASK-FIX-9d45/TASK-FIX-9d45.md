---
id: TASK-FIX-9d45
title: Remove body_content from agent episode sync
status: completed
task_type: implementation
created: 2026-03-04T12:00:00Z
updated: 2026-03-04T13:05:00Z
completed: 2026-03-04T13:05:00Z
completed_location: tasks/completed/TASK-FIX-9d45/
priority: high
tags: [graphiti, template-sync, agent-sync, performance]
complexity: 1
parent_review: TASK-REV-FE10
feature_id: FEAT-init-graphiti-remaining-fixes
wave: 1
implementation_mode: direct
dependencies: []
---

# Task: Remove body_content from agent episode sync

## Description

Remove the `body_content` field from the agent episode body in `sync_agent_to_graphiti()`. This is the same pattern as TASK-FIX-6e46 (which removed `full_content` from rule sync), applied to agents.

Two of three agents timed out at 120s during init_project_4 Step 2.5. The `body_content` field includes the full agent markdown body (~3KB), causing graphiti-core to run ~60 LLM calls for entity extraction. Removing it reduces extraction to metadata-only fields (~500 bytes).

## Why This Is Safe

The `agents` group in Graphiti is **NEVER queried by the Player/Coach autobuild agents**. Confirmed by code trace through `job_context_retriever.py` — same finding as TASK-FIX-6e46 for rules.

Agent content is served to Claude Code via `.claude/agents/*.md` files copied during Step 1 of init. The `body_content` field in agent episodes serves no runtime purpose.

## Evidence

From init_project_4.md:
- `fastapi-database-specialist`: succeeded (69s) — metadata + body_content
- `fastapi-specialist`: **timed out** (120s) — metadata + body_content
- `fastapi-testing-specialist`: **timed out** (120s) — metadata + body_content

All three files are ~3KB. File size is NOT the differentiator — the timeouts are non-deterministic due to OpenAI API latency variance.

## Files to Modify

- `guardkit/knowledge/template_sync.py` — remove `body_content` field from agent_body dict (line 385)
- `tests/knowledge/test_template_sync.py` — update tests to assert `body_content` is absent

## Implementation

```python
# BEFORE (template_sync.py:372-386):
agent_body = {
    "entity_type": "agent",
    "id": agent_name,
    "name": metadata.get('name', agent_name),
    "description": metadata.get('description', ''),
    "template_id": template_id,
    "capabilities": metadata.get('capabilities', []),
    "technologies": metadata.get('technologies', []),
    "stack": metadata.get('stack', []),
    "phase": metadata.get('phase', ''),
    "priority": metadata.get('priority', 5),
    "collaborates_with": metadata.get('collaborates_with', []),
    "keywords": metadata.get('keywords', []),
    "body_content": body_text,       # <-- REMOVE THIS LINE
}

# AFTER:
agent_body = {
    "entity_type": "agent",
    "id": agent_name,
    "name": metadata.get('name', agent_name),
    "description": metadata.get('description', ''),
    "template_id": template_id,
    "capabilities": metadata.get('capabilities', []),
    "technologies": metadata.get('technologies', []),
    "stack": metadata.get('stack', []),
    "phase": metadata.get('phase', ''),
    "priority": metadata.get('priority', 5),
    "collaborates_with": metadata.get('collaborates_with', []),
    "keywords": metadata.get('keywords', []),
    "content_preview": body_text[:500] if body_text else "",  # <-- ADD THIS
}
```

Note: This combines Fix 1 (remove body_content) and Fix 3 (add content_preview) from the review report into a single task, since they modify the same line and are logically coupled.

## Acceptance Criteria

- [ ] `body_content` field removed from agent_body dict
- [ ] `content_preview` (500 chars) added for search display
- [ ] Tests updated and passing
- [ ] `guardkit init fastapi-python` Step 2.5 agents sync faster (~30-50s vs 120s timeout)
