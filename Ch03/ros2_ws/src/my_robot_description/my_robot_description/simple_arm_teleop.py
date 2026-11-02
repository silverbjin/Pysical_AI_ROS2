#!/usr/bin/env python3
"""Keyboard teleoperation for the two-DOF Gazebo arm (Linux TTY only)."""

import select
import sys
import termios
import tty

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float64


HELP = """
--------------------------------------------------
My Robot Arm Teleoperation (interactive terminal)
--------------------------------------------------
W / S : Joint 1 (Shoulder) increase / decrease
A / D : Joint 2 (Elbow)    increase / decrease
Q     : Quit
--------------------------------------------------
"""
# 소프트웨어 제어 한계. URDF joint1 최대 ±3.14보다 의도적으로 보수적.
JOINT1_LIMIT = {"min": -1.57, "max": 1.57}
JOINT2_LIMIT = {"min": -1.57, "max": 1.57}
STEP_SIZE = 0.05


def constrain(value, minimum, maximum):
    """Clamp a command to the configured software limits."""
    return max(minimum, min(maximum, value))


class SimpleArmTeleop(Node):
    """Publish position targets through the ROS-Gazebo bridge."""

    def __init__(self):
        # Fail before entering raw mode or starting the control loop.
        if not sys.stdin.isatty():
            raise RuntimeError(
                "Keyboard teleop requires an interactive TTY; run in a terminal, "
                "not as a background launch process."
            )
        super().__init__("simple_arm_teleop")
        self.pub_j1 = self.create_publisher(Float64, "/joint1/cmd_pos", 10)
        self.pub_j2 = self.create_publisher(Float64, "/joint2/cmd_pos", 10)
        self.joint1_pos = 0.0
        self.joint2_pos = 0.0
        self.settings = termios.tcgetattr(sys.stdin.fileno())

    def get_key(self):
        """Read a single character, always restoring the terminal on exit."""
        fd = sys.stdin.fileno()
        try:
            tty.setraw(fd)
            readable, _, _ = select.select([sys.stdin], [], [], 0.1)
            return sys.stdin.read(1) if readable else ""
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, self.settings)

    def publish_commands(self):
        """Send both joints' target angles (radians) to the bridge."""
        for publisher, position in (
            (self.pub_j1, self.joint1_pos),
            (self.pub_j2, self.joint2_pos),
        ):
            message = Float64()
            message.data = position
            publisher.publish(message)


def main(args=None):
    rclpy.init(args=args)
    node = None
    try:
        node = SimpleArmTeleop()
        print(HELP, flush=True)
        node.publish_commands()
        while rclpy.ok():
            key = node.get_key().lower()
            if key in ("q", "\x03"):
                print("Quitting...")
                break
            if key not in ("w", "s", "a", "d"):
                # Do not flood the bridge with unchanged commands while idle.
                continue
            if key == "w":
                node.joint1_pos += STEP_SIZE
            elif key == "s":
                node.joint1_pos -= STEP_SIZE
            elif key == "a":
                node.joint2_pos += STEP_SIZE
            elif key == "d":
                node.joint2_pos -= STEP_SIZE

            node.joint1_pos = constrain(
                node.joint1_pos, JOINT1_LIMIT["min"], JOINT1_LIMIT["max"]
            )
            node.joint2_pos = constrain(
                node.joint2_pos, JOINT2_LIMIT["min"], JOINT2_LIMIT["max"]
            )
            node.publish_commands()
            print(
                f"Joint 1: {node.joint1_pos:+.2f} rad / "
                f"Joint 2: {node.joint2_pos:+.2f} rad",
                flush=True,
            )
    except KeyboardInterrupt:
        pass
    finally:
        if node is not None:
            # Double restoration is deliberate: cleanup after abnormal exit.
            termios.tcsetattr(
                sys.stdin.fileno(), termios.TCSADRAIN, node.settings
            )
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
