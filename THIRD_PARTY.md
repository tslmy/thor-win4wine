# Third-party code and assets

This repository holds Thor-specific adapters and research notes. It does not
vendor or redistribute the Windows media, ReactOS release, Wine runtime,
Box64 package, exported Debian userspace, or compositor builds.

The recipes fetch/build these projects; their own licenses and notices apply:

- [win4wine](https://github.com/mikuta0407/win4wine): pinned in `thor/sources.json`.
  Its patch series, bridge helpers and extractors are used from that source.
- [Wine](https://www.winehq.org/): LGPL-2.1-or-later; pinned Wine 11.0 source and
  win4wine patches. Retain applicable sources/notices if redistributing builds.
- [Box64](https://github.com/ptitSeb/box64): MIT; pinned package/hash in the source manifest.
- [labwc](https://github.com/labwc/labwc): GPL-2.0-only.
- [wlroots](https://gitlab.freedesktop.org/wlroots/wlroots): MIT.
- [libsfdo](https://gitlab.freedesktop.org/vyivel/libsfdo): see its source license.
- [ReactOS](https://reactos.org/): GPL/LGPL and component-specific licenses;
  upstream extractor records the release/source and checks its SHA-256.
- Debian/Fedora, Xvfb, Python Xlib, grim, wlrctl, wlr-randr and other dependencies:
  each retains its own source/license. The private rootfs is not a distributable
  appliance from this repository.

Windows XP and Windows 7 resources are proprietary Microsoft assets supplied by
the user. Use only media you are entitled to use and comply with its license.
No license to Windows assets is conveyed by these scripts. Never publish extracted
assets, prefixes, activation material, or bundled Microsoft binaries here.

Source pins make the procedure inspectable; OS image tags/package repositories
are not frozen, so this is not a bit-for-bit reproducible-build claim.
