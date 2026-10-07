"""Session-only appearance settings; no writes to other desktop profiles."""
import json
import os
from pathlib import Path


def configure(state, original=None):
    original = Path(original or os.environ.get('GH0STZK_CONFIG_HOME') or os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config'))
    overlay = state / 'session-config'
    overlay.mkdir(parents=True, exist_ok=True)
    # Keep application preferences, but give GTK/GSettings private writable storage.
    for source in original.iterdir():
        if source.name in ('gtk-3.0', 'gtk-4.0', 'glib-2.0'):
            continue
        target = overlay / source.name
        if not target.exists() and not target.is_symlink():
            target.symlink_to(source)
    for version in ('gtk-3.0', 'gtk-4.0'):
        target = overlay / version
        if not target.is_symlink():
            target.symlink_to(state / 'current' / version)
    (overlay / 'glib-2.0').mkdir(exist_ok=True)
    os.environ.update(GH0STZK_CONFIG_HOME=str(original), XDG_CONFIG_HOME=str(overlay),
                      GSETTINGS_BACKEND='keyfile', GH0STZK_SESSION='1')
    share = Path.home() / '.local/share/gh0stzk-hyprland-visuals/current/share'
    os.environ['XDG_DATA_DIRS'] = str(share) + ':' + os.environ.get('XDG_DATA_DIRS', '/usr/local/share:/usr/share')
    os.environ['XCURSOR_PATH'] = str(share / 'icons') + ':' + str(Path.home() / '.local/share/icons') + ':/usr/share/icons:/usr/share/pixmaps'
    appearance = json.loads((state / 'current/appearance.json').read_text())
    os.environ['XCURSOR_THEME'] = appearance['gtk_cursor']
    os.environ['XCURSOR_SIZE'] = '24'
    # A private GSettings backend selects GTK theme/icons without modifying dconf.
    os.environ.pop('GTK_THEME', None)
    return overlay
