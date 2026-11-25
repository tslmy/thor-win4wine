# External monitor in a running shell

**2026-11-24, Win7, Dell U3223QE on DP-1 at 1920x1080/60 Hz, plus the upper
panel.** The lower panel stays off. No display-driver errors were logged.
The user saw the monitor come on; the final desktop layout was checked by
compositor screenshots. ReactOS was not tried.

**Later that evening, XP:** switched from Win7 with the monitor unplugged, then
replugged. Manual `on` and `desktop external` worked with no windows open and no
display-driver errors, and the user confirmed XP on the monitor. The secondary
handheld showed plain white. Automatic switching was then enabled for XP; see
below. Observed for minutes only.

## Why a monitor gets no signal

Sessions start with `autoEnableOutputs=no` and enable outputs once, at startup,
when DisplayPort must be unplugged. A monitor connected afterwards is detected
(`/sys/class/drm/card1-DP-1/status`) but left disabled.

## Automatic switching

**Windows 7 and XP.** The ReactOS session does not start it, and `watch` exits if
run there: ReactOS has never driven a monitor this way. Run `desktop handheld`
before unplugging in ReactOS if you used the manual commands.

Each Win7 or XP session starts `win4wine-external watch`, which follows the DP-1
connector (a state counts after three one-second readings). Its log is
`external-watch.txt` in the session's state directory.

- **Plug in:** runs `on`. Then it moves the desktop to the monitor, restarting
  the shell, only if no Windows window is open. A window counts unless its Win32
  class is the desktop, taskbar or Start menu; unknown classes count. A program with no window at all is not detected
  and would be closed by the restart. Otherwise the desktop stays put.
- **Unplug:** makes the handheld primary again, without restarting anything.
- A failure is not retried until the cable changes again. Automatic restarts are
  at least 150 s apart, because the supervisor gives up after three in 120 s.
- `off` by hand lasts until the next replug.

Tested on Win7: unplug returned a normal desktop to the handheld; replug enabled
the monitor and kept the desktop on the handheld while a window was open; with
no window open, the watcher moved the desktop to the monitor and restarted the
shell (compositor screenshots, no driver errors). That last run was triggered by
restarting the watcher with the monitor connected, not by the cable. A session
that starts the watcher itself is still untested: on 2026-11-24 it was started
by hand with `systemd-run --user` in the running session.

Tested on XP with the real cable, user confirming: unplug returned the desktop and
open windows to the handheld; replug enabled the monitor and kept the desktop on
the handheld while windows were open; replug with none open moved the desktop to
the monitor. No kernel display errors. As on Win7, the watcher was started by
hand in the running session; **starting from a fresh session is untested.**

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
restarts the shell, which fixed it. The finished command has since run end to end
through the watcher.

## The Reconfigure / Exit menu (fixed)

Clicking an area no Windows window covers, such as the second screen, opened
labwc's own menu, where Exit ends the session. The shipped `menu.xml` defines an
empty `root-menu`, and labwc 0.8.3 fills an empty root menu with those two items
(`init_rootmenu` in `src/menu/menu.c`). `labwc-rc.xml` now unbinds all three
mouse buttons on the bare background. Verified with synthetic clicks on DP-1:
the menu appeared before and not after. A running session picks the file up on
`SIGHUP` to labwc.

## Known problems

- **XP shell restarted on an unplug, once.** The desktop was already on the
  handheld and no windows were open, so the watcher did nothing; `xp-shell.log`
  shows `X Error: BadWindow (X_UnmapWindow)` and the supervisor restarted the
  shell. Cause unknown, not reproduced on purpose. Open windows would have been
  lost. An earlier XP unplug with the desktop on the monitor did not do this.
  The supervisor falls back after three shell exits in two minutes, and the
  watcher's restart spacing counts only its own restarts.
- The compositor log shows bursts of `connector DP-1: Atomic commit failed:
  Device or resource busy` during XP use. No visible effect was reported; not
  investigated.
- A Control Panel window dragged to the secondary screen stayed there with its
  caption buttons off the right edge. Cause not investigated.

## Not verified

- With the desktop on the monitor, the secondary handheld showed wallpaper over
  only about two thirds of its width.
- `desktop handheld` after the fix, monitor audio, suspend/resume, long-run
  stability, 4K (still excluded; see [XP.md](XP.md)).
