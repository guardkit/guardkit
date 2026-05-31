# llama-swap keep-alive timer — start / stop runbook

Quick reference for pausing and resuming the keep-alive timer on
`promaxgb10-41b1`.

## What it is

`llama-swap-keepalive.timer` fires `llama-swap-keepalive.service` **every
5 minutes**. The service runs `/usr/local/bin/llama-swap-keepalive.sh`,
which probes llama-swap's admin endpoint and revives any
configured-but-crashed model child (one observed overnight four-way crash
left workhorse + tutor down until manually re-requested — TASK-OPS-7CB1).

- Units live in `/etc/systemd/system/` → **commands need `sudo`**.
- Repo source of truth: [`scripts/llama-swap-keepalive.sh`](../../../scripts/llama-swap-keepalive.sh),
  [`.service`](../../../scripts/llama-swap-keepalive.service),
  [`.timer`](../../../scripts/llama-swap-keepalive.timer).

## Quick reference

| Goal | Command |
|---|---|
| Check status / next fire | `systemctl status llama-swap-keepalive.timer` |
| | `systemctl list-timers llama-swap-keepalive.timer` |
| **Pause now** (this boot) | `sudo systemctl stop llama-swap-keepalive.timer` |
| **Resume now** | `sudo systemctl start llama-swap-keepalive.timer` |
| Stop an in-flight revive too | `sudo systemctl stop llama-swap-keepalive.service` |
| Disable across reboots | `sudo systemctl disable llama-swap-keepalive.timer` |
| Re-enable across reboots | `sudo systemctl enable llama-swap-keepalive.timer` |
| Enable **and** start now | `sudo systemctl enable --now llama-swap-keepalive.timer` |
| Recent run logs | `journalctl -u llama-swap-keepalive.service -n 50 --no-pager` |
| Follow logs live | `journalctl -u llama-swap-keepalive.service -f` |

## Stop the timer

Halt the 5-minute schedule for the rest of this boot (it will return on
reboot because the unit is still *enabled*):

```bash
sudo systemctl stop llama-swap-keepalive.timer
```

If a revive is already running when you stop the timer (e.g. a cold
start is mid-flight), the in-progress service finishes on its own. To
cut that off too:

```bash
sudo systemctl stop llama-swap-keepalive.service
```

To keep it off across reboots as well, also disable it:

```bash
sudo systemctl disable llama-swap-keepalive.timer
```

## Start the timer

Resume the 5-minute schedule:

```bash
sudo systemctl start llama-swap-keepalive.timer
```

If you previously *disabled* it, re-enable so it survives reboots:

```bash
sudo systemctl enable --now llama-swap-keepalive.timer
```

## Confirm the state

```bash
systemctl is-active  llama-swap-keepalive.timer   # active | inactive
systemctl is-enabled llama-swap-keepalive.timer   # enabled | disabled
systemctl list-timers llama-swap-keepalive.timer  # shows NEXT fire time
```

## When to pause keep-alive — mutually-exclusive workloads

Three matrix sets evict at least part of the always-on family:
`coder_30b`, `tutor`, and `lpa`. While any of them is loaded, the
keep-alive timer's 5-min probe of `qwen-graphiti` / `nomic-embed` /
`qwen36-workhorse` / `architect-agent` would trigger the solver to
switch back to the `all` set — **evicting the on-demand model
mid-session**. Pause the timer for any session likely to exceed 5
minutes between requests.

The general pattern is:

```bash
# Before the long session
sudo systemctl stop llama-swap-keepalive.timer

# ... run your workload ...

# After the session — pick ONE of:
#   (a) just resume the timer; the family will revive on next probe
sudo systemctl start llama-swap-keepalive.timer
#   (b) immediately reset memory before resuming (recommended after big VLM loads)
curl -sS http://localhost:9000/unload
sudo systemctl start llama-swap-keepalive.timer
```

Per-workload specifics below.

### `coder_30b` — opt-in autobuild coder (`qwen3-coder-30b`)

Loading `autobuild-coder` evicts every other llama.cpp model in `all`
(qg, ne, qw, aa, dl) — coder-30b runs alone at ~22 GB. The 5-min revive
probe for `qwen-graphiti` would otherwise swap the coder out mid-build
(the ~111 GB workhorse↔coder ping-pong documented in
[`AUTOBUILD-ON-LLAMA-SWAP-findings.md`](./AUTOBUILD-ON-LLAMA-SWAP-findings.md)
§9.2 / §9.4).

