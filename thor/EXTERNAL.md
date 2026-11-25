# External monitor in a running shell

Laptop style: plug in, and the monitor becomes the primary screen. The desktop,
taskbar and open windows move to it, and the upper panel becomes the second
screen. Unplug, and they come back. Nothing is restarted. The lower panel stays
off. Measured on 2026-11-24 with a Dell U3223QE on DP-1 at 1920x1080/60 Hz.

**Not reliable yet: unplugging can restart the XP shell and close its windows,
and repeated plugging can fail in the kernel.** See
[below](#open-problems-unplugging-and-the-usb-c-link).

## How it works

Sessions start labwc with `autoEnableOutputs=no` and enable outputs once, so a
monitor connected later is detected but left disabled. That was deliberate,
after the three-output failure in [XP.md](XP.md). win4wine itself does not react
to hotplug.

Each Win7 or XP session therefore starts `win4wine-external watch`, which follows
`/sys/class/drm/card*-DP-1/status` (a state counts after three one-second
readings) and logs to `external-watch.txt` in the session's state directory.
ReactOS does not start it.

- **Plug in:** only for a tested monitor (`TESTED_MONITORS`: the Dell U3223QE;
  others stay off until `win4wine-external on`). Enables DP-1 at up to 1080p, makes it primary, then watches the
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

## Open problems: unplugging and the USB-C link

Two causes of restarts on unplug were found and patched:

1. **Wine** treated `BadRROutput` (`XRRGetOutputInfo` on a removed output) as
   fatal. Reproduced by `wlr-randr --output DP-1 --off` on the first try.
   [`patches/0002-winex11-tolerate-removed-output.patch`](patches/0002-winex11-tolerate-removed-output.patch)
   ignores `BadRROutput`, `BadRRCrtc` and `BadWindow` from `UnmapWindow`. No
   such error appeared in the few removals afterwards.
2. **win4wine's supervisor** restarted the shell because the taskbar unmaps for
   about 35 ms on removal.
   [`win4wine-patches/0001-supervisor-brief-taskbar-loss.patch`](win4wine-patches/0001-supervisor-brief-taskbar-loss.patch)
   waits two seconds. `tools/thor.py` applies it to the pinned source.

Installed on the device 2026-11-24, originals in
`~/.local/state/win4wine-xp/driver-backup/` (`winex11.so.before-removed-output`,
`supervisor.py.before-taskbar-grace`). The Wine build is shared by all three shells.

**The real-cable test afterwards failed, so neither fix is proven:**

- Two of three plug-ins gave no picture. The compositor logged no DP connection
  and `wlr-randr` timed out after 10 s. The kernel had logged
  `qcom-qmp-combo-phy: phy init failed --> -110`, warnings in
  `qmp_combo_typec_switch_set`, and USB controller runtime-PM errors. This is
  below userspace; its cause is unknown. A reboot has not been tried.
- On the one good plug-in, the user reported that mouse and touch did not
  register, and the shell restarted about 7 s after the unplug with no X error
  logged. Cause unknown; the supervisor does not record why it restarts.

**After a reboot, 2026-11-24:** two Dell round trips, which the user reported as
working. The log also shows one shell restart while docked, 36 s after the
second plug-in and before its unplug: `ready=True taskbar=False shell exit=15
proxy exit=None`, with no X error. Cause unknown.

**Hard reset with XREAL One Pro glasses.** The user plugged the Dell in a third
time, removed it (22:24:39), plugged in the glasses, and the whole system
rebooted. The saved journal ends at the Dell removal: nothing about the glasses,
no panic, no shutdown, empty pstore. Whether the watcher had begun enabling them
is unknown, so a userspace trigger is not ruled out, and the new restriction
cannot prevent a crash that happens at plug time. **Do not plug the glasses in
with unsaved work.** Logs: `~/.local/state/win4wine-xp/xreal-crash-20261124/`.

The
supervisor patch also writes why it restarts the shell to
`supervisor-output.txt` (`restarting the shell: ready=… taskbar=… shell exit=…
proxy exit=…`); read it after the next failure.

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
