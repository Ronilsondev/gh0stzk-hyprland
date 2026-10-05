"""Controle de sessão e temas, com gerações atômicas e processos pertencentes à adaptação."""
import argparse
import contextlib
import fcntl
import getpass
import json
import os
import random
import re
import shlex
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from render import ROOT, dump, lua, materialize, render, theme

CONFIG = Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config')) / 'gh0stzk-hyprland'
STATE = Path(os.environ.get('XDG_STATE_HOME', Path.home() / '.local/state')) / 'gh0stzk-hyprland'
CURRENT = STATE / 'current'
CTL = ROOT / 'bin/gh0stzk'


def run(args, check=True, **kwargs):
    return subprocess.run([str(x) for x in args], check=check, capture_output=True, timeout=kwargs.pop('timeout', 15), **kwargs)


def output(args, default=''):
    try:
        p = run(args, check=False)
        return p.stdout.decode(errors='replace').strip() if p.returncode == 0 else default
    except (OSError, subprocess.TimeoutExpired):
        return default


def prefs():
    data = json.loads((ROOT / 'config/preferences.json').read_text())
    if (CONFIG / 'preferences.json').exists():
        data.update(json.loads((CONFIG / 'preferences.json').read_text()))
    for key in ('terminal', 'files', 'browser', 'mixer'):
        if not isinstance(data[key], list) or not data[key] or not all(isinstance(a, str) and '\n' not in a for a in data[key]):
            raise ValueError(f'{key} precisa ser uma lista de argumentos')
    return data


def selected():
    try:
        return json.loads((CURRENT / 'selection.json').read_text())
    except FileNotFoundError:
        return {'theme': 'emilia', 'wallpaper': None}


def require_session():
    if not os.environ.get('HYPRLAND_INSTANCE_SIGNATURE'):
        raise RuntimeError('Esta ação exige uma sessão Hyprland. Use --offline apenas para preparar um tema.')


def monitors():
    require_session()
    return json.loads(run(['hyprctl', '-j', 'monitors']).stdout)


@contextlib.contextmanager
def locked(name='theme'):
    STATE.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (STATE / (name + '.lock')).open('a') as file:
        fcntl.flock(file, fcntl.LOCK_EX)
        yield


def atomic_json(path, data):
    temp = path.with_name(path.name + '.tmp')
    dump(temp, data)
    os.replace(temp, path)


def link(target, name):
    temp = STATE / (name + '.tmp')
    temp.unlink(missing_ok=True)
    temp.symlink_to(target)
    os.replace(temp, STATE / name)


def validate_generation(path):
    for file in path.rglob('*.json'):
        json.loads(file.read_text())
    if shutil.which('luac'):
        run(['luac', '-p', path / 'theme.lua'])
    bars = json.loads((path / 'waybar.json').read_text())
    if not bars:
        raise ValueError('Tema sem barras')
    for bar in bars:
        for side in ('left', 'center', 'right'):
            for mod in bar['modules-' + side]:
                if mod not in bar:
                    raise ValueError('Módulo indefinido: ' + mod)
    if shutil.which('rofi'):
        # dump-theme parses styles without opening a menu.
        for file in (path / 'rofi').glob('*.rasi'):
            if file.name != 'shared.rasi':
                run(['rofi', '-no-config', '-theme', file, '-dump-theme'])


def process_identity(pid):
    try:
        proc = Path('/proc') / str(pid)
        if proc.stat().st_uid != os.getuid():
            return None
        # comm may contain spaces/parentheses; starttime is field 22.
        fields = (proc / 'stat').read_text().rsplit(')', 1)[1].split()
        if fields[0] == 'Z':
            return None
        return fields[19]
    except (OSError, IndexError):
        return None


def registry():
    signature = re.sub(r'[^a-zA-Z0-9_-]', '_', os.environ.get('HYPRLAND_INSTANCE_SIGNATURE', 'offline'))
    return STATE / ('processes-' + signature + '.json')


def records():
    try:
        return json.loads(registry().read_text())
    except FileNotFoundError:
        return {}


def alive(record):
    return record and process_identity(record['pid']) == record['start']