```bash
sudo systemctl stop llama-swap-keepalive.timer
# ... guardkit autobuild task TASK-XXX --model autobuild-coder ...
curl -sS http://localhost:9000/unload
sudo systemctl start llama-swap-keepalive.timer
```

> Historical: `qwen-coder-next` (vLLM/FP8) was an even larger exclusive
> coder (~92 GB resident) that had the same constraint. It was removed
> from the live config 2026-05-30 (see §9.9) after the forum AgentBench
> review showed `qwen36-workhorse` outperforms it on agent tasks. The
> launch script + HF cache are preserved for zero-download restoration.

### `tutor` — study tutor session (`gemma4-tutor`)

Loading `study-tutor` (or any of its aliases: `gcse-tutor`,
`gemma4-specialist`) switches to the `tutor` set (`gt & qw`), evicting
`qwen-graphiti`, `nomic-embed`, `architect-agent`, and `granite-docling`.
Tutor sessions are usually short interactive turns; the 5-min keep-alive
probe is unlikely to fire between messages. **Only pause for long
sessions** (>5 min between user messages).

```bash
# Optional — only if the session will have long gaps between turns
sudo systemctl stop llama-swap-keepalive.timer
# ... interactive tutor session ...
sudo systemctl start llama-swap-keepalive.timer
```

If the tutor gets evicted mid-session, the next user message reloads it
in ~8 s (warm cache cold start). Recoverable, but disruptive.

See [`AUTOBUILD-ON-LLAMA-SWAP-findings.md`](./AUTOBUILD-ON-LLAMA-SWAP-findings.md)
§9.9 for the tutor matrix-set design.

### `lpa` / `lpa_v3` — LPA POC page→markdown extraction

Two vision models are registered for the LPA POC workload — pick which
via `DOCLING_VLM_MODEL` env var on the POC side:

| Model | Set | Resident | Notes |
|---|---|---:|---|
| `granite-vision-4-1-4b` (aliases: `granite-vision-4.1-4b`, `granite-vision`) | `lpa` | ~26 GB | Granite4Vision arch; EOS-collapse pattern on Ashworth Section 2 — kept for comparison |
| `granite-vision-3-3-2b` (alias: `granite-vision-3.3-2b`) | `lpa_v3` | ~15 GB | LlavaNext arch; current LPA-POC default; leaner |

Loading either switches to its respective set, evicting `qwen-graphiti`,
`architect-agent`, and `granite-docling`. **The two LPA sets are also
mutually exclusive with each other** — requesting one vision model
evicts the other if loaded. Both are vLLM-served with a 30-min idle ttl.

**Pause the timer before any LPA batch that will run longer than ~5
minutes** — otherwise the 5-min `qg` probe will switch back to `all`
and evict the vision model mid-batch (cold reload: ~110 s for 4.1-4b,
~110 s warm / ~6 min first-ever for 3.3-2b including the 6 GB download).

```bash
sudo systemctl stop llama-swap-keepalive.timer
# ... LPA extraction batch (Ashworth + Fairfax + Pengelly etc.) ...
# When done, EITHER let it auto-unload on the 30-min ttl, OR force-unload now:
curl -sS http://localhost:9000/unload
sudo systemctl start llama-swap-keepalive.timer
```

For ad-hoc single-page tests (one POST, sub-minute), pausing the timer
isn't strictly necessary — but is good hygiene if there's any chance of
follow-up requests.

To **switch which vision model is in use** mid-session, just POST to the
other model id; llama-swap will evict the current one and load the
other (cold load). To **clear the prefix cache** of either model
without changing the set, force a container restart:
`docker stop vllm-granite-vision` (4.1-4b) or
`docker stop vllm-granite-vision-3-3-2b` (3.3-2b). `--rm` cleans up;
the next POST triggers a fresh container with empty caches.

See [`AUTOBUILD-ON-LLAMA-SWAP-findings.md`](./AUTOBUILD-ON-LLAMA-SWAP-findings.md)
§9.10 / §9.11 (4.1-4b setup history) and §9.12 (3.3-2b fallback + memory
math) for the full setup details, vLLM image rationale, and matrix-set
design.
