#!/bin/bash
# Extract from the user's mounted XP disc; never modify the medium or commit its binaries.
set -euo pipefail
root=$(cd -- "$(dirname -- "$0")/.." && pwd)
media=${1:-/Volumes/GRTMPVOL_EN}
[[ -d $media ]] || { echo "Mounted XP medium not found: $media" >&2; exit 1; }
mkdir -p "$root/.build/xp/tmp"
exec docker run --rm --name thor-xp-extract --platform linux/arm64 \
    -v "$media:/media:ro" -v "$root/win4wine:/input:ro" \
    -v "$root/.build/xp:/output" -e TMPDIR=/output/tmp \
    fedora:44 /bin/bash -c '
        set -e
        dnf --setopt=install_weak_deps=False install -y python3 cabextract
        python3 /input/extract/extract.py /media /output/assets-xp
        tar -C /output -czf /output/assets-xp.tar.gz assets-xp
    '
