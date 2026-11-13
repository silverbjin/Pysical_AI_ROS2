import rclpy
from rclpy.node import Node
from rclpy.executors import ExternalShutdownException
from sensor_msgs.msg import JointState
import time
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
from builtin_interfaces.msg import Duration
import math

class WaveHelloNode(Node):
    def __init__(self):
        super().__init__('wave_hello_node')
        
        # 1. 퍼블리셔 설정
        # 큐 사이즈는 10이면 충분하다. 실시간 제어에서는 최신 명령이 중요하기 때문.
        self.publisher_ = self.create_publisher(
            JointTrajectory, 
            '/arm_controller/joint_trajectory', 
            10
        )
        
        # 2. 제어 주기 설정 (매우 중요)
        # 50Hz (0.02초) 주기로 명령을 보낸다. 
        # 너무 느리면 로봇이 뚝뚝 끊겨 보이고, 너무 빠르면 통신 부하가 걸린다.
        self.timer_period = 0.02  # seconds
        self.timer = self.create_timer(self.timer_period, self.timer_callback)
        
        # 3. 로봇 관절 설정 (URDF와 일치해야 함)
        self.joint_names = ['joint1', 'joint2', 'joint3', 'joint4']
        # §5.6: initial joint2/joint3 posture must NOT jump in 20 ms.
        # Use a single 3s controller trajectory and wait for measured feedback
        # before the textbook's original 50Hz sinusoidal commands begin.
        self._pose = [0.0, -0.5, 0.8, 0.0]
        self._measured = None
        self._measured_seen_wall = None
        self._mode = 'WAIT_FOR_JOINT_STATES'
        self._ramp_sent_ns = None
        self._wave_started_ns = None
        self.create_subscription(JointState, '/joint_states', self.on_joint_state, 10)

        
        # 4. 모션 파라미터 설정 (튜닝 포인트)
        # Joint 1: 허리 (천천히 크게 움직임)
        self.j1_amp = 0.3      # 진폭: +/- 0.3 라디안 (약 17도)
        self.j1_freq = 1.0     # 주파수: 1.0 rad/s (약 6초에 1회 왕복)
        
        # Joint 4: 손목 (빠르게 작게 움직임 - 안녕!)
        self.j4_amp = 0.5      # 진폭: +/- 0.5 라디안 (약 28도)
        self.j4_freq = 4.0     # 주파수: 4.0 rad/s (1.5초에 1회 왕복)
        self.j4_offset = 0.0   # 중심점: 0도

        # 시작 시간 기록
        self.start_time = None  # Begin sine phase only after measured ramp completion.
        
        self.get_logger().info('Hello Robot Node Started! Waving is beginning...')

    def on_joint_state(self, msg):
        if not all(name in msg.name for name in self.joint_names):
            return
        positions = [float(msg.position[msg.name.index(j)])
                     for j in self.joint_names]
        if not all(math.isfinite(p) for p in positions):
            return
        self._measured = positions
        self._measured_seen_wall = time.monotonic()

    def timer_callback(self):
        # The original 20 ms, four-joint pose jump would request excessive
        # initial velocities. Preserve original sine amplitudes and rates but
        # transition to the start pose with one 3s controller trajectory.
        now_ns = self.get_clock().now().nanoseconds
        fresh = self._measured is not None and (
            self._measured_seen_wall is not None
            and time.monotonic() - self._measured_seen_wall <= 1.0
        )
        if self._mode == 'BLOCKED':
            return
        if self._mode == 'WAIT_FOR_JOINT_STATES':
            if not fresh or now_ns <= 0:
                return
            msg = JointTrajectory()
            msg.joint_names = self.joint_names
            point = JointTrajectoryPoint()
            point.positions = list(self._pose)
            point.time_from_start = Duration(sec=3, nanosec=0)
            msg.points.append(point)
            self.publisher_.publish(msg)
            self._ramp_sent_ns = now_ns
            self._mode = 'RAMP_TO_START'
            self.get_logger().info('CH05_56_START_RAMP_3S_SENT')
            return
        if self._mode == 'RAMP_TO_START':
            if not fresh:
                return
            elapsed = (now_ns - self._ramp_sent_ns) / 1e9
            if elapsed < 3.0:
                return
            errors = [abs(now - goal) for now, goal in zip(self._measured, self._pose)]
            if max(errors) <= 0.15:
                self._mode = 'WAVE'
                self._wave_started_ns = now_ns
                self.start_time = now_ns / 1e9
                self.get_logger().info(
                    f'CH05_56_START_POSE_MEASURED_WITHIN_TOLERANCE errors={errors}'
                )
            elif elapsed > 6.0:
                self.get_logger().error(
                    f'CH05_56_START_POSE_BLOCKED errors={errors}; '
                    'no sinusoidal commands will be published'
                )
                self._mode = 'BLOCKED'
            return
        # WAVE mode: original textbook signal, only after observed startup.
        current_time = now_ns / 1e9
        elapsed_time = current_time - self.start_time
        
        # --- [핵심 로직: 사인파 생성] ---
        
        # 1. 허리 관절 (Joint 1): 천천히 좌우로
        # sin(t) 함수를 이용해 부드러운 왕복 운동 생성
        pos_j1 = self.j1_amp * math.sin(self.j1_freq * elapsed_time)
        
        # 2. 어깨/팔꿈치 (Joint 2, 3): 고정된 자세 유지
        # 팔을 약간 들어 올려 인사하기 좋은 자세를 만든다.
        pos_j2 = -0.5  # 어깨를 뒤로 약간 젖힘
        pos_j3 = 0.8   # 팔꿈치를 굽힘
        
        # 3. 손목 관절 (Joint 4): 빠르게 흔들기
        # cos를 쓰든 sin을 쓰든 상관없으나, 위상차를 주기 위해 여기선 sin 사용
        pos_j4 = self.j4_amp * math.sin(self.j4_freq * elapsed_time) + self.j4_offset
        
        # --- [메시지 패킹] ---
        
        msg = JointTrajectory()
        msg.joint_names = self.joint_names
        
        point = JointTrajectoryPoint()
        point.positions = [pos_j1, pos_j2, pos_j3, pos_j4]
        
        # 중요: 명령 도달 시간 지정
        # 우리는 0.02초마다 명령을 보내므로, 로봇이 이 위치까지 도달하는 시간도
        # 그와 비슷하거나 약간 길게 잡아주어야 부드럽게 이어진다.
        point.time_from_start = Duration(sec=0, nanosec=int(self.timer_period * 1e9))
        
        msg.points.append(point)
        self.publisher_.publish(msg)

def main(args=None):
    rclpy.init(args=args)
    node = WaveHelloNode()
    
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        # 안전하게 종료: 노드가 꺼질 때 로봇을 멈추고 싶다면 여기서 0도 명령을 보낼 수도 있다.
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()

if __name__ == '__main__':
    main()
