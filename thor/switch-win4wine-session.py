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
    'xp': ('armada-xp.desktop', 'xp-standalone.json', 'win4wine-xp', 'xp-shell.json', 'XP-Shell'),
    'reactos': ('armada-reactos.desktop', 'reactos-standalone.json', 'win4wine-standalone', 'reactos-shell.json', 'ReactOS'),
}
if variant not in choices:
    raise SystemExit('Usage: switch-win4wine-session.py xp|reactos')
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
if any(p.read_text().strip() == 'connected' for p in Path('/sys/class/drm').glob('card*-DP-*/status')):
    raise SystemExit('Disconnect the external monitor before switching. Multi-output switching is gated after a display-driver failure and unexpected reboot.')
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
