#!/usr/bin/env python3
"""Add the XP login session without changing existing sessions or boot defaults."""
import hashlib
import json
import os
from pathlib import Path
import subprocess

if os.geteuid() != 0:
    raise SystemExit('Run with sudo after XP preparation/validation.')
home = Path('/var/home/armada')
base = home / '.local/share/win4wine'
config_path = home / '.config/win4wine/xp-standalone.json'
config = json.loads(config_path.read_text())
if config.get('shell') != 'xp' or not (Path(config['prefix']) / 'xp-shell.json').is_file():
    raise SystemExit('The dedicated XP prefix/configuration is incomplete.')
for path in (home / '.local/bin/xp-standalone-session', base / 'tools/xp-standalone-start', base / 'labwc/bin/labwc'):
    if not path.is_file() or not os.access(path, os.X_OK):
        raise SystemExit(f'Missing executable: {path}')
source = base / 'tools/armada-xp.desktop'
target = Path('/etc/win4wine/wayland-sessions/armada-xp.desktop')
data = source.read_bytes()
if target.exists() and target.read_bytes() != data:
    record = base / 'xp-registration.json'
    previous = json.loads(record.read_text()) if record.is_file() else {}
    if previous.get('path') != str(target) or previous.get('sha256') != hashlib.sha256(target.read_bytes()).hexdigest():
        raise SystemExit(f'Refusing to overwrite existing unrecognized content: {target}')
if not Path('/etc/sddm.conf.d/50-win4wine-session-dirs.conf').is_file():
    raise SystemExit('Register the persistent standalone session directory first.')
target.write_bytes(data)
target.chmod(0o644)
subprocess.run(['restorecon', '-F', str(target)], check=True)
(base / 'xp-registration.json').write_text(json.dumps({
    'path': str(target), 'sha256': hashlib.sha256(data).hexdigest(),
    'prefix': config['prefix'], 'autologin_changed': False,
}, indent=2) + '\n')
print('Registered Windows XP Shell (Standalone); ReactOS and boot defaults are unchanged.')
