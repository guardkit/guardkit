# Feature Input: AutoBuild Instrumentation + Context Reduction

## Feature Name

`autobuild-instrumentation`

## One-liner

Add structured observability to the AutoBuild pipeline and migrate from static always-on markdown context to minimal role-specific digests backed by on-demand Graphiti retrieval — enabling data-driven performance tuning of the GB10 / vLLM / Qwen3-Coder-Next stack.

---

## Background & Motivation

AutoBuild performance on the GB10 (DGX Spark running vLLM with Qwen3-Coder-Next) is heavily affected by **prefill latency** — the time to process input tokens before generation begins. Currently, every AutoBuild task injects a large always-on context bundle (Claude.md + core rules + extended rules) regardless of what is actually needed for that task. This is efficient for frontier models where latency is network-bound, but is a significant bottleneck for local inference where prefill cost is real compute.

At the same time, we now have Graphiti operational as a knowledge graph, which means we can retrieve only the context that is relevant to a specific task rather than injecting everything up front.

This feature delivers two tightly coupled things:

1. **Role-specific minimal digests** — small, stable system prompts (~300–600 tokens) for each agent role (Player, Coach, Resolver, Router), replacing the current large rules bundle in the always-on path.

2. **Structured instrumentation** — an event emission layer that captures what happens at every significant point in an AutoBuild run (LLM calls, Graphiti queries, tool executions, task lifecycle) so we can measure the impact of context changes and tune accordingly.

These are coupled because without instrumentation we are flying blind — we need to measure before and after to validate that digest-only context actually improves throughput without degrading quality.

---

## Goals

- Measure where time and tokens are spent in an AutoBuild run (prefill vs generation vs tooling vs Graphiti retrieval)
- Detect whether static rules bundle is hurting GB10 latency relative to a minimal digest
- Establish a controlled A/B test between prompt profiles: `digest_only`, `digest+graphiti`, `digest+rules_bundle`
- Identify the most common failure categories so we can target improvements
- Enable adaptive wave concurrency by tracking per-wave queue depth, rate limits, and latency trends
- Provide a migration path from the current static-context approach to retrieval-first without breaking existing AutoBuild behaviour

---

## What Is NOT in Scope

- Changes to the Player-Coach adversarial loop logic itself
- New Graphiti schema design (the context loader already exists)
- Dashboard UI (logs and structured events are sufficient for now — dashboards are a follow-on)
- Changes to the Claude Desktop / frontier model side of the pipeline

---

## Core Concepts

### Prompt Profiles

Every LLM call is tagged with a `prompt_profile` that identifies what context was injected:

- `digest_only` — role digest only, no rules bundle, no Graphiti
- `digest+graphiti` — role digest plus retrieved Graphiti context
- `digest+rules_bundle` — role digest plus the current full rules bundle (existing behaviour, used as baseline)
- `digest+graphiti+rules_bundle` — transitional phase during migration

The `prompt_profile` tag is the key to A/B comparisons.

### Role-Specific Digests

Four digests covering the existing AutoBuild roles, each under ~300–600 tokens:

**Player Digest** — implements the task. Rules: minimal changes, no unrelated refactoring, stop and ask if ambiguous, do not claim untested outcomes. Output contract: summary, files changed, how to verify, risks/assumptions.

**Coach Digest** — validates the Player's output against task requirements. Rules: strict comparison against acceptance criteria, categorise failures using the controlled vocabulary, return minimal next action. Output contract: verdict (pass|fail), failure category, issues list, next action.

**Resolver Digest** — root cause analysis for repeated failures. Rules: retrieval-first before guessing, structured remediation plan, identify what context needs persisting back to Graphiti.

**Router Digest** — selects model tier. Rules: smallest capable model, escalate to frontier only for cross-cutting architectural changes, repeated failures, or security-sensitive logic.

### Failure Category Vocabulary

A controlled vocabulary for failure classification (used by Coach and in task lifecycle events):

`knowledge_gap` | `context_missing` | `spec_ambiguity` | `test_failure` | `env_failure` | `dependency_issue` | `rate_limit` | `timeout` | `tool_error` | `other`

This enables dashboard queries like "top 3 reasons AutoBuild loops" and drives targeted remediation.

---

## Event Schema

### Common Fields (all events)

Every event includes: `run_id`, `feature_id`, `task_id`, `agent_role` (player|coach|resolver|router), `attempt` (1..n), `timestamp`

### `llm.call`

Captures every model invocation:

- `provider` (anthropic | openai | local-vllm)
- `model`
- `input_tokens`, `output_tokens`
- `latency_ms` (wall clock)
- `ttft_ms` (time to first token, if available from vLLM)
- `prefix_cache_hit` (boolean, inferred from vLLM response headers where available)
- `context_bytes` (approximate)
- `prompt_profile` (see above)
- `status` (ok | error)
- `error_type` (rate_limited | timeout | tool_error | other)

### `tool.exec`

Captures every shell/tool invocation by the agent:

- `tool_name`
- `cmd` (redact secrets)
- `exit_code`
- `latency_ms`
- `stdout_tail` (truncated), `stderr_tail` (truncated)

