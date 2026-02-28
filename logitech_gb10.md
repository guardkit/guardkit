Get the service running on startup (already enabled) and you're done. Just to confirm it survives a reboot:


sudo systemctl is-enabled logid
Should say enabled. That's it — side button now opens the Activities overview like Mission Control on macOS, and it'll work every time you log in.

yes it says enabled thanks
You're welcome! To summarise what we ended up with:

Built logiops from source
Device name: "MX Master 3S"
Button CID: 0xc3 (the gesture/thumb button)
Action: KEY_LEFTMETA → opens GNOME Activities overview
The CID 0xc3 turned out to be the correct one, and the device name had to match exactly what logid reports — the two things that were tripping us up.


I can see the problem. The journal shows that before the reboot, logid was successfully finding the MX Master 3S on hidraw2. But after this boot (the -- Boot line), it found the keyboard but failed to add the mouse device on hidraw2.

This is a race condition — after reboot, logid starts before the mouse has fully connected via Bluetooth/USB receiver. It tried 5 times and gave up.

The simplest fix is to restart the logid service now that the mouse is connected. Run this in your terminal:


sudo systemctl restart logid
Then check the logs:


journalctl -u logid --no-pager -n 5
You should see Device found: MX Master 3S and the side button should work again.

To prevent this on future reboots, you can add a restart delay so logid waits for Bluetooth devices to connect. Run:


sudo systemctl edit logid
And add these lines in the editor that opens:


[Service]
RestartSec=5
Restart=on-failure
This tells systemd to automatically retry if logid fails to find the device, with a 5-second delay between attempts. Save and close, then run sudo systemctl daemon-reload.

where in the file do we add these lines?
When you run sudo systemctl edit logid, it opens a new blank file (an override file at /etc/systemd/system/logid.service.d/override.conf). You're not editing the original service file — this is a drop-in override.

Just paste the entire block as the only content in that file:


[Service]
RestartSec=5
Restart=on-failure
Save and close. That's all that should be in the file.

But first — restart the service now to get your button working immediately:


sudo systemctl restart logid
ok when I choose the write out option the File Name to Write :<86f looks incorrect
That's the nano editor showing the default path. It looks wrong because it's showing a truncated path. Press Ctrl+C to cancel out of that, then exit nano with Ctrl+X and say N to not save.

Instead, let's do it manually which is cleaner. Run these commands one at a time:


sudo mkdir -p /etc/systemd/system/logid.service.d

echo '[Service]
RestartSec=5
Restart=on-failure' | sudo tee /etc/systemd/system/logid.service.d/override.conf

sudo systemctl daemon-reload

sudo systemctl restart logid
That creates the override file directly, reloads systemd, and restarts logid. Your mouse button should start working right away.






ANTHROPIC_BASE_URL=http://localhost:8000 ANTHROPIC_API_KEY=vllm-local guardkit autobuild task TASK-GLI-004 --verbose


ANTHROPIC_BASE_URL=http://localhost:8000 ANTHROPIC_API_KEY=vllm-local guardkit autobuild feature FEAT-EC3C --verbose

[R]evise - lets really dig deeper to understand the root cause of the issue - we have had these features building on the macbook. Also we have had to work hard to get this working so we need to ensure we understand the full picture and don't unwitingly undo the architecture. Please use C4 diagramming to fully understand the sequence of flow and trace what is happening in order to understand how to fix the issues