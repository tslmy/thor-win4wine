#!/usr/bin/env python3
"""Root-only registration, parameterized for the desktop user's actual home/UID."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import pwd
import subprocess


def main(shell, user):
    if os.geteuid() != 0:
        raise SystemExit('Run with sudo, only after inspecting the installer and validating the prefix.')
    account = pwd.getpwnam(user)
    if account.pw_uid == 0:
        raise SystemExit('Root may not own a shell session.')
    home = Path(account.pw_dir)
    base = home / '.local/share/win4wine'
    tools = base / 'tools'
    from importlib.util import module_from_spec, spec_from_file_location
    spec = spec_from_file_location('install_user', tools / 'install-user.py')
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    config = json.loads((home / f'.config/win4wine/{shell}-standalone.json').read_text())
    marker = {'xp': 'xp-shell.json', 'reactos': 'reactos-shell.json', 'win7': 'win7-shell.json'}[shell]
    if config.get('shell', 'reactos') != shell or not (Path(config['prefix']) / marker).is_file():
        raise SystemExit('Selected prefix/config is incomplete.')
    entry = (tools / f'armada-{shell}.desktop').read_text()
    session_dir = Path('/etc/win4wine/wayland-sessions')
    files = {
        session_dir / f'armada-{shell}.desktop': entry,
        Path('/etc/sddm.conf.d/50-win4wine-session-dirs.conf'):
            '# Additional sessions only; no autologin/default changes.\n[Wayland]\n'
            'SessionDir=/etc/win4wine/wayland-sessions,/usr/local/share/wayland-sessions,/usr/share/wayland-sessions\n',
    }
    for name in ('standalone-test-control.py', 'switch-win4wine-session.py'):
        files[Path('/etc/win4wine') / name] = module.render((tools / name).read_text(), home, user, account.pw_uid)
    for path, data in files.items():
        if path.is_symlink() or (path.exists() and path.read_text() != data):
            raise SystemExit(f'Refusing existing different or symlinked root file: {path}')
    for path, data in files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(data)
        path.chmod(0o755 if path.suffix == '.py' else 0o644)
    subprocess.run(['restorecon', '-F', *map(str, files)], check=True)
    apps = home / '.local/share/applications'
    apps_existed = apps.exists()
    apps.mkdir(parents=True, exist_ok=True)
    if not apps_existed:
        os.chown(apps, account.pw_uid, account.pw_gid)
    dest = apps / f'switch-to-{shell}.desktop'
    data = (tools / f'switch-to-{shell}.desktop').read_text()
    if dest.exists() and dest.read_text() != data:
        raise SystemExit(f'Refusing existing different application entry: {dest}')
    dest.write_text(data)
    dest.chmod(0o644)
    os.chown(dest, account.pw_uid, account.pw_gid)
    record = base / f'registration-{shell}.json'
    record.write_text(json.dumps({
        'shell': shell, 'boot_defaults_changed': False,
        'files': {str(p): hashlib.sha256(data.encode()).hexdigest() for p, data in files.items()},
    }, indent=2) + '\n')
    os.chown(record, account.pw_uid, account.pw_gid)
    print(f'Registered {shell}. No SDDM restart, default selection, system FEX or Steam changes.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('shell', choices=('reactos', 'xp', 'win7'))
    parser.add_argument('--user', required=True)
    args = parser.parse_args()
    main(args.shell, args.user)
