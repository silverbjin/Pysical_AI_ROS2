"""No network or real weights: verify fail-fast asset boundaries."""
import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from fetch_models import acquire, resolve_entry, REVISION


class AssetTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.cache = Path(self.temp.name)
        self.payload = b'not a checkpoint; hash fixture only'
        self.entry = dict(id='yolov8n', source_revision=REVISION, license='AGPL-3.0',
                          source_url=f'https://huggingface.co/Ultralytics/YOLOv8/resolve/{REVISION}/yolov8n.pt',
                          sha256=hashlib.sha256(self.payload).hexdigest())

    def test_good_local_hash(self):
        path = self.cache / 'yolov8n.pt'
        path.write_bytes(self.payload)
        self.assertEqual(acquire(self.entry, self.cache), (path, self.entry['sha256']))

    def test_missing_and_ack_required(self):
        with self.assertRaises(FileNotFoundError):
            acquire(self.entry, self.cache)
        with self.assertRaises(PermissionError):
            acquire(self.entry, self.cache, fetch=True)

    def test_corruption_does_not_overwrite(self):
        path = self.cache / 'yolov8n.pt'
        path.write_bytes(b'corrupt')
        with self.assertRaisesRegex(ValueError, 'SHA256 mismatch'):
            acquire(self.entry, self.cache, fetch=True, acknowledged=True)
        self.assertEqual(path.read_bytes(), b'corrupt')

    def test_reject_symlink(self):
        original = self.cache / 'other'
        original.write_bytes(self.payload)
        (self.cache / 'yolov8n.pt').symlink_to(original)
        with self.assertRaises(ValueError):
            acquire(self.entry, self.cache)

    def test_manifest_fail_closed(self):
        self.assertEqual(resolve_entry({'models': [self.entry]}, 'yolov8n'), self.entry)
        for changed in (dict(self.entry, sha256=None), dict(self.entry, source_url='https://example.com/model.pt')):
            with self.assertRaises(ValueError):
                resolve_entry({'models': [changed]}, 'yolov8n')
        with self.assertRaises(ValueError):
            resolve_entry({'models': [self.entry]}, 'locomotion')


if __name__ == '__main__':
    unittest.main(verbosity=2)
