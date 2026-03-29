---
id: TASK-TI-023
title: Document ainvoke() message contract and retry pattern
status: completed
created: 2026-03-29T23:30:00Z
updated: 2026-03-30T00:05:00Z
completed: 2026-03-30T00:05:00Z
priority: p1
tags: [template, documentation, sdk-contract, adversarial]
complexity: 2
parent_review: TASK-REV-32D2
feature_id: FEAT-TI
wave: 0
implementation_mode: direct
depends_on: []
test_results:
  status: passed
  coverage: null
  last_run: 2026-03-30T00:05:00Z
---

# Task: Document ainvoke() Message Contract and Retry Pattern

## Description

TASK-REV-R2A1 discovered a critical SDK contract that caused a production crash: `create_agent()` unconditionally prepends the `system_prompt` on every `ainvoke()` call. Passing `system` role messages in the input dict causes dual system messages, which vLLM rejects with HTTP 400.

This contract must be documented in the template so users building adversarial agents don't repeat this bug.

## What to Create

1. **Add to `factory_guards.py` docstring**: The `ainvoke()` contract rule:
   - Input must contain only `user` and `assistant` messages
   - Never include `system` messages — the framework owns system message injection
   - Additional instructions (e.g., retry reinforcement) must use `user` role

2. **Add to AGENTS.md.template**: Warning about the `ainvoke()` contract

3. **Add `assert_no_system_messages()` usage note**: Already exists in `factory_guards.py` — ensure it's referenced in the orchestrator pattern documentation

4. **Add to orchestrator_pattern.py.template**: Comment documenting the correct retry pattern:

```python
# IMPORTANT: ainvoke() contract (TASK-REV-R2A1)
# create_agent() unconditionally prepends system_prompt on every ainvoke() call.
# NEVER pass system role messages in input — use "user" role for reinforcement.
# Violation causes dual system messages → vLLM HTTP 400.
retry_input = {
    "messages": [{
        "role": "user",  # NOT "system"
        "content": "IMPORTANT: Your previous response was not valid JSON..."
                   + player_content,
    }]
}
```

## Acceptance Criteria

- [x] `ainvoke()` contract documented in factory_guards.py
- [x] Retry pattern documented in orchestrator_pattern.py.template
- [x] AGENTS.md.template includes framework contract note
- [x] Warning references TASK-REV-R2A1 for traceability

## Effort Estimate

30 minutes
