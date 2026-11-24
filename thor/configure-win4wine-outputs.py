#!/usr/bin/env python3
"""Enable the upper panel and a conservative DP mode; never enable the lower panel."""
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
        command += ['--output', 'DSI-1', '--off']
    if 'DP-1' in names:
        modes = [m for m in names['DP-1'].get('modes', []) if m['width'] <= 1920 and m['height'] <= 1080]
        if modes:
            preferred = next((m for m in modes if m['width'] == 1920 and m['height'] == 1080), None)
            mode = preferred or max(modes, key=lambda m: m['width'] * m['height'])
            command += ['--output', 'DP-1', '--on', '--mode', f"{mode['width']}x{mode['height']}",
                        '--transform', 'normal', '--scale', '1', '--pos', '1280,0']
            print(f"External output: conservative {mode['width']}x{mode['height']} mode")
        else:
            command += ['--output', 'DP-1', '--off']
            print('External output left off: no reported mode at or below 1920x1080.')
subprocess.run(command, check=True, timeout=30)
print(subprocess.check_output(['wlr-randr', '--json'], text=True), end='')
