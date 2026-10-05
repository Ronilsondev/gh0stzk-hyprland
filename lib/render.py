"""Renderizadores Wayland. Dados importados são inertes, comandos são explícitos."""
import copy
import html
import json
import re
import shlex
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def lua(value):
    if isinstance(value, dict):
        return '{' + ', '.join('[' + lua(k) + '] = ' + lua(v) for k, v in value.items()) + '}'
    if isinstance(value, list):
        return '{' + ', '.join(map(lua, value)) + '}'
    if isinstance(value, bool):
        return str(value).lower()
    return json.dumps(value, ensure_ascii=False)


def theme(name):
    if not re.fullmatch(r'[a-z0-9]+', name):
        raise ValueError('Nome de tema inválido')
    data = json.loads((ROOT / 'themes' / name / 'theme.json').read_text())
    assert data['name'] == name
    for k in ('bg', 'fg', 'red', 'green', 'blue', 'FOCUSED_BC'):
        if not re.fullmatch(r'#[0-9a-fA-F]{6,8}', data['palette'][k]):
            raise ValueError(f'Cor inválida: {name}/{k}')
    if not (ROOT / 'themes' / name / data['wallpaper']).is_file():
        raise ValueError('Wallpaper ausente')
    return data


def clean(text):
    return re.sub(r'%\{[^}]*\}', '', text).strip('"')


def number(value, default=0):
    m = re.match(r'-?[0-9.]+', str(value))
    return float(m[0]) if m else default


def csscolor(value, colors):
    value = re.sub(r'\$\{color\.([^}]+)\}', lambda m: colors.get(m[1], '#000000'), value)
    if re.fullmatch(r'#[\da-fA-F]{8}', value):  # Polybar uses ARGB, GTK uses RGBA.
        value = '#' + value[3:] + value[1:3]
    return value if re.fullmatch(r'#[\da-fA-F]{6,8}', value) else 'transparent'


