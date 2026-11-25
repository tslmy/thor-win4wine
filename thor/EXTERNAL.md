# External monitor in a running shell

Laptop style, in the Windows 7 and XP sessions: plug in, and the monitor becomes
the primary screen. The desktop, taskbar and open windows move to it, and the
upper panel becomes the second screen. Unplug, and they come back. Nothing is
restarted. The lower panel stays off. Measured on 2026-11-24 with a Dell U3223QE
on DP-1 at 1920x1080/60 Hz.

## How it works

Sessions start labwc with `autoEnableOutputs=no`, so by itself a monitor
connected later stays disabled. That was deliberate, after the three-output
failure in [XP.md](XP.md). [kanshi](https://sr.ht/~emersion/kanshi/), started by
the Win7 and XP startup scripts, applies [`kanshi-config`](kanshi-config) when
the set of connected outputs changes. It logs to `kanshi.txt` in the session's
state directory.

- **docked:** the Dell at layout x=0, the upper panel to its right.
- **handheld:** the upper panel at x=0.
- The lower panel is disabled in both; the monitor is held to 1080p.
- Only listed monitors match. Any other display matches no profile and stays off.
  To add one, copy the `docked` profile with its `make model *` description
  (`wlr-randr` prints it) and mind the risks below.
- The Win7 and XP shell settings have **no `primary`**, so Windows' primary screen
  is the leftmost one. Both screens are 1920x1080 in pixels, so Windows sees the
  same geometry either way and has nothing to rearrange.

ReactOS does not start kanshi and keeps `primary`; it has never driven a monitor.

kanshi is not in Armada's image. `containers/native.Dockerfile` installs it, and
the native build packs it with libscfg, vali and aml into
`~/.local/share/win4wine/kanshi/`.

Disconnect DisplayPort before switching shells or logging in again: the launchers
still refuse to start with it connected. Switch from a desktop session, not from
Gaming Mode.

Nothing switches the monitor off on display-driver errors.

## Tested

- XP, real cable: three dock/undock cycles, user confirming windows moved and
  clicks worked.
- Win7, in a fresh session that started kanshi itself: two cycles, user
  confirming the same.
- In both: no shell restart, no X, display-resource or USB-C errors. Short runs.
- Not tried: ReactOS, monitor audio, suspend/resume, long-run stability, 4K
  (still excluded), a fresh install from the updated build recipe (the packaging
  step was run on its own and kanshi's libraries resolved).

## Earlier approach, removed

`win4wine-external`, a script of ours, watched the DP-1 connector and arranged the
screens. It first only rewrote the session's IPC `primary` file and restarted the
shell, on the untested assumption that Explorer could not follow a live change.
It later moved the layout as well, nudging positions by a pixel because Xwayland
had not applied them. With `primary` unset, kanshi needs neither.

## Problems seen with the script, not disproven with kanshi

Two causes of restarts on unplug were found and patched. Both patches remain:

1. **Wine** treated `BadRROutput` (`XRRGetOutputInfo` on a removed output) as
   fatal. Reproduced by `wlr-randr --output DP-1 --off` on the first try.
   [`patches/0002-winex11-tolerate-removed-output.patch`](patches/0002-winex11-tolerate-removed-output.patch)
   ignores `BadRROutput`, `BadRRCrtc` and `BadWindow` from `UnmapWindow`.
2. **win4wine's supervisor** restarted the shell because the taskbar unmaps for
   about 35 ms on removal.
   [`win4wine-patches/0001-supervisor-brief-taskbar-loss.patch`](win4wine-patches/0001-supervisor-brief-taskbar-loss.patch)
   waits two seconds, and writes why it restarts to `supervisor-output.txt`
   (`restarting the shell: ready=… taskbar=… shell exit=… proxy exit=…`).
   `tools/thor.py` applies it to the pinned source.

Originals on the device are in `~/.local/state/win4wine-xp/driver-backup/`. The
Wine build is shared by all three shells.

Unexplained:

- With both patches in, one real-cable test still failed: two plug-ins gave no
  picture after `qcom-qmp-combo-phy: phy init failed --> -110` and USB controller
  errors, and the compositor stopped answering for over 10 s.
- One XP shell restart while docked: `taskbar=False shell exit=15`, no X error.

The supervisor falls back after three shell exits in two minutes.

## XREAL One Pro glasses: do not plug them in

**In stock Plasma**, with no win4wine session or compositor running (Armada
20261109.dfed5d6, kernel 7.2.6), both plug-ins gave "no signal" and froze touch
until after unplugging, when the queued touches arrived together. The kernel
logged, about 29 times a second, `[dpu error]unable to find appropriate mixers`,
`failed to reserve hw resources: -119` and `LM_4/LM_5, invalid DSPP_-1`; KWin
reported `Modeset failed`. Afterwards the driver was still failing with nothing
attached and the upper screen was off until a reboot. These match the first
three-output failure in [XP.md](XP.md). Reported as
[armada#943](https://github.com/armada-os/armada/issues/943). A
[comment on armada#755](https://github.com/armada-os/armada/issues/755) describes
a different XREAL failure, in a driver the Thor does not load.

**Earlier, in XP**, plugging them in was followed by a hard reboot. The journal
ends at the preceding Dell removal, with no panic and empty pstore, so the cause
is not established.

Logs on the device, under `~/.local/state/win4wine-xp/`: `xreal-crash-20261124/`
and `xreal-plasma-2233/`.

## Other findings

- **Reconfigure / Exit menu (fixed).** Clicking an uncovered area opened labwc's
  own menu, where Exit ends the session: labwc 0.8.3 fills an empty `root-menu`
  with those items. `labwc-rc.xml` now unbinds the buttons on the bare background.
- The secondary screen shows no wallpaper of its own (black or white).
- Bursts of `connector DP-1: Atomic commit failed: Device or resource busy` in
  the compositor log; no visible effect reported, not investigated.
