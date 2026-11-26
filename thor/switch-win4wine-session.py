#!/usr/bin/env python3
"""Independent root worker for a guarded switch between the registered shells."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

if os.geteuid() != 0:
    raise SystemExit('Run through win4wine-switch (the worker must survive logout).')
variant = sys.argv[1] if len(sys.argv) == 2 else ''
choices = {
    'win7': ('armada-win7.desktop', 'win7-standalone.json', 'win4wine-win7', 'win7-shell.json', 'Win7-Shell'),
    'xp': ('armada-xp.desktop', 'xp-standalone.json', 'win4wine-xp', 'xp-shell.json', 'XP-Shell'),
    'reactos': ('armada-reactos.desktop', 'reactos-standalone.json', 'win4wine-standalone', 'reactos-shell.json', 'ReactOS'),
}
if variant not in choices:
    raise SystemExit('Usage: switch-win4wine-session.py xp|reactos|win7')
session, filename, state_dir, marker, identity = choices[variant]
home = Path('/var/home/armada')
config = json.loads((home / '.config/win4wine' / filename).read_text())
if not (Path(config['prefix']) / marker).is_file():
    raise SystemExit('The selected shell prefix is incomplete; refusing to switch.')
manager = subprocess.check_output(['runuser', '-u', 'armada', '--', '/usr/bin/env',
    'XDG_RUNTIME_DIR=/run/user/1000', 'DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus',
    'systemctl', '--user', 'show-environment'], text=True)
if f'XDG_CURRENT_DESKTOP={identity}\n' in manager:
    print('That shell is already the active desktop; no switch needed.')
    raise SystemExit(0)
def xreal_or_unknown_connected():
    """armada#953: a DP disable after a failed link training resets the SoC. XREAL
    glasses (EDID maker MRG, 0x3647) often fail their first training and re-assert
    hot-plug while SDDM restarts. An unreadable EDID counts as glasses."""
    for dp in Path('/sys/class/drm').glob('card*-DP-*'):
        try:
            if (dp / 'status').read_text().strip() != 'connected':
                continue
            edid = (dp / 'edid').read_bytes()
        except OSError:
            return True
        if len(edid) < 10 or edid[8:10] == bytes([0x36, 0x47]):
            return True
    return False


if xreal_or_unknown_connected():
    raise SystemExit('Unplug the XREAL glasses first: with them connected, a shell switch can reset the Thor (armada#953). Other monitors can stay connected.')
control = '/etc/win4wine/standalone-test-control.py'
started = time.time()
subprocess.run(['python3', control, 'begin', '--session', session], check=True)
deadline = time.monotonic() + 180
stable_since = None
try:
    while time.monotonic() < deadline:
        try:
            state = json.loads((home / '.local/state' / state_dir / 'status.json').read_text())
            ready = state.get('state') == 'xp-shell' and state.get('time', 0) >= started
        except (OSError, ValueError):
            ready = False
        if ready:
            stable_since = stable_since or time.monotonic()
            if time.monotonic() - stable_since >= 10:
                subprocess.run(['python3', control, 'accept'], check=True)
                print(f'{variant} shell is ready. Current session kept; boot defaults unchanged.')
                break
        else:
            stable_since = None
        time.sleep(.5)
    else:
        raise RuntimeError('The selected shell did not become ready within three minutes.')
except BaseException:
    subprocess.run(['python3', control, 'rollback'], check=False)
    raise
