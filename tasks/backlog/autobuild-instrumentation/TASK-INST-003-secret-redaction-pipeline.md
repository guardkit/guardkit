---
id: TASK-INST-003
title: Implement secret redaction pipeline
task_type: feature
parent_review: TASK-REV-2FE2
feature_id: FEAT-INST
wave: 2
implementation_mode: task-work
complexity: 4
dependencies:
- TASK-INST-001
autobuild:
  enabled: true
  max_turns: 5
  mode: tdd
status: in_review
autobuild_state:
  current_turn: 1
  max_turns: 30
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-CF57
  base_branch: main
  started_at: '2026-03-02T21:58:05.851037'
  last_updated: '2026-03-02T22:03:29.056675'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-03-02T21:58:05.851037'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
---

# Task: Implement Secret Redaction Pipeline

## Description

Create a redaction pipeline that sanitises secrets from tool.exec event fields before emission. This prevents API keys, tokens, and passwords from appearing in structured event logs.

## Requirements

### Redaction Patterns

Standard patterns to detect and redact:
- API keys (e.g., `sk-...`, `AKIA...`, `ghp_...`, `ghs_...`)
- Bearer tokens (e.g., `Bearer eyJ...`)
- Passwords in environment variables (e.g., `PASSWORD=secret`, `DB_PASS=value`)
- Generic token patterns (e.g., `token=...`, `api_key=...`)
- Base64-encoded credentials in URLs (e.g., `https://user:pass@host`)

### Redaction Rules

1. Matched secrets replaced with `[REDACTED]`
2. Redaction applied to `cmd`, `stdout_tail`, and `stderr_tail` fields of ToolExecEvent
3. Tool names sanitised against shell metacharacters (prevent injection via event data)
4. Redaction MUST NOT alter non-secret content
5. Redaction patterns are configurable (list of regex patterns)

### Sanitisation

- Tool names stripped of shell metacharacters (`; | & $ \` > < ( )`)
- Command arguments redacted but command structure preserved

## Acceptance Criteria

- [ ] Standard secret patterns detected and replaced with [REDACTED]
- [ ] cmd, stdout_tail, stderr_tail all redacted before event emission
- [ ] Tool names sanitised against shell metacharacters
- [ ] Non-secret content preserved unchanged
- [ ] Redaction patterns configurable via list
- [ ] No secret values appear in emitted events (validated by test)
- [ ] Unit tests cover all standard patterns plus edge cases

## File Location

`guardkit/orchestrator/instrumentation/redaction.py`

## Test Location

`tests/orchestrator/instrumentation/test_redaction.py`
