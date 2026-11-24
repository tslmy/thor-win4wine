#!/usr/bin/env python3
"""Exercise XP/Luna in native headless labwc without closing the live ReactOS desktop."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
from Xlib import X, display, error, protocol

home = Path.home()
root = home / 'win4wine'
base = home / '.local/share/win4wine'
config = json.loads((home / '.config/win4wine/xp-standalone.json').read_text())
sys.path.insert(0, str(root / 'session'))
from dpi import prefix_dpi
expected_dpi = prefix_dpi(config['prefix'])
try:
    subprocess.run([str(Path(config['wine']).with_name('wineserver')), '-w'],
                   env=dict(os.environ, WINEPREFIX=config['prefix']), check=True, timeout=2,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
except subprocess.TimeoutExpired:
    raise SystemExit('Do not run a second headless desktop in an active XP prefix. Log off XP first.')
logpath = home / '.local/state/win4wine-xp/headless-test.log'

def wait(predicate, label, timeout=90):
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

with tempfile.TemporaryDirectory(prefix='win4wine-xp-test-', dir=os.environ['XDG_RUNTIME_DIR']) as temp:
    work = Path(temp)
    runtime, ipc, state = work / 'runtime', work / 'ipc', work / 'state'
    for p in (runtime, ipc, state):
        p.mkdir(mode=0o700)
    config['state'] = str(state)
    config['primary'] = 'HEADLESS-1'
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
               XDG_CURRENT_DESKTOP='XP-Shell', XDG_SESSION_TYPE='wayland', LANG='en_US.UTF-8', LC_ALL='en_US.UTF-8')
    for name in ('DISPLAY', 'WAYLAND_DISPLAY', 'XAUTHORITY', 'SESSION_MANAGER'):
        env.pop(name, None)
    with logpath.open('w') as log:
        compositor = subprocess.Popen(['dbus-run-session', '--', str(base / 'labwc/bin/labwc'),
            '-V', '-C', str(base / 'labwc-config'), '-S', str(startup)], env=env,
            stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        d = None
        try:
            xdisplay = wait(lambda: started.read_text().strip(), 'headless Xwayland startup')
            wait(lambda: json.loads((state / 'status.json').read_text()).get('state') == 'xp-shell', 'XP shell readiness')
            d = display.Display(xdisplay)
            atom = d.intern_atom
            def windows(kind):
                found = []
                for window in d.screen().root.query_tree().children:
                    try:
                        p = window.get_full_property(atom('_WIN4WINE_CLASS'), X.AnyPropertyType)
                        if p and bytes(p.value).rstrip(b'\0').lower() == kind.lower().encode():
                            if window.get_attributes().map_state == X.IsViewable:
                                found.append(window)
                    except error.XError:
                        pass
                return found
            for kind in ('Progman', 'Shell_TrayWnd'):
                matches = wait(lambda: windows(kind), kind)
                assert all(w.get_wm_class()[0] == 'xp-explorer.exe' for w in matches), kind
            print('PASS: genuine XP explorer owns desktop and taskbar', flush=True)
            wine_env = dict(env, DISPLAY=xdisplay, WINEPREFIX=config['prefix'], WINEDEBUG='-all', WIN4WINE_EXTERNAL_SHELL='1')
            wine_env.pop('WIN4WINE_IPC', None)
            subprocess.run([config['wine'], str(root / '.local/bridge/standalone-display-test.exe'), str(expected_dpi), '1'],
                           env=wine_env, check=True, timeout=60)
            print(f'PASS: XP Luna theme and Win32 {expected_dpi}-DPI APIs', flush=True)
            before = {w.id for w in windows('CabinetWClass')}
            subprocess.Popen([config['wine'], r'C:\xp\xp-explorer.exe', 'C:\\'], env=wine_env,
                             stdout=log, stderr=subprocess.STDOUT)
            opened = wait(lambda: [w for w in windows('CabinetWClass') if w.id not in before], 'XP folder window')
            for w in opened:
                assert w.get_wm_class()[0] == 'xp-explorer.exe'
                w.send_event(protocol.event.ClientMessage(window=w, client_type=atom('WM_PROTOCOLS'),
                    data=(32, [atom('WM_DELETE_WINDOW'), X.CurrentTime, 0, 0, 0])))
            d.flush()
            print('PASS: folders open in the XP shell', flush=True)
            wine_env['WIN4WINE_SESSION_REQUEST'] = 'Z:' + str(state / 'session-request').replace('/', '\\')
            subprocess.run([config['wine'], str(root / '.local/bridge/exit-windows-test.exe'), 'logoff'],
                           env=wine_env, check=True, timeout=60)
            wait(lambda: json.loads((state / 'status.json').read_text()).get('state') == 'stopped', 'XP logoff')
            assert (state / 'session-request').read_text().strip() == 'logoff'
            print('PASS: XP logoff ends the test session', flush=True)
        finally:
            if d:
                try:
                    d.close()
                except error.ConnectionClosedError:
                    pass
            try:
                os.killpg(compositor.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            compositor.wait(timeout=20)
