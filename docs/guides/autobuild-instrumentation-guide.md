# AutoBuild Instrumentation Guide

**Version**: 1.0.0
**Last Updated**: 2026-03-08
**Compatibility**: GuardKit v1.0+, AutoBuild with instrumentation (FEAT-INST)
**Document Type**: Technical Reference

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Event Types Reference](#event-types-reference)
- [File Locations](#file-locations)
- [How to Use](#how-to-use)
- [Prompt Profiles and Digests](#prompt-profiles-and-digests)
- [Adaptive Concurrency](#adaptive-concurrency)
- [vLLM / Local Backend Specifics](#vllm--local-backend-specifics)
- [Secret Redaction](#secret-redaction)
- [Troubleshooting](#troubleshooting)

---

## Overview

AutoBuild instrumentation provides structured observability across the entire Player-Coach pipeline. Every LLM call, tool execution, task lifecycle event, wave completion, and Graphiti query is captured as a typed event and persisted to a local JSONL file.

**Why instrumentation exists:**

- **Cost tracking** — Token counts per call let you calculate spend per task and per feature.
- **Performance analysis** — Latency metrics (`latency_ms`, `ttft_ms`) reveal bottlenecks in LLM calls and tool executions.
- **A/B prompt comparison** — The `prompt_profile` field tags each call so you can compare digest-only vs digest+rules_bundle strategies.
- **Failure diagnosis** — Structured `failure_category` fields enable grouping and triaging failures without reading logs.
- **Adaptive concurrency** — Wave completion events feed the `ConcurrencyController` which auto-tunes worker count based on rate limits and p95 latency.

**Relationship to the AutoBuild pipeline:**

```
Feature Orchestrator → Waves → Tasks → Player-Coach Turns → LLM Calls + Tool Executions
       │                  │        │            │
  wave.completed    task.started  task.completed/failed   llm.call + tool.exec
```

Every layer of the pipeline emits events. The instrumentation is always-on JSONL — there is zero runtime cost when the data is not being analysed. Events are written append-only under an async lock and never block the LLM critical path.

---

## Architecture

### Event Emission Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                        EVENT SOURCES                                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  AutoBuildOrchestrator ──► task.started / task.completed / task.failed
│  AgentInvoker ──────────► llm.call / tool.exec                     │
│  FeatureOrchestrator ───► wave.completed                           │
│  GraphitiContextLoader ─► graphiti.query                           │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│                        MIDDLEWARE                                    │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  tool.exec events ──► SecretRedactor ──► redacted tool.exec        │
│  (cmd, stdout_tail, stderr_tail fields are scrubbed)               │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│                        EVENT EMITTER (Protocol)                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  EventEmitter Protocol:                                             │
│    async emit(event: BaseEvent) -> None                            │
│    async flush() -> None                                           │
│    async close() -> None                                           │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│                        BACKENDS                                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  CompositeBackend (fan-out)                                         │
│    ├── JSONLFileBackend (always-on) → events.jsonl                 │
│    └── NATSBackend (optional) → NATS subject                      │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Backend Options

| Backend | Purpose | Always On | Notes |
|---------|---------|-----------|-------|
| **JSONLFileBackend** | Local JSONL persistence | Yes | One JSON object per line, async-lock protected |
| **NATSBackend** | Async publish to NATS | No | Logs warning on failure, never raises |
| **CompositeBackend** | Fan-out to multiple backends | — | If one backend fails, others still receive the event |
| **NullEmitter** | Testing | — | Optionally captures events in `.events` list |

### Protocol-Based Injection

All orchestrators accept an `EventEmitter` via constructor injection. In production, a `CompositeBackend` wrapping `JSONLFileBackend` (+ optionally `NATSBackend`) is injected. In tests, `NullEmitter(capture=True)` is injected for assertion-based testing without file I/O.

---

## Event Types Reference

All events extend `BaseEvent` which provides these common fields:

| Field | Type | Description |
|-------|------|-------------|
| `run_id` | `str` | Unique identifier for the AutoBuild run |
| `feature_id` | `str?` | Optional feature identifier |
| `task_id` | `str` | Task identifier (e.g., `TASK-001`) |
| `agent_role` | `AgentRole` | `player`, `coach`, `resolver`, or `router` |
| `attempt` | `int` | 1-indexed attempt number |
| `timestamp` | `str` | ISO 8601 formatted timestamp |
| `schema_version` | `str` | Default `1.0.0` for forward compatibility |

### Controlled Vocabularies

**AgentRole**: `player` | `coach` | `resolver` | `router`

**FailureCategory**: `knowledge_gap` | `context_missing` | `spec_ambiguity` | `test_failure` | `env_failure` | `dependency_issue` | `rate_limit` | `timeout` | `tool_error` | `other`

**PromptProfile**: `digest_only` | `digest+graphiti` | `digest+rules_bundle` | `digest+graphiti+rules_bundle`

**LLMProvider**: `anthropic` | `openai` | `local-vllm`

**LLMCallStatus**: `ok` | `error`

**LLMCallErrorType**: `rate_limited` | `timeout` | `tool_error` | `other`

**GraphitiQueryType**: `context_loader` | `nearest_neighbours` | `adr_lookup`

**GraphitiStatus**: `ok` | `error`

### llm.call

Emitted for every LLM API call made by the Player or Coach.

| Field | Type | Description |
|-------|------|-------------|
| `provider` | `LLMProvider` | `anthropic`, `openai`, or `local-vllm` |
| `model` | `str` | Model identifier (e.g., `claude-sonnet-4-20250514`) |
| `input_tokens` | `int` | Number of input tokens |
| `output_tokens` | `int` | Number of output tokens |
| `latency_ms` | `float` | Total call latency in milliseconds |
| `ttft_ms` | `float?` | Time-to-first-token (streaming only) |
| `prefix_cache_hit` | `bool?` | Whether vLLM prefix cache was hit |
| `prefix_cache_estimated` | `bool` | Whether cache hit was estimated |
| `context_bytes` | `int?` | Context size in bytes |
| `prompt_profile` | `PromptProfile` | Which prompt assembly strategy was used |
| `status` | `LLMCallStatus` | `ok` or `error` |
| `error_type` | `LLMCallErrorType?` | Error classification when status is `error` |

**Example:**

```json
{
  "run_id": "run-a1b2c3d4",
  "feature_id": "FEAT-INST",
  "task_id": "TASK-INST-005b",
  "agent_role": "player",
  "attempt": 1,
  "timestamp": "2026-03-08T10:15:30.123Z",
  "schema_version": "1.0.0",
  "provider": "anthropic",
  "model": "claude-sonnet-4-20250514",
  "input_tokens": 12500,
  "output_tokens": 3200,
  "latency_ms": 8450.2,
  "ttft_ms": 1230.5,
  "prefix_cache_hit": null,
  "prefix_cache_estimated": false,
  "context_bytes": 48000,
  "prompt_profile": "digest+rules_bundle",
  "status": "ok",
  "error_type": null
}
```

### tool.exec

Emitted for every tool invocation (Bash, Read, Write, Edit, etc.). Fields are redacted for security.

| Field | Type | Description |
|-------|------|-------------|
| `tool_name` | `str` | Sanitised tool name |
| `cmd` | `str` | Command string (secrets redacted) |
| `exit_code` | `int` | Process exit code |
| `latency_ms` | `float` | Execution latency in milliseconds |
| `stdout_tail` | `str` | Truncated tail of stdout (secrets redacted) |
| `stderr_tail` | `str` | Truncated tail of stderr (secrets redacted) |

**Example:**

```json
{
  "run_id": "run-a1b2c3d4",
  "feature_id": null,
  "task_id": "TASK-INST-005b",
  "agent_role": "player",
  "attempt": 1,
  "timestamp": "2026-03-08T10:16:02.456Z",
  "schema_version": "1.0.0",
  "tool_name": "Bash",
  "cmd": "pytest tests/orchestrator/instrumentation/ -v --tb=short",
  "exit_code": 0,
  "latency_ms": 3200.1,
  "stdout_tail": "12 passed in 2.8s",
  "stderr_tail": ""
}
```

### task.started

Emitted when an AutoBuild task begins execution.

No additional fields beyond BaseEvent.

**Example:**

```json
{
  "run_id": "run-a1b2c3d4",
  "feature_id": null,
  "task_id": "TASK-INST-005b",
  "agent_role": "player",
  "attempt": 1,
  "timestamp": "2026-03-08T10:15:00.000Z",
  "schema_version": "1.0.0"
}
```

### task.completed

Emitted when a task finishes successfully.

| Field | Type | Description |
|-------|------|-------------|
| `turn_count` | `int` | Number of player-coach turns taken |
| `diff_stats` | `str` | Summary of code changes (e.g., `+50 -10`) |
| `verification_status` | `str` | Coach verification outcome |
| `prompt_profile` | `PromptProfile` | Profile used for the task |

**Example:**

```json
{
  "run_id": "run-a1b2c3d4",
  "feature_id": "FEAT-INST",
  "task_id": "TASK-INST-005b",
  "agent_role": "player",
  "attempt": 1,
  "timestamp": "2026-03-08T10:25:00.000Z",
  "schema_version": "1.0.0",
  "turn_count": 3,
  "diff_stats": "+180 -12",
  "verification_status": "pass",
  "prompt_profile": "digest+rules_bundle"
}
```

### task.failed

Emitted when a task fails after exhausting retries.

| Field | Type | Description |
|-------|------|-------------|
| `failure_category` | `FailureCategory` | Categorised reason for failure |

**Example:**

```json
{
  "run_id": "run-a1b2c3d4",
  "feature_id": "FEAT-INST",
  "task_id": "TASK-INST-005b",
  "agent_role": "player",
  "attempt": 3,
  "timestamp": "2026-03-08T10:35:00.000Z",
  "schema_version": "1.0.0",
  "failure_category": "test_failure"
}
```

### wave.completed

Emitted after each parallel wave in a feature build completes.

| Field | Type | Description |
|-------|------|-------------|
| `wave_id` | `str` | Unique identifier for the wave |
| `worker_count` | `int` | Number of concurrent workers |
| `queue_depth_start` | `int` | Queue depth at wave start |
| `queue_depth_end` | `int` | Queue depth at wave end |
| `tasks_completed` | `int` | Number of completed tasks |
| `task_failures` | `int` | Number of failed tasks |
| `rate_limit_count` | `int` | Number of rate-limit events |
| `p95_task_latency_ms` | `float?` | 95th percentile task latency |

**Example:**

```json
{
  "run_id": "run-a1b2c3d4",
  "feature_id": "FEAT-INST",
  "task_id": "wave-2",
  "agent_role": "router",
  "attempt": 1,
  "timestamp": "2026-03-08T10:40:00.000Z",
  "schema_version": "1.0.0",
  "wave_id": "wave-2",
  "worker_count": 3,
  "queue_depth_start": 5,
  "queue_depth_end": 2,
  "tasks_completed": 3,
  "task_failures": 0,
  "rate_limit_count": 0,
  "p95_task_latency_ms": 45000.0
}
```

### graphiti.query

Emitted for each Graphiti knowledge graph query.

| Field | Type | Description |
|-------|------|-------------|
| `query_type` | `GraphitiQueryType` | `context_loader`, `nearest_neighbours`, or `adr_lookup` |
| `items_returned` | `int` | Number of items returned |
| `tokens_injected` | `int` | Number of tokens injected into context |
| `latency_ms` | `float` | Query latency in milliseconds |
| `status` | `GraphitiStatus` | `ok` or `error` |

**Example:**

```json
{
  "run_id": "run-a1b2c3d4",
  "task_id": "TASK-INST-005b",
  "agent_role": "player",
  "attempt": 1,
  "timestamp": "2026-03-08T10:15:05.000Z",
  "schema_version": "1.0.0",
  "query_type": "context_loader",
  "items_returned": 4,
  "tokens_injected": 2800,
  "latency_ms": 320.5,
  "status": "ok"
}
```

---

## File Locations

| Resource | Path |
|----------|------|
| Events file | `.guardkit/autobuild/{task_id}/events.jsonl` |
| Player reports | `.guardkit/autobuild/{task_id}/player_turn_{turn}.json` |
| Coach decisions | `.guardkit/autobuild/{task_id}/coach_turn_{turn}.json` |
| Task-work results | `.guardkit/autobuild/{task_id}/task_work_results.json` |
| Digest files | `.guardkit/digests/{role}.md` (player, coach, resolver, router) |
| Schemas module | `guardkit/orchestrator/instrumentation/schemas.py` |
| Emitter module | `guardkit/orchestrator/instrumentation/emitter.py` |
| Redaction module | `guardkit/orchestrator/instrumentation/redaction.py` |
| Digests module | `guardkit/orchestrator/instrumentation/digests.py` |
| Prompt profiles | `guardkit/orchestrator/instrumentation/prompt_profile.py` |
| Concurrency | `guardkit/orchestrator/instrumentation/concurrency.py` |
| LLM helpers | `guardkit/orchestrator/instrumentation/llm_instrumentation.py` |
| Tests | `tests/orchestrator/instrumentation/` |

---

## How to Use

### Viewing Events

```bash
# Pretty-print all events for a task
cat .guardkit/autobuild/TASK-001/events.jsonl | jq .

# Count events by type
jq -r '.event_type' .guardkit/autobuild/TASK-001/events.jsonl | sort | uniq -c | sort -rn
```

### Filtering by Event Type

```bash
# All LLM calls
jq 'select(.event_type == "llm.call")' .guardkit/autobuild/TASK-001/events.jsonl

# All tool executions
jq 'select(.event_type == "tool.exec")' .guardkit/autobuild/TASK-001/events.jsonl

# All failures
jq 'select(.event_type == "task.failed")' .guardkit/autobuild/TASK-001/events.jsonl
```

### Token Usage Summary

```bash
# Token counts per LLM call
jq 'select(.event_type == "llm.call") | {model, input_tokens, output_tokens, latency_ms}' \
  .guardkit/autobuild/TASK-001/events.jsonl

# Total tokens for a task
jq -s '[.[] | select(.event_type == "llm.call")] |
  {total_input: (map(.input_tokens) | add),
   total_output: (map(.output_tokens) | add),
   call_count: length}' \
  .guardkit/autobuild/TASK-001/events.jsonl
```

### Comparing Prompt Profiles

```bash
# Group LLM calls by prompt profile
jq 'select(.event_type == "llm.call") | {prompt_profile, input_tokens, latency_ms}' \
  .guardkit/autobuild/TASK-001/events.jsonl

# Average tokens by profile (for A/B comparison)
jq -s '[.[] | select(.event_type == "llm.call")] | group_by(.prompt_profile) | map({
  profile: .[0].prompt_profile,
  avg_input: (map(.input_tokens) | add / length),
  avg_latency: (map(.latency_ms) | add / length),
  count: length
})' .guardkit/autobuild/TASK-001/events.jsonl
```

### Identifying Slow Tasks

```bash
# LLM calls sorted by latency (slowest first)
jq -s 'map(select(.event_type == "llm.call")) | sort_by(-.latency_ms) | .[:5] |
  .[] | {task_id, model, latency_ms, input_tokens}' \
  .guardkit/autobuild/TASK-001/events.jsonl

# Tool executions sorted by latency
jq -s 'map(select(.event_type == "tool.exec")) | sort_by(-.latency_ms) | .[:5] |
  .[] | {tool_name, cmd: .cmd[:80], latency_ms, exit_code}' \
  .guardkit/autobuild/TASK-001/events.jsonl
```

### Failure Analysis

```bash
# All failures grouped by category
jq 'select(.event_type == "task.failed") | {task_id, failure_category, attempt}' \
  .guardkit/autobuild/TASK-001/events.jsonl

# Errors in LLM calls
jq 'select(.event_type == "llm.call" and .status == "error") |
  {task_id, error_type, model, latency_ms}' \
  .guardkit/autobuild/TASK-001/events.jsonl
```

---

## Prompt Profiles and Digests

### What Prompt Profiles Are

A prompt profile describes which context sources are assembled into the system prompt for each agent invocation. The `prompt_profile` field on `llm.call` and `task.completed` events enables A/B comparison of different prompt strategies.

| Profile | Content | Tokens (typical) |
|---------|---------|-------------------|
| `digest_only` | Role-specific digest only | 300-600 |
| `digest+graphiti` | Digest + Graphiti knowledge context | 600-1200 |
| `digest+rules_bundle` | Digest + full rules bundle | 1500-3000 |
| `digest+graphiti+rules_bundle` | All sources combined | 2000-4000 |

**Current default**: `digest+rules_bundle` (Phase 1 baseline).

### Where Digest Files Live

Digest files are role-specific condensed instructions at `.guardkit/digests/`:

| File | Role | Purpose |
|------|------|---------|
| `player.md` | Player | Implementation rules, output contract, quality expectations |
| `coach.md` | Coach | Validation rules, output contract, anti-stub enforcement |
| `resolver.md` | Resolver | Conflict resolution rules |
| `router.md` | Router | Task routing and wave management rules |

### Token Budget

- **Target range**: 300-600 tokens per digest
- **Hard limit**: 700 tokens (enforced by `DigestValidator`)
- **Token counting**: Uses `tiktoken` (`cl100k_base` encoding) with word-based fallback (~0.75 tokens per word)

### Validating Digests

```python
from guardkit.orchestrator.instrumentation.digests import DigestValidator
from pathlib import Path

validator = DigestValidator(digest_dir=Path(".guardkit/digests"))

# Validate a single role
result = validator.validate("player")
print(f"Tokens: {result.token_count}, Warning: {result.warning}")

# Validate all roles
results = validator.validate_all()
for r in results:
    print(f"{r.role}: {r.token_count} tokens")
```

### Prompt Profile Migration Phases

| Phase | Profile | Description |
|-------|---------|-------------|
| Phase 1 (baseline) | `digest+rules_bundle` | Digest alongside full rules bundle; measures baseline token usage |
| Phase 2 | `digest_only` | Digest only; measures token savings and quality delta |
| Phase 3 | `digest+graphiti` | Digest with Graphiti context; measures knowledge-enhanced quality |
| Phase 4 | `digest+graphiti+rules_bundle` | All sources; measures combined effectiveness |

Compare phases by filtering events on `prompt_profile` and comparing token counts, latency, and task success rates.

---

## Adaptive Concurrency

The `ConcurrencyController` uses `wave.completed` events to automatically adjust the number of parallel workers during feature builds.

### How It Works

1. The `FeatureOrchestrator` emits a `wave.completed` event after each wave.
2. The `ConcurrencyController.on_wave_completed()` method evaluates the event.
3. A `ConcurrencyDecision` is returned with `action` (`maintain`, `reduce`, `increase`) and `new_workers`.

### Policy Rules

Rules are evaluated in order. First match wins.

| Priority | Trigger | Action | Detail |
|----------|---------|--------|--------|
| 1 | `rate_limit_count > 0` | Reduce by 50% | `new = max(1, current // 2)` |
| 2 | p95 latency > threshold | Reduce by 50% | Threshold = `baseline * (1 + p95_threshold_pct / 100)` |
| 3 | Stable for N minutes + reduced | Increase by +1 | `new = min(current + 1, initial)` |
| 4 | Default | Maintain | No change needed |

### Configuration

```python
from guardkit.orchestrator.instrumentation.concurrency import ConcurrencyController

controller = ConcurrencyController(
    initial_workers=4,          # Starting (and maximum) worker count
    p95_threshold_pct=100.0,    # 100% above baseline triggers reduction
    stability_minutes=5.0       # Minutes of stability before recovery
)
```

### Relevance to Local/vLLM Backends

On local inference backends, GPU contention is the primary bottleneck. The adaptive concurrency system is particularly valuable here because:

- **Rate limits manifest differently** — local vLLM servers queue requests rather than returning 429s, causing p95 latency spikes instead.
- **Recovery is safe** — the +1 gradual recovery avoids re-saturating the GPU.
- **Default `max_parallel=1`** — for local backends (per TASK-VPT-001), the controller starts conservative and adapts.

---

## vLLM / Local Backend Specifics

### Provider Detection

The `detect_provider()` function identifies the LLM backend from the base URL:

| Base URL Pattern | Detected Provider |
|------------------|-------------------|
| `None` or empty | `anthropic` |
| Contains `api.anthropic.com` | `anthropic` |
| Contains `openai` | `openai` |
| Contains `localhost` or `vllm` | `local-vllm` |

### Prefix Cache Hit Detection

For vLLM backends, the `x-vllm-prefix-cache-hit` response header is inspected:

- Header value `"true"` → `prefix_cache_hit=True`
- Header value `"false"` → `prefix_cache_hit=False`
- Header absent → `prefix_cache_hit=None`

The `prefix_cache_estimated` field is always `False` for direct header detection.

### Key Metrics to Watch

| Metric | Field | Why It Matters |
|--------|-------|----------------|
| Time to first token | `ttft_ms` | Measures prefill latency; high values indicate context too large for GPU |
| Total latency | `latency_ms` | End-to-end call time including generation |
| Input tokens | `input_tokens` | Prefill cost; digest-only profiles reduce this significantly |
| Prefix cache hit | `prefix_cache_hit` | Cache hits reduce prefill time; monitor hit rate |

### vLLM Defaults (from TASK-VPT-001)

| Setting | Value | Reason |
|---------|-------|--------|
| `max_parallel` | 1 | Prevents GPU contention on single-GPU setups |
| `timeout_multiplier` | 3.0 | Local inference is slower than API calls |

### jq Queries for vLLM Analysis

```bash
# All local-vllm calls with cache status
jq 'select(.event_type == "llm.call" and .provider == "local-vllm") |
  {model, input_tokens, ttft_ms, latency_ms, prefix_cache_hit}' \
  .guardkit/autobuild/TASK-001/events.jsonl

# Average TTFT for cached vs uncached
jq -s 'map(select(.event_type == "llm.call" and .provider == "local-vllm")) |
  group_by(.prefix_cache_hit) | map({
    cache_hit: .[0].prefix_cache_hit,
    avg_ttft: (map(.ttft_ms // 0) | add / length),
    count: length
  })' .guardkit/autobuild/TASK-001/events.jsonl
```

See also: [Local Backend AutoBuild Guide](local-backend-autobuild-guide.md) for vLLM server setup and tuning.

---

## Secret Redaction

### What Is Redacted Automatically

The `SecretRedactor` applies pattern-based redaction to `tool.exec` events only. The following patterns are scrubbed and replaced with `[REDACTED]`:

| Pattern | What It Catches |
|---------|-----------------|
| `sk-[A-Za-z0-9_-]{10,}` | OpenAI-style secret keys |
| `AKIA[A-Z0-9]{12,}` | AWS access key IDs |
| `gh[ps]_[A-Za-z0-9]{10,}` | GitHub tokens (personal + server) |
| `bearer [token]` (case-insensitive) | Bearer authentication tokens |
| `PASSWORD=...`, `PASS=...`, `SECRET=...` | Environment variable secrets |
| `token=...`, `api_key=...` | Generic token/key parameters |
| `://user:pass@host` | URL-embedded credentials |

### Redacted Fields

Only `tool.exec` events are redacted. The affected fields are:

- `cmd` — the command string
- `stdout_tail` — truncated stdout output
- `stderr_tail` — truncated stderr output

Additionally, `tool_name` is sanitised to remove shell metacharacters (`;`, `|`, `&`, `$`, `` ` ``, `>`, `<`, `(`, `)`).

### Adding Custom Redaction Patterns

```python
from guardkit.orchestrator.instrumentation.redaction import SecretRedactor

custom_redactor = SecretRedactor(patterns=[
    r"sk-[A-Za-z0-9_-]{10,}",       # Keep defaults
    r"AKIA[A-Z0-9]{12,}",
    r"my-custom-prefix-[A-Za-z0-9]+", # Add your own
])
```

Pass the custom redactor to `redact_tool_exec_event()` to apply it.

---

## Troubleshooting

### No Events in File

**Symptom**: `.guardkit/autobuild/{task_id}/events.jsonl` is empty or missing.

**Cause**: The emitter is not wired into the orchestrator. This was implemented in TASK-INST-013 (CLI emitter wiring).

**Fix**: Verify that the AutoBuild CLI creates a `JSONLFileBackend` and injects it into the orchestrators. Check `guardkit/cli/autobuild.py` for the emitter setup.

### DigestLoadError

**Symptom**: `DigestLoadError: Digest file not found for role 'player'`

**Cause**: Digest files are missing from `.guardkit/digests/`. This was implemented in TASK-INST-014 (digest file creation).

**Fix**: Ensure all four digest files exist:
```bash
ls .guardkit/digests/
# Expected: coach.md  player.md  resolver.md  router.md
```

### Events File Growing Large

The events file is append-only with no automatic rotation. For long-running feature builds, the file can grow large.

**Safe to delete between runs**:
```bash
rm .guardkit/autobuild/TASK-001/events.jsonl
```

A new file will be created on the next run. No data loss occurs for the current run — only historical events are removed.

### NATS Backend Warnings

**Symptom**: `WARNING: NATS publish failed: ...`

**Cause**: The NATS backend is optional. If the NATS server is unreachable, warnings are logged but events are still persisted to JSONL.

**Fix**: No action required. JSONL persistence is always-on and unaffected by NATS failures. To silence warnings, remove the `NATSBackend` from the `CompositeBackend` configuration.

### Events with `status: "error"`

Filter for error events to diagnose API issues:

```bash
# LLM call errors
jq 'select(.event_type == "llm.call" and .status == "error") |
  {task_id, error_type, model, provider}' \
  .guardkit/autobuild/TASK-001/events.jsonl

# Rate limit events specifically
jq 'select(.event_type == "llm.call" and .error_type == "rate_limited") |
  {timestamp, model, provider}' \
  .guardkit/autobuild/TASK-001/events.jsonl
```

---

### Related Documentation

- [AutoBuild Workflow Guide](autobuild-workflow.md) — Full AutoBuild architecture, Player-Coach loop, and CLI usage
- [Local Backend AutoBuild Guide](local-backend-autobuild-guide.md) — vLLM server setup, model alignment, and performance tuning
- [CLI vs Claude Code](cli-vs-claude-code.md) — When to use the CLI vs slash commands
