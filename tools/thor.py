#!/usr/bin/env python3
"""Build-host CLI. Configuration is environment-only; never writes SSH credentials."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tarfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / '.build/reproduce'
SOURCES = json.loads((ROOT / 'thor/sources.json').read_text())
SOURCE = BUILD / 'win4wine'
SHELLS = ('reactos', 'xp', 'win7')


def run(*args, label=None, **kwargs):
    print('+', label or shlex.join(map(str, args)), flush=True)
    return subprocess.run(list(map(str, args)), check=True, **kwargs)


def download(url, path, digest=None):
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        part = path.with_suffix(path.suffix + '.part')
        with urllib.request.urlopen(url, timeout=120) as response, part.open('wb') as out:
            shutil.copyfileobj(response, out)
        part.replace(path)
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest and actual != digest:
        raise SystemExit(f'SHA-256 mismatch: {path}; inspect/remove the failed download manually.')
    return actual


def source():
    pin = SOURCES['win4wine']
    marker = SOURCE / '.thor-source.json'
    if SOURCE.exists():
        if not marker.is_file() or json.loads(marker.read_text()) != pin:
            raise SystemExit(f'Refusing unexpected existing source: {SOURCE}')
        return
    archive = BUILD / 'downloads/win4wine.tar.gz'
    digest = download(f"{pin['url']}/archive/{pin['commit']}.tar.gz", archive,
                      SOURCES['win4wine_archive_sha256'])
    SOURCE.mkdir(parents=True)
    with tarfile.open(archive) as tar:
        for member in tar.getmembers():
            parts = Path(member.name).parts[1:]
            if not parts:
                continue
            member.name = str(Path(*parts))
            tar.extract(member, SOURCE, filter='data')
    marker.write_text(json.dumps(pin) + '\n')
    (BUILD / 'source-download-sha256.txt').write_text(digest + '\n')


def docker_image(kind):
    tag = f'thor-win4wine-{kind}:local'
    run('docker', 'build', '--platform', 'linux/amd64' if kind == 'wine' else 'linux/arm64',
        '-t', tag, '-f', ROOT / f'containers/{kind}.Dockerfile', ROOT)
    return tag


def container(kind, script, *, extra=(), mounts=(), capture=False):
    directory = BUILD / kind
    directory.mkdir(parents=True, exist_ok=True)
    args = ['docker', 'run', '--rm', '--platform', 'linux/amd64' if kind == 'wine' else 'linux/arm64',
            '-v', f'{SOURCE}:/input:ro', '-v', f'{ROOT / "thor"}:/tools:ro',
            '-v', f'{directory}:/build']
    for host, guest in mounts:
        args += ['-v', f'{Path(host).resolve()}:{guest}:ro']
    args += list(extra)
    args += [f'thor-win4wine-{kind}:local']
    if kind == 'native':
        args += ['-c', script]
    return run(*args, stdout=subprocess.PIPE if capture else None)


def build_wine():
    source()
    tag = docker_image('wine')
    container('wine', '', extra=('-e', f'JOBS={os.environ.get("THOR_JOBS", "6")}'))
    package_userspace(tag)


def package_userspace(tag='thor-win4wine-wine:local'):
    # Export an unstarted image container: never includes the /build bind mount,
    # private media or host home. This is a private userspace, not Armada's rootfs.
    result = run('docker', 'create', '--platform', 'linux/amd64', tag,
                 stdout=subprocess.PIPE, text=True)
    cid = result.stdout.strip()
    try:
        run('docker', 'export', '-o', BUILD / 'wine/rootfs.tar', cid)
    finally:
        run('docker', 'rm', cid)
    box = SOURCES['box64']
    download(box['url'], BUILD / 'downloads/box64.deb', box['sha256'])
    # dpkg-deb extracts on the build host container, never installs a host package.
    run('docker', 'run', '--rm', '--platform', 'linux/amd64', '--entrypoint', 'bash',
        '-v', f'{BUILD}:/output', tag, '-c',
        'set -e; mkdir -p /output/box64; dpkg-deb -x /output/downloads/box64.deb /output/box64; '
        'tar -C /output/box64 -czf /output/wine/box64.tar.gz .')


def build_native():
    source()
    docker_image('native')
    container('native', 'set -e; bash /tools/build-labwc-inner.sh; '
              'mkdir -p /build/support/tools /build/support/python; '
              'cp /usr/bin/grim /usr/bin/wlrctl /usr/bin/wlr-randr /build/support/tools/; '
              'python3 -c "import Xlib,six,shutil; shutil.copytree(Xlib.__path__[0], '
              '\'/build/support/python/Xlib\', dirs_exist_ok=True); '
              'shutil.copyfile(six.__file__, \'/build/support/python/six.py\')"; '
              'tar -C /build/support -czf /build/native-support.tar.gz tools python',
              extra=('-e', 'THOR_SKIP_PACKAGES=1', '-e', 'THOR_LABWC_PREFIX=/opt/thor/labwc'))


def smoke_native():
    run('docker', 'run', '--rm', '--platform', 'linux/arm64', '--user', '1000:1000',
        '-v', f'{BUILD / "native"}:/build:ro', '-v', f'{ROOT / "thor"}:/tools:ro',
        '-v', f'{ROOT / "containers/smoke-native.sh"}:/smoke.sh:ro',
        'thor-win4wine-native:local', '/smoke.sh')


def test_container():
    for name in ('wine/wine-runtime.tar.gz', 'wine/rootfs.tar', 'wine/box64.tar.gz',
                 'native/labwc-arm64.tar.gz', 'native/native-support.tar.gz', 'native/assets-reactos.tar.gz'):
        if not (BUILD / name).is_file():
            raise SystemExit(f'Missing {name}; run just build and just extract reactos first.')
    run('docker', 'build', '--platform', 'linux/arm64', '-t', 'thor-win4wine-test:local',
        '-f', ROOT / 'containers/test.Dockerfile', ROOT)
    run('docker', 'run', '--rm', '--platform', 'linux/arm64',
        '-v', f'{BUILD}:/artifacts:ro', '-v', f'{ROOT / "thor"}:/tools:ro',
        '-v', f'{ROOT / "containers"}:/checks:ro', 'thor-win4wine-test:local')


def extract(shell, media):
    source()
    if shell != 'reactos' and not media:
        raise SystemExit('XP/Win7 require a path to your own licensed media; no download is provided.')
    if shell != 'reactos' and not Path(media).exists():
        raise SystemExit(f'Media does not exist: {media}')
    if shell == 'win7' and not Path(media).is_file():
        raise SystemExit('Win7 requires an ISO file, not just its mounted directory.')
    if (BUILD / f'native/assets-{shell}').exists():
        raise SystemExit('Assets already exist; refusing to overwrite or merge extractions.')
    docker_image('native')
    program = {'reactos': 'reactos.py', 'xp': 'extract.py', 'win7': 'win7.py'}[shell]
    media_arg = '/media/input ' if shell != 'reactos' else ''
    container('native', f'set -e; command -v 7z >/dev/null || ln -s /usr/bin/7zz /usr/local/bin/7z; '
              f'python3 /input/extract/{program} {media_arg}/build/assets-{shell}; '
              f'tar -C /build -czf /build/assets-{shell}.tar.gz assets-{shell}',
              mounts=[(media, '/media/input')] if media else [])


def ssh_options():
    args = ['-o', 'BatchMode=yes', '-o', 'ConnectTimeout=15']
    if os.environ.get('THOR_SSH_KEY'):
        args += ['-i', str(Path(os.environ['THOR_SSH_KEY']).expanduser())]
    return args


def target():
    host = os.environ.get('THOR_HOST', '')
    user = os.environ.get('THOR_USER', '')
    if not host or host.startswith('-') or not re.fullmatch(r'[A-Za-z0-9_.:@-]+', host):
        raise SystemExit('Set THOR_HOST to your SSH host/alias (no shell syntax).')
    if user and not re.fullmatch(r'[a-z_][a-z0-9_-]*', user):
        raise SystemExit('THOR_USER must be a Linux login name.')
    return f'{user}@{host}' if user else host


def remote_python(script, *, args=(), capture=False):
    command = shlex.join(['python3', '-c', script, *map(str, args)])
    return run('ssh', *ssh_options(), target(), command,
               label=f'ssh {target()} python3 <remote script>',
               stdout=subprocess.PIPE if capture else None, text=True)


def identity():
    result = remote_python('import json,os,pwd; p=pwd.getpwuid(os.getuid()); '
                           'print(json.dumps(dict(user=p.pw_name,uid=p.pw_uid,home=p.pw_dir)))', capture=True)
    data = json.loads(result.stdout)
    if data['uid'] == 0 or not re.fullmatch(r'/[A-Za-z0-9_./-]+', data['home']):
        raise SystemExit('Connect as a regular user with a conventional absolute home path.')
    if not re.fullmatch(r'[a-z_][a-z0-9_-]*', data['user']):
        raise SystemExit('Unsupported login name.')
    return data


def preflight():
    remote_python((ROOT / 'thor/preflight.py').read_text())


def deploy():
    preflight()
    who = identity()
    needed = ['wine/wine-runtime.tar.gz', 'wine/rootfs.tar', 'wine/box64.tar.gz',
              'native/labwc-arm64.tar.gz', 'native/native-support.tar.gz']
    for path in needed:
        if not (BUILD / path).is_file():
            raise SystemExit(f'Missing {path}; run just build first.')
    bundle = BUILD / 'deploy.tar'
    with tarfile.open(bundle, 'w') as tar:
        tar.add(SOURCE, arcname='source', filter=lambda m: None if '/.local/' in m.name else m)
        for path in needed:
            tar.add(BUILD / path, arcname=Path(path).name)
        # Never sweep a developer's untracked helper, capture or local secret into a bundle.
        files = subprocess.check_output(['git', 'ls-files', '-z', 'thor'], cwd=ROOT).split(b'\0')
        for raw in files:
            if raw:
                name = raw.decode()
                tar.add(ROOT / name, arcname=name)
    upload = '.local/state/thor-bootstrap'
    remote_python('from pathlib import Path; import sys; '
                  'Path.home().joinpath(sys.argv[1]).mkdir(parents=True,exist_ok=True)', args=[upload])
    destination = f"{target()}:{who['home']}/{upload}/deploy.tar"
    run('scp', *ssh_options(), bundle, destination)
    remote_python('from pathlib import Path; import subprocess; '
                  'h=Path.home(); p=h/".local/state/thor-bootstrap"; '
                  'subprocess.run(["tar","-xf",str(p/"deploy.tar"),"-C",str(p)],check=True); '
                  'subprocess.run(["python3",str(p/"thor/install-user.py"),str(p)],check=True)')


def device_action(action, shell=None):
    if action in ('switch', 'rescue') and os.environ.get('THOR_ALLOW_SWITCH') != '1':
        raise SystemExit('This closes the current desktop/apps. Unplug DP, preserve SSH, then set THOR_ALLOW_SWITCH=1.')
    if action == 'register':
        who = identity()
        command = ['sudo', '-n', 'python3', f"{who['home']}/.local/share/win4wine/tools/register-shell.py", shell, '--user', who['user']]
    elif action == 'rescue':
        command = ['sudo', '-n', 'python3', '/etc/win4wine/standalone-test-control.py', 'rescue']
    elif action == 'switch':
        command = ['.local/bin/win4wine-switch', shell]
    elif action == 'prefix':
        # Transfer extracted assets, never license keys or a host Wine prefix.
        archive = BUILD / f'native/assets-{shell}.tar.gz'
        if not archive.is_file():
            raise SystemExit(f'Run just extract {shell} first.')
        who = identity()
        run('scp', *ssh_options(), archive,
            f"{target()}:{who['home']}/.local/state/thor-bootstrap/{archive.name}")
        command = ['python3', '.local/share/win4wine/tools/prepare-shell.py', shell]
    elif action == 'test-headless':
        command = ['python3', '.local/share/win4wine/tools/test-shell-headless.py', shell]
    else:
        command = ['python3', '.local/share/win4wine/tools/test-standalone-live.py', '--shell', shell]
    remote_python('import os,subprocess,sys; from pathlib import Path; h=Path.home(); os.chdir(h); '
                  'env=dict(os.environ,PYTHONPATH=str(h/".local/share/win4wine/python"),'
                  'LD_LIBRARY_PATH=str(h/".local/share/win4wine/labwc/lib"),'
                  'XDG_RUNTIME_DIR=os.environ.get("XDG_RUNTIME_DIR",f"/run/user/{os.getuid()}"),'
                  'PATH=str(h/".local/bin")+":"+os.environ.get("PATH","")); '
                  'subprocess.run(sys.argv[1:],env=env,check=True)', args=command)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('source', 'doctor', 'check', 'build-wine', 'build-native', 'smoke-native', 'test-container',
                        'extract', 'preflight', 'deploy', 'prefix', 'register', 'test-headless', 'test-live', 'switch', 'rescue'))
    parser.add_argument('shell', nargs='?', choices=SHELLS)
    parser.add_argument('media', nargs='?', default='')
    args = parser.parse_args()
    if args.action == 'check':
        import ast
        for directory in ('thor', 'tools', 'tests'):
            for path in (ROOT / directory).glob('*.py'):
                ast.parse(path.read_text(), filename=str(path))
        for path in list((ROOT / 'thor').iterdir()) + list((ROOT / 'containers').glob('*.sh')):
            if path.is_file() and path.read_bytes().startswith(b'#!/bin/bash'):
                run('bash', '-n', path)
        print('Python and shell syntax checks passed.')
    elif args.action == 'doctor':
        if sys.version_info < (3, 12):
            raise SystemExit('Python 3.12+ is required on the build host.')
        for tool in ('docker', 'ssh', 'scp', 'git'):
            if not shutil.which(tool):
                raise SystemExit(f'Missing host prerequisite: {tool}')
        run('docker', 'info', '--format', '{{.Architecture}}')
        print(json.dumps(SOURCES, indent=2))
        print('Docker must support linux/amd64 AND linux/arm64; Docker Desktop does by default.')
    elif args.action in ('source', 'build-wine', 'build-native', 'smoke-native', 'test-container', 'preflight', 'deploy'):
        globals()[args.action.replace('-', '_')]()
    elif args.action == 'rescue':
        device_action('rescue')
    elif not args.shell:
        parser.error('This action requires reactos, xp or win7.')
    elif args.action == 'extract':
        extract(args.shell, args.media)
    else:
        device_action(args.action, args.shell)


if __name__ == '__main__':
    try:
        main()
    except subprocess.CalledProcessError as error:
        raise SystemExit(f'Command failed (exit {error.returncode}). See the output above; no automatic reset or cleanup is performed.')
