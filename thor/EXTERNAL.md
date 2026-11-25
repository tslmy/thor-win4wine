# External monitor in a running shell

**2026-11-24, Win7, Dell U3223QE on DP-1 at 1920x1080/60 Hz, plus the upper
panel.** The lower panel stays off. No display-driver errors were logged.
The user saw the monitor come on; the final desktop layout was checked by
compositor screenshots. XP and ReactOS were not tried.

## Why a monitor gets no signal

Sessions start with `autoEnableOutputs=no` and enable outputs once, at startup,
when DisplayPort must be unplugged. A monitor connected afterwards is detected
(`/sys/class/drm/card1-DP-1/status`) but left disabled.

## Use

On the Thor, or over SSH, after plugging the monitor in:

```sh
~/.local/bin/win4wine-external on
```

```sh
~/.local/bin/win4wine-external desktop external
```

- `on` picks the largest mode up to 1080p, watches the kernel log for 20 s and
  switches DP-1 off again on display errors. It refuses if the lower panel is on.
- Without `desktop external`, the monitor is blank extended space: the shell
  draws its desktop and taskbar on the primary screen only.
- `desktop external` / `desktop handheld` **restarts the shell and closes its
  Windows programs.** The session itself continues.
- Before unplugging: `desktop handheld`, then `off`. `off` refuses while the
  desktop is on the monitor.
- `status` lists the outputs.

Run `on` again after each replug or new session; nothing watches for hotplug.
Disconnect DisplayPort before switching shells or logging in again: the launchers
still refuse to start with it connected.

## Findings

Writing the IPC `primary` file at runtime changed RandR's primary flag but not the
screen positions in Xwayland: it holds the new xdg-output positions until the
output reports a change. The result was wallpaper on one screen, taskbar on the
other. `desktop` nudges each output's position by one pixel and back, then
restarts the shell, which fixed it. The nudge was verified by hand before one
restart; the finished `desktop` command was not rerun end to end afterwards.

## Not verified

- With the desktop on the monitor, the secondary handheld showed wallpaper over
  only about two thirds of its width.
- Unplugging while the desktop is on the monitor. If the layout looks wrong
  afterwards, run `desktop handheld`.
- `desktop handheld` after the fix, monitor audio, suspend/resume, long-run
  stability, 4K (still excluded; see [XP.md](XP.md)).
