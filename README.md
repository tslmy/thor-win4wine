# AYN Thor / ArmadaOS experiments

Run ReactOS, Windows XP, or Windows 7 Explorer as a switchable standalone desktop
on an **AYN Thor running ArmadaOS**, using patched Wine, private Box64, and native labwc.

**Start with [the clone-to-install guide](docs/REPRODUCING.md).** The `justfile`
covers fetching pinned sources, building both runtimes in Docker, extracting your
own media, deploying over SSH, creating prefixes, registering sessions, testing,
and guarded switching. Run `just` to list recipes; `just check` is device-free.

> Experimental, not a full Windows installation. **Win7 is Basic, not full Aero.**
> The lower panel stays off. Disconnect external DisplayPort before switching:
> an earlier three-output trial encountered display-resource failures and an
> unexplained reboot. Existing Gaming Mode/desktop defaults are not replaced.

## Requirements

- Build host: Linux or macOS, Git, Python 3.12+, `just`, Docker with ARM64 and x86-64
  container support, SSH/SCP, internet access and roughly 25+ GiB free build storage.
- Target: Thor on Armada/Fedora 44 with its existing SDDM, Xwayland, native Python GI,
  working SSH, and 8+ GiB writable home storage. Other OS/hardware versions are untested.
- Windows variants: supply your own appropriately licensed XP SP3 x86 or Win7 SP1
  x64 medium. ReactOS needs no Windows media. No product key is collected.

```sh
just doctor
just check
just build
just extract reactos
export THOR_HOST=your-thor-hostname
export THOR_USER=your-linux-login
just preflight
just deploy
just prefix reactos
just test-headless reactos
just register reactos
```

Registration does **not** close the current desktop. Physical session switching
is a separate explicit opt-in; read the guide and preserve SSH recovery first.
Fresh installs are supported; automated in-place upgrades are intentionally refused.

## Source, privacy and limitations

The existing `win4wine/` directory is an independent upstream checkout and is
intentionally excluded from this repository. No Wine builds, rootfs archives,
ReactOS media, SSH keys, or live Wine prefixes are committed here.
The reproducible recipes use a pinned download under ignored `.build/reproduce/`,
not an existing developer checkout. See [SECURITY.md](SECURITY.md) for audit boundaries
and [THIRD_PARTY.md](THIRD_PARTY.md) for source/license attribution.

The public history preserves the implementation checkpoints with local identifiers
redacted and anonymized author metadata. Historical commit hashes in notes may
refer to the original private history and are not public revision selectors.

## Start here

- [Handoff and troubleshooting history](HANDOFF.md): what was tried, what
  actually worked, and what Claude or another agent should know before continuing.
- [Installed shell: usage and paths](thor/README.md): the working nested ReactOS
  shell, launch/exit instructions, compatibility layer, and validation.
- [Standalone shell investigation](thor/STANDALONE.md): how to replace Plasma
  as the active desktop session without removing the recovery options.
- [Windows XP variant](thor/XP.md): the second shell, switching, corrected DPI,
  lower-panel policy, and the display-driver failure/recovery history.
- [Windows 7 variant](thor/WIN7.md): the third shell, validation and the DWM/Aero blocker.

Device: AYN Thor Pro, Snapdragon 8 Gen 2, 12 GB RAM, running ArmadaOS.
The initial installation and investigation were performed on 2026-11-23.