def stop(name):
    recs = records()
    rec = recs.get(name)
    if alive(rec):
        os.kill(rec['pid'], signal.SIGTERM)
        for _ in range(30):
            if not alive(rec):
                break
            time.sleep(.05)
        else:
            raise RuntimeError(f'{name} não encerrou; não iniciarei uma cópia duplicada')
    recs.pop(name, None)
    atomic_json(registry(), recs)


def start(name, args, required=True, restart=False):
    recs = records()
    if alive(recs.get(name)):
        if not restart:
            return
        stop(name)
    if not shutil.which(str(args[0])):
        if required:
            raise RuntimeError('Comando ausente: ' + str(args[0]))
        return
    with (STATE / (name + '.log')).open('ab') as log:
        proc = subprocess.Popen([str(x) for x in args], stdout=log, stderr=log, start_new_session=True)
    time.sleep(.4)
    if proc.poll() is not None:
        if required:
            raise RuntimeError(f'{name} encerrou ao iniciar; veja {STATE / (name + ".log")}')
        return
    recs = records()
    recs[name] = {'pid': proc.pid, 'start': process_identity(proc.pid), 'args': list(map(str, args))}
    atomic_json(registry(), recs)


def foreign_process(name):
    own = {r['pid'] for r in records().values() if alive(r)}
    for pid in output(['pgrep', '-u', str(os.getuid()), '-x', name]).split():
        if int(pid) not in own:
            return True
    return False


def notification_owner():
    reply = output(['busctl', '--user', 'call', 'org.freedesktop.DBus', '/org/freedesktop/DBus',
                    'org.freedesktop.DBus', 'NameHasOwner', 's', 'org.freedesktop.Notifications'])
    return reply == 'b true'


def services(restart=True):
    require_session()
    wall = next(CURRENT.glob('wallpaper.*'))
    start('wallpaper', ['swaybg', '-i', wall, '-m', 'fill'], restart=restart)
    if foreign_process('waybar'):
        raise RuntimeError('Já existe Waybar externo. Desative seu autostart antes de usar esta sessão.')
    start('waybar', ['waybar', '-c', CURRENT / 'waybar.json', '-s', CURRENT / 'waybar.css'], restart=restart)
    own_dunst = alive(records().get('dunst'))
    if not own_dunst and notification_owner():
        raise RuntimeError('Outro servidor de notificações já possui o D-Bus; não será encerrado.')
    start('dunst', ['dunst', '-config', CURRENT / 'dunstrc'], restart=restart)
    if shutil.which('eww') and prefs()['widgets']:
        # eww configuration identity is a stable path; this is an isolated daemon.
        if restart:
            run(['eww', '-c', CURRENT / 'eww', 'reload'], check=False)
        else:
            run(['eww', '-c', CURRENT / 'eww', 'daemon'], check=False)
    # Reload only terminals launched with our class and config, not unrelated kitty windows.
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit():
            continue
        try:
            args = (proc / 'cmdline').read_bytes().split(b'\0')
            if process_identity(int(proc.name)) and str(CURRENT / 'kitty.conf').encode() in args:
                os.kill(int(proc.name), signal.SIGUSR1)
        except (OSError, ValueError):
            pass


