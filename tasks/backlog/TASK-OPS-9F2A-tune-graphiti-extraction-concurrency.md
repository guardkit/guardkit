---
id: TASK-OPS-9F2A
title: Tune Graphiti chunked-extraction concurrency to avoid llama-swap 429 throttling
status: backlog
task_type: feature
created: 2026-04-29T07:35:00Z
updated: 2026-04-29T07:35:00Z
priority: medium
tags: [graphiti, llama-swap, concurrency, throughput, ops, dgx-spark]
complexity: 4
parent_validation: TASK-RUN-D6F4
related_docs:
  - docs/research/dgx-spark/VALIDATION-D6F4-gap-fix-results.md
  - docs/research/dgx-spark/RUNBOOK-v3-production-deployment.md
  - .claude/rules/graphiti-knowledge.md
  - .claude/rules/graphiti-knowledge-graph.md
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Tune Graphiti chunked-extraction concurrency to avoid llama-swap 429 throttling

## Description

Surfaced during TASK-RUN-D6F4 post-fix validation on 2026-04-29: when
running `guardkit graphiti add-context <large-doc> --type full_doc`,
graphiti's full_doc parser splits the document into many chunks and
fires their entity-extraction `/v1/chat/completions` requests in
parallel against the `qwen-graphiti` model.

`qwen-graphiti` in `/opt/llama-swap/config/config.yaml` is configured
with `concurrencyLimit: 4`. When parallel chunk requests exceed that,
llama-swap responds with HTTP 429 ("Rate limit exceeded"). The OpenAI
client (and graphiti's own retry wrapper) handle this gracefully with
exponential backoff, so the operation eventually succeeds — but the
log fills with `Retrying request to /chat/completions` lines, total
wall-time is multiples of what it could be, and the user-visible
"Episode creation failed: Rate limit exceeded" warning is alarming
even though it's recovered.

Concrete numbers from the 2026-04-29 validation pass against
`docs/decisions/DECISION-DF-001-...` (~20 KB markdown):

- Connection error count: 0  (Gap #2 fixed — confirmed)
- Rate limit count:       8  (this issue)
- Retrying request count: 37 (this issue)
- Wall time before stopping the test: >300s (still in progress)

This is **not a Gap #2 regression**. The `Connection error` failure
mode from RUNBOOK-v3 RESULTS Gap #2 (Python client pointed at the
wrong port) is gone. This is a *separate*, pre-existing operational
issue — but it was masked previously because the v2 vLLM stack
served Graphiti at a higher concurrency.

## Options

Three handles to pull, listed cheapest first:

1. **Raise `concurrencyLimit` on `qwen-graphiti`** (config-only, no
   code). Current = 4. The model has `-np 2` (parallel slots) so
   on-server concurrency is 2; setting llama-swap's per-model
   concurrencyLimit to match (or just above with a small buffer for
   admin hits) lets clients self-throttle predictably. Or push -np
   higher with a KV-cache cost — Qwen2.5-14B Q8 has 21.3 GB resident,
   each extra parallel slot is ~1-2 GB additional KV cache.
2. **Throttle graphiti chunk dispatch client-side**. The
   `add-context` Python client could limit in-flight chat-completion
   requests to N (e.g., a `Semaphore(4)` around extraction calls).
   This is the right fix architecturally — the *client* should know
   how much its target backend can handle, not rely on retries to
   shape the load.
3. **Increase `--delay` between episodes** (already a CLI flag,
   default 0.5s). This is a sledgehammer and slows down ALL files,
   not just chunked ones.

Recommended: combination of (1) bumped to `concurrencyLimit: 8` +
(2) a `Semaphore(8)` in the graphiti client so the two layers agree.

## Acceptance Criteria

- [ ] Reproduce the issue: pick a large doc that triggers chunking,
      run `add-context` against the production llama-swap, capture
      Retry/RateLimit counts as a baseline.
- [ ] Implement the chosen option(s) — minimum: bump
      `concurrencyLimit` per the analysis.
- [ ] Re-run the same `add-context` call. Target: zero "Rate limit"
      log lines for a 20 KB markdown doc; total wall time bounded
      by `n_chunks × per-chunk-latency / concurrency_limit` to
      within 20%.
- [ ] If client-side semaphore lands: verify the semaphore is
      configurable via `.guardkit/graphiti.yaml` (don't hard-code).
- [ ] Update the runbook's Phase 5.2 config commentary to explain
      what concurrencyLimit does and how to tune it for a chunked
      workload.

## Test Requirements

- [ ] Before/after rate-limit-line count comparison on the same
      input document
- [ ] VRAM check after raising `concurrencyLimit` / `-np`: ensure we
      stay under 100 GB total (we're at 65 GB now, plenty of room,
      but each extra `-np` slot costs KV cache)
- [ ] Re-run TASK-RUN-D6F4-style Gap #2 validation to confirm the
      tuning doesn't introduce a regression in the underlying client
      config

## Notes

- llama-swap returns 429s with HTTP body `18` bytes (a stub) — the
  llama-swap log is more informative than the response.
- The 429 path is preferable to backpressure-via-queueing because it
  fails fast and tells the client to back off rather than holding
  TCP connections open. Raising the limit is fine; relying on
  unbounded server-side queueing is not.
- Watch out for graphiti's own retry policy double-counting:
  `WARNING: Transient FalkorDB error (attempt 2/3)` lines in the
  validation log show the wrapper is retrying the same request that
  the OpenAI client is already retrying. Document the layering so
  future debugging doesn't re-trace this.

## Out of Scope

- llama-server crash recovery — see TASK-OPS-7CB1.
- Per-model concurrency for `qwen36-workhorse` and `gemma4-tutor`.
  Both have `concurrencyLimit: 2` which is appropriate for their
  current usage (single-user agent + single-user tutor). Revisit if
  fleet expands.
