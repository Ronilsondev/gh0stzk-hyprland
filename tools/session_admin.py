#!/usr/bin/env python3
"""Operação administrativa limitada a uma entrada Wayland por UID, com journal root."""
import argparse
import base64
import fcntl
import json
import os
import pwd
import re
import sys
import tempfile
from pathlib import Path

SESSIONS = Path('/usr/share/wayland-sessions')
JOURNALS = Path('/var/lib/gh0stzk-hyprland/sessions')


def snapshot(path):
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise ValueError('Entrada de sessão deve ser arquivo regular: ' + str(path))
    if not path.exists():
        return None
    return {'data': base64.b64encode(path.read_bytes()).decode(), 'mode': path.stat().st_mode & 0o777}


def atomic(path, data, mode):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.gh0stzk-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(name, mode)
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def desktop(home):
    # Exec= has two escaping layers and no shell: first escape the backslash
    # itself, then the reserved characters, and finally double literal '%'.
    # Doubling the backslashes afterwards would undo the quoting of the others.
    path = str(home / '.local/bin/gh0stzk-session')
    if any(ord(c) < 32 for c in path):
        raise ValueError('Home contém caractere de controle')
    escaped = (path.replace('\\', '\\\\').replace('"', '\\"')
               .replace('`', '\\`').replace('$', '\\$').replace('%', '%%'))
    return ('[Desktop Entry]\nName=Hyprland — gh0stzk\nComment=Sessão isolada gh0stzk\n'
            'Type=Application\nDesktopNames=Hyprland\nExec="' + escaped + '" --login\n').encode()


def operation(action, uid, token=None):
    home = Path(pwd.getpwuid(uid).pw_dir)
    dest = SESSIONS / f'gh0stzk-{uid}.desktop'
    after = {'data': base64.b64encode(desktop(home)).decode(), 'mode': 0o644}
    if action == 'probe':
        return 0 if snapshot(dest) == after else 3
    if not token or not re.fullmatch(r'[a-f0-9]{32}', token):
        raise ValueError('Token inválido')
    JOURNALS.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (JOURNALS / '.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        journal = JOURNALS / f'{uid}-{token}.json'
        if action == 'install':
            if journal.exists():
                raise ValueError('Token já utilizado')
            before = snapshot(dest)
            record = {'uid': uid, 'before': before, 'after': after}
            atomic(journal, (json.dumps(record) + '\n').encode(), 0o600)
            atomic(dest, base64.b64decode(after['data']), after['mode'])
        else:
            if not journal.exists():
                # Caller journals the intent before invoking sudo. No journal means no admin mutation.
                return 0
            record = json.loads(journal.read_text())
            if record['uid'] != uid:
                raise ValueError('Journal pertence a outro usuário')
            current = snapshot(dest)
            if current == record['before']:
                return 0
            if current != record['after']:
                print('PRESERVADO: entrada de sessão modificada posteriormente', file=sys.stderr)
                return 2
            if record['before'] is None:
                dest.unlink()
            else:
                atomic(dest, base64.b64decode(record['before']['data']), record['before']['mode'])
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('action', choices=['probe', 'install', 'restore'])
    ap.add_argument('token', nargs='?')
    args = ap.parse_args()
    uid = int(os.environ.get('SUDO_UID', os.getuid()))
    if uid <= 0 or (args.action != 'probe' and os.geteuid() != 0):
        raise ValueError('Use sudo a partir de um usuário comum para registrar/restaurar a sessão.')
    return operation(args.action, uid, args.token)


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, ValueError) as exc:
        print('Sessão: ' + str(exc), file=sys.stderr)
        sys.exit(1)
