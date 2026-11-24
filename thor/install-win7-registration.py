#!/usr/bin/env python3
"""Register the isolated Win7 session, without changing boot defaults."""
import hashlib
import json
import os
from pathlib import Path
import subprocess

if os.geteuid() != 0: raise SystemExit('Run with sudo after validation.')
home = Path('/var/home/armada')
base = home / '.local/share/win4wine'
config = json.loads((home / '.config/win4wine/win7-standalone.json').read_text())
if config.get('shell') != 'win7' or not (Path(config['prefix']) / 'win7-shell.json').is_file():
    raise SystemExit('The Win7 prefix is incomplete.')
for p in (home / '.local/bin/win7-standalone-session', base / 'tools/win7-standalone-start', base / 'labwc/bin/labwc'):
    if not p.is_file() or not os.access(p, os.X_OK): raise SystemExit(f'Missing executable: {p}')
target = Path('/etc/win4wine/wayland-sessions/armada-win7.desktop')
data = (base / 'tools/armada-win7.desktop').read_bytes()
if target.exists() and target.read_bytes() != data: raise SystemExit('Refusing different existing Win7 session entry.')
target.write_bytes(data)
target.chmod(0o644)
subprocess.run(['restorecon', '-F', str(target)], check=True)
(base / 'win7-registration.json').write_text(json.dumps({
    'path': str(target), 'sha256': hashlib.sha256(data).hexdigest(),
    'prefix': config['prefix'], 'autologin_changed': False,
}, indent=2) + '\n')
print('Registered Windows 7 Shell (Standalone). Boot defaults unchanged.')
