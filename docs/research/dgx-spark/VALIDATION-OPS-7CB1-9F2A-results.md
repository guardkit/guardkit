# Validation Results: TASK-OPS-7CB1 + TASK-OPS-9F2A

**Validation date:** 2026-04-29
**Validated against:** [`RUNBOOK-v3-production-deployment.md`](RUNBOOK-v3-production-deployment.md) post-9F2A/7CB1 edits
**Source tasks:**
- [`TASK-OPS-7CB1`](../../../tasks/completed/2026-04/TASK-OPS-7CB1-investigate-overnight-llama-server-crashes.md) — keep-alive timer for crashed llama-server children
- [`TASK-OPS-9F2A`](../../../tasks/completed/2026-04/TASK-OPS-9F2A-tune-graphiti-extraction-concurrency.md) — Graphiti chunked-extraction concurrency tuning

**Originating validation:** [`VALIDATION-D6F4-gap-fix-results.md`](VALIDATION-D6F4-gap-fix-results.md)
**Lineage:**
```
RESULTS-v3 (gap analysis 2026-04-28)
  → TASK-RUN-D6F4 (runbook fixes 2026-04-28)
    → VALIDATION-D6F4 (post-fix validation 2026-04-29) ← surfaced these two follow-ups
      → TASK-OPS-7CB1, TASK-OPS-9F2A (operational fixes 2026-04-29)
        → THIS DOC (post-fix validation 2026-04-29)
```

**Host:** `promaxgb10-41b1` (Dell DGX Spark GB10, aarch64)

## Purpose

VALIDATION-D6F4 surfaced two operational findings that were not in
scope of TASK-RUN-D6F4 but warranted their own follow-ups: an overnight
four-way llama-server crash with no auto-revival, and HTTP 429
throttling from Graphiti's chunked-extraction parallelism. Both were
filed as TASK-OPS-7CB1 and TASK-OPS-9F2A respectively. This doc captures
the post-fix validation pass for both.

The deployment was **not** torn down for this validation. Like
VALIDATION-D6F4, the fixes were tested non-destructively against the
running stack. The exception was test 3 of TASK-OPS-7CB1, which
required deliberately killing all four model children to mirror the
original overnight failure mode — recovery completed in 30 seconds.

## Summary

| Task | Test | Result |
|------|------|--------|
| 7CB1 | Static (`bash -n`, `systemd-analyze verify`) | **PASS** |
| 7CB1 | Idempotent run with all 4 alive — no-op | **PASS** |
| 7CB1 | Single-model SIGKILL → keepalive revives in 5s | **PASS** |
| 7CB1 | Four-model SIGKILL → keepalive revives all in 30s | **PASS** |
| 7CB1 | Slot release after revive (8× parallel — none 429) | **PASS** |
| 9F2A | `chunk_extraction_concurrency: 4` in `.guardkit/graphiti.yaml` | **PASS** |
| 9F2A | `SEMAPHORE_LIMIT` env-var wiring in `cli/graphiti.py` | **PASS** |
| 9F2A | Re-run yesterday's 20 KB add-context — Rate limit / retry counts | **PASS** — 0 rate limits, 0 retries, 9/9 chunks complete in 35 min |

## TASK-OPS-7CB1 — Keep-alive timer

### Implementation summary

- New script: `scripts/llama-swap-keepalive.sh` (151 lines, no `jq`
  dep — uses python3 + flock-protected lock file)
- New systemd unit: `scripts/llama-swap-keepalive.service` (oneshot,
  user-scope, journal logging)
- New systemd timer: `scripts/llama-swap-keepalive.timer` (`OnBootSec=2min`,
  `OnUnitActiveSec=5min`, `Persistent=true`)
- Runbook Phase 5.6 added: install + verification recipe
- Runbook Phase 10.2 augmented: VS-Code-Chromium-scope operational
  warning (the actual root cause of the 2026-04-28→29 four-way exit)

### Static checks

```
bash -n scripts/llama-swap-keepalive.sh           → syntax OK
systemd-analyze verify (.service + .timer)        → no warnings on the keepalive units
```

### Dynamic test 1 — idempotent run (all 4 alive)

Pre-flight confirmed all four models alive and `/running` reports
`state=ready` for each. Ran the script:

