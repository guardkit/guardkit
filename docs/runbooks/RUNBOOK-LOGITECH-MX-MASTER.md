# RUNBOOK — Logitech MX Master 3S side-button remap (logiops/logid)

**Scope.** Configure the MX Master 3S thumb/gesture button (CID `0xc3`) to open
the GNOME Activities overview (Mission-Control style) on Ubuntu 24.04 GB10-class
boxes, and make it survive reboots. Covers a from-scratch install via `apt`,
the `logid` device config, and the durable systemd override that fixes the
post-reboot Bluetooth race.

**Status.** ✅ Verified on `spark-fcf6` (Ubuntu 24.04.4, MX Master 3S over
Bluetooth), 2026-06-24. Supersedes the from-source build captured in
[`logitech_gb10.md`](../../logitech_gb10.md) — Ubuntu 24.04 ships `logiops`
(0.3.3) in `apt`, so no source build is needed.

**Machine assumptions.**
- Ubuntu 24.04 (`apt` candidate `logiops 0.3.3-2build2`).
- MX Master 3S paired and connected (Bluetooth or Unifying receiver).
- `bluetooth.service` active.

**Device facts (the two things that trip this up).**
- Device **name must match exactly** what `logid` reports: `MX Master 3S`.
- Gesture/thumb button **CID is `0xc3`**.

---

## 0. (Optional) Passwordless sudo for unattended runs

Every step below needs `sudo`. For a hands-off / agent-driven run, grant
passwordless sudo **once per box** (technique from the dgx-spark runbooks). Skip
this section entirely if you're happy to type your password at each `sudo`.

```bash
echo "$USER ALL=(ALL) NOPASSWD:ALL" | sudo tee /etc/sudoers.d/90-mx-master >/dev/null
sudo chmod 0440 /etc/sudoers.d/90-mx-master
sudo visudo -cf /etc/sudoers.d/90-mx-master      # must print "parsed OK"
```

**Revoke when done** (recommended for anything but a dedicated dev box):

```bash
sudo rm /etc/sudoers.d/90-mx-master
```

---

## 1. Pre-flight — confirm the box is a candidate

```bash
. /etc/os-release && echo "$PRETTY_NAME"          # expect: Ubuntu 24.04.x LTS
apt-cache policy logiops | head -3                # Candidate: 0.3.3-2build2
systemctl is-active bluetooth                     # expect: active

# Find the MAC, then check it is CONNECTED — not merely paired.
MAC=$(bluetoothctl devices | awk '/MX Master/{print $2; exit}')
bluetoothctl info "$MAC" | grep -i Connected      # expect: Connected: yes
ls /dev/hidraw* 2>/dev/null || echo "NO HIDRAW — mouse not connected"
```

**Pass:** OS + candidate as annotated, `Connected: yes`, **and at least one
`/dev/hidraw*` node exists.** logid binds the mouse through `hidraw`; if no
hidraw node exists there is nothing for it to bind.

**Fail modes:**
- `logiops` has no candidate → box isn't 24.04; fall back to the from-source
  build in `logitech_gb10.md`.
- `Connected: no` / `NO HIDRAW` → the mouse is **paired but not connected**
  (powered off, asleep, out of range, or — on an Easy-Switch mouse — currently
  switched to a *different* host). The whole stack below installs fine without
  the mouse present, but it can't *bind* until the mouse connects. Fix the
  physical connection first (see §6.5), then continue.

---

## 2. Install logiops

```bash
sudo apt-get update
sudo apt-get install -y logiops
```

This provides the `logid` binary **and** the `logid.service` systemd unit. The
unit is installed disabled with no config — sections 3–5 supply both.

---

## 3. Write the device config — `/etc/logid.cfg`

Maps the gesture button (CID `0xc3`) to `KEY_LEFTMETA`, which GNOME binds to the
Activities overview.

```bash
sudo tee /etc/logid.cfg > /dev/null <<'EOF'
// logiops config — MX Master 3S thumb button -> GNOME Activities overview
// Device name MUST match what `logid` reports exactly.
devices: (
{
    name: "MX Master 3S";

    buttons: (
        {
            // CID 0xc3 = the gesture/thumb button.
            cid: 0xc3;
            action = {
                type: "Keypress";
                keys: ["KEY_LEFTMETA"];   // opens GNOME Activities overview
            };
        }
    );
}
);
EOF
```

> **Tuning later.** SmartShift, DPI, and other button maps can be added inside
> the same `devices:` block. Keep this runbook's version minimal — it's the
> proven, known-good baseline.

---

## 4. Durable systemd override — fix the reboot race

