# Handoff: win4wine on the AYN Thor

**For the user and Claude / the next agent. Updated 2026-11-23.**

## Short version

ReactOS 0.4.16's i386 shell is installed and works on the Thor in a fullscreen
Xwayland window over Plasma. It uses upstream win4wine's patched Wine 11.0,
**private Box64**, and native Python for the supervisor/window manager.
The taskbar, desktop, folder handoff, and logoff integration test passed.

It is **not yet a standalone login session**. Plasma/KWin are still running.
The next goal is a session whose only desktop shell is ReactOS; a compositor
is still required underneath it. See `thor/STANDALONE.md` for the investigation.

## Device and access

- AYN Thor Pro: Snapdragon 8 Gen 2, ARM64, 12 GB RAM, 256 GB storage.
- SSH: `ssh -i /Users/thor-user/.ssh/id_ed25519_thor armada@thor.local`
- Actual remote home is `/var/home/armada` (use `$HOME`, not `/home/armada`).
- Observed OS: Armada `20261109.dfed5d6`, Fedora-like 44, aarch64 kernel 7.2.6,
  4096-byte pages. `/usr` is immutable composefs; `/etc` and `/var` are writable.
- As of the end of installation, approximately 82 GB was available in `/var/home`.
- `sudo -n` worked for read-only diagnostics; no password was collected.

## What Claude left, and what was recovered

On the Mac:

- `win4wine/` was already cloned; no upstream source edits were needed for this installation.
- Upstream HEAD: `45d728622554289e36cd8dfe52e24f0faf8f9316`,
  “Merge branch 'ql-icons': Wine 0151, sharp small icons in Quick Launch”.
- Input media: `~/Downloads/ReactOS-0.4.16-i386.zip`.
- Docker container `w4w-build`: Debian trixie amd64; persistent volume `w4w-home`
  mounted at `/var/home/armada`.
- The build was **finished**, not still compiling: Wine compiled/installed and
  the bridge and ReactOS extraction completed. The container exited 1 during
  prefix creation because `C:\windows\syswow64\regsvr32.exe` could not run.
- Wine install patch digest:
  `2880f9ac8bc8a3976da2e5d6997be941038f0608fc35415dabe85570750bccc9`.
- The original Docker container and volume were retained. A temporary helper
  container, `w4w-recovery`, mounted the same volume to read/copy its files;
  it is now stopped, not deleted.

The Debian container filesystem was exported into the Thor's private rootfs,
excluding virtual filesystems and host bind mounts. The built Wine, bridge,
ReactOS assets, and source checkout were copied into `~/win4wine/` on the Thor.
The first transfer attempts were interrupted/restarted; the final runtime
transfer succeeded. Some build/source artifacts also remain on the Thor.
Do not interpret their presence as a need to rebuild Wine.

## Experiments, failures, and conclusions

### 1. Existing Armada FEX

Armada already provides `/usr/bin/FEX` and x86/x86-64 binfmt handlers. Its normal
rootfs is `/usr/share/guestos/fex-mesa`. A user FEX config also references Steam's
FEX thunk libraries. We did not change either configuration.

`FEX .../wine --version` returned `wine-11.0`, so the x86-64 launcher itself ran.
But both the Docker-created prefix and a fresh FEX-created test prefix lacked
the complete 32-bit `syswow64` files. Direct 32-bit command tests also failed.
In-place `wineboot -u` did not repair the incomplete prefix.

There were misleading secondary errors, including a “file probably truncated”
message for `msvcrt.dll`, missing imports, and an unimplemented `InternetOpenW`.
SHA-256 checks showed the installed DLL, prefix copy, and Docker source copy
matched; this was not evidence of a damaged transfer or bad source build.

**Measured conclusion:** this particular new-WoW64 Wine build did not work for
our 32-bit shell under the tested FEX configuration. The architectural suspicion
is the x86-64/32-bit WoW64 CPU transition. This was not reduced to an upstream
FEX bug or proven to mean all Wine/FEX combinations are unsupported. Do not
generalize the result to native ARM64 Wine+FEX, Proton, or traditional multilib Wine.

### 2. Private Box64: successful

Box64 ran the same patched Wine build and successfully populated `syswow64`.
A clean Box64 ReactOS prefix was then created successfully with upstream
`prefix/reactos.py` through `thor/create-reactos-prefix.py`.

The package was taken from the prebuilt repository linked by Box64's own
compile guide, extracted into the user's home, and SHA-256 verified:

- Package: `box64-generic-arm_0.4.5+20261117T153228.27c8275-1_arm64.deb`
- SHA-256: `5d7a3ee8a17b28cb3192465c054544faaafa7d894a4fa92ef6d9a50a58d7edd9`
- URL and install paths are also in `thor/README.md`.

Initial Box64 startup failed to find `libgcc_s.so.1`. Setting
`BOX64_LD_LIBRARY_PATH=$HOME/.local/share/win4wine/rootfs/usr/lib/x86_64-linux-gnu`
fixed it. The wrapper also sets `WINELOADER` and `WINESERVER`, and defaults
`BOX64_LOG=0` to avoid verbose runtime output.

