# Investigation: ReactOS as the sole desktop shell

**Working on the real DRM seat as of 2026-11-23, using a separate 192-DPI prefix.**

## Current status

- Native ARM64 patched labwc 0.8.3 / wlroots 0.18.2 / libsfdo 0.1.3 built in
  a Fedora 44 ARM64 Docker container and deployed in the Thor user's home.
- Upstream compositor assertions passed on an isolated native Xvfb: desktop,
  taskbar, stacking, proxy-frame pairing, geometry, maximization and shaped windows.
- Native GLES2 startup passed nested on Plasma's Wayland display. Driver log:
  EGL Mesa, GL freedreno, renderer **FD740** (Adreno 740).
- SDDM entry **ReactOS Shell (Standalone)** is registered and has been selected
  on the real DRM/logind seat. Both handheld panels are enabled and rotated correctly.
- Live assertions passed for ReactOS desktop/taskbar ownership, folders opening
  in ReactOS Explorer, and a native Linux terminal appearing in shell integration.
- No `plasmashell`, `kwin_wayland`, or Steam shell was running during those checks.
- The user confirmed touch works and clarified that the lower display is on;
  its background is black, not a failed panel.
- The user confirmed an explicitly positioned test window is visible on the
  Dell U2720Q via **DP-1 at 3840x2160 / approximately 60 Hz**.
- Standalone Wine is at **192 DPI**, verified through Win32 APIs, not just the
  registry. The original nested Wine prefix remains at 96 DPI.
- Original SDDM autologin and steamos-manager boot defaults are unchanged.
  Trial overrides were removed and rollback timers canceled after acceptance.
- Still to test/harden: audio playback and controller shortcuts, suspend/resume,
  actual polkit prompts, desktop portals, and an ordinary shell Log Off round trip.

### New files on the Thor

- Native compositor and private test Xvfb: `~/.local/share/win4wine/labwc/bin/`
- Launcher: `~/.local/bin/reactos-standalone-session`
- Startup adapter: `~/.local/share/win4wine/tools/reactos-standalone-start`
- Config: `~/.config/win4wine/reactos-standalone.json`
- Dedicated Wine prefix: `~/win4wine/.local/prefix-reactos-standalone/` (192 DPI)
- labwc config: `~/.local/share/win4wine/labwc-config/`
- Logs: `~/.local/state/win4wine-standalone/`
- Session entry: `/etc/win4wine/wayland-sessions/armada-reactos.desktop`
- Session-directory override: `/etc/sddm.conf.d/50-win4wine-session-dirs.conf`
- Registration manifest: `~/.local/share/win4wine/standalone-registration-20261123-221705.json`
- Safe trial controller: `/etc/win4wine/standalone-test-control.py`

The override adds only a session directory, **not an autologin selection**.
The registration tool refuses existing different content and records created
file hashes. No `/usr` overlay, system package installation, or display-manager
replacement was needed.

### Prepared behavior and escape routes

The standalone launcher requires an SDDM seat/VT environment, uses logind for
DRM access, and allows only one nested/standalone shell session at a time.
It stops lingering graphical-session units only when launched in that seat.
labwc is the only compositor in this session; no Plasma/Steam shell is started.

The startup adapter requests the upper panel at 60 Hz and uses the lower panel's
sole 1080x1240 mode (actually 59.999 Hz), with Wayland transform 270
(equivalent to KScreen Right), scale 1.5, upper panel primary and lower panel
centered beneath it. Touch devices are mapped by name to their own outputs
with mouse emulation. Real DRM startup and user touch feedback validated this setup.

- ReactOS Log Off ends the supervisor and should end labwc, returning control to
  SDDM. The destination afterwards is controlled by SDDM; boot defaults still select Game Mode.
- Ctrl+Alt+Backspace is a compositor-level emergency exit.
- Real shutdown/reboot remain disabled until separately approved/tested.
- The lower panel is a second desktop output, **not yet an on-screen keyboard**.
- ReactOS's wallpaper/taskbar are primary-only. Secondary and external outputs
  can therefore look black until a window is moved onto them; black is not "no signal".
