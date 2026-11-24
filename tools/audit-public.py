#!/usr/bin/env python3
"""Conservative tracked-source checks; use a real secret scanner before publication too."""
import re
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
PATTERNS = (
    rb'-----BEGIN (?:OPENSSH |RSA |EC |DSA )?PRIVATE KEY-----',
    rb'\bgh[pousr]_[A-Za-z0-9]{30,}\b',
    rb'\bgithub_pat_[A-Za-z0-9_]{40,}\b',
    rb'\bAKIA[0-9A-Z]{16}\b',
    rb'\bsk-[A-Za-z0-9]{32,}\b',
)
FORBIDDEN_SUFFIXES = {'.exe', '.dll', '.iso', '.wim', '.png', '.jpg', '.bmp', '.pem', '.key', '.deb', '.zip', '.gz'}


def problems(name, data):
    result = []
    if Path(name).suffix.lower() in FORBIDDEN_SUFFIXES:
        result.append('binary/media/key file extension')
    if b'\0' in data or data.startswith((b'MZ', b'\x7fELF', b'PK\x03\x04')):
        result.append('binary payload')
    if any(re.search(pattern, data) for pattern in PATTERNS):
        result.append('possible credential; value deliberately not printed')
    if name.startswith(('.build/', 'win4wine/', '.env', '.ssh/')):
        result.append('private/generated path')
    return result


def main():
    result = subprocess.run(['git', 'ls-files', '-z'], cwd=ROOT, check=True, stdout=subprocess.PIPE)
    failures = []
    for raw in result.stdout.split(b'\0'):
        if not raw:
            continue
        name = raw.decode()
        data = (ROOT / name).read_bytes()
        failures.extend(f'{name}: {item}' for item in problems(name, data))
    if failures:
        raise SystemExit('\n'.join(failures))
    print('PASS: tracked source contains no detected credentials, media, executables or generated runtime paths.')
    print('This heuristic check is not a guarantee. Scan full history with Gitleaks before publishing.')


if __name__ == '__main__':
    main()
