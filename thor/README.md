# win4wine on the AYN Thor

**New installation? Start with [the clone-to-install guide](../docs/REPRODUCING.md)
and the root `justfile`.** The paths and commands below describe the historical
development device. The new installer discovers your actual user/home/UID and
never requires the original developer's machine, Docker volume or credentials.

Installed on `armada@thor.local` on 2026-11-23, using the existing win4wine
checkout, Claude's completed patched Wine 11.0 build, and the supplied
`ReactOS-0.4.16-i386.zip`. The shell uses the classic ReactOS theme in English.

**Current session:** standalone **Windows 7 Basic**, at **120 DPI**, on the upper
panel only. XP / Silver Luna (120 DPI) and ReactOS (192 DPI) remain separately
installed and switchable. All three use software cursors; upper-output screenshots
show visible pointers, but physical DP validation is pending. The lower panel
is disabled; boot defaults still select Gaming Mode. See [WIN7.md](WIN7.md) for
Win7 results and the unfinished Aero effects, and [XP.md](XP.md) for safety limits.

## Open and close

In Armada's **Desktop Mode**, open **ReactOS Shell (win4wine)** from Plasma's
application launcher. It opens fullscreen on the upper display (`DSI-2`).
The nested desktop uses 1280×720, scaled fullscreen to the upper panel. You can
also run `~/.local/bin/reactos-shell-window` on the Thor.

Start → Log Off closes the shell and returns to Plasma. Shutdown and restart
requests only close this window; they do not power off or reboot the Thor.
Plasma's keyboard shortcuts remain available. No greeter, login session,
Gaming Mode, Steam configuration, or bootc image was replaced.

## Installed files

- Source and patched Wine: `~/win4wine/`
- Working prefix: `~/win4wine/.local/prefix-reactos-box64/`
- Session configuration: `~/.config/win4wine/reactos-session.json`
- Private runtime/support: `~/.local/share/win4wine/`
- Wine entry points: `~/.local/share/win4wine/box64-wine/bin/{wine,wineserver}`
- Application launcher: `~/.local/share/applications/reactos-shell.desktop`
- Logs and status: `~/.local/state/win4wine/`

The incomplete Docker-derived prefix at `~/win4wine/.local/prefix-reactos/` was
retained after repair attempts, not selected for use. The Docker volume
`w4w-home` and original `w4w-build` container on the Mac were retained.

## Architecture compatibility

ReactOS's explorer and shell DLLs are i386 Windows binaries. This patched
Wine uses new WoW64, with an x86-64 Unix runtime. Testing the build under
Armada's FEX left the 32-bit prefix components uninitialized and failed to
start 32-bit programs. A private Box64 runtime successfully ran the same build.

Box64 is extracted into the user's home directory, not installed as a system
package or registered in binfmt. Armada's FEX remains the system translator.
The private Debian rootfs supplies any required x86-64 libraries; Box64 also
wraps native ARM64 libraries. Native Python runs the supervisor and bridge WM.
Only pure Python Xlib is vendored, so Python GI uses Armada's native bindings.

Box64 package, from the prebuilt repository linked in Box64's compile guide:

- `box64-generic-arm_0.4.5+20261117T153228.27c8275-1_arm64.deb`
- URL: `https://pi-apps-coders.github.io/box64-debs/debian/box64-generic-arm_0.4.5+20261117T153228.27c8275-1_arm64.deb`
- Verified SHA-256: `5d7a3ee8a17b28cb3192465c054544faaafa7d894a4fa92ef6d9a50a58d7edd9`

## Validation

The upstream `tests/reactos_session.py` integration test passed on the Thor:

> PASS: ReactOS taskbar and desktop, folders in ReactOS explorer, log off

Its logoff probe was compiled with the private Debian MinGW compiler under
FEX. `tools/test-reactos-session.py` tolerates the nested X server closing
during the test's final connection cleanup after successful Log Off, without
changing any test assertions. The `.desktop` entry passed `desktop-file-validate`, and the launcher
passed `bash -n`.

This remains experimental shell integration, not a complete Windows or
ReactOS installation. ReactOS's unsupported settings/network/printer
components remain unsupported. Plasma owns the shared Linux notification
watcher, so the nested shell does not replace Plasma's system tray.

## Troubleshooting

Read `status.json`, `xp-shell.log`, `wm.log`, and `window-session.log*` in the
log directory. A healthy session reports `"state": "xp-shell"` (the upstream
supervisor uses that name for ReactOS too).

For this installation's systemd-launched test session, use
`systemctl --user stop win4wine-reactos` to close it. Normal application-launcher
starts do not use that transient unit.

Set `WIN4WINE_OUTPUT=DSI-1` when launching to use the lower display instead.
The launcher prevents two concurrent nested sessions.

## Standalone session (working)

**ReactOS Shell (Standalone)** is registered separately with SDDM and has been
selected/tested on the real DRM seat. Desktop/taskbar, folder handoff and native
Linux-window tests passed; the user confirmed touch and external DisplayPort
image output at 4K/60. The current session was kept, not made the boot default.

Its separate prefix is `~/win4wine/.local/prefix-reactos-standalone/`, at 192 DPI.
Win32 probes confirmed the change; classic shell icons remain 32x32 even as
text and menus get larger. The original nested configuration/prefix is unchanged.

The lower panel and external monitor are extended workspace. Their backgrounds
can be black because ReactOS paints the wallpaper/taskbar on the primary panel
only. They are not a second desktop shell or an automatic screen mirror.

**This describes the earlier three-output ReactOS trial.** The current policy,
requested while testing XP, disables the lower panel and starts labwc with all
outputs off before explicitly enabling the upper panel. External-session switching
is guarded until the revised conservative two-output setup is validated.

See [STANDALONE.md](STANDALONE.md) for remaining integration checks and recovery.
Do not run the standalone launcher directly over SSH. Ctrl+Alt+Backspace exits
the compositor; ordinary Log Off returns control to SDDM. Making this the managed
desktop or boot default is a separate configuration change.
