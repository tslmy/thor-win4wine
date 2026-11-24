# Win7 overnight work plan

User authorization: work independently overnight on 2026-11-24, add Windows 7 SP1
x64 from the supplied media, pursue Aero effects, and fix the missing mouse cursor.
The XP checkpoint was already committed as `4748769`.

## Protected test policy

- Keep DSI-1 and its touch input disabled; never test three physical outputs.
- Keep existing prefixes, bootc image and Steam configuration unchanged.
- Build and test Win7 in its own prefix and headless compositor before selecting it.
- Any real-session switch uses an independent timed rollback and a known fallback.
- External tests, if the monitor is actually connected, are limited initially to
  DSI-2 plus DP-1 at a reported mode no higher than 1920x1080. The compositor starts
  with all outputs disabled before applying that policy. No 4K or lower-panel test.
- Do not remove normal switching guards unless this conservative two-output
  configuration has passed a protected test. If DP remains unplugged overnight,
  record the hardware-validation gap rather than claiming physical DP success.
- Inspect screenshots with the private native grim tool; preserve diagnostic logs.

## Work order

1. Extract supplied Win7 x64 assets using the original ISO (also mounted at
   `/Volumes/GRMCULXFRER_EN_DVD`). Keep all proprietary artifacts in ignored `.build/`
   or on the Thor; no binary redistribution.
2. Create an isolated English Win7 prefix with the existing Wine 11/Box64 runtime.
3. Validate shell ownership, folders, DPI/theme, native Linux window integration,
   logoff, and safe panel configuration. Register a third SDDM entry and switch action.
4. Research Aero honestly. Upstream explicitly implements Windows 7 Basic and says
   DWM glass/live thumbnails/Peek are unsupported. Do not label Aero theme assets or
   a fake DwmIsCompositionEnabled return value as a completed Aero implementation.
   Keep any experimental effects opt-in and separate from the stable shell.
5. Investigate the common cursor path (Wine/Xwayland, wlroots cursor planes, touch
   hiding). Prefer a scoped software-cursor fallback over DRM-driver or firmware changes.
6. Commit working checkpoints and update handoff/variant docs. Leave a stable session
   running and add precise todos for genuinely unresolved work.

## Result

Win7 extraction, isolated prefix/session registration, headless shell/folder/logoff
tests and protected upper-panel validation completed. A guarded round trip through
XP and ReactOS back to Win7 passed with boot hashes unchanged. Upper screenshots
show cursors in all three variants after enabling supported software-cursor fallback.
Win7 was left running; the lower output remains off and trial timers are canceled.

Full Aero remains blocked by actual Wine DWM blur/thumbnail stubs (`E_NOTIMPL` in
the live probe), not by a missing visual-style file. DP was disconnected, so physical
external mouse visibility remains unverified. Both gaps are tracked in project todos.
See [WIN7.md](WIN7.md) for the measured evidence and remaining limitations.
