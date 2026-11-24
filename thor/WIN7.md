# Windows 7 shell on the Thor

**2026-11-24: installed and running as the sole desktop shell on the upper panel,
at 120 DPI. Windows 7 Basic works; full Aero glass/effects are not implemented.**

## Installation and isolation

The supplied English Windows 7 SP1 x64 ISO, also mounted at
`/Volumes/GRMCULXFRER_EN_DVD/`, was read through a read-only Docker mount.
Upstream `extract/win7.py` selected Professional and extracted 141 files.
Microsoft media, extracted assets and screenshots stay in ignored `.build/`
or on the Thor, never in Git.

- Assets: `~/win4wine/.local/assets-win7/`
- Prefix: `~/win4wine/.local/prefix-win7-standalone/`
- Config: `~/.config/win4wine/win7-standalone.json`
- Logs/screenshots: `~/.local/state/win4wine-win7/`
- Session: `/etc/win4wine/wayland-sessions/armada-win7.desktop`
- Launcher: `~/.local/bin/win7-standalone-session`
- Startup: `~/.local/share/win4wine/tools/win7-standalone-start`

The existing private Wine 11.0/Box64 and ARM64 labwc runtime are reused.
XP retains Silver/Metallic Luna at 120 DPI; ReactOS retains its separate
192-DPI prefix. Neither prefix was replaced. The factory refuses existing
prefix/config paths and runs Wine setup on a private native Xvfb.

An earlier interrupted source transfer had truncated remote `prefix/win7.py`
at 38912 bytes. Its hash exactly matched that prefix of the clean local upstream
file. The partial file was backed up in the Win7 state directory before restoring
the complete 39436-byte upstream file. No nested-repository source change was made.

## Switching and safety

Use the Linux programs menu's **Switch to Windows 7 Shell**, or on the Thor:

```sh
~/.local/bin/win4wine-switch win7
```

`xp` and `reactos` remain supported by the same command. Switching closes the
current desktop/apps, uses a temporary SDDM selection and an independent
eight-minute rollback timer, then accepts after stable software readiness.
The permanent Gaming Mode boot/default configuration remains unchanged.

**Disconnect DisplayPort before switching.** All three launchers preserve that
guard. DSI-1 and its touch device stay disabled; DSI-2 is 1080x1920/60 Hz,
transform 270, scale 1.5. Startup enables approved outputs explicitly instead
of briefly allocating all outputs. Do not restore 4K or three-output operation.
Read [XP.md](XP.md) for the prior display-resource failures and recovery evidence.

The first Win7 physical launch lost a race with the outgoing XP session's lock.
After that lock released, a retry worked. All three launchers now wait up to
20 seconds per lock before refusing; they still prevent concurrent shell sessions.
Protected Win7 → XP → ReactOS → Win7 switches subsequently passed without retries.

SSH remains the recovery channel. Ctrl+Alt+Backspace exits labwc; Log Off is
expected to return to SDDM (stock autologin policy decides the destination).
Real shutdown/reboot commands are disabled. Root trial controller `rescue`
selects Armada Desktop using its own temporary override; verify screen visibility.

## Measured validation

- Private native compositor: x64 Win7 Explorer owns desktop/taskbar; folder
  browsing and headless Log Off passed. Win32 system DPI is 120 and the active
  visual style is `Aero/aero.msstyles`, `NormalColor/NormalSize`.
- Physical native DRM: desktop/taskbar ownership, folder browsing, native Konsole
  integration, and absence of Plasma/KWin/Steam shell passed for all three variants.
- Upper-panel compositor screenshots show the cursor in Win7, XP and ReactOS.
- The software-cursor environment setting is present in the live compositor,
  and the built wlroots source implements it; no driver/firmware change was made.
- No matching new DPU allocation errors were found during these upper-only switches.
- Trial overrides were removed, timers canceled, and the three saved boot/mode
  configuration hashes verified unchanged after each accepted switch.

The user was away: this is screenshot/software validation, not new user confirmation
of physical touch, audio or mouse visibility. DP was disconnected, so the reported
external-display cursor failure remains physically unverified.

`capture-shell-cursor.py --shell win7|xp|reactos` moves a virtual pointer and saves
upper-output captures with/without the cursor. It never enables or modesets outputs.
Private native `grim` and `wlrctl` live under `~/.local/share/win4wine/tools/`.
Do not use `test-win7-headless.py` while the live Win7 prefix is active.

## Aero: remaining blocker, not a theme checkbox

Upstream explicitly supports **Windows 7 Basic**, not DWM Aero glass, Peek or
live taskbar thumbnails. Inspection of the actual Wine source on the Thor confirms:

- `DwmIsCompositionEnabled` deliberately returns FALSE inside `w7-explorer.exe`.
- `DwmEnableBlurBehindWindow` and thumbnail operations are unimplemented stubs.
- `DwmExtendFrameIntoClientArea` returns success without rendering glass.
- A generic non-shell probe reports composition enabled because Wine defaults to
  a newer Windows version. That result is **not evidence of functioning DWM**.

The live `shell-ui-probe-x64.exe` at 120 DPI returned `0x80004001` (`E_NOTIMPL`)
for both blur-behind and thumbnail registration. Results are saved in
`~/.local/state/win4wine-win7/dwm-api-probe.txt`.

The supplied Aero assets provide the Basic theme and Aero cursor images, not the
composition engine. No fake composition toggle, native DWM DLL replacement or
unproven compositor fork was installed. Full effects require substantial Wine/DWM
and compositor rendering work (or a separate Windows VM approach with its own
performance trade-offs), not just enabling Vulkan or selecting `aero.msstyles`.
The requested full Aero effects remain unfinished; stable Win7 was left running.