### `graphiti.query`

Captures every Graphiti context retrieval:

- `query_type` (context_loader | nearest_neighbours | adr_lookup)
- `items_returned`
- `tokens_injected` (estimated)
- `latency_ms`
- `status`

### `task.started` / `task.completed` / `task.failed`

Lifecycle events including:

- `failure_category` (from controlled vocabulary above)
- `turn_count` (Player + Coach turns combined)
- `diff_stats` (files changed, insertions, deletions)
- `verification_status` (passed | failed | not_run)
- `prompt_profile` (profile used for this task)

### `wave.*`

Per-wave events for adaptive concurrency:

- `wave_id`, `worker_count`
- `queue_depth_start`, `queue_depth_end`
- `tasks_completed`, `task_failures`
- `rate_limit_count`
- `p95_task_latency_ms`

Adaptation policy: if `rate_limit_count > 0` or p95 rises by more than a configurable threshold, reduce concurrency by 50%. If stable for N minutes, increase by +1.

---

## A/B Experiment Design

Run the same representative task set (minimum 10 tasks, ideally from existing AutoBuild eval suite) under two profiles:

**Profile A — Baseline (current behaviour)**
- `digest+rules_bundle` always injected

**Profile B — Minimal**
- `digest_only` or `digest+graphiti` depending on Graphiti availability
- No rules bundle

Collect per-profile: p50/p95 `llm.call.latency_ms`, average `input_tokens`, turns per task, first-attempt success rate, failure category distribution.

---

## Migration Plan

The migration from static context to retrieval-first is phased to avoid breaking existing AutoBuild behaviour:

**Phase 1 — Instrumentation only.** Keep existing context approach. Add digests alongside rules bundle. Tag all calls with `prompt_profile = digest+rules_bundle`. Baseline measurements established.

**Phase 2 — Graphiti retrieval enabled.** Add context loader call at task start. Still include rules bundle. Tag as `digest+graphiti+rules_bundle`. Begin identifying rules that Graphiti makes redundant.

**Phase 3 — Digest + Graphiti default.** Remove rules bundle from default path. Move rules to a tagged "Rules Library" in Graphiti, retrievable by domain tags (e.g. `conventions.testing`, `architecture.nats`, `security.auth`). Tag as `digest+graphiti`. Rules library items retrieved only when relevant Graphiti coverage is low.

**Phase 4 — Targeted recovery.** If `failure_category` is `knowledge_gap` or `spec_ambiguity`, retrieve additional rules slices. Do not reintroduce full bundle unless genuinely necessary.

---

## Rules Library Tagging (for Phase 3+)

Rules in the Graphiti-backed library should be tagged with domain identifiers so they can be retrieved selectively:

- `conventions.naming`, `conventions.testing`
- `pipelines.nats`, `pipelines.faststream`
- `db.migrations`, `security.auth`
- `architecture.player-coach`, `architecture.graphiti`
- `observability.logging`, `observability.tracing`

---

## Acceptance Criteria (high-level, for Gherkin generation)

- Given an AutoBuild run completes, all `llm.call` events should be emitted with non-null `input_tokens`, `output_tokens`, `latency_ms`, and `prompt_profile`
- Given a task fails, a `task.failed` event should be emitted with a valid `failure_category` from the controlled vocabulary
- Given a Graphiti context retrieval occurs, a `graphiti.query` event should be emitted with `tokens_injected` estimated
- Given the same task is run under `digest+rules_bundle` and `digest+graphiti` profiles, the instrumentation data should allow calculating p50 latency difference and input token reduction
- Given the Player Digest is in use, the system prompt injected for the player role should be under 700 tokens
- Given a wave experiences a rate limit event, `rate_limit_count` on the `wave.*` event should increment and concurrency should adapt
- Given a task completes under `digest_only` or `digest+graphiti`, the Coach should still correctly classify the output (no regression in verification quality)

---

## Key Files / Areas of the Codebase to Consider

- Wherever the prompt is assembled before an LLM call (the "prompt assembly" point) — this is where `prompt_profile` tagging happens and where digest selection logic lives
- The LLM client wrapper / any centralised model call point — this is where `llm.call` events are emitted
- The task runner / AutoBuild orchestrator — where `task.*` lifecycle events are emitted
- The Graphiti context loader — where `graphiti.query` events are emitted
- Wave/concurrency management — where `wave.*` events are emitted and adaptive policy is applied
- `.guardkit/` digests directory (new) — home for the four role-specific digest files

---

## Notes for Spec Generation

- Stack is Python (FastStream/NATS, FastAPI, Graphiti)
- Events should be emitted as structured JSON over NATS (consistent with existing event bus architecture) and/or written to a local structured log file for offline analysis
- Do not assume a specific observability backend (no OpenTelemetry dependency required at this stage — structured log files are sufficient)
- The digests themselves are static markdown/text files, not code — they are prompt engineering artefacts
- Prefix cache hit detection on vLLM may be approximate — emit what is available from the API response, flag as `estimated` if not directly provided