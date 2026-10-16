import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.widgets import Slider, Button

class Planar2DOF:
    def __init__(self, l1=1.0, l2=1.0):
        self.l1 = l1
        self.l2 = l2

    def forward_kinematics(self, theta):
        th1, th2 = theta
        x1 = self.l1 * np.cos(th1)
        y1 = self.l1 * np.sin(th1)
        x2 = x1 + self.l2 * np.cos(th1 + th2)
        y2 = y1 + self.l2 * np.sin(th1 + th2)
        return np.array([x1, y1]), np.array([x2, y2])

    def jacobian(self, theta):
        th1, th2 = theta
        j11 = -self.l1 * np.sin(th1) - self.l2 * np.sin(th1 + th2)
        j12 = -self.l2 * np.sin(th1 + th2)
        j21 =  self.l1 * np.cos(th1) + self.l2 * np.cos(th1 + th2)
        j22 =  self.l2 * np.cos(th1 + th2)
        return np.array([[j11, j12], [j21, j22]])

    def inverse_kinematics_history(self, target, theta_init, alpha=1.0, tol=1e-3, max_iter=40):
        theta = np.array(theta_init, dtype=float)
        history = [theta.copy()]
        status = "Max Iteration Reached"
        
        for i in range(max_iter):
            _, end_pos = self.forward_kinematics(theta)
            error = target - end_pos
            error_norm = np.linalg.norm(error)
            
            if error_norm < tol:
                status = f"Converged ({i} iters)"
                break
                
            J = self.jacobian(theta)
            det_J = np.linalg.det(J)
            
            if abs(det_J) < 1e-4:
                status = "Divergence (Singularity!)"
                break
                
            J_inv = np.linalg.inv(J)
            delta_theta = J_inv @ error
            
            # 수치 폭발 시, 폭발하는 최종 단계까지 history에 넣어 시각화한 뒤 브레이크
            if np.linalg.norm(delta_theta) > 5.0:
                status = "Divergence (Explosion!)"
                exploded_theta = theta + alpha * delta_theta
                history.append(exploded_theta.copy())
                break
                
            theta = theta + alpha * delta_theta
            history.append(theta.copy())
            
        return history, status

# ====================================================
# 🎨 Matplotlib 창 설정 및 작화 요소(전역 상태) 초기화
# ====================================================
fig, ax = plt.subplots(figsize=(8, 8))
plt.subplots_adjust(bottom=0.38)

L1, L2 = 1.0, 1.0
robot = Planar2DOF(L1, L2)

# 전역 상태 제어 변수들
current_theta = np.array([0.0, np.radians(90)]) 
rollback_theta = current_theta.copy() # ⭐ 발산 시 되돌아갈 세이브 포인트
updating_sliders = False  

ax.set_xlim(-2.3, 2.3)
ax.set_ylim(-2.3, 2.3)
ax.set_aspect('equal')
ax.grid(True, linestyle='--', alpha=0.5)
status_text = ax.text(-2.1, 2.0, "Status: Ready", fontsize=12, fontweight='bold', color='black')

arm_line, = ax.plot([], [], 'o-', lw=5, markersize=9, color='#2c3e50', zorder=3)
target_point, = ax.plot([], [], 'r*', markersize=14, zorder=4, label='Target')
trail_line, = ax.plot([], [], 'g--', lw=1.5, alpha=0.7, zorder=2)

trail_x, trail_y = [], []
ani = None
history = []

# ==========================================
# 🎛️ UI 컨트롤 배치 / 버튼 배치
# ==========================================
ax_color = 'lightgoldenrodyellow'
ax_tx    = plt.axes([0.2, 0.28, 0.6, 0.02], facecolor=ax_color)
ax_ty    = plt.axes([0.2, 0.24, 0.6, 0.02], facecolor=ax_color)
ax_th1   = plt.axes([0.2, 0.20, 0.6, 0.02], facecolor=ax_color)
ax_th2   = plt.axes([0.2, 0.16, 0.6, 0.02], facecolor=ax_color)
ax_alpha = plt.axes([0.2, 0.12, 0.6, 0.02], facecolor=ax_color)

s_tx    = Slider(ax_tx, 'Target X', -2.2, 2.2, valinit=1.0, valfmt='%.2f')
s_ty    = Slider(ax_ty, 'Target Y', -2.2, 2.2, valinit=1.0, valfmt='%.2f')
s_th1   = Slider(ax_th1, 'Init Th1', -180.0, 180.0, valinit=0.0, valfmt='%.1f deg')
s_th2   = Slider(ax_th2, 'Init Th2', -180.0, 180.0, valinit=90.0, valfmt='%.1f deg')
s_alpha = Slider(ax_alpha, 'Alpha', 0.01, 2.0, valinit=0.5, valfmt='%.2f')

# 버튼 2개 배치 (Run Animation / Reset All)
ax_btn_run = plt.axes([0.25, 0.03, 0.22, 0.04])
ax_btn_rst = plt.axes([0.53, 0.03, 0.22, 0.04])
btn_run    = Button(ax_btn_run, 'Run Animation', color='#2ecc71', hovercolor='#27ae60')
btn_reset  = Button(ax_btn_rst, 'Reset Simulator', color='#e74c3c', hovercolor='#c0392b')

