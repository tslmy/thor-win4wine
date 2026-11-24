#!/bin/bash
# Run inside the native build image as a non-root user; no DRM devices are mounted.
set -euo pipefail
work=$(mktemp -d)
export XDG_RUNTIME_DIR=$work/runtime
mkdir -m 700 "$XDG_RUNTIME_DIR" "$work/config"
cp /tools/labwc-rc.xml "$work/config/rc.xml"
cat > "$work/start" <<'START'
#!/bin/bash
set -e
trap 'kill -TERM "$LABWC_PID"' EXIT
python3 /tools/configure-win4wine-outputs.py --test-output HEADLESS-1 > "$XDG_RUNTIME_DIR/outputs.json"
touch "$XDG_RUNTIME_DIR/passed"
START
chmod +x "$work/start"
export WLR_BACKENDS=headless WLR_HEADLESS_OUTPUTS=1 WLR_RENDERER=pixman WLR_NO_HARDWARE_CURSORS=1
unset DISPLAY WAYLAND_DISPLAY
if ! timeout 20 /build/stage/opt/thor/labwc/bin/labwc -C "$work/config" -S "$work/start" > "$work/compositor.log" 2>&1; then
    cat "$work/compositor.log" >&2
    exit 1
fi
test -f "$XDG_RUNTIME_DIR/passed"
cat "$XDG_RUNTIME_DIR/outputs.json"
echo 'PASS: freshly built native compositor initializes a synthetic output without DRM.'
