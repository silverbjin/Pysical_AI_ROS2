"""Regression for nested vendored wheel metadata; synthetic wheels only."""
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from zipfile import ZipFile
from g00_make_wheel_lock import make_lock


class WheelLockTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.wh = self.root / 'wheels'
        self.wh.mkdir()
        self.out = self.root / 'evidence'
        for name in ('torch', 'torchvision', 'numpy', 'onnx', 'onnxruntime', 'ultralytics'):
            self.wheel(name)

    def wheel(self, name, extra=None):
        path = self.wh / f'{name}-1.0-py3-none-any.whl'
        with ZipFile(path, 'w') as f:
            f.writestr(f'{name}-1.0.dist-info/METADATA', f'Name: {name}\nVersion: 1.0\n')
            if extra:
                f.writestr(extra, 'Name: vendored\nVersion: 9.0\n')
        return path

    def test_nested_metadata_ignored(self):
        path = self.wheel('setuptools', 'setuptools/_vendor/example-9.0.dist-info/METADATA')
        self.assertEqual(make_lock(self.wh, self.out), 7)
        rows = json.loads((self.out / 'wheel_manifest.json').read_text())
        self.assertNotIn('vendored', [x['name'] for x in rows])
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        self.assertIn(f'setuptools==1.0 --hash=sha256:{digest}', (self.out / 'cpu.candidate.lock.txt').read_text())

    def test_two_root_metadata_rejected(self):
        self.wheel('setuptools', 'other-9.0.dist-info/METADATA')
        with self.assertRaisesRegex(ValueError, 'Invalid root wheel metadata'):
            make_lock(self.wh, self.out)
        self.assertFalse((self.out / 'cpu.candidate.lock.txt').exists())

    def test_missing_required_rejected(self):
        next(self.wh.glob('onnx-*.whl')).unlink()
        with self.assertRaisesRegex(ValueError, 'Incomplete CPU wheelhouse'):
            make_lock(self.wh, self.out)
        self.assertFalse((self.out / 'cpu.candidate.lock.txt').exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