# ==========================================
# 🔄 실시간 렌더링, 애니메이션, 인터랙션 내부 로직
# ==========================================
def update_anim(frame):
    """애니메이션 프레임 업데이트 및 종료 시 상태 제어"""
    global current_theta, updating_sliders
    
    theta = history[frame]
    joint_pos, end_pos = robot.forward_kinematics(theta)
    arm_line.set_data([0, joint_pos[0], end_pos[0]], [0, joint_pos[1], end_pos[1]])
    
    trail_x.append(end_pos[0])
    trail_y.append(end_pos[1])
    trail_line.set_data(trail_x, trail_y)
    
    # 마지막 프레임 처리 : 수렴/발산 여부에 따른 상태 저장 및 슬라이더 동기화
    if frame == len(history) - 1:
        if "Converged" in final_status:
            # 성공했다면 이 위치를 다음 주행의 시작점으로 저장
            current_theta = theta.copy()
        else:
            # ⭐ 핵심: 발산/실패했다면 튕겨나간 연산을 보여준 뒤, 안전했던 이전 각도로 강제 롤백!
            current_theta = rollback_theta.copy()
            status_text.set_text(f"{final_status}\n[Rollback to Safe Posture]")
        
        # 슬라이더 값 동기화
        updating_sliders = True
        s_th1.set_val(np.degrees(current_theta[0]))
        s_th2.set_val(np.degrees(current_theta[1]))
        updating_sliders = False
        
    return arm_line, trail_line

def reset_view(val):
    """사용자가 슬라이더를 마우스로 조작할 때 뷰 갱신"""
    global current_theta, ani, trail_x, trail_y
    
    # 코드가 슬라이더를 강제 동기화하는 중이라면 뷰 리셋 연산을 건너뜀 (에러 및 루프 방지)
    if updating_sliders:
        return
    
    # 진행 중인 애니메이션 강제 종료
    if ani is not None and ani.event_source is not None:
        ani.event_source.stop()
    
    # 타겟 위치 즉시 갱신    
    target_point.set_data([s_tx.val], [s_ty.val])
    current_theta = np.array([np.radians(s_th1.val), np.radians(s_th2.val)])
    
    # 로봇 팔 초기 위치 즉시 갱신
    joint_pos, end_pos = robot.forward_kinematics(current_theta)
    arm_line.set_data([0, joint_pos[0], end_pos[0]], [0, joint_pos[1], end_pos[1]])
    
    # 궤적 및 텍스트 초기화
    trail_x, trail_y = [], []
    trail_line.set_data([], [])
    status_text.set_text("Status: Ready (Press Run)")
    status_text.set_color('black')
    fig.canvas.draw_idle()

# 모든 슬라이더 조작을 하나의 리셋 핸들러에 묶음으로 
# 슬라이더가 조작될 때마다 실시간으로 화면 리셋 (인터랙티브 핵심)
s_tx.on_changed(reset_view)
s_ty.on_changed(reset_view)
s_th1.on_changed(reset_view)
s_th2.on_changed(reset_view)

def start_simulation(event):
    """[Run Animation] 버튼 클릭 시 수치해석 연산 및 궤적 애니메이션 시작"""
    global history, final_status, ani, trail_x, trail_y, rollback_theta
    
    if ani is not None and ani.event_source is not None:
        ani.event_source.stop()
        
    target_pos = np.array([s_tx.val, s_ty.val])
    alpha_val = s_alpha.val
    
    # ⭐ 이번 실행이 실패할 경우를 대비해 출발 전 위치를 세이브포인트에 저장
    rollback_theta = current_theta.copy()
    
    # 수치해석 구동
    # ⭐ 슬라이더를 만졌든, 이전 연산에서 멈췄든 항상 최신의 current_theta를 시작점으로 사용
    history, final_status = robot.inverse_kinematics_history(
        target_pos, current_theta, alpha=alpha_val
    )
    
    # 상태 텍스트 색상 변경
    status_text.set_text(f"Status: {final_status}")
    status_text.set_color('#27ae60' if "Converged" in final_status else '#c0392b')
    
    # blit=False 로 설정하여 모든 UI 요소의 갱신을 보장합니다.    
    trail_x, trail_y = [], []
    ani = FuncAnimation(
        fig, update_anim, frames=len(history),
        blit=False, interval=100, repeat=False
    )
    fig.canvas.draw_idle()

def emergency_reset(event):
    """⭐ 전체 시스템을 초기 청정 상태로 완전히 되돌리는 마스터 리셋"""
    global current_theta, rollback_theta, ani
    if ani is not None and ani.event_source is not None:
        ani.event_source.stop()
        
    global updating_sliders
    updating_sliders = True
    s_tx.reset()
    s_ty.reset()
    s_th1.reset()
    s_th2.reset()
    s_alpha.reset()
    updating_sliders = False
    
    current_theta = np.array([0.0, np.radians(90)])
    rollback_theta = current_theta.copy()
    reset_view(None)

btn_run.on_clicked(start_simulation)
btn_reset.on_clicked(emergency_reset)

# 최초 실행
reset_view(None)

plt.show()