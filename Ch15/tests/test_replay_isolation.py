import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'python'))
from replay_contract import validate,SAFE
class TestReplay(unittest.TestCase):
    def test_allow(self):self.assertEqual(validate(81,80,SAFE),list(SAFE))
    def test_reject(self):
        for domain,source,topics in [(80,80,SAFE),(81,80,SAFE+('/cmd_vel',)),(81,80,SAFE+('/clock',)),(81,80,('/navigate_to_pose/_action/send_goal',)),(0,80,SAFE)]:
            with self.assertRaises(ValueError):validate(domain,source,topics)
if __name__=='__main__':unittest.main()
