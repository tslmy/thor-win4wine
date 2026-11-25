"""Plug/unplug decisions of thor/win4wine-external, without a device."""
import runpy
import tempfile
import unittest
from pathlib import Path
from unittest import mock

external = runpy.run_path(str(Path(__file__).resolve().parent.parent / 'thor/win4wine-external'))


class LinkTest(unittest.TestCase):
    def test_flapping_is_ignored_until_the_state_settles(self):
        link = external['Link']()
        readings = [True, False, True, True, True, True, False, True, False, False, False]
        self.assertEqual([link.update(r) for r in readings],
                         [None, None, None, None, True, None, None, None, None, None, False])

    def test_starting_disconnected_is_not_an_unplug(self):
        link = external['Link']()
        self.assertEqual([link.update(False) for _ in range(5)], [None] * 5)


class OpenWindowsTest(unittest.TestCase):
    shell = [('w7-explorer.exe', 'Progman', 'Program Manager'),
             ('w7-explorer.exe', 'Shell_TrayWnd', ''),
             ('w7-explorer.exe', 'DV2ControlHost', 'Start menu'),
             ('w7-explorer.exe', 'Win4WineStartButton', 'Start'),
             ('w7-explorer.exe', 'Desktop User Picture', 'armada'),
             ('org.kde.konsole', '', 'Konsole')]

    def test_shell_and_linux_windows_do_not_block_a_restart(self):
        self.assertEqual(external['users_windows'](self.shell), [])

    def test_folder_program_and_unidentified_windows_block_it(self):
        windows = self.shell + [('w7-explorer.exe', 'CabinetWClass', 'Control Panel'),
                                ('notepad.exe', 'Notepad', 'Untitled'),
                                ('setup.exe', '', '')]
        self.assertEqual(external['users_windows'](windows),
                         ['Control Panel', 'Untitled', 'setup.exe'])


class WatchTest(unittest.TestCase):
    def test_other_shells_are_left_alone(self):
        watch = external['watch']
        for shell in ('xp', 'reactos'):
            def unexpected(*args):
                self.fail(f'acted in a {shell} session')
            fakes = {'session': lambda: ({'shell': shell}, None, {}),
                     'connected': unexpected, 'plugged': unexpected, 'unplugged': unexpected}
            with tempfile.TemporaryDirectory() as runtime, \
                    mock.patch.dict(watch.__globals__, fakes):
                self.assertIsNone(watch({'XDG_RUNTIME_DIR': runtime}))


if __name__ == '__main__':
    unittest.main()
