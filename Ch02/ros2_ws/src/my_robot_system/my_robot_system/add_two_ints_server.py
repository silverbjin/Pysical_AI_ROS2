#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from example_interfaces.srv import AddTwoInts  # ROS 2 예제 서비스 타입

class AddTwoIntsServer(Node):
    def __init__(self):
        super().__init__('add_two_ints_server')
        
        # 1. 서비스 서버 생성
        # self.create_service(서비스타입, '서비스이름', 콜백함수)
        self.srv = self.create_service(
            AddTwoInts, 
            'add_two_ints', 
            self.add_two_ints_callback
        )
        
        self.get_logger().info('Add Two Ints Server Ready.')

    def add_two_ints_callback(self, request, response):
        """
        요청이 들어올 때마다 실행되는 콜백 함수
        request: 클라이언트가 보낸 데이터 (a, b)
        response: 서버가 채워서 돌려줄 데이터 (sum)
        """
        # 2. 비즈니스 로직 수행 (여기서는 덧셈)
        response.sum = request.a + request.b
        
        self.get_logger().info(f'Incoming request: a={request.a}, b={request.b}')
        self.get_logger().info(f'Sending response: sum={response.sum}')
        
        # 3. 결과 반환
        return response

def main(args=None):
    rclpy.init(args=args)
    node = AddTwoIntsServer()
    
    try:
        # 서버는 요청이 올 때까지 계속 대기해야 하므로 일반 spin을 사용한다.
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
