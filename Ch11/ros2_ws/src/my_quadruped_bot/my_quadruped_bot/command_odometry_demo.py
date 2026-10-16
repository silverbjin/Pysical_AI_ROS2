"""Teaching-only command integration. Never used by localization.launch.py."""
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
import math

def euler_to_quaternion(roll, pitch, yaw):
    qx = math.sin(roll/2) * math.cos(pitch/2) * math.cos(yaw/2) - math.cos(roll/2) * math.sin(pitch/2) * math.sin(yaw/2)
    qy = math.cos(roll/2) * math.sin(pitch/2) * math.cos(yaw/2) + math.sin(roll/2) * math.cos(pitch/2) * math.sin(yaw/2)
    qz = math.cos(roll/2) * math.cos(pitch/2) * math.sin(yaw/2) - math.sin(roll/2) * math.sin(pitch/2) * math.cos(yaw/2)
    qw = math.cos(roll/2) * math.cos(pitch/2) * math.cos(yaw/2) + math.sin(roll/2) * math.sin(pitch/2) * math.sin(yaw/2)
    return [qx, qy, qz, qw]

class CommandOdometryDemo(Node):
    def __init__(self):
        super().__init__('command_odometry_demo')
        
        # 1. 구독 및 발행 설정
        self.create_subscription(Twist, '/demo/cmd_vel', self.cmd_vel_callback, 10)
        self.odom_pub = self.create_publisher(Odometry, '/demo/odom', 10)
        
        # 로봇 상태 변수
        self.x = 0.0
        self.y = 0.0
        self.th = 0.0
        
        self.vx = 0.0
        self.vy = 0.0
        self.vth = 0.0
        
        self.last_time = self.get_clock().now()
        self.last_cmd_time = self.get_clock().now() # [추가] 명령어 타임아웃 검사용
        
        # 주기적인 오도메트리 계산 타이머 (50Hz)
        # self.create_timer(0.02, self.update_odometry)
        # 기존 50Hz(0.02)에서 30Hz(약 0.033초) 주기로 데이터 발행 변경
        self.create_timer(0.033, self.update_odometry)
        self.get_logger().info("DEMO ONLY: integrating commands, not measuring robot motion")

    def cmd_vel_callback(self, msg):
        slip_factor = 0.9 
        self.vx = msg.linear.x * slip_factor
        self.vy = msg.linear.y * slip_factor
        self.vth = msg.angular.z * slip_factor
        self.last_cmd_time = self.get_clock().now() # 명령이 들어온 최신 시간 갱신

    def update_odometry(self):
        current_time = self.get_clock().now()
        dt = (current_time - self.last_time).nanoseconds / 1e9
        self.last_time = current_time
        
        # [방어 코드 추가] 0.2초 동안 새로운 cmd_vel이 없으면 로봇이 멈춘 것으로 간주
        if (current_time - self.last_cmd_time).nanoseconds / 1e9 > 0.2:
            self.vx = 0.0
            self.vy = 0.0
            self.vth = 0.0
        
        # 1. 위치 적분 (Dead Reckoning)
        delta_x = (self.vx * math.cos(self.th) - self.vy * math.sin(self.th)) * dt
        delta_y = (self.vx * math.sin(self.th) + self.vy * math.cos(self.th)) * dt
        delta_th = self.vth * dt
        
        self.x += delta_x
        self.y += delta_y
        self.th += delta_th
        
        # 2. 메시지 생성
        odom = Odometry()
        odom.header.stamp = current_time.to_msg()
        odom.header.frame_id = "odom"
        # odom.child_frame_id = "base_link" # 프로젝트 배치에 따라 필요 시 네임스페이스 확인 필요
        odom.child_frame_id = "base_footprint" # 프로젝트 배치에 따라 필요 시 네임스페이스 확인 필요
        
        # 위치 및 자세 주입
        odom.pose.pose.position.x = self.x
        odom.pose.pose.position.y = self.y
        odom.pose.pose.position.z = 0.0 
        
        q = euler_to_quaternion(0, 0, self.th)
        odom.pose.pose.orientation.x = q[0]
        odom.pose.pose.orientation.y = q[1]
        odom.pose.pose.orientation.z = q[2]
        odom.pose.pose.orientation.w = q[3]
        
        # 속도 주입
        odom.twist.twist.linear.x = self.vx
        odom.twist.twist.linear.y = self.vy
        odom.twist.twist.angular.z = self.vth
        
        # 3. 공분산(Covariance) 설정 - 6x6 대각 성분 인덱스 수정 [중요]
        # 계산하지 않는 변수(z, roll, pitch)는 불확실성을 극대화(1.0)하여 EKF가 IMU를 믿도록 유도
        pose_cov = [0.0 for _ in range(36)]
        pose_cov[0]  = 0.05  # x 오차 범위
        pose_cov[7]  = 0.05  # y 오차 범위
        pose_cov[14] = 1.0   # z (다리 오도메트리는 z축을 모르므로 불확실성 극대화)
        pose_cov[21] = 1.0   # roll (IMU에게 주도권을 넘김)
        pose_cov[28] = 1.0   # pitch (IMU에게 주도권을 넘김)
        pose_cov[35] = 0.05  # yaw 오차 범위
        
        # 속도 공분산도 동일한 메커니즘으로 설정
        twist_cov = [0.0 for _ in range(36)]
        twist_cov[0]  = 0.01 # 추정 속도 vx는 비교적 정확함
        twist_cov[7]  = 0.01 # vy 정확함
        twist_cov[14] = 1.0
        twist_cov[21] = 1.0
        twist_cov[28] = 1.0
        twist_cov[35] = 0.02
        
        odom.pose.covariance = pose_cov
        odom.twist.covariance = twist_cov
        
        self.odom_pub.publish(odom)
        
def main(args=None):
    rclpy.init(args=args)
    node = CommandOdometryDemo()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
