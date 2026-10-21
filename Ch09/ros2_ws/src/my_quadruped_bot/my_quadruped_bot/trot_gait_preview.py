"""Open-loop trot phase preview; not a validated walking controller.

This node owns all 12 joint command topics. Do not run it with stand_up
or single_leg_mover. It does not enforce base balance or ground contact.
"""
import math

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float64


LEGS = ("fr", "fl", "rr", "rl")
JOINT_TYPES = ("hip", "thigh", "calf")
NOMINAL = {"hip": 0.0, "thigh": -0.6, "calf": 1.2}
GROUP_A = frozenset(("fl", "rr"))  # diagonal pair
GROUP_B = frozenset(("fr", "rl"))  # opposite diagonal


class TrotGaitPreview(Node):
    def __init__(self):
        super().__init__("trot_gait_preview")
        self.declare_parameter("amplitude", 0.15)
        self.declare_parameter("frequency", 1.0)
        self.declare_parameter("ramp_seconds", 2.0)
        self.amplitude = float(self.get_parameter("amplitude").value)
        self.frequency = float(self.get_parameter("frequency").value)
        self.ramp_seconds = float(self.get_parameter("ramp_seconds").value)

        if not 0.0 <= self.amplitude <= 0.25:
            raise ValueError("amplitude must be in [0.0, 0.25] rad")
        if not 0.0 < self.frequency <= 2.0:
            raise ValueError("frequency must be in (0.0, 2.0] Hz")
        if not 0.1 <= self.ramp_seconds <= 30.0:
            raise ValueError("ramp_seconds must be in [0.1, 30.0] s")

        self.pubs = {}
        for leg in LEGS:
            for kind in JOINT_TYPES:
                name = f"{leg}_{kind}"
                topic = f"/model/my_quadruped/joint/{name}_joint/cmd_pos"
                self.pubs[name] = self.create_publisher(Float64, topic, 10)

        self._origin_ns = None
        self.timer = self.create_timer(0.01, self.timer_callback)
        self.get_logger().warn(
            "Trot phase preview only: no stability or true foot trajectories"
        )

    def timer_callback(self):
        now_ns = self.get_clock().now().nanoseconds
        if self._origin_ns is None or now_ns < self._origin_ns:
            self._origin_ns = now_ns

        elapsed = max(0.0, (now_ns - self._origin_ns) * 1.0e-9)
        ramp = min(1.0, elapsed / self.ramp_seconds)
        motion_time = max(0.0, elapsed - self.ramp_seconds)

        for name, publisher in self.pubs.items():
            leg, kind = name.split("_", 1)
            target = NOMINAL[kind] * ramp
            if kind == "thigh" and elapsed >= self.ramp_seconds:
                phase = 0.0 if leg in GROUP_A else math.pi
                target += self.amplitude * math.sin(
                    2.0 * math.pi * self.frequency * motion_time + phase
                )
            publisher.publish(Float64(data=float(target)))


def main(args=None):
    rclpy.init(args=args)
    node = None
    try:
        node = TrotGaitPreview()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if node is not None:
            node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
