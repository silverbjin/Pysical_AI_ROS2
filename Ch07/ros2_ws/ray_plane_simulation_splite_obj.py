#!/usr/bin/env python3
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider

# 1. 카메라 내부 파라미터 (ROS2 실습 환경 표준)
fx, fy = 554.25, 554.25
cx, cy = 320.0, 240.0
img_w, img_h = 640, 480

# 2. 멀티 플롯 창 설정 (좌: 3D 물리 공간, 우: 2D 카메라 뷰파인더)
fig = plt.figure(figsize=(15, 8))
ax3d = fig.add_subplot(121, projection='3d')
ax2d = fig.add_subplot(122)

# 슬라이더 5개를 배치하기 위해 하단 여백을 충분히 확보
plt.subplots_adjust(bottom=0.38, wspace=0.25)

# 초기 파라미터 설정
init_z0 = 0.7       # 카메라 설치 높이 (m)
init_pitch = 25.0   # 카메라 다운 피치 각도 (degrees)
init_obj_x = 2.0    # 물체의 실제 X 위치 (앞뒤)
init_obj_y = 0.0    # 물체의 실제 Y 위치 (좌우)
init_obj_z = 0.0    # 물체의 실제 Z 위치 (높이 -> 0이면 지면)

# 3. GUI 슬라이더 세팅 (위치 및 범위 정의)
ax_z0    = plt.axes([0.15, 0.30, 0.70, 0.02])
ax_pitch = plt.axes([0.15, 0.24, 0.70, 0.02])
ax_x     = plt.axes([0.15, 0.18, 0.70, 0.02])
ax_y     = plt.axes([0.15, 0.12, 0.70, 0.02])
ax_z     = plt.axes([0.15, 0.06, 0.70, 0.02])

s_z0    = Slider(ax_z0,    'Cam Height (z0) [m]', 0.1, 2.0, valinit=init_z0)
s_pitch = Slider(ax_pitch, 'Cam Pitch [deg]',    -10.0, 60.0, valinit=init_pitch)
s_x     = Slider(ax_x,     'Object X (Forward)',  0.5, 4.0, valinit=init_obj_x)
s_y     = Slider(ax_y,     'Object Y (Left/Right)', -2.0, 2.0, valinit=init_obj_y)
s_z     = Slider(ax_z,     'Object Z (Altitude)', 0.0, 1.0, valinit=init_obj_z)

