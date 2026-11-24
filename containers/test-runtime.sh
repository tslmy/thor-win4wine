#!/bin/bash
# Fresh Fedora ARM64 account test. No DRM, SSH, SDDM or host home is available.
set -euo pipefail
report_failure() {
    result=$?
    if [[ $result != 0 && -d /home/player/.local/state ]]; then
        find /home/player/.local/state -type f -name '*.log' -print -exec tail -n 60 {} \;
    fi
}
trap report_failure EXIT
mkdir -p /stage /run/user/2001
chmod 700 /run/user/2001
chown player:player /run/user/2001
ln -s /artifacts/win4wine /stage/source
ln -s /tools /stage/thor
for name in wine-runtime.tar.gz rootfs.tar box64.tar.gz; do
    ln -s "/artifacts/wine/$name" "/stage/$name"
done
for name in labwc-arm64.tar.gz native-support.tar.gz; do
    ln -s "/artifacts/native/$name" "/stage/$name"
done
runuser -u player -- env XDG_RUNTIME_DIR=/run/user/2001 \
    python3 /tools/install-user.py /stage
runuser -u player -- mkdir -p /home/player/.local/state/thor-bootstrap
runuser -u player -- cp /artifacts/native/assets-reactos.tar.gz /home/player/.local/state/thor-bootstrap/
runuser -u player -- env XDG_RUNTIME_DIR=/run/user/2001 \
    PYTHONPATH=/home/player/.local/share/win4wine/python \
    LD_LIBRARY_PATH=/home/player/.local/share/win4wine/labwc/lib \
    PATH=/home/player/.local/bin:/usr/bin:/bin \
    python3 /tools/prepare-shell.py reactos
runuser -u player -- env XDG_RUNTIME_DIR=/run/user/2001 \
    PYTHONPATH=/home/player/.local/share/win4wine/python \
    LD_LIBRARY_PATH=/home/player/.local/share/win4wine/labwc/lib \
    PATH=/home/player/.local/bin:/usr/bin:/bin \
    python3 /tools/test-shell-headless.py reactos
echo 'PASS: fresh-account install, Box64/Wine ReactOS prefix, cursors and headless session in ARM64 Fedora.'
