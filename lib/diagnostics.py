"""Small allowlisted VM report. No environment dump, window titles or raw logs."""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess


def probe(args):
    try:
        p = subprocess.run(list(map(str, args)), capture_output=True, text=True, timeout=12)
        return p.returncode, p.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None, ''


def report(root, state):
    home = str(Path.home())
    def safe(value):
        return str(value).replace(home, '~')
    data = {'session': {k: os.environ.get(k) for k in ('XDG_SESSION_TYPE', 'XDG_CURRENT_DESKTOP', 'XDG_SESSION_DESKTOP', 'GH0STZK_SESSION')},
            'versions': {}, 'missing_commands': [], 'packages': {}, 'processes': [], 'logs': [],
            'graphical_appearance_verified': False}
    manifest = json.loads((root / 'packages.json').read_text())
    data['missing_commands'] = [c for c in manifest['required_commands'] if not shutil.which(c)]
    for package in manifest['official'] + ['eww']:
        rc, value = probe(['pacman', '-Q', package])
        data['packages'][package] = value if rc == 0 else 'ausente/não verificável'
    for command, flag in [('Hyprland','--version'),('waybar','--version'),('rofi','-version'),('dunst','--version'),('eww','--version'),('kitty','--version'),('hyprlock','--version'),('hypridle','--version'),('swaybg','--version')]:
        rc, value = probe([command, flag])
        data['versions'][command] = safe(value.splitlines()[0][:200]) if value else 'não verificável'
    current = state / 'current'
    data['generation'] = safe(current.resolve()) if current.exists() else None
    try:
        selection = json.loads((current / 'selection.json').read_text())
        data['theme'] = selection['theme']
        data['wallpaper_exists'] = Path(selection['wallpaper']).is_file()
        appearance = json.loads((current / 'appearance.json').read_text())
    except (OSError, ValueError):
        appearance = {}
        data['theme'] = None
    data['files'] = {name: (current / name).is_file() for name in ['theme.lua','waybar.json','waybar.css','kitty.conf','dunstrc','hyprlock.conf','hypridle.conf','eww/eww.yuck','eww/eww.scss','rofi/style_1.rasi','gtk-3.0/settings.ini']}
    share = Path.home() / '.local/share/gh0stzk-hyprland-visuals/current/share'
    data['appearance'] = appearance
    data['resources'] = {k: (share / ('themes' if k == 'gtk_theme' else 'icons') / v / ('gtk-3.20/gtk.css' if k == 'gtk_theme' else 'cursors/left_ptr' if k == 'gtk_cursor' else 'index.theme')).is_file() for k,v in appearance.items()}
    data['fonts'] = {}
    for font in ('JetBrainsMono Nerd Font','Terminess Nerd Font Mono','Maple Mono NF','Inconsolata'):
        matched = probe(['fc-match','-f','%{family}',font])[1]
        data['fonts'][font] = {'matched': matched, 'available': font.casefold() in matched.casefold()}
    if os.environ.get('GH0STZK_SESSION') == '1':
        data['gtk_selected'] = {key: probe(['gsettings','get','org.gnome.desktop.interface',key])[1]
                                for key in ('gtk-theme','icon-theme','cursor-theme','font-name')}
    try:
        assets = json.loads((share.parent / 'report.json').read_text())
        data['visual_asset_limitations'] = {key: len(assets[key]) for key in ('omitted_links','broken_links')}
    except (OSError, ValueError, KeyError):
        data['visual_asset_limitations'] = 'relatório ausente'
    data['hyprland_config_expected'] = safe(root / 'config/hyprland.lua')
    data['hyprland_config_running'] = []
    known = {'Hyprland','waybar','dunst','swaybg','eww','kitty','hypridle','hyprlock','wl-paste','gh0stzk'}
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit():
            continue
        try:
            if proc.stat().st_uid != os.getuid():
                continue
            args = (proc / 'cmdline').read_bytes().decode(errors='replace').split('\0')
            name = Path(args[0]).name
            if name not in known:
                continue
            configs = {a: safe(args[i+1]) for i,a in enumerate(args[:-1]) if a in ('--config','-c','-config','-s','-i')}
            data['processes'].append({'name':name,'pid':int(proc.name),'configuration':configs})
            if name == 'Hyprland':
                data['hyprland_config_running'].append(configs.get('--config', configs.get('-c','padrão; não verificável por argv')))
        except (OSError, IndexError):
            continue
    # Only report project session entries, no arbitrary user command lines.
    data['login_entry'] = {}
    for entry in Path('/usr/share/wayland-sessions').glob(f'gh0stzk-{os.getuid()}.desktop'):
        lines = entry.read_text().splitlines()
        data['login_entry'][entry.name] = [safe(l) for l in lines if l.startswith(('Name=','Exec='))]
    rc, errors = probe(['hyprctl','configerrors'])
    data['hyprland_configerrors'] = ('nenhum' if not errors else 'erros presentes: consultar localmente hyprctl configerrors') if rc == 0 else 'compositor não acessível'
    # Logs can contain clipboard data, app metadata or credentials. Report categories and line numbers only.
    patterns = {'missing-file':r'no such file|not found', 'configuration':r'parse|syntax|invalid|config.*error',
                'failed':r'error|failed|fatal|traceback', 'display':r'cannot.*display|failed.*wayland'}
    paths = list(state.glob('*.log'))
    runtime = os.environ.get('XDG_RUNTIME_DIR')
    if runtime:
        paths += list((Path(runtime) / 'hypr').glob('*/hyprland.log'))
    for path in paths:
        try:
            lines = path.read_text(errors='replace').splitlines()[-300:]
            hits = {key: [i+1 for i,line in enumerate(lines) if re.search(pattern,line,re.I)] for key,pattern in patterns.items()}
            if any(hits.values()):
                data['logs'].append({'file':safe(path),'last_300_lines_matches':hits})
        except OSError:
            pass
    print(json.dumps(data, ensure_ascii=False, indent=2))
