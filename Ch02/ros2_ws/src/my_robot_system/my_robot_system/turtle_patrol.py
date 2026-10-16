#!/usr/bin/env python3
import rclpy
import math
import random
from rclpy.node import Node
from rclpy.action import ActionClient
from geometry_msgs.msg import Twist
from turtlesim.msg import Pose
from turtlesim.srv import SetPen
from turtlesim.action import RotateAbsolute

class TurtlePatrolNode(Node):
    def __init__(self):
        super().__init__('turtle_patrol_controller')
        
        # 1. 통신 객체 초기화
        # [Topic] 속도 명령 발행 (Publisher)
        self.cmd_vel_pub = self.create_publisher(Twist, '/turtle1/cmd_vel', 10)
        
        # [Topic] 현재 위치 수신 (Subscriber)
        self.pose_sub = self.create_subscription(Pose, '/turtle1/pose', self.pose_callback, 10)
        
        # [Service] 펜 색상 변경 (Client)
        self.pen_client = self.create_client(SetPen, '/turtle1/set_pen')
        
        # [Action] 절대 각도 회전 (Action Client)
        self.rotate_client = ActionClient(self, RotateAbsolute, '/turtle1/rotate_absolute')

        # 2. 로봇 상태 관리 변수
        self.current_pose = Pose()
        self.start_pose = Pose() # 이동 시작 지점 저장
        self.state = 'IDLE' # 상태: IDLE, FORWARD, ROTATING
        self.loop_count = 0 # 사각형 몇 바퀴 돌았나?

        self.get_logger().info("Turtle Patrol Controller Started!")
        
        # 서비스와 액션 서버가 뜰 때까지 대기
        self.wait_for_servers()
        
        # 첫 이동 시작
        self.start_forward_motion()

    def wait_for_servers(self):
        """필수 서비스와 액션 서버가 준비될 때까지 기다린다."""
        while not self.pen_client.wait_for_service(timeout_sec=1.0):
            self.get_logger().warn('Waiting for SetPen service...')
        
        self.get_logger().info('Waiting for RotateAbsolute action server...')
        self.rotate_client.wait_for_server()
        self.get_logger().info('All systems ready.')

    def pose_callback(self, msg):
        """
        [Topic Sub] 0.016초(60Hz)마다 호출되며 로봇의 두뇌 역할을 한다.
        현재 상태(self.state)에 따라 다음에 할 행동을 결정한다.
        """
        self.current_pose = msg

        # 상태 1: 직진 중일 때
        if self.state == 'FORWARD':
            # 이동 거리 계산 (피타고라스 정리)
            distance = math.sqrt(
                (msg.x - self.start_pose.x)**2 + (msg.y - self.start_pose.y)**2
            )
            
            if distance >= 2.0: # 2미터 이동 완료 시
                self.stop_robot()
                self.state = 'ROTATING' # 상태 변경
                self.change_pen_color() # 펜 색상 변경 요청 (Service)
                self.start_rotation()   # 회전 요청 (Action)
            else:
                self.publish_cmd_vel(2.0, 0.0) # 계속 직진

    def start_forward_motion(self):
        """직진을 시작하기 위한 초기화"""
        self.get_logger().info("Moving Forward...")
        self.state = 'FORWARD'
        self.start_pose = self.current_pose # 현재 위치를 시작점으로 기록

    def stop_robot(self):
        """로봇 정지"""
        self.publish_cmd_vel(0.0, 0.0)

    def publish_cmd_vel(self, linear_x, angular_z):
        msg = Twist()
        msg.linear.x = float(linear_x)
        msg.angular.z = float(angular_z)
        self.cmd_vel_pub.publish(msg)

    def change_pen_color(self):
        """[Service Call] 펜 색상을 랜덤하게 변경"""
        req = SetPen.Request()
        req.r = random.randint(0, 255)
        req.g = random.randint(0, 255)
        req.b = random.randint(0, 255)
        req.width = 3
        req.off = 0
        
        # 비동기 호출 (응답을 기다리지 않고 넘어감)
        future = self.pen_client.call_async(req)
        # 팁: 색상 변경은 매우 빠르므로 콜백 처리를 생략해도 무방하다.

    def start_rotation(self):
        """[Action Call] 90도 회전 명령 전송"""
        self.get_logger().info("Turning 90 degrees...")
        
        goal_msg = RotateAbsolute.Goal()
        # 현재 각도에서 90도(pi/2)를 더한다. 
        # Turtlesim의 각도는 -pi ~ pi 범위를 가지므로 정규화가 필요할 수 있으나,
        # RotateAbsolute 액션이 알아서 최단 경로로 처리해준다.
        target_theta = self.current_pose.theta + (math.pi / 2)
        goal_msg.theta = target_theta
        
        send_goal_future = self.rotate_client.send_goal_async(goal_msg)
        send_goal_future.add_done_callback(self.goal_response_callback)

    def goal_response_callback(self, future):
        """액션 서버가 목표를 수락했는지 확인"""
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().info('Rotation rejected :(')
            return

        # 결과(회전 완료)를 기다림
        get_result_future = goal_handle.get_result_async()
        get_result_future.add_done_callback(self.get_result_callback)

    def get_result_callback(self, future):
        """[Action Result] 회전이 완료되면 호출됨"""
        self.get_logger().info("Rotation Completed.")
        
        # 회전이 끝났으므로 다시 직진 상태로 복귀
        self.start_forward_motion()

def main(args=None):
    rclpy.init(args=args)
    node = TurtlePatrolNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
