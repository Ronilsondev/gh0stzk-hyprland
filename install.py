#!/usr/bin/env python3
"""Instalador de arquivos, sem instalar pacotes nem iniciar serviços. GPL-3.0."""
import argparse
import datetime
import fcntl
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import uuid
import shlex
from pathlib import Path

ROOT = Path(__file__).resolve().parent
NAME = 'gh0stzk-hyprland'


def fingerprint(path):
    if path.is_symlink():
        return {'kind': 'link', 'target': os.readlink(path)}
    if path.is_file():
        return {'kind': 'file', 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                'mode': path.stat().st_mode & 0o777}
    if path.exists():
        return {'kind': 'directory'}
    return None


def save(path, obj):
    temp = path.with_name(path.name + '.tmp')
    temp.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n')
    os.replace(temp, path)


def check_parents(path, home):
    """Do not follow parent symlinks into unrelated locations."""
    if not path.is_relative_to(home):
        raise ValueError('Destino fora da home escolhida: ' + str(path))
    for parent in path.parents:
        if parent == home:
            break
        if parent.is_symlink():
            raise ValueError('Diretório pai é um symlink; configuração explícita necessária: ' + str(parent))


def copy_atomic(src, dst):
    dst.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.gh0stzk-', dir=dst.parent)
    os.close(fd)
    temp = Path(name)
    try:
        if src.is_symlink():
            temp.unlink()
            temp.symlink_to(os.readlink(src))
        else:
            shutil.copy2(src, temp)
        os.replace(temp, dst)
    finally:
        temp.unlink(missing_ok=True)


def dependencies():
    manifest = json.loads((ROOT / 'packages.json').read_text())
    missing = [x for x in manifest['required_commands'] if not shutil.which(x)]
    print('Pacotes oficiais: ' + ' '.join(manifest['official']))
    print('AUR opcional: ' + ', '.join(manifest['aur_optional']))
    print('Opcionais oficiais: ' + ', '.join(manifest['official_optional']))
    print('Comandos ausentes: ' + (', '.join(missing) or 'nenhum'))
    for binary, minimum in [('Hyprland', (0, 56)), ('rofi', (2, 0))]:
        if shutil.which(binary):
            result = subprocess.run([binary, '--version' if binary == 'Hyprland' else '-version'],
                                    capture_output=True, text=True, timeout=10)
            version = re.search(r'(\d+)\.(\d+)', result.stdout + result.stderr)
            if not version or tuple(map(int, version.groups())) < minimum:
                missing.append(binary + ' (versão insuficiente/desconhecida)')
    return missing


def plan(home, with_fonts=False, with_portals=False):
    entries = []
    for dirname in ('bin', 'lib', 'config', 'themes', 'assets', 'docs', 'tools'):
        for src in sorted((ROOT / dirname).rglob('*')):
            if not src.is_file() or '__pycache__' in src.parts or src.suffix == '.pyc':
                continue
            if src.is_relative_to(ROOT / 'assets/fonts') and not src.is_relative_to(ROOT / 'assets/fonts/MapleMono-NF'):
                continue  # only fonts with an included redistribution license
            entries.append((src, home / '.local/share' / NAME / src.relative_to(ROOT), False))
    for name in ('LICENSE', 'UPSTREAM.json', 'packages.json', 'CREDITS.md', 'README.md', 'install.py', 'instalar.sh', 'resources.json'):
        entries.append((ROOT / name, home / '.local/share' / NAME / name, False))
    # The small Python launchers resolve a local symlink to locate the installation.
    for name in ('gh0stzk', 'gh0stzk-session'):
        entries.append((None, home / '.local/bin' / name, False))
    for name in ('local.lua', 'preferences.json'):
        entries.append((ROOT / 'config' / name, home / '.config' / NAME / name, True))
    if with_fonts:
        for src in sorted((ROOT / 'assets/fonts/MapleMono-NF').rglob('*')):
            if src.is_file():
                entries.append((src, home / '.local/share/fonts' / NAME / src.relative_to(ROOT / 'assets/fonts'), False))
    if with_portals:
        entries.append((ROOT / 'config/hyprland-portals.conf', home / '.config/xdg-desktop-portal/hyprland-portals.conf', True))
    return entries


