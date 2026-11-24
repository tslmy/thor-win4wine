#!/usr/bin/env python3
"""Create a clean ReactOS prefix using the private Box64 Wine wrappers."""
import importlib.util
from pathlib import Path
import subprocess
import tempfile

home = Path.home()
root = home / 'win4wine'
wine = home / '.local/share/win4wine/box64-wine/bin/wine'
spec = importlib.util.spec_from_file_location('reactos', root / 'prefix/reactos.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

def run(self, *args, timeout=300, check=True, env=None):
    with tempfile.TemporaryFile() as output:
        result = subprocess.run([str(self.wine), *args], env=env or self.env,
                                timeout=timeout, stdout=output, stderr=output)
        if check and result.returncode:
            output.seek(0)
            print(output.read().decode(errors='replace'), flush=True)
            result.check_returncode()
        return result

module.Prefix.run = run
module.create(root / '.local/assets-reactos', root / '.local/prefix-reactos-box64',
              home, wine, 'en', 'classic')
