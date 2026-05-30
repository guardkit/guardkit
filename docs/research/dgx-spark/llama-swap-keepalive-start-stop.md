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

## When to pause it — exclusive coder builds (`qwen-coder-next` or `qwen3-coder-30b`)

`qwen-coder-next` (vLLM/FP8) and `qwen3-coder-30b` are **exclusive**
models (sets `coder_next` / `coder_30b`): loading either evicts the other
llama.cpp models (all but `granite-docling`). While one is loaded for a
build, the keep-alive timer's next probe would revive `qwen36-workhorse`
and — via llama-swap's `matrix.sets` — **evict the coder mid-build** (the
~111 GB workhorse↔coder ping-pong). So pause it first (example uses
coder-next; `--model autobuild-coder` for coder-30b):

```bash
# Before a coder-next build
sudo systemctl stop llama-swap-keepalive.timer

# ... run: guardkit autobuild task TASK-XXX --model qwen-coder-next ...

# After the build (swap back to the family, then resume keep-alive)
curl -sS http://localhost:9000/unload
sudo systemctl start llama-swap-keepalive.timer
```

See [`AUTOBUILD-ON-LLAMA-SWAP-findings.md`](./AUTOBUILD-ON-LLAMA-SWAP-findings.md)
§9.2 for the full coder-next smoke test and rationale.
