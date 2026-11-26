#!/usr/bin/env python3
"""Enable both internal panels at session start; kanshi then adds a known monitor."""
import argparse
import json
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--test-output', help='Explicit synthetic output for isolated tests only')
args = parser.parse_args()
outputs = json.loads(subprocess.check_output(['wlr-randr', '--json'], text=True))
names = {o['name']: o for o in outputs}
if args.test_output:
    if args.test_output not in names:
        raise SystemExit('The requested synthetic test output is absent.')
    command = ['wlr-randr', '--output', args.test_output, '--on', '--custom-mode', '1280x800', '--scale', '1.5']
else:
    if 'DSI-2' not in names:
        raise SystemExit('Upper internal display DSI-2 is unavailable; refusing a headless real session.')
    command = ['wlr-randr', '--output', 'DSI-2', '--on', '--mode', '1080x1920@60Hz',
               '--transform', '270', '--scale', '1.5', '--pos', '0,0']
    if 'DSI-1' in names:
        # The lower panel's only mode is 59.999 Hz, so name it without a rate.
        command += ['--output', 'DSI-1', '--on', '--mode', '1080x1240',
                    '--transform', '270', '--scale', '1.5', '--pos', '226,720']
    if 'DP-1' in names:
        # Leave a monitor connected at startup to kanshi, which knows the tested ones.
        command += ['--output', 'DP-1', '--off']
subprocess.run(command, check=True, timeout=30)
print(subprocess.check_output(['wlr-randr', '--json'], text=True), end='')
