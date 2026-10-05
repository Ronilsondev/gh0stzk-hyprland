"""Integração isolada: rede, pacman, sudo, serviços e Hyprland são simulados."""
import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tools')]
import bootstrap
import install
import session_admin
import validate


class BootstrapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = tempfile.TemporaryDirectory(prefix='gh bootstrap ')
        cls.repo = Path(cls.base.name) / 'repo with spaces'
        shutil.copytree(ROOT, cls.repo, ignore=shutil.ignore_patterns('.git', '.agents', '.aws', '.codex', '__pycache__', 'upstream'))
        cls.osfile = Path(cls.base.name) / 'os-release'
        cls.osfile.write_text('ID=arch\n')
        script = cls.repo / 'instalar.sh'
        script.write_text(script.read_text().replace('source /etc/os-release', 'source "' + str(cls.osfile) + '"'))
        backend = cls.repo / 'tools/bootstrap.py'
        backend.write_text(backend.read_text().replace("Path('/etc/os-release')", 'Path(' + repr(str(cls.osfile)) + ')'))
        cls.git = shutil.which('git')
        for cmd in ([cls.git, 'init', '-q', '-b', 'main', str(cls.repo)],
                    [cls.git, '-C', str(cls.repo), 'add', '.'],
                    [cls.git, '-C', str(cls.repo), '-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '-qm', 'fixture']):
            subprocess.run(cmd, check=True, capture_output=True)
        # A published clone has an origin; the installer must discover it from `git remote -v`.
        subprocess.run([cls.git, '-C', str(cls.repo), 'remote', 'add', 'origin',
                        'https://github.com/test/fixture.git'], check=True, capture_output=True)
        cls.head = subprocess.check_output([cls.git, '-C', str(cls.repo), 'rev-parse', 'HEAD'], text=True).strip()

    @classmethod
    def tearDownClass(cls):
        cls.base.cleanup()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='gh install test ')
        self.basepath = Path(self.temp.name)
        self.home = self.basepath / 'home with spaces'
        self.home.mkdir()
        self.bin = self.basepath / 'mock bin'
        self.bin.mkdir()
        self.logs = self.basepath / 'calls.jsonl'
        self.downloads = self.basepath / 'downloads'
        self.downloads.mkdir()
        self.env = dict(os.environ, HOME=str(self.home), TMPDIR=str(self.downloads),
                        PATH=str(self.bin) + ':' + os.environ['PATH'], MOCK_LOG=str(self.logs),
                        MOCK_REPO=str(self.repo), REAL_GIT=self.git, PYTHONDONTWRITEBYTECODE='1')
        for key in ('XDG_CONFIG_HOME', 'XDG_STATE_HOME', 'XDG_DATA_HOME', 'BASH_ENV', 'SUDO_UID'):
            self.env.pop(key, None)
        mock = self.bin / '_mock'
        mock.write_text('#!' + sys.executable + '\n' + r'''
import json, os, pathlib, subprocess, sys
name = pathlib.Path(sys.argv[0]).name
args = sys.argv[1:]
with open(os.environ['MOCK_LOG'], 'a') as f: f.write(json.dumps([name, *args]) + '\n')
fail = os.environ.get('MOCK_FAIL')
if name == 'id': print('0' if fail == 'root' else '1000'); sys.exit(0)
if name == 'df':
    print('Filesystem 1024-blocks Used Available Capacity Mounted')
    print('mock 99999999 1 ' + ('1024' if fail == 'disk' else '99999998') + ' 1% /'); sys.exit(0)
if name == 'uname': print('x86_64' if fail != 'arch' else 'aarch64'); sys.exit(0)
if name == 'sudo':
    if args[0] in ('pacman', 'systemctl'): sys.exit(subprocess.call(args))
    if 'session_admin.py' in ' '.join(args): sys.exit(0)
    sys.exit(99)
if name == 'curl': sys.exit(22 if fail == 'download' else 0)
if name == 'git':
    if 'fetch' in args:
        if fail == 'git': sys.exit(128)
        args = [os.environ['MOCK_REPO'] if x.startswith('https://github.com/') else x for x in args]
        args = ['-c', 'protocol.file.allow=always', *[x.replace('protocol.file.allow=never', 'protocol.file.allow=always') for x in args]]
    sys.exit(subprocess.call([os.environ['REAL_GIT'], *args]))
if name == 'pacman':
    if '-Q' in args: sys.exit(1)
    sys.exit(1 if fail == 'pacman' and '-Syu' in args else 0)
if name == 'systemctl':
    if 'is-active' in args or 'is-enabled' in args: sys.exit(1)
    sys.exit(0)
if name == 'Hyprland':
    if '--version' in args: print('Hyprland 0.56.2'); sys.exit(0)
    if '--help' in args: print('--verify-config'); sys.exit(0)
    sys.exit(1 if fail == 'hyprland' else 0)
if name == 'rofi' and '-version' in args: print('Version: 2.0.0')
sys.exit(0)
''')
        mock.chmod(0o755)
        commands = set(json.loads((ROOT / 'packages.json').read_text())['required_commands'])
        for name in commands | {'sudo', 'pacman', 'systemctl', 'curl', 'git', 'df', 'id', 'uname'}:
            (self.bin / name).symlink_to(mock)

    def tearDown(self):
        self.temp.cleanup()

    def execute(self, *args, standalone=False, fail=None, stdin=None):
        script = self.repo / 'instalar.sh'
        if standalone:
            script = self.basepath / 'instalar.sh'
            shutil.copy2(self.repo / 'instalar.sh', script)
        env = self.env | ({'MOCK_FAIL': fail} if fail else {})
        return subprocess.run(['/bin/bash', str(script), *args], env=env, text=True,
                              input=stdin, capture_output=True, timeout=60)

    def calls(self):
        return [json.loads(x) for x in self.logs.read_text().splitlines()] if self.logs.exists() else []

    def test_local_full_install_second_install_preferences_restore(self):
        local = self.home / '.config/gh0stzk-hyprland/local.lua'
        local.parent.mkdir(parents=True)
        local.write_text('-- preserve me\n')
        prefs = local.with_name('preferences.json')
        prefs.write_text('{"widgets": false}')
        portal = self.home / '.config/xdg-desktop-portal/hyprland-portals.conf'
        portal.parent.mkdir()
        portal.write_text('[preferred]\ndefault=gtk\n')
        result = self.execute('--yes', '--without-session')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(local.read_text(), '-- preserve me\n')
        self.assertEqual(prefs.read_text(), '{"widgets": false}')
        self.assertIn('default=gtk', portal.read_text())
        backups = list((self.home / '.local/state/gh0stzk-hyprland/backups').glob('*/manifest.json'))
        self.assertEqual(len(backups), 1)
        provenance = json.loads(backups[0].read_text())['provenance']
        # Origin discovered from `git remote -v`; one coherent commit recorded.
        self.assertEqual(provenance['source'], 'https://github.com/test/fixture')
        self.assertEqual(provenance['ref'], 'main')
        self.assertEqual(len(provenance['commit']), 40)
        self.assertIn('remote origin detectado', result.stdout)
        result = self.execute('--yes', '--without-session')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(len(list(backups[0].parent.parent.glob('*/manifest.json'))), 1)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(install.main(['--home', str(self.home), '--restore', str(backups[0].parent), '--apply']), 0)
        self.assertFalse((self.home / '.local/bin/gh0stzk').exists())
        self.assertTrue(local.exists())
        calls = self.calls()
        self.assertTrue(any(c[:3] == ['pacman', '-Syu', '--needed'] for c in calls))
        self.assertFalse(any('--noconfirm' in c or '--allow-missing' in c for c in calls))

    def test_pinned_ref_resolves_one_commit_and_never_mixes_files(self):
        # A tag stands for an immutable reference: the abridged SHA of HEAD is not
        # reachable through a remote fetch, which is exactly why tags/releases matter.
        subprocess.run([self.git, '-C', str(self.repo), 'tag', 'v-test'], check=True, capture_output=True)
        result = self.execute('--yes', '--without-session', '--ref', 'v-test', '--repo',
                              'https://github.com/test/fixture', standalone=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        backups = list((self.home / '.local/state/gh0stzk-hyprland/backups').glob('*/manifest.json'))
        provenance = json.loads(backups[0].read_text())['provenance']
        self.assertEqual(provenance['commit'], self.head)
        self.assertEqual(provenance['ref'], 'v-test')
        installed = self.home / '.local/share/gh0stzk-hyprland'
        # Every applied file must come from that single commit, byte for byte.
        for name in ('install.py', 'instalar.sh', 'packages.json', 'tools/bootstrap.py'):
            self.assertEqual((installed / name).read_bytes(), (self.repo / name).read_bytes(), name)
        self.assertIn(self.head, result.stdout)
        self.assertEqual(list(self.downloads.iterdir()), [])
        checkouts = [c for c in self.calls() if c[0] == 'git' and 'checkout' in c]
        self.assertEqual(len(checkouts), 1)
        self.assertIn('--detach', checkouts[0])
        self.assertIn(self.head, checkouts[0])

    def test_unreachable_ref_fails_without_touching_home(self):
        result = self.execute('--yes', '--repo', 'https://github.com/test/fixture',
                              '--ref', 'nao-existe', standalone=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Download do Git falhou', result.stderr)
        self.assertIn('NÃO foram aplicados', result.stderr)
        self.assertFalse((self.home / '.local').exists())
        self.assertEqual(list(self.downloads.iterdir()), [])

    def test_help_and_unknown_option(self):
        result = self.execute('--help')
        self.assertEqual(result.returncode, 0, result.stderr)
        for expected in ('--dry-run', '--yes', '--repo', '--ref', '--optional', '--with-eww',
                         '--without-session', 'pacman -Syu --needed', 'reinicia nem encerra'):
            self.assertIn(expected, result.stdout)
        self.assertEqual(self.calls(), [])
        self.assertNotEqual(self.execute('--nao-existe').returncode, 0)

    def test_refuses_root_unsupported_arch_and_small_disk(self):
        for failure, expected in (('root', 'usuário comum'), ('arch', 'x86_64'), ('disk', '2 GiB')):
            result = self.execute('--yes', fail=failure)
            self.assertNotEqual(result.returncode, 0, expected)
            self.assertIn(expected, result.stderr)
            self.assertFalse((self.home / '.local').exists(), expected)
            self.assertFalse(any(c[0] in ('pacman',) for c in self.calls()), expected)

    def test_refuses_non_arch_distribution(self):
        original = self.osfile.read_text()
        self.osfile.write_text('ID=manjaro\n')
        try:
            result = self.execute('--yes')
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('Arch Linux', result.stderr)
            self.assertFalse((self.home / '.local').exists())
        finally:
            self.osfile.write_text(original)

    def test_standalone_pinned_download_and_cleanup(self):
        result = self.execute('--yes', '--without-session', '--repo', 'https://github.com/test/fixture', standalone=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(list(self.downloads.iterdir()), [])
        self.assertTrue((self.home / '.local/share/gh0stzk-hyprland/tools/session_admin.py').is_file())
        self.assertTrue(any('checkout' in c and '--detach' in c for c in self.calls()))

    def test_download_failures_never_apply(self):
        for failure in ('download', 'git'):
            result = self.execute('--yes', '--repo', 'https://github.com/test/fixture', standalone=True, fail=failure)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse((self.home / '.local').exists())
            self.assertEqual(list(self.downloads.iterdir()), [])

    def test_pacman_failure_stops_before_validation_and_apply(self):
        result = self.execute('--yes', fail='pacman')
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.home / '.local').exists())
        self.assertFalse(any(c[0] == 'Hyprland' for c in self.calls()))

    def test_rejected_hyprland_stops_before_apply(self):
        result = self.execute('--yes', fail='hyprland')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('verify-config falhou', result.stderr)
        self.assertFalse((self.home / '.local').exists())

    def test_dry_run_local_and_standalone_do_not_write(self):
        for standalone in (False, True):
            before = list(self.home.rglob('*'))
            result = self.execute('--dry-run', standalone=standalone)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(before, list(self.home.rglob('*')))
            self.assertEqual(list(self.downloads.iterdir()), [])
        # Only read-only git calls are tolerated; never a mutation or a network op.
        for call in self.calls():
            self.assertNotIn(call[0], ('sudo', 'pacman', 'curl', 'fc-cache'), call)
            if call[0] == 'git':
                for verb in ('fetch', 'clone', 'checkout', 'pull', 'push', 'init', 'add', 'commit'):
                    self.assertNotIn(verb, call, call)

    def test_dry_run_without_python_or_desktop(self):
        # Restrict PATH to dirname: Bash/pwd/printf are builtins, Python truly absent.
        emptybin = self.basepath / 'minimal'
        emptybin.mkdir()
        (emptybin / 'dirname').symlink_to(shutil.which('dirname'))
        self.env['PATH'] = str(emptybin)
        result = self.execute('--dry-run')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('LIMITAÇÃO', result.stdout)
        self.assertIn('apenas o instalar.sh', result.stdout)
        self.assertEqual(list(self.home.iterdir()), [])
        # Standalone with python3 available still cannot read the manifest.
        result = self.execute('--dry-run', standalone=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('LIMITAÇÃO', result.stdout)
        self.assertIn('git clone', result.stdout)
        self.assertEqual(list(self.home.iterdir()), [])
        self.assertEqual(list(self.downloads.iterdir()), [])

    def test_confirmation_cancellation_no_admin(self):
        result = self.execute(stdin='n\n')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(any(c[0] in ('sudo', 'pacman') for c in self.calls()))

    def test_upstream_and_missing_origin_rejected(self):
        for candidate in ('https://github.com/gh0stzk/dotfiles', 'https://github.com/gh0stzk/dotfiles.git',
                          'http://github.com/test/fixture', 'git@github.com:evil/repo.git',
                          'https://github.com/test/fixture with space', 'https://example.com/a/b'):
            self.assertNotEqual(self.execute('--repo', candidate).returncode, 0, candidate)
        # An ssh remote of a real repository is normalized to HTTPS.
        self.assertEqual(self.execute('--dry-run', '--repo', 'git@github.com:test/fixture.git').returncode, 0)
        result = self.execute('--yes', standalone=True)
        self.assertIn('Origem ainda não definida', result.stderr)

    def test_install_without_session_writes_no_admin_file(self):
        result = self.execute('--yes', '--without-session')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse(any('session_admin.py' in c for c in self.calls()))
        manifest = json.loads(next((self.home / '.local/state/gh0stzk-hyprland/backups').glob('*/manifest.json')).read_text())
        self.assertNotIn('session', manifest)


class PolicyTests(unittest.TestCase):
    def test_native_validation_is_required(self):
        with patch.object(validate.shutil, 'which', return_value=None):
            with self.assertRaisesRegex(ValueError, 'Hyprland obrigatório'):
                validate.verify_hyprland(Path('/unused'), {}, required=True)

    def test_missing_required_dependencies_refuses_apply(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(install, 'dependencies', return_value=['Hyprland']), contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(ValueError):
                install.main(['--apply', '--home', tmp])
            self.assertEqual(list(Path(tmp).iterdir()), [])

    def test_network_conflict_refuses_services(self):
        with patch.object(bootstrap, 'configured', side_effect=lambda unit, user=False: unit == 'systemd-networkd.service'), patch.object(bootstrap, 'output', return_value=''):
            with self.assertRaisesRegex(ValueError, 'Rede existente'):
                bootstrap.service_plan()

    def test_invalid_package_manifest(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(bootstrap, 'ROOT', Path(tmp)):
            data = json.loads((ROOT / 'packages.json').read_text())
            data['official'].append('--bad-option')
            (Path(tmp) / 'packages.json').write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, 'Nome inválido'):
                bootstrap.manifest()

    def test_admin_session_backup_restore_and_local_edits(self):
        with tempfile.TemporaryDirectory(prefix='session test ') as tmp:
            folder = Path(tmp)
            with patch.object(session_admin, 'SESSIONS', folder / 'sessions'), patch.object(session_admin, 'JOURNALS', folder / 'journals'):
                dest = folder / 'sessions' / f'gh0stzk-{os.getuid()}.desktop'
                dest.parent.mkdir()
                dest.write_text('original')
                dest.chmod(0o640)
                before = session_admin.snapshot(dest)
                token = 'a' * 32
                self.assertEqual(session_admin.operation('install', os.getuid(), token), 0)
                self.assertEqual(session_admin.operation('probe', os.getuid()), 0)
                self.assertEqual(dest.stat().st_mode & 0o777, 0o644)
                self.assertEqual(session_admin.operation('restore', os.getuid(), token), 0)
                self.assertEqual(session_admin.snapshot(dest), before)
                self.assertEqual(session_admin.operation('restore', os.getuid(), token), 0)
                token = 'b' * 32
                session_admin.operation('install', os.getuid(), token)
                dest.write_text('later edit')
                self.assertEqual(session_admin.operation('restore', os.getuid(), token), 2)
                self.assertEqual(dest.read_text(), 'later edit')

    def test_desktop_quotes_spaces_and_field_codes(self):
        entry = session_admin.desktop(Path('/home/user space%')).decode()
        self.assertIn('Exec="/home/user space%%/.local/bin/gh0stzk-session"', entry)
        self.assertIn('Name=Hyprland — gh0stzk', entry)
        self.assertIn('Type=Application', entry)

    def test_desktop_escapes_reserved_exec_characters(self):
        # The backslash must be escaped first, otherwise the escapes added later
        # would be neutralised and the quoting broken.
        entry = session_admin.desktop(Path(r'/home/we$"ird`one')).decode()
        self.assertIn(r'Exec="/home/we\$\"ird\`one/.local/bin/gh0stzk-session"', entry)
        self.assertIn(r'Exec="/home/a\\b/.local/bin/gh0stzk-session"',
                      session_admin.desktop(Path(r'/home/a\b')).decode())
        self.assertEqual(session_admin.desktop(Path('/home/x')).decode().count('Exec='), 1)

    def test_installer_markers_and_upstream_guard(self):
        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp) / 'instalar.sh'
            shutil.copy2(ROOT / 'instalar.sh', script)
            script.chmod(0o755)
            original = script.read_text()
            self.assertIn('PROJECT_REPO', validate.check_installer(script))
            for broken, expected in (
                    ("PROJECT_REPO=''", 'PROJECT_REPO'),
                    ('--dry-run', '--dry-run'),
                    ('pacman -Syu --needed', 'pacman -Syu --needed')):
                script.write_text(original.replace(broken, 'REMOVIDO'))
                with self.assertRaisesRegex(ValueError, expected):
                    validate.check_installer(script)
            # A partial upgrade or a non-interactive transaction must be refused.
            for bad in ('sudo pacman -Sy --needed -- base-devel', 'sudo pacman -Syu --noconfirm -- x'):
                script.write_text(original.replace('sudo pacman -Syu --needed -- "${missing[@]}"', bad))
                with self.assertRaisesRegex(ValueError, 'atualização total e interativa'):
                    validate.check_installer(script)
            script.write_text(original.replace('python3 -B "$root/tools/bootstrap.py" --dry-run',
                                               'python3 -B "$root/tools/bootstrap.py" --allow-missing'))
            with self.assertRaisesRegex(ValueError, '--allow-missing'):
                validate.check_installer(script)
            script.write_text(original.replace(
                "PROJECT_REPO=''", "PROJECT_REPO='https://github.com/gh0stzk/dotfiles'", 1))
            with self.assertRaisesRegex(ValueError, 'upstream'):
                validate.check_installer(script)
            script.chmod(0o644)
            with self.assertRaisesRegex(ValueError, 'permissão'):
                validate.check_installer(script)
            script.chmod(0o755)
            script.unlink()
            with self.assertRaisesRegex(ValueError, 'ausente'):
                validate.check_installer(script)

    def test_manifest_requires_declared_origin_for_external_resources(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(bootstrap, 'ROOT', Path(tmp)):
            data = json.loads((ROOT / 'packages.json').read_text())
            data['official'].append('--bad-option')
            (Path(tmp) / 'packages.json').write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, 'Nome inválido'):
                bootstrap.manifest()
            data['official'] = data['official'][:-1]
            data['external_not_installed']['gh0stzk-icons-tokyo-night'] = 'tem um nome bonito'
            (Path(tmp) / 'packages.json').write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, 'Origem não declarada'):
                bootstrap.manifest()
            data['external_not_installed']['gh0stzk-icons-tokyo-night'] = 'repo http://exemplo.invalid/pkgs'
            data['official'].append('rofi')
            (Path(tmp) / 'packages.json').write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, 'Duplicatas'):
                bootstrap.manifest()

    def test_payload_survives_a_checkout_without_upstream(self):
        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp) / 'published'
            shutil.copytree(ROOT, copy, ignore=shutil.ignore_patterns('__pycache__', 'upstream', '.git'))
            self.assertFalse((copy / 'upstream').exists())
            with patch.object(bootstrap, 'ROOT', copy):
                bootstrap.payload()  # vendored resources are enough for a fresh install
                (copy / 'instalar.sh').chmod(0o644)
                with self.assertRaisesRegex(ValueError, 'permissão de execução'):
                    bootstrap.payload()
            (copy / 'instalar.sh').chmod(0o755)
            with patch.object(bootstrap, 'ROOT', copy):
                data = json.loads((copy / 'resources.json').read_text())
                victim = sorted(data)[0]
                (copy / victim).write_bytes(b'tampered')
                with self.assertRaisesRegex(ValueError, 'Recurso ausente/modificado'):
                    bootstrap.payload()

    def test_installer_bash_syntax_is_valid(self):
        subprocess.run(['bash', '-n', str(ROOT / 'instalar.sh')], check=True)
        for binary in sorted((ROOT / 'bin').glob('gh0stzk*')) + [ROOT / 'instalar.sh']:
            self.assertTrue(os.access(binary, os.X_OK), str(binary))


if __name__ == '__main__':
    unittest.main()
