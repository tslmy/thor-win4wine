#!/usr/bin/env python3
"""Smoke-test native GLES2 rendering nested on the existing Wayland desktop."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

home = Path.home()
base = home / '.local/share/win4wine'
state = home / '.local/state/win4wine-standalone'
state.mkdir(parents=True, exist_ok=True)
manager = dict(line.split('=', 1) for line in subprocess.check_output(
    ['systemctl', '--user', 'show-environment'], text=True).splitlines() if '=' in line)
parent = manager.get('WAYLAND_DISPLAY')
if not parent:
    raise SystemExit('An existing Wayland session is required for the nested smoke test.')
parent_socket = Path(parent)
if not parent_socket.is_absolute():
    parent_socket = Path(os.environ['XDG_RUNTIME_DIR']) / parent_socket
with tempfile.TemporaryDirectory(prefix='win4wine-gles2-', dir=os.environ['XDG_RUNTIME_DIR']) as temp:
    work = Path(temp)
    runtime = work / 'runtime'
    runtime.mkdir(mode=0o700)
    ipc = work / 'ipc'
    ipc.mkdir(mode=0o700)
    output = state / 'test-gles2-outputs.json'
    startup = work / 'startup.sh'
    startup.write_text("#!/bin/sh\nsleep 1\nname=$(/usr/bin/wlr-randr --json | python3 -c 'import json,sys; print(json.load(sys.stdin)[0][\"name\"])')\n"
                       f'/usr/bin/wlr-randr --output "$name" --on\n'
                       f'/usr/bin/timeout 10s /usr/bin/wlr-randr --json > "{output}"\nsleep 1\n')
    startup.chmod(0o755)
    env = dict(os.environ, XDG_RUNTIME_DIR=str(runtime), WAYLAND_DISPLAY=str(parent_socket),
               WLR_BACKENDS='wayland', WLR_RENDERER='gles2', WIN4WINE_IPC=str(ipc))
    env.pop('DISPLAY', None)
    env.pop('XAUTHORITY', None)
    with (state / 'test-gles2.log').open('w') as log:
        subprocess.run([str(base / 'labwc/bin/labwc'), '-V', '-C', str(base / 'labwc-config'),
                        '-S', str(startup)], env=env, stdout=log, stderr=subprocess.STDOUT,
                       check=True, timeout=45)
    outputs = json.loads(output.read_text())
    assert any(o.get('enabled') for o in outputs), outputs
    print('PASS: native ARM64 labwc GLES2 renderer with an enabled nested Wayland output')