def module(name, original, ident, palette):
    """Explicit backend mapping; no commands are translated from the source."""
    cmd = lambda s: '@CTL@ ' + s
    name = {'cpu': 'cpu_bar', 'memory': 'memory_bar', 'colorpick': 'colorpicker'}.get(name, name)
    mapping = {'bspwm': 'hyprland/workspaces', 'title': 'hyprland/window',
               'cpu_bar': 'cpu', 'memory_bar': 'memory', 'filesystem': 'disk',
               'date': 'clock', 'pulseaudio': 'pulseaudio', 'battery': 'battery',
               'network': 'network', 'brightness': 'backlight', 'xkeyboard': 'hyprland/language',
               'bluetooth': 'bluetooth', 'tray': 'tray', 'mpd': 'mpris'}
    base = mapping.get(name, 'custom/' + ident)
    key = base + '#' + ident if name in mapping else base
    prefix = clean(original.get('format-prefix', original.get('format-volume-prefix', '')))
    options = {
        'bspwm': {'format': '{icon}', 'format-icons': {
            'active': clean(original.get('label-focused', '●')).replace('%name%', '●').replace('%icon%', '●'),
            'default': clean(original.get('label-occupied', '●')).replace('%name%', '●').replace('%icon%', '●'),
            'urgent': clean(original.get('label-urgent', '!')).replace('%name%', '!').replace('%icon%', '!'),
            'empty': clean(original.get('label-empty', '○')).replace('%name%', '○').replace('%icon%', '○')},
            'all-outputs': False, 'persistent-workspaces': {'*': 5}},
        'title': {'format': '{}', 'max-length': 24, 'separate-outputs': True},
        'cpu_bar': {'format': prefix + '{usage}%', 'interval': 3},
        'memory_bar': {'format': prefix + '{used:0.1f}G', 'interval': 5},
        'filesystem': {'format': prefix + '{used}', 'path': '/', 'interval': 60},
        'date': {'format': '{:' + clean(original.get('time', '%H:%M')).replace('%P', '%p') + '}',
                 'format-alt': '{:%a, %d %b %Y}', 'tooltip-format': '<tt>{calendar}</tt>'},
        'pulseaudio': {'format': prefix + ' {volume}%', 'format-muted': '󰝟',
                      'on-click': cmd('volume mute'), 'on-click-right': cmd('app mixer'), 'scroll-step': 5},
        'battery': {'format': '󰁹 {capacity}%', 'format-charging': '󰂄 {capacity}%',
                    'states': {'warning': 25, 'critical': 10}},
        'network': {'format-wifi': ' {signalStrength}%', 'format-ethernet': '󰈀 {bandwidthDownBytes}',
                    'format-disconnected': '󰖪', 'tooltip-format': '{ifname}: {ipaddr}', 'on-click': cmd('network')},
        'brightness': {'format': '󰃠 {percent}%', 'on-scroll-up': cmd('brightness up'),
                       'on-scroll-down': cmd('brightness down')},
        'xkeyboard': {'format': '{short}', 'on-click': cmd('keyboard')},
        'bluetooth': {'format': '', 'format-disabled': '', 'format-connected': ' {num_connections}',
                      'on-click': cmd('bluetooth')},
        'tray': {'icon-size': 14, 'spacing': 6},
        'mpd': {'format': '{title}', 'format-paused': 'Ⅱ {title}', 'title-len': 18,
                'on-click': cmd('widget music'), 'on-click-right': 'playerctl play-pause'},
    }
    if name in options:
        return key, options[name]
    actions = {'launcher': 'launcher', 'power': 'power', 'mplayer': 'widget music',
               'usercard': 'widget launchermenu', 'colorpicker': 'colorpicker', 'r00t': 'app terminal',
               'menu': 'launcher', 'apps': 'launcher', 'browser': 'app browser',
               'filem': 'app files', 'terminal': 'app terminal', 'editor': 'app terminal',
               'fetch': 'widget launchermenu', 'whats': 'app browser'}
    if name in ('vpn', 'target', 'mod'):
        return key, {'exec': cmd('status ' + name), 'return-type': 'json', 'interval': 5}
    if name == 'mpd_control':
        return key, {'format': '    ', 'on-click': 'playerctl play-pause',
                     'on-scroll-up': 'playerctl next', 'on-scroll-down': 'playerctl previous'}
    if name in ('updates', 'weather'):
        return key, {'exec': cmd('status ' + name), 'return-type': 'json', 'interval': 900,
                     'on-click': cmd('updates' if name == 'updates' else 'widget launchermenu')}
    label = clean(original.get('label', ''))
    if name in actions:
        label = label or {'launcher': '󰣇', 'power': '', 'mplayer': '', 'usercard': ''}.get(name, '•')
        return key, {'format': html.escape(label), 'on-click': cmd(actions[name]),
                     **({'on-click-right': cmd('theme')} if name == 'launcher' else {})}
    # Decorative separators / powerline glyphs, not empty placeholder modules.
    if original.get('type') == 'custom/text' or name.startswith(('bi', 'bd', 'sep')) or name == 'dots':
        return key, {'format': html.escape(label), 'tooltip': False}
    raise ValueError(f'Módulo sem migração explícita: {name}')


def custom_composition(data):
    p = data['palette']
    if data['name'] == 'andrea':
        return [{'name': 'andrea', 'width': '97.4%', 'offset-x': '1.3%', 'height': '48', 'offset-y': '10',
                 'background': '#00000000', 'foreground': p['fg'], 'radius': '12',
                 'font-0': 'JetBrainsMono NF:size=9',
                 'modules-left': 'launcher apps date', 'modules-center': 'bspwm',
                 'modules-right': 'mpd mpd_control network pulseaudio updates power'}]
    return [{'name': 'z0mbi3', 'position': 'left', 'width': '47', 'height': '90%',
             'offset-x': '10', 'offset-y': '5%', 'background': p['bg'], 'foreground': p['fg'],
             'radius': '9', 'font-0': 'JetBrainsMono NF:size=10',
             'modules-left': 'launcher bspwm', 'modules-center': '',
             'modules-right': 'tray updates network battery pulseaudio usercard mplayer date power'}]


