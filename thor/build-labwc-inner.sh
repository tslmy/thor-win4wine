#!/bin/bash
set -euo pipefail
if [[ ${THOR_SKIP_PACKAGES:-0} != 1 ]]; then
dnf install -y gcc gcc-c++ meson ninja-build patch curl pkgconf-pkg-config python3 \
    wayland-devel wayland-protocols-devel libxkbcommon-devel libxml2-devel \
    cairo-devel pango-devel glib2-devel libinput-devel pixman-devel libpng-devel \
    librsvg2-devel libdrm-devel mesa-libgbm-devel mesa-libEGL-devel mesa-libGLES-devel \
    libseat-devel libdisplay-info-devel libliftoff-devel lcms2-devel hwdata hwdata-devel \
    libxcb-devel xcb-util-errors-devel xcb-util-wm-devel xcb-util-renderutil-devel \
    xorg-x11-server-Xwayland-devel xorg-x11-server-Xvfb
fi
prefix=${THOR_LABWC_PREFIX:-/var/home/armada/.local/share/win4wine/labwc}
source /input/wayland/upstream.env
fetch() {
    local name=$1 url=$2 target=$3
    if [[ ! -d "$target" ]]; then
        curl --fail --location --retry 3 "$url" -o "/build/$name.tar.gz"
        mkdir -p "$target"
        tar -xzf "/build/$name.tar.gz" --strip-components=1 -C "$target"
        sha256sum "/build/$name.tar.gz" >> /build/source-sha256.txt
    fi
}
src=/build/source
fetch labwc "https://codeload.github.com/labwc/labwc/tar.gz/$LABWC_COMMIT" "$src"
fetch wlroots "https://gitlab.freedesktop.org/wlroots/wlroots/-/archive/$WLROOTS_COMMIT/wlroots-$WLROOTS_COMMIT.tar.gz" "$src/subprojects/wlroots"
fetch libsfdo "https://gitlab.freedesktop.org/vyivel/libsfdo/-/archive/$LIBSFDO_COMMIT/libsfdo-$LIBSFDO_COMMIT.tar.gz" "$src/subprojects/libsfdo"
if [[ -f /tools/native-source-sha256.txt ]]; then
    (cd /build && sha256sum --check /tools/native-source-sha256.txt)
fi
apply_series() {
    local target=$1 series=$2
    if [[ ! -f "$target/.thor-patched" ]]; then
        while IFS= read -r name; do
            [[ -z $name || $name == \#* ]] && continue
            patch --batch --forward -d "$target" -p1 < "$series/$name"
        done < "$series/series"
        touch "$target/.thor-patched"
    fi
}
apply_series "$src" /input/wayland/patches/labwc
apply_series "$src/subprojects/wlroots" /input/wayland/patches/wlroots
setup=()
[[ ! -f /build/out/build.ninja ]] || setup+=(--reconfigure)
meson setup "${setup[@]}" /build/out "$src" --prefix="$prefix" \
    --libdir=lib --buildtype=release \
    --force-fallback-for=wlroots-0.18,libsfdo-basedir,libsfdo-desktop,libsfdo-icon \
    -Dxwayland=enabled -Dman-pages=disabled -Dwlroots:werror=false \
    -Dwlroots:xwayland=enabled -Dwlroots:backends=drm,libinput,x11 \
    -Dwlroots:renderers=gles2
ninja -C /build/out -j6
DESTDIR=/build/stage ninja -C /build/out install
cp /usr/bin/Xvfb "/build/stage$prefix/bin/Xvfb"
python3 /input/wine/patch-state.py --digest /input/wayland/patches/labwc /input/wayland/patches/wlroots \
    > "/build/stage$prefix/win4wine-patches"
cp /build/source-sha256.txt "/build/stage$prefix/"
ldd "/build/stage$prefix/bin/labwc"
tar -C "/build/stage$(dirname "$prefix")" -czf /build/labwc-arm64.tar.gz "$(basename "$prefix")"
