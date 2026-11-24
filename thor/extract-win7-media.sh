#!/bin/bash
set -euo pipefail
root=$(cd -- "$(dirname -- "$0")/.." && pwd)
iso=${1:-$HOME/Downloads/Windows 7 SP1 64-Bit DVD.iso}
[[ -f $iso ]] || { echo "Win7 ISO not found: $iso" >&2; exit 1; }
mkdir -p "$root/.build/win7/tmp"
exec docker run --rm --name thor-win7-extract --platform linux/arm64 \
    -v "$iso:/media/win7.iso:ro" -v "$root/win4wine:/input:ro" \
    -v "$root/.build/win7:/output" -e TMPDIR=/output/tmp \
    fedora:44 /bin/bash -c '
        set -e
        dnf --setopt=install_weak_deps=False install -y python3 7zip
        if ! command -v 7z >/dev/null; then ln -s "$(command -v 7zz)" /usr/local/bin/7z; fi
        python3 /input/extract/win7.py /media/win7.iso /output/assets-win7
        tar -C /output -czf /output/assets-win7.tar.gz assets-win7
    '
