# External monitor in a running shell

**2026-11-24, Win7, Dell U3223QE on DP-1 at 1920x1080/60 Hz, plus the upper
panel.** The lower panel stays off. No display-driver errors were logged.
The user saw the monitor come on; the final desktop layout was checked by
compositor screenshots. XP and ReactOS were not tried.

## Why a monitor gets no signal

Sessions start with `autoEnableOutputs=no` and enable outputs once, at startup,
when DisplayPort must be unplugged. A monitor connected afterwards is detected
(`/sys/class/drm/card1-DP-1/status`) but left disabled.

## Automatic switching

Each standalone session starts `win4wine-external watch`, which follows the DP-1
connector (a state counts after three one-second readings). Its log is
`external-watch.txt` in the session's state directory.

- **Plug in:** runs `on`. Then it moves the desktop to the monitor, restarting
  the shell, only if no Windows window is open. A window counts unless its Win32
  class is the desktop, taskbar or Start menu; unknown classes count, so XP or
  ReactOS may simply never move. A program with no window at all is not detected
  and would be closed by the restart. Otherwise the desktop stays put.
- **Unplug:** makes the handheld primary again, without restarting anything.
- A failure is not retried until the cable changes again. Automatic restarts are
  at least 150 s apart, because the supervisor gives up after three in 120 s.
- `off` by hand lasts until the next replug.

Tested on Win7: unplug returned a normal desktop to the handheld, and replug
enabled the monitor and kept the desktop on the handheld because a window was
open. **The automatic move with no window open has not run on the device**, and
neither has a session that started the watcher itself: on 2026-11-24 it was
started by hand with `systemd-run --user` in the running session.

## Manual use

On the Thor, or over SSH:

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

Disconnect DisplayPort before switching shells or logging in again: the launchers
still refuse to start with it connected.

## Findings

Writing the IPC `primary` file at runtime changed RandR's primary flag but not the
screen positions in Xwayland: it holds the new xdg-output positions until the
output reports a change. The result was wallpaper on one screen, taskbar on the
other. `desktop` nudges each output's position by one pixel and back, then
restarts the shell, which fixed it. The nudge was verified by hand before one
restart; the finished `desktop` command was not rerun end to end afterwards.

## Known problems

- Right-clicking an area no Windows window covers (the secondary screen) opens
  labwc's own menu, **Reconfigure / Exit**. Exit ends the session. The shipped
  `menu.xml` defines an empty `root-menu`, and labwc 0.8.3 fills an empty root
  menu with those two items (`init_rootmenu` in `src/menu/menu.c`). Not fixed.
- A Control Panel window dragged to the secondary screen stayed there with its
  caption buttons off the right edge. Cause not investigated.

## Not verified

- With the desktop on the monitor, the secondary handheld showed wallpaper over
  only about two thirds of its width.
- `desktop handheld` after the fix, monitor audio, suspend/resume, long-run
  stability, 4K (still excluded; see [XP.md](XP.md)).
