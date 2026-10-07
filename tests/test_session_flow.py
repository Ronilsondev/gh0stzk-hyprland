"""Behavioral regressions. A stub compositor is not graphical validation."""
import contextlib
import io
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'lib'), str(ROOT / 'tools')]
import install
import runtime
import bootstrap
import visuals
from render import render, materialize
from session_env import configure


class SessionFlowTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('lua'), 'Lua absent; callback execution not verified')
    def test_autostart_executes_controller_with_session_argument(self):
        with tempfile.TemporaryDirectory(prefix='gh callback ') as tmp:
            home = Path(tmp)
            ctl = home / 'project with spaces/bin/gh0stzk'
            ctl.parent.mkdir(parents=True)
            ctl.write_text('#!/bin/sh\nprintf "%s\\n" "$@"\n')
            ctl.chmod(0o755)
            state = home / '.local/state/gh0stzk-hyprland'
            state.mkdir(parents=True)
            harness = home / 'run.lua'
            harness.write_text('''local proxy = {}
setmetatable(proxy, {__index=function() return proxy end, __call=function() return proxy end})
hl = setmetatable({}, {__index=function() return proxy end})
hl.on = function(event, cb) if event == 'hyprland.start' then cb() end end
hl.exec_cmd = function(cmd) print(cmd) end
dofile = function() return {} end
assert(loadfile(arg[1]))()
''')
            env = dict(os.environ, HOME=str(home), GH0STZK_ROOT=str(ctl.parents[1]), XDG_STATE_HOME=str(home / '.local/state'), XDG_CONFIG_HOME=str(home / '.config'))
            command = subprocess.check_output(['lua', str(harness), str(ROOT / 'config/hyprland.lua')], env=env, text=True).strip()
            subprocess.run(['/bin/sh','-c',command], env=env, check=True)
            self.assertEqual((state / 'session.log').read_text(), 'session\n')

    def test_wrapper_loads_installed_generation_and_explicit_config(self):
        with tempfile.TemporaryDirectory(prefix='gh wrapper ') as tmp:
            home = Path(tmp)
            with contextlib.redirect_stdout(io.StringIO()):
                install.main(['--home',tmp,'--apply','--allow-missing'])
            mockbin = home / 'mockbin'; mockbin.mkdir()
            log = home / 'calls.jsonl'
            script = '#!' + sys.executable + '\n' + '''import json, os, pathlib, sys
name=pathlib.Path(sys.argv[0]).name
with open(os.environ['TEST_CALLS'],'a') as f: f.write(json.dumps([name,*sys.argv[1:]])+'\\n')
if name=='Hyprland' and '--version' in sys.argv: print('Hyprland 0.56.2')
'''
            for name in ('Hyprland','start-hyprland','gsettings'):
                p=mockbin/name; p.write_text(script); p.chmod(0o755)
            env = {k:v for k,v in os.environ.items() if not k.startswith(('XDG_', 'GH0STZK_', 'HYPRLAND_'))}
            env.update(HOME=tmp, PATH=str(mockbin)+':'+os.environ['PATH'], TEST_CALLS=str(log), DISPLAY=':greeter')
            env.pop('WAYLAND_DISPLAY',None)
            wrapper = home / '.local/bin/gh0stzk-session'
            p=subprocess.run([str(wrapper),'--login'],env=env,capture_output=True,text=True)
            self.assertEqual(p.returncode,0,p.stderr)
            state=home/'.local/state/gh0stzk-hyprland'
            self.assertEqual(json.loads((state/'current/selection.json').read_text())['theme'],'emilia')
            calls=[json.loads(line) for line in log.read_text().splitlines()]
            expected=str(home/'.local/share/gh0stzk-hyprland/config/hyprland.lua')
            self.assertIn(['start-hyprland','--','--config',expected],calls)
            self.assertIn(['gsettings','set','org.gnome.desktop.interface','icon-theme','TokyoNight-SE'],calls)
            # TTY invocation inside an existing display must still refuse.
            p=subprocess.run([str(wrapper)],env=env,capture_output=True,text=True)
            self.assertNotEqual(p.returncode,0)

    def test_gtk_profile_is_private_and_preserves_app_preferences(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {}, clear=True):
            home=Path(tmp); original=home/'config'; original.mkdir()
            (original/'gtk-3.0').mkdir(); (original/'gtk-3.0/settings.ini').write_text('original')
            (original/'glib-2.0').mkdir(); (original/'kitty').mkdir()
            state=home/'state'; (state/'current').mkdir(parents=True)
            (state/'current/appearance.json').write_text(json.dumps({'gtk_cursor':'Qogirr'}))
            overlay=configure(state,original)
            self.assertFalse((overlay/'glib-2.0').is_symlink())
            self.assertEqual((overlay/'kitty').resolve(),original/'kitty')
            self.assertEqual((original/'gtk-3.0/settings.ini').read_text(),'original')
            self.assertEqual(os.environ['GSETTINGS_BACKEND'],'keyfile')
            self.assertEqual(configure(state,original),overlay)

    def test_terminal_receives_generated_kitty_config(self):
        with patch.object(runtime,'prefs',return_value={'terminal':['kitty']}), patch.object(runtime.subprocess,'Popen') as launch:
            runtime.app('terminal')
            self.assertEqual(launch.call_args.args[0],['kitty','--config',str(runtime.CURRENT/'kitty.conf'),'--class','gh0stzk-terminal'])

    def test_theme_resources_and_multiple_panels_are_materialized(self):
        with tempfile.TemporaryDirectory() as tmp:
            prefs=json.loads((ROOT/'config/preferences.json').read_text())
            names=['emilia']+sorted(p.parent.name for p in (ROOT/'themes').glob('*/theme.json') if p.parent.name!='emilia')
            for name in names:
                dest=Path(tmp)/name; render(name,dest,prefs); materialize(dest,dest)
                appearance=json.loads((dest/'appearance.json').read_text())
                self.assertIn(appearance['gtk_icons'],(dest/'gtk-3.0/settings.ini').read_text())
                self.assertIn(appearance['gtk_icons'],(dest/'rofi/style_1.rasi').read_text())
                self.assertTrue(list(dest.glob('wallpaper.*')))
                bars=json.loads((dest/'waybar.json').read_text())
                if name=='pamela': self.assertEqual(len(bars),6)
                if name=='z0mbi3': self.assertEqual(bars[0]['position'],'left')

    def test_missing_widgets_never_fall_back_to_menu(self):
        with patch.object(runtime,'prefs',return_value={'widgets':True}), patch.object(runtime,'run',side_effect=FileNotFoundError('eww')), patch.object(runtime,'choose') as menu:
            with self.assertRaises(FileNotFoundError): runtime.main(['widget','music'])
            menu.assert_not_called()

    def test_appearance_refuses_global_gsettings(self):
        with patch.dict(os.environ,{'GH0STZK_SESSION':'','GSETTINGS_BACKEND':'dconf'}), patch.object(runtime,'run') as run:
            with self.assertRaises(RuntimeError): runtime.apply_appearance()
            run.assert_not_called()

    def test_failed_eww_package_install_propagates(self):
        with patch.object(bootstrap.os,'getuid',return_value=1000), patch.object(bootstrap,'run',side_effect=subprocess.CalledProcessError(1,['pacman'])):
            with self.assertRaises(subprocess.CalledProcessError): bootstrap.install_eww(Path('/tmp/fixture.pkg.tar.zst'))

    def test_visual_failure_cannot_publish_generation(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(visuals,'check',side_effect=ValueError('missing resource')):
            home=Path(tmp); data=json.loads((ROOT/'visuals.json').read_text())
            dest=home/'.local/share/gh0stzk-hyprland-visuals'/data['revision']
            dest.mkdir(parents=True); (dest/'report.json').write_text('{}')
            with self.assertRaises(ValueError): visuals.install(home)
            self.assertFalse((dest.parent/'current').exists())

    def test_offline_native_rejection_restores_selected_generation(self):
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            state=Path(tmp)/'state'
            with patch.object(runtime,'STATE',state), patch.object(runtime,'CURRENT',state/'current'), patch.object(runtime,'CONFIG',Path(tmp)/'config'):
                with patch.object(runtime.shutil,'which',return_value=None):
                    runtime.apply_theme('emilia',offline=True)
                previous=(state/'current').resolve()
                with patch.object(runtime.shutil,'which',side_effect=lambda name: '/mock/Hyprland' if name=='Hyprland' else None), patch.object(runtime,'run',side_effect=subprocess.CalledProcessError(1,['Hyprland'])):
                    with self.assertRaises(subprocess.CalledProcessError): runtime.apply_theme('pamela',offline=True)
                self.assertEqual((state/'current').resolve(),previous)

    def test_managed_process_start_is_idempotent_and_stop_checks_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            state=Path(tmp)
            with patch.object(runtime,'STATE',state), patch.dict(os.environ,{'HYPRLAND_INSTANCE_SIGNATURE':'fixture'}):
                try:
                    runtime.start('fixture',['sleep','30'])
                    first=runtime.records()['fixture']
                    runtime.start('fixture',['sleep','30'])
                    self.assertEqual(runtime.records()['fixture'],first)
                    self.assertTrue(runtime.alive(first))
                finally:
                    runtime.stop('fixture')
                self.assertFalse(runtime.alive(first))


if __name__ == '__main__': unittest.main()
