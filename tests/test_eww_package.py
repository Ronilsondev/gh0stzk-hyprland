"""Receita real, fontes temporárias e Cargo simulado: nenhum build/instalação real."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECIPE = ROOT / 'tools/eww/PKGBUILD'


class EwwPackageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='eww recipe ')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.srcdir = self.base / 'sources with spaces'
        self.source = self.srcdir / 'eww-0.6.0'
        self.source.mkdir(parents=True)
        self.scripts = self.base / 'mock commands'
        self.scripts.mkdir()
        self.log = self.base / 'cargo.jsonl'
        self.home = self.base / 'home'
        self.global_cache = self.home / '.cargo'
        self.inherited_cache = self.base / 'inherited cargo'
        for cache in (self.global_cache, self.inherited_cache):
            cache.mkdir(parents=True)
            (cache / 'sentinel').write_text('do not modify')
        cargo = self.scripts / 'cargo'
        cargo.write_text('#!' + sys.executable + ' -I\n' + r'''
import json, os, pathlib, sys
args = sys.argv[1:]
with open(os.environ['MOCK_LOG'], 'a') as stream:
    stream.write(json.dumps({'args': args, 'home': os.environ.get('CARGO_HOME')}) + '\n')
if args[0] == os.environ.get('MOCK_FAIL'):
    sys.exit(23)
if args[0] == 'update' and not os.environ.get('MOCK_NO_UPDATE'):
    old = args[args.index('-p') + 1].split('@')[1]
    new = args[args.index('--precise') + 1]
    lock = pathlib.Path('Cargo.lock')
    lock.write_text(lock.read_text().replace('version = "' + old + '"', 'version = "' + new + '"'))
''')
        cargo.chmod(0o755)
        self.env = dict(os.environ, HOME=str(self.home), CARGO_HOME=str(self.inherited_cache),
                        PATH=str(self.scripts) + ':' + os.environ['PATH'], MOCK_LOG=str(self.log))
        for key in ('BASH_ENV', 'ENV', 'MOCK_FAIL', 'MOCK_NO_UPDATE'):
            self.env.pop(key, None)
        self.lock('0.3.34')

    def lock(self, *versions):
        # The actual upstream has both time 0.1.45 and time 0.3.34.
        entries = [('time', '0.1.45'), ('not-time', '0.3.1')]
        entries.extend(('time', version) for version in versions)
        text = 'version = 3\n' + ''.join(
            f'\n[[package]]\nname = "{name}"\nversion = "{version}"\n' for name, version in entries)
        (self.source / 'Cargo.lock').write_text(text)

    def phase(self, name, **extra):
        # Separate Bash processes mirror makepkg's phase boundaries.
        return subprocess.run(['/bin/bash', '-c', 'source "$1"; cd "$srcdir"; "$2"',
                               'recipe-test', str(RECIPE), name],
                              env=self.env | {'srcdir': str(self.srcdir)} | extra,
                              text=True, capture_output=True, timeout=20)

    def calls(self):
        return [json.loads(line) for line in self.log.read_text().splitlines()] if self.log.exists() else []

    def test_cleanbuild_reapplies_fix_and_uses_private_cache_in_both_phases(self):
        # A pre-cleanbuild edit disappears; prepare must correct the new extraction.
        self.lock('0.3.36')
        for _ in range(2):
            shutil.rmtree(self.source)
            self.source.mkdir()
            self.lock('0.3.34')
            for phase in ('prepare', 'build'):
                result = self.phase(phase)
                self.assertEqual(result.returncode, 0, result.stderr)
            packages = tomllib.loads((self.source / 'Cargo.lock').read_text())['package']
            self.assertEqual([p['version'] for p in packages if p['name'] == 'time'],
                             ['0.1.45', '0.3.36'])
        expected = [['update', '-p', 'time@0.3.34', '--precise', '0.3.36'],
                    ['fetch', '--locked'],
                    ['build', '--frozen', '--release', '--no-default-features', '--features', 'wayland']]
        self.assertEqual([call['args'] for call in self.calls()], expected * 2)
        self.assertEqual({call['home'] for call in self.calls()}, {str(self.srcdir / '.cargo-home')})
        for cache in (self.global_cache, self.inherited_cache):
            self.assertEqual([p.name for p in cache.iterdir()], ['sentinel'])
            self.assertEqual((cache / 'sentinel').read_text(), 'do not modify')

    def test_compatible_versions_are_not_downgraded(self):
        for version in ('0.3.36', '0.3.37', '0.3.100'):
            with self.subTest(version=version):
                self.lock(version)
                result = self.phase('prepare')
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn(f'version = "{version}"', (self.source / 'Cargo.lock').read_text())
        self.assertEqual([call['args'] for call in self.calls()], [['fetch', '--locked']] * 3)

    def test_prepare_is_repeatable_without_another_update(self):
        for _ in range(2):
            result = self.phase('prepare')
            self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([call['args'][0] for call in self.calls()], ['update', 'fetch', 'fetch'])

    def test_update_failure_stops_before_fetch_and_build(self):
        result = self.phase('prepare', MOCK_FAIL='update')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('não foi possível atualizar time@0.3.34 para 0.3.36', result.stderr)
        self.assertEqual([call['args'][0] for call in self.calls()], ['update'])

    def test_ineffective_update_is_detected_before_fetch(self):
        result = self.phase('prepare', MOCK_NO_UPDATE='1')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('0.3.34 incompatível', result.stderr)
        self.assertEqual([call['args'][0] for call in self.calls()], ['update'])

    def test_fetch_failure_is_reported(self):
        result = self.phase('prepare', MOCK_FAIL='fetch')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('cargo fetch --locked falhou', result.stderr)
        self.assertNotIn('build', [call['args'][0] for call in self.calls()])

    def test_build_rejects_old_lock_even_when_prepare_was_skipped(self):
        for versions in (('0.3.34',), ('0.3.36', '0.3.34')):
            with self.subTest(versions=versions):
                self.lock(*versions)
                result = self.phase('build')
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('0.3.34 incompatível', result.stderr)
        self.assertEqual(self.calls(), [])

    def test_build_revalidates_after_prepare(self):
        self.assertEqual(self.phase('prepare').returncode, 0)
        self.lock('0.3.34')
        result = self.phase('build')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('execute prepare()', result.stderr)
        self.assertEqual([call['args'][0] for call in self.calls()], ['update', 'fetch'])

    def test_multiple_versions_use_unambiguous_selector(self):
        self.lock('0.3.34', '0.3.37')
        result = self.phase('prepare')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.calls()[0]['args'], ['update', '-p', 'time@0.3.34', '--precise', '0.3.36'])
        result = self.phase('build')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('version = "0.3.37"', (self.source / 'Cargo.lock').read_text())

    def test_invalid_lock_stops_without_cargo(self):
        lock = self.source / 'Cargo.lock'
        cases = [None, 'not toml [', 'version = 3\n', 'package = "invalid"',
                 '[[package]]\nname="time"\n', '[[package]]\nname="time"\nversion=34\n',
                 '[[package]]\nname="time"\nversion="0.3.36-rc.1"\n',
                 '[[package]]\nname="time"\nversion="garbage"\n',
                 '[[package]]\nname="time"\nversion="0.2.27"\n',
                 '[[package]]\nname="time"\nversion="0.1.45"\n',
                 '[[package]]\nname="time-macros"\nversion="0.3.36"\n']
        for text in cases:
            with self.subTest(text=text):
                lock.unlink(missing_ok=True)
                if text is not None:
                    lock.write_text(text)
                for phase in ('prepare', 'build'):
                    result = self.phase(phase)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn('Erro Eww:', result.stderr)
                    self.assertIn('Cargo.lock', result.stderr)
        self.assertEqual(self.calls(), [])

    def test_python_imports_are_isolated_from_sources(self):
        (self.source / 'tomllib.py').write_text('raise RuntimeError("untrusted module")\n')
        result = self.phase('prepare')
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_source_integrity_license_and_wayland_contract(self):
        result = subprocess.run(['/bin/bash', '-c',
                                 'source "$1"; printf "%s\\n" "$pkgrel" "${license[*]}" "${source[*]}" "${sha256sums[*]}" "${makedepends[*]}"',
                                 'recipe-test', str(RECIPE)], capture_output=True, text=True, check=True)
        self.assertEqual(result.stdout.splitlines(), [
            '2', 'MIT', 'eww-0.6.0.tar.gz::https://codeload.github.com/elkowar/eww/tar.gz/refs/tags/v0.6.0',
            'cef361946946c566b79f8ddc6208d1a3f16b4ff9961439a3f86935e1cfa174a1', 'rust python'])
        (self.source / 'target/release').mkdir(parents=True)
        (self.source / 'target/release/eww').write_text('fixture executable')
        (self.source / 'LICENSE').write_text('fixture MIT license')
        pkgdir = self.base / 'package'
        result = self.phase('package', pkgdir=str(pkgdir))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((pkgdir / 'usr/share/licenses/eww/LICENSE').read_text(), 'fixture MIT license')
        self.assertTrue(os.access(pkgdir / 'usr/bin/eww', os.X_OK))


if __name__ == '__main__':
    unittest.main()
