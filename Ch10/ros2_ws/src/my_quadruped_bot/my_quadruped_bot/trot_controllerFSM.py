#!/usr/bin/env python3
import rclpy
import numpy as np
from rclpy.node import Node
# from geometry_msgs.msg import Twist
from std_msgs.msg import Float64
from enum import Enum

# 패키지 구조 명세에 맞춘 임포트
from my_quadruped_bot.gait_planner import GaitPlanner
from my_quadruped_bot.generalized_gait_planner import GeneralizedGaitPlanner
from my_quadruped_bot.trajectory_generator import TrajectoryGenerator
from my_quadruped_bot.inverse_kinematics import InverseKinematics

# Odometry 발행, TF 브로드캐스팅, 동적 파라미터 재구성, 속도 명령 LPF
import math
from rclpy.parameter import Parameter
from rcl_interfaces.msg import SetParametersResult
from geometry_msgs.msg import Twist, TransformStamped, Quaternion
from nav_msgs.msg import Odometry
from sensor_msgs.msg import JointState
from tf2_ros import TransformBroadcaster
from my_robot_interfaces.srv import SetGait

def euler_to_quaternion(roll, pitch, yaw) -> Quaternion:
    """Euler 각도를 Quaternion 메시지로 변환하는 헬퍼 함수"""
    qx = np.sin(roll/2) * np.cos(pitch/2) * np.cos(yaw/2) - np.cos(roll/2) * np.sin(pitch/2) * np.sin(yaw/2)
    qy = np.cos(roll/2) * np.sin(pitch/2) * np.cos(yaw/2) + np.sin(roll/2) * np.cos(pitch/2) * np.sin(yaw/2)
    qz = np.cos(roll/2) * np.cos(pitch/2) * np.sin(yaw/2) - np.sin(roll/2) * np.sin(pitch/2) * np.cos(yaw/2)
    qw = np.cos(roll/2) * np.cos(pitch/2) * np.cos(yaw/2) + np.sin(roll/2) * np.sin(pitch/2) * np.sin(yaw/2)
    return Quaternion(x=qx, y=qy, z=qz, w=qw)

class RobotState(Enum):
    IDLE = 1          
    STAND_UP = 2      
    STAND = 3         
    LOCOMOTION = 4    

