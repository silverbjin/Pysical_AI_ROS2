"""
[코드 6-1] simple_ik_concept_animated.py : 2축 로봇 팔의 수치해석적 IK 및 내부 상태 시각화 예제
"""
import math
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation

# 로봇 팔 링크 길이 정의 (단위: m)
L1 = 0.5
L2 = 0.5

def forward_kinematics(theta1, theta2):
    """정운동학(FK): 관절 각도를 입력받아 말단 장치(End-Effector)의 (x, y) 좌표 반환"""
    x = L1 * math.cos(theta1) + L2 * math.cos(theta1 + theta2)
    y = L1 * math.sin(theta1) + L2 * math.sin(theta1 + theta2)
    return np.array([x, y])

def compute_jacobian(theta1, theta2):
    """
    야코비안 행렬 계산: 현재 관절 상태에서 미세 변화에 따른 말단 속도 관계식
    J = [[dx/d_theta1, dx/d_theta2],
         [dy/d_theta1, dy/d_theta2]]
    """
    j11 = -L1 * math.sin(theta1) - L2 * math.sin(theta1 + theta2)
    j12 = -L2 * math.sin(theta1 + theta2)
    j21 =  L1 * math.cos(theta1) + L2 * math.cos(theta1 + theta2)
    j22 =  L2 * math.cos(theta1 + theta2)
    return np.array([[j11, j12], [j21, j22]])

def inverse_kinematics_numerical(target_x, target_y, init_theta1=0.1, init_theta2=0.1):
    """
    수치해석적 역운동학 (Newton-Raphson Method)
    매 Iteration마다 솔버가 계산하는 관절 공간의 '업데이트 값'을 추적하여 기록합니다.
    """
    theta = np.array([init_theta1, init_theta2])
    
    # 시각화를 위해 (현재 각도, 직전 단계 대비 델타 각도)를 저장
    history = [(theta.copy(), np.array([0.0, 0.0]))]
    
    learning_rate = 0.1
    tolerance = 0.001  # 허용 오차 1mm
    max_iter = 100
    
    for i in range(max_iter):
        current_pos = forward_kinematics(theta[0], theta[1])
        error = np.array([target_x, target_y]) - current_pos
        
        if np.linalg.norm(error) < tolerance:
            break
            
        J = compute_jacobian(theta[0], theta[1])
        
        try:
            J_inv = np.linalg.pinv(J)  # 의사역행렬(Pseudo-Inverse)을 통한 특이점 방어
        except np.linalg.LinAlgError:
            print("특이점(Singularity) 발생!")
            break
            
        # 솔버가 구하고자 하는 핵심 가치: Delta Theta (관절 공간에서의 수정 방향 및 크기)
        delta_theta = J_inv @ error
        theta = theta + learning_rate * delta_theta
        
        # 실제 반영된 변화량(학습률 적용)과 함께 기록
        history.append((theta.copy(), learning_rate * delta_theta))
        
    return history

