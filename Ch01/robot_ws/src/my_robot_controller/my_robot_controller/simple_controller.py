#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import rclpy                        # ROS 2의 Python 클라이언트 라이브러리
from rclpy.node import Node         # ROS 2 노드 기능을 가진 부모 클래스

class SimpleController(Node):
    """
    로봇 제어를 위한 기본 노드 클래스입니다.
    rclpy.node.Node를 상속받아 ROS 2의 모든 기능을 사용할 수 있습니다.
    """

    def __init__(self):
        # 1. 부모 클래스(Node)의 생성자 호출
        # 'my_robot_node'는 ROS 2 네트워크 상에서 보일 이 노드의 이름입니다.
        # 파일명과 달라도 상관없지만, 유니크해야 합니다.
        super().__init__('my_robot_node') 

        # 2. 로거(Logger)를 이용한 초기화 메시지 출력
        # print() 대신 self.get_logger().info()를 사용하는 습관을 들여야 합니다.
        # 시간 정보와 노드 이름이 함께 출력되어 디버깅에 유리합니다.
        self.get_logger().info("Simple Controller 노드가 시작되었습니다!")

        # 3. 타이머 설정 (이벤트 스케줄링)
        # 1.0초마다 self.timer_callback 함수를 자동으로 실행하도록 예약합니다.
        self.timer_period = 1.0  # 초 단위
        self.timer = self.create_timer(self.timer_period, self.timer_callback)
        
        # 내부 상태 변수 (카운터)
        self.counter = 0

    def timer_callback(self):
        """
        정해진 주기마다 실행되는 콜백 함수입니다.
        로봇의 센서 값을 읽거나 모터 명령을 내리는 메인 로직이 이곳에 들어갑니다.
        """
        self.counter += 1
        msg = f"로봇 생존 신호 송신 중... (Heartbeat: {self.counter})"
        self.get_logger().info(msg)

def main(args=None):
    """
    프로그램의 진입점(Entry Point)입니다.
    """
    # 1. ROS 2 통신 초기화 (DDS 미들웨어 연결 등)
    rclpy.init(args=args)

    # 2. 노드 객체 생성
    node = SimpleController()

    try:
        # 3. 노드 실행 유지 (Spin)
        # 이 함수가 호출되면 노드는 종료되지 않고, 들어오는 이벤트(타이머, 토픽 등)를
        # 무한히 기다리며 처리하는 상태가 됩니다.
        rclpy.spin(node)
    
    except KeyboardInterrupt:
        # Ctrl+C가 입력되면 조용히 종료
        node.get_logger().info("종료 신호를 받았습니다.")
    
    finally:
        # 4. 자원 해제 및 종료
        node.destroy_node() # 노드 소멸
        rclpy.shutdown()    # ROS 2 통신 종료

if __name__ == '__main__':
    main()
