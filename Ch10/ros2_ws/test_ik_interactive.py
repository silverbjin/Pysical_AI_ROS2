#!/usr/bin/env python3
import os
import sys
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, Button

import matplotlib.font_manager as fm

# --- [추가] OS별 한글 폰트 설정 및 깨짐 방지 ---
plt.rcParams['axes.unicode_minus'] = False  # 유니코드 마이너스 대신 일반 하이픈 사용 강제
plt.rcParams['mathtext.fontset'] = 'cm'     # 수학 텍스트 렌더러를 Computer Modern(표준)으로 고정
# 시스템에 나눔 폰트나 맑은 고딕이 있는지 확인 후 적용
font_candidates = ['NanumGothic', 'Malgun Gothic', 'AppleGothic', 'Noto Sans CJK KR']
font_name = "DejaVu Sans" # 기본 Fallback

for fc in font_candidates:
    if any(fc in f.name for f in fm.fontManager.ttflist):
        font_name = fc
        plt.rcParams['font.family'] = font_name
        break

# --- [경로 제약 조건 반영] ---
package_parent_path = os.path.join(os.path.dirname(__file__), 'src', 'my_quadruped_bot')
if package_parent_path not in sys.path:
    sys.path.append(package_parent_path)

from my_quadruped_bot.inverse_kinematics import InverseKinematics
# ------------------------------

def forward_kinematics(q: np.ndarray, l1: float, l2: float, l3: float) -> list:
    """관절 각도와 링크 길이를 기반으로 각 관절의 3D 좌표를 계산 (FK)"""
    q1, q2, q3 = q
    
    # 2D 지역 평면(X-Z') 좌표 연산
    x_hip, z_prime_hip = 0.0, 0.0
    x_knee = l2 * np.sin(q2)
    z_prime_knee = -l2 * np.cos(q2)
    x_foot = x_knee + l3 * np.sin(q2 + q3)
    z_prime_foot = z_prime_knee - l3 * np.cos(q2 + q3)

    # 3D 전역 좌표계로 투영
    p_origin = np.array([0.0, 0.0, 0.0])
    p_hip = np.array([x_hip, l1 * np.cos(q1) - z_prime_hip * np.sin(q1), l1 * np.sin(q1) + z_prime_hip * np.cos(q1)])
    p_knee = np.array([x_knee, l1 * np.cos(q1) - z_prime_knee * np.sin(q1), l1 * np.sin(q1) + z_prime_knee * np.cos(q1)])
    p_foot = np.array([x_foot, l1 * np.cos(q1) - z_prime_foot * np.sin(q1), l1 * np.sin(q1) + z_prime_foot * np.cos(q1)])

    return [p_origin, p_hip, p_knee, p_foot]

