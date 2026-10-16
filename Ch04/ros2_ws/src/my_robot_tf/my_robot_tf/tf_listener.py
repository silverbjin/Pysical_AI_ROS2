import math
import rclpy
from rclpy.node import Node
from rclpy.duration import Duration

# TF2 Listener 관련 모듈 임포트 (필수)
from tf2_ros import TransformException
from tf2_ros.buffer import Buffer
from tf2_ros.transform_listener import TransformListener

class FrameListener(Node):
    def __init__(self):
        super().__init__('tf_listener_node')

        # 1. 버퍼와 리스너 생성
        # 버퍼를 먼저 만들고, 리스너에게 이 버퍼를 쓰라고 알려준다.
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)

        # 2. 타겟과 소스 프레임 정의
        self.target_frame = 'world'      # 기준 (경찰 로봇이 world 원점에 있다고 가정)
        self.source_frame = 'turtle_frame' # 추적 대상

        # 3. 주기적으로 조회하기 위한 타이머 (1.0초 마다)
        self.timer = self.create_timer(1.0, self.on_timer)
        
        self.get_logger().info("TF Listener Started. Watching turtle_frame...")

    def on_timer(self):
        # TF 조회는 실패할 확률이 높으므로 반드시 try-except 처리를 해야 한다.
        try:
            # 핵심 함수: lookup_transform(기준프레임, 타겟프레임, 시간)
            # Time()은 '가장 최근에 가능한 시간'의 데이터를 달라는 뜻이다.
            # rclpy.time.Time()은 0초(Zero time)를 의미하며, TF에서는 'Latest'로 통한다.
            t = self.tf_buffer.lookup_transform(
                self.target_frame,
                self.source_frame,
                rclpy.time.Time()
            )
        except TransformException as ex:
            # 데이터가 아직 안 들어왔거나, 연결 트리가 끊어져 있으면 예외 발생
            self.get_logger().info(f'Could not transform {self.target_frame} to {self.source_frame}: {ex}')
            return

        # 조회 성공 시 데이터 처리
        x = t.transform.translation.x
        y = t.transform.translation.y
        z = t.transform.translation.z
        
        # 거리 계산 (유클리드 거리)
        distance = math.sqrt(x**2 + y**2)
        
        self.get_logger().info(f'Detected: Turtle is at ({x:.2f}, {y:.2f}), Distance: {distance:.2f}m')

def main():
    rclpy.init()
    node = FrameListener()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
