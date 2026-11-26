"""The docking setup: kanshi profiles, and the settings they rely on."""
import re
import unittest
from pathlib import Path

THOR = Path(__file__).resolve().parent.parent / 'thor'


def profiles():
    text = (THOR / 'kanshi-config').read_text()
    return {name: dict(re.findall(r'^\toutput ("[^"]+"|\S+) (.*)$', body, re.M))
            for name, body in re.findall(r'^profile (\w+) \{\n(.*?)^\}', text, re.M | re.S)}


class DockingTest(unittest.TestCase):
    def test_lower_panel_is_disabled_in_every_profile(self):
        self.assertEqual(sorted(profiles()), ['docked', 'glasses', 'handheld'])
        for outputs in profiles().values():
            self.assertEqual(outputs['DSI-1'], 'disable')

    def test_monitor_is_leftmost_when_docked_and_held_to_1080p(self):
        docked = profiles()['docked']
        monitor = docked['"Dell Inc. DELL U3223QE *"']  # wildcard: no serial number here
        self.assertIn('mode 1920x1080 position 0,0', monitor)
        self.assertIn('position 1920,0', docked['DSI-2'])
        self.assertIn('position 0,0', profiles()['handheld']['DSI-2'])

    def test_glasses_are_leftmost_like_the_monitor(self):
        glasses = profiles()['glasses']
        self.assertIn('mode 1920x1080@60Hz position 0,0', glasses['"Nreal XREAL One Pro*"'])
        self.assertIn('position 1920,0', glasses['DSI-2'])

    def test_docking_shells_start_kanshi_and_pin_no_primary(self):
        for shell in ('win7', 'xp', 'reactos'):
            self.assertIn('kanshi-config', (THOR / f'{shell}-standalone-start').read_text())
        for creator in ('create-win7-standalone.py', 'create-xp-standalone.py', 'prepare-shell.py'):
            self.assertNotIn("'primary'", (THOR / creator).read_text())
        self.assertNotIn('primary', (THOR / 'reactos-standalone.json').read_text())


if __name__ == '__main__':
    unittest.main()
