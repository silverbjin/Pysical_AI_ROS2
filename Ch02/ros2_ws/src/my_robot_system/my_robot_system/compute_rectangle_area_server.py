#!/usr/bin/env python3
"""ComputeRectangleArea.srv를 실제로 제공하는 교육용 서비스 서버."""
import rclpy
from rclpy.node import Node
from my_robot_interfaces.srv import ComputeRectangleArea


def compute_area(length, width):
    """정의된 float64 두 값을 곱한다; 물리 치수의 유효성 판단은 별개."""
    return float(length) * float(width)


class RectangleAreaServer(Node):
    def __init__(self):
        super().__init__('compute_rectangle_area_server')
        self.srv = self.create_service(
            ComputeRectangleArea,
            'compute_rectangle_area',
            self.compute_callback,
        )
        self.get_logger().info('ComputeRectangleArea service ready.')

    def compute_callback(self, request, response):
        response.area = compute_area(request.length, request.width)
        return response


def main(args=None):
    rclpy.init(args=args)
    node = RectangleAreaServer()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