def apply_theme(name, offline=False, wallpaper=None):
    if not offline:
        require_session()
    with locked():
        data = theme(name)
        preferences = prefs()
        overrides_file = CONFIG / 'themes' / (name + '.json')
        overrides = json.loads(overrides_file.read_text()) if overrides_file.exists() else {}
        saved = STATE / ('wallpaper-' + name + '.json')
        if not wallpaper and saved.exists():
            candidate = json.loads(saved.read_text())['path']
            wallpaper = candidate if Path(candidate).is_file() else None
        generations = STATE / 'generations'
        generations.mkdir(exist_ok=True)
        dest = Path(tempfile.mkdtemp(prefix=time.strftime('%Y%m%d-%H%M%S-'), dir=generations))
        render(name, dest, preferences, monitors() if not offline else None, wallpaper, overrides)
        # Validate against this generation before switching the shared pointer.
        materialize(dest, dest)
        validate_generation(dest)
        # Final configs use the stable pointer for live terminal/widget reloads.
        for path in dest.rglob('*'):
            if path.is_file() and path.suffix not in ('.webp', '.png', '.jpg', '.jpeg'):
                path.write_text(path.read_text().replace(str(dest), str(CURRENT)))
        previous = CURRENT.resolve() if CURRENT.is_symlink() else None
        link(dest, 'current')
        try:
            if not offline:
                run(['hyprctl', 'reload'])
                errors = output(['hyprctl', 'configerrors'])
                if errors.strip():
                    raise RuntimeError('Hyprland rejeitou a configuração: ' + errors)
                services()
        except Exception:
            if previous:
                link(previous, 'current')
                if not offline:
                    run(['hyprctl', 'reload'], check=False)
                    try:
                        services()
                    except Exception as e:
                        print('Recuperação dos serviços incompleta: ' + str(e), file=sys.stderr)
            else:
                CURRENT.unlink(missing_ok=True)
            raise
        if previous and previous != dest:
            link(previous, 'previous')
        atomic_json(saved, {'path': json.loads((dest / 'selection.json').read_text())['wallpaper']})
        print(f'Tema aplicado: {name}' + (' (preparação offline; sem teste gráfico)' if offline else ''))


def choose(items, prompt, style='style_3', icons=None, message=None):
    require_session()
    if not items:
        return None
    text = '\n'.join(str(v) + ('\0icon\x1f' + str(icons[i]) if icons else '') for i, v in enumerate(items))
    args = ['rofi', '-no-config', '-dmenu', '-i', '-no-custom', '-format', 'i', '-p', prompt,
            '-theme', CURRENT / 'rofi' / (style + '.rasi')]
    if message:
        args += ['-mesg', message]
    result = run(args, check=False, input=text.encode(), timeout=86400)
    if result.returncode != 0:
        return None
    try:
        i = int(result.stdout)
        return i if 0 <= i < len(items) else None
    except ValueError:
        return None


def app(kind, extra=()):
    p = prefs()
    if kind in ('terminal', 'floating', 'scratch'):
        command = list(p['terminal'])
        # The integrated terminal is Kitty. Alternatives may define their own config/arguments.
        if Path(command[0]).name == 'kitty':
            command += ['--config', str(CURRENT / 'kitty.conf'), '--class', 'gh0stzk-' + kind]
        elif kind in ('floating', 'scratch'):
            raise RuntimeError('Scratchpad/flutuante integrado exige Kitty; personalize uma regra no local.lua para outro terminal.')
    else:
        command = list(p[kind])
    if p.get('gtk_environment') and kind == 'files':
        appearance = json.loads((CURRENT / 'appearance.json').read_text())
        os.environ['GTK_THEME'] = appearance['gtk_theme']
    subprocess.Popen(command + list(extra), start_new_session=True)


def dispatch(expr):
    return run(['hyprctl', 'dispatch', expr])


def lockscreen():
    require_session()
    with locked('lockscreen'):
        if not foreign_process('hyprlock'):
            start('hyprlock', ['hyprlock', '-c', CURRENT / 'hyprlock.conf'])


def power(action=None):
    actions = ['bloquear', 'suspender', 'sair', 'reiniciar', 'desligar']
    if action is None:
        icons = ['󰍁', '', '󰗽', '󰜉', '󰐥']
        index = choose(icons, 'Sessão', 'PowerMenu', message='Bloquear · Suspender · Sair · Reiniciar · Desligar')
        if index is None:
            return
        action = actions[index]
    if action not in actions:
        raise ValueError('Ação de energia inválida')
    if action == 'bloquear':
        lockscreen()
    elif action == 'suspender':
        # Hypridle holds the sleep inhibitor until the Wayland session is locked.
        if not alive(records().get('hypridle')):
            raise RuntimeError('Hypridle gerenciado precisa estar ativo para suspender com bloqueio confirmado.')
        run(['systemctl', 'suspend'])
    elif choose(['Cancelar', 'Confirmar'], 'Confirmar', 'style_3',
                message=f'Confirma {action}? Esta ação encerra ou reinicia o sistema.') == 1:
        if action == 'sair':
            if os.environ.get('MANAGERPID') and output(['systemctl', '--user', 'is-active', 'wayland-wm@Hyprland.service']) == 'active':
                run(['uwsm', 'stop'])
            else:
                dispatch('hl.dsp.exit()')
        else:
            run(['systemctl', {'reiniciar': 'reboot', 'desligar': 'poweroff'}[action]])


