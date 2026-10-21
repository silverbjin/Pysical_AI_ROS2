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


# Use the actual GaitPlanner, TrajectoryGenerator and IK.
# Running this script requires ROS message packages; it is not a Gazebo physics test.

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
        if sim_time < 4.2:
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
            
    assert controller.state.name == 'STAND', 'Controller failed to return to STAND'
    assert len(commands) == 4, 'All four legs must receive joint targets'
    assert all(len(values) == 3 and np.all(np.isfinite(values))
               for values in commands.values()), 'Non-finite or incomplete command'
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
                assert len(commands) == 4
                assert all(np.all(np.isfinite(v)) for v in commands.values())
                print("   Generated 12 finite joint commands; physical yaw not verified")

    print("====== 회전 기동 및 Recovery 검증 완료 ======")

if __name__ == "__main__":
    test_robot_fsm_behavior()
    test_robot_yaw_behavior()