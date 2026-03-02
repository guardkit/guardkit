# GuardKit AutoBuild: Instrumentation + Minimal Always-On Digest (Claude Code)

## Purpose

AutoBuild performance on local inference (GB10 + vLLM) is heavily affected by **prefill** (input-token processing). Large always-on context (Claude.md + rules) can dominate latency, especially when AutoBuild runs **multi-agent (Player/Coach) and multi-iteration loops**.

This document defines:
1) **A minimal always-on Digest** suitable for Claude Code and local coding models.
2) **Instrumentation** to measure where time/tokens go, whether Graphiti retrieval reduces work, and what “rate-limit resilience” looks like in practice.

---

## Part A — Minimal Always-On Digest (for Claude Code / Local Coder)

### Goals for the Digest
- Keep it small: **~300–800 tokens**
- Contain only *global invariants* and *output contracts*
- Avoid large examples, code snippets, and verbose style guides
- Everything else moves to **on-demand retrieval** (Graphiti / file summaries)

### Always-On Digest (copy/paste)

**SYSTEM / DEVELOPER DIGEST**

You are a software engineer working in an AutoBuild workflow. Follow these rules:

1) **Truthfulness and execution**
- Do not claim commands/tests ran unless you actually ran them.
- If you cannot run something, say what you *would* run and why.

2) **Minimise risk**
- Make the smallest change that satisfies the task.
- Do not refactor unrelated code.
- Preserve existing architecture, naming conventions, and patterns unless the task explicitly requires change.

3) **Be explicit about assumptions**
- If requirements are ambiguous, stop and ask or mark the task as blocked with specific questions.
- If you must assume, list assumptions clearly.

4) **Use retrieval instead of bloating context**
- Prefer using provided context + targeted file reads over adding large general guidance.
- Use Graphiti/context retrieval outputs when available; do not request re-sending entire docs.

5) **Output contract**
Return a final report with:
- **Summary** (1–3 bullets)
- **Changes made** (file list + what changed)
- **How to verify** (commands/tests)
- **Notes / risks** (if any)

(End Digest)

### Optional: “Coach Digest” variant (even smaller)
Use this for Coach/Verifier role if you split prompts by role:

- Validate requirements and test outcomes.
- If failing, return:
  - failure category (see Part B)
  - minimal reproduction steps
  - the smallest next action for Player

---

## Part B — Instrumentation Plan (to measure performance + reliability)

### What we want to learn (core questions)
1) **Is the always-on context hurting GB10 latency?**
2) **Where is time spent?** (prefill vs generation vs tool execution)
3) **Does Graphiti reduce turns and token usage?**
4) **What causes failures?** (missing context, test issues, environment, ambiguity)
5) **How should we tune AutoBuild waves?** (concurrency, retries, backoff)

---

## B1 — Event model (the minimum useful schema)

### Required identifiers
Every event should include:
- `run_id` (unique per AutoBuild run)
- `feature_id` (or spec id)
- `task_id` (unique per task)
- `agent_role` (`player` | `coach` | `resolver` | `router`)
- `attempt` (1..n)
- `timestamp`

### Model call event: `llm.call`
Capture at least:
- `provider` (`anthropic` | `openai` | `local-vllm` | etc.)
- `model`
- `endpoint` (optional)
- `input_tokens`
- `output_tokens`
- `latency_ms` (wall clock)
- `ttft_ms` (time to first token, if available)
- `cache_hit` / `prefix_cache_hit` (if you can infer)
- `context_bytes` (or approximate chars)
- `status` (`ok` | `error`)
- `error_type` (`rate_limited` | `timeout` | `tool_error` | `other`)
- `prompt_profile` (`digest_only` | `digest+graphiti` | `digest+rules_bundle`)

> `prompt_profile` is crucial for A/B comparisons.

### Tool execution event: `tool.exec`
- `tool_name` (git, tests, build, etc.)
- `cmd` (redact secrets)
- `exit_code`
- `latency_ms`
- `stdout_tail` / `stderr_tail` (truncated)

### Graphiti retrieval event: `graphiti.query`
- `query_type` (`context_loader` | `nearest_neighbours` | `adr_lookup` | etc.)
- `items_returned`
- `tokens_injected` (estimated)
- `latency_ms`
- `status`

