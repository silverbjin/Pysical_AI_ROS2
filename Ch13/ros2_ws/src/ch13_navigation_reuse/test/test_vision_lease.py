from pathlib import Path
import sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ch13_navigation_reuse.vision_lease import VisionLease
class VisionLeaseTests(unittest.TestCase):
 def test_loss_latches_and_new_frame_does_not_resume(self):
  v=VisionLease();v.observe(2_000_000_000,1.,'gid');self.assertTrue(v.enable(2_000_000_000,1.));self.assertFalse(v.check(2_100_000_000,1.31));v.observe(2_200_000_000,1.32,'gid');self.assertFalse(v.check(2_200_000_000,1.33))
 def test_duplicate_frame_does_not_refresh_capture_wall(self):
  v=VisionLease();v.observe(2_000_000_000,1.,'gid');v.observe(2_000_000_000,1.29,'gid');self.assertFalse(v.enable(2_100_000_000,1.31))
