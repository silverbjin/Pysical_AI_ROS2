#!/usr/bin/env python3
import rclpy
from rclpy.node import Node

class BatteryNode(Node):
    def __init__(self):
        super().__init__('battery_monitor')
        self.battery_state = 100
        # 1.0초마다 실행
        self.timer = self.create_timer(1.0, self.timer_callback)
        self.get_logger().info("--- 배터리 모니터링 시작 ---")

    def timer_callback(self):
        # 1. 배터리 감소 로직 구현        
        if self.battery_state > 0:
            self.battery_state -= 10
        
        # 2. 0% 미만으로 떨어지지 않게 방어 코드 작성
        self.battery_state = max(0, self.battery_state)

        # 3. 상태에 따른 조건부 로깅 구현 (if-elif-else 사용)
        msg = f"현재 배터리 잔량: {self.battery_state}%"        
        if self.battery_state > 60:
            self.get_logger().info(f"[정상] {msg}")
        elif self.battery_state > 20:
            self.get_logger().warn(f"[주의] {msg}")
        else:
            self.get_logger().error(f"[위험] {msg} - 즉시 충전하세요!")

        # 4. 종료 처리 (선택 사항): 방전 시 타이머 중지
        if self.battery_state <= 0:
            self.get_logger().fatal("배터리 방전. 시스템을 정지합니다.")
            self.timer.cancel() # 타이머 취소

def main(args=None):
    rclpy.init(args=args)
    node = BatteryNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