```
[llama-swap-keepalive] All configured models are ready; nothing to revive.
rc=0, duration=0s
```

**PASS** — script correctly identified no-op condition, exited
immediately.

### Dynamic test 2 — single-model SIGKILL → revive

`SIGKILL`'d nomic-embed (PID 905674), confirmed `/running` showed
`nomic-embed: NOT READY`, ran keep-alive:

```
[llama-swap-keepalive] Reviving: nomic-embed
[llama-swap-keepalive]   nomic-embed: revived (HTTP 200)
rc=0, duration=5s
```

Post-revive nomic-embed PID = 921033 (different from pre-kill 905674,
confirming genuine respawn).

**Slot release verification** — fired 8× parallel embeddings against
the freshly-revived nomic-embed:

```
HTTP codes: 200 200 200 200 200 200 200 200
```

8/8 returned 200; the keep-alive's one-shot probe did not pin a
concurrencyLimit slot. **PASS.**

### Dynamic test 3 — full four-model SIGKILL → recovery

Mirrors the actual 2026-04-28→29 overnight failure mode where all four
children exited simultaneously and llama-swap parent survived.

Pre-kill PIDs: qwen-graphiti=857967, nomic-embed=921104,
qwen36-workhorse=874721, gemma4-tutor=875229.

`SIGKILL` all four:

```
killed qwen-graphiti PID=857967
killed nomic-embed PID=921104
killed qwen36-workhorse PID=874721
killed gemma4-tutor PID=875229
```

`/running` post-kill: `(running list empty)` — exactly the symptom
seen overnight.

Ran keep-alive:

```
[llama-swap-keepalive] Reviving: gemma4-tutor nomic-embed qwen-graphiti qwen36-workhorse
[llama-swap-keepalive]   gemma4-tutor: revived (HTTP 200)
[llama-swap-keepalive]   nomic-embed: revived (HTTP 200)
[llama-swap-keepalive]   qwen-graphiti: revived (HTTP 200)
[llama-swap-keepalive]   qwen36-workhorse: revived (HTTP 200)
rc=0, duration=30s
```

