import rclpy
from rclpy.node import Node
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
from builtin_interfaces.msg import Duration

class SimpleTrajectoryPublisher(Node):
    def __init__(self):
        super().__init__('simple_trajectory_publisher')
        
        # 1. 퍼블리셔 생성
        # 토픽 이름: /arm_controller/joint_trajectory (ros2_controllers.yaml에서 설정한 이름)
        # 큐 사이즈: 10
        self.publisher_ = self.create_publisher(
            JointTrajectory, 
            '/arm_controller/joint_trajectory', 
            10
        )
        
        # 2. 타이머 설정 (2초마다 콜백 실행)
        timer_period = 2.0 
        self.timer = self.create_timer(timer_period, self.timer_callback)
        
        # 로봇의 상태 (True: 굽힘, False: 폄)
        self.moving_forward = True
        
        # 3. 제어할 관절 이름 정의 
        # 주의: URDF 파일의 joint name과 100% 일치해야 함!
        self.joint_names = ['joint1', 'joint2', 'joint3', 'joint4']
        
        self.get_logger().info('Simple Trajectory Publisher Started!')

    def timer_callback(self):
        # 메시지 객체 생성
        msg = JointTrajectory()
        
        # 관절 이름 채우기
        msg.joint_names = self.joint_names
        
        # 경로 포인트 생성
        point = JointTrajectoryPoint()
        
        if self.moving_forward:
            # 목표 1: 팔을 앞으로 굽히는 자세 (단위: 라디안)
            # joint1=0.0, joint2=0.5, joint3=0.5, joint4=1.0
            point.positions = [0.0, 0.5, 0.5, 1.0]
            self.get_logger().info('Goal: Bending Position')
        else:
            # 목표 2: 팔을 원점으로 펴는 자세 (Home)
            point.positions = [0.0, 0.0, 0.0, 0.0]
            self.get_logger().info('Goal: Home Position')
            
        # 중요: 동작 수행 시간 설정 (이동 속도 결정)
        # 여기서는 1초 동안 부드럽게 이동하도록 설정
        point.time_from_start = Duration(sec=1, nanosec=0)
        
        # 포인트 추가 (리스트 형태)
        msg.points.append(point)
        
        # 메시지 발행
        self.publisher_.publish(msg)
        
        # 다음 동작을 위해 상태 토글
        self.moving_forward = not self.moving_forward

def main(args=None):
    rclpy.init(args=args)
    node = SimpleTrajectoryPublisher()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
