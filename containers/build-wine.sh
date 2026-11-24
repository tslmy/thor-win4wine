#!/bin/bash
# Runs only in the disposable x86-64 build container, not on Armada.
set -euo pipefail
jobs=${JOBS:-6}
mkdir -p /build/source /build/wine-out /build/wine-install /build/bridge
source /input/wine/upstream.env
if [[ ! -f /build/source/.thor-source ]]; then
    [[ -z $(ls -A /build/source) ]] || { echo 'Incomplete source; inspect /build/source before retrying.' >&2; exit 1; }
    curl --fail --location --retry 3 "https://codeload.github.com/wine-mirror/wine/tar.gz/$WINE_COMMIT" -o /build/wine-source.tar.gz
    expected=$(python3 -c 'import json; print(json.load(open("/tools/sources.json"))["wine_source_sha256"])')
    echo "$expected  /build/wine-source.tar.gz" | sha256sum --check
    sha256sum /build/wine-source.tar.gz > /build/wine-source.sha256
    tar -xzf /build/wine-source.tar.gz --strip-components=1 -C /build/source
    while IFS= read -r name; do
        [[ -z $name || $name == \#* ]] && continue
        patch --batch --forward -d /build/source -p1 < "/input/wine/patches/$name"
    done < /input/wine/patches/series
    python3 /input/wine/patch-state.py --digest /input/wine/patches > /build/source/.thor-source
fi
digest=$(python3 /input/wine/patch-state.py --digest /input/wine/patches)
expected=$(python3 -c 'import json; print(json.load(open("/tools/sources.json"))["wine_patches_sha256"])')
[[ $digest == "$expected" ]] || { echo 'Unexpected Wine patch digest.' >&2; exit 1; }
[[ $(cat /build/source/.thor-source) == "$digest" ]] || { echo 'Patch inputs changed; use a new build directory.' >&2; exit 1; }
cd /build/wine-out
extra=()
for v in {24..43}; do extra+=("--disable-d3dx9_$v"); done
for v in {33..43}; do extra+=("--disable-d3dx10_$v"); done
for v in {33..42} 46 47; do extra+=("--disable-d3dcompiler_$v"); done
/build/source/configure --prefix=/build/wine-install --enable-archs=i386,x86_64 \
    --without-wayland --disable-tests "${extra[@]}"
make -j"$jobs"
make install
for arch in i386 x86_64; do
    cp "/build/wine-install/lib/wine/$arch-windows/comctl32_v6.dll" \
       "/build/wine-install/lib/wine/$arch-windows/win4wine-controls.dll"
done
echo "$digest" > /build/wine-install/win4wine-patches
# Build helpers in a throwaway copy: the source mount remains read-only.
mkdir -p /build/helpers
cp -a /input/. /build/helpers/
bash /build/helpers/bridge-wm/build.sh
cp -a /build/helpers/.local/bridge/. /build/bridge/
i686-w64-mingw32-gcc -O2 -municode /input/tests/exit-windows.c -o /build/bridge/exit-windows-test.exe -luser32
x86_64-w64-mingw32-gcc -O2 -Wall -Wextra -Werror /tools/shell-ui-probe.c \
    -o /build/bridge/shell-ui-probe-x64.exe -luxtheme -ldwmapi -lgdi32 -luser32
tar -C /build -czf /build/wine-runtime.tar.gz wine-install bridge
echo 'Wine and bridge built. Rootfs is exported separately by the host recipe.'
