# AYN Thor / ArmadaOS experiments

Thor-specific launchers, reproducible support scripts, and research notes.
The existing `win4wine/` directory is an independent upstream checkout and is
intentionally excluded from this repository. No Wine builds, rootfs archives,
ReactOS media, SSH keys, or live Wine prefixes are committed here.

## Start here

- [Handoff and troubleshooting history](HANDOFF.md): what was tried, what
  actually worked, and what Claude or another agent should know before continuing.
- [Installed shell: usage and paths](thor/README.md): the working nested ReactOS
  shell, launch/exit instructions, compatibility layer, and validation.
- [Standalone shell investigation](thor/STANDALONE.md): how to replace Plasma
  as the active desktop session without removing the recovery options.
- [Windows XP variant](thor/XP.md): the second shell, switching, corrected DPI,
  lower-panel policy, and the display-driver failure/recovery history.

Device: AYN Thor Pro, Snapdragon 8 Gen 2, 12 GB RAM, running ArmadaOS.
The initial installation and investigation were performed on 2026-11-23.
