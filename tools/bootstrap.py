#!/usr/bin/env python3
"""Orquestra Arch; install.py continua sendo o único aplicador de dotfiles."""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import install


def run(args, **kwargs):
    print('+ ' + ' '.join(map(str, args)), flush=True)
    return subprocess.run(list(map(str, args)), check=True, **kwargs)


def output(args):
    return subprocess.run(args, capture_output=True, text=True, check=False).stdout.strip()


def manifest():
    data = json.loads((ROOT / 'packages.json').read_text())
    for key, kind in [('official', list), ('official_optional', dict), ('aur_optional', dict),
                      ('required_commands', list), ('external_not_installed', dict)]:
        values = data.get(key)
        if not isinstance(values, kind) or not values:
            raise ValueError('Manifesto inválido: ' + key)
        if any(not isinstance(x, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9+_.-]*', x) for x in values):
            raise ValueError('Nome inválido em ' + key)
        if len(values) != len(set(values)):
            raise ValueError('Duplicatas em ' + key)
    for key, description in list(data['external_not_installed'].items()) + list(data['aur_optional'].items()):
        # Descriptions must state where the resource comes from; silence is not allowed.
        if not re.search(r'(AUR|github\.com|repositório|repo|http)', description, re.I):
            raise ValueError('Origem não declarada para ' + key + ': ' + description)
    if set(data['official']) & (set(data['official_optional']) | set(data['aur_optional'])):
        raise ValueError('Categorias sobrepostas no manifesto')
    return data


def payload():
    required = ['install.py', 'instalar.sh', 'LICENSE', 'UPSTREAM.json', 'packages.json',
                'bin/gh0stzk', 'bin/gh0stzk-session', 'lib/runtime.py', 'lib/render.py',
                'config/hyprland.lua', 'tools/validate.py', 'tools/session_admin.py', 'resources.json']
    for name in required:
        if not (ROOT / name).is_file():
            raise ValueError('Cópia incompleta: ' + name)
    if not os.access(ROOT / 'instalar.sh', os.X_OK):
        raise ValueError('instalar.sh sem permissão de execução')
    # A fresh install never has upstream/; every needed byte is vendored and hashed.
    resources = json.loads((ROOT / 'resources.json').read_text())
    for name, digest in resources.items():
        path = Path(name)
        if path.is_absolute() or '..' in path.parts:
            raise ValueError('Caminho inválido em resources.json')
        source = ROOT / path
        if not source.is_file() or hashlib.sha256(source.read_bytes()).hexdigest() != digest:
            raise ValueError('Recurso ausente/modificado: ' + name)
    if len(list((ROOT / 'themes').glob('*/theme.json'))) != 18:
        raise ValueError('Esperados exatamente 18 temas')


def versions():
    """Versões reais dos validadores; ausentes viram 'ausente', nunca um palpite."""
    found = {}
    for binary, args in (('Hyprland', ['--version']), ('rofi', ['-version']),
                         ('waybar', ['--version']), ('dunst', ['--version']),
                         ('luac', ['-v'])):
        if not shutil.which(binary):
            found[binary] = 'ausente'
            continue
        try:
            proc = subprocess.run([binary, *args], capture_output=True, text=True, timeout=10)
        except (OSError, subprocess.SubprocessError):
            found[binary] = 'ilegível'
            continue
        found[binary] = (proc.stdout + proc.stderr).strip().splitlines()[:1] or ['desconhecida']
        found[binary] = found[binary][0]
    return found


def configured(unit, user=False):
    prefix = ['systemctl'] + (['--user'] if user else [])
    return any(subprocess.run(prefix + [verb, '--quiet', unit], capture_output=True).returncode == 0
               for verb in ('is-active', 'is-enabled'))


def service_plan():
    conflicts = [unit for unit in ('systemd-networkd.service', 'dhcpcd.service', 'iwd.service', 'connman.service')
                 if configured(unit)]
    # Instance units and existing network profiles also require an explicit decision.
    enabled = output(['systemctl', 'list-unit-files', '--state=enabled', '--no-legend'])
    if re.search(r'(dhcpcd|netctl|wpa_supplicant)@', enabled):
        conflicts.append('unidades de rede por interface')
    if not configured('NetworkManager.service') and any(Path('/etc/systemd/network').glob('*.network')):
        conflicts.append('/etc/systemd/network/*.network')
    if conflicts:
        raise ValueError('Rede existente: ' + ', '.join(conflicts) +
                         '. Decida a integração com NetworkManager antes de instalar; nenhum serviço será substituído.')
    for package in ('pulseaudio', 'pipewire-media-session'):
        if subprocess.run(['pacman', '-Q', package], capture_output=True).returncode == 0:
            raise ValueError('Áudio existente: ' + package + '. Decida a migração para PipeWire/WirePlumber antes de instalar.')
    if configured('pulseaudio.socket', True) or configured('pulseaudio.service', True):
        raise ValueError('PulseAudio em uso. Migração automática recusada.')
    plan = []
    for unit, user in [('NetworkManager.service', False), ('pipewire.socket', True),
                       ('pipewire-pulse.socket', True), ('wireplumber.service', True)]:
        state = output(['systemctl'] + (['--user'] if user else []) + ['is-enabled', unit])
        if state.startswith('masked'):
            raise ValueError('Serviço mascarado por decisão local: ' + unit)
        if not configured(unit, user):
            plan.append((unit, user))
    return plan


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--source', default='local')
    ap.add_argument('--ref', default='main')
    for name in ('fonts', 'portals', 'session'):
        ap.add_argument('--without-' + name, action='store_true')
    ap.add_argument('--optional', action='append', default=[])
    ap.add_argument('--with-eww', type=Path)
    args = ap.parse_args(argv)
    data = manifest()
    payload()
    if set(args.optional) - data['official_optional'].keys():
        raise ValueError('Pacote opcional fora de official_optional')
    packages = list(dict.fromkeys(data['official'] + args.optional))
    print('Obrigatórios oficiais: ' + ' '.join(data['official']))
    print('Opcionais selecionados: ' + (' '.join(args.optional) or 'nenhum'))
    for name, why in data['official_optional'].items():
        print('  oficial opcional: ' + name + ' — ' + why)
    for name, why in data['aur_optional'].items():
        print('  AUR opcional: ' + name + ' — ' + why)
    for name, why in data['external_not_installed'].items():
        print('  fora deste repositório: ' + name + ' — ' + why)
    print('Recursos conferidos: 18 temas, wallpapers, fontes licenciadas e assets; upstream dispensável.')
    if args.dry_run:
        print('ATENÇÃO: o fluxo real atualizará TODO o sistema: sudo pacman -Syu --needed -- ' + ' '.join(packages))
        print('DRY-RUN: inspecionar rede/áudio; validar com Hyprland --verify-config e Rofi; install.py; fc-cache.')
        options = ['--dry-run']
        if not args.without_fonts:
            options.append('--with-fonts')
        if not args.without_portals:
            options.append('--with-portals')
        if not args.without_session:
            print('DRY-RUN: sessão administrativa com journal e restauração em /var/lib/gh0stzk-hyprland.')
        return install.main(options)
    if os.getuid() == 0:
        raise ValueError('Execute instalar.sh como usuário comum.')
    os_release = dict(line.split('=', 1) for line in Path('/etc/os-release').read_text().splitlines() if '=' in line)
    if os_release.get('ID', '').strip('"') != 'arch' or os.uname().machine != 'x86_64':
        raise ValueError('Exige Arch Linux x86_64.')
    for key, suffix in [('XDG_CONFIG_HOME', '.config'), ('XDG_DATA_HOME', '.local/share'), ('XDG_STATE_HOME', '.local/state')]:
        if os.environ.get(key) and Path(os.environ[key]) != Path.home() / suffix:
            raise ValueError('XDG personalizado não suportado por install.py: ' + key)
    services = service_plan()  # before a pacman transaction can replace an audio stack
    for label, unit, user in (('Bluetooth', 'bluetooth.service', False),
                              ('NetworkManager', 'NetworkManager.service', False)):
        print('Detecção prévia: ' + label + ' -> ' +
              ('ativo/habilitado' if configured(unit, user) else 'ausente ou inativo'))
    if not shutil.which('blueman-manager') and not shutil.which('blueman'):
        print('Bluetooth: interface opcional ausente. Adicione --optional blueman bluez bluez-utils.')
    if any(user for _, user in services):
        run(['systemctl', '--user', 'show-environment'], stdout=subprocess.DEVNULL)
    if args.with_eww:
        args.with_eww = args.with_eww.expanduser().resolve(strict=True)
        name = output(['pacman', '-Qp', '--print-format', '%n', str(args.with_eww)])
        if name != 'eww':
            raise ValueError('--with-eww exige pacote local com nome eww, compilado com Wayland.')
    run(['sudo', 'pacman', '-Syu', '--needed', '--', *packages])
    # Query the synchronized repositories and ensure each requested official package exists.
    run(['pacman', '-Si', '--', *packages], stdout=subprocess.DEVNULL)
    if args.with_eww:
        run(['sudo', 'pacman', '-U', '--', args.with_eww])
    missing = install.dependencies()
    if missing:
        raise ValueError('Dependências obrigatórias ausentes/incompatíveis: ' + ', '.join(missing))
    print('Versões usadas na validação: ' + '; '.join(f'{k} {v}' for k, v in versions().items()))
    run([sys.executable, '-B', ROOT / 'tools/validate.py', '--require-native',
         '--local-config', Path.home() / '.config/gh0stzk-hyprland'])
    version = output(['git', '-C', str(ROOT), 'rev-parse', '--verify', 'HEAD'])
    dirty = output(['git', '-C', str(ROOT), 'status', '--porcelain', '--untracked-files=no'])
    provenance = {'source': args.source, 'ref': args.ref, 'commit': version or None,
                  'local_changes': bool(dirty), 'payload_sha256': hashlib.sha256((ROOT / 'resources.json').read_bytes()).hexdigest()}
    options = ['--apply', '--provenance', json.dumps(provenance)]
    for name in ('fonts', 'portals', 'session'):
        if not getattr(args, 'without_' + name):
            options.append('--with-' + name)
    result = install.main(options)
    if result:
        return result
    fonts = Path.home() / '.local/share/fonts/gh0stzk-hyprland'
    if fonts.is_dir():
        run(['fc-cache', '-f', str(fonts)])
        print('Cache de fontes atualizado em ' + str(fonts))
    else:
        run(['fc-cache', '-f'])
        print('Sem fontes desta adaptação instaladas; cache geral atualizado.')
    # Enable only absent services, never restart/disable another stack or touch login manager.
    for unit, user in services:
        run((['systemctl', '--user'] if user else ['sudo', 'systemctl']) + ['enable', '--now', unit])
    print('')
    print('Instalação concluída. Nada foi reiniciado e sua sessão continua intacta.')
    print('Origem: ' + args.source + ' | referência: ' + args.ref +
          ' | commit: ' + (version or 'cópia local sem commit; hash dos recursos registrado'))
    print('Backup: ~/.local/state/gh0stzk-hyprland/backups (use exatamente o diretório informado na aplicação)')
    print('Sessão: saia voluntariamente e escolha "Hyprland — gh0stzk" no gerenciador de login;')
    print('ou, em um TTY, execute: ~/.local/bin/gh0stzk-session')
    print('Restauração: python3 ~/.local/share/gh0stzk-hyprland/install.py --restore CAMINHO_DO_BACKUP --apply')
    print('A restauração devolve arquivos; pacotes, atualização do sistema e serviços habilitados permanecem.')
    if shutil.which('eww'):
        print('Eww detectado; os widgets usam Wayland. Se não abrirem, confira preferências["widgets"].')
    else:
        print('Eww ausente (AUR opcional): perfil e controles de música usam as alternativas Rofi.')
    print('Ainda pendente de prova: sessão gráfica real. Temas GTK, ícones e cursor originais')
    print('permanecem opcionais e não são instalados por este fluxo.')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print('Instalação interrompida: ' + str(exc) + '\nConfira a etapa acima; se já houve aplicação, use o backup informado. Nenhuma sessão foi encerrada.', file=sys.stderr)
        sys.exit(1)
