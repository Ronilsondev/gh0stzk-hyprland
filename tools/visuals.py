#!/usr/bin/env python3
"""Download pinned data archives. Never installs packages or executes archive scripts."""
import hashlib
import configparser
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def extract(archive, dest):
    """Only regular data and confined relative symlinks; no tar extraction as root."""
    omitted = []
    with tempfile.TemporaryFile() as raw:
        subprocess.run(['zstd', '-dc', str(archive)], stdout=raw, check=True)
        raw.seek(0)
        with tarfile.open(fileobj=raw) as tar:
            metadata = tar.extractfile('.PKGINFO').read().decode()
            if 'license = GPL3\n' not in metadata:
                raise ValueError('Licença inesperada: ' + archive.name)
            links = []
            for member in tar:
                path = PurePosixPath(member.name)
                if path.is_absolute() or '..' in path.parts:
                    raise ValueError('Caminho inseguro no recurso: ' + member.name)
                if not member.name.startswith(('usr/share/icons/', 'usr/share/themes/')):
                    continue
                target = dest / Path(*path.parts[2:])
                if member.isdir():
                    target.mkdir(parents=True, exist_ok=True)
                elif member.isfile():
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with tar.extractfile(member) as src, target.open('wb') as out:
                        shutil.copyfileobj(src, out)
                elif member.issym():
                    links.append((target, member.linkname))
                else:
                    raise ValueError('Tipo inesperado: ' + member.name)
            for target, value in links:
                if value.startswith('/') or not (target.parent / value).resolve().is_relative_to(dest.resolve()):
                    omitted.append(str(target.relative_to(dest)))
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                target.symlink_to(value)
    return omitted


def check(share):
    missing = []
    for file in (ROOT / 'themes').glob('*/theme.json'):
        p = json.loads(file.read_text())['palette']
        for rel in (f'themes/{p["gtk_theme"]}/gtk-3.20/gtk.css',
                    f'icons/{p["gtk_icons"]}/index.theme',
                    f'icons/{p["gtk_cursor"]}/cursors/left_ptr'):
            if not (share / rel).is_file():
                missing.append(file.parent.name + ': ' + rel)
    for index in (share / 'icons').glob('*/index.theme'):
        parser = configparser.ConfigParser(interpolation=None, strict=False)
        parser.read(index)
        for parent in parser.get('Icon Theme', 'Inherits', fallback='').split(','):
            parent = parent.strip()
            if parent and parent not in ('Papirus', 'hicolor', 'Adwaita') and not (share / 'icons' / parent / 'index.theme').is_file():
                missing.append(index.parent.name + ': herança ' + parent)
    if missing:
        raise ValueError('Recursos visuais obrigatórios ausentes: ' + '; '.join(missing))


def install(home=None, cache=None):
    home = Path(home or Path.home())
    data = json.loads((ROOT / 'visuals.json').read_text())
    base = home / '.local/share/gh0stzk-hyprland-visuals'
    dest = base / data['revision']
    if not (dest / 'report.json').exists():
        base.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='.stage-', dir=base) as tmp:
            stage = Path(tmp)
            share = stage / 'share'
            share.mkdir()
            omitted = []
            for item in data['archives']:
                archive = Path(cache) / item['file'] if cache else stage / item['file']
                if not cache:
                    subprocess.run(['curl', '--fail', '--location', '--silent', '--show-error',
                                    '--proto', '=https', '--proto-redir', '=https', '--max-time', '180',
                                    '--output', str(archive), item['url']], check=True)
                if hashlib.sha256(archive.read_bytes()).hexdigest() != item['sha256']:
                    raise ValueError('Hash incorreto: ' + item['file'])
                omitted.extend(extract(archive, share))
                if not cache:
                    archive.unlink()
            check(share)
            broken = [str(p.relative_to(share)) for p in share.rglob('*') if p.is_symlink() and not p.exists()]
            report = dict(data, omitted_links=omitted, broken_links=broken)
            (stage / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
            os.rename(stage, dest)
    check(dest / 'share')
    temp = base / 'current.new'
    temp.unlink(missing_ok=True)
    temp.symlink_to(dest.name)
    os.replace(temp, base / 'current')
    report = json.loads((dest / 'report.json').read_text())
    print('Recursos visuais conferidos: ' + str(dest))
    if report['omitted_links'] or report['broken_links']:
        print('Limitação dos arquivos originais: ícones individuais indisponíveis; lista exata em ' + str(dest / 'report.json'))
    return dest
