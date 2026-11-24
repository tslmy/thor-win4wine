#!/usr/bin/env python3
"""Non-destructive checks of the actual standalone desktop and a Linux window."""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from Xlib import X, display, error, protocol

home = Path.home()
root = home / 'win4wine'
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--shell', choices=('reactos', 'xp'), default='reactos')
args = parser.parse_args()
config = json.loads((home / f'.config/win4wine/{args.shell}-standalone.json').read_text())
owner = 'xp-explorer.exe' if args.shell == 'xp' else 'ros-explorer.exe'
label = 'Windows XP' if args.shell == 'xp' else 'ReactOS'
manager = dict(line.split('=', 1) for line in subprocess.check_output(
    ['systemctl', '--user', 'show-environment'], text=True).splitlines() if '=' in line)
for name in ('DISPLAY', 'WAYLAND_DISPLAY', 'XAUTHORITY', 'XDG_CURRENT_DESKTOP'):
    if name in manager:
        os.environ[name] = manager[name]
    else:
        os.environ.pop(name, None)
sys.path.insert(0, str(root / 'session'))
from wineenv import SHELLS, environment
env = environment(dict(os.environ, WINEDEBUG='-all'), config, SHELLS[args.shell])
state = json.loads((Path(config['state']) / 'status.json').read_text())
assert state['state'] == 'xp-shell', state
for name in ('plasmashell', 'kwin_wayland', 'steam'):
    assert subprocess.run(['pgrep', '-x', name], stdout=subprocess.DEVNULL).returncode != 0, name
d = display.Display()
atom = d.intern_atom

def wait(predicate, label, timeout=45):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        found = predicate()
        if found:
            return found
        time.sleep(.1)
    raise AssertionError(label)

def windows(kind):
    found = []
    for window in d.screen().root.query_tree().children:
        try:
            p = window.get_full_property(atom('_WIN4WINE_CLASS'), X.AnyPropertyType)
            if p and bytes(p.value).rstrip(b'\0').decode().lower() == kind.lower():
                if window.get_attributes().map_state == X.IsViewable:
                    found.append(window)
        except error.XError:
            pass
    return found

for kind in ('Progman', 'Shell_TrayWnd'):
    matches = wait(lambda: windows(kind), kind)
    assert all(w.get_wm_class()[0] == owner for w in matches), kind
print(f'PASS: {label} desktop/taskbar, no Plasma/KWin/Steam shell', flush=True)
before = {w.id for w in windows('CabinetWClass')}
command = r'C:\xp\xp-explorer.exe' if args.shell == 'xp' else 'explorer.exe'
subprocess.Popen([config['wine'], command, 'C:\\'], env=env,
                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
opened = wait(lambda: [w for w in windows('CabinetWClass') if w.id not in before], f'{label} folder')
for w in opened:
    assert w.get_wm_class()[0] == owner
    w.send_event(protocol.event.ClientMessage(window=w, client_type=atom('WM_PROTOCOLS'),
        data=(32, [atom('WM_DELETE_WINDOW'), X.CurrentTime, 0, 0, 0])))
d.flush()
print(f'PASS: folder requests open in {label} Explorer', flush=True)
pid = int(subprocess.check_output(['pgrep', '-u', str(os.getuid()), '-x', 'labwc'], text=True).strip())
labwc_env = dict(item.split(b'=', 1) for item in Path(f'/proc/{pid}/environ').read_bytes().split(b'\0') if b'=' in item)
ipc = Path(labwc_env[b'WIN4WINE_IPC'].decode())
table = ipc / 'windows.tsv'
baseline = set(table.read_text().splitlines()) if table.exists() else set()
with (Path(config['state']) / 'linux-window-probe.log').open('w') as log:
    terminal = subprocess.Popen(['/usr/bin/konsole', '--separate', '--nofork', '-p',
                                 'tabtitle=Standalone probe', '-e', '/usr/bin/sleep', '60'],
                                env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    try:
        added = wait(lambda: {line for line in set(table.read_text().splitlines()) - baseline
                             if 'Konsole' in line or 'Standalone probe' in line} if table.exists() else set(),
                     'Linux window in shell IPC', timeout=30)
        assert any('Konsole' in line or 'Standalone probe' in line for line in added), added
        print('PASS: native Linux terminal integrated into the shell window list', flush=True)
    finally:
        try:
            os.killpg(terminal.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        terminal.wait(timeout=15)
d.close()