def render_bars(data, monitors):
    bars = data['bars'] or custom_composition(data)
    configs, styles = [], ['* { border: none; min-height: 0; min-width: 0; }',
                          'tooltip { background: ' + data['palette']['bg'] + '; color: ' + data['palette']['fg'] + '; }']
    for mi, mon in enumerate(monitors):
        w, h = mon['width'] / mon.get('scale', 1), mon['height'] / mon.get('scale', 1)
        if mon.get('transform', 0) % 2:
            w, h = h, w
        for bi, bar in enumerate(bars):
            position = bar.get('position', 'bottom' if bar.get('bottom') == 'true' else 'top')
            vert = position in ('left', 'right')
            size = lambda v, axis: round(number(v) * axis / 100) if '%' in str(v) else round(number(v))
            bw = size(bar.get('width', '100%'), w)
            bh = size(bar.get('height', '30'), h)
            x, y = size(bar.get('offset-x', '0'), w), size(bar.get('offset-y', '0'), h)
            border = int(number(bar.get('border-size', 0)))
            name = f"{data['name']}-{bi}"
            cfg = {'name': name, 'layer': 'top', 'position': position, 'exclusive': False,
                   'passthrough': False, 'fixed-center': bar.get('fixed-center', 'true') == 'true',
                   'output': mon['name'], 'width': bw, 'height': bh + (0 if vert else 2 * border),
                   'margin-left': x, 'margin-right': max(0, round(w - x - bw)) if not vert else 0,
                   'margin-top': y if position != 'bottom' else 0,
                   'margin-bottom': y if position == 'bottom' else (max(0, round(h-y-bh)) if vert else 0)}
            colors = data['bar_colors']
            selector = f'window#waybar.{name}'
            font = bar.get('font-0', 'JetBrainsMono Nerd Font:size=10').strip('"')
            family = font.split(':')[0]
            fs = re.search(r'(pixel)?size=([\d.]+)', font)
            fontsize = number(fs[2]) * (1 if fs and fs[1] else 4 / 3) if fs else 13
            styles.append(f'{selector} {{ background: {csscolor(bar.get("background", data["palette"]["bg"]), colors)}; '
                          f'color: {csscolor(bar.get("foreground", data["palette"]["fg"]), colors)}; '
                          f'border: {border}px solid {csscolor(bar.get("border-color", "#00000000"), colors)}; '
                          f'border-radius: {number(bar.get("radius", 0))}px; '
                          f'font-family: "{family}", "Material Design Icons Desktop", "Font Awesome 6 Free", monospace; '
                          f'font-size: {fontsize:.1f}px; }}')
            serial = 0
            for side in ('left', 'center', 'right'):
                cfg['modules-' + side] = []
                for m in bar.get('modules-' + side, '').split():
                    ident = f'b{bi}m{serial}'
                    serial += 1
                    orig = data['modules'].get(m, {})
                    key, opts = module(m, orig, ident, data['palette'])
                    # Every module gets a stable unique instance, including repeated separators.
                    cfg['modules-' + side].append(key)
                    cfg[key] = opts
                    cssid = key.replace('hyprland/', '').replace('/', '-').replace('#', '.')
                    s = f'{selector} #{cssid}'
                    fg = next((orig[k] for k in ('label-foreground', 'format-foreground', 'format-volume-foreground') if k in orig), None)
                    bg = next((orig[k] for k in ('label-background', 'format-background', 'format-volume-background') if k in orig), None)
                    props = []
                    if fg:
                        props.append('color: ' + csscolor(fg, colors))
                    if bg:
                        props.append('background: ' + csscolor(bg, colors))
                    if m == 'bspwm':
                        styles += [f'{s} button {{ padding: 0 6px; background: transparent; color: {data["palette"]["blackb"]}; }}',
                                   f'{s} button.active {{ color: {data["palette"]["yellow"]}; }}']
                    if m.startswith(('bi', 'bd')) and orig.get('type') == 'custom/text':
                        props.append('font-family: "MesloLGS NF"; font-size: 23px; padding: 0')
                    if props:
                        styles.append(s + ' { ' + '; '.join(props) + '; }')
                    if vert:
                        if m == 'date':
                            opts['format'] = '{:%H\n%M}'
                        if m in ('network', 'battery', 'pulseaudio'):
                            opts['format'] = {'network': '', 'battery': '󰁹', 'pulseaudio': ''}[m]
                            if m == 'network':
                                opts['format-wifi'], opts['format-ethernet'] = '', '󰈀'
                        styles.append(s + ' { padding: 5px 0; }')
                    # The two Eww bar themes ship raster icons; keep those actual assets.
                    if data['name'] in ('andrea', 'z0mbi3'):
                        iconmap = {'andrea': {'launcher': 'zombie', 'apps': 'files', 'power': 'poweroff'},
                                   'z0mbi3': {'usercard': 'usercard', 'mplayer': 'music_player', 'power': 'sys-powermenu'}}
                        icon = iconmap[data['name']].get(m)
                        if icon:
                            opts['format'] = ' '
                            styles.append(s + ' { background-image: url("@ROOT@/themes/' + data['name'] + '/images/' + icon + '.png"); '
                                          'background-repeat: no-repeat; background-position: center; background-size: contain; min-width: 24px; min-height: 24px; }')
            if data['name'] == 'andrea':
                styles.append(f'{selector} .modules-left, {selector} .modules-center, {selector} .modules-right '
                              '{ background: #f5eee6; color: #151515; border: 1px solid #161616; '
                              'border-radius: 12px; padding: 5px 10px; box-shadow: 3px 3px 3px #161616; }')
                styles.append(f'{selector} label {{ padding: 0 5px; }}')
            configs.append(cfg)
    return configs, '\n'.join(styles) + '\n'


