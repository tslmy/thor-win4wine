#!/usr/bin/env python3
"""Create one new shell on private Xvfb; does not switch the physical desktop."""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time


def cursor_arguments(shell, assets, destination):
    # Upstream uses positional sys.argv checks, not argparse: flag order matters.
    if shell == 'win7':
        return ['--win7', str(assets / 'cursors/user32.dll'), str(assets / 'cursors'), str(destination)]
    arguments = [str(assets / 'resources/user32.dll'), str(destination)]
    return arguments + (['--reactos'] if shell == 'reactos' else [])


def main(shell):
    if os.geteuid() == 0:
        raise SystemExit('Create prefixes as the ordinary desktop user, never root.')
    home = Path.home()
    root = home / 'win4wine'
    base = home / '.local/share/win4wine'
    tools = base / 'tools'
    assets = root / f'.local/assets-{shell}'
    prefix = root / f'.local/prefix-{shell}-standalone'
    config = home / f'.config/win4wine/{shell}-standalone.json'
    if prefix.exists() or config.exists() or assets.exists():
        raise SystemExit('Refusing existing assets, prefix or config. Inspect partial installations manually; no reset is performed.')
    archive = home / f'.local/state/thor-bootstrap/assets-{shell}.tar.gz'
    if not archive.is_file():
        raise SystemExit(f'Missing extracted assets: {archive}')
    subprocess.run(['tar', '-xzf', str(archive), '-C', str(root / '.local')], check=True)
    state = home / '.local/state' / ('win4wine-standalone' if shell == 'reactos' else f'win4wine-{shell}')
    state.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, PYTHONPATH=str(base / 'python'), WINEDEBUG='-all',
               LD_LIBRARY_PATH=str(base / 'labwc/lib'), LANG='en_US.UTF-8', LC_ALL='en_US.UTF-8')
    # Use the already-measured factory scripts for XP and Win7.
    if shell != 'reactos':
        subprocess.run(['python3', str(tools / f'create-{shell}-standalone.py')], env=env, check=True)
    else:
        from Xlib import display
        wine = base / 'box64-wine/bin/wine'
        number = next((n for n in range(41, 61) if not Path(f'/tmp/.X11-unix/X{n}').exists()), None)
        if number is None:
            raise SystemExit('No free private X display.')
        env.update(DISPLAY=f':{number}', WINEPREFIX=str(prefix), WINE=str(wine))
        for key in ('XAUTHORITY', 'WAYLAND_DISPLAY', 'WINEARCH'):
            env.pop(key, None)
        with (state / 'installation.log').open('w') as log:
            xvfb = subprocess.Popen([str(base / 'labwc/bin/Xvfb'), env['DISPLAY'], '-screen', '0',
                '1280x800x24', '-nolisten', 'tcp', '-ac', '-noreset'], env=env,
                stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            try:
                for _ in range(100):
                    if xvfb.poll() is not None:
                        raise RuntimeError('Private Xvfb exited; inspect installation.log.')
                    try:
                        d = display.Display(env['DISPLAY'])
                        d.close()
                        break
                    except Exception:
                        time.sleep(.1)
                else:
                    raise RuntimeError('Private Xvfb did not become ready.')
                def setup(*command):
                    subprocess.run(command, env=env, check=True, timeout=1800,
                                   stdout=log, stderr=subprocess.STDOUT)
                setup('python3', str(root / 'prefix/reactos.py'), 'create', str(assets), str(prefix),
                      '--home', str(home), '--wine', str(wine), '--lang', 'en', '--theme', 'classic')
                setup('python3', str(root / 'prefix/display.py'), '--dpi', '192')
                setup('python3', str(root / 'session/linux_apps.py'), str(prefix), '--wine', str(wine))
                config.parent.mkdir(parents=True, exist_ok=True)
                config.write_text(json.dumps({
                    'shell': shell, 'wine': str(wine), 'prefix': str(prefix), 'state': str(state),
                    'locale': 'en_US.UTF-8', 'linux_font': 'Tahoma', 'linux_menu': True,
                    'welcome_screen': False, 'cursor_theme': 'win4wine-reactos',
                    'shutdown_command': None, 'reboot_command': None, 'readiness_timeout': 120,
                    'primary': 'DSI-2',
                }, indent=2) + '\n')
            finally:
                subprocess.run([str(wine.with_name('wineserver')), '-k'], env=env, timeout=30, stdout=log, stderr=log)
                subprocess.run([str(wine.with_name('wineserver')), '-w'], env=env, timeout=30, stdout=log, stderr=log)
                try:
                    os.killpg(xvfb.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                xvfb.wait(timeout=20)
    destination = home / f'.local/share/icons/win4wine-{shell}'
    subprocess.run(['python3', str(root / 'greeter/cursors.py'), *cursor_arguments(shell, assets, destination)], env=env, check=True)
    data = json.loads(config.read_text())
    data['cursor_theme'] = f'win4wine-{shell}'
    config.write_text(json.dumps(data, indent=2) + '\n')
    print(f'{shell}: independent prefix ready. Run headless tests, then register; no physical session was switched.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('shell', choices=('reactos', 'xp', 'win7'))
    main(parser.parse_args().shell)