The wrapper directory has `lib` and `share` symlinks back to the real Wine
installation. This matters: win4wine resolves helper DLLs and `wine.inf`
relative to the configured Wine executable. A random wrapper in `.local/bin`
without this layout would break those lookups.

No system package installation or binfmt replacement was performed. FEX is
still used for some x86 Linux tools, including compiling the MinGW test probe.

### 3. Prefix repair vs. replacement

The Docker-derived `~/win4wine/.local/prefix-reactos/` is retained after failed
repair attempts, but is **not the active prefix**. Starting clean under Box64
worked where in-place repair did not.

Use **`~/win4wine/.local/prefix-reactos-box64/`**. Its marker and configured Wine
path point to the private Box64 wrappers. Temporary test prefixes
`prefix-clean-test` and `prefix-box64-test` were removed after testing.

`thor/recover-reactos-prefix.py` records the attempted in-place repair. It is
historical/debugging support, **not the successful installation recipe**.
The create script refuses to overwrite an existing prefix; keep that safety check.

### 4. Python and desktop integration pitfalls

- Native Armada Python is 3.14; the exported Debian Python is 3.13.
- Native Python lacked Xlib, which is pure Python. We copied **only `Xlib/`**
  into `~/.local/share/win4wine/python/` and put that directory on `PYTHONPATH`.
- Putting all Debian `dist-packages` on native `PYTHONPATH` broke GI: the
  Debian Python GI code did not match Armada's ARM64 `gi._gi` extension.
  Native GI + vendored Xlib imports now work.
- Plasma already owns `org.kde.StatusNotifierWatcher`. win4wine's tray helper
  detects that and exits without taking over Plasma's tray. That is expected
  in the nested setup; standalone ownership will be different.
- Capturing Wine subprocess output with pipes caused waits for inherited
  descriptors held by background Wine services. Diagnostic scripts now use
  temporary files instead. Do not reintroduce `capture_output=True` for long-lived
  Wine command trees without accounting for that behavior.
- Keeping a Wine server persistent can accelerate registry setup, but a bare
  `wineserver -p` can keep the launching SSH command alive. If used, own the
  process explicitly and stop only the intended prefix's server.
- Rootfs compiler names such as `i686-w64-mingw32-gcc` use absolute Debian
  alternatives symlinks. `FEX /usr/bin/i686-w64-mingw32-gcc` did not resolve here;
  the explicit `i686-w64-mingw32-gcc-posix` executable worked.

### 5. Window and panel setup

The launcher obtains the existing Plasma Wayland socket from the user manager
environment when invoked over SSH. It does not guess a socket or restart SDDM.

It starts a rootful Xwayland server, usually `:10`, fullscreen on `DSI-2`,
with geometry **1280x720**. Without explicit geometry the X root was only
640x480, despite fullscreen presentation. The final resolution was verified
with Xrandr and a screenshot.

It clears the inherited `XAUTHORITY` before connecting to its own X server,
uses a runtime lock to prevent concurrent sessions, and disables real shutdown
and reboot commands in a generated nested-session config. It deliberately
does **not** use `-host-grab`, so Plasma shortcuts remain an escape route.

The supervisor rotates root-level `*.log` files on startup. Since the launcher
opens its output before the supervisor, `window-session.log.1` and
`xwayland.log.1` can be the live launcher logs. Do not assume `.1` always means
an inactive previous run.

## Current files and validation

See `thor/README.md` for the full remote path list. Local `thor/` contains the
launcher, `.desktop` file, Box64 wrapper, creation/recovery helpers, and test adapter.
The local files were copied to the Thor; the native Box64 executable and Wine
runtime are intentionally not in Git.

Validation completed on the device:

- Shell readiness on first attempt; supervisor status `"state": "xp-shell"`
  (that is upstream's shared status name, even for ReactOS).
- Upstream integration assertions: ReactOS taskbar/desktop ownership, opening
  a folder in ReactOS Explorer instead of Wine Explorer, and logoff ending the session.
- The logoff probe was compiled under FEX with MinGW.
- The test adapter tolerates the nested X server closing during the final
  `Display.close()` after successful logoff; it changes no assertions.
- `desktop-file-validate` and launcher `bash -n` passed.
- Final screenshot: `~/.local/state/win4wine/reactos-shell.png`, 1280x720.

The running nested session was left open as the transient user unit
`win4wine-reactos.service`. The application launcher normally starts the script
directly, without that unit. To stop the test-launched instance:
`systemctl --user stop win4wine-reactos`.

## Guardrails for the next phase

1. Do not rerun upstream `scripts/setup.sh` on immutable Armada; its package and
   display-manager modifications are for other distributions.
2. Do not remove Plasma or replace the display manager to obtain a sole shell.
   Add a separate login session first, preserving the existing sessions.
3. A native ARM64 compositor is preferred. Do not assume an x86 compositor
   translated by FEX/Box64 will handle DRM/GBM/Adreno correctly.
4. Current power commands are deliberately disabled. Standalone power handling,
   auth prompts, screen locking, audio, controller input, and the lower screen
   need explicit validation before changing defaults.
5. A true standalone DRM test requires releasing the active desktop's seat.
   Arrange a controlled logout and rollback with the user; don't abruptly kill
   Plasma, restart SDDM, or change autologin on an assumption.
