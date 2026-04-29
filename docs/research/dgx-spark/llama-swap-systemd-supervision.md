# llama-swap systemd Supervision (user unit + `-watch-config`)

**Date deployed:** 2026-04-29
**Host:** `promaxgb10-41b1` (Dell DGX Spark GB10)
**Companion to:** [`llama-swap-setup.md`](./llama-swap-setup.md) §6
**Trigger:** the [Gemma 4 tutor template-leak runbook](../../../../agentic-dataset-factory/domains/architect-agent-probe/RUNBOOK-fix-tutor-template-leak.md) revealed two operational gaps while applying a config change. This doc captures the fix.

---

## Why

Two findings from the 2026-04-29 tutor template-leak fix:

1. **`llama-swap` was running un-supervised.** The process was an ad-hoc launch (`llama-swap -config … -listen :9000 &` from a terminal) that survived because it was re-parented to `systemd --user` when the launching terminal closed. `systemctl is-active llama-swap.service` returned `inactive`, and the binary's actual parent was `pid 1 → /usr/lib/systemd/systemd --user`, *not* the documented system unit. Two consequences:
   - **No auto-recovery on llama-swap crash.** TASK-OPS-7CB1's keep-alive timer revives crashed *children* (llama-server instances), but if `llama-swap` itself dies, nothing brings it back. (See `TASK-OPS-7CB1` in `agentic-dataset-factory/tasks/completed/2026-04/`.)
   - **No reboot recovery.** After a reboot, the box does not return to a serving state until someone re-runs the launch by hand.
2. **Config edits required a manual `kill -HUP <llama-swap pid>`.** llama-swap caches its config in memory at startup; killing a model child does NOT cause it to re-read the file. The `-watch-config` flag (introduced upstream and already documented in the binary's `-h`) makes llama-swap watch the config for changes and auto-reload — but it was not enabled on the running process.

A **stale legacy system unit at `/etc/systemd/system/llama-swap.service`** also exists (from an earlier setup pass). It is `enabled` but `inactive`, and is configured `User=root`, which conflicts with the current user-owned `/opt/llama-swap/` tree. On the next reboot it would attempt to start as `root` and race the user unit for port 9000. It needs to be disabled — see "Pending sudo cleanup" below.

## What was deployed

A systemd **user** unit at `/home/richardwoollcott/.config/systemd/user/llama-swap.service`:

```ini
[Unit]
Description=llama-swap (LLM model multiplexer for the GuardKit/dataset-factory fleet)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart=/usr/local/bin/llama-swap \
  -config /opt/llama-swap/config/config.yaml \
  -listen :9000 \
  -watch-config
Restart=on-failure
RestartSec=5
StandardOutput=append:/opt/llama-swap/logs/llama-swap.log
StandardError=append:/opt/llama-swap/logs/llama-swap.log

[Install]
WantedBy=default.target
```

Install + enable steps used (no sudo required for any of these):

```bash
mkdir -p ~/.config/systemd/user
# (write the unit file above)
systemctl --user daemon-reload
systemctl --user enable llama-swap.service
# Switch over from the orphaned process:
ORPHAN_PID=$(pgrep -fx 'llama-swap -config /opt/llama-swap/config/config.yaml -listen :9000')
kill -TERM "$ORPHAN_PID"
# wait until port 9000 is free, then:
systemctl --user start llama-swap.service
```

`on_startup.preload` then brought all four models back up in ~60 s (Graphiti first, then nomic-embed, then workhorse, then tutor).

## Validation (2026-04-29)

| Check | Method | Result |
|---|---|---|
| Unit recognised | `systemctl --user cat llama-swap.service` | PASS |
| Service active | `systemctl --user is-active llama-swap.service` | `active` |
| Service enabled | `systemctl --user is-enabled llama-swap.service` | `enabled` |
| Binary reflects new flags | `ps -o cmd -p $MainPID` shows `-watch-config` | PASS |
| All 4 models preload | poll `/running` until `state=ready` for all 4 | 4/4 ready ~60 s after start |
| Tutor template-leak workaround survives restart | repeat Phase 4.1 of the leak runbook | CLEAN — the custom `--chat-template-file` config change is honoured |
| `-watch-config` actually triggers reload | `touch /opt/llama-swap/config/config.yaml` and `tail` the log | log emits `Configuration Changed` within 1–3 s |

## Pending sudo cleanup (one-shot, requires interactive password)

The legacy stale unit at `/etc/systemd/system/llama-swap.service` is still **enabled**. On the next reboot it will try to start as `User=root`. Run these once:

```bash
# 1) Remove the install symlink so it won't auto-start at boot.
sudo systemctl disable llama-swap.service

# 2) Move the unit file aside.
#    NOTE: do NOT use `systemctl mask` here — mask only works for unit
#    names that don't already have a real file at the target path
#    (mask creates a symlink to /dev/null and refuses to overwrite).
#    Since `/etc/systemd/system/llama-swap.service` is a real file,
#    mask fails with: "File ... already exists." Rename instead.
sudo mv /etc/systemd/system/llama-swap.service \
        /etc/systemd/system/llama-swap.service.legacy-2026-04-29.bak
sudo systemctl daemon-reload

# 3) Allow the user unit to start at boot before login.
#    Without this, the user manager exits when richardwoollcott logs out,
#    so a freshly-rebooted box without an active desktop session won't serve.
sudo loginctl enable-linger richardwoollcott
```

After all three, on the next reboot:

- The `root` system unit no longer exists in systemd's view → never starts.
- `systemd --user@richardwoollcott` will start at boot (lingered).
- The user unit will start llama-swap with `-watch-config`.
- `on_startup.preload` brings all four models up.

To verify post-reboot without rebooting now:

```bash
loginctl show-user richardwoollcott | grep Linger    # expect: Linger=yes
systemctl is-enabled llama-swap.service              # expect: not-found
```

## Operational notes

- **Stop / restart for maintenance:** `systemctl --user stop llama-swap.service` and `systemctl --user start llama-swap.service`. Killing children is *not* equivalent — see Phase 3 of the [tutor template-leak runbook](../../../../agentic-dataset-factory/domains/architect-agent-probe/RUNBOOK-fix-tutor-template-leak.md#phase-3-reload-llama-swap) for why.
- **Config edits no longer need a manual signal.** Edit `/opt/llama-swap/config/config.yaml`, save. llama-swap re-reads within ~1–3 s. Affected children are restarted; unaffected children are left running. Confirm via `tail -f /opt/llama-swap/logs/llama-swap.log` for `Configuration Changed`.
- **Logs:** `/opt/llama-swap/logs/llama-swap.log` (appended by the unit's `StandardOutput`/`StandardError`). The user unit does not also log to `journalctl --user -u llama-swap` because of `StandardOutput=append:`.
- **Relationship to TASK-OPS-7CB1's keep-alive timer:** the keep-alive timer revives crashed *children* (individual `llama-server` processes). This unit supervises the *parent* (`llama-swap` itself). Both are needed; neither makes the other redundant.

## Rollback

If the user unit misbehaves:

```bash
systemctl --user stop llama-swap.service
systemctl --user disable llama-swap.service
# Optional: launch the orphan again as before
nohup llama-swap -config /opt/llama-swap/config/config.yaml -listen :9000 \
  >> /opt/llama-swap/logs/llama-swap.log 2>&1 &
disown
```

The unit file can be removed entirely via `rm ~/.config/systemd/user/llama-swap.service && systemctl --user daemon-reload`.
