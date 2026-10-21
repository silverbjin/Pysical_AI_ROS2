"""4.4절: 대상·원본 프레임을 파라미터로 고를 수 있는 TF listener."""

import math

import rclpy
from rclpy.node import Node
from tf2_ros import TransformException
from tf2_ros.buffer import Buffer
from tf2_ros.transform_listener import TransformListener


class FrameListener(Node):
    def __init__(self):
        super().__init__("tf_listener_node")
        self.declare_parameter("target_frame", "world")
        self.declare_parameter("source_frame", "turtle_frame")
        self.target_frame = self.get_parameter("target_frame").value
        self.source_frame = self.get_parameter("source_frame").value
        if (not isinstance(self.target_frame, str)
                or not isinstance(self.source_frame, str)
                or not self.target_frame.strip()
                or not self.source_frame.strip()
                or self.target_frame == self.source_frame):
            raise ValueError("target_frame and source_frame must be distinct nonempty strings")

        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)
        self.timer = self.create_timer(1.0, self.on_timer)
        self.get_logger().info(
            f"TF listener started: {self.target_frame} <- {self.source_frame}"
        )

    def on_timer(self):
        try:
            transform = self.tf_buffer.lookup_transform(
                self.target_frame, self.source_frame, rclpy.time.Time()
            )
        except TransformException as exc:
            self.get_logger().warn(
                f"Could not transform {self.target_frame} <- "
                f"{self.source_frame}: {exc}"
            )
            return

        x = transform.transform.translation.x
        y = transform.transform.translation.y
        distance_xy = math.hypot(x, y)
        self.get_logger().info(
            f"Detected: Turtle is at ({x:.2f}, {y:.2f}), "
            f"Distance: {distance_xy:.2f}m"
        )


def main():
    rclpy.init()
    node = None
    try:
        node = FrameListener()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if node is not None:
            node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
