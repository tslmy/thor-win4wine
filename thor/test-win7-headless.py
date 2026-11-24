#!/usr/bin/env python3
"""Validate the x64 Win7 shell in a private native compositor and bus."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
from Xlib import X, display, error

home = Path.home()
root = home / 'win4wine'
base = home / '.local/share/win4wine'
config = json.loads((home / '.config/win4wine/win7-standalone.json').read_text())
sys.path.insert(0, str(root / 'session'))
from dpi import prefix_dpi
from wineenv import SHELLS, environment
expected_dpi = prefix_dpi(config['prefix'])
try:
    subprocess.run([str(Path(config['wine']).with_name('wineserver')), '-w'],
                   env=dict(os.environ, WINEPREFIX=config['prefix']), check=True, timeout=2,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
except subprocess.TimeoutExpired:
    raise SystemExit('Win7 prefix is active; do not share it between displays.')

def wait(predicate, label, timeout=120):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        try:
            found = predicate()
            if found:
                return found
        except (OSError, ValueError):
            pass
        time.sleep(.1)
    raise AssertionError(label)

with tempfile.TemporaryDirectory(prefix='win4wine-w7-test-', dir=os.environ['XDG_RUNTIME_DIR']) as temp:
    work = Path(temp)
    runtime, ipc, state = work / 'runtime', work / 'ipc', work / 'state'
    for p in (runtime, ipc, state): p.mkdir(mode=0o700)
    config.update(state=str(state), primary='HEADLESS-1', welcome_screen=False)
    test_config = work / 'session.json'
    test_config.write_text(json.dumps(config))
    started = work / 'display'
    startup = work / 'startup.sh'
    startup.write_text(f'#!/bin/sh\npython3 "{base}/tools/configure-win4wine-outputs.py" --test-output HEADLESS-1 || exit $?\n'
                       f'printf "%s\\n" "$DISPLAY" > "{started}"\n'
                       f'exec python3 "{root}/session/supervisor.py" --config "{test_config}"\n')
    startup.chmod(0o755)
    env = dict(os.environ, XDG_RUNTIME_DIR=str(runtime), WIN4WINE_IPC=str(ipc),
               WLR_BACKENDS='headless', WLR_HEADLESS_OUTPUTS='1', WLR_RENDERER='pixman',
               WLR_NO_HARDWARE_CURSORS='1', XDG_CURRENT_DESKTOP='Win7-Shell', XDG_SESSION_TYPE='wayland',
               LANG='en_US.UTF-8', LC_ALL='en_US.UTF-8')
    for name in ('DISPLAY', 'WAYLAND_DISPLAY', 'XAUTHORITY', 'SESSION_MANAGER'): env.pop(name, None)
    with (home / '.local/state/win4wine-win7/headless-test.log').open('w') as log:
        process = subprocess.Popen(['dbus-run-session', '--', str(base / 'labwc/bin/labwc'), '-V',
            '-C', str(base / 'labwc-config'), '-S', str(startup)], env=env,
            stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        d = None
        try:
            xdisplay = wait(lambda: started.read_text().strip(), 'headless display')
            wait(lambda: json.loads((state / 'status.json').read_text()).get('state') == 'xp-shell', 'Win7 readiness')
            d = display.Display(xdisplay)
            def windows(kind):
                result = []
                for w in d.screen().root.query_tree().children:
                    try:
                        p = w.get_full_property(d.intern_atom('_WIN4WINE_CLASS'), X.AnyPropertyType)
                        if p and bytes(p.value).rstrip(b'\0').lower() == kind.lower().encode():
                            if w.get_attributes().map_state == X.IsViewable: result.append(w)
                    except error.XError: pass
                return result
            for kind in ('Progman', 'Shell_TrayWnd'):
                matches = wait(lambda: windows(kind), kind)
                assert all(w.get_wm_class()[0] == 'w7-explorer.exe' for w in matches), kind
            print('PASS: x64 Windows 7 Explorer owns desktop/taskbar', flush=True)
            wine_env = environment(dict(env, DISPLAY=xdisplay, WINEDEBUG='-all', WIN4WINE_COMPOSITED='1'), config, SHELLS['win7'])
            subprocess.run([config['wine'], str(base / 'tools/shell-ui-probe-x64.exe'), str(expected_dpi)],
                           env=wine_env, check=True, timeout=60)
            before = {w.id for w in windows('CabinetWClass')}
            subprocess.Popen([config['wine'], r'C:\w7\w7-explorer.exe', 'C:\\'], env=wine_env, stdout=log, stderr=subprocess.STDOUT)
            wait(lambda: [w for w in windows('CabinetWClass') if w.id not in before], 'Win7 folder')
            print('PASS: Windows 7 folder window', flush=True)
            wine_env['WIN4WINE_SESSION_REQUEST'] = 'Z:' + str(state / 'session-request').replace('/', '\\')
            subprocess.run([config['wine'], str(root / '.local/bridge/exit-windows-test.exe'), 'logoff'],
                           env=wine_env, check=True, timeout=60)
            wait(lambda: json.loads((state / 'status.json').read_text()).get('state') == 'stopped', 'Win7 logoff')
            print('PASS: Win7 logoff ends isolated session', flush=True)
        finally:
            if d:
                try: d.close()
                except error.ConnectionClosedError: pass
            try: os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError: pass
            process.wait(timeout=20)
