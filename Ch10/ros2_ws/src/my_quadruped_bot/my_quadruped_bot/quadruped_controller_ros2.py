#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
파일명: quadruped_controller_ros2.py
설명: 'Physical AI 실무 가이드' 10.7절 통합 예제 코드
      - 동적 파라미터 재구성 (안전 검증 포함)
      - 50Hz 메인 제어 루프 (LPF 적용, IK 예외 처리 및 실시간성 체크)
      - 추측 항법(Dead Reckoning) 기반 오도메트리 및 TF 발행
      - [수정] cmd_vel 구독자 추가를 통한 원격 제어(Teleop) 연동
"""

import math
import numpy as np

import rclpy
from rclpy.node import Node
from rcl_interfaces.msg import SetParametersResult

from sensor_msgs.msg import JointState
from std_msgs.msg import Float64
from nav_msgs.msg import Odometry
from geometry_msgs.msg import TransformStamped, Twist  # Twist 임포트 추가
from tf2_ros import TransformBroadcaster

# (참고) 책의 이전 장에서 구현한 모듈들을 임포트한다고 가정
from my_quadruped_bot.trajectory_generator import TrajectoryGenerator
from my_quadruped_bot.inverse_kinematics import InverseKinematics
from my_quadruped_bot.generalized_gait_planner import GeneralizedGaitPlanner, GAIT_LIBRARY

class QuadrupedControllerROS2(Node):
    def __init__(self):
        super().__init__('quadruped_controller')
        
        # -----------------------------------------------------------------
        # 1. 파라미터 선언 및 동적 재구성(Dynamic Reconfigure) 설정
        # -----------------------------------------------------------------
        self.declare_parameter('alpha', 0.1)        # 속도 스무딩 LPF 계수
        self.declare_parameter('step_freq', 2.0)    # 보행 주파수 (Hz)
        self.declare_parameter('gait_type', 'trot') # 기본 보행 타입
        self.declare_parameter('cmd_timeout_sec', 0.5)
        self.declare_parameter('publish_cmd_odom_tf', False)
        
        self.alpha = self.get_parameter('alpha').value
        self.supported_gaits = list(GAIT_LIBRARY)
        
        # 파라미터 변경 콜백 등록 (실시간 튜닝 지원)
        self.add_on_set_parameters_callback(self.parameter_callback)
        
        # 제어 지연 방지 플래그
        self.is_first_loop = True

        # -----------------------------------------------------------------
        # 2. 제어 데이터 구조 및 하드코딩 방지 (관절 이름 매핑)
        # -----------------------------------------------------------------
        self.leg_names = ['FL', 'FR', 'RL', 'RR']
        self.joint_types = ['hip', 'thigh', 'calf']
        self.joint_names = [f"{leg}_{joint}_joint" for leg in self.leg_names for joint in self.joint_types]
        
        # IK 실패 시 Jerk 방지를 위한 안전 스탠스 (이전 상태 유지용)
        self.default_stance = [0.0, -0.3, 0.6]
        self.prev_joint_positions = self.default_stance * len(self.leg_names)
        
        # 속도 및 오도메트리 상태 변수
        self.cmd_vel_target = [0.0, 0.0, 0.0]  # x, y, yaw 목표 속도
        self.cmd_vel_filtered = [0.0, 0.0, 0.0]
        self.odom_pose = {'x': 0.0, 'y': 0.0, 'theta': 0.0}
        self.last_odom_time = self.get_clock().now()
        self.last_cmd_time = self.get_clock().now()
        self.publish_cmd_odom_tf = bool(self.get_parameter('publish_cmd_odom_tf').value)

        # 외부 알고리즘 객체 초기화 (가정)
        self.ik_solver = InverseKinematics()
        self.gait_planner = GeneralizedGaitPlanner(initial_gait='trot')
        self.traj_gen = TrajectoryGenerator(step_height=0.04, stance_depth=-0.30)        

        # -----------------------------------------------------------------
        # 3. ROS 2 통신 인터페이스 (Subscriber, Publisher, TF)
        # -----------------------------------------------------------------
        # [추가] cmd_vel 토픽 구독을 통한 속도 명령 수신
        self.cmd_sub = self.create_subscription(
            Twist,
            'cmd_vel',
            self.cmd_vel_callback,
            10
        )
        
        # JointState is feedback (Gazebo -> ROS); commands use individual Float64 topics.
        self.joint_publishers = {}
        for leg in self.leg_names:
            for joint in self.joint_types:
                name = f'{leg.lower()}_{joint}_joint'
                topic = f'/model/my_quadruped/joint/{name}/cmd_pos'
                self.joint_publishers[name] = self.create_publisher(Float64, topic, 10)
        # Clearly label commanded dead reckoning; do not claim sensor odometry.
        self.odom_pub = self.create_publisher(Odometry, 'cmd_integrated_odom', 10)
        self.tf_broadcaster = TransformBroadcaster(self) if self.publish_cmd_odom_tf else None
        
        # 50Hz (0.02초) 메인 제어 루프 타이머
        self.control_timer = self.create_timer(0.02, self.control_loop_callback)
        self.get_logger().info("Quadruped Controller Node Started (50Hz). Ready for Teleop.")

    # =====================================================================
    # [추가] 원격 제어(Teleop) 속도 명령 수신 콜백
    # =====================================================================
    def cmd_vel_callback(self, msg: Twist):
        # 배열 인덱스: 0 -> x (전후진), 1 -> y (좌우 횡이동), 2 -> yaw (제자리 회전)
        command = [msg.linear.x, msg.linear.y, msg.angular.z]
        if not all(math.isfinite(float(x)) for x in command):
            self.get_logger().warning('Rejecting non-finite cmd_vel')
            return
        self.cmd_vel_target = [max(-limit, min(limit, float(x)))
                               for x, limit in zip(command, (0.25, 0.15, 0.5))]
        self.last_cmd_time = self.get_clock().now()

    # =====================================================================
    # 10.7.5 동적 파라미터 안전 검증 및 반영
    # =====================================================================
    def parameter_callback(self, params):
        # Validate first to avoid accepting half-applied parameter batches.
        updates = {p.name: p.value for p in params}
        for name, value in updates.items():
            if name == 'publish_cmd_odom_tf':
                return SetParametersResult(successful=False, reason='TF setting requires restart')
            if name == 'alpha' and not (isinstance(value, (int, float)) and math.isfinite(value) and 0 < value <= 1):
                return SetParametersResult(successful=False, reason='alpha must be in (0, 1]')
            if name == 'step_freq' and not (isinstance(value, (int, float)) and math.isfinite(value) and 0.2 <= value <= 4.0):
                return SetParametersResult(successful=False, reason='step_freq must be 0.2..4 Hz')
            if name == 'gait_type' and value not in self.supported_gaits:
                return SetParametersResult(successful=False, reason='Unsupported gait')
            if name == 'cmd_timeout_sec' and not (isinstance(value, (int, float)) and math.isfinite(value) and 0.05 <= value <= 2.0):
                return SetParametersResult(successful=False, reason='timeout must be 0.05..2 sec')
        if 'alpha' in updates:
            self.alpha = float(updates['alpha'])
        if 'step_freq' in updates:
            freq = float(updates['step_freq'])
            self.gait_planner.current_gait.frequency = freq
            if self.gait_planner.next_gait is not None:
                self.gait_planner.next_gait.frequency = freq
        if 'gait_type' in updates:
            self.gait_planner.set_gait(updates['gait_type'])
        return SetParametersResult(successful=True)

    # =====================================================================
    # 10.7.3 메인 제어 루프 구현
    # =====================================================================
    def control_loop_callback(self):
        start_time = self.get_clock().now()
        
        current_loop_positions = []
        age = (start_time - self.last_cmd_time).nanoseconds / 1e9
        if age < 0.0 or age > self.get_parameter('cmd_timeout_sec').value:
            self.cmd_vel_target = [0.0, 0.0, 0.0]
        self.gait_planner.update(0.02)
        leg_states = self.gait_planner.get_leg_states()
        
        # [단계 1] 속도 명령 스무딩 (LPF)
        for i in range(3):
            self.cmd_vel_filtered[i] = (self.alpha * self.cmd_vel_target[i] + 
                                        (1.0 - self.alpha) * self.cmd_vel_filtered[i])
            
        # 다리별 역운동학 연산
        for i, leg in enumerate(self.leg_names):
            # [단계 2] 목표 발끝 위치 계산 (Trajectory)
            target_foot_pos = self.compute_foot_trajectory(leg, self.cmd_vel_filtered, leg_states[leg])
            
            # [단계 3] IK 해 계산 및 예외(Jerk 방지) 처리
            hx = 0.25 if leg.startswith('F') else -0.25
            hy = 0.10 if leg.endswith('L') else -0.10
            ik_angles = self.ik_solver.solve(
                target_foot_pos[0] - hx, target_foot_pos[1] - hy,
                target_foot_pos[2], is_right_leg=leg.endswith('R'))
            
            start_idx = i * 3
            end_idx = start_idx + 3
            
            if ik_angles is not None:
                current_loop_positions.extend(ik_angles)
                self.prev_joint_positions[start_idx:end_idx] = ik_angles
            else:
                self.get_logger().warn(f"[{leg}] IK 실패! 이전 안전 각도를 유지합니다.")
                current_loop_positions.extend(self.prev_joint_positions[start_idx:end_idx])
                
        # [단계 4] Send Gazebo position-command Float64 messages.
        for name, angle in zip(self.joint_names, current_loop_positions):
            self.joint_publishers[name.lower()].publish(Float64(data=float(angle)))
        self.publish_odometry(self.cmd_vel_filtered, start_time)
        
        # 실시간성 체크 (목표 20ms 이내 보장 확인)
        loop_duration = (self.get_clock().now() - start_time).nanoseconds / 1e6
        if loop_duration > 20.0:
            self.get_logger().error(f"제어 지연: {loop_duration:.2f}ms (위험 수준)")

    def compute_foot_trajectory(self, leg, cmd_vel, state):
        """Compute body-frame stance/swing target for each leg."""
        nominal = np.array([
            0.25 if leg.startswith('F') else -0.25,
            0.15 if leg.endswith('L') else -0.15,
            -0.30,
        ], dtype=float)
        vx, vy, wz = cmd_vel
        foot_v = np.array([vx - wz * nominal[1], vy + wz * nominal[0], 0.0])
        gait = self.gait_planner.current_gait
        cycle = 1.0 / gait.frequency
        duty = gait.duty_factor
        phase, is_swing = state
        if not is_swing:
            return self.traj_gen.generate_stance(nominal, foot_v, phase, cycle, duty)
        half_stroke = foot_v * cycle * duty * 0.5
        return self.traj_gen.generate_swing(nominal - half_stroke,
                                            nominal + half_stroke, phase)

    # =====================================================================
    # 10.7.4 추측 항법(Dead Reckoning) 기반 오도메트리
    # =====================================================================
    def publish_odometry(self, current_vel, current_time):
        if self.is_first_loop:
            self.last_odom_time = current_time
            self.is_first_loop = False
            return  # 첫 주기는 dt 측정이 부정확하므로 스킵
        
        # 동적 dt 계산 (Jitter로 인한 누적 오차 방지)
        dt = (current_time - self.last_odom_time).nanoseconds / 1e9
        self.last_odom_time = current_time
        
        if dt <= 0.0:
            return

        vx, vy, wz = current_vel[0], current_vel[1], current_vel[2]
        theta = self.odom_pose['theta']
        
        # 로컬 속도를 글로벌 좌표계로 변환하여 적분
        self.odom_pose['x'] += (vx * math.cos(theta) - vy * math.sin(theta)) * dt
        self.odom_pose['y'] += (vx * math.sin(theta) + vy * math.cos(theta)) * dt
        self.odom_pose['theta'] += wz * dt
        
        q = self.euler_to_quaternion(0.0, 0.0, self.odom_pose['theta'])
        
        # 1. TF 메시지 게시 (RViz2 시각화)
        t = TransformStamped()
        t.header.stamp = current_time.to_msg()
        t.header.frame_id = 'cmd_odom'
        t.child_frame_id = 'base_link'
        t.transform.translation.x = self.odom_pose['x']
        t.transform.translation.y = self.odom_pose['y']
        t.transform.translation.z = 0.0
        t.transform.rotation.x, t.transform.rotation.y, t.transform.rotation.z, t.transform.rotation.w = q
        if self.tf_broadcaster is not None:
            self.tf_broadcaster.sendTransform(t)
        
        # 2. Odometry 토픽 발행 (Nav2 연동 등 확장성)
        odom_msg = Odometry()
        odom_msg.header.stamp = current_time.to_msg()
        odom_msg.header.frame_id = 'cmd_odom'
        odom_msg.child_frame_id = 'base_link'
        odom_msg.pose.pose.position.x = self.odom_pose['x']
        odom_msg.pose.pose.position.y = self.odom_pose['y']
        odom_msg.pose.pose.orientation.x, odom_msg.pose.pose.orientation.y, odom_msg.pose.pose.orientation.z, odom_msg.pose.pose.orientation.w = q
        odom_msg.twist.twist.linear.x = vx
        odom_msg.twist.twist.linear.y = vy
        odom_msg.twist.twist.angular.z = wz
        odom_msg.pose.covariance[0] = 10.0 # command-integrated estimate, not sensed pose
        odom_msg.pose.covariance[7] = 10.0
        odom_msg.pose.covariance[35] = 10.0
        self.odom_pub.publish(odom_msg)

    def euler_to_quaternion(self, roll, pitch, yaw):
        qx = np.sin(roll/2) * np.cos(pitch/2) * np.cos(yaw/2) - np.cos(roll/2) * np.sin(pitch/2) * np.sin(yaw/2)
        qy = np.cos(roll/2) * np.sin(pitch/2) * np.cos(yaw/2) + np.sin(roll/2) * np.cos(pitch/2) * np.sin(yaw/2)
        qz = np.cos(roll/2) * np.cos(pitch/2) * np.sin(yaw/2) - np.sin(roll/2) * np.sin(pitch/2) * np.cos(yaw/2)
        qw = np.cos(roll/2) * np.cos(pitch/2) * np.cos(yaw/2) + np.sin(roll/2) * np.sin(pitch/2) * np.sin(yaw/2)
        return [qx, qy, qz, qw]

def main(args=None):
    rclpy.init(args=args)
    node = QuadrupedControllerROS2()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("사용자에 의해 종료됩니다.")
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()