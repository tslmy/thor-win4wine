# Continuing this project

Read `HANDOFF.md`, `thor/README.md`, `thor/STANDALONE.md`, and `thor/XP.md` before changing
the device's session setup. Those files distinguish measured results from
untested proposals.

- `win4wine/` has its own Git history. Do not vendor it into the parent repository
  or reset its files. The parent repository tracks Thor-specific adaptations.
- `thor-pad-mouse/` (controller as mouse in desktop sessions) is likewise its own
  repository; do not vendor it here.
- Do not run upstream `scripts/setup.sh` directly on Armada: it is designed to
  install system packages and potentially change the display manager.
- Keep Armada's system FEX, Steam configuration, and bootc image unchanged
  unless the user authorizes changes to them.
- Before a login-session switch, confirm the user is ready to close the current
  desktop. Preserve SSH access and a tested route back to Armada Desktop or Gaming Mode.
- Use separate configuration files for nested and standalone sessions. Do not
  enable real poweroff/reboot commands in the nested session.
- Keep documentation current and commit only this session's changes, using plain git.
- This checkout is the public repository. Never commit a device address, key path,
  device login, personal email, serial number or capture. Commit as the author in
  the local Git config (a GitHub noreply address). Run
  `python3 tools/audit-public.py` before pushing.
- Device connection settings are in `.env` (git-ignored; see `env.example`):
  `ssh -i "$THOR_SSH_KEY" "$THOR_USER@$THOR_HOST"` after `set -a; . ./.env`.
- The shells run three outputs (both panels and DP, up to 4K); `thor/EXTERNAL.md`,
  "Three outputs", has the DPU budget and the limits. Keep the launchers' refusal to
  start with the XREAL glasses connected until Armada's kernel has the DP PUSH_IDLE
  fix (armada#953, armada#956): until then, a failed DP link training followed by a
  disable or an unplug resets the SoC, and the glasses fail training often. Keep `thor/capture-reset.sh` running during DP tests.
- XP assets are proprietary user-provided media. Keep them and screenshots out
  of this repository; `.build/` is ignored for that purpose.