class TrotController:
    def __init__(self):
        # self.gait_planner = GaitPlanner('trot')
        # 새로 구현한 GeneralizedGaitPlanner로 교체 (기본값 trot)
        self.gait_planner = GeneralizedGaitPlanner(initial_gait='trot')
        self.traj_gen = TrajectoryGenerator()
        self.ik_solver = InverseKinematics()
        
        self.state = RobotState.IDLE
        self.state_time = 0.0 
        
        self.idle_height = 0.18      
        self.target_height = 0.25 # 0.30    
        self.current_height = self.idle_height
        self.step_frequency = 2.0
        
        self.cmd_vel = {'x': 0.0, 'y': 0.0, 'yaw': 0.0}
        self.last_non_zero_vel = {'x': 0.0, 'y': 0.0, 'yaw': 0.0}
        self.base_foot_pos = self.get_nominal_foot_positions(self.idle_height)

    def update_command(self, msg: Twist):
        self.cmd_vel['x'] = msg.linear.x
        self.cmd_vel['y'] = msg.linear.y
        self.cmd_vel['yaw'] = msg.angular.z

    def get_nominal_foot_positions(self, height: float) -> dict:
        """Body Frame 중심 기준 기본 발 위치 산출 (오픈루프 안정성 강화를 위해 좌우 폭 확장)"""
        # lx, ly = 0.25, 0.15 
        lx = 0.25        
        # 기본 0.15m에서 4cm(0.04m) 바깥으로 벌림 (총 0.19m)
        # 튜닝하기 편하도록 패딩 변수를 더하는 형태로 작성했습니다.
        ly = 0.15 + 0.04
        
        return {
            'FL': np.array([ lx,  ly, -height]),
            'FR': np.array([ lx, -ly, -height]),
            'RL': np.array([-lx,  ly, -height]),
            'RR': np.array([-lx, -ly, -height])
        }

    def run_step(self, dt: float) -> dict:
        self.state_time += dt
        joint_commands = {}
        leg_names = ['FL', 'FR', 'RL', 'RR']
        
        vel_norm = np.hypot(self.cmd_vel['x'], self.cmd_vel['y'])
        cmd_active = (vel_norm > 0.01 or abs(self.cmd_vel['yaw']) > 0.01)

        if self.state == RobotState.IDLE:
            # 기존: idle_height를 0.18m 고정으로 시작하여 폭발적 토크 발생
            self.base_foot_pos = self.get_nominal_foot_positions(self.idle_height)
            # # 변경: IDLE 상태에서도 최초 1~2초 동안은 웅크린 높이에서 idle_height까지 서서히 증가시킴
            # init_duration = 2.0 # 2초 동안 부드럽게 초기화
            # ratio = min(self.state_time / init_duration, 1.0)
            # # 웅크린 높이(0.08m)에서 준비 높이(0.18m)까지 선형 보간
            # crouch_height = 0.08 
            # current_idle_height = crouch_height + (self.idle_height - crouch_height) * ratio
            # self.base_foot_pos = self.get_nominal_foot_positions(current_idle_height)
                        
            for name in leg_names:
                joint_commands[name] = self._solve_leg_ik(name, self.base_foot_pos[name])
            if self.state_time > 1.0:
                self._transition_to(RobotState.STAND_UP)

        elif self.state == RobotState.STAND_UP:
            stand_duration = 3.0
            ratio = min(self.state_time / stand_duration, 1.0)
            
            self.current_height = self.idle_height + (self.target_height - self.idle_height) * ratio
            self.base_foot_pos = self.get_nominal_foot_positions(self.current_height)
            
            for name in leg_names:
                joint_commands[name] = self._solve_leg_ik(name, self.base_foot_pos[name])
            if ratio >= 1.0:
                self._transition_to(RobotState.STAND)

        elif self.state == RobotState.STAND:
            self.base_foot_pos = self.get_nominal_foot_positions(self.target_height)
            for name in leg_names:
                joint_commands[name] = self._solve_leg_ik(name, self.base_foot_pos[name])
            if cmd_active:
                self._transition_to(RobotState.LOCOMOTION)

        elif self.state == RobotState.LOCOMOTION:
            # -----------------------------------------------------------
            # [추가] 속도 명령 크기에 따른 보행 패턴 실시간 전이 예약
            # -----------------------------------------------------------
            # if cmd_active:
            #     if vel_norm < 0.1:  # 0.05 m/s 등 초저속 주행 시
            #         self.gait_planner.set_gait('crawl')  # 정적 안정성이 높은 크롤 예약
            #     else:
            #         self.gait_planner.set_gait('trot')   # 일반 속도에서는 트로트 예약            
            # -----------------------------------------------------------
            # [수정] 히스테리시스(Hysteresis)를 적용한 보행 패턴 전이 예약
            # -----------------------------------------------------------
            if cmd_active:
                if vel_norm < 0.08:
                    self.gait_planner.set_gait('crawl')  # 확실한 저속 구간에서만 크롤 변환
                elif vel_norm > 0.12:
                    self.gait_planner.set_gait('trot')   # 확실한 가속 구간에서만 트로트 변환
                # 0.08 ~ 0.12 m/s 중첩 구간에서는 이전 루프의 보행 모드가 안전하게 유지됨
            
            # -----------------------------------------------------------
            # [위치] 통합 플래너의 주기적 시간 업데이트 및 상태 추출
            # -----------------------------------------------------------
            self.gait_planner.update(dt) # 한 주기가 끝나는 시점에 안전하게 보행 전이됨
            leg_states = self.gait_planner.get_leg_states()
            
            # 기존 교재의 주파수 기반 스탠스 타임 계산 보완
            current_freq = self.gait_planner.current_gait.frequency
            stance_time = 1.0 / (2.0 * current_freq)            
            # self.gait_planner.update(dt)
            # leg_states = self.gait_planner.get_leg_states()
            # stance_time = 1.0 / (2.0 * self.step_frequency)
            
            if cmd_active:
                self.last_non_zero_vel['x'] = self.cmd_vel['x']
                self.last_non_zero_vel['y'] = self.cmd_vel['y']
                self.last_non_zero_vel['yaw'] = self.cmd_vel['yaw']
                active_vel = self.cmd_vel
            else:
                active_vel = {
                    'x': self.last_non_zero_vel.get('x', 0.0), 
                    'y': self.last_non_zero_vel.get('y', 0.0),
                    'yaw': self.last_non_zero_vel.get('yaw', 0.0)
                }

            for name in leg_names:
                phase, is_swing = leg_states[name]
                nominal_pos = self.base_foot_pos[name]
                
                v_rot_x = -active_vel['yaw'] * nominal_pos[1]
                v_rot_y = active_vel['yaw'] * nominal_pos[0]
                
                total_vel_x = active_vel['x'] + v_rot_x
                total_vel_y = active_vel['y'] + v_rot_y
                
                half_stride_x = total_vel_x * stance_time / 2.0
                half_stride_y = total_vel_y * stance_time / 2.0
                
                if not is_swing:
                    target_x = nominal_pos[0] + half_stride_x * (1.0 - 2.0 * phase)
                    target_y = nominal_pos[1] + half_stride_y * (1.0 - 2.0 * phase)
                    target_pos = np.array([target_x, target_y, -self.target_height])
                else:
                    start_pos = np.array([nominal_pos[0] - half_stride_x, nominal_pos[1] - half_stride_y, -self.target_height])
                    end_pos = np.array([nominal_pos[0] + half_stride_x, nominal_pos[1] + half_stride_y, -self.target_height])
                    target_pos = self.traj_gen.generate_swing(start_pos, end_pos, phase)
                    
                joint_commands[name] = self._solve_leg_ik(name, target_pos)

            if not cmd_active and self.gait_planner.is_cycle_completed():
                self._transition_to(RobotState.STAND)

        return joint_commands

    def _transition_to(self, next_state: RobotState):
        self.state = next_state
        self.state_time = 0.0

    # ========================================================
    # [수정 포인트] Body Frame -> Leg Local Frame 변환 로직 추가
    # ========================================================
    def _solve_leg_ik(self, name: str, target_pos: np.ndarray) -> list:
        is_right = (name in ['FR', 'RR'])
        
        # 각 다리별 고관절(Hip Joint)의 물리적 오프셋 딕셔너리
        hip_offsets = {
            'FL': ( 0.25,  0.15),
            'FR': ( 0.25, -0.15),
            'RL': (-0.25,  0.15),
            'RR': (-0.25, -0.15)
        }
        
        # 바디 중심 기준 좌표에서 고관절 오프셋을 제거하여 '다리 중심 로컬 좌표'로 변환
        lx, ly = hip_offsets[name]
        local_x = target_pos[0] - lx
        local_y = target_pos[1] - ly
        local_z = target_pos[2]  # Z축은 평행하므로 그대로 유지
        
        # 변환된 로컬 좌표를 IK 솔버에 입력
        q = self.ik_solver.solve(local_x, local_y, local_z, is_right)
        
        # IK 연산 실패 시 안전 기립 각도 대입
        return q if q is not None else [0.0, -0.6, 1.2]