def screenshot(mode):
    require_session()
    if mode == 'menu':
        icons = ['', '', '󰔝']
        i = choose(icons, 'Captura', 'Screenshot',
                   message='Tela completa · Região selecionada · Janela focada')
        if i is None:
            return
        mode = ['full', 'region', 'window'][i]
    args = ['grim']
    if mode == 'region':
        geometry = output(['slurp'])
        if not geometry:
            return
        args += ['-g', geometry]
    elif mode == 'window':
        win = json.loads(run(['hyprctl', '-j', 'activewindow']).stdout)
        if not win or not win.get('mapped'):
            raise RuntimeError('Nenhuma janela capturável está focada')
        x, y = map(int, win['at'])
        w, h = map(int, win['size'])
        args += ['-g', f'{x},{y} {w}x{h}']
    elif mode != 'full':
        raise ValueError('Tipo de captura inválido')
    pictures = Path(output(['xdg-user-dir', 'PICTURES'], str(Path.home() / 'Pictures')))
    folder = pictures / 'Screenshots'
    folder.mkdir(parents=True, exist_ok=True)
    file = folder / (time.strftime('%Y-%m-%d_%H-%M-%S-') + str(time.time_ns() % 1000000) + '.png')
    run(args + [str(file)])
    run(['wl-copy', '--type', 'image/png'], input=file.read_bytes())
    run(['notify-send', 'Captura salva', str(file)], check=False)


def status(kind):
    if kind == 'vpn':
        active = output(['nmcli', '-t', '-f', 'TYPE,NAME', 'connection', 'show', '--active']).splitlines()
        names = [line.partition(':')[2] for line in active if line.startswith(('vpn:', 'wireguard:', 'tun:'))]
        return {'text': ' ' + ', '.join(names) if names else '', 'tooltip': 'VPNs ativas via NetworkManager'}
    if kind == 'target':
        return {'text': '', 'tooltip': 'Módulo de alvo de pentest não configura hosts automaticamente'}
    if kind == 'mod':
        win = json.loads(output(['hyprctl', '-j', 'activewindow'], '{}'))
        return {'text': 'Full' if win.get('fullscreen') else ('Float' if win.get('floating') else 'Dwindle')}
    if kind == 'updates':
        result = output(['checkupdates'], '')
        return {'text': str(len(result.splitlines())) if result else '0', 'tooltip': 'Pacotes oficiais (checkupdates); clique para consultar'}
    if kind == 'weather':
        source = prefs().get('weather_file')
        if source and Path(source).is_file():
            data = json.loads(Path(source).read_text())
            return {'text': str(data.get('text', ''))[:100], 'tooltip': str(data.get('tooltip', ''))[:300]}
        return {'text': '', 'tooltip': 'Clima não configurado'}
    raise ValueError('Status desconhecido')


def widget_data(kind):
    if kind == 'music':
        art = output(['playerctl', 'metadata', 'mpris:artUrl'])
        # Only local files: no untrusted metadata interpolated into a shell command or CSS URL.
        art = art.removeprefix('file://')
        if not Path(art).is_file() or any(c in art for c in "'\"()\\\n"):
            art = str(ROOT / 'assets/menu/fallback.webp')
        return {'title': output(['playerctl', 'metadata', 'xesam:title'], 'Sem reprodução'),
                'artist': output(['playerctl', 'metadata', 'xesam:artist']),
                'status': output(['playerctl', 'status']), 'art': art}
    return {'user': getpass.getuser(), 'host': socket.gethostname(),
            'uptime': output(['uptime', '-p']), 'os': 'Arch Linux' if Path('/etc/arch-release').exists() else 'Linux',
            'packages': str(len(output(['pacman', '-Qq']).splitlines())) + ' pacotes',
            'weather': status('weather')['text'] or 'Clima: configure weather_file'}