def desired(src, dst):
    return fingerprint(src) if src else {'kind': 'link', 'target': '../share/' + NAME + '/bin/' + dst.name}


def restore(backup, home, apply):
    backup = backup.resolve()
    root = home / '.local/state' / NAME / 'backups'
    if backup.parent != root.resolve():
        raise ValueError('Backup deve estar no diretório de backups desta instalação')
    manifest = json.loads((backup / 'manifest.json').read_text())
    if manifest['home'] != str(home):
        raise ValueError('Backup pertence a outra home')
    conflicts = []
    session = manifest.get('session')
    if session:
        print('Sessão administrativa: ' + session)
        if apply:
            result = subprocess.run(['sudo', sys.executable, str(ROOT / 'tools/session_admin.py'), 'restore', session])
            if result.returncode == 2:
                conflicts.append('entrada administrativa de sessão')
            elif result.returncode:
                raise ValueError('Restauração administrativa falhou; arquivos do usuário preservados')
    for entry in reversed(manifest['changes']):
        rel = Path(entry['path'])
        if rel.is_absolute() or '..' in rel.parts:
            raise ValueError('Caminho inválido no manifesto')
        path = home / rel
        check_parents(path, home)
        now = fingerprint(path)
        if now == entry['before']:
            continue  # already restored, including a previous interrupted run
        if now != entry['after']:
            conflicts.append(str(rel))
            print('PRESERVADO (alteração posterior): ' + str(rel))
            continue
        source = backup / 'files' / rel
        if entry['before'] and fingerprint(source) != entry['before']:
            raise ValueError('Backup corrompido: ' + str(rel))
        print(('RESTAURAR ' if apply else 'DRY-RUN restaurar ') + str(rel))
        if apply:
            if entry['before'] is None:
                path.unlink()  # exact file matched; no recursive deletion
            else:
                copy_atomic(source, path)
    if apply:
        save(backup / 'restore-report.json', {'time': datetime.datetime.now().isoformat(), 'preserved': conflicts})
    return 2 if conflicts else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description='Instalação isolada; por padrão apenas inspeciona.')
    ap.add_argument('--apply', action='store_true', help='Aplicar as alterações de arquivos')
    ap.add_argument('--dry-run', action='store_true', help='Inspecionar (padrão)')
    ap.add_argument('--home', type=Path, default=Path.home(), help='Home de destino, inclusive temporária para testes')
    ap.add_argument('--restore', type=Path, help='Diretório de backup datado')
    ap.add_argument('--allow-missing', action='store_true', help='Preparar arquivos mesmo sem dependências; não declara desktop funcional')
    ap.add_argument('--with-session', action='store_true', help='Registrar entrada Wayland administrativa com backup')
    ap.add_argument('--provenance', help='JSON da origem/commit, fornecido por instalar.sh')
    ap.add_argument('--with-fonts', action='store_true', help='Disponibilizar fontes originais no fontconfig do usuário')
    ap.add_argument('--with-portals', action='store_true', help='Instalar preferência de portais específica de Hyprland')
    args = ap.parse_args(argv)
    if args.apply and args.dry_run:
        raise ValueError('Escolha --apply ou --dry-run')
    home = args.home.expanduser().resolve()
    if not home.is_dir():
        raise ValueError('Home de destino deve existir')
    if args.restore:
        return restore(args.restore, home, args.apply)
    session_change = False
    if args.with_session:
        if home != Path.home().resolve() or os.getuid() == 0:
            raise ValueError('--with-session exige a home do usuário comum atual')
        probe = subprocess.run([sys.executable, str(ROOT / 'tools/session_admin.py'), 'probe'])
        if probe.returncode not in (0, 3):
            raise ValueError('Não foi possível inspecionar a entrada de sessão')
        session_change = probe.returncode == 3
    missing = dependencies()
    previous = {}
    backup_root = home / '.local/state' / NAME / 'backups'
    if backup_root.is_dir():
        for journal in sorted(backup_root.glob('*/manifest.json')):
            if (journal.parent / 'restore-report.json').exists():
                continue
            for entry in json.loads(journal.read_text()).get('changes', []):
                previous[entry['path']] = entry['after']
    changes = []
    for src, dst, preserve in plan(home, args.with_fonts, args.with_portals):
        check_parents(dst, home)
        before = fingerprint(dst)
        after = desired(src, dst)
        if before == after or (preserve and before is not None):
            continue
        rel = str(dst.relative_to(home))
        if rel in previous and before != previous[rel]:
            raise ValueError('Alteração local preservada; resolva antes de atualizar: ' + str(dst))
        if before and before['kind'] == 'directory':
            raise ValueError('Arquivo de destino é um diretório: ' + str(dst))
        changes.append((src, dst, before, after))
    print(f'Destino: {home} | {len(changes)} arquivos/links a alterar')
    print('Preserva shell, Neovim, Kitty global e o gerenciador de login instalado.')
    if not args.apply:
        for _, dst, _, _ in changes[:12]:
            print('DRY-RUN ' + str(dst.relative_to(home)))
        print('Use --apply para aplicar. Nenhum arquivo foi alterado.')
        return 0
    if missing and not args.allow_missing:
        raise ValueError('Dependências ausentes/antigas; instale-as antes ou use --allow-missing para preparar apenas arquivos')
    if not changes and not session_change:
        print('Instalação já corresponde aos arquivos entregues; nenhuma alteração.')
        return 0
    backup_root = home / '.local/state' / NAME / 'backups'
    check_parents(backup_root / 'lock', home)
    backup_root.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (backup_root / '.install.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        # Recheck under lock; concurrent installers must never overwrite unseen changes.
        if any(fingerprint(dst) != before for _, dst, before, _ in changes):
            raise ValueError('Destino mudou durante a inspeção; execute novamente')
        stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
        backup = backup_root / stamp
        backup.mkdir(mode=0o700)
        manifest = {'version': 2, 'home': str(home), 'created': stamp, 'changes': [],
                    'provenance': json.loads(args.provenance) if args.provenance else {'source': 'local'}}
        save(backup / 'manifest.json', manifest)
        try:
            for src, dst, before, after in changes:
                rel = dst.relative_to(home)
                if before:
                    copy_atomic(dst, backup / 'files' / rel)
                manifest['changes'].append({'path': str(rel), 'before': before, 'after': after})
                # Journal before replacement: interruption can be restored safely.
                save(backup / 'manifest.json', manifest)
                if src:
                    copy_atomic(src, dst)
                else:
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    temp = dst.with_name(dst.name + '.gh0stzk-new')
                    temp.unlink(missing_ok=True)
                    temp.symlink_to(after['target'])
                    os.replace(temp, dst)
            if session_change:
                manifest['session'] = uuid.uuid4().hex
                save(backup / 'manifest.json', manifest)
                subprocess.run(['sudo', sys.executable, str(ROOT / 'tools/session_admin.py'),
                                'install', manifest['session']], check=True)
            (backup / 'changes.log').write_text('\n'.join(x['path'] for x in manifest['changes']) + '\n')
        except Exception:
            print('Instalação interrompida. Backup recuperável: ' + str(backup), file=sys.stderr)
            raise
    print('Aplicado. Backup: ' + str(backup))
    print('Restaurar: python3 ' + shlex.quote(str(home / '.local/share' / NAME / 'install.py')) +
          ' --restore ' + shlex.quote(str(backup)) + ' --apply')
    if args.with_fonts:
        print('Atualize o cache quando desejar: fc-cache -f ~/.local/share/fonts/gh0stzk-hyprland')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, ValueError, subprocess.SubprocessError) as e:
        print('Erro: ' + str(e), file=sys.stderr)
        sys.exit(1)
