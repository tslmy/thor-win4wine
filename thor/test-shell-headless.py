#!/usr/bin/env python3
"""Shared isolated native compositor test for all three shell variants."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
from Xlib import X, display, error

shell = sys.argv[1] if len(sys.argv) == 2 else ''
if shell not in ('xp', 'reactos', 'win7'):
    raise SystemExit('Usage: test-shell-headless.py xp|reactos|win7')
home = Path.home()
root = home / 'win4wine'
base = home / '.local/share/win4wine'
config = json.loads((home / f'.config/win4wine/{shell}-standalone.json').read_text())
sys.path.insert(0, str(root / 'session'))
from wineenv import SHELLS, environment
from dpi import prefix_dpi
try:
    subprocess.run([str(Path(config['wine']).with_name('wineserver')), '-w'],
                   env=dict(os.environ, WINEPREFIX=config['prefix']), check=True, timeout=2,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
except subprocess.TimeoutExpired:
    raise SystemExit('Selected prefix is active. Log off first; never share a prefix across displays.')


def wait(predicate, label):
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        try:
            value = predicate()
            if value:
                return value
        except (OSError, ValueError):
            pass
        time.sleep(.1)
    raise RuntimeError(f'Timed out waiting for {label}')


with tempfile.TemporaryDirectory(prefix='thor-shell-', dir=os.environ['XDG_RUNTIME_DIR']) as temp:
    work = Path(temp)
    runtime, ipc, state = (work / name for name in ('runtime', 'ipc', 'state'))
    for directory in (runtime, ipc, state):
        directory.mkdir(mode=0o700)
    test_config = dict(config, state=str(state), primary='HEADLESS-1', welcome_screen=False)
    path = work / 'session.json'
    path.write_text(json.dumps(test_config))
    started = work / 'display'
    startup = work / 'startup.sh'
    startup.write_text(f'#!/bin/sh\npython3 "{base}/tools/configure-win4wine-outputs.py" --test-output HEADLESS-1 || exit $?\n'
                       f'printf "%s\\n" "$DISPLAY" > "{started}"\n'
                       f'exec python3 "{root}/session/supervisor.py" --config "{path}"\n')
    startup.chmod(0o755)
    env = dict(os.environ, XDG_RUNTIME_DIR=str(runtime), WIN4WINE_IPC=str(ipc),
               WLR_BACKENDS='headless', WLR_HEADLESS_OUTPUTS='1', WLR_RENDERER='pixman',
               WLR_NO_HARDWARE_CURSORS='1', LANG='en_US.UTF-8', LC_ALL='en_US.UTF-8')
    for key in ('DISPLAY', 'WAYLAND_DISPLAY', 'XAUTHORITY', 'SESSION_MANAGER'):
        env.pop(key, None)
    with (Path(config['state']) / 'reproducible-headless.log').open('w') as log:
        process = subprocess.Popen(['dbus-run-session', '--', str(base / 'labwc/bin/labwc'), '-V',
            '-C', str(base / 'labwc-config'), '-S', str(startup)], env=env,
            stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        connection = None
        try:
            xdisplay = wait(lambda: started.read_text().strip(), 'Xwayland')
            wait(lambda: json.loads((state / 'status.json').read_text()).get('state') == 'xp-shell', 'shell')
            connection = display.Display(xdisplay)
            def windows(kind):
                result = []
                for window in connection.screen().root.query_tree().children:
                    try:
                        prop = window.get_full_property(connection.intern_atom('_WIN4WINE_CLASS'), X.AnyPropertyType)
                        if prop and bytes(prop.value).rstrip(b'\0').lower() == kind.lower().encode():
                            if window.get_attributes().map_state == X.IsViewable:
                                result.append(window)
                    except error.XError:
                        pass
                return result
            owner = {'xp': 'xp-explorer.exe', 'reactos': 'ros-explorer.exe', 'win7': 'w7-explorer.exe'}[shell]
            for kind in ('Progman', 'Shell_TrayWnd'):
                assert all(w.get_wm_class()[0] == owner for w in wait(lambda: windows(kind), kind))
            wine_env = environment(dict(env, DISPLAY=xdisplay, WINEDEBUG='-all'), test_config, SHELLS[shell])
            if shell != 'reactos':
                subprocess.run([config['wine'], str(base / 'tools/shell-ui-probe-x64.exe'), str(prefix_dpi(config['prefix']))],
                               env=wine_env, check=True, timeout=60, stdout=log, stderr=log)
            before = {w.id for w in windows('CabinetWClass')}
            command = {'xp': r'C:\xp\xp-explorer.exe', 'win7': r'C:\w7\w7-explorer.exe', 'reactos': 'explorer.exe'}[shell]
            subprocess.Popen([config['wine'], command, 'C:\\'], env=wine_env, stdout=log, stderr=log)
            wait(lambda: [w for w in windows('CabinetWClass') if w.id not in before], 'folder')
            wine_env['WIN4WINE_SESSION_REQUEST'] = 'Z:' + str(state / 'session-request').replace('/', '\\')
            subprocess.run([config['wine'], str(root / '.local/bridge/exit-windows-test.exe'), 'logoff'],
                           env=wine_env, check=True, timeout=60, stdout=log, stderr=log)
            wait(lambda: json.loads((state / 'status.json').read_text()).get('state') == 'stopped', 'logoff')
            print(f'PASS: {shell} desktop/taskbar ownership, folder and headless logoff')
        finally:
            if connection:
                try:
                    connection.close()
                except error.ConnectionClosedError:
                    pass
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            process.wait(timeout=20)
