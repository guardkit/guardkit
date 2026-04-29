---
id: TASK-OPS-7CB1
title: Investigate overnight llama-server crashes and add auto-respawn policy
status: backlog
task_type: investigation
created: 2026-04-29T07:35:00Z
updated: 2026-04-29T07:35:00Z
priority: medium
tags: [dgx-spark, llama-swap, llama-server, reliability, ops]
complexity: 5
parent_validation: TASK-RUN-D6F4
related_docs:
  - docs/research/dgx-spark/VALIDATION-D6F4-gap-fix-results.md
  - docs/research/dgx-spark/RUNBOOK-v3-production-deployment.md
  - docs/research/dgx-spark/RESULTS-v3-production-deployment.md
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Investigate overnight llama-server crashes and add auto-respawn policy

## Description

Surfaced during TASK-RUN-D6F4 post-fix validation on 2026-04-29: between
the 2026-04-28 production cutover (Runbook v3 Phase 5) and 2026-04-29
~07:13, all four llama-server child processes spawned by llama-swap
exited unexpectedly. The llama-swap parent (PID 4081448, started
2026-04-28 18:22:17) survived; only the four model children died.

The crash was discovered when validating Gap #1 (matrix.sets eviction
fix): only `qwen-graphiti` and `nomic-embed` were running at validation
time, because they had been respawned to serve a `guardkit graphiti
add-context` call that morning. `qwen36-workhorse` and `gemma4-tutor`
remained DOWN until manually triggered.

llama-swap log evidence (`/opt/llama-swap/logs/llama-swap.log`,
lines 93-96):

```
[INFO] <nomic-embed> process exited but not StateStopping, current state: ready
[INFO] <gemma4-tutor> process exited but not StateStopping, current state: ready
[INFO] <qwen36-workhorse> process exited but not StateStopping, current state: ready
[INFO] <qwen-graphiti> process exited but not StateStopping, current state: ready
[INFO] Matrix: model=qwen-graphiti starting (no models running)
```

The "process exited but not StateStopping" pattern is llama-swap's
fingerprint for "child died unexpectedly" (i.e., not via llama-swap's
own stop-model command). Subsequent matrix-driven respawns succeeded.

No kernel OOM events in dmesg; llama-swap parent process was unaffected.
`hooks.on_startup.preload` only runs at llama-swap startup, so dead
children are not auto-revived — they only come back when first
re-requested or, with `matrix.sets`, when llama-swap notices a peer
needs them.

This is **separate from the original Gap #1**. matrix.sets correctly
prevents *request-driven eviction* (validated under 30-round parallel
load — all four PIDs unchanged). What it does not do is auto-revive
crashed children when no traffic is hitting them.

## Investigation Goals

1. Identify the root cause of the four-way crash. Candidates:
   - llama.cpp (b6957 build) segfault under specific request shape
   - GPU driver / CUDA stack reset (NVIDIA driver event log, `dmesg`,
     `journalctl -k`)
   - Coordinated SIGTERM from a host event (logout? sleep? cron?)
   - Memory pressure short of OOM (cgroup limit hit?)
2. Quantify: how often does this happen? Was 2026-04-28→29 the first
   occurrence, or has it been happening every night?
3. Decide on auto-respawn policy:
   - Option A: rely on matrix-driven respawn (current state — only
     resurrects when traffic hits)
   - Option B: add a periodic external health check that `curl`s each
     model's chat/embeddings endpoint every N minutes to keep them warm
   - Option C: file an upstream feature request on `llama-swap` for a
     `restart_on_crash: true` per-model policy
   - Option D: configure systemd watchdog or supervise child PIDs

## Acceptance Criteria

- [ ] Root cause identified (or recorded as "unreproduced after N days
      of monitoring + log capture")
- [ ] Frequency quantified (one-off vs nightly vs per-event)
- [ ] Auto-respawn policy chosen and implemented (matrix-only is fine if
      the analysis shows the crash is rare/benign)
- [ ] Runbook v3 Phase 5.4 updated to mention the failure mode + chosen
      policy, so future readers don't re-discover this
- [ ] If Option B chosen: a small periodic health-check script lives at
      `scripts/llama-swap-keepalive.sh` and is wired into the systemd
      unit (or a separate timer)

## Test Requirements

- [ ] Reproduce or fail-to-reproduce after 7 days of normal traffic +
      monitoring. If reproducible, capture the trigger.
- [ ] If keep-alive script lands: verify dead processes get respawned
      within one polling interval (and that the keep-alive itself does
      not hold concurrencyLimit slots permanently)

## Notes

- llama-swap admin endpoint `GET /running` lists currently-loaded
  models; useful for the keep-alive probe.
- llama-swap admin endpoint `GET /v1/models` lists *configured* models
  regardless of running state.
- The two endpoints together let a keep-alive script compute "configured
  but not running" and trigger a one-shot request to revive each.

## Out of Scope

- Tuning `concurrencyLimit` — see TASK-OPS-9F2A for the throttling
  follow-up surfaced in the same validation pass.
- Reverting from llama-swap to vLLM. Rollback path is documented in
  Runbook v3 Appendix and `scripts/archive-vllm/` if needed, but
  switching back is not the answer to this incident.
