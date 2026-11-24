#!/usr/bin/env python3
"""Install a freshly built private runtime; refuses existing destinations."""
import json
import os
from pathlib import Path
import pwd
import shutil
import subprocess
import sys


def render(text, home, user, uid):
    """Render historical device templates without changing Armada's stock names."""
    return (text.replace('/var/home/armada', str(home))
            .replace('/run/user/1000', f'/run/user/{uid}')
            .replace("'armada'", repr(user))
            .replace('User=armada', f'User={user}'))


def install(stage, home=None):
    if os.geteuid() == 0:
        raise SystemExit('Run as the desktop user, not root.')
    home = home or Path.home()
    account = pwd.getpwuid(os.getuid())
    base = home / '.local/share/win4wine'
    root = home / 'win4wine'
    destinations = [base, root]
    for dest in destinations:
        if dest.exists() or dest.is_symlink():
            raise SystemExit(f'Refusing existing runtime/source: {dest}. No in-place upgrade is attempted.')
    tools = base / 'tools'
    base.mkdir(parents=True)
    # Archives were built locally. Rootfs needs trusted absolute library symlinks.
    def unpack(archive, target):
        target.mkdir(parents=True, exist_ok=True)
        subprocess.run(['tar', '-xf', str(stage / archive), '-C', str(target)], check=True)
    shutil.copytree(stage / 'source', root)
    unpack('wine-runtime.tar.gz', root / '.local')
    unpack('rootfs.tar', base / 'rootfs')
    unpack('box64.tar.gz', base / 'box64')
    unpack('labwc-arm64.tar.gz', base)
    unpack('native-support.tar.gz', base)
    tools.mkdir(exist_ok=True)
    for path in (stage / 'thor').iterdir():
        if path.is_file():
            target = tools / path.name
            target.write_text(render(path.read_text(), home, account.pw_name, account.pw_uid))
            target.chmod(0o755 if path.read_text().startswith('#!') else 0o644)
    bins = home / '.local/bin'
    bins.mkdir(parents=True, exist_ok=True)
    for name in ('win4wine-switch', 'reactos-standalone-session', 'xp-standalone-session', 'win7-standalone-session'):
        target = bins / name
        if target.exists() or target.is_symlink():
            raise SystemExit(f'Refusing existing command: {target}')
        shutil.copy2(tools / name, target)
        target.chmod(0o755)
    for name in ('wlr-randr',):
        target = bins / name
        if not target.exists() and not target.is_symlink():
            target.symlink_to(tools / name)
    wrappers = base / 'box64-wine'
    (wrappers / 'bin').mkdir(parents=True)
    for name in ('wine', 'wineserver'):
        shutil.copy2(tools / 'win4wine-box64', wrappers / 'bin' / name)
        (wrappers / 'bin' / name).chmod(0o755)
    for name in ('lib', 'share'):
        (wrappers / name).symlink_to(root / '.local/wine-install' / name, target_is_directory=True)
    config = base / 'labwc-config'
    config.mkdir()
    shutil.copy2(tools / 'labwc-rc.xml', config / 'rc.xml')
    shutil.copy2(root / '.local/bridge/shell-ui-probe-x64.exe', tools / 'shell-ui-probe-x64.exe')
    for binary in (base / 'labwc/bin/labwc', base / 'labwc/bin/Xvfb', tools / 'grim', tools / 'wlr-randr'):
        result = subprocess.run(['ldd', str(binary)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        if result.returncode or 'not found' in result.stdout:
            raise SystemExit(f'Unresolved native dependencies for {binary}:\n{result.stdout}')
    (base / 'installation.json').write_text(json.dumps({
        'user': account.pw_name, 'uid': account.pw_uid, 'home': str(home),
        'sources': json.loads((stage / 'thor/sources.json').read_text()),
        'status': 'runtime installed; prefixes and root registration are separate',
    }, indent=2) + '\n')
    print('Private runtime installed. No session was switched and no boot default was changed.')


if __name__ == '__main__':
    install(Path(sys.argv[1]).resolve())