def session():
    require_session()
    with locked('session'):
        if alive(records().get('watcher')):
            return
        run(['dbus-update-activation-environment', '--systemd', 'WAYLAND_DISPLAY', 'XDG_CURRENT_DESKTOP',
             'HYPRLAND_INSTANCE_SIGNATURE'], check=False)
        apply_theme(selected()['theme'])
        if not foreign_process('hypridle'):
            start('hypridle', ['hypridle', '-c', CURRENT / 'hypridle.conf'])
        else:
            print('Hypridle externo detectado; mantido. Menu suspender gerenciado indisponível.', file=sys.stderr)
        if prefs()['clipboard']:
            start('clipboard-text', ['wl-paste', '--type', 'text', '--watch', 'cliphist', 'store'])
            start('clipboard-image', ['wl-paste', '--type', 'image', '--watch', 'cliphist', 'store'])
        if prefs()['widgets'] and shutil.which('eww'):
            run(['eww', '-c', CURRENT / 'eww', 'daemon'], check=False)
        if prefs()['polkit'] == 'auto':
            agents = ['polkit-kde-authentication-agent-1', 'lxqt-policykit-agent', 'polkit-gnome-authentication-agent-1', 'hyprpolkitagent']
            if not any(output(['pgrep', '-u', str(os.getuid()), '-f', '/(' + '|'.join(agents) + ')( |$)']).split()):
                if output(['systemctl', '--user', 'is-active', 'hyprpolkitagent.service']) != 'active':
                    run(['systemctl', '--user', 'start', 'hyprpolkitagent.service'], check=False)
        start('watcher', [CTL, 'watch'])


def watch():
    sig = os.environ['HYPRLAND_INSTANCE_SIGNATURE']
    path = Path(os.environ['XDG_RUNTIME_DIR']) / 'hypr' / sig / '.socket2.sock'
    client = socket.socket(socket.AF_UNIX)
    client.connect(str(path))
    with client.makefile() as stream:
        for event in stream:
            if event.startswith(('monitoradded>>', 'monitorremoved>>', 'monitoraddedv2>>', 'configreloaded>>')):
                # Geometry changes after a manual reload; no compositor reload feedback loop.
                with locked():
                    data = theme(selected()['theme'])
                    from render import render_bars
                    cfg, css = render_bars(data, monitors())
                    text = json.dumps(cfg, ensure_ascii=False, indent=2).replace('@CTL@', json.dumps(shlex.quote(str(CTL)))[1:-1])
                    (CURRENT / 'waybar.json').write_text(text)
                    (CURRENT / 'waybar.css').write_text(css.replace('@ROOT@', str(ROOT)))
                    start('waybar', ['waybar', '-c', CURRENT / 'waybar.json', '-s', CURRENT / 'waybar.css'], restart=True)


