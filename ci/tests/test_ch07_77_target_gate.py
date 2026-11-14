"""No-ROS G01 RED/GREEN boundary. Do not test old already accepted 7.2–7.6."""
import sys
from pathlib import Path
import unittest

PKG = Path(__file__).resolve().parents[1] / "Ch07/ros2_ws/src/vision_basics"
sys.path.insert(0, str(PKG))
from vision_basics.mission_target_gate import TargetGate, candidate_pregrasp


class AdmissionContract(unittest.TestCase):
    def gate(self):
        return TargetGate()

    def valid(self, gate, now=100.0):
        gate.set_valid(True, now)

    def offer(self, gate, stamp=100.0, xyz=(0.6, 0.1, 0.5),
              frame="base_link", now=100.0):
        return gate.accept(xyz=xyz, stamp_s=stamp, frame_id=frame, now_s=now)

    def test_first_sample_is_not_enough_and_stable_second_accepts_once(self):
        gate = self.gate()
        self.valid(gate)
        self.assertIsNone(self.offer(gate))
        self.assertEqual(gate.last_reason, "FIRST_STABLE_SAMPLE_PENDING")
        result = self.offer(gate, stamp=100.1, xyz=(0.605, 0.105, 0.51), now=100.12)
        self.assertIsNotNone(result)
        self.assertEqual(gate.last_reason, "READY_FOR_PLAN_ONLY")
        self.assertIsNone(self.offer(gate, stamp=100.2, now=100.2))
        self.assertEqual(gate.last_reason, "ONE_SHOT_ALREADY_ACCEPTED")
        self.assertEqual(gate.goal_count, 0)

    def test_no_detection_and_invalid_resets_pending(self):
        gate = self.gate()
        self.assertIsNone(self.offer(gate))
        self.valid(gate)
        self.assertIsNone(self.offer(gate))
        gate.set_valid(False, 100.03)
        self.assertIsNone(self.offer(gate, stamp=100.1, now=100.1))
        self.valid(gate, 100.11)
        self.assertIsNone(self.offer(gate, stamp=100.15, now=100.16))
        self.assertIsNotNone(self.offer(gate, stamp=100.18, now=100.19))

    def test_invalid_values_all_fail_closed(self):
        vectors = [
            ((float("nan"), 0, 0.5), 100, "base_link", 100),
            ((float("inf"), 0, 0.5), 100, "base_link", 100),
            ((0.5, float("-inf"), 0.5), 100, "base_link", 100),
            ((0.6, 0.1, 0.5), 99.0, "base_link", 100),
            ((0.6, 0.1, 0.5), 100.3, "base_link", 100),
            ((0.6, 0.1, 0.5), 100, "camera_optical_frame", 100),
            ((3.0, 0.0, 0.5), 100, "base_link", 100),
            ((0.6, 0.1, -0.4), 100, "base_link", 100),
            ((0.6, 0.1, 0.5), 0, "base_link", 100),
        ]
        for xyz, stamp, frame, now in vectors:
            with self.subTest(xyz=xyz, stamp=stamp, frame=frame):
                gate = self.gate()
                self.valid(gate)
                self.assertIsNone(self.offer(gate, stamp, xyz, frame, now))
                self.assertIsNone(gate.accepted)
                self.assertEqual(gate.goal_count, 0)

    def test_time_and_motion_consistency(self):
        for second_stamp, xyz in [(100.6,(0.6,0.1,0.5)),
                                  (100.2,(0.9,0.1,0.5)),
                                  (100.0,(0.6,0.1,0.5))]:
            gate = self.gate()
            self.valid(gate)
            self.assertIsNone(self.offer(gate))
            self.assertIsNone(self.offer(gate, second_stamp, xyz,
                                         now=100.25 if second_stamp<=100.25 else 100.6))
            self.assertEqual(gate.goal_count,0)

    def test_pregrasp_is_not_hardcoded(self):
        a, b = self.gate(), self.gate()
        self.valid(a)
        self.valid(b)
        self.offer(a, 100, (0.6,0.1,0.5))
        ta=self.offer(a,100.1,(0.6,0.1,0.5),now=100.15)
        self.offer(b,100,(0.8,-0.1,0.7))
        tb=self.offer(b,100.1,(0.8,-0.1,0.7),now=100.15)
        self.assertEqual(candidate_pregrasp(ta),(0.6,0.1,0.62))
        self.assertNotEqual(candidate_pregrasp(ta),candidate_pregrasp(tb))
        self.assertEqual(a.goal_count+b.goal_count,0)

    def test_validity_timeout_never_generates_goal(self):
        g=self.gate()
        self.valid(g,now=100)
        self.assertIsNone(self.offer(g,stamp=100.58,now=100.6))
        self.assertEqual(g.last_reason,"EXPIRED_VALIDITY")
        self.assertEqual(g.goal_count,0)


if __name__=="__main__":
    unittest.main()
