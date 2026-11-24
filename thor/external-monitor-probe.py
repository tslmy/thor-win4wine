#!/usr/bin/env python3
"""Show a conspicuous, temporary X11 test window on the DisplayPort output."""
import os
import select
import subprocess
import time
from Xlib import X, Xatom, Xutil, display
from Xlib.ext import randr

manager = dict(line.split('=', 1) for line in subprocess.check_output(
    ['systemctl', '--user', 'show-environment'], text=True).splitlines() if '=' in line)
for name in ('DISPLAY', 'XAUTHORITY'):
    if name in manager:
        os.environ[name] = manager[name]
    else:
        os.environ.pop(name, None)
d = display.Display()
root = d.screen().root
resources = root.xrandr_get_screen_resources_current()
output = None
for ident in resources.outputs:
    info = d.xrandr_get_output_info(ident, resources.config_timestamp)
    name = info.name.decode() if isinstance(info.name, bytes) else info.name
    if name == 'DP-1' and info.crtc:
        output = d.xrandr_get_crtc_info(info.crtc, resources.config_timestamp)
        break
if output is None:
    raise SystemExit('DisplayPort is not connected/enabled in Xwayland.')
width, height = min(1100, output.width - 100), min(650, output.height - 100)
x, y = output.x + 50, output.y + 50
window = root.create_window(x, y, width, height, 0, X.CopyFromParent, X.InputOutput,
                           X.CopyFromParent, background_pixel=0x204080,
                           event_mask=X.ExposureMask | X.StructureNotifyMask)
window.set_wm_name('DisplayPort live test - ReactOS standalone')
window.set_wm_class('win4wine-dp-probe', 'Win4wineDisplayProbe')
window.set_wm_normal_hints(flags=Xutil.USPosition | Xutil.USSize, x=x, y=y, width=width, height=height)
# Synthetic Wine identity, as used by upstream's compositor tests: Linux-window
# cascading otherwise relocates this diagnostic window onto the primary panel.
window.change_property(d.intern_atom('_WIN4WINE_CLASS'), Xatom.STRING, 8, b'Win4WineDisplayProbe')
window.change_property(d.intern_atom('_WIN4WINE_HWND'), Xatom.CARDINAL, 32, [window.id])
window.change_property(d.intern_atom('_MOTIF_WM_HINTS'), d.intern_atom('_MOTIF_WM_HINTS'), 32, [2, 0, 0, 0, 0])
delete = d.intern_atom('WM_DELETE_WINDOW')
window.set_wm_protocols([delete])
gc = window.create_gc(foreground=0xffffff)
window.map()
d.flush()
print(f'DisplayPort test window at {x},{y}, {width}x{height}', flush=True)
end = time.monotonic() + 180
try:
    while time.monotonic() < end:
        if not d.pending_events():
            select.select([d.fileno()], [], [], 1)
            if not d.pending_events():
                continue
        event = d.next_event()
        if event.type == X.Expose:
            window.draw_text(gc, 50, 80, 'EXTERNAL DISPLAYPORT TEST')
            window.draw_text(gc, 50, 120, 'This blue window is on the Dell external monitor.')
            window.draw_text(gc, 50, 160, 'ReactOS remains the only desktop shell.')
            d.flush()
        elif event.type == X.ClientMessage and event.data[1][0] == delete:
            break
finally:
    window.destroy()
    d.flush()
    d.close()