# --- 시각화 및 애니메이션 설정 ---
if __name__ == "__main__":
    # 독자가 역운동학의 수렴 과정을 극적으로 관찰할 수 있도록 초기 위치와 목표 위치를 멀리 배치
    # 초기 관절: (0.1 rad, 0.1 rad) -> 대략 제 1사분면에 웅크린 상태
    # 목표 위치: (-0.6, 0.5) -> 제 2사분면 끝단 멀리 설정 (총 도달 가능 반경 1.0m 이내)
    target_pos = (-0.6, 0.5)
    
    # IK 계산 수행 및 히스토리 추출
    history = inverse_kinematics_numerical(target_pos[0], target_pos[1], init_theta1=0.1, init_theta2=0.1)
    
    fig, ax = plt.subplots(figsize=(7, 7))
    ax.set_xlim(-1.2, 1.2)
    ax.set_ylim(-1.2, 1.2)
    ax.set_aspect('equal')
    ax.set_title("IK Solver Internal State (Newton-Raphson)\n[Press 'Space' to START / PAUSE]")
    ax.grid(True, linestyle='--', alpha=0.5)
    
    # 목표 지점 및 기하학적 한계선(작업 영역 구역) 표시
    ax.plot(target_pos[0], target_pos[1], 'r*', markersize=15, label="Target Position")
    workspace_boundary = plt.Circle((0, 0), L1 + L2, color='gray', fill=False, linestyle=':', alpha=0.5)
    ax.add_artist(workspace_boundary)
    
    # 그래픽 객체 초기화
    line, = ax.plot([], [], 'o-', lw=4, markersize=8, color='#2C3E50', label="Robot Arm")
    # 엔드이펙터의 이전 흔적(궤적)을 남기기 위한 라인 설정 (오렌지색, 투명도 0.6)
    trail_line, = ax.plot([], [], color='#E67E22', lw=2, alpha=0.6, linestyle='-', label="End-Effector Trail")
    
    # 상태 정보를 실시간으로 출력할 텍스트 패널
    text_info = ax.text(0.05, 0.82, "", transform=ax.transAxes, 
                        fontdict={'family': 'monospace', 'size': 10},
                        bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    ax.legend(loc="lower left")
    
    # 궤적 저장을 위한 리스트
    trail_x, trail_y = [], []
    
    # [조건 반영] 프로그램 실행 시 처음에는 일시정지(대기) 상태로 시작
    is_paused = True

    def update(frame_idx):
        if frame_idx >= len(history):
            return line, trail_line, text_info
            
        theta, delta_theta = history[frame_idx]
        
        # 순운동학으로 각 관절의 물리적 x, y 좌표 도출
        x0, y0 = 0, 0
        x1 = L1 * math.cos(theta[0])
        y1 = L1 * math.sin(theta[0])
        x2, y2 = forward_kinematics(theta[0], theta[1])
        
        # 로봇 팔 세그먼트 업데이트
        line.set_data([x0, x1, x2], [y0, y1, y2])
        
        # 엔드이펙터 끝점 궤적 축적 및 업데이트
        trail_x.append(x2)
        trail_y.append(y2)
        trail_line.set_data(trail_x, trail_y)
        
        # 오차 계산
        error_dist = math.dist([x2, y2], target_pos)
        
        # 솔버가 구하고 있는 값 자체(\Delta \theta)와 상태 변화를 실시간으로 피드백
        status = (
            f"[Iteration {frame_idx:02d}]\n"
            f"---------------------------------\n"
            f"Current Joint Angles:\n"
            f"  Th1 = {math.degrees(theta[0]):7.2f}°\n"
            f"  Th2 = {math.degrees(theta[1]):7.2f}°\n"
            f"Solver Output (Delta Theta):\n"
            f"  d_Th1 = {delta_theta[0]:.5f} rad\n"
            f"  d_Th2 = {delta_theta[1]:.5f} rad\n"
            f"---------------------------------\n"
            f"Distance Error = {error_dist:.4f} m"
        )
        text_info.set_text(status)
        return line, trail_line, text_info

    def toggle_pause(event):
        global is_paused
        if event.key == ' ':
            if is_paused:
                ani.resume()
                print("[시스템] 애니메이션 시작/재개")
            else:
                ani.pause()
                print("[시스템] 일시 정지")
            is_paused = not is_paused

    fig.canvas.mpl_connect('key_press_event', toggle_pause)

    # 애니메이션 정의
    ani = animation.FuncAnimation(
        fig, update, frames=len(history), interval=150, blit=False, repeat=False
    )
    
    # [핵심 구현] 초기 구동 시 인트로 화면에서 일시정지 상태를 유지하게 만듦
    # plt.show()가 호출된 직후 이벤트를 통해 루프가 돌기 전 첫 프레임 상태로 일시정지 시킵니다.
    ani.pause() 
    
    plt.show()