#!/usr/bin/env python3
"""Move a virtual pointer and capture the approved upper output, never modeset."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import time

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--shell', choices=('xp', 'reactos', 'win7'), required=True)
args = parser.parse_args()
home = Path.home()
base = home / '.local/share/win4wine'
config = json.loads((home / f'.config/win4wine/{args.shell}-standalone.json').read_text())
state = Path(config['state'])
assert json.loads((state / 'status.json').read_text())['state'] == 'xp-shell'
pid = int(subprocess.check_output(['pgrep', '-u', str(os.getuid()), '-x', 'labwc'], text=True).strip())
compositor_env = dict(item.split('=', 1) for item in Path(f'/proc/{pid}/environ').read_text().split('\0') if '=' in item)
assert compositor_env.get('WLR_NO_HARDWARE_CURSORS') == '1', 'Software cursor fallback not enabled'
manager = dict(line.split('=', 1) for line in subprocess.check_output(
    ['systemctl', '--user', 'show-environment'], text=True).splitlines() if '=' in line)
assert manager.get('XDG_CURRENT_DESKTOP') == config.get('desktop_identity', {
    'xp': 'XP-Shell', 'reactos': 'ReactOS', 'win7': 'Win7-Shell'}[args.shell])
env = dict(os.environ, WAYLAND_DISPLAY=manager['WAYLAND_DISPLAY'])
outputs = json.loads(subprocess.check_output(['wlr-randr', '--json'], env=env, text=True))
assert any(o['name'] == 'DSI-2' and o['enabled'] for o in outputs)
assert not any(o['name'] == 'DSI-1' and o['enabled'] for o in outputs), 'Lower output must stay off'
# A large negative delta clamps the pointer to the approved output's origin.
for dx, dy in ((-10000, -10000), (200, 200)):
    subprocess.run([str(base / 'tools/wlrctl'), 'pointer', 'move', str(dx), str(dy)], env=env, check=True)
time.sleep(.3)
for suffix, flags in (('without-cursor', []), ('with-cursor', ['-c'])):
    target = state / f'cursor-probe-{suffix}.png'
    subprocess.run([str(base / 'tools/grim'), *flags, '-o', 'DSI-2', str(target)], env=env, check=True)
(state / 'cursor-probe.json').write_text(json.dumps({
    'shell': args.shell, 'software_cursor': True, 'outputs': outputs,
    'validation': 'Inspect screenshots; physical DP visibility is not proven.'
}, indent=2) + '\n')
print(f'Captured upper-panel cursor evidence in {state}; no output configuration changed.')
