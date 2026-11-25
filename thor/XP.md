# Windows XP shell on the Thor

**Current result (2026-11-24): XP is running on the upper panel, at corrected
120 DPI, with Silver/Metallic Luna. The lower panel is disabled.**

**Overnight update:** Win7 is now the active shell; XP remains available at the
same corrected DPI/style. Win7 → XP → ReactOS → Win7 switches passed after adding
a bounded wait for outgoing session locks. All three force software cursors and
their upper-output screenshots show visible pointers. DP was disconnected, so the
external mouse issue is not yet physically validated. `win4wine-switch win7` and
its application entry are installed. See [WIN7.md](WIN7.md) for the current result.

## Media and isolation

The user supplied the mounted English XP Professional SP3 volume at
`/Volumes/GRTMPVOL_EN/`, identified as
`en_windows_xp_professional_with_service_pack_3_x86_cd_vl_x14-73974.iso`.
The upstream extractor read it through a read-only Docker mount and extracted
176 files. No Microsoft binaries were downloaded, committed, or pushed.

- Assets: `~/win4wine/.local/assets-xp/`
- Separate prefix: `~/win4wine/.local/prefix-xp-standalone/`
- Config: `~/.config/win4wine/xp-standalone.json`
- Logs: `~/.local/state/win4wine-xp/`
- Existing private patched Wine 11.0/Box64 and native labwc are shared as runtimes,
  not as Wine prefixes. ReactOS's prefix and 192-DPI setting remain separate.

The shell is the provided XP `explorer.exe`, renamed to `C:\xp\xp-explorer.exe`.
Its native shell DLLs, Luna, fonts, Bliss and optional shell additions come from
the user's medium. Existing win4wine bridge helpers were reused without rebuilding
or replacing the running ReactOS components.

XP's integration includes folder task panes, tray helpers, Display Properties,
sound schemes, Start menu helpers, and the supplied legacy IE/Media Player components.
This is not a full Windows installation. XP/IE6 are obsolete: use a modern browser
for untrusted sites rather than treating those legacy components as secure.

## Switching

Both entries are registered with SDDM:

- **Windows XP Shell (Standalone)** — `/etc/win4wine/wayland-sessions/armada-xp.desktop`
- **ReactOS Shell (Standalone)** — existing `armada-reactos.desktop`

Application entries **Switch to Windows XP Shell** and **Switch to ReactOS Shell**
are installed in `~/.local/share/applications/` and appear in the Linux programs menu.
The user command is `~/.local/bin/win4wine-switch xp` or
`~/.local/bin/win4wine-switch reactos`.

Switching closes the current desktop/apps. The user command starts an independent
root systemd worker so it survives logout. It uses a temporary SDDM selection and
an eight-minute rollback, accepts the new session after ten seconds of stable
software readiness, and rolls back on startup failure. **Software readiness is
not proof of physical display health.** No permanent autologin/default change is made.

**Upper+DP at 1080p has since worked inside a running Win7 session, and Win7
sessions now enable a hotplugged monitor within those limits (XP and ReactOS do
not); see
[EXTERNAL.md](EXTERNAL.md).** Switching with DP connected is still untested.
XP itself later drove the monitor at 1080p with the lower panel off, using the
manual commands; the user confirmed the picture. Plugging in now moves the
desktop and windows to the monitor; unplugging is not yet reliable.

**Switch from a desktop session, not straight from Gaming Mode.** On 2026-11-24,
just after a reboot, `win4wine-switch xp` from Gaming Mode failed: labwc got
`/dev/dri/card1: Device or resource busy`, and the rollback selected Plasma.
Switching again from Plasma worked. Seen once.

**For now, disconnect DisplayPort before switching or selecting either shell.**
The switch command/worker and both standalone launchers enforce this guard after
the three-output failure below. There is no force/bypass flag.

## Revised display policy

The user explicitly allowed disabling the lower internal panel to simplify setup.
This applies to the win4wine sessions and the recovery desktop, not the boot image
or Steam's configuration.

- `DSI-2`: enabled at 1080x1920/60 Hz, transform 270, scale 1.5.
- `DSI-1`: disabled, including bottom touchscreen events in labwc.
- labwc has `autoEnableOutputs=no`, so it does not briefly allocate all three
  displays before the startup helper runs, nor automatically enable a hotplugged DP output.
- `configure-win4wine-outputs.py` explicitly enables the upper panel and keeps the
  lower one off. If explicitly run with DP connected, it chooses a reported mode
  at or below 1920x1080, never automatically the 4K preferred mode.

**Upper-only XP is physically validated. Upper+DP using this revised conservative
policy is not yet validated.** Do not remove the guard or automatically run the
external configurator until a separate, protected two-output test is authorized.

