#!/usr/bin/env python3
"""One-session SDDM trial with an independent, timed rollback to Armada Desktop."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

RUNTIME = Path('/run/win4wine-test')
STATE = RUNTIME / 'state.json'
CONFIG = RUNTIME / 'autologin.conf'
OVERRIDE = Path('/etc/sddm.conf.d/zzzz-win4wine-live-test.conf')
TIMER = 'win4wine-standalone-rollback'
SELF = Path('/etc/win4wine/standalone-test-control.py')
BASELINE = [Path('/etc/sddm.conf.d/armada.conf'),
            Path('/etc/sddm.conf.d/zz-holo-autologin.conf'),
            Path('/var/home/armada/.config/steamos-manager/state.toml')]

def call(*args, **kwargs):
    return subprocess.run(args, check=True, **kwargs)

def save(state):
    temporary = STATE.with_suffix('.tmp')
    temporary.write_text(json.dumps(state, indent=2) + '\n')
    os.replace(temporary, STATE)

def selection(session):
    return ('# Temporary win4wine trial; target disappears on reboot.\n'
            '[Autologin]\nUser=armada\nRelogin=false\nSession=' + session + '\n')

def select(session):
    temporary = CONFIG.with_suffix('.tmp')
    temporary.write_text(selection(session))
    temporary.chmod(0o644)
    os.replace(temporary, CONFIG)

def remove_override():
    if not OVERRIDE.is_symlink() or OVERRIDE.readlink() != CONFIG:
        raise RuntimeError(f'Refusing to remove an unexpected override: {OVERRIDE}')
    OVERRIDE.unlink()
    CONFIG.unlink(missing_ok=True)

def baseline_status(state):
    return {name: Path(name).exists() and hashlib.sha256(Path(name).read_bytes()).hexdigest() == digest
            for name, digest in state['baseline_sha256'].items()}

def main(action, session='armada-reactos.desktop'):
    if os.geteuid() != 0:
        raise SystemExit('Requires sudo; changes only its own temporary SDDM override.')
    RUNTIME.mkdir(mode=0o755, exist_ok=True)
    with (RUNTIME / 'control.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if action in ('begin', 'arm'):
            if OVERRIDE.exists() or OVERRIDE.is_symlink():
                raise RuntimeError('A trial override already exists; inspect/finish that trial first.')
            if session not in ('armada-reactos.desktop', 'armada-xp.desktop', 'armada-win7.desktop'):
                raise RuntimeError('Only the registered ReactOS, XP and Win7 sessions are supported.')
            if not (Path('/etc/win4wine/wayland-sessions') / session).is_file():
                raise RuntimeError('The standalone session is not registered.')
            timer = TIMER + '-' + str(time.time_ns())
            state = {'phase': 'arming', 'started': time.time(), 'timer': timer, 'session': session,
                     'baseline_sha256': {str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                                         for p in BASELINE if p.exists()}}
            save(state)
            call('systemd-run', '--unit=' + timer, '--on-active=8min',
                 '/usr/bin/python3', str(SELF), 'rollback')
            call('systemctl', 'is-active', '--quiet', timer + '.timer')
            select(session)
            OVERRIDE.symlink_to(CONFIG)
            call('restorecon', '-F', str(OVERRIDE))
            state['phase'] = 'testing'
            save(state)
            print('Trial armed: automatic rollback to Armada Desktop in 8 minutes.', flush=True)
            if action == 'begin':
                call('systemctl', 'restart', 'sddm.service')
        elif action == 'status':
            if not STATE.exists():
                print('No trial state in this boot.')
                return
            state = json.loads(STATE.read_text())
            print(json.dumps(dict(state, baseline_unchanged=baseline_status(state)), indent=2))
        elif action == 'accept':
            state = json.loads(STATE.read_text())
            if state['phase'] != 'testing' or CONFIG.read_text() != selection(state.get('session', 'armada-reactos.desktop')):
                raise RuntimeError('The shell trial is no longer active; cannot accept it.')
            state['phase'] = 'accepted'
            save(state)
            call('systemctl', 'stop', state.get('timer', TIMER) + '.timer')
            remove_override()
            print('Current shell session kept. Temporary override removed; boot defaults unchanged.')
            print(json.dumps(baseline_status(state), indent=2))
        elif action in ('rollback', 'rescue'):
            if not STATE.exists() and action == 'rescue':
                state = {'phase': 'recovery', 'started': time.time(),
                         'baseline_sha256': {str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                                             for p in BASELINE if p.exists()}}
                save(state)
            elif not STATE.exists():
                print('No active trial in this boot.')
                return
            else:
                state = json.loads(STATE.read_text())
            if action == 'rollback' and state['phase'] != 'testing':
                print('No active trial; nothing to roll back.')
                return
            if action == 'rescue' and not OVERRIDE.exists() and not OVERRIDE.is_symlink():
                select('armada-plasma.desktop')
                OVERRIDE.symlink_to(CONFIG)
                call('restorecon', '-F', str(OVERRIDE))
            if not OVERRIDE.is_symlink() or OVERRIDE.readlink() != CONFIG:
                raise RuntimeError('Unexpected override; refusing to change it.')
            state['phase'] = 'rolling-back'
            save(state)
            subprocess.run(['systemctl', 'stop', state.get('timer', TIMER) + '.timer'], check=False)
            select('armada-plasma.desktop')
            call('systemctl', 'restart', 'sddm.service')
            for _ in range(120):
                result = subprocess.run(['runuser', '-u', 'armada', '--', '/usr/bin/env',
                    'XDG_RUNTIME_DIR=/run/user/1000', 'DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus',
                    'systemctl', '--user', 'is-active', '--quiet', 'plasma-kwin_wayland.service'])
                if result.returncode == 0:
                    remove_override()
                    state['phase'] = 'rolled-back'
                    save(state)
                    print('Armada Desktop fallback started; verify physical display visibility. Boot defaults unchanged.')
                    print(json.dumps(baseline_status(state), indent=2))
                    return
                time.sleep(1)
            raise RuntimeError('Plasma did not start; temporary fallback remains selected. SSH recovery required.')
        else:
            raise SystemExit('Usage: standalone-test-control.py arm|begin|status|accept|rollback')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('arm', 'begin', 'status', 'accept', 'rollback', 'rescue'))
    parser.add_argument('--session', choices=('armada-reactos.desktop', 'armada-xp.desktop', 'armada-win7.desktop'), default='armada-reactos.desktop')
    args = parser.parse_args()
    main(args.action, args.session)