- SSH remains the recovery channel; do not rely solely on GUI recovery.

For a failing test session, the existing Armada helper
`sudo -n /usr/libexec/armada/session-control switch-desktop` selects the stock
Armada desktop and restarts/switches SDDM. This is disruptive and is a recovery
action, not something to run during preparation. Any temporary autologin/test
override must first be removed/restored if one is introduced during the test.

### Rebuilding and repeating safe tests

On the Mac, run `bash thor/build-labwc-arm64.sh`. It creates or resumes the
`thor-labwc-build` container; generated sources and artifacts live in ignored
`.build/labwc/`. Pinned source archives and patch digests accompany the runtime.

On the Thor, `PYTHONPATH=$HOME/.local/share/win4wine/python python3
~/.local/share/win4wine/tools/test-native-labwc.py` runs the isolated compositor
assertions. `python3 ~/.local/share/win4wine/tools/test-labwc-gles2.py` runs the
brief nested GLES2 smoke test while an existing Wayland desktop is available.

To recreate the dedicated prefix, first close all Wine programs in the original
source prefix, then run `python3 ~/.local/share/win4wine/tools/create-standalone-prefix.py`.
It defaults to 192 DPI, refuses to overwrite an existing destination, and uses
Btrfs reflinks when available. DPI lives in the prefix registry, not a JSON `dpi` field.

Making ReactOS the boot/default managed desktop remains a separate decision.

## What the live trial uncovered

### SDDM/compositor lifecycle

The lower mode is 59.999 Hz, so exact `1080x1240@60Hz` selection was rejected.
Use `--mode 1080x1240` for this single-mode panel. The first failure also exposed
a lifecycle issue: SDDM was tracking a shell waiting on labwc; the compositor
could survive the helper and keep the session lock. The launcher now **execs
labwc directly**, and the primary startup script terminates its own `LABWC_PID`
on exit, including startup failures. The orphaned test compositor was terminated
by its specific PID; no broad user-process kill was used.

### Safe trial and unchanged defaults

`standalone-test-control.py arm|begin` creates a temporary autologin selection
via `/etc/sddm.conf.d/zzzz-win4wine-live-test.conf`, a symlink to a file in `/run`.
Thus its target disappears on reboot instead of making a failed trial persistent.
It arms an independent root systemd rollback timer for eight minutes before
switching/stopping SDDM. `arm` prepares protection without restarting the display
manager, useful while adjusting a stopped Wine prefix; `begin` also restarts SDDM.

`accept` cancels that trial's timer, removes only its expected symlink/config,
and leaves the current ReactOS session running. SHA-256 comparisons confirmed
`armada.conf`, `zz-holo-autologin.conf`, and steamos-manager `state.toml` were unchanged.
The automatic rollback branch was armed but did not need to run during the
successful trial; do not claim a full recovery-path test has been performed.

### DPI: measure the APIs, not only a perceived change

The user found 96 DPI too small and did not perceive a sufficient change at
144 DPI. We cloned the idle, validated prefix with Btrfs reflinks, keeping the
original at 96 DPI, and raised the standalone copy to 192 DPI. Upstream probes
confirmed system DPI 192, Tahoma menu/caption fonts at 22 pixels, a 50-pixel
taskbar and an 87x40 Start button. At 144 DPI these were 17-pixel fonts and a
40-pixel taskbar. **Classic shell icons remain 32x32** by the upstream XP-style
policy, so DPI is not an across-the-board image enlargement.

### DisplayPort: connected state is not sufficient visual validation

DP-1 did hotplug and modeset at 4K/60. Disconnect/reconnect attempts also logged
USB/PHY resume warnings (including a resume timeout); no kernel, firmware, or
USB binding was changed to address those warnings. Subsequent reconnect worked.

