#!/usr/bin/env python3
"""Create an isolated English Windows 7 x64 shell prefix with scoped native tools."""
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from Xlib import display

home = Path.home()
root = home / 'win4wine'
base = home / '.local/share/win4wine'
assets = root / '.local/assets-win7'
prefix = root / '.local/prefix-win7-standalone'
wine = base / 'box64-wine/bin/wine'
server = wine.with_name('wineserver')
state = home / '.local/state/win4wine-win7'
state.mkdir(parents=True, exist_ok=True)
if prefix.exists():
    raise SystemExit(f'Refusing existing Win7 prefix: {prefix}')
config = home / '.config/win4wine/win7-standalone.json'
if config.exists():
    raise SystemExit(f'Refusing existing Win7 config: {config}')
if not (assets / 'media.json').is_file():
    raise SystemExit('Extract the user-provided Win7 media first.')
number = next((n for n in range(41, 61) if not Path(f'/tmp/.X11-unix/X{n}').exists()), None)
if number is None:
    raise SystemExit('No free test X display.')
env = dict(os.environ, DISPLAY=f':{number}', WINEPREFIX=str(prefix), WINEDEBUG='-all',
           LANG='en_US.UTF-8', LC_ALL='en_US.UTF-8')
env.pop('XAUTHORITY', None)
env.pop('WAYLAND_DISPLAY', None)
os.environ.update(env)
sys.path.insert(0, str(root / 'prefix'))
spec = importlib.util.spec_from_file_location('win7_prefix', root / 'prefix/win7.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
original_settings = module.settings
def settings(p, lang):
    original_settings(p, lang)
    p.reg(r'HKCU\Control Panel\Desktop', 'LogPixels', 120, 'REG_DWORD')
    p.reg(r'HKCU\Software\Microsoft\Windows\CurrentVersion\Policies\Explorer',
          'NoLowDiskSpaceChecks', 1, 'REG_DWORD')
module.settings = settings

with (state / 'installation.log').open('w') as log:
    def run(self, *args, timeout=300, check=True, env=None):
        print('Wine:', *args, flush=True)
        return subprocess.run([str(self.wine), *args], env=env or self.env, check=check,
                              timeout=timeout, stdout=log, stderr=subprocess.STDOUT)
    def stop(self):
        subprocess.run([str(server), '-k'], env=self.env, timeout=30,
                       stdout=log, stderr=subprocess.STDOUT)
        subprocess.run([str(server), '-w'], env=self.env, timeout=30,
                       stdout=log, stderr=subprocess.STDOUT)
    module.Prefix.run = run
    module.Prefix.stop = stop
    xvfb = subprocess.Popen([str(base / 'labwc/bin/Xvfb'), f':{number}', '-screen', '0',
                             '1280x800x24', '-nolisten', 'tcp', '-ac', '-noreset'], env=env,
                            stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    try:
        for _ in range(100):
            if xvfb.poll() is not None:
                raise RuntimeError('Native Xvfb exited.')
            try:
                connection = display.Display(env['DISPLAY'])
                connection.close()
                break
            except Exception:
                time.sleep(.1)
        else:
            raise RuntimeError('Native Xvfb did not become ready.')
        module.create(assets, prefix, home, str(wine))
        subprocess.run(['python3', str(root / 'greeter/cursors.py'), '--win7',
                        str(assets / 'cursors/user32.dll'), str(assets / 'cursors'),
                        str(home / '.local/share/icons/win4wine-win7')], check=True, env=env)
        subprocess.run(['python3', str(root / 'session/linux_apps.py'), str(prefix), '--wine', str(wine)],
                       env=env, check=True, timeout=300, stdout=log, stderr=subprocess.STDOUT)
        config.parent.mkdir(parents=True, exist_ok=True)
        if config.exists():
            raise RuntimeError('Refusing existing Win7 config.')
        config.write_text(json.dumps({
            'shell': 'win7', 'wine': str(wine), 'prefix': str(prefix), 'state': str(state),
            'locale': 'en_US.UTF-8', 'linux_font': 'Segoe UI', 'linux_menu': True,
            'welcome_screen': False, 'cursor_theme': 'win4wine-win7',
            'shutdown_command': None, 'reboot_command': None, 'readiness_timeout': 120,
            'primary': 'DSI-2',
        }, indent=2) + '\n')
        print('Windows 7 standalone prefix/config ready.', flush=True)
    finally:
        subprocess.run([str(server), '-k'], env=env, timeout=30, stdout=log, stderr=subprocess.STDOUT)
        subprocess.run([str(server), '-w'], env=env, timeout=30, stdout=log, stderr=subprocess.STDOUT)
        try:
            os.killpg(xvfb.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        xvfb.wait(timeout=20)
