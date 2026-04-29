---
id: TASK-OPS-9F2A
title: Tune Graphiti chunked-extraction concurrency to avoid llama-swap 429 throttling
status: completed
task_type: feature
created: 2026-04-29T07:35:00Z
updated: 2026-04-29T08:35:00Z
completed: 2026-04-29T08:35:00Z
completed_location: tasks/completed/2026-04/
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
  status: passing
  coverage: null
  last_run: 2026-04-29T08:30:00Z
  notes: |
    71 config tests pass. 55 add-context tests pass. 1 pre-existing unrelated
    failure in test_add_episode_group_specific_timeouts (240/360 timeout drift
    from TASK-REV-2266) — verified failing on main without these changes.
follow_ups:
  - description: |
      Re-run `add-context` against production llama-swap on a 20 KB doc to
      confirm zero "Rate limit" log lines and bounded wall-time. Requires
      GB10 server access — the only acceptance criterion not closeable in code.
    blocked_by: production-server-access
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

## Implementation (2026-04-29)

Picked option 2 (client-side semaphore via config) layered on the
existing implicit option 1 (kept llama-swap `concurrencyLimit: 4` for
`qwen-graphiti`; client now matches it instead of overshooting at 5).

### Code changes

- [guardkit/knowledge/config.py](guardkit/knowledge/config.py)
  — add `chunk_extraction_concurrency: int = 5` to `GraphitiSettings`,
  load from YAML, `CHUNK_EXTRACTION_CONCURRENCY` env override, validate
  range 1-20.
- [guardkit/cli/graphiti.py](guardkit/cli/graphiti.py)
  — `_cmd_add_context` now reads
  `settings.chunk_extraction_concurrency` and uses it for
  `SEMAPHORE_LIMIT` instead of the hardcoded `"5"`. `load_graphiti_config()`
  is called *before* graphiti-core imports (it only touches PyYAML).
- [.guardkit/graphiti.yaml](.guardkit/graphiti.yaml)
  — set `chunk_extraction_concurrency: 4` to match the production
  llama-swap `qwen-graphiti` `concurrencyLimit: 4`. Inline doc explains
  the two-layer agreement and how to tune.
- [docs/research/dgx-spark/RUNBOOK-v3-production-deployment.md](docs/research/dgx-spark/RUNBOOK-v3-production-deployment.md)
  — Phase 5.2 `qwen-graphiti` block now has a tuning-notes header
  explaining `concurrencyLimit` semantics, the client-server two-layer
  agreement, and the `-np` ↔ `concurrencyLimit` ↔
  `chunk_extraction_concurrency` capacity chain.

### Test changes

- [tests/knowledge/test_config.py](tests/knowledge/test_config.py)
  — added 5 unit tests: default value (5), custom value, below-range
  rejection (0 → ValueError), above-range rejection (21 → ValueError),
  bool-as-int rejection. Plus YAML-load and env-var-override tests.
- [tests/unit/cli/commands/test_graphiti_add_context.py](tests/unit/cli/commands/test_graphiti_add_context.py)
  — updated `test_semaphore_limit_set_before_initialize` to mock
  `load_graphiti_config` so the assertion is independent of the
  project's `.guardkit/graphiti.yaml`. Added
  `test_semaphore_limit_reads_from_config` proving the env var
  reflects `chunk_extraction_concurrency`.

### Acceptance criteria status

- [x] Issue reproduced (during the TASK-RUN-D6F4 validation that
      surfaced this — 8 rate-limit hits, 37 retries on a 20 KB doc).
- [x] Chosen option implemented — client-side semaphore made
      configurable via `.guardkit/graphiti.yaml`.
- [ ] Re-run validation against production llama-swap to confirm zero
      "Rate limit" log lines on the same 20 KB doc. **REQUIRES
      PRODUCTION SERVER ACCESS** — open this once GB10 is reachable.
- [x] Semaphore configurable via `.guardkit/graphiti.yaml` (not
      hardcoded). Confirmed by `test_semaphore_limit_reads_from_config`.
- [x] RUNBOOK Phase 5.2 commentary updated.

### Tuning guidance left in code

The two layers must agree:
- Server: `concurrencyLimit` in `/opt/llama-swap/config/config.yaml`
  for `qwen-graphiti`.
- Client: `chunk_extraction_concurrency` in `.guardkit/graphiti.yaml`.

Set the client equal to or just below the server limit. Both are
bounded above by the on-server `-np N` (parallel slot count).
Increasing throughput meaningfully = bump `-np` AND
`concurrencyLimit` AND `chunk_extraction_concurrency` together,
re-checking VRAM headroom (each extra slot ≈ 1-2 GB KV cache for
Qwen2.5-14B Q8).