The initial diagnostic window was cascaded back to the handheld by Linux-window
placement, invalidating that visual test. The corrected probe uses synthetic
Wine window identity like upstream's compositor tests, so its requested X11
position is preserved. Global coordinates 3210,50 were verified on DP-1, and
the user then confirmed the blue window was visible. Probe windows/services
were stopped after testing. Do not describe the earlier blank external workspace
as proof that DisplayPort is unsupported.

### Remaining integration caveat

PipeWire, PipeWire PulseAudio and WirePlumber were running, but playback was not
audibly tested. A polkit agent starts, yet its log includes a desktop-portal
activation failure. Investigate proper graphical-session target/portal integration
before claiming complete desktop-service or Flatpak support. None of that requires
putting Plasma's desktop shell back underneath ReactOS.

## What “sole shell” means here

ReactOS Explorer can own the desktop, taskbar, menus, and application switching
without Plasma or Steam running as a desktop shell. It cannot replace Linux's
display/input infrastructure: a compositor and Xwayland are still necessary.
Those are plumbing, not a second desktop shell.

## Recommended architecture

SDDM login → **native ARM64 patched labwc** (DRM/Wayland) → Xwayland →
native Python win4wine supervisor + Box64/patched Wine → ReactOS Explorer.

This follows win4wine's upstream Wayland-session design rather than trying to
hide Plasma. Its patched labwc replaces the X11 bridge window manager, knows
about ReactOS/Wine desktop and taskbar windows, and gives native Wayland Linux
apps the shell integration/frames. Wine itself can remain the working x86-64
WoW64 build behind the private Box64 wrappers.

Relevant upstream files:

- `win4wine/docs/wayland.md`
- `win4wine/wayland/build.sh` and `wayland/upstream.env`
- `win4wine/wayland/session.sh`
- `win4wine/wayland/patches/labwc/` and `wayland/patches/wlroots/`
- `win4wine/session/supervisor.py`, especially `configure_outputs()` and `run()`

The pinned upstream build uses labwc 0.8.3, wlroots 0.18.2 and libsfdo as
fallback subprojects. It enables DRM/libinput/X11 backends and GLES2 rendering.
wlroots is built into the compositor rather than replacing a system package.
Use a native ARM64 build container with Fedora-compatible dependencies, or
otherwise inspect/deploy all required native shared libraries. A Wine rebuild
should not be necessary just to add the compositor.

## Findings on this Thor

- Display manager: **SDDM**, with a Wayland greeter/session wrapper.
- Existing session entries: Armada Desktop, Armada Plasma Mobile, Steam Big
  Picture, and upstream Plasma entries. No X11 sessions were registered.
- Before preparation, `Xorg`, `labwc`, and `weston` were not found on PATH.
  **Cage** and **Gamescope** were already installed. Xwayland works; native
  labwc is now deployed privately rather than added to the system PATH.
- `/usr/local` is a directory in the immutable filesystem, not a writable
  `/var/usrlocal` symlink. Do not assume generic Fedora bootc `/usr/local` recipes apply.
- SDDM supports **comma-separated SessionDir lists** (confirmed with
  `sddm --example-config`). A persistent extra session directory can live in
  `/etc/win4wine/wayland-sessions`, alongside `/usr/share/wayland-sessions` in
  an added `[Wayland] SessionDir=...` override. This must preserve stock sessions.
- Scripts/binaries can stay in `/var/home/armada/.local/...`; registration and
  SDDM overrides can live in `/etc`, outside the immutable image.

### Autologin / mode management is not just one SDDM option

- `/etc/sddm.conf.d/armada.conf`: user `armada`, `Relogin=true`, Steam session.
- `/etc/sddm.conf.d/zz-holo-autologin.conf`: selects the Steam session.
- `~/.config/steamos-manager/state.toml`: `default_login_mode="Game"`,
  `desktop_session="armada-plasma.desktop"` at inspection time.
- `/usr/libexec/armada/session-control` can change the override and restart
  SDDM; `/usr/libexec/os-session-select` normally delegates to `steamosctl`.
