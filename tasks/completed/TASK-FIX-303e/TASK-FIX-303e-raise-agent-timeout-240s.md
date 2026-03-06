---
id: TASK-FIX-303e
title: Raise agent episode timeout from 150s to 240s
status: completed
created: 2026-03-06T12:00:00Z
updated: 2026-03-06T12:30:00Z
completed: 2026-03-06T12:30:00Z
completed_location: tasks/completed/TASK-FIX-303e/
priority: low
task_type: implementation
complexity: 2
parent_review: TASK-REV-8A31
feature_id: FEAT-GIP
tags: [graphiti, seeding, timeout, agents]
wave: 2
implementation_mode: task-work
dependencies: [TASK-FIX-cc7e]
---

# Task: Raise agent episode timeout from 150s to 240s

## Problem

9 of 18 agent episodes still timeout at the 150s tier. Agents generate substantial content requiring extended LLM processing. The jump from 6/18 to 9/18 on fresh vLLM (guardkit_3) suggests some agents are near the 150s boundary.

### Consistently Timing Out Agents (guardkit_3)

- agent_mcp_typescript_mcp_testing_specialist
- agent_nextjs_fullstack_nextjs_server_components_specialist
- agent_react_fastapi_monorepo_docker_orchestration_specialist
- agent_react_fastapi_monorepo_monorepo_type_safety_specialist
- agent_react_fastapi_monorepo_react_fastapi_monorepo_specialist

These 5 timed out in guardkit_3. An additional 4 timed out in guardkit_2 but succeeded in guardkit_3 (near-boundary episodes).

## Solution

Increase the agent timeout tier from 150s to 240s in `graphiti_client.py`. This should recover 3-5 more agents that are in the 150-240s range.

## Scope

- Change the agent timeout constant from 150s to 240s
- Verify the timeout tier logic in `graphiti_client.py` (the `"agent" in group_id` pattern)
- Run a confirmation reseed to measure improvement

## Acceptance Criteria

- [x] Agent timeout increased to 240s
- [x] Timeout tier logic verified
- [x] Tests pass

## Completion Summary

### Changes Made
- `guardkit/knowledge/graphiti_client.py:980` — Agent episode timeout raised from 150s to 240s
- `tests/knowledge/test_graphiti_client.py:778,785` — Test assertion updated to match new 240s timeout

### Verification
- 7/7 timeout-related tests pass
- Timeout tier logic confirmed: `group_id == "agents"` matches all agent episodes (seeded via `seed_agents.py` with `group_id="agents"`)
