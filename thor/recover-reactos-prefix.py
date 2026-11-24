#!/usr/bin/env python3
"""Finish the prefix left by the interrupted Docker installation, in place."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile

root = Path.home() / 'win4wine'
spec = importlib.util.spec_from_file_location('reactos', root / 'prefix/reactos.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
dest = root / '.local/prefix-reactos'
assets = root / '.local/assets-reactos'
wine = Path(os.environ.get('WIN4WINE_WINE', root / '.local/wine-install/bin/wine'))
if (dest / module.MARKER).is_file():
    raise SystemExit('Prefix is already complete; use prefix/reactos.py stage instead.')
prefix = module.Prefix(dest, wine, 'en')

def run(*args, timeout=300, check=True, env=None):
    # Wine's background services can inherit output descriptors. A pipe would
    # wait for all those services to exit, not just the command itself.
    with tempfile.TemporaryFile() as output:
        result = subprocess.run([str(prefix.wine), *args], env=env or prefix.env,
                                timeout=timeout, stdout=output, stderr=output)
        if check and result.returncode:
            output.seek(0)
            print(output.read().decode(errors='replace'), flush=True)
            result.check_returncode()
    return result

prefix.run = run
prefix.run('wineboot', '-u', timeout=900)
prefix.wait()
server = subprocess.Popen([str(wine.with_name('wineserver')), '-p'], env=prefix.env,
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    prefix.place_files()
    prefix.registrations()
    prefix.appearance('classic')
finally:
    prefix.stop()
    server.wait(timeout=30)
update = (dest / '.update-timestamp').read_text().strip()
(dest / '.ros-registry-version').write_text(f'{module.VERSION} {update}\n')
manifest = json.loads((assets / 'manifest.json').read_text())
(dest / module.MARKER).write_text(json.dumps({
    'assets': str(assets), 'home': str(Path.home()), 'wine': str(wine),
    'lang': 'en', 'reactos': manifest['reactos'],
}, indent=2) + '\n')
print(f'Prefix recovered: {dest}')