- `/usr/libexec/armada/steam-default-session` seeds managed desktop-session
  defaults. A custom entry named `armada-reactos.desktop` may fit its existing
  `armada-*.desktop` preservation rule, but this needs end-to-end validation.

Therefore, first add a **selectable** session without changing boot defaults.
Only then investigate the supported steamos-manager/steamosctl path for making
it the managed desktop or boot default. Do not edit its state file speculatively
or let `Relogin=true` trap the device in a crashing session loop.

### Displays and touch

- Upper panel: `DSI-2`, raw 1080x1920, 120 Hz or 60 Hz, rotated right into
  1920x1080 landscape. Plasma currently uses scale 1.6.
- Lower panel: `DSI-1`, raw 1080x1240 at 60 Hz, also currently rotated right;
  Plasma uses scale 1.5. Current desktop positions are user-adjusted, not an
  assumption to overwrite.
- Device environment names the touchscreens `top_touchscreen` and
  `bottom_touchscreen`, with each associated connector.
- Armada's `setup-dual-screen` script uses **KWin-specific** input mapping and
  layout configuration. Those settings will not automatically configure labwc.
- win4wine's supervisor output config currently handles mode, custom mode,
  position and scale, **not transform**. Add rotation through labwc/output
  configuration or a targeted pre-supervisor `wlr-randr --transform ...`
  adapter; don't assume a `transform` JSON field will work.
- Touch-to-output mapping, axis transforms, the lower-screen role, keyboard,
  and suspend/resume must be tested under the actual DRM session.

## Other approaches considered

**Direct Xorg + current X11 bridge:** closest to the tested nested desktop,
but Xorg is absent and Thor's dual-panel rotation/input would need fresh Xorg
configuration. It is not the natural first choice for this Wayland ARM device.

**Gamescope instead of Steam:** Gamescope already has Armada device handling
and a standalone DRM backend. However, its own XWM conflicts with the current
win4wine X11 bridge if both manage the same root. Hosting the whole current
rootful Xwayland desktop inside it could be a practical interim session with
no Plasma/Steam shell, but it retains nested scaling and is not equivalent to
native win4wine Wayland window integration. Do not simply replace Steam's
`CLIENTCMD` and assume multiwindow behavior will work.

**Cage:** lightweight and installed, but intended for a kiosk client. It does
not provide win4wine's patched desktop/window integration or the required
dual-screen configuration on its own. It could host a nested desktop, not
replace the specialized compositor directly.

**KWin without plasmashell:** technically no Plasma desktop shell, but retains
KWin and KDE-specific plumbing. The current X11 bridge would still need an
isolated root. It is an alternative if native labwc cannot handle the hardware,
not the recommended clean architecture.

## Implementation and acceptance gates

1. Build/deploy native patched labwc and a native `wlr-randr` if needed, keeping
   all application-specific artifacts out of the immutable system image.
2. Test native compositor startup/nested integration without logging out first.
   This validates the build, not direct DRM access or real touch mapping.
3. Make a separate standalone config (do not repurpose the safe nested config).
   Keep the same Box64 Wine wrappers and active ReactOS prefix initially.
4. Add an SDDM session and persistent session-directory override; back up only
   the config files actually changed. Keep Armada Desktop and Gaming Mode available.
5. With user approval for a session interruption, perform a controlled logout
   and select the new session. Maintain SSH and prepare a rollback to the known
   Armada session without requiring the experimental GUI to work.
6. Prove no `plasmashell`, KWin compositor, or Steam shell remains active;
   verify ReactOS taskbar/desktop ownership and native Linux app integration.
7. Test both panels, orientation, touch, keyboard/controller input, audio,
   polkit prompts, power controls, and recovery after shell/compositor failure.
8. Only after those tests, consider making ReactOS the managed desktop or
   autologin default. Decide separately whether real shutdown/reboot should be enabled.

Keeping Plasma **installed as a fallback** does not mean it runs underneath
ReactOS. Removing Plasma packages is unnecessary and makes recovery harder.
