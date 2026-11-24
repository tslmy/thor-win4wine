#!/usr/bin/env python3
"""Clone the validated, idle nested prefix and set standalone DPI (default 192)."""
import argparse
import json
import os
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--dpi', type=int, default=192)
args = parser.parse_args()
if not 19 <= args.dpi <= 480:
    parser.error('DPI must be between 19 and 480.')
home = Path.home()
source = home / 'win4wine/.local/prefix-reactos-box64'
target = home / 'win4wine/.local/prefix-reactos-standalone'
wine = home / '.local/share/win4wine/box64-wine/bin/wine'
server = wine.with_name('wineserver')
if not (source / 'reactos-shell.json').is_file():
    raise SystemExit('The validated source ReactOS prefix is missing.')
if target.exists():
    raise SystemExit(f'Refusing to overwrite existing standalone prefix: {target}')
try:
    subprocess.run([str(server), '-w'], env=dict(os.environ, WINEPREFIX=str(source)),
                   check=True, timeout=2, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
except subprocess.TimeoutExpired:
    raise SystemExit('Close all Wine programs in the source prefix before cloning it.')
subprocess.run(['cp', '-a', '--reflink=auto', str(source), str(target)], check=True)
env = dict(os.environ, WINEPREFIX=str(target), WINE=str(wine), WINEDEBUG='-all')
try:
    subprocess.run(['python3', str(home / 'win4wine/prefix/display.py'), '--dpi', str(args.dpi)],
                   env=env, check=True, timeout=120)
finally:
    subprocess.run([str(server), '-k'], env=env, timeout=20,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run([str(server), '-w'], env=env, timeout=20,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
config = home / '.config/win4wine/reactos-standalone.json'
data = json.loads(config.read_text())
data['prefix'] = str(target)
config.write_text(json.dumps(data, indent=2) + '\n')
print(f'Standalone prefix ready at {args.dpi} DPI. Original prefix is unchanged.')