def main(argv=None):
    ap = argparse.ArgumentParser(description='Desktop gh0stzk para Hyprland (adaptação independente)')
    ap.add_argument('action', choices=['theme', 'rollback', 'refresh', 'wallpaper', 'launcher', 'launcher-style',
        'app', 'scratch', 'volume', 'brightness', 'media', 'network', 'bluetooth', 'clipboard', 'lock', 'power',
        'screenshot', 'keyboard', 'windows', 'help', 'widget', 'widget-data', 'status', 'updates', 'colorpicker',
        'edit-theme', 'bar', 'session', 'watch', 'list', 'prepare'])
    ap.add_argument('args', nargs='*')
    ap.add_argument('--offline', action='store_true')
    args = ap.parse_args(argv)
    a, values = args.action, args.args
    if a in ('theme', 'prepare', 'refresh'):
        name = values[0] if values else selected()['theme']
        if a == 'theme' and not values:
            names = sorted(p.name for p in (ROOT / 'themes').iterdir() if (p / 'theme.json').exists())
            i = choose(names, 'Tema', 'RiceSelector', [ROOT / 'themes' / n / 'preview.webp' for n in names])
            if i is None:
                return
            name = names[i]
        apply_theme(name, args.offline or a == 'prepare')
    elif a == 'list':
        print('\n'.join(sorted(p.name for p in (ROOT / 'themes').iterdir() if (p / 'theme.json').exists())))
    elif a == 'rollback':
        if not (STATE / 'previous').is_symlink():
            raise RuntimeError('Não há geração anterior')
        if not args.offline:
            require_session()
        with locked():
            old, active = (STATE / 'previous').resolve(), CURRENT.resolve()
            validate_generation(old)
            link(old, 'current')
            try:
                if not args.offline:
                    run(['hyprctl', 'reload'])
                    if output(['hyprctl', 'configerrors']).strip():
                        raise RuntimeError('Hyprland rejeitou a geração anterior')
                    services()
            except Exception:
                link(active, 'current')
                if not args.offline:
                    run(['hyprctl', 'reload'], check=False)
                    services()
                raise
            link(active, 'previous')
            print('Geração anterior restaurada: ' + selected()['theme'])
    elif a == 'wallpaper':
        name = selected()['theme']
        files = sorted((ROOT / 'themes' / name / 'walls').glob('*'))
        custom = prefs()['wallpaper_directory']
        if custom:
            files += sorted(p for p in Path(custom).expanduser().glob('*') if p.suffix.lower() in ('.png', '.webp', '.jpg', '.jpeg'))
        i = choose([p.name for p in files], 'Wallpaper', 'WallSelect', files)
        if i is not None:
            apply_theme(name, wallpaper=str(files[i]))
    elif a == 'launcher':
        style = prefs()['launcher_style']
        if style not in ('style_1', 'style_2', 'style_3'):
            raise ValueError('Estilo desconhecido')
        run(['rofi', '-no-config', '-show', 'drun', '-theme', CURRENT / 'rofi' / (style + '.rasi')], check=False, timeout=86400)
    elif a == 'launcher-style':
        i = choose(['Normal', 'Tela inteira', 'Mínimo'], 'Launcher', 'StyleSelect',
                   [ROOT / 'assets/menu' / f'style_{i}.webp' for i in (1, 2, 3)])
        if i is not None:
            p = prefs(); p['launcher_style'] = f'style_{i+1}'
            CONFIG.mkdir(parents=True, exist_ok=True); atomic_json(CONFIG / 'preferences.json', p)
    elif a == 'app':
        app(values[0])
    elif a == 'scratch':
        with locked('scratch'):
            windows = json.loads(run(['hyprctl', '-j', 'clients']).stdout)
            if not any(w.get('class') == 'gh0stzk-scratch' for w in windows):
                app('scratch')
                for _ in range(40):
                    if any(w.get('class') == 'gh0stzk-scratch' for w in json.loads(run(['hyprctl', '-j', 'clients']).stdout)):
                        break
                    time.sleep(.05)
            dispatch('hl.dsp.workspace.toggle_special("gh0stzk")')
    elif a == 'volume':
        v = values[0]
        run(['wpctl', 'set-mute', '@DEFAULT_AUDIO_SOURCE@' if v == 'mic' else '@DEFAULT_AUDIO_SINK@', 'toggle'] if v in ('mic', 'mute') else
            ['wpctl', 'set-volume', '-l', '1.0', '@DEFAULT_AUDIO_SINK@', '5%+' if v == 'up' else '5%-'])
    elif a == 'brightness':
        if not list(Path('/sys/class/backlight').glob('*')):
            raise RuntimeError('Nenhum dispositivo de brilho disponível')
        run(['brightnessctl', '-c', 'backlight', 'set', '+5%' if values[0] == 'up' else '5%-'])
    elif a == 'media':
        if values[0] not in ('play-pause', 'next', 'previous', 'stop'):
            raise ValueError('Ação multimídia inválida')
        run(['playerctl', values[0]])
    elif a == 'network':
        if not output(['nmcli', '-t', '-f', 'DEVICE', 'device']):
            raise RuntimeError('NetworkManager ou dispositivos de rede indisponíveis')
        app('floating', ['-e', 'nmtui'])
    elif a == 'bluetooth':
        if not list(Path('/sys/class/bluetooth').glob('*')):
            raise RuntimeError('Nenhum adaptador Bluetooth disponível')
        subprocess.Popen(['blueman-manager'], start_new_session=True)
    elif a == 'clipboard':
        entries = output(['cliphist', 'list']).splitlines()
        i = choose(entries, 'Clipboard', 'Clipboard')
        if i is not None:
            decoded = run(['cliphist', 'decode'], input=(entries[i] + '\n').encode()).stdout
            run(['wl-copy'], input=decoded)
    elif a == 'lock':
        lockscreen()
    elif a == 'power':
        power(values[0] if values else None)
    elif a == 'screenshot':
        screenshot(values[0] if values else 'menu')
    elif a == 'keyboard':
        run(['hyprctl', 'switchxkblayout', 'all', 'next'])
    elif a == 'windows':
        wins = json.loads(run(['hyprctl', '-j', 'clients']).stdout)
        i = choose([f'{w["workspace"]["name"]} · {w["class"]} · {w["title"]}'.replace('\n', ' ') for w in wins], 'Janelas', 'Windows')
        if i is not None:
            dispatch('hl.dsp.focus({window=' + lua('address:' + wins[i]['address']) + '})')
    elif a == 'help':
        lines = (ROOT / 'docs/ATALHOS.md').read_text().splitlines()
        choose([l for l in lines if l.startswith('|') and '---' not in l], 'Atalhos')
    elif a == 'widget':
        if not prefs()['widgets'] or not shutil.which('eww'):
            if values[0] == 'music':
                i = choose(['Anterior', 'Tocar/pausar', 'Próxima'], 'Música')
                if i is not None:
                    run(['playerctl', ['previous', 'play-pause', 'next'][i]], check=False)
            else:
                choose([f'{k}: {v}' for k, v in widget_data('system').items()], 'Sistema')
        elif values[0] in ('music', 'launchermenu'):
            run(['eww', '-c', CURRENT / 'eww', 'open', '--toggle', values[0]])
    elif a in ('status', 'widget-data'):
        print(json.dumps(status(values[0]) if a == 'status' else widget_data(values[0]), ensure_ascii=False))
    elif a == 'updates':
        text = output(['checkupdates'], 'Nenhuma atualização disponível ou consulta indisponível.')
        choose(text.splitlines(), 'Atualizações oficiais')
    elif a == 'colorpicker':
        run(['hyprpicker', '-a'], check=False, timeout=86400)
    elif a == 'edit-theme':
        name = selected()['theme']
        fields = ['BORDER_WIDTH', 'P_CORNER_R', 'P_BLUR', 'P_SHADOWS', 'P_ANIMATIONS', 'P_TERM_OPACITY']
        labels = ['Borda', 'Arredondamento', 'Blur', 'Sombras', 'Animações', 'Opacidade do terminal']
        i = choose(labels, 'Editar ' + name)
        if i is None:
            return
        choices = [['0', '1', '2', '3', '4'], ['0', '4', '6', '10', '16'], ['false', 'true'],
                   ['false', 'true'], ['#', '@'], ['0.8', '0.9', '0.96', '1.0']][i]
        j = choose(choices, labels[i])
        if j is not None:
            path = CONFIG / 'themes' / (name + '.json'); path.parent.mkdir(parents=True, exist_ok=True)
            previous = path.read_bytes() if path.exists() else None
            custom = json.loads(previous) if previous else {}; custom[fields[i]] = choices[j]
            atomic_json(path, custom)
            try:
                apply_theme(name)
            except Exception:
                if previous is None:
                    path.unlink()
                else:
                    path.write_bytes(previous)
                raise
    elif a == 'bar':
        with locked():
            if values[0] == 'hide':
                stop('waybar')
            else:
                start('waybar', ['waybar', '-c', CURRENT / 'waybar.json', '-s', CURRENT / 'waybar.css'])
    elif a == 'session':
        session()
    elif a == 'watch':
        watch()


def entry():
    try:
        main()
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        print('Erro: ' + str(error), file=sys.stderr)
        if os.environ.get('HYPRLAND_INSTANCE_SIGNATURE') and shutil.which('notify-send'):
            run(['notify-send', '-u', 'critical', 'gh0stzk Hyprland', str(error)[:500]], check=False)
        sys.exit(1)
