# Reproduce from a fresh clone

This guide is the entry point; the historical handoff records experiments, not
an installer. Run the `just` commands from the **build host**, not from a root
shell on the Thor. Nothing calls upstream `scripts/setup.sh` on Armada.

## 1. Prepare the host and connection

Install Git, Python 3.12+, [just](https://github.com/casey/just), Docker, and OpenSSH
using your host's supported package manager. Docker must support `linux/arm64`
and `linux/amd64` (Docker Desktop normally does). On a Linux host, arrange the
other architecture's emulation yourself; these recipes do not install binfmt rules.

Clone this repository and use a local filesystem with at least 25 GiB free;
Wine builds and Docker images can need more. Source builds may take hours,
especially under architecture translation. `THOR_JOBS` controls Wine parallelism.

```sh
just doctor
just check
export THOR_HOST=thor.local
export THOR_USER=your-login
# Optional: otherwise SSH uses your existing agent/config and known_hosts.
export THOR_SSH_KEY="$HOME/.ssh/your-thor-key"
just preflight
```

Substitute your real SSH hostname/alias and existing Linux login. No address,
key filename, password or token is built into these recipes. SSH uses batch mode
and host-key checking; establish and verify access yourself first. Do not commit
private connection settings. Secrets are not needed for the public downloads.

The preflight is read-only. It requires ARM64 Linux, the existing SDDM and
Xwayland, systemd/DBus tools, native Python GI, SELinux `restorecon`, and 8 GiB
free in the user's home. It does not install missing system packages or change
Armada's immutable image. The measured target is Armada/Fedora 44 on the Thor;
ABI mismatches or other OS versions must be investigated, not papered over by
replacing system graphics libraries. The installer's `ldd` checks reject missing
native dependencies.

## 2. Build the private runtimes

```sh
just build
just smoke-native
```

- `just source` downloads win4wine at the exact commit in `thor/sources.json`.
  It does not rely on or modify a developer's ignored `win4wine/` checkout.
- `just build-wine` builds Wine 11.0 with that source's ordered patches and
  new WoW64 (x86-64 Unix, i386+x86-64 PE), plus the PE bridge/test helpers,
  in an x86-64 Debian trixie container. The image filesystem is exported as
  a private userspace; no `/build` mount or host home is in that export.
- The pinned, SHA-256-checked Box64 package is extracted, never installed as
  a host/system package. The existing system FEX and its Steam setup stay untouched.
- `just build-native` builds patched labwc/wlroots/libsfdo in Fedora 44 ARM64
  and packages native Xvfb, cursor tools and **only pure-Python Xlib**. Native
  Python GI always comes from Armada, not from an incompatible foreign rootfs.

Artifacts stay under ignored `.build/reproduce/`. Cached builds may resume, but
an unknown source directory or changed patch marker is refused. Inspect partial
builds before deleting anything. Docker build contexts include only `containers/`;
Windows media, SSH files and host prefixes never enter them.

After `just build` and `just extract reactos`, `just test-container` exercises
installation, an independent prefix and the shared headless test in a disposable
Fedora ARM64 container with a different login/UID. It has no DRM devices or host
home mounted. This is complementary to, not a substitute for, a real Thor test.

**Reproducible procedure, not bit-identical binaries:** upstream commits and
Box64/native source archives are pinned/checked, but Debian/Fedora image tags and
package repositories can receive updates. Build logs and downloaded source hashes
remain local. No prebuilt runtime is published by this repository.

## 3. Extract one or more shells

ReactOS is open source; upstream downloads its pinned, hash-checked release:

```sh
just extract reactos
```

For XP, supply your own English XP Professional SP3 x86 ISO or a mounted disc:

```sh
just extract xp "/path/to/your-xp-sp3-x86.iso"
```

For Win7, supply your own English Windows 7 SP1 x64 ISO (not just a mounted folder):

```sh
just extract win7 "/path/to/your-win7-sp1-x64.iso"
```

The extractors mount media read-only and refuse existing extraction directories.
Assets are private and ignored, then transferred to your Thor. They are never
included in Git or a release. Respect the applicable Microsoft license. No Windows
product key is requested. Other languages/editions have not been tested here.

## 4. Deploy without logging out

```sh
just deploy
```

This discovers the SSH user's actual home, username and UID. It refuses root and
unsupported path formats, then installs into `~/win4wine` and
`~/.local/share/win4wine`, plus four launchers under `~/.local/bin`. Per-account
SDDM entries and root-worker templates are rendered rather than assuming a
particular username, `/var/home` path, or UID 1000.

**An existing runtime/source destination is a hard stop**, including this project's
original development installation. This is deliberately not an upgrade/reset
command. It may leave an inspectable partial runtime after a dependency failure;
it never silently deletes it or overwrites a live prefix. The upload staging area
is `~/.local/state/thor-bootstrap`; retain it until validation is complete.

No sudo, SDDM restart, prefix startup or default selection is part of deployment.
Do not upload tar archives received from an untrusted source: the deployment
bundle/rootfs is trusted **locally built** output and includes library symlinks.

## 5. Create and test each chosen prefix

For each shell you extracted (replace `reactos` with `xp` or `win7`):

```sh
just prefix reactos
just test-headless reactos
```

Factories refuse existing assets, prefixes or config files. Wine setup runs on
a private native Xvfb, not the physical desktop. Headless validation uses an
isolated native compositor and DBus session and refuses a live prefix. It checks
shell ownership, opening a folder and Log Off; XP/Win7 also probe theme and DPI.
**Headless does not mean silent:** Wine may play startup sounds on the host's audio.

Defaults: ReactOS classic at 192 DPI, XP Silver/Metallic Luna at 120 DPI, Win7
Basic at 120 DPI. All have separate configs/prefixes and native cursor themes.
Real poweroff/reboot commands are disabled. Windows 7's Aero theme resources
are present, but **glass, Peek and live thumbnails do not work**: Wine's required
DWM operations are stubs. The check must not mistake generic composition=1
for working Aero.

## 6. Register, then deliberately switch

Registration needs root permission to add `/etc/win4wine` and one SDDM config.
Remote recipes use `sudo -n` and never accept/log a sudo password. If that is not
available, open your own terminal on the Thor and run the narrow registration
command interactively with your normal sudo authentication; do **not** grant
blanket passwordless sudo just for this project:

```sh
sudo python3 "$HOME/.local/share/win4wine/tools/register-shell.py" reactos --user "$(id -un)"
```

When noninteractive sudo is already configured, use:

```sh
just register reactos
```

Repeat for each shell. This only **adds** SDDM session choices and Linux-menu
switch entries. It refuses different existing root files. It does not select a
boot default, replace SDDM, modify steamos-manager/Steam, or restart the desktop.

Before a physical switch:

- Save work and close applications: the current desktop will end.
- Disconnect DisplayPort. Keep a working SSH connection from another device.
- Know how to return to stock Armada Desktop/Gaming Mode using the existing SDDM
  choices; keep those stock sessions installed.
- Keep the lower panel disabled. Do not remove the external-switching guard or
  try 4K/three outputs: see the failure evidence in `thor/XP.md`.

Only when ready:

```sh
THOR_ALLOW_SWITCH=1 just switch reactos
just test-live reactos
```

The root worker survives logout, sets a temporary `/run`-backed SDDM override,
and arms an independent eight-minute rollback to Armada Desktop. It accepts after
ten seconds of stable **software** readiness. That does not prove physical screen
health. Ctrl+Alt+Backspace exits labwc; Log Off returns to SDDM, whose unchanged
stock policy decides the next session. Automatic rollback, when needed, selects
stock Armada Desktop; verify that its displays are physically visible.

The standalone defaults keep only DSI-2 on: 1080×1920/60 Hz, transform 270,
scale 1.5. DSI-1 and its touch input stay off. Software cursors are forced.
An unplugged DP monitor cannot validate the original external-cursor fault.

Emergency return over SSH (also closes the current desktop):

```sh
THOR_ALLOW_SWITCH=1 just rescue
```

If the worker is unavailable, inspect `/run/win4wine-test/state.json` and the
specific override before changing anything. Do not blindly remove unrelated
SDDM files or reset Steam's mode configuration.

## Validation status and scope

The original installation passed per-shell headless and physical-session checks,
including Win7 → XP → ReactOS → Win7 switching and visible upper-output cursor
screenshots. The new build-host recipes have source/unit/syntax checks, a fresh
native build and a GPU-less synthetic-output smoke test. The device was unreachable
during packaging, so a **fresh full
clone-to-device installation has not yet been validated**. Treat this as a
reviewable experimental reproduction workflow, not a guarantee on every Thor.

Audio, controller integration, suspend/resume, portals/polkit, full Aero, and
physical external-cursor validation still have gaps. See the variant docs for
measured results versus proposals. This procedure never makes those gaps disappear.