### Task lifecycle events
- `task.started`
- `task.completed`
- `task.failed`
Include:
- `failure_category` (see B2)
- `turn_count` (Player + Coach turns)
- `diff_stats` (files changed, insertions/deletions)
- `verification_status` (`passed` | `failed` | `not_run`)

---

## B2 — Failure categorisation (fast heuristic first)

Use a small controlled vocabulary:

- `knowledge_gap` — missing domain/project knowledge; needs ADR/docs/history
- `context_missing` — needed files not loaded; wrong assumptions about code
- `spec_ambiguity` — acceptance criteria unclear/contradictory
- `test_failure` — tests failing or missing; CI mismatch
- `env_failure` — build tools/SDK missing; local env differs
- `dependency_issue` — external service/library mismatch
- `rate_limit` — 429 / quota / capacity throttling
- `timeout` — request timed out / long generation stalled
- `tool_error` — git, filesystem, command errors
- `other`

This enables dashboards like: “Top 3 reasons AutoBuild loops”.

---

## B3 — The A/B test to answer “is rules bloat hurting GB10?”

### Experiment design
Run the same 10 representative tasks with:

**Profile A — Current**
- Digest + full Claude.md/rules (core/ext) always injected

**Profile B — Minimal**
- Digest only
- + Graphiti retrieval (context loader) if available
- (no rules bundle)

Collect:
- p50 / p95 `llm.call.latency_ms`
- average `input_tokens`
- turns per task
- success rate first attempt

If Profile B improves latency significantly, your current setup is painting a worse picture.

---

## B4 — Wave/concurrency instrumentation (agentic scaling)

AutoBuild “waves” should be **elastic** (adaptive concurrency). You need metrics:

Per wave:
- `wave_id`
- `worker_count`
- `queue_depth_start/end`
- `tasks_completed`
- `task_failures`
- `rate_limit_count`
- `p95_task_latency_ms`

Adaptation policy (starter):
- If `rate_limit_count > 0` or `p95_task_latency_ms` rises > X%, reduce concurrency by 50%
- If stable for N minutes, increase by +1

---

## B5 — Minimal dashboards (even if it’s just logs)

### Dashboard 1: Performance
- latency p50/p95 per model/provider
- input_tokens vs latency scatter
- TTFT trends

### Dashboard 2: Quality/Outcome
- success rate
- turns per task
- failures by category

### Dashboard 3: Graphiti impact
- tasks with Graphiti retrieval vs without:
  - latency
  - turns
  - success rate
  - input_tokens

---

## Part C — Implementation notes (where to wire this in)

### 1) Prompt assembly
Add `prompt_profile` tagging at the point where you build the final prompt:
- `digest_only`
- `digest+graphiti`
- `digest+rules_bundle`

### 2) LLM client wrapper
Centralise all model calls behind one wrapper that:
- measures wall clock
- extracts token usage if available
- records provider/model
- records errors (429/timeout)

### 3) Graphiti context loader
When Graphiti is available:
- emit `graphiti.query`
- estimate tokens injected
- include a short “retrieved context manifest” (IDs/titles only)

### 4) Task runner
Emit task lifecycle events and attach:
- turn_count
- diff stats
- verification results

---

## Part D — Migration plan: from rules bundle to retrieval

### Phase 1: Keep existing rules, add Digest and instrumentation
- Always include Digest
- Keep current rules approach
- Start collecting `prompt_profile = digest+rules_bundle`

### Phase 2: Enable Graphiti retrieval per task
- Add context loader call at task start
- Still keep rules bundle, but begin “rules trimming”
- Collect `prompt_profile = digest+graphiti+rules_bundle`

### Phase 3: Default to Digest + Graphiti
- Remove rules bundle from default path
- Keep a “Rules Library” retrievable by tags
- Collect `prompt_profile = digest+graphiti`

### Phase 4: Optional safety net
- If failure_category is `spec_ambiguity` or `knowledge_gap`, retrieve additional rules slices
- Do not reintroduce full bundle unless truly necessary

---

## Appendix — “Rules Library” tagging suggestion

Store rules as retrievable chunks with tags such as:
- `conventions.naming`
- `conventions.testing`
- `pipelines.azure-devops`
- `db.migrations`
- `security.auth`
- `architecture.yarp`
- `observability.logging`

Graphiti retrieval can then inject only what matters per task.

---