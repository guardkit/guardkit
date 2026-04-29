---
id: TASK-OPS-7CB1
title: Investigate overnight llama-server crashes and add auto-respawn policy
status: completed
task_type: investigation
created: 2026-04-29T07:35:00Z
updated: 2026-04-29T08:15:00Z
completed: 2026-04-29T08:15:00Z
completed_location: tasks/completed/2026-04/
previous_state: in_review
state_transition_reason: "Investigation, decision, implementation, runbook update, and verification complete. 7-day recurrence test deferred to monitoring window — keep-alive timer logs every revive event to journalctl -u llama-swap-keepalive, accumulating data passively."
priority: medium
tags: [dgx-spark, llama-swap, llama-server, reliability, ops]
complexity: 5
parent_validation: TASK-RUN-D6F4
related_docs:
  - docs/research/dgx-spark/VALIDATION-D6F4-gap-fix-results.md
  - docs/research/dgx-spark/RUNBOOK-v3-production-deployment.md
  - docs/research/dgx-spark/RESULTS-v3-production-deployment.md
test_results:
  status: passing
  coverage: null
  last_run: 2026-04-29T08:00:00Z
  notes: "Manual revival test: killed nomic-embed PID 858757; keep-alive detected, revived in 5s, returned exit 0. Concurrency-slot test: 8 parallel requests post-revive all 200 in <40ms (no 429), confirming the warmup probe does not pin a concurrencyLimit slot. Idempotent re-run is a clean no-op."
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

