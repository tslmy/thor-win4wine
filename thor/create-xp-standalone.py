#!/usr/bin/env python3
"""Create an isolated English XP/Luna prefix using provided media and private Wine."""
import json
import os
from pathlib import Path
import signal
import subprocess
import time
from Xlib import display

home = Path.home()
root = home / 'win4wine'
base = home / '.local/share/win4wine'
assets = root / '.local/assets-xp'
prefix = root / '.local/prefix-xp-standalone'
wine = base / 'box64-wine/bin/wine'
server = wine.with_name('wineserver')
state = home / '.local/state/win4wine-xp'
state.mkdir(parents=True, exist_ok=True)
if prefix.exists():
    raise SystemExit(f'Refusing to overwrite existing XP prefix: {prefix}')
config = home / '.config/win4wine/xp-standalone.json'
if config.exists():
    raise SystemExit(f'Refusing existing XP configuration: {config}')
if not (assets / 'manifest.json').is_file():
    raise SystemExit('Extract the user-provided XP media first.')
for helper in ('theme-settings.exe', 'menu-settings.exe', 'xptray.exe', 'startmenu.exe',
               'iexplore.exe', 'linux-links.exe'):
    if not (root / '.local/bridge' / helper).is_file():
        raise SystemExit(f'Missing existing bridge helper: {helper}')
number = next((n for n in range(41, 61) if not Path(f'/tmp/.X11-unix/X{n}').exists()), None)
if number is None:
    raise SystemExit('No free headless X display.')
env = dict(os.environ, DISPLAY=f':{number}', WINEPREFIX=str(prefix), WINE=str(wine),
           WINEDEBUG='-all', LANG='en_US.UTF-8', LC_ALL='en_US.UTF-8')
env.pop('XAUTHORITY', None)
env.pop('WAYLAND_DISPLAY', None)
env.pop('WINEARCH', None)

with (state / 'installation.log').open('w') as log:
    xvfb = subprocess.Popen([str(base / 'labwc/bin/Xvfb'), f':{number}', '-screen', '0',
                             '1280x800x24', '-nolisten', 'tcp', '-ac', '-noreset'],
                            env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    try:
        for _ in range(100):
            if xvfb.poll() is not None:
                raise RuntimeError('Native Xvfb failed; inspect installation.log.')
            try:
                connection = display.Display(env['DISPLAY'])
                connection.close()
                break
            except Exception:
                time.sleep(.1)
        else:
            raise RuntimeError('Headless X display did not become ready.')
        # File logging, not pipes: Wine's background processes inherit descriptors.
        with (state / 'prefix-setup.log').open('w') as output:
            def setup(*args):
                print('Running:', *args, flush=True)
                subprocess.run(args, env=env, check=True, timeout=1800,
                               stdout=output, stderr=subprocess.STDOUT)
            setup('python3', str(root / 'prefix/create.py'), str(assets), str(prefix),
                  '--home', str(home), '--wine', str(wine))
            # Commit DPI before applying theme metrics in a fresh Wine process.
            setup('python3', str(root / 'prefix/display.py'), '--dpi', '120')
            subprocess.run([str(server), '-k'], env=env, stdout=output, stderr=subprocess.STDOUT, timeout=30)
            subprocess.run([str(server), '-w'], env=env, stdout=output, stderr=subprocess.STDOUT, timeout=30)
            setup('python3', str(root / 'prefix/display.py'), '--theme', 'luna', '--menu', 'xp')
            setup('python3', str(root / 'prefix/extras.py'), str(prefix), '--wine', str(wine))
            setup('python3', str(root / 'session/linux_apps.py'), str(prefix), '--wine', str(wine))
            setup('python3', str(root / 'xp-explorer/scripts/pins.py'), str(prefix), '--wine', str(wine))
            setup('python3', str(root / 'prefix/stage.py'), str(prefix), '--wine', str(wine))
            subprocess.run([str(server), '-k'], env=env, stdout=output, stderr=subprocess.STDOUT, timeout=30)
            subprocess.run([str(server), '-w'], env=env, stdout=output, stderr=subprocess.STDOUT, timeout=30)
            setup(str(wine), str(root / '.local/bridge/theme-settings.exe'), 'msstyles',
                  r'C:\windows\Resources\Themes\Luna\luna.msstyles', 'Metallic', 'NormalSize')
            setup(str(wine), 'reg', 'add', r'HKCU\Software\Microsoft\Windows\CurrentVersion\Policies\Explorer',
                  '/v', 'NoLowDiskSpaceChecks', '/t', 'REG_DWORD', '/d', '1', '/f')
        config.parent.mkdir(parents=True, exist_ok=True)
        if config.exists():
            raise RuntimeError(f'Refusing existing XP configuration: {config}')
        config.write_text(json.dumps({
            'shell': 'xp', 'wine': str(wine), 'prefix': str(prefix), 'state': str(state),
            'locale': 'en_US.UTF-8', 'linux_font': 'Tahoma', 'linux_menu': True,
            'welcome_screen': False, 'cursor_theme': 'win4wine-xp', 'shutdown_command': None,
            'reboot_command': None, 'readiness_timeout': 90,
        }, indent=2) + '\n')
        print(f'XP/Luna prefix and configuration ready: {prefix}', flush=True)
    finally:
        subprocess.run([str(server), '-k'], env=env, stdout=log, stderr=subprocess.STDOUT, timeout=30)
        subprocess.run([str(server), '-w'], env=env, stdout=log, stderr=subprocess.STDOUT, timeout=30)
        try:
            os.killpg(xvfb.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        xvfb.wait(timeout=20)
