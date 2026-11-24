#!/usr/bin/env python3
"""Run upstream's integration test against a nested Xwayland session."""
from pathlib import Path
import runpy
import sys
from Xlib import display, error

close = display.Display.close

def close_nested_display(self):
    try:
        close(self)
    except error.ConnectionClosedError:
        # Successful Log Off can shut down the nested X server before the
        # upstream test's finally block closes its own connection.
        pass

display.Display.close = close_nested_display
test = Path.home() / 'win4wine/tests/reactos_session.py'
sys.argv = [str(test), *sys.argv[1:]]
runpy.run_path(str(test), run_name='__main__')