- [x] Root cause identified (or recorded as "unreproduced after N days
      of monitoring + log capture") — *recorded as unproven for the single
      observed event; ruled out kernel/CUDA/OOM/cron/suspend; flagged
      VS-Code-scope hosting as strong contributing factor. See Findings.*
- [x] Frequency quantified (one-off vs nightly vs per-event) — *one event
      in available log history; 7-day quantification deferred to
      keep-alive monitoring window (open below).*
- [x] Auto-respawn policy chosen and implemented (matrix-only is fine if
      the analysis shows the crash is rare/benign) — *Option B (keep-alive
      timer); Option A retained as "what happens if traffic hits first".*
- [x] Runbook v3 Phase 5.4 updated to mention the failure mode + chosen
      policy, so future readers don't re-discover this — *added Phase 5.4
      forward-ref + new Phase 5.6 (install + verify) + Phase 10.2
      hosting warning.*
- [x] If Option B chosen: a small periodic health-check script lives at
      `scripts/llama-swap-keepalive.sh` and is wired into the systemd
      unit (or a separate timer) — *script + .service + .timer all
      shipped in scripts/.*

## Test Requirements

- [ ] Reproduce or fail-to-reproduce after 7 days of normal traffic +
      monitoring. If reproducible, capture the trigger. — *DEFERRED to
      monitoring window: every revive event lands in
      `journalctl -u llama-swap-keepalive` once installed.*
- [x] If keep-alive script lands: verify dead processes get respawned
      within one polling interval (and that the keep-alive itself does
      not hold concurrencyLimit slots permanently) — *PASS: SIGKILL'd
      nomic-embed → revived in 5 s; 8 parallel post-revive requests all
      200 in <40 ms (no 429).*

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

## Findings (2026-04-29)

### Frequency

**One observed event** in the entire `/opt/llama-swap/logs/llama-swap.log`
(file birthed 2026-04-28 18:10, log preserved across the deploy):

```
$ grep -c "process exited but not StateStopping" /opt/llama-swap/logs/llama-swap.log
4   # all four lines from the same single event (lines 93-96)
```

Cannot yet distinguish "one-off" from "nightly" — the log only spans one
overnight window since the 2026-04-28 cutover. The acceptance criterion of
"7 days of monitoring" is left to elapse; once the keep-alive timer is
installed (Phase 5.6), every revive event also lands in
`journalctl -u llama-swap-keepalive`, which gives a recurrence counter for
free.

### Root cause analysis

| Candidate                                      | Status                  | Evidence                                                                                  |
| ---------------------------------------------- | ----------------------- | ----------------------------------------------------------------------------------------- |
| llama.cpp segfault under specific request shape | **Plausible, unproven** | Log gap during which it could have happened. No core dumps configured, no crash trace.    |
| GPU/CUDA/NVRM driver event                     | **Ruled out**           | `journalctl -k --since 2026-04-28T19:00 --until 2026-04-29T07:30` is clean. No NVRM, no `cuda`, no `drm`, no `nvidia` fault. The only NVRM line in journal is at 18:13 (vLLM teardown). |
| Kernel OOM-killer                              | **Ruled out**           | No `Out of memory` / `Killed process` lines in kernel journal during window.              |
| Coordinated SIGTERM (cron / sleep / suspend)   | **Ruled out**           | No crontab references llama-swap or llama-server; no systemd timers either; no `pkill` in user bash history (closed 00:46 with benign `which guardkit-py`); no suspend/resume events. |
| cgroup memory.max                              | **Ruled out**           | `user@1000.service` and `app-org.chromium.Chromium-5777.scope` have no memory limits set. |

**Strong contributing factor uncovered (separate from "what killed them"):**

The production llama-swap stack is **not running under the systemd unit**
that Runbook v3 Phase 10.2 prescribes. The unit `/etc/systemd/system/llama-swap.service`
is `Active: inactive (dead)`; `journalctl -u llama-swap` returns "No entries".

The actually-running llama-swap (PID 4081448) was launched directly from a
VS Code integrated terminal during the 2026-04-28 cutover, and **all four
llama-server children inherit its cgroup**:

```
$ cat /proc/4081448/cgroup
0::/user.slice/user-1000.slice/user@1000.service/app.slice/app-org.chromium.Chromium-5777.scope

$ for pid in 857967 858757 874721 875229; do cat /proc/$pid/cgroup; done
0::/user.slice/user-1000.slice/user@1000.service/app.slice/app-org.chromium.Chromium-5777.scope
0::/user.slice/user-1000.slice/user@1000.service/app.slice/app-org.chromium.Chromium-5777.scope
0::/user.slice/user-1000.slice/user@1000.service/app.slice/app-org.chromium.Chromium-5777.scope
0::/user.slice/user-1000.slice/user@1000.service/app.slice/app-org.chromium.Chromium-5777.scope
```

This places the entire production stack inside VS Code's Chromium scope. VS
Code's swap peak on this scope is 4.1 GB and current memory 31 GB; Chromium
has its own memory-pressure reaping and lifecycle events (window reload,
extension host restart). Children killed by VS Code/Chromium do not show up
in kernel logs, which matches our "no kernel evidence of cause" observation
exactly. Whether or not Chromium is the *specific* killer here, the
arrangement bypasses the `Restart=on-failure` policy of the prepared unit
and gives several plausible kill paths that are invisible to standard
Linux observability.

**Conclusion:** root cause **unproven** for this single event, but the
hosting arrangement is itself a defect that explains why the fault left no
trace and why the children stayed dead. The structural fix is to actually
run llama-swap under the systemd unit (Runbook v3 Phase 10.2). The keep-alive
timer (this task's deliverable) addresses the symptom — children stay dead
until traffic hits — independent of what kills them.

### Decision: Option B (keep-alive timer), with operational guidance

- **Implemented Option B**: `scripts/llama-swap-keepalive.sh` +
  `.service` + `.timer`, installed via Runbook v3 Phase 5.6.
- **Documented in Runbook v3 Phase 10.2** that the production llama-swap
  must be started via `sudo systemctl start llama-swap`, NOT from a VS
  Code terminal — with a verification snippet that reads the cgroup of
  the running PID and warns if it lives under any `chromium` or `app-`
  scope.
- **Did not pursue Option C** (upstream `restart_on_crash` feature
  request). With matrix.sets correctly limiting eviction (TASK-RUN-D6F4
  Gap #1 PASS) and the keep-alive timer running every 5 minutes, dead
  children come back without upstream changes. If the recurrence rate
  during the 7-day monitoring window justifies it, file the upstream
  request as a separate task.
- **Did not pursue Option D** (per-child PID supervision via systemd).
  llama-swap reparents children itself; wedging another supervisor in
  between would race with llama-swap's own state machine.

### Verification (Test Requirements)

- [x] Killed `nomic-embed` (PID 858757) with SIGKILL → keep-alive script
      detected the missing model from `/running` vs `/v1/models` diff,
      revived it via a one-shot `/v1/embeddings` call, returned exit 0
      in 5 s.
- [x] Concurrency-slot regression test: after revive, fired 8 parallel
      `/v1/embeddings` requests against `nomic-embed` — all returned
      `HTTP 200` in `<40 ms`. No 429 throttling, confirming the warmup
      probe does not pin a `concurrencyLimit` slot.
- [x] Idempotent re-run: a second invocation while all 4 are healthy
      reports `All configured models are ready; nothing to revive.` and
      exits 0 with no traffic.
- [ ] **7-day recurrence test**: open. The keep-alive timer is scheduled
      to log every revive event to `journalctl -u llama-swap-keepalive`,
      so the next 7 days will quantify whether the 2026-04-28→29 event
      was a one-off or recurrent. Re-evaluate once that data lands.

### Files added / modified

- `scripts/llama-swap-keepalive.sh` (new) — probe + revive
- `scripts/llama-swap-keepalive.service` (new) — `Type=oneshot` unit
- `scripts/llama-swap-keepalive.timer` (new) — `OnUnitActiveSec=5min`
- `docs/research/dgx-spark/RUNBOOK-v3-production-deployment.md`:
    - Phase 5.4: operational note pointing forward to Phase 5.6
    - Phase 5.6 (new): keep-alive install + verify
    - Phase 10.2: VS-Code-scope hosting warning + cgroup verification
