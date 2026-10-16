"""
[코드 6-1] interactive_ik_solver.py : 슬라이더를 통한 2축 로봇 팔의 IK 수치해석 실시간 시뮬레이터
"""
import math
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.widgets import Slider, Button

# 로봇 팔 링크 길이 (단위: m)
L1 = 0.5
L2 = 0.5

def forward_kinematics(theta1, theta2):
    x = L1 * math.cos(theta1) + L2 * math.cos(theta1 + theta2)
    y = L1 * math.sin(theta1) + L2 * math.sin(theta1 + theta2)
    return np.array([x, y])

def compute_jacobian(theta1, theta2):
    j11 = -L1 * math.sin(theta1) - L2 * math.sin(theta1 + theta2)
    j12 = -L2 * math.sin(theta1 + theta2)
    j21 =  L1 * math.cos(theta1) + L2 * math.cos(theta1 + theta2)
    j22 =  L2 * math.cos(theta1 + theta2)
    return np.array([[j11, j12], [j21, j22]])

def inverse_kinematics_numerical(target_x, target_y, init_t1, init_t2):
    theta = np.array([init_t1, init_t2])
    history = [(theta.copy(), np.array([0.0, 0.0]))]
    
    learning_rate = 0.1
    tolerance = 0.001
    max_iter = 150
    
    for i in range(max_iter):
        current_pos = forward_kinematics(theta[0], theta[1])
        error = np.array([target_x, target_y]) - current_pos
        
        if np.linalg.norm(error) < tolerance:
            break
            
        J = compute_jacobian(theta[0], theta[1])
        try:
            J_inv = np.linalg.pinv(J)
        except np.linalg.LinAlgError:
            break
            
        delta_theta = J_inv @ error
        theta = theta + learning_rate * delta_theta
        history.append((theta.copy(), learning_rate * delta_theta))
        
    return history

