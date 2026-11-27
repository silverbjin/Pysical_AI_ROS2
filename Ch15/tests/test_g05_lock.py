import json,shutil,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'python'))
from g05_lock import verify
class LockTests(unittest.TestCase):
    def test_real_exact(self):
        self.assertEqual(verify(ROOT)['result'],'PASS')
    def test_drift_and_extra_repos(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'dependencies').mkdir()
            for name in ('quadruped_robot.repos','quadruped_robot.lock.repos','reuse.audit.json','native_local_use_approval.json'):
                shutil.copyfile(ROOT/'dependencies'/name,root/'dependencies'/name)
            p=root/'dependencies/quadruped_robot.lock.repos';original=p.read_text()
            for candidate in [original.replace('d010212c3f5c9e6e5542ada61cfdacc19b00f775','main'),original+'  nested:\n    type: git\n    url: https://example.invalid/repo\n    version: main\n']:
                p.write_text(candidate)
                with self.assertRaises(ValueError):verify(root)
if __name__=='__main__':unittest.main()
