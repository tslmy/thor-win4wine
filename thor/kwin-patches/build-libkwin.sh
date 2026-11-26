#!/bin/bash
# Build libkwin.so.6 for Armada KWin 6.8.2 in Docker on an arm64 Mac. Put next to
# this script a patches/ folder with Armada's two KWin patches (armada-packages,
# kwin/patches) and ours as 0003-drm-test-color-offloading-with-the-pending-modeset.patch.
# The build tree stays in the container; out/libkwin.so.6.8.2 is the result.
set -euxo pipefail
cd "$(dirname "$0")"
docker container inspect kwinb >/dev/null 2>&1 || docker run -d --name kwinb --platform linux/arm64 -v "$PWD/patches:/patches:ro" -v "$PWD/out:/out" registry.fedoraproject.org/fedora:44 sleep infinity
docker start kwinb
docker exec kwinb bash -euxo pipefail -c '
  cd /root
  if [ ! -e .deps-done ]; then
    dnf -y install rpm-build rpmdevtools koji "dnf-command(builddep)" >/dev/null
    rpmdev-setuptree
    [ -e kwin-6.8.2-2.fc44.src.rpm ] || koji download-build --arch=src kwin-6.8.2-2.fc44
    rpm -i kwin-6.8.2-2.fc44.src.rpm
    SPEC=/root/rpmbuild/SPECS/kwin.spec
    cp /patches/*.patch /root/rpmbuild/SOURCES/
    LAST=$(grep -nE "^(Patch|Source)[0-9]*:" "$SPEC" | tail -1 | cut -d: -f1)
    sed -i "${LAST}a Patch9001: 0001-input-panel-allow-configuring-output-by-env.patch\nPatch9002: 0002-x11-windowed-select-touch-events.patch\nPatch9003: 0003-drm-test-color-offloading-with-the-pending-modeset.patch" "$SPEC"
    dnf -y builddep "$SPEC" >/dev/null
    rpmbuild -bp --define "dist .fc44.armada" "$SPEC"
    touch .deps-done
  fi
  rpmbuild -bc --define "dist .fc44.armada" --define "_lto_cflags %{nil}" --define "debug_package %{nil}" /root/rpmbuild/SPECS/kwin.spec > /root/build.log 2>&1 || { tail -50 /root/build.log; exit 1; }
  cp -L $(find /root/rpmbuild/BUILD -name "libkwin.so.6.8.2" | head -1) /out/libkwin.so.6.8.2
'
ls -la out
