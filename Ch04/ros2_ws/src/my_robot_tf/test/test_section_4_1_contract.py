"""4.1절 ROS 비의존 정적 계약 테스트."""

import unittest

from my_robot_tf.frame_contracts import is_unit_quaternion, validate_frame_tree


class TestFrameContracts(unittest.TestCase):
    def test_valid_forest_and_chain(self):
        self.assertTrue(validate_frame_tree([
            ("map", "odom"), ("odom", "base_link"),
            ("base_link", "camera_link"), ("world2", "sensor2"),
        ]))

    def test_duplicate_parent_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "two parents"):
            validate_frame_tree([("odom", "base_link"), ("map", "base_link")])

    def test_cycle_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "cycle"):
            validate_frame_tree([("a", "b"), ("b", "c"), ("c", "a")])

    def test_identity_quaternion(self):
        self.assertTrue(is_unit_quaternion(0, 0, 0, 1))
        self.assertFalse(is_unit_quaternion(0, 0, 0, 0))
        self.assertFalse(is_unit_quaternion(float("nan"), 0, 0, 1))

    def test_empty_and_self_frame_rejected(self):
        for edges in [[("", "base")], [("base", "base")]]:
            with self.assertRaises(ValueError):
                validate_frame_tree(edges)


if __name__ == "__main__":
    unittest.main()
