# Continuing this project

Read `HANDOFF.md`, `thor/README.md`, and `thor/STANDALONE.md` before changing
the device's session setup. Those files distinguish measured results from
untested proposals.

- `win4wine/` has its own Git history. Do not vendor it into the parent repository
  or reset its files. The parent repository tracks Thor-specific adaptations.
- Do not run upstream `scripts/setup.sh` directly on Armada: it is designed to
  install system packages and potentially change the display manager.
- Keep Armada's system FEX, Steam configuration, and bootc image unchanged
  unless the user authorizes changes to them.
- Before a login-session switch, confirm the user is ready to close the current
  desktop. Preserve SSH access and a tested route back to Armada Desktop or Gaming Mode.
- Use separate configuration files for nested and standalone sessions. Do not
  enable real poweroff/reboot commands in the nested session.
- Keep documentation current and commit only this session's changes using GitButler.
