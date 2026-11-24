# Investigation: ReactOS as the sole desktop shell

**Research only as of 2026-11-23. No standalone login session installed yet.**

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
- `Xorg`, `labwc`, and `weston` were not found on PATH. **Cage** and **Gamescope**
  are already installed. Xwayland is present and works.
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
