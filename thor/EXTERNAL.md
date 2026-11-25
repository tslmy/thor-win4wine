# External monitor in a running shell

Laptop style: plug in, and the monitor becomes the primary screen. The desktop,
taskbar and open windows move to it, and the upper panel becomes the second
screen. Unplug, and they come back. Nothing is restarted. The lower panel stays
off. Measured on 2026-11-24 with a Dell U3223QE on DP-1 at 1920x1080/60 Hz.

**Open bug: unplugging can still restart the XP shell and close its windows.**
See [below](#open-bug-unplugging-can-restart-the-shell).

## How it works

Sessions start labwc with `autoEnableOutputs=no` and enable outputs once, so a
monitor connected later is detected but left disabled. That was deliberate,
after the three-output failure in [XP.md](XP.md). win4wine itself does not react
to hotplug.

Each Win7 or XP session therefore starts `win4wine-external watch`, which follows
`/sys/class/drm/card*-DP-1/status` (a state counts after three one-second
readings) and logs to `external-watch.txt` in the session's state directory.
ReactOS does not start it.

- **Plug in:** enables DP-1 at up to 1080p, makes it primary, then watches the
  kernel log for 20 s and switches it off again on display errors.
- **Unplug:** makes the handheld primary again.
- **Making a screen primary** takes two things: writing its name to the session's
  IPC `primary` file, and putting it at layout x=0 with the other to its right.
  Both screens are 1920x1080 in pixels, so Windows sees the same geometry and the
  shell has nothing to rearrange.
- Xwayland holds new positions until an output reports a change, so every output
  is first placed one pixel off, then exactly.

[kanshi](https://sr.ht/~emersion/kanshi/), the usual hotplug tool for such
compositors, was not evaluated. Fedora packages it; it is not on the Thor. It
could replace the detection and layout, not the `primary` file or the error check.

An earlier version only wrote the `primary` file and restarted the shell, on the
untested assumption that Explorer could not follow a live change. That was wrong.

## Manual use

```sh
~/.local/bin/win4wine-external status
```

```sh
~/.local/bin/win4wine-external desktop external
```

`on`, `off` and `desktop handheld` also exist. None restarts anything.

Disconnect DisplayPort before switching shells or logging in again: the launchers
still refuse to start with it connected.

## Tested

- XP, real cable, current version: plug-in moved the desktop and a Notepad window
  to the monitor, and replug moved the desktop and a folder window, both without
  a restart; the user confirmed clicks work. Unplug brought the layout back, but
  see the bug below. No kernel display errors.
- XP session started from Plasma with the monitor detached launched its own
  watcher (previous version of the script, same startup lines).
- Win7: only the previous, restart-based version was tried. **The current
  version has not run on Win7**, and a fresh Win7 session has not been tried.
- Not tried: ReactOS, monitor audio, suspend/resume, long-run stability, 4K
  (still excluded).

## Open bug: unplugging can restart the shell

Removing the monitor removes an X output. A Wine process that later asks about it
gets a fatal `X Error: BadRROutput` (`RRGetOutputInfo`), the supervisor restarts
the shell, and Windows programs are closed. Seen on XP several times, not on
every unplug; once the restart came only at the first click afterwards. Errors
appeared in `xp-shell.log` or `proxy.log`, sometimes with `BadWindow`
(`X_UnmapWindow`) as well. Not seen in the few Win7 unplugs.

`dlls/winex11.drv/xrandr.c` calls `XRRGetOutputInfo` with stored output IDs in
several places without `X11DRV_expect_error`, though the file already uses that
guard for another call. Guarding them is the likely fix; it has not been written
or built, and whether `BadWindow` is a separate problem is unknown.

The supervisor falls back after three shell exits in two minutes.

## Other findings

- **Reconfigure / Exit menu (fixed).** Clicking an uncovered area opened labwc's
  own menu, where Exit ends the session: labwc 0.8.3 fills an empty `root-menu`
  with those items. `labwc-rc.xml` now unbinds the buttons on the bare background.
- The secondary screen shows no wallpaper of its own (black or white).
- Bursts of `connector DP-1: Atomic commit failed: Device or resource busy` in
  the compositor log; no visible effect reported, not investigated.
- A Control Panel window dragged to the second screen once stayed there with its
  caption buttons off the edge. Seen under the earlier layout; not retested.
