import hashlib
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile
from verify_openvino_wheels import verify

class WheelTests(unittest.TestCase):
    def test_optional_profile_and_negative_edges(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);wh=root/'wheels';wh.mkdir();lock=root/'lock'
            rows=[]
            for name,version in [('openvino','2025.1.0'),('openvino_telemetry','2025.2.0')]:
                path=wh/(name+'-'+version+'.whl')
                with ZipFile(path,'w') as z:
                    z.writestr(name+'-'+version+'.dist-info/METADATA',f'Name: {name}\nVersion: {version}\n')
                rows.append(f'{name}=={version} --hash=sha256:'+hashlib.sha256(path.read_bytes()).hexdigest())
            lock.write_text('\n'.join(rows)+'\n')
            self.assertEqual(verify(lock,wh)['status'],'PASS')
            with self.assertRaises(ValueError):
                lock.write_text(rows[0]+'\n');verify(lock,wh)
            lock.write_text('\n'.join(rows)+'\n')
            with self.assertRaises(ValueError):
                lock.write_text('\n'.join(rows)+'\n'+rows[0]+'\n');verify(lock,wh)
            lock.write_text('\n'.join(rows)+'\n')
            path.unlink()
            with self.assertRaises(ValueError):verify(lock,wh)
if __name__=='__main__':unittest.main(verbosity=2)
