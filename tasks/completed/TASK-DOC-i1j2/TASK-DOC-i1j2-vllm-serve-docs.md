---
id: TASK-DOC-i1j2
title: Document vLLM SERVED_MODEL_NAME alignment requirement and add startup health check
status: completed
completed: 2026-02-24T00:00:00Z
completed_location: tasks/completed/TASK-DOC-i1j2/
task_type: implementation
created: 2026-02-23T00:00:00Z
updated: 2026-02-24T00:00:00Z
priority: low
tags: [autobuild, vllm, documentation, health-check, gb10]
complexity: 1
parent_review: TASK-REV-ED10
feature_id: FEAT-7a2e
wave: 3
implementation_mode: task-work
dependencies: [TASK-FIX-f1a2]
test_results:
  status: pending
  coverage: null
---

# Task: Document vLLM SERVED_MODEL_NAME alignment requirement and add startup health check

## Problem Statement

The relationship between `SERVED_MODEL_NAME` in `scripts/vllm-serve.sh` and the bundled `claude`
CLI default model ID is implicit. There is no documentation explaining that:
1. `SERVED_MODEL_NAME` must match the model ID the Claude CLI sends by default
2. If the Claude SDK is upgraded and the bundled CLI default changes, `SERVED_MODEL_NAME` must be
   updated too (or all SDK invocations will 404)
3. This exact issue has already caused two separate failures (TASK-REV-AB3D for the Player,
   TASK-REV-ED10 for the Coach)

Without this documentation, the next SDK upgrade will silently break vLLM autobuild again.

## Acceptance Criteria

- [x] `scripts/vllm-serve.sh` includes a comment block explaining the `SERVED_MODEL_NAME`
      alignment requirement and how to verify it
- [x] `docs/guides/simple-local-autobuild.md` (or equivalent) documents the model alignment
      requirement and references `vllm-serve.sh`
- [ ] (Optional) A pre-flight health check hint is added to the autobuild CLI output when
      `ANTHROPIC_BASE_URL` is set, reminding operators to verify `/v1/models` includes the
      expected model alias before starting

## Implementation Notes

### vllm-serve.sh comment block

Add above the `SERVED_MODEL_NAME` line:

```bash
# IMPORTANT: SERVED_MODEL_NAME must match the model ID used by the bundled claude CLI.
# The Claude Agent SDK's bundled 'claude' binary sends requests using its own default model ID.
# As of Claude Code Sonnet 4.6: the CLI default is "claude-sonnet-4-6".
# If you upgrade guardkit-py or claude-agent-sdk and autobuild starts failing with 404,
# check the new CLI default: ANTHROPIC_BASE_URL=http://localhost:8000 claude --version
# then update SERVED_MODEL_NAME below to match.
# See: docs/guides/simple-local-autobuild.md for full setup instructions.
SERVED_MODEL_NAME="claude-sonnet-4-6"
```

### docs/guides/ update

Add a "Model Alignment" section to the local autobuild guide explaining:
- Why `SERVED_MODEL_NAME` matters
- How to verify alignment: `curl http://localhost:8000/v1/models` vs `claude --version`
- What breaks when they diverge (Player 404, Coach SDK error)
- Reference to TASK-REV-AB3D and TASK-REV-ED10 as historical examples

## Files to Modify

- `scripts/vllm-serve.sh` — add comment block above `SERVED_MODEL_NAME`
- `docs/guides/simple-local-autobuild.md` (or create if absent) — add Model Alignment section
