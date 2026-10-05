#!/usr/bin/env python3
"""Valida arquivos em diretório temporário. Nunca inicia uma sessão gráfica."""
import argparse
import configparser
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'lib'))
from render import materialize, render, theme
from runtime import validate_generation


def check_balanced(path):
    """Basic structural check, explicitly not a native Rasi/Yuck/Hyprlang parser."""
    text = path.read_text()
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.S)
    text = re.sub(r'(?m)^\s*(?://|;;|#).*$', '', text)
    # Yuck expressions allow quotes inside ${...}; remove quoted strings first.
    text = re.sub(r'"(?:\\.|[^"\\])*"', '""', text)
    stack = []
    for c in text:
        if c in '({[':
            stack.append(c)
        elif c in ')}]':
            if not stack or stack.pop() != dict(zip(')}]', '({['))[c]:
                raise ValueError(f'Delimitadores inconsistentes: {path}')
    if stack:
        raise ValueError(f'Delimitadores abertos: {path}')


def check_installer(path):
    """O instalador é o único bootstrap: exigimos origem centralizada e
    atualização total. Só marcação e sintaxe; o comportamento é testado em tests/."""
    path = Path(path)
    if not path.is_file():
        raise ValueError('instalar.sh ausente na raiz do projeto')
    if not os.access(path, os.X_OK):
        raise ValueError('Executável sem permissão: ' + str(path))
    text = path.read_text()
    if re.search(r'''PROJECT_REPO\s*=\s*['"]?https://github\.com/gh0stzk/dotfiles''', text):
        raise ValueError('instalar.sh não pode apontar a origem para o upstream do gh0stzk')
    for marker in ("PROJECT_REPO=''", 'PROJECT_REF=', '--dry-run', '--yes', '--help',
                   'pacman -Syu --needed', 'git -C "$tmp" init', 'FETCH_HEAD^{commit}'):
        if marker not in text:
            raise ValueError('instalar.sh sem o item obrigatório: ' + marker)
    # Inspect real commands only: the help heredoc mentions the options by name.
    body = re.sub(r"<<'HELP'.*?\nHELP\n", '\n', text, flags=re.S)
    for line in body.splitlines():
        if 'pacman' not in line:
            continue
        if re.search(r'-Sy(?![u0-9])', line) or re.search(r'(?<![\w-])-S(?!yu)\s', line) or '--noconfirm' in line:
            raise ValueError('instalar.sh exige atualização total e interativa: ' + line.strip())
    if '--allow-missing' in body:
        raise ValueError('instalar.sh não pode mascarar dependências com --allow-missing')
    return text


def hyprland_version():
    """Versão real do binário instalado; 'ausente' quando não há Hyprland."""
    if not shutil.which('Hyprland'):
        return 'ausente'
    proc = subprocess.run(['Hyprland', '--version'], capture_output=True, text=True, timeout=10)
    return (proc.stdout + proc.stderr).strip() or 'desconhecida'


