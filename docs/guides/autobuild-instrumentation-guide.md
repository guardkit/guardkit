# AutoBuild Instrumentation Guide

**Version**: 1.1.0
**Last Updated**: 2026-04-11
**Compatibility**: GuardKit v1.0+, AutoBuild with instrumentation (FEAT-INST)
**Document Type**: Technical Reference

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Event Types Reference](#event-types-reference)
- [File Locations](#file-locations)
- [How to Use](#how-to-use)
- [Prompt Profiles and Digests](#prompt-profiles-and-digests)
- [Template Pattern Context](#template-pattern-context)
- [Adaptive Concurrency](#adaptive-concurrency)
- [vLLM / Local Backend Specifics](#vllm--local-backend-specifics)
- [Secret Redaction](#secret-redaction)
- [Bootstrap Hard-Fail Gate (`bootstrap_failure_mode`)](#bootstrap-hard-fail-gate-bootstrap_failure_mode)
- [Troubleshooting](#troubleshooting)
  - [If AutoBuild stalls immediately](#if-autobuild-stalls-immediately)

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
| Template pattern loader | `guardkit/knowledge/template_pattern_loader.py` |
| Template resolver | `guardkit/templates/resolver.py` |
| Context loader (pattern wiring) | `guardkit/knowledge/autobuild_context_loader.py` |
| Tests (instrumentation) | `tests/orchestrator/instrumentation/` |
| Tests (template patterns) | `tests/unit/test_template_pattern_loader.py` |

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

### Heartbeat Labels

Heartbeat log lines emitted by `async_heartbeat` (`[<task_id>] <phase> in progress... (<N>s elapsed)`) use distinct phase labels so operators can disambiguate which agent is running:

- **`task-work implementation`** — the actual `task-work` Player invocation (the real implementation work).
- **`Player invocation`** / **`Coach invocation`** — direct `_invoke_with_role` calls without a delegation wrapper (legacy call sites).
- **`specialist:<name> invocation`** — orchestrator-driven specialists run via `run_specialist` (`specialist:test-orchestrator invocation` for Phase 4, `specialist:code-reviewer invocation` for Phase 5). These run as `agent_type=player`/`coach` under the hood but surface a distinct label so they aren't conflated with the actual Player. (TASK-ABSR-DIAG.)

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

## Template Pattern Context

### Overview

Template pattern context injects stack-specific `.template` files into the Player's prompt at build time, giving the AI canonical code shapes to follow when generating code. This was implemented in FEAT-TPL-PLAYER (tasks TASK-TPL-001 through TASK-TPL-004).

**Why template patterns exist:**

- **Consistency** — The Player sees the same patterns the template author intended, producing code that matches the project's established architecture.
- **Reduced hallucination** — Instead of inferring patterns from agent prose descriptions, the Player reads actual parameterised code templates.
- **Stack-specific guidance** — Each builtin template ships its own `.template` files (FastAPI routers, .NET endpoints, React components, etc.). Only relevant files are loaded per task.

### Data Flow

```
guardkit init <template>
    │
    ├── Copies .claude/ config layer → project
    └── Records template name in .claude/manifest.json
        │
        ... (development happens) ...
        │
/feature-build TASK-XXX
    │
    ▼
AutoBuildContextLoader._append_template_patterns()
    │
    ├── 1. Read .claude/manifest.json → extract `name` field
    │
    ├── 2. resolve_template_source_dir(name)
    │       → installer/core/templates/{name}/
    │       → fallback: ~/.guardkit/templates/{name}/
    │
    ├── 3. load_template_patterns(manifest_path)
    │       → enumerate templates/*.template files
    │
    ├── 4. select_patterns(context, tech_stack, file_path_hints)
    │       → file-path hint matching (priority 1)
    │       → tech-stack keyword fallback (priority 2)
    │       → alphabetical fallback (priority 3)
    │       → cap: max 5 files, ~3000 tokens
    │
    ├── 5. format_pattern_block(context, file_contents)
    │       → markdown block with fenced code blocks
    │
    └── 6. Append to AutoBuildContextResult.prompt_text
```

### Key Components

| Component | File Path | Purpose |
|-----------|-----------|---------|
| Template pattern loader | `guardkit/knowledge/template_pattern_loader.py` | Reads manifest, resolves template dir, enumerates `.template` files |
| Template resolver | `guardkit/templates/resolver.py` | Resolves template source directory from name |
| Context integration | `guardkit/knowledge/autobuild_context_loader.py` | `_append_template_patterns()` wires loader into Player context |
| Tests | `tests/unit/test_template_pattern_loader.py` | Unit tests for loader, selector, and formatter |

### Manifest Requirement

The `.claude/manifest.json` file must contain a `name` field matching a known template:

```json
{
  "name": "fastapi-python",
  "version": "1.0.0"
}
```

This is written automatically by `guardkit init <template>`. Projects without a manifest (or with a missing/invalid `name` field) degrade gracefully — no patterns are loaded, no errors are raised, and the Player proceeds without pattern context.

### Pattern Selection Rules

Selection follows a priority cascade:

1. **File-path hints** — If the task touches files in `app/api/`, match template files under an `api/` subdirectory.
2. **Tech-stack keywords** — If no file-path matches, use the tech stack (e.g., `"python"` → look for `api/`, `core/`, `config/`, `models/` subdirectories).
3. **Alphabetical fallback** — If nothing else matches, take the first 3 files alphabetically.
4. **Budget enforcement** — Maximum 5 files, approximately 3000 tokens. Files that would exceed the budget are skipped with a warning.

### Graceful Degradation

The template pattern pipeline never raises exceptions. Each failure point produces a warning and returns empty context:

| Condition | Behaviour |
|-----------|-----------|
| No `worktree_path` configured | Skip silently (debug log) |
| `.claude/manifest.json` missing | Skip silently (debug log) |
| `name` field missing or invalid | Warning logged, empty context |
| Template source dir not found | Warning logged, empty context |
| No `templates/` subdirectory | Warning logged, empty context |
| No files match selection criteria | Skip silently (debug log) |
| File read error | Individual file skipped, others still loaded |

### Logging

Template pattern loading emits structured log messages at info and warning levels:

```
[TemplatePattern] Appended pattern block: 3 files, ~750 tokens (api/router.py.template, models/base.py.template, crud/crud_base.py.template)
[TemplatePattern] Skipped db/session.py.template: adding 400 tokens would exceed budget (2800/3000)
```

### Token Impact

Typical token costs by template type:

| Template | Files Available | Files Selected (typical) | Token Cost |
|----------|----------------|--------------------------|------------|
| fastapi-python | 8-12 | 3-5 | ~500-800 |
| dotnet-railway-fastendpoints | 18-22 | 3-5 | ~600-1000 |
| react-typescript | 6-10 | 3-5 | ~400-700 |
| python-library | 4-6 | 3-4 | ~300-500 |
| No manifest / unknown template | — | 0 | 0 |

The ~500-1000 token overhead is comparable to a single Graphiti context block and is well within the Player's context budget.

### Relationship to Other Context Sources

Template patterns are additive — they do not replace any existing context source:

```
Player Context Assembly:
  ├── Graphiti knowledge context (similar outcomes, patterns, ADRs)
  ├── Role constraints and quality gates
  ├── Turn states (cross-turn learning)
  ├── Implementation modes
  ├── Template pattern context  ◄── NEW (FEAT-TPL-PLAYER)
  └── Task description and acceptance criteria
```

The pattern block is appended to `prompt_text` after all other context sources. It appears in the Player's prompt as a "## Stack Pattern Reference" section.

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

## Bootstrap Hard-Fail Gate (`bootstrap_failure_mode`)

When AutoBuild creates a shared worktree it runs an environment bootstrap (detect `pyproject.toml` / `package.json` / `*.csproj` / etc., run the matching install). By default this phase is **non-blocking** — if every install fails the orchestrator prints a yellow-⚠ line and proceeds into Wave 1 anyway.

For the forge/GB10 case this turned into a foot-gun: `forge` required Python ≥3.13 but the GB10 host ran 3.12, every `pip install -e .` failed, and AutoBuild still marched into Wave 1. Review [TASK-REV-E4F5](../../.claude/reviews/TASK-REV-E4F5-review-report.md) recommendation R4a asked for an opt-in gate that turns this into a loud error instead of a silent warning. [TASK-FIX-7A04](../../tasks/in_progress/autobuild-sdk-stall-resilience/TASK-FIX-7A04-bootstrap-hardfail-gate.md) implements it.

### Configuration

Set in `.guardkit/config.yaml` (feature-level), override per-invocation on the CLI:

```yaml
# .guardkit/config.yaml
autobuild:
  bootstrap:
    failure_mode: warn   # "warn" (default) or "block"
    optional_stacks: []  # stacks that should NOT count toward the essential-stack check
```

```bash
# CLI override — wins over the yaml value
guardkit autobuild feature FEAT-XXX --bootstrap-failure-mode block
```

### Modes

| Mode | Behavior when 0/N installs succeed | Behavior when partial success | Behavior when all succeed |
|---|---|---|---|
| `warn` (default) | yellow-⚠ line, continue to Wave 1 | yellow-⚠ line, continue | green-✓ line, continue |
| `block` | raise `FeatureOrchestrationError` before Wave 1 | yellow-⚠ line, continue | green-✓ line, continue |

`block` fires only on **total-failure** (`installs_failed == installs_attempted`) of at least one **essential** stack (i.e. a detected stack not listed in `optional_stacks`). Partial success is never blocking — the orchestrator is still making progress.

### When to use `block`

- **Dedicated AutoBuild hosts** (e.g. GB10-class boxes running `claude-agent-sdk`) where a silent-broken environment will just produce Coach-runs-against-wrong-interpreter failures a wave later. The loud error at `_bootstrap_environment` beats a cryptic pytest failure two turns in.
- **`requires-python` constraints that don't match the host** (the forge/GB10 case). The hard-fail message carries the `requires-python` value and the PEP-668 stderr tail, so the fix is usually a one-line host upgrade.
- **CI / scheduled feature builds** where an unattended run with a broken venv is worse than a hard failure that gets picked up by the next agent.

### When to stay on `warn`

- **Developer machines** where you expect to manually reconcile a partial install (e.g. you're iterating on a new stack and the install genuinely may not work yet).
- **Features that intentionally span optional stacks**. Use `optional_stacks:` to downgrade specific stacks rather than flipping the whole feature back to `warn`.

### Error message shape

On hard-fail the error includes the attempted stacks, the manifest path, `requires-python` (when declared), a PEP-668 marker (when the install tripped `externally-managed-environment`), the stderr tail, and a hint:

```
FeatureOrchestrationError: Bootstrap hard-fail: 0/1 install(s) succeeded for essential stack(s): python.
Manifest: /worktree/pyproject.toml
Manifest requires-python: >=3.13
Detected PEP 668 externally-managed-environment failure.
Install stderr (tail):
error: externally-managed-environment
…
Hint: set `bootstrap_failure_mode: warn` in .guardkit/config.yaml (or pass `--bootstrap-failure-mode warn`) to downgrade this to a non-blocking warning.
```

### `requires-python` pre-check

The MacBook Pro `jarvis` FEAT-J002 run surfaced a neighboring failure mode: pip's error for an interpreter/`requires-python` mismatch is opaque (`Package 'jarvis' requires a different Python: 3.14.2 not in '<3.13,>=3.12'`) and easy to miss in the install log. To cut that diagnostic round-trip the orchestrator runs a **pre-pip `requires-python` check** (amendment from [TASK-REV-JMBP](../../.claude/reviews/TASK-REV-JMBP-review-report.md) Workstream E).

How it works:

1. For every Python manifest, read `requires-python` from `[project]` (PEP 621) or `[tool.poetry].python` (legacy Poetry).
2. Compare against the active interpreter's version via `packaging.specifiers.SpecifierSet`.
3. If any manifest fails the check, act based on `bootstrap_failure_mode`:
   - `warn` — emit a structured `⚠ Python X does not satisfy requires-python=`Y`` line per mismatch, then continue to pip (pip remains authoritative).
   - `block` — raise **before** pip runs, with a multi-line remediation hint that names `uv`, `pyenv`, and `conda` install commands for a compatible minor version.

The pre-check is a silent no-op when:

- A manifest declares no `requires-python` constraint.
- The specifier string is malformed (pip stays authoritative).
- `packaging.specifiers` is unavailable at import time.

Example `block`-mode error:

```
FeatureOrchestrationError: Bootstrap requires-python mismatch (pre-pip).
Python 3.14.2 does not satisfy requires-python=`<3.13,>=3.12` for /worktree/pyproject.toml.
Install a compatible interpreter with one of:
  • uv python install 3.12
  • pyenv install 3.12 && pyenv local 3.12
  • conda create -n <name> python=3.12 && conda activate <name>
Hint: set `bootstrap_failure_mode: warn` in .guardkit/config.yaml (or pass `--bootstrap-failure-mode warn`) to downgrade this to a non-blocking warning.
```

### Related work

- Wave 2 task [TASK-FIX-7A05](../../tasks/backlog/autobuild-sdk-stall-resilience/TASK-FIX-7A05-wire-venv-to-coach-pytest.md) wires the bootstrap venv into the Coach pytest interpreter, closing the rest of the GB10 class-of-defect (venv-was-built-but-Coach-ignored-it).
- Review: [TASK-REV-E4F5](../../.claude/reviews/TASK-REV-E4F5-review-report.md) findings F6 and F7.
- Amendment: [TASK-REV-JMBP](../../.claude/reviews/TASK-REV-JMBP-review-report.md) Workstream E (requires-python pre-check).

---

## Troubleshooting

### If AutoBuild stalls immediately

**Symptom**: AutoBuild exits or stalls within the first few seconds — no `task.started` event emitted, or the final-summary classification reads `player_invocation_stall` rather than a mid-loop coach-feedback stall.

This class-of-defect — *Player invocation systematically errored before any work happened, and the orchestrator misnamed the problem at summary-time* — has been observed twice:

- [TASK-REV-8A08](../../.claude/reviews/TASK-REV-8A08-review-report.md) on FEAT-486D / TASK-AD-004 (SDK stream timeout)
- [TASK-REV-E4F5](../../.claude/reviews/TASK-REV-E4F5-review-report.md) on FEAT-FORGE-002 (SDK auth + version skew)

Use this triage table to self-diagnose before opening a review:

| Symptom (from summary)                                    | Likely cause                                     | Quick check                                                                  |
|-----------------------------------------------------------|--------------------------------------------------|------------------------------------------------------------------------------|
| `player_invocation_stall` + auth error                    | Not logged into Claude on this host              | `claude` CLI login                                                           |
| `player_invocation_stall` + "Unknown message type"        | SDK version skew (e.g. `rate_limit_event`)       | `pip show claude-agent-sdk` — compare to working host                        |
| `player_invocation_stall` + stream/timeout                | Network or endpoint config                       | `ANTHROPIC_BASE_URL` + `vllm-serve.sh` — see [TASK-REV-8A08](../../.claude/reviews/TASK-REV-8A08-review-report.md) |
| `unrecoverable_stall [environment_stall]`                  | Worktree environment is broken — Player gates pass but independent tests fail with `failure_classification == "infrastructure"` for ≥3 consecutive turns (e.g. interpreter mismatch with `requires-python`) | Read the diagnostic line — it names the bootstrap state, the active interpreter, and the manifest's `requires-python`. Set `bootstrap_failure_mode: block` in `.guardkit/config.yaml` so the next run hard-fails at preflight, then install a compatible interpreter via `uv python install <X>` / `pyenv install <X>` / `conda create -n <name> python=<X>`. See [TASK-ABSR-C3D4](../../tasks/completed/TASK-ABSR-C3D4/TASK-ABSR-C3D4.md). |

**Where the signal lives**: `player_result.error` in the Player turn artefact, and `recovery_metadata` on synthetic reports. The orchestrator currently captures the signal at the call site but does not consult it at final-summary time; treat the summary's stall category as a starting guess, not an authoritative diagnosis, and open `player_result.error` first.

For `environment_stall`, the signal lives in the trailing `coach_turn_*.json` files: each turn carries `validation_results.quality_gates.all_gates_passed == True`, `validation_results.independent_tests.tests_passed == False`, and a `test_verification` issue with `failure_classification == "infrastructure"`. The summary renderer reads `<worktree>/.guardkit/bootstrap_state.json` and the worktree's `pyproject.toml` (via `DetectedManifest.get_requires_python()`) to enrich the diagnostic; missing or corrupt state files are tolerated. Non-Python worktrees fall through to the generic stall message.

**Related fix work**: [TASK-FIX-7A01](../../tasks/in_review/TASK-FIX-7A01-pin-sdk-log-version.md) pins `claude-agent-sdk` to a known-good band and logs the version at startup, which removes the SDK-skew failure mode from this table. Until that lands, the `pip show claude-agent-sdk` check is the fastest way to confirm or rule out version skew. The companion task [TASK-ABSR-A1B2](../../tasks/completed/2026-04/TASK-ABSR-A1B2-bootstrap-block-smart-default.md) makes `bootstrap_failure_mode: block` the smart-default when `requires-python` is declared, eliminating the `environment_stall` precondition for new runs.

### Environment-class conditional approval (`environment_conditional_approval`)

When a user explicitly opts into `bootstrap_failure_mode: warn` and the bootstrap install silently fails, Coach's independent pytest run will hit `ImportError` / `ModuleNotFoundError` even though Player's gates passed inside the (broken) venv. Without intervention this presents as a feedback loop on a purely environmental fault — Player has nothing to fix.

The fifth conditional-approval clause in `CoachValidator.validate` covers this case. It fires when **all** of the following are true:

- `failure_class == "infrastructure"` and `failure_confidence == "ambiguous"` (the `_INFRA_AMBIGUOUS` patterns: `ImportError`, `ModuleNotFoundError`, `No module named`)
- `gates_status.all_gates_passed == True` (Player did everything right inside the venv it had)
- `task.requires_infrastructure` is empty / unset (the existing `requires_infrastructure + Docker unavailable` branch already handles the declared-deps case)
- `<worktree>/.guardkit/bootstrap_state.json` exists and reports `success: False` (read by the `_bootstrap_likely_broken` helper — missing file or `success: true` is treated as "unknown / can't prove env failure" and the clause **does not** fire)

When the clause fires, the `CoachValidationResult` is tagged with `environment_conditional_approval: True` (visible in the JSON payload's top-level `environment_conditional_approval` key, alongside the longer-standing `approved_without_independent_tests` flag). Logs emit at `WARNING` level:

```
Conditional approval for {task_id}: environment-class infrastructure failure
(infrastructure/ambiguous) on a known-broken bootstrap; all Player gates passed.
Marking approved with environment flag.
```

The clause is deliberately narrow:

- A real `ImportError` on a **healthy** bootstrap (Player imported a non-existent module) does NOT match — `bootstrap_state.json` reports `success: True`, so the helper returns False, so the clause doesn't fire, and the existing feedback path runs as before.
- A code defect (`failure_class == "code"`) on a broken bootstrap also doesn't match — only the infrastructure/ambiguous classification triggers the clause.
- It pairs with the smart-default `bootstrap_failure_mode: block` work (TASK-ABSR-A1B2) and the `environment_stall` sub-type detection (TASK-ABSR-C3D4): when this clause fires, neither stall happens; when the clause doesn't fire (e.g. `block` mode aborted the run at preflight), neither does the stall.

**Origin**: belt-and-braces layer for [TASK-ABSR-A1B2](../../tasks/completed/2026-04/TASK-ABSR-A1B2-bootstrap-block-smart-default.md)'s smart-default, motivated by the FEAT-J004-702C / TASK-J004-004 stall. See [TASK-ABSR-2468](../../tasks/completed/TASK-ABSR-2468/TASK-ABSR-2468.md).

### Environment variable tunables

| Env var | Default | Purpose |
|---------|---------|---------|
| `GUARDKIT_MIN_TURN_BUDGET` | `600` | Overrides `MIN_TURN_BUDGET_SECONDS` (the wall-clock floor required before `_loop_phase` starts a new turn). Lower (e.g. `300`) on tasks where Coach feedback is small and short turn-2/3 retries are still useful; the orchestrator will exit with `timeout_budget_exhausted` only when the remaining budget falls below this floor. Read once at module load. See [TASK-ABSR-MTBC](../../tasks/completed/TASK-ABSR-MTBC/TASK-ABSR-MTBC-env-overridable-min-turn-budget.md). |
| `GUARDKIT_COACH_GRACE_PERIOD_SECONDS` | `1500` | Overrides `COACH_GRACE_PERIOD_SECONDS` — the budget granted to Coach when Player succeeds *and* the shared task-level `cancellation_event` is set (i.e. the real task-timeout boundary fired during the Player turn). Default raised from 120 → 1500 in TASK-FIX-SPECCOCH01 (Shape B) to cover empirically-observed Coach turn-1 latency under slow coaches (run-9 of FEAT-AOF measured 944 s under gemma4:26b with `--reasoning off`; the default leaves ~50 % headroom for `--reasoning auto`'s richer reasoning channel). The grace branch is now narrowly scoped to real task-timeout boundaries — Shape A of the same task decoupled specialist-hang detection from this event so a healthy hang in the test-orchestrator no longer cascades into Coach being capped at the grace budget. Also reserved upfront by `_cap_specialist_timeout` so specialists never consume the budget Coach might need. Read once at module load. Tune down (e.g. `300`) on fast coaches to reclaim specialist budget; tune up on very slow coaches. See [TASK-FIX-SPECCOCH01](../../tasks/in_progress/autobuild-harness-migration/TASK-FIX-SPECCOCH01-decouple-specialist-hang-from-coach-grace.md). |

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
- [Template Pattern Player Context](../features/FEAT-TPL-PLAYER-template-pattern-player-context.md) — Feature spec for template pattern injection (FEAT-TPL-PLAYER)

---

## Pre-merge `task_work_results.json` verification

> Source: TASK-AB-FIX-INVAB1 AC-013 (review report Appendix C). Cross-link
> from `.claude/rules/autobuild.md`.

Before merging an autobuild branch, run this defence-in-depth check to
catch the FEAT-6CC5 class of false-positive approval (Player-promised
files that don't actually exist on disk). The deterministic Coach gate
in `coach_validator.py` already enforces this on every turn after
TASK-AB-FIX-INVAB1, but the standalone script is useful when reviewing
historical archives or auditing a turn artefact in isolation.

```bash
# Detect promises that name implementation_files inconsistent with the
# Player's own files_created/files_modified lists.
python3 -c '
import json, sys
d = json.load(open(sys.argv[1]))
promised = {f for p in d.get("completion_promises", [])
              for f in (p.get("implementation_files") or [])
              if p.get("status") == "complete"}
actual = set(d.get("files_created", []) + d.get("files_modified", []))
missing = promised - actual
if missing:
    print(f"FALSE-POSITIVE INDICATOR: {sorted(missing)}")
    sys.exit(1)
print("ok")
' .guardkit/autobuild/TASK-XXX/task_work_results.json
```

Exit code 0 = pass; exit code 1 = at least one promised
implementation_file is absent from the Player's own files_created /
files_modified lists, indicating either (a) the Player misreported its
own changes or (b) the file genuinely does not exist on disk. Either
way, do not merge until the discrepancy is investigated.

**Architectural-regression detector** — confirms `CoachVerifier` is wired
into the deterministic Coach path:

```bash
$ grep -c "CoachVerifier\|_verify_player_claims\|HonestyVerification\|honesty_verification" \
    guardkit/orchestrator/quality_gates/coach_validator.py
# Post TASK-AB-FIX-INVAB1: must be ≥ 5 (imports + helpers + dataclass field
# + to_dict mirror). A zero result indicates the architectural regression
# has been re-introduced — see TASK-INV-AB1 review report.
```
