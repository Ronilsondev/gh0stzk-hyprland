#!/usr/bin/env python3
"""Importação determinística de dados; nunca executa código do upstream."""
import argparse
import configparser
import json
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UP = ROOT / 'upstream/gh0stzk-dotfiles'


def variables(path):
    values = {}
    for line in path.read_text().splitlines():
        match = re.match(r'''^([\w]+)=(['"])(.*?)\2''', line)
        if match:
            key, _, value = match.groups()
            value = re.sub(r'\$\{(\w+)\}|\$(\w+)',
                           lambda m: values.get(m[1] or m[2], '$' + (m[1] or m[2])), value)
            values[key] = value
    return values


def ini(path):
    cp = configparser.ConfigParser(interpolation=None, strict=False)
    cp.read(path)
    return {s: dict(cp[s]) for s in cp.sections()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--theme')
    args = ap.parse_args()
    commit = subprocess.check_output(['git', '-C', str(UP), 'rev-parse', 'HEAD'], text=True).strip()
    (ROOT / 'UPSTREAM.json').write_text(json.dumps({
        'url': 'https://github.com/gh0stzk/dotfiles', 'commit': commit,
        'license': 'GPL-3.0', 'retrieved': '2026-10-05',
    }, indent=2) + '\n')
    shutil.copy2(UP / 'LICENSE', ROOT / 'LICENSE')
    for folder in ('fonts',):
        shutil.copytree(UP / 'misc' / folder, ROOT / 'assets' / folder, dirs_exist_ok=True)
    shutil.copytree(UP / 'config/bspwm/config/rofi-themes', ROOT / 'assets/rofi', dirs_exist_ok=True)
    shutil.copytree(UP / 'config/bspwm/config/assets', ROOT / 'assets/menu', dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns('*.mp4'))
    for part in ('profilecard', 'player', 'cheatsheet'):
        dest = ROOT / 'assets/widgets'
        dest.mkdir(exist_ok=True)
        shutil.copy2(UP / f'config/bspwm/eww/{part}/{part}.scss', dest)
    for src in sorted((UP / 'config/bspwm/rices').iterdir()):
        if not src.is_dir() or (args.theme and src.name != args.theme):
            continue
        v = variables(src / 'theme-config.bash')
        dest = ROOT / 'themes' / src.name
        dest.mkdir(exist_ok=True)
        shutil.copytree(src / 'walls', dest / 'walls', dirs_exist_ok=True)
        shutil.copy2(src / 'preview.webp', dest)
        bars = ini(src / 'config.ini') if (src / 'config.ini').exists() else {}
        modules = ini(src / 'modules.ini') if (src / 'modules.ini').exists() else {}
        # Only data used by the renderer, never upstream commands.
        keep = ('label', 'format', 'font-', 'label-', 'format-', 'time', 'date', 'ramp-')
        clean_modules = {k.removeprefix('module/'): {a: b for a, b in d.items()
                        if a == 'type' or a.startswith(keep)} for k, d in modules.items()}
        # Drop embedded Polybar action handlers; keep their visible label.
        for mod in clean_modules.values():
            for key, val in mod.items():
                mod[key] = re.sub(r'%\{A\d*:[^}]*\}|%\{A\}', '', val)
        info = {'name': src.name, 'source_commit': commit, 'palette': {
            k: val for k, val in v.items() if k not in ('CUSTOM_DIR', 'DEFAULT_WALL', 'ANIMATED_WALL')},
            'wallpaper': 'walls/' + Path(v['DEFAULT_WALL']).name,
            'bar_colors': bars.get('color', {}),
            'bars': [{k: val for k, val in b.items() if k not in
                      ('monitor', 'monitor-strict', 'wm-restack', 'enable-ipc')}
                     | {'name': s[4:]} for s, b in bars.items() if s.startswith('bar/')],
            'modules': clean_modules, 'status': 'migrado; teste gráfico pendente'}
        if src.name in ('andrea', 'z0mbi3'):
            shutil.copytree(src / 'bar/images', dest / 'images', dirs_exist_ok=True)
            info['composition'] = src.name
        (dest / 'theme.json').write_text(json.dumps(info, ensure_ascii=False, indent=2) + '\n')
        print(f'{src.name}: {len(info["bars"])} painéis Polybar, {len(list((dest / "walls").iterdir()))} wallpapers')


if __name__ == '__main__':
    main()
