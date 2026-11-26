# KWin patch for three outputs in Plasma

[`0001-drm-test-color-offloading-with-the-pending-modeset.patch`](0001-drm-test-color-offloading-with-the-pending-modeset.patch)
fixes Plasma's endless "Modeset failed" with both panels and a DisplayPort display
(armada#943). The cause is in [../EXTERNAL.md](../EXTERNAL.md#three-outputs-2026-11-25).
It applies to KWin 6.8.2; master has the same code. Submitted upstream as
[plasma/kwin!10474](https://invent.kde.org/plasma/kwin/-/merge_requests/10474).

## On the device, until Armada's KWin carries it

Nothing in the image changes. As measured on 2026-11-25:

- `~/.local/lib/kwin-test/libkwin.so.6`: built with [`build-libkwin.sh`](build-libkwin.sh)
  from Fedora's `kwin-6.8.2-2.fc44` source RPM, Armada's two KWin patches and this one,
  then `strip --strip-debug`.
- `~/.local/lib/kwin-test/real/kwin_wayland`: a copy of `/usr/bin/kwin_wayland`. The
  image binary has `cap_sys_nice`, which makes the loader ignore `LD_LIBRARY_PATH`;
  the copy has no capability, so KWin runs without realtime priority. It must keep
  the name `kwin_wayland`, or Qt's platform plugin fails to load and KWin aborts.
- `~/.local/lib/kwin-test/bin/kwin_wayland`: [`kwin_wayland-wrapper`](kwin_wayland-wrapper).
  It runs the copy with the patched library only while the checksums of the image's
  `libkwin.so.6.8.2` and `kwin_wayland` match `image-kwin.sha256` (written at install
  time); after an image update it runs `/usr/bin/kwin_wayland`.
- `~/.config/systemd/user/plasma-kwin_wayland.service.d/kwin-test.conf`:
  [`plasma-kwin_wayland-kwin-test.conf`](plasma-kwin_wayland-kwin-test.conf) puts the
  wrapper first on `PATH`; `kwin_wayland_wrapper` looks up `kwin_wayland` there.

To undo, delete the drop-in and `~/.local/lib/kwin-test`, then start a new Plasma
session. Restarting `plasma-kwin_wayland.service` alone leaves Plasma half-restarted;
switch to Gaming Mode and back instead.
