---
id: TASK-REV-84A7
title: Analyse failing Graphiti add-context commands
status: review_complete
created: 2026-03-18T00:00:00Z
updated: 2026-03-18T00:00:00Z
priority: high
tags: [graphiti, vllm, token-limits, context-window]
task_type: review
review_mode: decision
review_depth: standard
complexity: 3
review_results:
  mode: decision
  depth: standard
  findings_count: 4
  recommendations_count: 4
  decision: implement_option_a
  report_path: .claude/reviews/TASK-REV-84A7-review-report.md
  completed_at: 2026-03-18T00:00:00Z
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Analyse failing Graphiti add-context commands

## Description

Analyse the failing `guardkit graphiti add-context` commands when seeding the agentic-dataset-factory project. Multiple files fail with the same root cause: `max_tokens` (16384) exceeds the remaining context window of the Qwen 2.5 model (32768 total context).

## Evidence Files

- **Command run log**: `docs/reviews/failing-graphiti/run-1.md`
- **Docker container logs**: `docs/reviews/failing-graphiti/docker-1.md`

## Observed Behaviour

### Successful commands
- `docs/design/contracts/API-tools.md`
- `docs/design/contracts/API-output.md`
- `docs/design/models/DM-goal-schema.md`
- `docs/design/decisions/DDR-001.md`
- `docs/design/decisions/DDR-002.md`
- `docs/design/decisions/DDR-003.md`

### Failed commands (all same error)
- `docs/design/contracts/API-entrypoint.md` — input 18954 tokens
- `docs/design/models/DM-training-example.md` — input 17557 tokens
- `docs/design/models/DM-coach-rejection.md` — input 16765 tokens
- `docs/design/models/DM-agent-config.md` — input 17335 tokens
- `docs/design/models/DM-rejected-example.md` — input 16591 tokens

### Root Error
```
'max_tokens' or 'max_completion_tokens' is too large: 16384.
This model's maximum context length is 32768 tokens and
your request has N input tokens (16384 > 32768 - N).
```

The graphiti-core LLM client hardcodes `max_tokens=16384`. When input tokens exceed ~16384 (i.e., input + max_tokens > 32768), the request fails. Retries (2 attempts) don't help since the same parameters are re-sent.

## Review Objectives

1. **Root cause confirmation**: Verify whether the 16384 max_tokens is hardcoded in graphiti-core or configurable
2. **GuardKit's role**: Determine if GuardKit can override max_tokens when initialising the Graphiti LLM client
3. **Document size analysis**: Understand why some docs succeed (smaller input tokens) and others fail
4. **Docker log analysis**: Check for any additional errors or warnings in the vLLM/container logs
5. **Mitigation options**: Evaluate potential fixes:
   - Dynamic max_tokens calculation (e.g., `min(16384, context_window - input_tokens - buffer)`)
   - Document chunking for large files (already partially implemented?)
   - Increasing model context window (different model or vLLM config)
   - Configurable max_tokens in GuardKit's Graphiti integration

## Acceptance Criteria

- [ ] Root cause fully documented with code references
- [ ] Docker logs analysed for additional failure context
- [ ] At least 2 mitigation options evaluated with pros/cons
- [ ] Recommendation provided for preferred fix approach
