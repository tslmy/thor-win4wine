# External monitor in a running shell

Laptop style, in the Windows 7, XP and ReactOS sessions: plug in, and the monitor becomes
the primary screen. The desktop, taskbar and open windows move to it, and the
upper panel becomes the second screen. Unplug, and they come back. Nothing is
restarted. Measured on 2026-11-24 with a Dell U3223QE on DP-1 at 1920x1080/60 Hz,
and on 2026-11-25 with XREAL One Pro glasses in ReactOS. Since 2026-11-25 the lower
panel stays on as well, and the Dell runs at 3840x2160/60 Hz
([three outputs](#three-outputs-2026-11-25)).

## How it works

Sessions start labwc with `autoEnableOutputs=no`, so by itself a monitor
connected later stays disabled. That was deliberate, after the three-output
failure in [XP.md](XP.md). [kanshi](https://sr.ht/~emersion/kanshi/), started by
the Win7, XP and ReactOS startup scripts, applies [`kanshi-config`](kanshi-config) when
the set of connected outputs changes. It logs to `kanshi.txt` in the session's
state directory.

- **docked:** the Dell at 3840x2160/60 Hz, scale 1, at layout x=0; the upper
  panel to its right, the lower panel centred beneath the upper one.
- **glasses:** XREAL One Pro (`Nreal XREAL One Pro*`: they report no serial) at
  1920x1080/60 Hz, x=0; the panels as in `docked`.
- **handheld:** the upper panel at x=0, the lower panel centred beneath it.
- Only listed monitors match. Any other display matches no profile and stays off.
  To add one, copy the `docked` profile with its `make model *` description
  (`wlr-randr` prints it) and mind the risks below.
- The Win7, XP and ReactOS shell settings have **no `primary`**, so Windows' primary screen
  is the leftmost one. The upper panel and a 1080p monitor are both 1920x1080 in
  pixels, so Windows has nothing to rearrange. At 4K it does, and the shells do not:
  see [three outputs](#three-outputs-2026-11-25).

ReactOS used to pin `primary` to DSI-2 and start no kanshi, so a display plugged in
later stayed off. An existing ReactOS install keeps `"primary"` in
`~/.config/win4wine/reactos-standalone.json` until it is removed by hand.

kanshi is not in Armada's image. `containers/native.Dockerfile` installs it, and
the native build packs it with libscfg, vali and aml into
`~/.local/share/win4wine/kanshi/`.

Disconnect DisplayPort before switching shells or logging in again: the launchers
still refuse to start with it connected. That guard now stands for the kernel reset
in [Hard resets around DisplayPort](#hard-resets-around-displayport-cause-found-2026-11-25):
a switch restarts SDDM, and the fbdev console then enables DP while the glasses
re-assert hot-plug. Keep it until Armada's kernel carries the fix. Switch from a desktop session, not from
Gaming Mode: from Gaming Mode, SDDM showed its greeter instead of the trial
autologin, and the switch rolled back after three minutes (2026-11-25).

Nothing switches the monitor off on display-driver errors.

## Tested

- XP, real cable: three dock/undock cycles, user confirming windows moved and
  clicks worked.
- Win7, in a fresh session that started kanshi itself: two cycles, user
  confirming the same.
- In both: no shell restart, no X, display-resource or USB-C errors. Short runs.
- ReactOS with XREAL One Pro, fresh session: one plug-in and one unplug. The
  user confirmed the desktop and taskbar on the glasses; the shell did not restart
  and the kernel logged no DPU or PHY errors.
- 2026-11-25, ReactOS with both panels: the user confirmed both panels, a window
  dragged to the lower panel, and touch. The Dell at 4K over a 2-lane link: no
  picture (see [three outputs](#three-outputs-2026-11-25)). With 4 lanes: all three
  outputs on, and again after an unplug and replug.
- 2026-11-25, ReactOS with both panels, glasses plugged in: the first link training
  failed (`-110`), the glasses dropped hot-plug a second later, and the SoC reset
  ([the DP bug](#hard-resets-around-displayport-cause-found-2026-11-25)). The glasses
  with both panels are therefore untested in labwc.
- Not tried: three outputs in XP or Win7, the glasses in XP or Win7 since the
  profile was added, monitor audio, suspend/resume, long-run stability, a fresh
  install from the updated build recipe (the packaging step was run on its own and
  kanshi's libraries resolved).

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

## XREAL One Pro glasses

They work in ReactOS through the `glasses` profile above, and in Plasma with the
setting below. Hard reboots with them connected come from a DP driver bug, described in
[Hard resets around DisplayPort](#hard-resets-around-displayport-cause-found-2026-11-25),
so end a session with them unplugged.

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
ends at the preceding Dell removal, with no panic and empty pstore. It most likely
hit the DP bug below, but that log was lost.

Logs on the device, under `~/.local/state/win4wine-xp/`: `xreal-crash-20261124/`
and `xreal-plasma-2233/`.

**Cause in Plasma (2026-11-25).** A KWin bug, explained in
[three outputs](#three-outputs-2026-11-25). Setting the external display to **Prefer
color accuracy** (`"colorPowerTradeoff": "PreferAccuracy"` in
`~/.config/kwinoutputconfig.json`) avoids it for that display. Details are in a
[comment on armada#943](https://github.com/armada-os/armada/issues/943#issuecomment-7182038303).

## Three outputs (2026-11-25)

**Hardware budget.** SM8550's DPU has six layer mixers (LM_0–5, paired 0/1, 2/3,
4/5) and four colour blocks (DSPP_0–3, wired to LM_0–3). The kernel gives a CRTC one
DSPP per mixer when it has a `CTM` or `GAMMA_LUT` (`dpu_crtc_get_topology`). Mixers
per output: the upper panel 2 (two DSC encoders), the lower panel 1, DP 2. DP gets
two for any mode wider than 1080 pixels, so 1080p and 4K cost the same. That is five
of six mixers, so three outputs fit. Hardware colour for all three does not: the panels
need 3 DSPPs, DP 2 more, and there are 4. One output has to do its colour in a shader.

**labwc (Win7, XP, ReactOS).** labwc sets no `CTM` or `GAMMA_LUT`, so the DSPPs never
come into it. Measured in ReactOS: both panels on with touch, then the Dell plugged in.
The kernel put the upper panel on LM_0/1, the lower on LM_2 and DP on LM_4/5, and all
three showed a picture at 3840x2160/60 Hz.

**4K needs four DP lanes.** The Thor's device tree has no `link-frequencies` on its DP
output, so the kernel caps the link at HBR2 (5.4 Gbit/s a lane). The Dell's USB-C
port, at its default "High Data Speed" setting, keeps USB 3 and gives DP two lanes:
8.64 Gbit/s of data, while 3840x2160/60 Hz at 8 bits a colour needs 12.8. The kernel
still offered and chose that mode, dropped to 18 bits a pixel, and the Dell showed no
picture. The panels went black too (cursor only) until the Dell was unplugged. With the
Dell's *USB-C Prioritization* set to **High Resolution** (four lanes, USB 2 data), the
link runs at 4 x HBR2 and 4K works at 30 bits a pixel. Two HBR3 lanes would carry
12.96 Gbit/s; the Odin 3 got HBR3 that way in armada#858, and the Thor needs the same
device-tree line (drafted, not submitted, untested). Until then, a monitor on a 2-lane
link needs a mode of at most about 8.6 Gbit/s, such as 2560x1440/60 Hz.

**The shells do not follow a larger primary screen.** Win7, XP and ReactOS size their
desktop and taskbar from the primary screen at login. With the Dell at 4K, X11 reports
DP-1 as a 3840x2160 primary, but the desktop stays 1920x1080 in its top-left corner,
at scale 1 and at scale 2 alike. Windows can still be moved to the rest of the screen.
The Dell profile uses scale 1 so that the screen is native 4K for windows.

**Plasma.** The failure in armada#943 is a KWin 6.8.2 bug, reproduced with
`drm.debug=0x112`. `DrmOutput::tryKmsColorOffloading()` tests an output's hardware
colour pipeline on that output's own, against the current kernel state. When a hotplug
re-enables the lower panel and DP in one modeset, DP's test still sees the lower
panel's DSPP mixer free and passes. The combined commit then gives that mixer to the
lower panel first, DP's request for a DSPP pair fails (`[CRTC:263:crtc-2] atomic
driver check failed: -119`), and `DrmGpu::doModeset()` retries it on every frame
("Modeset failed: No XENIX semaphores available"). With all three outputs already on,
switching DP to "Prefer efficiency" worked: the test failed and KWin fell back to
shader colour. Only the modeset path breaks. A KWin patch, [`kwin-patches/`](kwin-patches/README.md), tests the colour pipeline
against all outputs while a modeset is pending, so the fallback is taken.

Tested on the device with the Dell at 4K and DP on "Prefer efficiency": disable DP and
the lower panel, then enable both in one `kscreen-doctor` call. Stock KWin: 60 "Modeset
failed" in 8 s, and neither output came back. Patched KWin: four runs, no failure, all
three outputs on, DP on LM_4/5 with shader colour and both panels keeping their DSPPs.
A physical unplug and replug of the Dell also worked, and Plasma starts with all three
outputs. The patched library is installed for the user, not in the image (see
`kwin-patches/README.md`); it falls back to the image KWin after an update. Without it,
set external displays to *Prefer color accuracy*. The glasses' entry still has that
setting: they were not tested with the patch, because their flaky link training risks
the DP reset below.

Upstream, `drm/msm/dpu: try reserving the DSPP-less LM first` (42f62cd79578) was
reverted (9f593419eb42) after blue screens on X1E80100. drm/msm issue 102 explains
why: since GAMMA_LUT support, a colour change reallocates all of a CRTC's blocks
without a modeset. The Thor does not need that patch once KWin falls back correctly.

## Hard resets around DisplayPort (cause found, 2026-11-25)

**Cause.** A DP disable that follows a failed DP link training resets the SoC.
`msm_dp_bridge_atomic_enable()` gives up on a failed training with the link clocks
off. The next `msm_dp_bridge_atomic_disable()` still writes `PUSH_IDLE` to the link
registers, an unclocked access. The machine resets with no oops and no panic, and
pstore stays empty. Upstream fixed this in v7.3 with e249a6e2a130 ("drm/msm/dp: skip
PUSH_IDLE when the link was never enabled"), first reported on Snapdragon X2 Elite.
It carries no stable tag. Armada's kernel is 7.2.6 and does not include it.

**Why the glasses hit it.** About a second after losing a signal, the XREAL One
Pro drop hot-plug and re-assert it. An enable that lands in that window fails
training with `-6`, and the next disable resets. Session changes do this
on their own. During an SDDM restart, nothing holds the display, so the kernel's
fbdev console (`msmdrmfb`) enables DP, at 640x480 because it misses the modes. It
also lights the lower panel. This happens just as the glasses re-assert. That
fits all three earlier reboots: a DSI-1 disable during a DP modeset loop, an
unplug with an SDDM restart, and a plug-in after a Dell removal. Those logs were
lost, though, so the fit is not proven.

**Evidence.** Reproduced twice, on the same step both times, in Plasma with the
glasses connected and the lower panel off:

```sh
kscreen-doctor output.DP-1.disable; sleep 0.96
kscreen-doctor output.DP-1.enable;  sleep 0.2
kscreen-doctor output.DP-1.disable
```

The streamed log ends with `link training #1 on phy 0 failed. ret=-6`, `Failed
link training (rc=-104)`, DPU frame-done and vblank timeouts, then the unplug
handler. After each reset the bootloader reported `PM: Reset by PSHOLD` / `Reset
Type: Hard Reset`, as it did for the unexplained reboot before. That is a reset
the SoC itself requested, not a PMIC fault. These survived, each tried once:
`wlr-randr --output DP-1 --off` with the glasses plugged in, unplugging with DP on
in ReactOS, an SDDM restart with DP on, and unplugging and plugging in under the
fbdev console with SDDM stopped. Sixteen plain off/on cycles in Plasma also
survived.

**Until Armada carries the fix:** don't toggle DP off and on within a few
seconds. Unplug before restarting SDDM or switching sessions (the win4wine
launchers already require it). If an output just failed to come up, unplug
instead of disabling it. Reported with a backport as
[armada#953](https://github.com/armada-os/armada/issues/953). The backport is a one-line gate in
`msm_dp_bridge_atomic_disable()`.

**Capture.** [`capture-reset.sh`](capture-reset.sh) streams `dmesg`, the
journal and a one-second heartbeat over SSH into `.build/reset-capture/`. It sets
`drm.debug=0x100` (DP messages) until the next boot.
`capture-reset.sh reason` prints the bootloader's reset cause after a reboot.
It reads the XBL log at `0x81a00000` (`xbl-dt-log-merged-region`) through
`/dev/mem`. On Armada without image changes there is nothing better: no
`/dev/watchdog`, no ramoops region, no netconsole, no lockup detectors and
`kernel.panic=0`. The journal on disk loses the last ~40 s before a reset, so
stream it.

## Other findings

- **Reconfigure / Exit menu (fixed).** Clicking an uncovered area opened labwc's
  own menu, where Exit ends the session: labwc 0.8.3 fills an empty `root-menu`
  with those items. `labwc-rc.xml` now unbinds the buttons on the bare background.
- The secondary screen shows no wallpaper of its own (black or white).
- Bursts of `connector DP-1: Atomic commit failed: Device or resource busy` in
  the compositor log; no visible effect reported, not investigated.