# --- GUI 및 시각화 설정 ---
if __name__ == "__main__":
    # 초기 상태 변수
    init_target = [-0.6, 0.5]
    init_theta = [0.1, 0.1]
    
    # 메인 피규어 생성 및 슬라이더 공간 확보
    fig, ax = plt.subplots(figsize=(8, 9))
    plt.subplots_adjust(bottom=0.35) # 하단에 슬라이더 배치를 위한 여백 확보
    
    ax.set_xlim(-1.2, 1.2)
    ax.set_ylim(-1.2, 1.2)
    ax.set_aspect('equal')
    ax.set_title("Interactive IK Solver\n[Press 'Space' to START / PAUSE]")
    ax.grid(True, linestyle='--', alpha=0.5)
    
    # 작업 영역(Workspace) 경계선
    workspace = plt.Circle((0, 0), L1 + L2, color='gray', fill=False, linestyle=':', alpha=0.5)
    ax.add_artist(workspace)
    
    # 그래픽 객체 초기화
    target_point, = ax.plot(init_target[0], init_target[1], 'r*', markersize=15, label="Target")
    line, = ax.plot([], [], 'o-', lw=4, markersize=8, color='#2C3E50', label="Robot Arm")
    trail_line, = ax.plot([], [], color='#E67E22', lw=2, alpha=0.6, linestyle='-')
    text_info = ax.text(0.05, 0.75, "", transform=ax.transAxes, 
                        fontdict={'family': 'monospace', 'size': 9},
                        bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    ax.legend(loc="upper right")

    # --- 애니메이션 상태 제어기 ---
    # ani.pause()의 버그를 우회하기 위해 논리적으로 재생 상태를 제어합니다.
    sim_state = {
        'history': inverse_kinematics_numerical(init_target[0], init_target[1], init_theta[0], init_theta[1]),
        'frame_idx': 0,
        'is_playing': False,
        'trail_x': [],
        'trail_y': []
    }

    def update_anim(frame):
        # 플레이 상태일 때만 프레임을 전진시킴
        if sim_state['is_playing'] and sim_state['frame_idx'] < len(sim_state['history']) - 1:
            sim_state['frame_idx'] += 1
            
        current_idx = sim_state['frame_idx']
        theta, delta_theta = sim_state['history'][current_idx]
        
        x0, y0 = 0, 0
        x1 = L1 * math.cos(theta[0])
        y1 = L1 * math.sin(theta[0])
        x2, y2 = forward_kinematics(theta[0], theta[1])
        
        line.set_data([x0, x1, x2], [y0, y1, y2])
        
        # 궤적 업데이트 로직 (재생 중이거나 초기 상태일 때만 궤적 추가)
        if sim_state['is_playing'] or current_idx == 0:
            if current_idx == 0:
                sim_state['trail_x'], sim_state['trail_y'] = [x2], [y2]
            else:
                sim_state['trail_x'].append(x2)
                sim_state['trail_y'].append(y2)
        trail_line.set_data(sim_state['trail_x'], sim_state['trail_y'])
        
        error_dist = math.dist([x2, y2], [target_point.get_xdata()[0], target_point.get_ydata()[0]])
        
        status = (
            f"Iter: {current_idx:02d} / {len(sim_state['history'])-1}\n"
            f"Th1: {math.degrees(theta[0]):7.2f}° | d_Th1: {delta_theta[0]:.4f}\n"
            f"Th2: {math.degrees(theta[1]):7.2f}° | d_Th2: {delta_theta[1]:.4f}\n"
            f"Error: {error_dist:.4f} m\n"
            f"Status: {'PLAYING' if sim_state['is_playing'] else 'PAUSED'}"
        )
        text_info.set_text(status)
        return line, trail_line, target_point, text_info

    # --- UI 컨트롤 (슬라이더) 설정 ---
    axcolor = 'lightgoldenrodyellow'
    ax_tx  = plt.axes([0.15, 0.20, 0.65, 0.03], facecolor=axcolor)
    ax_ty  = plt.axes([0.15, 0.15, 0.65, 0.03], facecolor=axcolor)
    ax_th1 = plt.axes([0.15, 0.10, 0.65, 0.03], facecolor=axcolor)
    ax_th2 = plt.axes([0.15, 0.05, 0.65, 0.03], facecolor=axcolor)

    # 슬라이더 객체 생성
    s_tx = Slider(ax_tx, 'Target X', -1.0, 1.0, valinit=init_target[0])
    s_ty = Slider(ax_ty, 'Target Y', -1.0, 1.0, valinit=init_target[1])
    s_th1 = Slider(ax_th1, 'Init Th1 (rad)', -math.pi, math.pi, valinit=init_theta[0])
    s_th2 = Slider(ax_th2, 'Init Th2 (rad)', -math.pi, math.pi, valinit=init_theta[1])

    def on_slider_change(val):
        """슬라이더 값 변경 시 시뮬레이션을 초기화하고 경로를 재계산합니다."""
        tx, ty = s_tx.val, s_ty.val
        th1, th2 = s_th1.val, s_th2.val
        
        target_point.set_data([tx], [ty])
        sim_state['history'] = inverse_kinematics_numerical(tx, ty, th1, th2)
        sim_state['frame_idx'] = 0
        sim_state['is_playing'] = False # 변경 시 다시 정지 상태로 진입
        sim_state['trail_x'].clear()
        sim_state['trail_y'].clear()
        fig.canvas.draw_idle()

    # 슬라이더 이벤트 연결
    s_tx.on_changed(on_slider_change)
    s_ty.on_changed(on_slider_change)
    s_th1.on_changed(on_slider_change)
    s_th2.on_changed(on_slider_change)

    # --- 키보드 이벤트 (스페이스바 토글) ---
    def on_key_press(event):
        if event.key == ' ':
            # 재생이 끝난 상태에서 스페이스바를 누르면 처음부터 다시 재생
            if sim_state['frame_idx'] >= len(sim_state['history']) - 1:
                sim_state['frame_idx'] = 0
                sim_state['trail_x'].clear()
                sim_state['trail_y'].clear()
            
            sim_state['is_playing'] = not sim_state['is_playing']
            fig.canvas.draw_idle()

    fig.canvas.mpl_connect('key_press_event', on_key_press)

    # frames=200 은 중요하지 않음 (내부 루프에서 인덱스를 자체 관리하므로)
    ani = animation.FuncAnimation(fig, update_anim, interval=100, blit=False, cache_frame_data=False)
    
    plt.show()