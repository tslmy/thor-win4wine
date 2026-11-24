#!/usr/bin/env python3
"""Register the prepared standalone session, without restarting SDDM/autologin."""
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess

if os.geteuid() != 0:
    raise SystemExit('Run with sudo after the native runtime has been validated.')
home = Path('/var/home/armada')
base = home / '.local/share/win4wine'
for path in (base / 'labwc/bin/labwc', home / '.local/bin/reactos-standalone-session',
             base / 'tools/reactos-standalone-start', home / '.config/win4wine/reactos-standalone.json'):
    if not path.is_file():
        raise SystemExit(f'Missing prerequisite: {path}')
entry = (base / 'tools/armada-reactos.desktop').read_bytes()
directory = Path('/etc/win4wine/wayland-sessions')
override = Path('/etc/sddm.conf.d/50-win4wine-session-dirs.conf')
content = (b'# Managed by Thor win4wine standalone registration. No autologin settings.\n'
           b'[Wayland]\n'
           b'SessionDir=/etc/win4wine/wayland-sessions,/usr/local/share/wayland-sessions,/usr/share/wayland-sessions\n')
files = {directory / 'armada-reactos.desktop': entry, override: content}
for path, data in files.items():
    if path.exists() and path.read_bytes() != data:
        raise SystemExit(f'Refusing to overwrite existing different content: {path}')
record = base / ('standalone-registration-' + datetime.now().strftime('%Y%m%d-%H%M%S') + '.json')
manifest = []
for path, data in files.items():
    existed = path.exists()
    manifest.append({'path': str(path), 'already_existed': existed,
                     'sha256': hashlib.sha256(data).hexdigest()})
    path.parent.mkdir(parents=True, exist_ok=True)
    if not existed:
        path.write_bytes(data)
        path.chmod(0o644)
subprocess.run(['restorecon', '-F', *map(str, files)], check=True)
record.write_text(json.dumps(manifest, indent=2) + '\n')
record.chmod(0o644)
print('Registered ReactOS Shell (Standalone). SDDM has NOT been restarted.')
print('Autologin and steamos-manager defaults have NOT been changed.')
print(f'Registration manifest: {record}')
