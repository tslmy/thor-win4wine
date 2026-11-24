#!/usr/bin/env python3
"""Read-only deployment prerequisites. No sudo, installs or display changes."""
import importlib
import os
from pathlib import Path
import platform
import shutil
import subprocess

if platform.system() != 'Linux' or platform.machine() not in ('aarch64', 'arm64'):
    raise SystemExit('Target must be ARM64 Linux; this recipe is for Thor/ArmadaOS.')
if os.geteuid() == 0:
    raise SystemExit('Connect as the ordinary desktop user, not root.')
for tool in ('python3', 'tar', 'flock', 'systemctl', 'dbus-run-session',
             'dbus-update-activation-environment', 'Xwayland', 'sudo', 'restorecon', 'ldd'):
    if not shutil.which(tool):
        raise SystemExit(f'Missing target dependency: {tool}. Resolve it using your OS documentation.')
for module in ('gi',):
    try:
        importlib.import_module(module)
    except ImportError:
        raise SystemExit(f'Missing native Python module: {module}')
if not Path('/etc/sddm.conf.d').is_dir():
    raise SystemExit('This installer requires the existing SDDM setup; it will not replace your display manager.')
if shutil.disk_usage(Path.home()).free < 8 * 1024**3:
    raise SystemExit('At least 8 GiB free in the target home is required (more for all three variants).')
model = Path('/sys/firmware/devicetree/base/model')
print('Device:', model.read_text().rstrip('\0') if model.exists() else 'unknown')
release = Path('/etc/os-release').read_text()
print(release)
print('PASS: basic target prerequisites. Validated baseline is Armada/Fedora 44; other OS versions are untested.')
print('No packages, prefixes, boot settings or display sessions were changed.')
