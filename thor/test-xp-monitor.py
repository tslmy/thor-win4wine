#!/usr/bin/env python3
"""Open a dedicated XP test folder and move its real Explorer window to an output."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from Xlib import X, display, error
from Xlib.ext import randr

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('output', choices=('DP-1', 'DSI-1'))
args = parser.parse_args()
home = Path.home()
root = home / 'win4wine'
config = json.loads((home / '.config/win4wine/xp-standalone.json').read_text())
manager = dict(line.split('=', 1) for line in subprocess.check_output(
    ['systemctl', '--user', 'show-environment'], text=True).splitlines() if '=' in line)
for name in ('DISPLAY', 'WAYLAND_DISPLAY', 'XAUTHORITY'):
    if name in manager:
        os.environ[name] = manager[name]
    else:
        os.environ.pop(name, None)
sys.path.insert(0, str(root / 'session'))
from wineenv import SHELLS, environment
env = environment(dict(os.environ, WINEDEBUG='-all'), config, SHELLS['xp'])
d = display.Display()
resources = d.screen().root.xrandr_get_screen_resources_current()
output = None
for ident in resources.outputs:
    info = d.xrandr_get_output_info(ident, resources.config_timestamp)
    name = info.name.decode() if isinstance(info.name, bytes) else info.name
    if name == args.output and info.crtc:
        output = d.xrandr_get_crtc_info(info.crtc, resources.config_timestamp)
        break
if output is None:
    raise SystemExit(f'{args.output} is not connected/enabled.')

def folders():
    result = {}
    for w in d.screen().root.query_tree().children:
        try:
            p = w.get_full_property(d.intern_atom('_WIN4WINE_CLASS'), X.AnyPropertyType)
            if p and bytes(p.value).rstrip(b'\0') in (b'CabinetWClass', b'ExploreWClass'):
                hwnd = w.get_full_property(d.intern_atom('_WIN4WINE_HWND'), X.AnyPropertyType)
                if hwnd and w.get_attributes().map_state == X.IsViewable:
                    result[w.id] = (w, int(hwnd.value[0]))
        except error.XError:
            pass
    return result

before = set(folders())
label = 'Display test ' + args.output
(Path(config['prefix']) / 'drive_c/xp' / label).mkdir(exist_ok=True)
subprocess.Popen([config['wine'], r'C:\xp\xp-explorer.exe', 'C:\\xp\\' + label], env=env,
                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
end = time.monotonic() + 45
while time.monotonic() < end:
    added = {ident: value for ident, value in folders().items() if ident not in before}
    if added:
        break
    time.sleep(.1)
else:
    raise RuntimeError('The diagnostic XP folder did not open a new window.')
window, hwnd = next(iter(added.values()))
x, y = output.x + 40, output.y + 40
width, height = min(1100, output.width - 80), min(700, output.height - 80)
subprocess.run([config['wine'], str(home / '.local/share/win4wine/tools/move-xp-window.exe'),
                f'{hwnd:x}', str(x), str(y), str(width), str(height)], env=env, check=True, timeout=45)
time.sleep(.5)
position = window.translate_coords(d.screen().root, 0, 0)
print(f'Actual XP folder on {args.output}: global {-position.x},{-position.y}', flush=True)
d.close()