def render(name, dest, prefs, monitors=None, wallpaper=None, overrides=None):
    data = copy.deepcopy(theme(name))
    if overrides:
        for key, value in overrides.items():
            if key not in ('BORDER_WIDTH', 'P_CORNER_R', 'P_BLUR', 'P_SHADOWS', 'P_ANIMATIONS', 'P_TERM_OPACITY'):
                raise ValueError('Preferência de tema não suportada: ' + key)
            data['palette'][key] = str(value)
    dest.mkdir(parents=True, exist_ok=True)
    p = data['palette']
    wall = Path(wallpaper) if wallpaper else ROOT / 'themes' / name / data['wallpaper']
    if not wall.is_file() or wall.suffix.lower() not in ('.webp', '.png', '.jpg', '.jpeg'):
        raise ValueError('Wallpaper estático inexistente ou não suportado')
    # A stable local filename avoids config-language injection from custom filenames.
    shutil.copy2(wall, dest / ('wallpaper' + wall.suffix.lower()))
    wallref = '@CURRENT@/wallpaper' + wall.suffix.lower()
    dump(dest / 'selection.json', {'theme': name, 'wallpaper': str(wall)})
    config = {'general': {'layout': 'dwindle', 'gaps_in': 5, 'gaps_out': 5,
                         'border_size': int(p['BORDER_WIDTH']), 'col': {'active_border': p['FOCUSED_BC'], 'inactive_border': p['NORMAL_BC']}},
              'decoration': {'rounding': int(p['P_CORNER_R']), 'blur': {'enabled': p['P_BLUR'] == 'true'},
                             'shadow': {'enabled': p['P_SHADOWS'] == 'true', 'color': p['SHADOW_C']}},
              'animations': {'enabled': p['P_ANIMATIONS'] == '@'}}
    if not 0 <= config['decoration']['rounding'] <= 100 or not 0 <= config['general']['border_size'] <= 20:
        raise ValueError('Borda/arredondamento fora dos limites')
    if not 0.1 <= float(p['P_TERM_OPACITY']) <= 1:
        raise ValueError('Opacidade fora de 0.1–1.0')
    reserved = {side: int(p[side.upper() + '_PADDING']) for side in ('top', 'right', 'bottom', 'left')}
    (dest / 'theme.lua').write_text('hl.config(' + lua(config) + ')\nreturn ' + lua(reserved) + '\n')
    bars, css = render_bars(data, monitors or [{'name': '*', 'width': 1600, 'height': 900, 'scale': 1}])
    dump(dest / 'waybar.json', bars)
    (dest / 'waybar.css').write_text(css)
    rofi = dest / 'rofi'
    shutil.copytree(ROOT / 'assets/rofi', rofi, dirs_exist_ok=True)
    aliases = {'font': 'rofi_font', 'background': 'rofi_background', 'bg-alt': 'rofi_bg_alt',
               'background-alt': 'rofi_background_alt', 'foreground': 'rofi_fg', 'selected': 'rofi_selected',
               'active': 'rofi_active', 'urgent': 'rofi_urgent'}
    (rofi / 'shared.rasi').write_text('* {\n' + '\n'.join(f'  {k}: ' + (json.dumps(p[v]) if k == 'font' else p[v]) + ';' for k, v in aliases.items()) + '\n}\n')
    for path in rofi.glob('*.rasi'):
        text = path.read_text().replace('~/.cache/rofi_header.webp', wallref)
        text = re.sub(r'~/.config/bspwm/config/assets/', '@ROOT@/assets/menu/', text)
        # Only load drun/dmenu on Wayland; window switching uses compositor IPC.
        text = text.replace('"drun,run,window"', '"drun,run"')
        if path.name == 'RiceSelector.rasi':
            text = re.sub(r'(main-bg:).*?;', r'\1 ' + p['bg'] + ';', text)
            text = re.sub(r'(main-fg:).*?;', r'\1 ' + p['fg'] + ';', text)
            text = re.sub(r'(select-bg:).*?;', r'\1 ' + p['blue'] + ';', text)
        path.write_text(text)
    dun = ['[global]', 'force_xwayland = false', 'follow = mouse', 'width = 330', 'height = (0, 300)']
    for key in ('origin', 'offset', 'transparency', 'corner_radius', 'font'):
        dun.append(key + ' = ' + p['dunst_' + key])
    dun += ['frame_width = ' + p['dunst_border'], 'frame_color = "' + p['dunst_frame_color'] + '"',
            'icon_theme = "' + p['dunst_icon_theme'] + ',Papirus-Dark,Adwaita"', 'format = "<b>%s</b>\\n%b"']
    for urgency, color, timeout in [('low', p['green'], 3), ('normal', p['fg'], 5), ('critical', p['red'], 0)]:
        dun += [f'[urgency_{urgency}]', f'background = "{p["bg"]}"', f'foreground = "{color}"', f'timeout = {timeout}']
    (dest / 'dunstrc').write_text('\n'.join(dun) + '\n')
    kitty = [f'font_family {p["term_font_name"]}', f'font_size {p["term_font_size"]}',
             'linux_display_server wayland', f'foreground {p["fg"]}', f'background {p["bg"]}',
             f'background_opacity {p["P_TERM_OPACITY"]}', f'cursor {p["fg"]}',
             f'selection_background {p["magenta"]}', f'selection_foreground {p["bg"]}',
             'enable_audio_bell no', 'window_padding_width 8', 'shell_integration disabled']
    names = ['black', 'red', 'green', 'yellow', 'blue', 'magenta', 'cyan', 'white']
    for i, key in enumerate(names + [k + 'b' for k in names]):
        kitty.append(f'color{i} {p[key]}')
    (dest / 'kitty.conf').write_text('\n'.join(kitty) + '\n')
    hc = lambda k: 'rgb(' + p[k].lstrip('#')[:6] + ')'
    (dest / 'hyprlock.conf').write_text(f'''background {{
    monitor =
    path = {wallref}
    blur_passes = 2
}}
input-field {{
    monitor =
    size = 280, 55
    position = 0, -100
    outer_color = {hc('sl_ring')}
    inner_color = {hc('sl_bg')}
    font_color = {hc('sl_fg')}
    check_color = {hc('sl_verify')}
    fail_color = {hc('sl_wrong')}
    font_family = {p['term_font_name']}
    placeholder_text = Senha
    rounding = {p['P_CORNER_R']}
}}
label {{
    monitor =
    text = $TIME
    color = {hc('sl_date')}
    font_size = 64
    font_family = {p['term_font_name']}
    position = 0, 80
}}
''')
    shutil.copy2(ROOT / 'config/hypridle.conf', dest / 'hypridle.conf')
    eww = dest / 'eww'
    shutil.copytree(ROOT / 'config/eww', eww, dirs_exist_ok=True)
    for path in (ROOT / 'assets/widgets').glob('*.scss'):
        shutil.copy2(path, eww)
    (eww / 'colors.scss').write_text('\n'.join(f'${k}: {p[v]};' for k, v in {
        'bg': 'bg', 'bg-alt': 'accent_color', 'fg': 'fg', 'black': 'blackb', 'red': 'red',
        'green': 'green', 'yellow': 'yellow', 'blue': 'blue', 'magenta': 'magenta', 'cyan': 'cyan', 'archicon': 'arch_icon'}.items()) + '\n')
    dump(dest / 'appearance.json', {k: p[k] for k in ('gtk_theme', 'gtk_icons', 'gtk_cursor')})
    return data


def materialize(dest, current, ctl=None):
    replacements = {'@ROOT@': str(ROOT), '@CURRENT@': str(current),
                    '@CTL@': shlex.quote(str(ctl or ROOT / 'bin/gh0stzk'))}
    for path in dest.rglob('*'):
        if path.suffix in ('.json', '.lua', '.rasi', '.conf', '.css', '.scss', '.yuck') or path.name == 'dunstrc':
            text = path.read_text()
            for a, b in replacements.items():
                # JSON contains shell commands and needs its own escaping layer.
                text = text.replace(a, json.dumps(b)[1:-1] if path.suffix == '.json' else b)
            path.write_text(text)
