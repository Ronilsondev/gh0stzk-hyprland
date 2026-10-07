import contextlib
import importlib.util
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('resource_manifest', ROOT / 'tools/resource_manifest.py')
manifest = importlib.util.module_from_spec(spec)
spec.loader.exec_module(manifest)


class ResourceManifestTests(unittest.TestCase):
    def test_check_never_rewrites_manifest(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            asset = root / 'assets/example.txt'
            asset.parent.mkdir()
            asset.write_text('resource\n')
            with patch.object(manifest, 'ROOT', root), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(manifest.main([]), 0)
                recorded = (root / 'resources.json').read_bytes()
                self.assertEqual(manifest.main(['--check']), 0)
                self.assertEqual((root / 'resources.json').read_bytes(), recorded)
                asset.write_text('changed\n')
                self.assertEqual(manifest.main(['--check']), 1)
                self.assertEqual((root / 'resources.json').read_bytes(), recorded)
                asset.unlink()
                self.assertEqual(manifest.main(['--check']), 1)
                self.assertEqual((root / 'resources.json').read_bytes(), recorded)

    def test_invalid_or_missing_manifest_fails_without_writing(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            path = root / 'resources.json'
            with patch.object(manifest, 'ROOT', root), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(manifest.main(['--check']), 1)
                self.assertFalse(path.exists())
                path.write_text('invalid json\n')
                self.assertEqual(manifest.main(['--check']), 1)
                self.assertEqual(path.read_text(), 'invalid json\n')

    def test_unlicensed_fonts_are_excluded(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            licensed = root / 'assets/fonts/MapleMono-NF/font.ttf'
            licensed.parent.mkdir(parents=True)
            licensed.write_bytes(b'licensed')
            (licensed.parent.parent / 'private.ttf').write_bytes(b'private')
            self.assertEqual(list(manifest.inventory(root)), ['assets/fonts/MapleMono-NF/font.ttf'])
