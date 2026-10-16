#!/usr/bin/env python3
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider

# 1. 카메라 내부 파라미터 고정 (ROS2 실습 환경과 일치)
fx, fy = 554.25, 554.25
cx, cy = 320.0, 240.0

# 2. 메인 그래픽스 창 설정
fig = plt.figure(figsize=(12, 8))
ax = fig.add_subplot(111, projection='3d')
plt.subplots_adjust(bottom=0.35)  # 슬라이더 공간 확보

# 초기 파라미터 설정
init_z0 = 0.6       # 카메라 높이 (m)
init_pitch = 20.0   # 카메라 다운 피치 각도 (degrees)
init_u = 320.0      # 화면 정중앙 픽셀
init_v = 340.0      # 중앙보다 약간 아래쪽 픽셀 (바닥을 바라보도록 설정)

# 3. Matplotlib 슬라이더 GUI 배치
ax_z0    = plt.axes([0.15, 0.22, 0.65, 0.03])
ax_pitch = plt.axes([0.15, 0.16, 0.65, 0.03])
ax_u     = plt.axes([0.15, 0.10, 0.65, 0.03])
ax_v     = plt.axes([0.15, 0.04, 0.65, 0.03])

s_z0    = Slider(ax_z0,    'Cam Height (z0) [m]', 0.1, 2.0, valinit=init_z0)
s_pitch = Slider(ax_pitch, 'Cam Pitch [deg]',    -45.0, 60.0, valinit=init_pitch)
s_u     = Slider(ax_u,     'Pixel U (X-axis)',   0.0, 640.0, valinit=init_u)
s_v     = Slider(ax_v,     'Pixel V (Y-axis)',   0.0, 480.0, valinit=init_v)

def update(val):
    # 슬라이더로부터 현재 시뮬레이터 변수 읽기
    z0 = s_z0.val
    pitch_deg = s_pitch.val
    u = s_u.val
    v = s_v.val

    theta = np.radians(pitch_deg)

    # [Step 1] 핀홀 카메라 모델: 픽셀을 카메라 광학 프레임 기준 3D 방향 벡터(v_c)로 복원
    xc = (u - cx) / fx
    yc = (v - cy) / fy
    zc = 1.0
    v_c = np.array([xc, yc, zc])

    # [Step 2] 외적 파라미터 변환 행렬 구성 (Optical Frame -> Base Link)
    # 기본 변환(Pitch=0일 때): Z_opt -> X_base, X_opt -> -Y_base, Y_opt -> -Z_base
    # 여기에 카메라가 바닥을 향해 숙이는 Pitch 변환 결합
    R = np.array([
        [0, -np.sin(theta),  np.cos(theta)],
        [-1,             0,              0],
        [0, -np.cos(theta), -np.sin(theta)]
    ])
    
    # 로봇 중심 대비 카메라 정적 설치 위치 (X=0, Y=0에 장착되었다고 가정)
    P_cam = np.array([0.0, 0.0, z0])

    # 카메라 벡터를 로봇 기준 벡터(v_b)로 회전 유도
    v_b = np.dot(R, v_c)

    # 3D 뷰포트 초기화 및 고정 뷰 각도 세팅
    ax.cla()
    ax.set_xlim(-0.5, 4.0)
    ax.set_ylim(-2.0, 2.0)
    ax.set_zlim(-0.1, 2.0)
    ax.set_xlabel('X (Forward / m)')
    ax.set_ylabel('Y (Left / m)')
    ax.set_zlabel('Z (Up / m)')
    ax.set_title('2D Camera Ray-Plane Intersection Simulator', fontsize=14, fontweight='bold')

    # 바닥 지면 (Z = 0) 그리드 시각화
    grid_x, grid_y = np.meshgrid(np.linspace(-0.5, 4.0, 15), np.linspace(-2.0, 2.0, 15))
    grid_z = np.zeros_like(grid_x)
    ax.plot_wireframe(grid_x, grid_y, grid_z, color='lightgray', alpha=0.5, linewidth=0.5)

    # 카메라 원점 플롯
    ax.scatter(P_cam[0], P_cam[1], P_cam[2], color='blue', s=120, zorder=5, label='Camera Center')

    # [Step 3] 지면 교점(Ray-Plane Intersection) 방정식 연산
    if v_b[2] < 0:  # 벡터가 지면(아래쪽)을 향할 때만 교점 존재
        # 직선 방정식 스케일 팩터 t 계산: t = -z0 / v_z
        t = -z0 / v_b[2]
        
        # 교점 복원: P = P_cam + t * v_b
        P_intersect = P_cam + t * v_b

        # 시각화 데이터 플롯 (광선 및 바닥 교차점)
        ax.plot([P_cam[0], P_intersect[0]], [P_cam[1], P_intersect[1]], [P_cam[2], P_intersect[2]], 
                color='darkorange', linewidth=2.5, linestyle='-', label='Projection Ray')
        ax.scatter(P_intersect[0], P_intersect[1], P_intersect[2], 
                   color='red', s=200, marker='*', zorder=6, label='Estimated 3D Target')

        # 계산된 3D 좌표 실시간 텍스트 출력
        info_text = f"Estimated 3D Coord:\nX = {P_intersect[0]:.3f}m\nY = {P_intersect[1]:.3f}m\nZ = 0.000m (Ground)"
        ax.text(P_intersect[0], P_intersect[1], P_intersect[2] + 0.15, info_text, 
                color='black', weight='bold', bbox=dict(facecolor='white', alpha=0.8, boxstyle='round,pad=0.5'))
    else:
        # 광선이 하늘을 향해 평면과 만나지 않는 경우 예외 처리 시각화
        P_end = P_cam + 2.0 * v_b
        ax.plot([P_cam[0], P_end[0]], [P_cam[1], P_end[1]], [P_cam[2], P_end[2]], 
                color='black', linewidth=2, linestyle='--', label='Ray (No Intersection)')
        ax.text(0, 0, z0 + 0.2, "Error: Ray points upward!", color='purple', weight='bold')

    ax.legend(loc='upper right')
    fig.canvas.draw_idle()

# 슬라이더 값 변경 시 대화형 이벤트 트리거 연동
s_z0.on_changed(update)
s_pitch.on_changed(update)
s_u.on_changed(update)
s_v.on_changed(update)

# 첫 화면 렌더링 초기화 실행
update(None)
plt.show()