def verify_hyprland(dest, env, required=False):
    if not shutil.which('Hyprland'):
        if required:
            raise ValueError('Hyprland obrigatório para validar a instalação')
        return 'não executado: Hyprland ausente'
    helptext = subprocess.run(['Hyprland', '--help'], capture_output=True, text=True).stdout
    if '--verify-config' not in helptext:
        if required:
            raise ValueError('Hyprland instalado não oferece --verify-config')
        return 'não executado: versão sem --verify-config'
    proc = subprocess.run(['Hyprland', '--verify-config', '--config', str(ROOT / 'config/hyprland.lua')],
                          capture_output=True, text=True, env=env, timeout=30)
    (dest / 'hyprland-verify.log').write_text(proc.stdout + proc.stderr)
    if proc.returncode:
        raise ValueError('Hyprland --verify-config falhou: ' + proc.stdout[-1000:] + proc.stderr[-1000:])
    return 'Hyprland --verify-config passou (sem sessão gráfica)'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--require-native', action='store_true', help='Falhar se parsers nativos obrigatórios estiverem ausentes')
    ap.add_argument('--local-config', type=Path, help='Validar também preferências existentes sem alterá-las')
    ap.add_argument('--render-dir', type=Path, help='Guardar configurações renderizadas para revisão')
    ap.add_argument('--report', type=Path, help='Salvar relatório JSON')
    args = ap.parse_args()
    if args.require_native:
        for binary in ('Hyprland', 'rofi', 'luac'):
            if not shutil.which(binary):
                raise ValueError('Parser obrigatório ausente: ' + binary)
    report = {'static': [], 'themes': {}, 'skipped': [], 'graphical_session_tested': False}
    for base in ('lib', 'tools', 'tests'):
        for file in (ROOT / base).glob('*.py'):
            compile(file.read_text(), str(file), 'exec')
    for file in list((ROOT / 'bin').glob('gh0stzk*')) + sorted(ROOT.glob('*.py')):
        if file.is_file():
            compile(file.read_text(), str(file), 'exec')
    report['static'].append('Sintaxe Python')
    for file in list((ROOT / 'themes').glob('*/theme.json')) + [ROOT / 'packages.json', ROOT / 'UPSTREAM.json', ROOT / 'config/preferences.json']:
        json.loads(file.read_text())
    for file in list((ROOT / 'bin').glob('gh0stzk*')) + [ROOT / 'instalar.sh']:
        if not os.access(file, os.X_OK):
            raise ValueError('Executável sem permissão: ' + str(file))
    report['static'].append('JSON')
    report['static'].append('Permissões de bit/gh0stzk, gh0stzk-session e instalar.sh')
    # instalar.sh is the only shell program and it lives at the repository root,
    # so the folder scan alone would never see it.
    shell = [ROOT / 'instalar.sh']
    for folder in ('bin', 'lib', 'config', 'tools'):
        for file in sorted((ROOT / folder).rglob('*')):
            if file.is_file() and '__pycache__' not in file.parts and file not in shell:
                if re.search(r'^#!.*\b(?:ba)?sh\b', file.read_text()):
                    shell.append(file)
    sources = shell + sorted(ROOT.glob('*.py')) + sorted(ROOT.glob('*.sh'))
    for file in sources:
        if not file.is_file() or '__pycache__' in file.parts:
            continue
        if file in shell:
            subprocess.run(['bash', '-n', str(file)], check=True)
        text = file.read_text()
        if re.search(r'/home/(?:ronilson|z0mbi3)', text):
            raise ValueError('Caminho pessoal: ' + str(file))
        if re.search(r'''\[(?:'|")(?:bspc|xrandr|xdotool|wmctrl|xprop|maim|xclip|feh|picom|sxhkd|i3lock)(?:'|")''', text):
            raise ValueError('Dependência X11 em comando executável: ' + str(file))
    if shellcheck := shutil.which('shellcheck'):
        subprocess.run([shellcheck, *map(str, shell)], check=True)
        report['static'].append(f'ShellCheck sem avisos: {len(shell)} scripts')
    else:
        report['skipped'].append('ShellCheck: indisponível')
    report['static'] += ['Caminhos pessoais e comandos X11 migrados',
                         f'Sintaxe shell (bash -n): {len(shell)} scripts, incluindo instalar.sh']
    check_installer(ROOT / 'instalar.sh')
    report['static'].append('instalar.sh: origem centralizada, atualização total e download de um commit')
    upstream = ROOT / 'upstream/gh0stzk-dotfiles'
    source = json.loads((ROOT / 'UPSTREAM.json').read_text())
    if (upstream / '.git').exists():
        commit = subprocess.check_output(['git', '-C', str(upstream), 'rev-parse', 'HEAD'], text=True).strip()
        if commit != source['commit']:
            raise ValueError('Commit upstream divergiu')
        if subprocess.check_output(['git', '-C', str(upstream), 'status', '--porcelain']):
            raise ValueError('Upstream foi modificado')
        names = {p.name for p in (upstream / 'config/bspwm/rices').iterdir() if p.is_dir()}
        if names != {p.parent.name for p in (ROOT / 'themes').glob('*/theme.json')}:
            raise ValueError('Conjunto de temas incompleto')
        for folder in (ROOT / 'themes').iterdir():
            for file in [folder / 'preview.webp', *list((folder / 'walls').glob('*'))]:
                original = upstream / 'config/bspwm/rices' / folder.name / file.relative_to(folder)
                if hashlib.sha256(file.read_bytes()).digest() != hashlib.sha256(original.read_bytes()).digest():
                    raise ValueError('Recurso original modificado: ' + str(file))
        report['static'].append('Upstream intacto, commit/conjunto de temas/hashes de wallpapers e prévias')
    with tempfile.TemporaryDirectory(prefix='gh0stzk-validate-') as temp:
        base = args.render_dir.resolve() if args.render_dir else Path(temp) / 'renders'
        # Include a scaled/rotated multi-monitor fixture, never query the current compositor.
        fixtures = [{'name': 'TEST-A', 'width': 1600, 'height': 900, 'scale': 1},
                    {'name': 'TEST-B', 'width': 2560, 'height': 1440, 'scale': 1.25, 'transform': 1}]
        for path in sorted((ROOT / 'themes').glob('*/theme.json')):
            name = path.parent.name
            dest = base / name
            preferences = json.loads((ROOT / 'config/preferences.json').read_text())
            overrides = {}
            if args.local_config:
                userprefs = args.local_config / 'preferences.json'
                if userprefs.exists():
                    preferences.update(json.loads(userprefs.read_text()))
                for key in ('terminal', 'files', 'browser', 'mixer'):
                    if not isinstance(preferences[key], list) or not preferences[key] or not all(isinstance(x, str) and '\n' not in x for x in preferences[key]):
                        raise ValueError('Preferência de aplicativo inválida: ' + key)
                override = args.local_config / 'themes' / (name + '.json')
                if override.exists():
                    overrides = json.loads(override.read_text())
            render(name, dest, preferences, fixtures, overrides=overrides)
            materialize(dest, dest)
            validate_generation(dest)
            cp = configparser.ConfigParser(interpolation=None)
            cp.read(dest / 'dunstrc')
            assert cp.getboolean('global', 'force_xwayland') is False
            for file in dest.rglob('*'):
                if file.suffix in ('.rasi', '.yuck', '.scss', '.css', '.conf'):
                    check_balanced(file)
                    text = file.read_text()
                    if '@ROOT@' in text or '@CURRENT@' in text or '@CTL@' in text:
                        raise ValueError('Token não resolvido: ' + str(file))
                    for ref in re.findall(r'(?:@import|include)\s+"([^"\n]+)"', text):
                        # Sass imports omit .scss.
                        target = file.parent / ref
                        if not target.exists() and not target.with_suffix('.scss').exists():
                            raise ValueError('Import inexistente: ' + str(target))
                    for ref in re.findall(r'url\(["\']([^"\']+)["\']', text):
                        if '$' not in ref and not Path(ref).exists():
                            raise ValueError('Imagem inexistente: ' + ref)
            bars = json.loads((dest / 'waybar.json').read_text())
            assert len(bars) == max(1, len(theme(name)['bars'])) * len(fixtures)
            # An isolated HOME prevents native validation from reading user local.lua.
            fakehome = Path(temp) / ('home-' + name)
            fakecurrent = fakehome / '.local/state/gh0stzk-hyprland/current'
            fakecurrent.parent.mkdir(parents=True)
            fakecurrent.symlink_to(dest)
            if args.local_config and (args.local_config / 'local.lua').exists():
                localdest = fakehome / '.config/gh0stzk-hyprland'
                localdest.mkdir(parents=True)
                shutil.copy2(args.local_config / 'local.lua', localdest / 'local.lua')
            env = dict(os.environ, HOME=str(fakehome), XDG_CONFIG_HOME=str(fakehome / '.config'),
                       XDG_STATE_HOME=str(fakehome / '.local/state'), GH0STZK_ROOT=str(ROOT))
            for variable in ('HYPRLAND_INSTANCE_SIGNATURE', 'WAYLAND_DISPLAY', 'DISPLAY'):
                env.pop(variable, None)
            native = verify_hyprland(dest, env, args.require_native)
            report['themes'][name] = {'static': 'passou', 'panels_per_monitor': len(bars) // 2,
                                     'hyprland': native, 'visual': 'não testado'}
        if shutil.which('luac'):
            for file in (ROOT / 'config').glob('*.lua'):
                subprocess.run(['luac', '-p', str(file)], check=True)
            report['static'].append('Sintaxe Lua (luac) de config/*.lua: NÃO prova compatibilidade com Hyprland')
        else:
            report['skipped'].append('luac ausente')
    report['hyprland_version'] = hyprland_version()
    report['caveats'] = [
        'luac -p valida apenas sintaxe Lua; a compatibilidade com o Hyprland exige o '
        'parser do próprio Hyprland (Hyprland --verify-config), executado acima.',
        'Validação estática não abre sessão gráfica: camada, DRM/GL, áudio, portais, '
        'captura, bloqueio e inatividade continuam sem prova.',
    ]
    for name in ('rofi', 'waybar', 'dunst', 'eww', 'hyprlock', 'hypridle', 'Hyprland'):
        if not shutil.which(name):
            report['skipped'].append(name + ': binário ausente; parser nativo/teste funcional não executado')
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, AssertionError, subprocess.SubprocessError) as e:
        print('FALHOU: ' + str(e), file=sys.stderr)
        sys.exit(1)
