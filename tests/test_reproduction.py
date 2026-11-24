import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import tarfile
import shutil
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load(name, file):
    spec = importlib.util.spec_from_file_location(name, ROOT / file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


cli = load('thor_cli', 'tools/thor.py')
installer = load('user_install', 'thor/install-user.py')
audit = load('public_audit', 'tools/audit-public.py')
history = load('public_history', 'tools/rewrite-public-history.py')
prepare = load('prepare_shell', 'thor/prepare-shell.py')


class ReproductionTests(unittest.TestCase):
    def test_upstream_cursor_cli_argument_order(self):
        assets, output = Path('/assets'), Path('/icons/theme')
        self.assertEqual(prepare.cursor_arguments('reactos', assets, output),
                         ['/assets/resources/user32.dll', '/icons/theme', '--reactos'])
        self.assertEqual(prepare.cursor_arguments('xp', assets, output),
                         ['/assets/resources/user32.dll', '/icons/theme'])
        self.assertEqual(prepare.cursor_arguments('win7', assets, output),
                         ['--win7', '/assets/cursors/user32.dll', '/assets/cursors', '/icons/theme'])

    def test_target_requires_explicit_host(self):
        with patch.dict(os.environ, {}, clear=True), self.assertRaises(SystemExit):
            cli.target()

    def test_target_rejects_shell_and_option_injection(self):
        for value in ('-oProxyCommand=bad', 'host;bad', 'host bad', '$(bad)', 'host\nbad'):
            with self.subTest(value=value), patch.dict(os.environ, {'THOR_HOST': value}, clear=True):
                with self.assertRaises(SystemExit):
                    cli.target()

    def test_custom_connection(self):
        with patch.dict(os.environ, {'THOR_HOST': 'my-thor.local', 'THOR_USER': 'gamer', 'THOR_SSH_KEY': '~/private key'}, clear=True):
            self.assertEqual(cli.target(), 'gamer@my-thor.local')
            self.assertIn(str(Path('~/private key').expanduser()), cli.ssh_options())

    def test_remote_python_quotes_arguments(self):
        with patch.dict(os.environ, {'THOR_HOST': 'thor.local'}, clear=True), patch.object(cli, 'run') as run:
            cli.remote_python('print("safe")', args=['a path; not a command'])
            command = run.call_args.args[-1]
            import shlex
            self.assertEqual(shlex.split(command), ['python3', '-c', 'print("safe")', 'a path; not a command'])

    def test_disruptive_actions_require_opt_in(self):
        for action in ('switch', 'rescue'):
            with patch.dict(os.environ, {}, clear=True), patch.object(cli, 'remote_python') as remote:
                with self.assertRaises(SystemExit):
                    cli.device_action(action, 'win7')
                remote.assert_not_called()

    def test_source_refuses_unknown_directory(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(cli, 'SOURCE', Path(temp)):
            with self.assertRaises(SystemExit):
                cli.source()

    def test_source_skips_matching_pin(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)
            (path / '.thor-source.json').write_text(json.dumps(cli.SOURCES['win4wine']))
            with patch.object(cli, 'SOURCE', path), patch.object(cli, 'download') as download:
                cli.source()
                download.assert_not_called()

    def test_media_must_be_user_supplied(self):
        with patch.object(cli, 'source'), patch.object(cli, 'docker_image') as docker:
            with self.assertRaises(SystemExit):
                cli.extract('xp', '')
            docker.assert_not_called()

    def test_rendered_root_helpers_follow_actual_account(self):
        for name in ('standalone-test-control.py', 'switch-win4wine-session.py'):
            text = installer.render((ROOT / 'thor' / name).read_text(), Path('/var/home/gamer'), 'gamer', 2001)
            self.assertNotIn('/run/user/1000', text)
            self.assertNotIn('/var/home/armada', text)
            if name == 'standalone-test-control.py':
                self.assertIn('User=gamer', text)
                self.assertIn('armada-plasma.desktop', text)  # stock recovery session must NOT be renamed
            else:
                self.assertIn("'gamer'", text)
                self.assertIn('/run/user/2001', text)

    def test_generated_session_entries_use_actual_home(self):
        for shell in cli.SHELLS:
            text = installer.render((ROOT / f'thor/armada-{shell}.desktop').read_text(), Path('/home/player'), 'player', 1002)
            self.assertIn(f'Exec=/home/player/.local/bin/{shell}-standalone-session', text)

    def test_launchers_preserve_safety_policy(self):
        for shell in cli.SHELLS:
            text = (ROOT / f'thor/{shell}-standalone-session').read_text()
            for expected in ('WLR_NO_HARDWARE_CURSORS=1', 'flock -w 20', 'card*-DP-*/status', 'XDG_SEAT'):
                self.assertIn(expected, text)
        text = (ROOT / 'thor/labwc-rc.xml').read_text()
        self.assertIn('<autoEnableOutputs>no</autoEnableOutputs>', text)
        self.assertIn('<sendEventsMode>no</sendEventsMode>', text)

    def test_audit_detects_secrets_without_printing_them(self):
        credential = b'ghp_' + b'A' * 36
        self.assertTrue(audit.problems('test.txt', credential))
        self.assertTrue(audit.problems('thing.dll', b'MZ' + b'\0' * 20))
        self.assertTrue(audit.problems('.build/file', b'generated'))
        self.assertFalse(audit.problems('thor/test.py', b'print("hello")'))

    def test_build_context_excludes_runtime_and_media(self):
        lines = (ROOT / '.dockerignore').read_text().splitlines()
        self.assertIn('*', lines)
        self.assertEqual([x for x in lines if x.startswith('!')], [
            '!containers/', '!containers/wine.Dockerfile', '!containers/native.Dockerfile',
            '!containers/build-wine.sh', '!containers/smoke-native.sh',
            '!containers/test.Dockerfile', '!containers/test-runtime.sh'])

    def test_container_stages_home_files_as_the_unprivileged_account(self):
        script = (ROOT / 'containers/test-runtime.sh').read_text()
        self.assertIn('runuser -u player -- mkdir -p /home/player/.local/state/thor-bootstrap', script)
        self.assertIn('runuser -u player -- cp /artifacts/native/assets-reactos.tar.gz', script)
        for line in script.splitlines():
            if line.startswith(('mkdir ', 'cp ', 'chown ')):
                self.assertNotIn('/home/player/', line, 'Root must not create an unwritable parent in the test home')

    def test_history_scrubber_redacts_every_occurrence(self):
        value = history.scrub(b'private/path and private/path', {'private/path': 'public/example'})
        self.assertEqual(value, b'public/example and public/example')
        with self.assertRaises(ValueError):
            history.scrub(b'any text', {'': 'bad'})

    def test_history_replay_refuses_existing_destination(self):
        with tempfile.TemporaryDirectory() as temp, self.assertRaises(SystemExit):
            history.replay(ROOT, Path(temp), {})

    def test_fresh_user_install_renders_commands_without_root_or_session_switch(self):
        with tempfile.TemporaryDirectory() as temp:
            work = Path(temp)
            home, stage = work / 'gamer-home', work / 'stage'
            home.mkdir()
            stage.mkdir()
            (stage / 'source').mkdir()
            (stage / 'source/session').mkdir()
            shutil.copytree(ROOT / 'thor', stage / 'thor', ignore=shutil.ignore_patterns('__pycache__'))
            contents = {
                'wine-runtime.tar.gz': ['wine-install/lib/placeholder', 'wine-install/share/placeholder', 'bridge/shell-ui-probe-x64.exe'],
                'rootfs.tar': ['usr/lib/x86_64-linux-gnu/placeholder'],
                'box64.tar.gz': ['usr/local/bin/box64'],
                'labwc-arm64.tar.gz': ['labwc/bin/labwc', 'labwc/bin/Xvfb'],
                'native-support.tar.gz': ['tools/grim', 'tools/wlrctl', 'tools/wlr-randr', 'python/Xlib/placeholder'],
            }
            import io
            for archive, names in contents.items():
                with tarfile.open(stage / archive, 'w:gz') as tar:
                    for name in names:
                        info = tarfile.TarInfo(name)
                        info.size = 4
                        info.mode = 0o755
                        tar.addfile(info, io.BytesIO(b'test'))
            calls = []
            def execute(args, **kwargs):
                calls.append(args)
                if args[0] == 'tar':
                    with tarfile.open(args[2]) as tar:
                        tar.extractall(args[4], filter='data')
                else:
                    self.assertEqual(args[0], 'ldd')
                return SimpleNamespace(returncode=0, stdout='all resolved')
            account = SimpleNamespace(pw_name='gamer', pw_uid=2001)
            with patch.object(installer.os, 'geteuid', return_value=2001), \
                    patch.object(installer.pwd, 'getpwuid', return_value=account), \
                    patch.object(installer.subprocess, 'run', side_effect=execute):
                installer.install(stage, home=home)
                with self.assertRaises(SystemExit):
                    installer.install(stage, home=home)
            worker = (home / '.local/share/win4wine/tools/standalone-test-control.py').read_text()
            self.assertIn('User=gamer', worker)
            self.assertIn('/run/user/2001', worker)
            self.assertTrue((home / '.local/share/win4wine/box64-wine/lib').is_symlink())
            self.assertTrue((home / '.local/bin/win7-standalone-session').stat().st_mode & 0o111)
            self.assertTrue((home / '.local/share/win4wine/labwc-config/rc.xml').exists())
            self.assertFalse(any('sudo' in command or 'systemctl' in command for command in calls))


if __name__ == '__main__':
    unittest.main()