> **Why this is mandatory, not optional.** `logid` scans `hidraw` early, retries
> 5× for the mouse, then gives up and keeps running **half-bound** — so the
> button is dead after a reboot and `Restart=on-failure` never fires (logid
> didn't fail, it half-succeeded). The fix is to delay `logid` until Bluetooth
> has settled. (Full root-cause history in `logitech_gb10.md` §"Durable fix".)

```bash
sudo mkdir -p /etc/systemd/system/logid.service.d
sudo tee /etc/systemd/system/logid.service.d/override.conf > /dev/null <<'EOF'
[Unit]
After=bluetooth.service systemd-user-sessions.service
Wants=bluetooth.service

[Service]
ExecStartPre=/bin/sleep 10
Restart=always
RestartSec=5
EOF
```

- `ExecStartPre=/bin/sleep 10` — the actual fix; gives Bluetooth/USB 10s to
  settle before logid scans `hidraw`.
- `After=` + `Wants=bluetooth.service` — belt-and-braces ordering.
- `Restart=always` — if logid ever exits, it comes back (`on-failure` was
  insufficient — see the box above).

---

## 5. Enable, reload, start

```bash
sudo systemctl daemon-reload
sudo systemctl enable logid
sudo systemctl restart logid
sleep 13 && journalctl -u logid --no-pager -n 10
```

**Pass:** the journal shows the device bound on the first try, e.g.:

```
logid[...]: [INFO] Device found: MX Master 3S on /dev/hidrawN:255
```

Then press the thumb button — the Activities overview should open.

**Confirm it survives reboots:**

```bash
systemctl is-enabled logid                        # expect: enabled
```

### 5.1 Verify the scroll wheel (it works out of the box)

The MX Master 3S wheel is a **high-resolution** wheel — it emits
`REL_WHEEL_HI_RES` events, which X11/libinput and Wayland both handle natively.
logid does **not** touch scrolling, so once the mouse is connected the wheel
just works; no config is needed.

To prove events are flowing, capture to a file (don't rely on live terminal
output — if you run this through a non-streaming wrapper you may scroll outside
the capture window and wrongly conclude the wheel is dead):

```bash
EV=event8   # the MX Master 3S evdev node — confirm via /proc/bus/input/devices
sudo timeout 12 evtest /dev/input/$EV > /tmp/wheel.log 2>&1   # scroll during these 12s
grep -cE '^Event: time.*REL_WHEEL' /tmp/wheel.log            # > 0 means the wheel works
```

If the count is `0`, the mouse almost certainly wasn't connected during the
window (see §6.5) — not a wheel fault.

---

## 6. Troubleshooting — side button dead after a reboot

1. Inspect the journal:
   ```bash
   journalctl -u logid --no-pager -n 20
   ```
   Look for `Failed to add device /dev/hidrawN after 5 tries`.
2. **Quick fix** (the mouse is awake by now, so it binds):
   ```bash
   sudo systemctl restart logid
   ```
3. **If it keeps happening**, bump the settle delay in the override from `10` →
   `15` or `20`:
   ```bash
   sudo sed -i 's#/bin/sleep 10#/bin/sleep 20#' /etc/systemd/system/logid.service.d/override.conf
   sudo systemctl daemon-reload && sudo systemctl restart logid
   ```
4. **Wrong device name** symptom: journal finds the keyboard but never the
   mouse, and no retries for `MX Master 3S`. Confirm the exact reported name and
   make `/etc/logid.cfg`'s `name:` match it verbatim.

### 6.5 No `/dev/hidraw*` at all — mouse paired but not connected

If `ls /dev/hidraw*` returns nothing and `bluetoothctl info <MAC>` shows
`Connected: no`, logid has nothing to bind. The software stack is fine; the
mouse just isn't connected to *this* box right now. This is common on a
headless/remote GB10/spark box where the mouse lives on a desk paired to
another host.

1. **Power the mouse on** (switch on the underside).
2. **Press the Easy-Switch button** on the underside to select the channel
   paired with this box (cycle 1/2/3 until the LED settles on this host's
   channel). An MX Master 3S pairs up to 3 hosts — only one is active at a time.
3. Bring it into Bluetooth range of this box.
4. Confirm it landed:
   ```bash
   MAC=$(bluetoothctl devices | awk '/MX Master/{print $2; exit}')
   bluetoothctl connect "$MAC"          # or just wake the mouse; it auto-connects
   bluetoothctl info "$MAC" | grep -i Connected   # expect: Connected: yes
   ls /dev/hidraw*                                 # expect: at least one node
   ```
5. Now bind it:
   ```bash
   sudo systemctl restart logid
   ```
   Press the thumb button — the Activities overview should open.

> A remote `bluetoothctl connect` **cannot** wake a mouse that is off, out of
> range, or switched to another Easy-Switch channel — those need physical
> action at the mouse.

---

## 7. Teardown

```bash
sudo systemctl disable --now logid
sudo rm -f /etc/logid.cfg
sudo rm -rf /etc/systemd/system/logid.service.d
sudo systemctl daemon-reload
sudo apt-get remove -y logiops          # optional
```

---

## See also

- [`logitech_gb10.md`](../../logitech_gb10.md) — original chat log + from-source
  build history and the durable-fix root-cause analysis.
- [`RUNBOOK-INFRA-ORCHESTRATION.md`](RUNBOOK-INFRA-ORCHESTRATION.md) — GB10
  infrastructure-tier runbook (sibling format).
