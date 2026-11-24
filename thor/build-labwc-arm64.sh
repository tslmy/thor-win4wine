#!/bin/bash
# Native ARM64 build on the Mac's Docker Linux VM; never alters the Thor OS.
set -euo pipefail
root=$(cd -- "$(dirname -- "$0")/.." && pwd)
mkdir -p "$root/.build/labwc"
if docker container inspect thor-labwc-build >/dev/null 2>&1; then
    [[ $(docker inspect --format '{{.State.Running}}' thor-labwc-build) == false ]] || {
        echo 'The native labwc build is already running.' >&2
        exit 1
    }
    exec docker start -a thor-labwc-build
fi
exec docker run --name thor-labwc-build --platform linux/arm64 \
    -v "$root/win4wine:/input:ro" -v "$root/thor:/tools:ro" \
    -v "$root/.build/labwc:/build" \
    fedora:44 /bin/bash /tools/build-labwc-inner.sh
