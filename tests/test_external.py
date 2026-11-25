"""Plug/unplug decisions of thor/win4wine-external, without a device."""
import runpy
import tempfile
import unittest
from pathlib import Path
from unittest import mock

external = runpy.run_path(str(Path(__file__).resolve().parent.parent / 'thor/win4wine-external'))


def output(width, height, scale, transform='normal'):
    return {'enabled': True, 'scale': scale, 'transform': transform,
            'modes': [{'width': width, 'height': height, 'current': True}]}


class PlacesTest(unittest.TestCase):
    both = {'DSI-2': output(1080, 1920, 1.5, '270'), 'DP-1': output(1920, 1080, 1.0)}

    def test_docked_puts_the_monitor_first_without_overlap(self):
        self.assertEqual(external['places'](self.both, 'DP-1'), {'DP-1': 0, 'DSI-2': 1920})

    def test_handheld_primary_puts_the_panel_first_without_overlap(self):
        self.assertEqual(external['places'](self.both, 'DSI-2'), {'DSI-2': 0, 'DP-1': 1280})

    def test_lone_panel_returns_to_the_origin(self):
        alone = {'DSI-2': self.both['DSI-2']}
        self.assertEqual(external['places'](alone, 'DSI-2'), {'DSI-2': 0})


class LinkTest(unittest.TestCase):
    def test_flapping_is_ignored_until_the_state_settles(self):
        link = external['Link']()
        readings = [True, False, True, True, True, True, False, True, False, False, False]
        self.assertEqual([link.update(r) for r in readings],
                         [None, None, None, None, True, None, None, None, None, None, False])

    def test_starting_disconnected_is_not_an_unplug(self):
        link = external['Link']()
        self.assertEqual([link.update(False) for _ in range(5)], [None] * 5)


class WatchTest(unittest.TestCase):
    def test_other_shells_are_left_alone(self):
        watch = external['watch']
        for shell in ('reactos', None):
            def unexpected(*args):
                self.fail(f'acted in a {shell} session')
            fakes = {'session': lambda: ({'shell': shell}, None),
                     'connected': unexpected, 'plugged': unexpected, 'arrange': unexpected}
            with tempfile.TemporaryDirectory() as runtime, \
                    mock.patch.dict(watch.__globals__, fakes):
                self.assertIsNone(watch({'XDG_RUNTIME_DIR': runtime}))


if __name__ == '__main__':
    unittest.main()
