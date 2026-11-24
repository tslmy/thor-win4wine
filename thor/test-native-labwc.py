#!/usr/bin/env python3
"""Run upstream compositor assertions on an isolated Xvfb, not Plasma's root."""
import os
from pathlib import Path
import runpy
import signal
import subprocess
import time
from Xlib import display

home = Path.home()
base = home / '.local/share/win4wine'
state = home / '.local/state/win4wine-standalone'
state.mkdir(parents=True, exist_ok=True)
number = next((n for n in range(41, 61) if not Path(f'/tmp/.X11-unix/X{n}').exists()), None)
if number is None:
    raise SystemExit('No free test X display.')
env = dict(os.environ, FEX_ROOTFS=str(base / 'rootfs'), DISPLAY=f':{number}',
           LABWC=str(base / 'labwc/bin/labwc'))
env.pop('XAUTHORITY', None)
env.pop('WAYLAND_DISPLAY', None)
os.environ.clear()
os.environ.update(env)
with (state / 'test-xvfb.log').open('w') as log:
    xvfb = subprocess.Popen([str(base / 'labwc/bin/Xvfb'), f':{number}',
                            '-screen', '0', '1280x800x24', '-nolisten', 'tcp', '-ac', '-noreset'],
                           env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    try:
        for _ in range(100):
            if xvfb.poll() is not None:
                raise RuntimeError(f'Xvfb exited; see {state / "test-xvfb.log"}')
            try:
                connection = display.Display()
                connection.close()
                break
            except Exception:
                time.sleep(.1)
        else:
            raise RuntimeError('Test Xvfb did not become ready.')
        code = runpy.run_path(str(home / 'win4wine/tests/wayland_compositor.py'))
        result = code['main']()
        if result:
            raise SystemExit(result)
        print('PASS: native ARM64 labwc compositor assertions on isolated Xvfb')
    finally:
        try:
            os.killpg(xvfb.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        xvfb.wait(timeout=20)