def update(val):
    # 슬라이더 변수 실시간 로드
    z0 = s_z0.val
    pitch_deg = s_pitch.val
    obj_x = s_x.val
    obj_y = s_y.val
    obj_z = s_z.val

    theta = np.radians(pitch_deg)

    # 매 프레임 화면 초기화
    ax3d.cla()
    ax2d.cla()

    # ==========================================================
    # CORE MATH 1: 3D 물체 -> 2D 픽셀 투영 (Forward Projection)
    # ==========================================================
    P_obj_base = np.array([obj_x, obj_y, obj_z]) # 실제 물체 고유 좌표
    P_cam_base = np.array([0.0, 0.0, z0])         # 카메라 원점 위치

    # Camera Optical -> Base Link 변환 행렬 (R_cam_to_base)
    R_c2b = np.array([
        [0, -np.sin(theta),  np.cos(theta)],
        [-1,             0,              0],
        [0, -np.cos(theta), -np.sin(theta)]
    ])
    # 역변환을 위한 Base Link -> Camera Optical 변환 행렬 (R_base_to_camera = R_c2b의 전치행렬)
    R_b2c = R_c2b.T

    # 로봇 기준 물체 벡터를 카메라 광학 좌표계 기준으로 변환
    v_obj_base = P_obj_base - P_cam_base
    v_obj_cam = np.dot(R_b2c, v_obj_base)

    # 핀홀 카메라 평면 투영 가능 여부 검사 (카메라 전방에 있는지 확인)
    is_front = v_obj_cam[2] > 0.1
    u, v = -1.0, -1.0

    if is_front:
        # 3D 좌표 -> 2D 픽셀 좌표 변환
        u = fx * (v_obj_cam[0] / v_obj_cam[2]) + cx
        v = fy * (v_obj_cam[1] / v_obj_cam[2]) + cy

    # ==========================================================
    # CORE MATH 2: 2D 픽셀 -> 지면 교점 역추적 (Ray-Plane Intersection)
    # ==========================================================
    estimated_success = False
    P_est_base = np.zeros(3)

    if is_front and (0 <= u <= img_w) and (0 <= v <= img_h):
        # 2D 픽셀 단위 벡터화
        xc = (u - cx) / fx
        yc = (v - cy) / fy
        zc = 1.0
        v_c = np.array([xc, yc, zc])
        
        # 로봇 좌표계 기준 방향 벡터로 변환
        v_b = np.dot(R_c2b, v_c)

        # 광선이 아래(지면)를 향하는 경우 교점 연산
        if v_b[2] < 0:
            t = -z0 / v_b[2]
            P_est_base = P_cam_base + t * v_b
            estimated_success = True

    # ==========================================================
    # VISUALIZATION: 좌측 3D 물리 공간 그리기
    # ==========================================================
    ax3d.set_xlim(-0.5, 4.0)
    ax3d.set_ylim(-2.0, 2.0)
    ax3d.set_zlim(-0.1, 2.0)
    ax3d.set_xlabel('X (Forward / m)')
    ax3d.set_ylabel('Y (Left / m)')
    ax3d.set_zlabel('Z (Up / m)')
    ax3d.set_title('3D Physical Robot Space', fontsize=12, fontweight='bold')

    # 지면 그리드 (Z=0)
    grid_x, grid_y = np.meshgrid(np.linspace(-0.5, 4.0, 15), np.linspace(-2.0, 2.0, 15))
    ax3d.plot_wireframe(grid_x, grid_y, np.zeros_like(grid_x), color='lightgray', alpha=0.4, linewidth=0.5)

    # 카메라 원점 표시
    ax3d.scatter(P_cam_base[0], P_cam_base[1], P_cam_base[2], color='blue', s=100, zorder=5, label='Camera Origin')

    # 가상 이미지 가이드 스크린 표시 (초점거리 0.3m 지점)
    f_disp = 0.3
    corners_c = np.array([
        [(0 - cx)/fx, (0 - cy)/fy, 1.0], [(img_w - cx)/fx, (0 - cy)/fy, 1.0],
        [(img_w - cx)/fx, (img_h - cy)/fy, 1.0], [(0 - cx)/fx, (img_h - cy)/fy, 1.0],
        [(0 - cx)/fx, (0 - cy)/fy, 1.0]
    ]) * f_disp
    corners_b = np.array([P_cam_base + np.dot(R_c2b, c) for c in corners_c])
    ax3d.plot(corners_b[:, 0], corners_b[:, 1], corners_b[:, 2], color='teal', linewidth=1.2, alpha=0.7, label='Virtual Screen')

    # 실제 물리 물체 (Green Ball)
    ax3d.scatter(P_obj_base[0], P_obj_base[1], P_obj_base[2], color='green', s=120, marker='o', zorder=7, label='True Object')
    
    # 공중에 떠 있는 경우 수직 보조선 추가
    if obj_z > 0:
        ax3d.plot([obj_x, obj_x], [obj_y, obj_y], [0, obj_z], color='green', linestyle=':', linewidth=1.5)

    # 알고리즘 역추적 결과 투영 (Red Star)
    if estimated_success:
        ax3d.plot([P_cam_base[0], P_est_base[0]], [P_cam_base[1], P_est_base[1]], [P_cam_base[2], P_est_base[2]], 
                  color='darkorange', linewidth=2, linestyle='-', alpha=0.8, label='Algorithm Ray')
        ax3d.scatter(P_est_base[0], P_est_base[1], P_est_base[2], color='red', s=180, marker='*', zorder=6, label='Estimated Target (Z=0)')
        
        # 오차가 존재할 경우 두 물체 간 변위선 연결
        if obj_z > 0:
            ax3d.plot([P_obj_base[0], P_est_base[0]], [P_obj_base[1], P_est_base[1]], [P_obj_base[2], P_est_base[2]], 
                      color='red', linestyle='--', linewidth=1.5, label='Localization Error')

        # 3D 텍스트 리포트
        info_3d = f"True: ({obj_x:.2f}, {obj_y:.2f}, {obj_z:.2f})\nEst : ({P_est_base[0]:.2f}, {P_est_base[1]:.2f}, 0.00)"
        ax3d.text(P_obj_base[0], P_obj_base[1], P_obj_base[2] + 0.15, info_3d, color='black', fontsize=8, weight='bold')

    ax3d.legend(loc='upper right', fontsize=8)

    # ==========================================================
    # VISUALIZATION: 우측 2D 카메라 뷰파인더 그리기
    # ==========================================================
    ax2d.set_xlim(0, img_w)
    ax2d.set_ylim(img_h, 0) # OpenCV 이미지 좌표계 동기화 (Y축 반전)
    ax2d.set_xlabel('U (Pixel X)')
    ax2d.set_ylabel('V (Pixel Y)')
    ax2d.grid(True, linestyle=':', color='gray', alpha=0.5)

    # 카메라 주점 가이드라인
    ax2d.axhline(cy, color='blue', linestyle='--', linewidth=0.7, alpha=0.4)
    ax2d.axvline(cx, color='blue', linestyle='--', linewidth=0.7, alpha=0.4)

    if is_front and (0 <= u <= img_w) and (0 <= v <= img_h):
        ax2d.set_title('2D Camera Viewfinder (Object In-Sight)', fontsize=12, fontweight='bold')
        # 센서에 맺힌 상 시각화
        ax2d.scatter(u, v, color='red', s=100, marker='P', label='Projected Feature')
        box_size = 32
        rect = plt.Rectangle((u - box_size/2, v - box_size/2), box_size, box_size, fill=False, color='lime', linewidth=1.5, label='Bounding Box')
        ax2d.add_patch(rect)
        ax2d.text(u + 20, v - 20, f"({int(u)}, {int(v)})", color='red', weight='bold', fontsize=9)
    else:
        ax2d.set_title('2D Camera Viewfinder (OUT OF SIGHT ⚠️)', fontsize=12, fontweight='bold', color='purple')
        ax2d.text(img_w/2, img_h/2, "Object Out of Camera FOV", color='purple', weight='bold', ha='center', va='center', bbox=dict(facecolor='white', alpha=0.8))

    ax2d.legend(loc='lower right', fontsize=8)
    fig.canvas.draw_idle()

# 슬라이더 동기화 이벤트 바인딩
s_z0.on_changed(update)
s_pitch.on_changed(update)
s_x.on_changed(update)
s_y.on_changed(update)
s_z.on_changed(update)

# 최초 렌더링 호출
update(None)
plt.show()