The revised zero-output-to-explicit-output startup was checked with native GLES2
and a headless XP test before being used on the actual panel. The user confirmed
the upper XP desktop and touch work, with the lower display off.

## Validation completed

- Headless native labwc: genuine XP Explorer desktop/taskbar ownership, Luna,
  Win32 DPI APIs, folder browsing and Log Off ending the test session.
- Live native DRM: XP desktop/taskbar, no Plasma/KWin/Steam shell, XP folder
  browsing and native Konsole integration.
- User confirmed the actual XP UI and touch on the upper panel.
- The user heard XP's startup sound. The headless display test still uses the
  host audio device, so its startup sound can be audible without a physical desktop switch.
- Current Win32 system DPI: 120. Source factory now defaults to 120, rather than 192.
- XP app/session `.desktop` files passed `desktop-file-validate`.

Do not run `test-xp-headless.py` while the live XP prefix is active. Its idle-prefix
guard prevents two desktops sharing a prefix. It derives expected DPI from the
prefix rather than assuming 192.

## DPI/theme issue and fix

The original 192-DPI attempt made labels disproportionate to fixed 32x32 icons.
The user selected 120 DPI, but existing Silver Luna metrics were inconsistent:
at system DPI 120 the API reported caption height 46 and oversized fonts, with
stored `CaptionHeight=36` and `MenuHeight=29` being scaled again.

Screenshots were captured using a private native Fedora `grim` executable, not
Xwayland's root image (which is not a reliable Wayland compositor screenshot).

We reapplied the user's **Metallic / NormalSize** Luna style with the existing
builtin Wine theme helper. That normalized API metrics to caption height 32,
Trebuchet caption font 16 pixels and Tahoma menu font 14 pixels. Existing Explorer
processes still used cached old frame geometry. Settings broadcasts and
`SWP_FRAMECHANGED` alone did not clear that cache.

Restarting XP's Wine processes through the existing supervisor, **without restarting
labwc or changing display hardware**, produced fresh Explorer windows whose
caption buttons fit. The user chose to keep corrected 120 DPI.

For future DPI changes: stop the affected Wine processes, set DPI, let that Wine
server exit, reapply the chosen Luna colour/size through the builtin helper in a
fresh process, then restart XP. Preserve the user's style colour; do not simply
force Blue or reset the entire prefix. The factory script uses separate DPI/theme
steps and normalizes the initial theme before first use.

Current screenshots/measurements are under `~/.local/state/win4wine-xp/`, including
`primary-after-restart.png` and `dpi-metrics-after-restart.txt`. They are not committed.

`NoLowDiskSpaceChecks=1` was set in the XP prefix only: the repeated "Z: low disk
space" balloon referred to Armada's full read-only composefs image, not the roughly
80 GB free in the writable home filesystem. No data was deleted to suppress it.

## Three-output failure and recovery — important

The initial live run enabled both internal panels plus DP at 4K. The upper XP
desktop/touch worked, but the user did not see a diagnostic Explorer folder on
DP even after its Win32/X11 position was verified. **External rendering was not
validated in that XP run.**

The eight-minute timer expired while this was unresolved and selected Armada
Desktop. Plasma loaded an external-only profile with both internal panels disabled.
After attempts to re-enable the panels, kernel logs repeatedly reported:

> `LM_4, invalid DSPP_-1`, `LM_5, invalid DSPP_-1`
>
> `unable to find appropriate mixers`
>
> `failed to reserve hw resources: -119`

KWin's "No XENIX semaphores available" is the strerror for this driver return,
**not evidence of Wine IPC semaphore exhaustion**. The recovery session was running
in software but all screens were black. DPMS wake, disconnecting DP, and a graphics
session restart did not visibly recover it.

The device then **rebooted unexpectedly at 2026-11-23 23:29:38**. The user confirmed
it was not a manual reboot. No system reboot command was issued; SDDM's
`FailureAction` and `StartLimitAction` were `none`. Previous-boot logs end amid
the display-resource errors; the exact reboot cause is unproven. Do not claim
a confirmed kernel panic/watchdog without further evidence.

After reboot the internal recovery desktop became visible. The user then allowed
the lower panel to be disabled. A later black upper screen, associated in time
with another audible headless test, recovered with DPMS wake and a temporary
`kde-inhibit`; no new DPU errors or reboot occurred in that episode. Do not
conflate that power-saving blanking with the earlier hardware failure.

Prior Plasma layouts were backed up before recovery/disable changes:

- `~/.local/state/win4wine-xp/recovery-20261123-232435/kwinoutputconfig.json`
- `~/.local/state/win4wine-xp/before-bottom-disable-20261123-234332/kwinoutputconfig.json`

Boot/mode config hashes were checked unchanged after accepted trials. The current
session was kept, and rollback timers were canceled. XP is an experimental shell;
this work does not establish a robust three-display or mixed-per-monitor-DPI setup.
