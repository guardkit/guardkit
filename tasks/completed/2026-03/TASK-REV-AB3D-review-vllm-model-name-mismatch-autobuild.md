---
id: TASK-REV-AB3D
title: Review vLLM model name mismatch causing autobuild SDK failures
status: backlog
task_type: review
created: 2026-02-23T14:00:00Z
updated: 2026-02-23T14:00:00Z
priority: high
tags: [autobuild, vllm, local-inference, sdk, model-name, gb10]
complexity: 3
related_tasks: [TASK-REV-8B3A]
evidence:
  request_log: docs/reviews/gb10_local_autobuild/run_1_request.md
  vllm_log: docs/reviews/gb10_local_autobuild/run_1_vllm.md
review_results:
  status: pending
  decision: null
test_results:
  status: pending
  coverage: null
---

# Task: Review vLLM Model Name Mismatch — Autobuild SDK Failures

## Problem Statement

AutoBuild fails immediately when using the local vLLM server (GB10). The SDK call
to the vLLM `/v1/messages` endpoint returns a 404 because the model name the SDK
sends does not match the alias vLLM is configured to serve.

## Evidence

### From `run_1_vllm.md` (vLLM server log)

```
ERROR 02-23 13:48:05 [serving_chat.py:179] Error with model
  error=ErrorInfo(message='The model `claude-sonnet-4-6` does not exist.',
  type='NotFoundError', param=None, code=404)
POST /v1/messages?beta=true HTTP/1.1" 404 Not Found
```

Note: the first request at 13:47:02 returned **200 OK** (the server itself is reachable),
but all subsequent autobuild SDK calls failed with 404.

### From `run_1_request.md` (autobuild output)

```
│ Model: claude-sonnet-4-5-20250929
```

The banner shows `claude-sonnet-4-5-20250929` — this is what the orchestrator
*intended* to use. However the underlying Claude Agent SDK CLI uses `claude-sonnet-4-6`
(its own current model ID) when making API calls, regardless of the orchestrator setting.

### From `curl http://localhost:8000/v1/models`

```json
{"id": "claude-sonnet-4-5-20250929", "root": "Qwen/Qwen3-Coder-Next-FP8"}
```

The vLLM server only registers one model alias: `claude-sonnet-4-5-20250929`.

## Root Cause Analysis

| Component | Value |
|---|---|
| vLLM `--served-model-name` | `claude-sonnet-4-5-20250929` |
| SDK actual request model | `claude-sonnet-4-6` |
| Result | 404 Not Found |

The `SERVED_MODEL_NAME` in `scripts/vllm-serve.sh` is set to `claude-sonnet-4-5-20250929`
(an older Claude model alias). The bundled Claude Agent SDK CLI
(`claude_agent_sdk/_bundled/claude`) sends requests using `claude-sonnet-4-6`,
which is the current Claude Sonnet model ID. These two values do not match, so
vLLM rejects every autobuild SDK call.

The `ANTHROPIC_BASE_URL` override correctly redirects traffic to the local vLLM
server, but vLLM's model name validation then rejects the request because the
model ID is unknown.

## Recommended Fix

Update `SERVED_MODEL_NAME` in `scripts/vllm-serve.sh` from:

```bash
SERVED_MODEL_NAME="claude-sonnet-4-5-20250929"
```

to:

```bash
SERVED_MODEL_NAME="claude-sonnet-4-6"
```

This aligns the vLLM alias with the model ID the Claude Agent SDK actually sends.
The vLLM server will then accept autobuild requests and route them to
`Qwen/Qwen3-Coder-Next-FP8` for local inference.

After changing the alias, restart the container:
```bash
./scripts/vllm-serve.sh
```

Then re-verify:
```bash
curl http://localhost:8000/v1/models
# Expected: "id": "claude-sonnet-4-6"
```

## Acceptance Criteria

- [ ] `scripts/vllm-serve.sh` `SERVED_MODEL_NAME` updated to `claude-sonnet-4-6`
- [ ] vLLM container restarted and `/v1/models` returns `claude-sonnet-4-6`
- [ ] `guardkit autobuild task TASK-GLI-004 --verbose` completes the design phase without a 404
- [ ] `docs/fixes/` updated with a note on the model name mismatch

## Additional Investigation (Optional)

If the autobuild orchestrator itself has a model configuration setting that is
separate from the SDK's built-in model, investigate whether that setting needs
to be kept in sync with future Claude model releases, or whether it can be removed
in favour of always deferring to whatever model the SDK uses by default.
