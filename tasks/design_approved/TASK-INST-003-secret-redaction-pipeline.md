---
autobuild:
  enabled: true
  max_turns: 5
  mode: tdd
autobuild_state:
  base_branch: main
  current_turn: 1
  last_updated: '2026-03-02T13:42:04.725015'
  max_turns: 30
  started_at: '2026-03-02T13:36:04.686773'
  turns:
  - coach_success: true
    decision: approve
    feedback: null
    player_success: true
    player_summary: Implementation via task-work delegation
    timestamp: '2026-03-02T13:36:04.686773'
    turn: 1
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-CF57
complexity: 4
dependencies:
- TASK-INST-001
feature_id: FEAT-INST
id: TASK-INST-003
implementation_mode: task-work
parent_review: TASK-REV-2FE2
status: design_approved
task_type: feature
title: Implement secret redaction pipeline
wave: 2
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