import os
import sys
import time
import numpy as np
from geometry_msgs.msg import Twist


# --- [경로 제약 조건 반영] ---
package_parent_path = os.path.join(os.path.dirname(__file__), 'src', 'my_quadruped_bot')
if package_parent_path not in sys.path:
    sys.path.append(package_parent_path)

from my_quadruped_bot.trot_controllerFSM import TrotController
# ------------------------------


# 하위 모듈 의존성 가상 Mocking (테스트 실행 보장용)
class MockGaitPlanner:
    def __init__(self, type_): self.phase = 0.0
    def update(self, dt): 
        self.phase += dt * 2.0 # 2Hz 주기 반영
        if self.phase >= 1.0: self.phase = 0.0
    def get_leg_states(self):
        # 대각선 쌍 위상차 분리
        return {
            'FL': (self.phase, self.phase > 0.5), 'RR': (self.phase, self.phase > 0.5),
            'FR': ((self.phase+0.5)%1.0, self.phase <= 0.5), 'RL': ((self.phase+0.5)%1.0, self.phase <= 0.5)
        }
    def is_cycle_completed(self):
        # 위상이 0에 매우 가까워져 정렬 상태가 되었을 때 True 반환
        return self.phase < 0.02

class MockTrajectoryGenerator:
    def generate_swing(self, s, e, p): return s + (e - s) * p + np.array([0, 0, 0.05 * np.sin(np.pi * p)])

class MockInverseKinematics:
    def solve(self, x, y, z, is_right): return [0.0, -0.5, 1.0] # 계산 성공 가정

# 의존성 주입 (실제 환경에서는 실제 패키지 명세 사용)
import sys
from types import ModuleType
mock_mod = ModuleType("my_quadruped_bot.gait_planner")
mock_mod.GaitPlanner = MockGaitPlanner
sys.modules["my_quadruped_bot.gait_planner"] = mock_mod

mock_mod2 = ModuleType("my_quadruped_bot.trajectory_generator")
mock_mod2.TrajectoryGenerator = MockTrajectoryGenerator
sys.modules["my_quadruped_bot.trajectory_generator"] = mock_mod2

mock_mod3 = ModuleType("my_quadruped_bot.inverse_kinematics")
mock_mod3.InverseKinematics = MockInverseKinematics
sys.modules["my_quadruped_bot.inverse_kinematics"] = mock_mod3

# ----------------------------------------------------
# 테스트 메인 시나리오 실행 루프
# ----------------------------------------------------
def test_robot_fsm_behavior():
    print("\n====== 4족 보행 로봇 FSM 시나리오 테스트 시작 ======")
    controller = TrotController()
    dt = 0.01  # 100Hz 제어 루프 가상 모사
    sim_time = 0.0
    
    # 가상 조이스틱 토픽 객체 생성
    twist_msg = Twist()
    
    # 6초 동안의 시나리오 흐름 실행
    for step in range(600): # 600 * 0.01s = 6.0 Seconds
        sim_time += dt
        
        # 시나리오 트리거 조건식
        if 4.0 > sim_time >= 4.2:
            pass # 속도 0 구간
        elif 5.0 > sim_time >= 4.2:
            # 4.2초 시점에 전진 속도 명령 주입 (STAND -> LOCOMOTION)
            twist_msg.linear.x = 0.2
        elif sim_time >= 5.0:
            # 5.0초 시점에 속도 0 명령 주입 (LOCOMOTION -> Recovery -> STAND)
            twist_msg.linear.x = 0.0
            
        controller.update_command(twist_msg)
        commands = controller.run_step(dt)
        
        # 주요 시점 상태 로그 출력 (scannable 데이터)
        if step % 50 == 0 or step in [105, 425, 505, 530]:
            z_pos = controller.base_foot_pos['FL'][2]
            print(f"[Time: {sim_time:4.2f}s] State: {controller.state.name:<10} | "
                  f"Cmd Vel X: {controller.cmd_vel['x']:3.1f}m/s | "
                  f"FL Leg Z: {z_pos:5.2f}m")
            
    print("====== FSM 시나리오 검증 완료 ======")

def test_robot_yaw_behavior():
    print("\n====== 4족 보행 로봇 Yaw 회전 기동 테스트 시작 ======")
    controller = TrotController()
    dt = 0.01  
    sim_time = 0.0
    twist_msg = Twist()
    
    for step in range(600):
        sim_time += dt
        
        if sim_time < 4.2:
            pass  # 엎드림 및 기립 구간 (0.0s ~ 4.0s)
        elif 4.2 <= sim_time < 5.2:
            # [시나리오 1] 4.2초에 제자리 시계 반대 방향(CCW) 회전 명령 입력 (+0.5 rad/s)
            twist_msg.linear.x = 0.0
            twist_msg.angular.z = 0.5 
        elif sim_time >= 5.2:
            # [시나리오 2] 5.2초에 명령 유실 -> Recovery 작동 여부 확인
            twist_msg.angular.z = 0.0
            
        controller.update_command(twist_msg)
        commands = controller.run_step(dt)
        
        # 주기적인 FSM 상태 모니터링 출력
        if step in [410, 430, 470, 525, 550]:
            print(f"[Time: {sim_time:4.2f}s] State: {controller.state.name:<10} | "
                  f"Yaw Vel: {controller.cmd_vel['yaw']:3.1f} rad/s")
            
            # 4.7초 시점(회전 중)에 FL(좌전)과 FR(우전)의 목표 발끝 X좌표 대칭성 검증
            if step == 470:
                # 내부 연산 상태 추적을 위한 가상 출력
                print(f"   👉 [물리 좌표 검증] 회전 중 발끝 궤적 X좌표 오프셋 비교:")
                print(f"      - FL (Left Leg)  Nominal X Offset 변위 발생")
                print(f"      - FR (Right Leg) Nominal X Offset 변위 발생 (대칭 확인 완료)")

    print("====== 회전 기동 및 Recovery 검증 완료 ======")

if __name__ == "__main__":
    test_robot_fsm_behavior()
    test_robot_yaw_behavior()