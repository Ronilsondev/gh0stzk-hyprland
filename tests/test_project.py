import contextlib
import io
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'lib')]
import install
import runtime
from render import render_bars, theme


class InstallTests(unittest.TestCase):
    def test_real_install_idempotent_safe_restore(self):
        with tempfile.TemporaryDirectory(prefix='gh test ') as folder:
            home = Path(folder)
            launcher = home / '.local/bin/gh0stzk'
            launcher.parent.mkdir(parents=True)
            launcher.write_text('original\n')
            local = home / '.config/gh0stzk-hyprland/local.lua'
            local.parent.mkdir(parents=True)
            local.write_text('-- minha preferência\n')
            original = install.fingerprint(launcher)
            before = sorted(str(p.relative_to(home)) for p in home.rglob('*'))
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(install.main(['--home', folder]), 0)
            self.assertEqual(before, sorted(str(p.relative_to(home)) for p in home.rglob('*')))
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(install.main(['--home', folder, '--apply', '--allow-missing', '--with-portals', '--with-fonts']), 0)
            self.assertTrue(launcher.is_symlink())
            self.assertEqual(local.read_text(), '-- minha preferência\n')
            self.assertEqual(subprocess.check_output([str(launcher), 'list'], text=True).splitlines(),
                             sorted(p.parent.name for p in (ROOT / 'themes').glob('*/theme.json')))
            backup_root = home / '.local/state/gh0stzk-hyprland/backups'
            backups = [p for p in backup_root.iterdir() if p.is_dir()]
            with contextlib.redirect_stdout(io.StringIO()):
                install.main(['--home', folder, '--apply', '--allow-missing', '--with-portals', '--with-fonts'])
            self.assertEqual(backups, [p for p in backup_root.iterdir() if p.is_dir()])
            changed = home / '.local/share/gh0stzk-hyprland/config/hyprland.lua'
            changed.write_text('-- alteração posterior\n')
            extra = changed.parent / 'novo-arquivo'; extra.write_text('meu')
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(install.main(['--home', folder, '--restore', str(backups[0]), '--apply']), 2)
            self.assertEqual(changed.read_text(), '-- alteração posterior\n')
            self.assertEqual(extra.read_text(), 'meu')
            self.assertEqual(install.fingerprint(launcher), original)
            self.assertEqual(local.read_text(), '-- minha preferência\n')

    def test_parent_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as folder, tempfile.TemporaryDirectory() as outside:
            home = Path(folder)
            (home / '.local').symlink_to(outside)
            with self.assertRaises(ValueError), contextlib.redirect_stdout(io.StringIO()):
                install.main(['--home', folder])
            self.assertEqual(list(Path(outside).iterdir()), [])


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.state = Path(self.tmp.name) / 'state'
        self.config = Path(self.tmp.name) / 'config'
        self.patches = [patch.object(runtime, 'STATE', self.state),
                        patch.object(runtime, 'CURRENT', self.state / 'current'),
                        patch.object(runtime, 'CONFIG', self.config)]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in reversed(self.patches):
            p.stop()
        self.tmp.cleanup()

    def test_offline_selection_persistence_and_exact_rollback(self):
        with contextlib.redirect_stdout(io.StringIO()):
            runtime.apply_theme('emilia', offline=True)
            first = (self.state / 'current').resolve()
            runtime.apply_theme('pamela', offline=True)
            runtime.main(['rollback', '--offline'])
        self.assertEqual((self.state / 'current').resolve(), first)
        self.assertEqual(runtime.selected()['theme'], 'emilia')
        self.assertFalse(self.config.exists())

    def test_invalid_theme_does_not_change_selection(self):
        with contextlib.redirect_stdout(io.StringIO()):
            runtime.apply_theme('emilia', offline=True)
        before = (self.state / 'current').resolve()
        with self.assertRaises(ValueError):
            runtime.apply_theme('../invalid', offline=True)
        self.assertEqual(before, (self.state / 'current').resolve())

    def test_service_failure_rolls_back(self):
        with contextlib.redirect_stdout(io.StringIO()):
            runtime.apply_theme('emilia', offline=True)
        before = (self.state / 'current').resolve()
        mon = [{'name': 'virtual', 'width': 1600, 'height': 900, 'scale': 1}]
        with patch.object(runtime, 'require_session'), patch.object(runtime, 'monitors', return_value=mon), \
             patch.object(runtime, 'run'), patch.object(runtime, 'output', return_value=''), \
             patch.object(runtime, 'services', side_effect=[RuntimeError('falha simulada'), None]) as services:
            with self.assertRaises(RuntimeError):
                runtime.apply_theme('jan')
            self.assertEqual(services.call_count, 2)
        self.assertEqual(before, (self.state / 'current').resolve())

    def test_validation_failure_before_switch(self):
        with contextlib.redirect_stdout(io.StringIO()):
            runtime.apply_theme('emilia', offline=True)
        before = (self.state / 'current').resolve()
        with patch.object(runtime, 'validate_generation', side_effect=ValueError('erro de parser')):
            with self.assertRaises(ValueError):
                runtime.apply_theme('jan', offline=True)
        self.assertEqual(before, (self.state / 'current').resolve())

    def test_power_requires_positive_confirmation(self):
        for action in ('sair', 'reiniciar', 'desligar'):
            with patch.object(runtime, 'choose', return_value=0), patch.object(runtime, 'run') as runner, patch.object(runtime, 'dispatch') as dispatcher:
                runtime.power(action)
                runner.assert_not_called(); dispatcher.assert_not_called()
        with patch.object(runtime, 'choose', return_value=1), patch.object(runtime, 'run') as runner:
            runtime.power('desligar')
            runner.assert_called_once_with(['systemctl', 'poweroff'])

    def test_reused_pid_never_signalled(self):
        self.state.mkdir()
        with patch.object(runtime, 'records', return_value={'test': {'pid': 123, 'start': 'old'}}), \
             patch.object(runtime, 'process_identity', return_value='new'), patch.object(runtime.os, 'kill') as kill:
            runtime.stop('test')
            kill.assert_not_called()

    def test_monitors_and_theme_compositions(self):
        mons = [{'name': 'TEST-A', 'width': 1600, 'height': 900, 'scale': 1},
                {'name': 'TEST-B', 'width': 2560, 'height': 1440, 'scale': 2}]
        bars, _ = render_bars(theme('pamela'), mons)
        self.assertEqual(len(bars), 12)
        self.assertEqual({b['output'] for b in bars}, {'TEST-A', 'TEST-B'})
        self.assertEqual(bars[0]['width'], 40)
        self.assertEqual(bars[6]['width'], 32)
        vertical, _ = render_bars(theme('z0mbi3'), mons)
        self.assertTrue(all(b['position'] == 'left' for b in vertical))
        bottom, _ = render_bars(theme('isabel'), mons)
        self.assertTrue(all(b['position'] == 'bottom' for b in bottom))


if __name__ == '__main__':
    unittest.main()
