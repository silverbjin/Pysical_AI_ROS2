#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
import random  # 센서 값을 임의로 만들기 위한 라이브러리

def advance_sensor_state(angle, battery_level, noise, joint_limit=1.57):
    """가상 관절각과 배터리값을 결정론적으로 갱신한다 (실제 센서 아님)."""
    next_angle = max(-joint_limit, min(joint_limit, angle + noise))
    next_battery = max(0.0, min(100.0, battery_level - 0.1))
    return next_angle, next_battery


# Node 클래스를 상속받아 나만의 노드 클래스를 정의한다.
class JointSensorNode(Node):
    def __init__(self):
        # 부모 클래스(Node)의 생성자를 호출한다. 
        # 이때 전달하는 문자열 'joint_sensor'가 ROS 네트워크 상의 노드 이름이 된다.
        super().__init__('joint_sensor')
        
        # 노드의 상태 변수 초기화
        self.joint_angle = 0.0
        self.battery_level = 100.0
        
        # 1.0초마다 self.timer_callback 메서드를 실행하는 타이머를 생성한다.
        # 로봇 프로그래밍에서 '주기적인 실행'은 매우 중요하다.
        self.timer_period = 1.0  # seconds
        self.timer = self.create_timer(self.timer_period, self.timer_callback)
        
        # 노드가 시작되었음을 알리는 로그 출력
        self.get_logger().info('Joint Sensor Node has been started.')

    def timer_callback(self):
        """
        타이머에 의해 주기적으로 호출되는 콜백 함수.
        실제 센서 데이터를 읽거나 처리하는 로직이 여기에 위치한다.
        """
        # 가상의 센서 데이터 생성 (랜덤 값)
        noise = random.uniform(-0.1, 0.1)
        self.joint_angle, self.battery_level = advance_sensor_state(
            self.joint_angle, self.battery_level, noise
        )
        
        # 로그 출력: 단순 print()가 아닌 ROS 2 로거를 사용해야 시간 정보 등이 함께 기록된다.
        self.get_logger().info(
            f'Joint Angle: {self.joint_angle:.2f} rad, Battery: {self.battery_level:.1f}%'
        )

def main(args=None):
    # 1. rclpy 초기화: ROS 2와 통신하기 위한 준비 단계
    rclpy.init(args=args)
    
    # 2. 노드 인스턴스 생성
    node = JointSensorNode()
    
    try:
        # 3. 노드 실행 (Spin): 
        # 이 함수는 프로그램이 종료될 때까지 무한 루프를 돌며
        # 타이머나 콜백 이벤트를 감지하고 처리한다.
        rclpy.spin(node)
    except KeyboardInterrupt:
        # Ctrl+C 입력 시 조용히 종료
        pass
    finally:
        # 4. 종료 처리: 리소스 해제
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
