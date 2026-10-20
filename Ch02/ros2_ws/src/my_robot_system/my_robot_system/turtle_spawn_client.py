#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from turtlesim.srv import Spawn  # Turtlesim의 소환 서비스 타입

class TurtleSpawnClient(Node):
    def __init__(self):
        super().__init__('turtle_spawn_client')
        # 1. 클라이언트 생성: self.create_client(서비스타입, '서비스이름')
        self.client = self.create_client(Spawn, '/spawn')
        
        # 2. 서비스 서버가 준비될 때까지 대기
        # 서버가 켜져 있지 않은데 요청을 보내면 에러가 나거나 소실된다.
        # 생성자에서 영구 대기하지 않고, 실제 요청 시 제한 시간 내 탐색한다.
        
        self.req = Spawn.Request()

    def send_request(self):
        """
        서버에 요청을 보내고, 결과를 기다리는 함수
        """
        # 서버 탐색: 최대 5초. 서버가 없으면 무한 대기 대신 실패시킨다.
        for _ in range(5):
            if self.client.wait_for_service(timeout_sec=1.0):
                break
            self.get_logger().warn('Spawn service not available yet...')
        else:
            raise TimeoutError('Spawn service unavailable after 5 s')

        # 요청 데이터 채우기
        self.req.x = 5.0
        self.req.y = 5.0
        self.req.theta = 0.0
        self.req.name = 'robot_turtle' # 소환될 거북이 이름

        # 3. 비동기 요청 전송 (call_async)
        # 요청을 보내고 'Future' 객체를 즉시 반환받는다.
        # Future는 "나중에 결과가 오면 교환해줄게"라는 대기표와 같다.
        self.future = self.client.call_async(self.req)
        
        # ROS 2 시스템이 Future가 완료될 때까지(응답이 올 때까지) spin 한다.
        rclpy.spin_until_future_complete(self, self.future, timeout_sec=5.0)
        if not self.future.done():
            raise TimeoutError('Spawn service response timed out after 5 s')
        if self.future.exception() is not None:
            raise self.future.exception()
        return self.future.result()

def main(args=None):
    rclpy.init(args=args)
    
    # 노드 생성
    client_node = TurtleSpawnClient()
    
    # 요청 전송 및 결과 수신
    try:
        response = client_node.send_request()
        client_node.get_logger().info(
            f'Success! Spawning Turtle: {response.name}'
        )
    except Exception as e:
        client_node.get_logger().error(f'Service call failed: {e}')
        # console_scripts는 sys.exit(main())을 사용하므로 실패를 성공으로 숨기지 않는다.
        raise SystemExit(1)
    
    finally:
        # 정상·타임아웃·중복 소환 실패 모두 자원을 회수한다.
        client_node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()

if __name__ == '__main__':
    main()
