---
id: TASK-CRV-3B1A
title: SDK sessions for Player resumption after CancelledError
status: backlog
created: 2026-03-09T00:00:00Z
updated: 2026-03-09T00:00:00Z
priority: medium
tags: [sdk, sessions, player, cancellederror, future]
task_type: feature
parent_review: TASK-REV-3F40
feature_id: FEAT-8290
wave: 4
implementation_mode: task-work
complexity: 7
dependencies: [TASK-CRV-1540]
---

# Task: SDK sessions for Player resumption after CancelledError

## Description

The Claude Agent SDK supports sessions (`session_id`) for resuming agent conversations with full context preserved. Currently, each Player invocation is stateless — when CancelledError fires, the Player starts over from scratch on the next turn. Using SDK sessions would allow the Player to resume from where it was cancelled, reducing redundant work and improving turn efficiency.

## Acceptance Criteria

- [ ] Player invocations capture `session_id` from SDK response
- [ ] On CancelledError, session_id stored in autobuild state for the task
- [ ] Next Player turn resumes the session using stored session_id
- [ ] Session resume prompt includes delta context (Coach feedback, new test results)
- [ ] Fallback to fresh invocation if session resume fails
- [ ] Session IDs cleaned up on task completion or task change
- [ ] Performance comparison: turns-to-approval with vs without session resume

## Implementation Notes

SDK session pattern (from official docs):

```python
# First invocation
async for message in query(prompt=prompt, options=options):
    response_messages.append(message)
    if isinstance(message, ResultMessage):
        session_id = message.session_id  # Capture
        break

# Resume invocation
options_with_session = ClaudeAgentOptions(
    ...existing_options,
    session_id=session_id,
)
async for message in query(prompt=resume_prompt, options=options_with_session):
    # Continues with full previous context
```

### Integration Points

- `agent_invoker.py`: Capture session_id from ResultMessage
- `autobuild.py`: Store session_id per task in autobuild_state
- `agent_invoker.py`: Accept optional session_id for resume
- Turn loop: Pass session_id from previous turn's CancelledError

### Risks

- Session state may expire between turns
- Resume context may conflict with Coach feedback
- Session storage increases state complexity

## Files to Modify

- `guardkit/orchestrator/agent_invoker.py` (session capture and resume)
- `guardkit/orchestrator/autobuild.py` (session state management)
- Task state YAML schema (add session_id field)