def launch_interactive_ik():
    # 초기 기구학 파라미터 및 목표점 정의
    init_l1, init_l2, init_l3 = 0.05, 0.20, 0.20
    init_x, init_y, init_z = 0.0, 0.05, -0.30
    
    ik_solver = InverseKinematics()
    
    # 메인 그래픽스 레이아웃 분할 (좌측: 3D 플롯, 하단/우측: 슬라이더)
    fig = plt.figure(figsize=(12, 8))
    plt.subplots_adjust(left=0.05, bottom=0.35, right=0.75, top=0.9)
    ax = fig.add_subplot(111, projection='3d')
    
    # 슬라이더 생성을 위한 캔버스 영역 축(Axes) 배치
    ax_x = plt.axes([0.15, 0.22, 0.50, 0.03])
    ax_y = plt.axes([0.15, 0.17, 0.50, 0.03])
    ax_z = plt.axes([0.15, 0.12, 0.50, 0.03])
    
    ax_l1 = plt.axes([0.80, 0.65, 0.15, 0.03])
    ax_l2 = plt.axes([0.80, 0.55, 0.15, 0.03])
    ax_l3 = plt.axes([0.80, 0.45, 0.15, 0.03])
    
    # UI 슬라이더 위젯 객체 매핑
    sl_x = Slider(ax_x, 'Target X (m)', -0.25, 0.25, valinit=init_x, valstep=0.01)
    sl_y = Slider(ax_y, 'Target Y (m)', -0.15, 0.15, valinit=init_y, valstep=0.01)
    sl_z = Slider(ax_z, 'Target Z (m)', -0.45, -0.05, valinit=init_z, valstep=0.01)
    
    sl_l1 = Slider(ax_l1, 'Link l1 (Hip)', 0.02, 0.10, valinit=init_l1, valstep=0.005)
    sl_l2 = Slider(ax_l2, 'Link l2 (Thigh)', 0.10, 0.30, valinit=init_l2, valstep=0.01)
    sl_l3 = Slider(ax_l3, 'Link l3 (Calf)', 0.10, 0.30, valinit=init_l3, valstep=0.01)

    # 실시간 텍스트 출력을 위한 피드백 박스 지정
    text_box = fig.text(0.78, 0.75, "", fontsize=10, bbox=dict(facecolor='white', alpha=0.8, boxstyle='round'))

    def update(val):
        ax.clear() # 이전 뼈대 잔상 제거
        
        # 1. 제원 및 목표 좌표 동적 수집
        l1 = sl_l1.val
        l2 = sl_l2.val
        l3 = sl_l3.val
        tx, ty, tz = sl_x.val, sl_y.val, sl_z.val
        
        # IK 인스턴스 파라미터 업데이트
        ik_solver.l1, ik_solver.l2, ik_solver.l3 = l1, l2, l3
        
        # 2. 역운동학 수식 연산 수행
        q_sol = ik_solver.solve(tx, ty, tz, is_right_leg=False)
        
        
        is_korean_available = plt.rcParams['font.family'][0] != "DejaVu Sans"
        
        if q_sol is not None:
            # 수식이 성립하는 정상 작업 공간 내부
            sk_arr = np.array(forward_kinematics(q_sol, l1, l2, l3))
            
            # 다리 Skeleton 및 목표 포인트 플로팅
            ax.plot(sk_arr[:,0], sk_arr[:,1], sk_arr[:,2], marker='o', markersize=7, linewidth=4, color='#1f77b4', label='Leg Mechanism')
            ax.scatter([tx], [ty], [tz], color='red', s=100, zorder=5, label='Target [X,Y,Z]')
            
            # 관절 노드 네이밍 표시
            names = ['Hip Base', 'Thigh Joint', 'Knee Joint', 'Foot End']
            for idx, txt in enumerate(names):
                ax.text(sk_arr[idx,0], sk_arr[idx,1], sk_arr[idx,2]+0.01, f' {txt}', fontsize=8)
            
            status_text = "상태: [O] 해 존재" if is_korean_available else "Status: [O] Valid IK"
            # 우측 수식 연산 피드백 텍스트 정보 갱신
            info_str = (f" [Joint Angles Solution]\n"
                        f" -----------------------\n"
                        f"  q1 (Roll)  : {np.degrees(q_sol[0]):6.2f}°\n"
                        f"  q2 (Pitch) : {np.degrees(q_sol[1]):6.2f}°\n"
                        f"  q3 (Knee)  : {np.degrees(q_sol[2]):6.2f}°\n"
                        f" -----------------------\n"
                        # f" 상태: ✅ 해 존재 (Valid IK)")
                        f" {status_text}")
        else:
            status_text = "상태: [X] 도달 불가" if is_korean_available else "Status: [X] Domain Error"
            # 특이점 또는 작업 공간 바깥(Unreachable) 영역 진입 시 예외 시각화
            ax.scatter([tx], [ty], [tz], color='purple', marker='X', s=150, zorder=5, label='Singularity / Out of Workspace')
            info_str = (f" [Joint Angles Solution]\n"
                        f" -----------------------\n"
                        f"  q1 (Roll)  :  NaN\n"
                        f"  q2 (Pitch) :  NaN\n"
                        f"  q3 (Knee)  :  NaN\n"
                        f" -----------------------\n"
                        # f" 상태: ❌ 도달 불가 (Domain Error)")
                        f" {status_text}")
            
        text_box.set_text(info_str)
        
        # 3D 축 한계 고정 및 환경 세팅 (왜곡 방지)
        ax.set_xlim(-0.3, 0.3)
        ax.set_ylim(-0.2, 0.4)
        ax.set_zlim(-0.5, 0.0)
        ax.set_xlabel('X (Forward/Backward)')
        ax.set_ylabel('Y (Lateral Offset)')
        ax.set_zlabel('Z (Height)')
        ax.set_title('Interactive Leg Inverse Kinematics Simulator', fontsize=14, fontweight='bold')
        ax.grid(True, linestyle=':', alpha=0.5)
        ax.legend(loc='upper left')
        fig.canvas.draw_idle()

    # 모든 슬라이더 조작 이벤트에 전역 업데이트 함수 등록
    for slider in [sl_x, sl_y, sl_z, sl_l1, sl_l2, sl_l3]:
        slider.on_changed(update)

    # 초기 화면 렌더링 호출
    update(None)
    plt.show()

if __name__ == "__main__":
    launch_interactive_ik()