class TrotControllerNode(Node):
    def __init__(self):
        super().__init__('trot_controller')
        self.get_logger().info("4족 보행 로봇 Trot Controller FSM 노드 시작!")
        
        self.controller = TrotController()
        self.gait_service = self.create_service(SetGait, 'set_gait', self.set_gait_callback)
        
        self.sub_cmd = self.create_subscription(
            Twist,
            'cmd_vel',
            self.cmd_vel_callback,
            10
        )
        
        self.joint_publishers = {}
        leg_names = ['FL', 'FR', 'RL', 'RR']
        
        for leg in leg_names:
            prefix = leg.lower() 
            for joint_type in ['hip', 'thigh', 'calf']:
                joint_name = f"{prefix}_{joint_type}_joint"
                topic_name = f"/model/my_quadruped/joint/{joint_name}/cmd_pos"
                self.joint_publishers[joint_name] = self.create_publisher(Float64, topic_name, 10)
        
        self.dt = 0.01  # 100Hz
        self.last_time = None  # 초기화 지연으로 인한 첫 dt 폭증 방지
        self.timer = self.create_timer(self.dt, self.timer_callback)
        
        # Odometry 발행, TF 브로드캐스팅, 동적 파라미터 재구성, 속도 명령 LPF
        # 1. 동적 파라미터 선언 (Dynamic Reconfiguration)
        self.declare_parameter('lpf_alpha', 0.1)       # 속도 스무딩 계수 (0.0 ~ 1.0)
        self.declare_parameter('gait_period', 0.5)     # Trot 1주기 시간 (초)
        self.declare_parameter('step_height', 0.05)    # 발을 드는 높이 (m)
        self.declare_parameter('base_frame_id', 'base_link')
        self.declare_parameter('odom_frame_id', 'odom')
        
        # 파라미터 업데이트 콜백 등록
        self.add_on_set_parameters_callback(self.parameters_callback)
        self.update_parameters()

        # 2. 목표 속도 및 LPF 적용 속도 변수
        self.target_vel_x = 0.0
        self.target_vel_y = 0.0
        self.target_omega_z = 0.0
        
        self.current_vel_x = 0.0
        self.current_vel_y = 0.0
        self.current_omega_z = 0.0

        # 3. Odometry 추정 변수
        self.odom_x = 0.0
        self.odom_y = 0.0
        self.odom_th = 0.0

        # 4. FSM 및 제어 주기 변수
        # self.phase = 0.0
        # self.control_rate = 100 # Hz
        # self.dt = 1.0 / self.control_rate
        # self.last_time = self.get_clock().now()

        # 5. Publisher / Subscriber / TF Broadcaster
        # self.cmd_vel_sub = self.create_subscription(Twist, 'cmd_vel', self.cmd_vel_callback, 10)
        
        self.odom_pub = self.create_publisher(Odometry, 'odom', 10)
        # self.joint_pub = self.create_publisher(JointState, 'joint_states', 10) # 실제 제어기에 맞게 토픽/메시지 타입 변경 필요
        self.tf_broadcaster = TransformBroadcaster(self)

        # 제어 루프 타이머
        # self.timer = self.create_timer(self.dt, self.control_loop)
        self.get_logger().info("TrotControllerFSM initialized with Odometry, TF, LPF, and Dynamic Params.")
        
    def set_gait_callback(self, request, response):
        accepted = self.controller.gait_planner.set_gait(request.gait_name)
        response.success = bool(accepted)
        response.message = ('Queued gait transition at next cycle boundary'
                            if accepted else 'Unsupported gait')
        return response

    def cmd_vel_callback(self, msg: Twist):
        # self.controller.update_command(msg)
        """목표 속도 수신 (LPF 적용을 위해 target에만 저장)"""
        self.target_vel_x = msg.linear.x
        self.target_vel_y = msg.linear.y
        self.target_omega_z = msg.angular.z

    def apply_low_pass_filter(self):
        """속도 명령 스무딩 (Gait Transition 시 급격한 위상 변화 및 물리엔진 충돌 방지)"""
        self.current_vel_x += self.lpf_alpha * (self.target_vel_x - self.current_vel_x)
        self.current_vel_y += self.lpf_alpha * (self.target_vel_y - self.current_vel_y)
        self.current_omega_z += self.lpf_alpha * (self.target_omega_z - self.current_omega_z)

    def timer_callback(self):        
        current_time = self.get_clock().now()
        
        if self.last_time is None:
            self.last_time = current_time
            return  # 첫 루프는 스킵하여 비정상적인 dt_sec 방지

        dt_sec = (current_time - self.last_time).nanoseconds / 1e9
        self.last_time = current_time
        
        # 1. 속도 스무딩 (LPF 적용)
        self.apply_low_pass_filter()
        
        # 2. 알고리즘 코어(Controller)에 부드러운 속도 주입
        safe_twist = Twist()
        safe_twist.linear.x = self.current_vel_x
        safe_twist.linear.y = self.current_vel_y
        safe_twist.angular.z = self.current_omega_z
        self.controller.update_command(safe_twist)
                
        # 3. Odometry 및 TF 업데이트
        self.update_odometry_and_tf(current_time, dt_sec)        
                
        # 4. FSM 및 IK 제어 스텝 실행 (고정값 self.dt 대신 실제 측정된 dt_sec 주입)
        joint_cmds = self.controller.run_step(dt_sec)
        
        # 5. 관절 명령 발행        
        joint_types = ['hip', 'thigh', 'calf']
        
        for leg_name, angles in joint_cmds.items():
            prefix = leg_name.lower()
            for i, j_type in enumerate(joint_types):
                joint_name = f"{prefix}_{j_type}_joint"
                msg = Float64()
                msg.data = float(angles[i])
                self.joint_publishers[joint_name].publish(msg)

    # Odometry 발행, TF 브로드캐스팅, 동적 파라미터 재구성, 속도 명령 LPF                    
    def update_odometry_and_tf(self, current_time, dt_sec):
        """Kinematics 기반 Odometry 계산 및 TF 발행"""        
        
        # 1. Odometry 적분 (Local -> Global Transform)
        delta_x = (self.current_vel_x * math.cos(self.odom_th) - self.current_vel_y * math.sin(self.odom_th)) * dt_sec
        delta_y = (self.current_vel_x * math.sin(self.odom_th) + self.current_vel_y * math.cos(self.odom_th)) * dt_sec
        delta_th = self.current_omega_z * dt_sec

        self.odom_x += delta_x
        self.odom_y += delta_y
        self.odom_th += delta_th

        odom_quat = euler_to_quaternion(0, 0, self.odom_th)

        # 2. Transform Broadcaster (odom -> base_link)
        t = TransformStamped()
        t.header.stamp = current_time.to_msg()
        t.header.frame_id = self.odom_frame_id
        t.child_frame_id = self.base_frame_id
        t.transform.translation.x = self.odom_x
        t.transform.translation.y = self.odom_y
        t.transform.translation.z = 0.0 # 평면 보행 가정, 필요시 로봇 높이 반영
        t.transform.rotation = odom_quat
        self.tf_broadcaster.sendTransform(t)

        # 3. Odometry Topic 발행
        odom_msg = Odometry()
        odom_msg.header.stamp = current_time.to_msg()
        odom_msg.header.frame_id = self.odom_frame_id
        odom_msg.child_frame_id = self.base_frame_id
        
        odom_msg.pose.pose.position.x = self.odom_x
        odom_msg.pose.pose.position.y = self.odom_y
        odom_msg.pose.pose.position.z = 0.0
        odom_msg.pose.pose.orientation = odom_quat
        
        # LPF가 적용된 현재 속도 반영
        odom_msg.twist.twist.linear.x = self.current_vel_x
        odom_msg.twist.twist.linear.y = self.current_vel_y
        odom_msg.twist.twist.angular.z = self.current_omega_z
        
        self.odom_pub.publish(odom_msg)
        
    def update_parameters(self):
        """파라미터 서버로부터 최신 값을 가져와 로컬 변수에 캐싱"""
        self.lpf_alpha = self.get_parameter('lpf_alpha').value
        self.gait_period = self.get_parameter('gait_period').value
        self.step_height = self.get_parameter('step_height').value
        self.base_frame_id = self.get_parameter('base_frame_id').value
        self.odom_frame_id = self.get_parameter('odom_frame_id').value
        
        # [추가] 초기화 시 알고리즘 코어에도 동기화
        self._sync_controller_params()

    def parameters_callback(self, params):
        """동적 파라미터 변경 시 호출되는 콜백"""
        for param in params:
            if param.name == 'lpf_alpha':
                if 0.0 <= param.value <= 1.0:
                    self.lpf_alpha = param.value
                    self.get_logger().info(f"Updated lpf_alpha: {self.lpf_alpha}")
                else:
                    return SetParametersResult(successful=False, reason="lpf_alpha must be between 0.0 and 1.0")
            elif param.name == 'gait_period':
                self.gait_period = param.value
            elif param.name == 'step_height':
                self.step_height = param.value

        # [추가] 파라미터 변경 시 알고리즘 코어에도 즉각 동기화
        self._sync_controller_params()                
        return SetParametersResult(successful=True)
    
    def _sync_controller_params(self):
        """ROS 파라미터를 FSM 알고리즘 변수에 매핑하는 헬퍼 함수"""
        # 주기(초)를 주파수(Hz)로 변환하여 동기화
        if self.gait_period > 0.0:
            self.controller.step_frequency = 1.0 / self.gait_period
            
            # [수정] 플래너 내부의 현재 활성화된 보행 주파수 객체에도 값을 직접 동기화
            if hasattr(self.controller.gait_planner, 'current_gait'):
                self.controller.gait_planner.current_gait.frequency = self.controller.step_frequency
        
        # 보행 높이 연동 필요 시 아래와 같이 추가 (Trajectory Generator 등에 전달)
        # 트랙터 제너레이터의 스텝 높이 파라미터 연동도 활성화
        if hasattr(self.controller, 'traj_gen'):
            self.controller.traj_gen.step_height = self.step_height
        
        
def main(args=None):
    rclpy.init(args=args)
    node = TrotControllerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("컨트롤러 노드를 종료합니다.")
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()