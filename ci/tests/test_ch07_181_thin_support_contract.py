#!/usr/bin/env python3
"""#181 pure-Python TDD: support remains physically load bearing and clears observed wrist."""
import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ch07_77_g04b_physics_fixture import validate_thin_physical_support

class ThinSupportContractTest(unittest.TestCase):
    def test_support_top_unchanged_actual_rod_bottom(self):
        c=validate_thin_physical_support(.006,.006,1.897,1.94,.08,1.8703095)
        self.assertAlmostEqual(c["support_top_world_z_m"],1.90)
        self.assertAlmostEqual(c["support_bottom_world_z_m"],1.894)
        self.assertGreater(c["prior_wrist_contact_clearance_z_m"],.02)
    def test_old_tall_post_cannot_get_a_new_pass(self):
        with self.assertRaisesRegex(ValueError,"NONPHYSICAL"):
            validate_thin_physical_support(.006,.20,1.80,1.94,.08,1.8703095)
    def test_floating_rod_above_shelf_not_accepted(self):
        with self.assertRaisesRegex(ValueError,"NOT_PHYSICALLY_SUPPORTED"):
            validate_thin_physical_support(.006,.006,1.88,1.94,.08,1.8703095)
    def test_support_still_in_measured_wrist_zone_rejected(self):
        with self.assertRaisesRegex(ValueError,"WRIST_INTERFERENCE_NOT_CLEARED"):
            validate_thin_physical_support(.006,.016,1.892,1.94,.08,1.8703095)

if __name__=="__main__":unittest.main()