Post-revive:
- qwen-graphiti: 922424 (was 857967 — respawned)
- nomic-embed: 922423 (was 921104 — respawned)
- qwen36-workhorse: 922425 (was 874721 — respawned)
- gemma4-tutor: 922422 (was 875229 — respawned)
- All four `state=ready`
- VRAM: 65.07 GiB (matches runbook's ~65 GB)

**PASS.** Total time from full crash to fully-warmed four-model
deployment: 30 seconds. Cold-start could be longer on a fresh boot
(no OS file-cache warmth on the GGUFs), but the keep-alive's
`REVIVE_TIMEOUT=300s` accommodates a full cold-start.

### Operational note — installation status

**Installed and active on the host as of 2026-04-29 09:38 BST.** Phase 5.6
of the runbook was followed verbatim, the `.timer` unit was enabled with
`--now` (so it both auto-starts on every boot via `WantedBy=timers.target`
and fired immediately).

Installed file inventory:

```
-rwxr-xr-x  /usr/local/bin/llama-swap-keepalive.sh           (root:root, 5261 B)
-rw-r--r--  /etc/systemd/system/llama-swap-keepalive.service (root:root, 772 B)
-rw-r--r--  /etc/systemd/system/llama-swap-keepalive.timer   (root:root, 543 B)
lrwxrwxrwx  /etc/systemd/system/timers.target.wants/llama-swap-keepalive.timer
              → /etc/systemd/system/llama-swap-keepalive.timer
```

Effective `ExecStart` after install-time sed-rewrite:
```
ExecStart=/usr/local/bin/llama-swap-keepalive.sh
```

First-run journal (immediate fire from `enable --now`):

```
Apr 29 09:38:13 promaxgb10-41b1 systemd[1]: Starting llama-swap-keepalive.service...
Apr 29 09:38:13 promaxgb10-41b1 llama-swap-keepalive.sh[1040751]: [llama-swap-keepalive] All configured models are ready; nothing to revive.
Apr 29 09:38:13 promaxgb10-41b1 systemd[1]: llama-swap-keepalive.service: Deactivated successfully.
Apr 29 09:38:13 promaxgb10-41b1 systemd[1]: Finished llama-swap-keepalive.service.
```

Timer schedule confirmed by `systemctl list-timers`:

```
NEXT                           LEFT     LAST                          PASSED  UNIT
Wed 2026-04-29 09:43:13 BST    4min 33s Wed 2026-04-29 09:38:13 BST   26s ago llama-swap-keepalive.timer
```

(5-min interval honoured, matches `OnUnitActiveSec=5min` in the unit.)

Boot/update behaviour confirmed by unit definition:
- `OnBootSec=2min` — timer first-fires 2 min after every boot
- `Persistent=true` — missed runs (suspended host) catch up on resume
- `WantedBy=timers.target` — auto-enabled across daily OS updates and reboots
- `Documentation=` field links the service back to TASK-OPS-7CB1 for
  future operators reading `systemctl status`

### Bonus finding (out of scope but recorded)

During test 3 the timing of llama-swap's response to dead children
hinted that llama-swap may have its own watchdog/proactive-restart
behaviour (a new PID appeared briefly between the kill and the
keep-alive request). This is **not** the auto-revival path — `/running`
remained empty and the children needed the keep-alive's request to
properly load and reach `state=ready`. But it's worth tracing exactly
what llama-swap does on `SIGCHLD` to a model child versus on idle
detection. Not blocking; flagged for future curiosity.

## TASK-OPS-9F2A — Graphiti extraction concurrency

### Implementation summary

- New config field: `chunk_extraction_concurrency: int = 5` (range 1-20)
  in `GuardkitGraphitiConfig` ([guardkit/knowledge/config.py:120-123](../../../guardkit/knowledge/config.py))
- Project value set to `4` in `.guardkit/graphiti.yaml:63` to match
  llama-swap's `qwen-graphiti.concurrencyLimit: 4`
- `cli/graphiti.py` reads the config and sets `SEMAPHORE_LIMIT` env var
  *before* importing graphiti-core (which captures the env var at
  module load time)
- Original env var saved/restored after the call, so other commands
  in the same Python process aren't affected
- 71 config tests + 55 add-context tests pass
- Runbook Phase 5.2 documents the two-layer agreement
  (`server.concurrencyLimit` ↔ `client.chunk_extraction_concurrency`)

### Static checks

`.guardkit/graphiti.yaml` (line 63):
```yaml
chunk_extraction_concurrency: 4
```

`load_graphiti_config()` round-trip:
```
chunk_extraction_concurrency = 4
→ SEMAPHORE_LIMIT will be set to 4
```

### Dynamic test — re-run yesterday's add-context against DECISION-DF-001

Same input doc, same flags, same llama-swap stack as VALIDATION-D6F4.
Yesterday's baseline:

| Metric | Yesterday (D6F4 validation) |
|--------|------------------------------|
| Connection error count | 0 |
| Rate limit count | 8 |
| Retrying request count | 37 |
| Wall time (before timeout) | >300s, still in progress when stopped |

Today's run with `chunk_extraction_concurrency: 4`:

| Metric | Today (9F2A applied) | Δ vs yesterday |
|--------|----------------------|-----------------|
| Connection error count | **0** | (still 0, Gap #2 stable) |
| Rate limit count | **0** | **−8 (eliminated)** |
| Retrying request count | **0** | **−37 (eliminated)** |
| Episode creation failed | **0** | (no failures) |
| Chunks completed | **9 of 9** | full doc completion |
| Wall time | **2093s (≈35 min)** | finished cleanly (yesterday was stopped mid-run) |

The 18,101-byte doc was split into 9 chunks (the v3 chunker's split is
based on token count, not the 8 I assumed earlier). Per-chunk
`add_episode` timings, in seconds:

```
chunk_0: 155s
chunk_1: 315s
chunk_2: 236s
chunk_3: 322s
chunk_4: 371s
chunk_5: 178s
chunk_6:  96s
chunk_7: 214s
chunk_8: 204s
─────────────
total:  2093s ≈ 34.9 min
mean:    232s/chunk (high variance: per-chunk LLM work depends on entity
         density and embedding-cache hit rate)
```

**PASS** — zero throttling events across 35 minutes of continuous LLM
work. Yesterday's test was stopped at ~300s while still on chunk 0/1
because the OpenAI client was retry-thrashing against llama-swap's 429s.
Today's run does the same total LLM work without retry overhead.

Note: graphiti processes chunks of a single document **sequentially**
(one `add_episode` at a time), and `chunk_extraction_concurrency`
parallelizes the LLM calls **within** a single `add_episode` (entity
extraction across the chunk's content). Total wall time is therefore
`sum(per_chunk_latency)`, not divided by concurrency. Raising
concurrency would speed up *individual* chunks if the per-chunk work
benefits from more parallelism, bounded by the underlying
`-np` slot count on `qwen-graphiti` (currently 2). Concurrency:4 with
np:2 is the right place to be — the extra two client slots absorb
brief network hiccups without overwhelming the server.

## Production state summary as of 2026-04-29 ~10:00 BST

Consolidated view of every gap that was found during the live runbook
execution and how it has been verified closed against the running
production deployment.

### Eight gaps total, eight PASS

| # | Gap | Source | Fix | Verification |
|---|-----|--------|-----|--------------|
| D6F4-1 | matrix.sets eviction | RESULTS-v3 §"Runbook gap #1" | Phase 5.2 `matrix.sets all` + `hooks.on_startup.preload` | 30 rounds × 4 models, 0 PID changes |
| D6F4-2 | `.guardkit/graphiti.yaml` not patched | RESULTS-v3 §"Runbook gap #2" | Phase 7.1 sed-block extended | 600s `add-context`, 0 connection errors |
| D6F4-3 | `--config`/`--listen` flag style | RESULTS-v3 §"Runbook gap #3" | Single-dash everywhere | grep audit + live process |
| D6F4-4 | GGUF glob casing | RESULTS-v3 §"Runbook gap #4" | `find -iname` | re-ran Phase 0.1, 8 hits vs 0 |
| D6F4-5 | `pkill -f` self-kill | RESULTS-v3 §"Runbook gap #5" | `pkill -x llama-server` | sandbox + live demonstration of `-f` self-kill |
| D6F4-6 | VRAM ~5 GB above estimate | RESULTS-v3 §"Runbook gap #6" | Phase 5.5 expected total → ~65 GB | nvidia-smi: 65.16 GiB |
| OPS-7CB1 | Crashed children not auto-revived | VALIDATION-D6F4 Finding #1 | Phase 5.6: keep-alive script + 5min timer | 4-model SIGKILL → revived in 30s; timer installed and active |
| OPS-9F2A | Chunked-extraction 429 throttling | VALIDATION-D6F4 Finding #2 | `chunk_extraction_concurrency: 4` (config) | 9-chunk doc: 0/0 vs yesterday's 8/37 |

### Current live state on `promaxgb10-41b1`

**llama-swap and models:**

```
PID 4081448  llama-swap (started 2026-04-28 18:22)
├── PID 922424  qwen-graphiti     21.8 GB  (revived during 7CB1 test, stable since)
├── PID 922423  nomic-embed        1.0 GB
├── PID 922425  qwen36-workhorse  23.8 GB
└── PID 922422  gemma4-tutor      19.1 GB
                                  ─────────
                          Total:  65.07 GiB
```

All four `state=ready` per `GET http://localhost:9000/running`.

**Keep-alive timer:**

```
llama-swap-keepalive.timer  enabled  active (waiting)
  ExecStart= /usr/local/bin/llama-swap-keepalive.sh
  Interval:  every 5 minutes (OnUnitActiveSec=5min)
  Boot fire: 2 min after every boot (OnBootSec=2min, Persistent=true)
  Wants:     timers.target → auto-enabled across daily OS updates and reboots
```

**Graphiti client (`add-context`):**

```
.guardkit/graphiti.yaml:
  llm_base_url:               http://promaxgb10-41b1:9000/v1
  embedding_base_url:         http://promaxgb10-41b1:9000/v1
  chunk_extraction_concurrency: 4   ← matches qwen-graphiti.concurrencyLimit: 4
```

### Open operational considerations

1. **llama-swap parent is in VS Code Chromium scope, not under systemd.**
   The Phase 10.2 systemd unit is `enabled` but currently `inactive`
   because the running parent (PID 4081448) was launched via `nohup`
   from a VS Code terminal during the 2026-04-28 cutover. The
   keep-alive timer covers crashed *children* regardless of where the
   parent lives; a parent crash would still need manual intervention.
   On the next reboot the systemd unit takes over naturally and the
   whole stack lives under `/system.slice/`. Manual migration is a
   ~3-5 min outage if needed sooner; documented in Phase 10.2 of the
   runbook.

2. **7-day recurrence quantification automated via weekly health check.**
   The original 2026-04-28→29 four-way exit has not recurred since the
   keep-alive was installed. Rather than scheduling a one-off remote
   agent (which has no path to host-side `journalctl` / `systemctl`),
   a local weekly health check runs every Monday at 09:00 BST,
   audits the keep-alive's last 7 days of activity (timer fires,
   no-op vs revival splits, failed revivals, fresh crash deltas),
   and writes `/opt/llama-swap/logs/healthcheck-YYYYMMDD.log` plus a
   journal entry tagged `llama-swap-healthcheck.service`. Three-state
   exit code (HEALTHY / ATTENTION / CRITICAL). Install steps are
   captured in [RUNBOOK Phase 5.7](RUNBOOK-v3-production-deployment.md#L580).

   **Installed and active on the host as of 2026-04-29 10:15 BST.** The
   `--now` install fire ran clean:

   ```
   [1] Keep-alive timer state         enabled, active
   [2] Keep-alive runs (last 7d)      total=8, no-op=8, revivals=0, failures=0
                                       (effective window 0d 0h since just installed)
   [3] Revival events                 No revival events.
   [4] Child-process exits            cumulative=10, new since last=0
                                       (state file seeded at install per Phase 5.7)
   [5] Current model state            4/4 ready, VRAM 65.14 GiB

   Summary: HEALTHY (exit 0)
   Next run: Mon 2026-05-04 09:00:00 BST
   ```

   Report file: `/opt/llama-swap/logs/healthcheck-20260429.log` (2361 B).
   The baseline seed step in Phase 5.7 (writing the cumulative crash
   count to `last_exit_count` at install time) means the first
   scheduled run won't replay yesterday's overnight crash + the four
   SIGKILL test events as "new" — the delta is zero.

### Validation chain (full lineage)

```
2026-04-28  RUNBOOK-v3 produced
2026-04-28  Live deployment → RESULTS-v3 captured 6 gaps
2026-04-28  TASK-RUN-D6F4 folded the 6 gaps back into the runbook
2026-04-29  VALIDATION-D6F4 → all 6 PASS, surfaced 2 operational findings
2026-04-29  TASK-OPS-7CB1 (keep-alive) + TASK-OPS-9F2A (concurrency) implemented
2026-04-29  VALIDATION-OPS-7CB1-9F2A (this doc) → both PASS, keep-alive installed
2026-04-29  Weekly health-check timer added (Phase 5.7, runs Mon 09:00) —
            replaces scheduled remote agent (cloud has no path to host)
2026-05-04  First scheduled health-check report — first Mon after install
```

## Cross-References

- **Originating validation:** [`VALIDATION-D6F4-gap-fix-results.md`](VALIDATION-D6F4-gap-fix-results.md)
- **Source tasks:**
  - [`TASK-OPS-7CB1`](../../../tasks/completed/2026-04/TASK-OPS-7CB1-investigate-overnight-llama-server-crashes.md)
  - [`TASK-OPS-9F2A`](../../../tasks/completed/2026-04/TASK-OPS-9F2A-tune-graphiti-extraction-concurrency.md)
- **Updated runbook:** [`RUNBOOK-v3-production-deployment.md`](RUNBOOK-v3-production-deployment.md)
- **Implementation files:**
  - `scripts/llama-swap-keepalive.sh`
  - `scripts/llama-swap-keepalive.service`
  - `scripts/llama-swap-keepalive.timer`
  - `guardkit/knowledge/config.py` (chunk_extraction_concurrency field)
  - `guardkit/cli/graphiti.py` (SEMAPHORE_LIMIT wiring)
  - `.guardkit/graphiti.yaml` (project value: 4)
