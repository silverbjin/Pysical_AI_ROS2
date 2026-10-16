#!/usr/bin/env python3
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider

# 1. 카메라 내부 파라미터 고정 (ROS2 실습 환경 기준)
fx, fy = 554.25, 554.25
cx, cy = 320.0, 240.0
img_w, img_h = 640, 480

# 2. 대화형 멀티 플롯 창 설정 (1행 2열 분할 구조)
fig = plt.figure(figsize=(15, 7.5))
ax3d = fig.add_subplot(121, projection='3d') # 좌측: 3D 기하학 공간
ax2d = fig.add_subplot(122)                  # 우측: 2D 카메라 뷰파인더

plt.subplots_adjust(bottom=0.28, wspace=0.25)  # 슬라이더 및 레이아웃 여백 조정

# 초기 상태 파라미터 세팅
init_z0 = 0.7       # 카메라 높이 (m)
init_pitch = 25.0   # 카메라 바닥 방향 기울기 각도 (degrees)
init_u = 320.0      # 객체 탐지 픽셀 U
init_v = 360.0      # 객체 탐지 픽셀 V (바닥을 향하도록 초기화)

# 3. GUI 슬라이더 배치 (하단 영역 고정)
ax_z0    = plt.axes([0.15, 0.19, 0.70, 0.025])
ax_pitch = plt.axes([0.15, 0.14, 0.70, 0.025])
ax_u     = plt.axes([0.15, 0.09, 0.70, 0.025])
ax_v     = plt.axes([0.15, 0.04, 0.70, 0.025])

s_z0    = Slider(ax_z0,    'Cam Height (z0) [m]', 0.1, 2.0, valinit=init_z0)
s_pitch = Slider(ax_pitch, 'Cam Pitch [deg]',    -30.0, 60.0, valinit=init_pitch)
s_u     = Slider(ax_u,     'Pixel U (X-axis)',   0.0, float(img_w), valinit=init_u)
s_v     = Slider(ax_v,     'Pixel V (Y-axis)',   0.0, float(img_h), valinit=init_v)

def update(val):
    # 슬라이더 값 동적 수집
    z0 = s_z0.val
    pitch_deg = s_pitch.val
    u = s_u.val
    v = s_v.val

    theta = np.radians(pitch_deg)

    # 양방향 Ax 캔버스 초기화
    ax3d.cla()
    ax2d.cla()

    # ==========================================
    # CORE LOGIC: 기하 연산 파트
    # ==========================================
    # 1. 2D 픽셀 -> 카메라 광학 3D 방향 벡터(v_c) 변환
    xc = (u - cx) / fx
    yc = (v - cy) / fy
    zc = 1.0
    v_c = np.array([xc, yc, zc])

    # 2. Camera Optical Frame -> Base Link 회전 행렬 구성
    R = np.array([
        [0, -np.sin(theta),  np.cos(theta)],
        [-1,             0,              0],
        [0, -np.cos(theta), -np.sin(theta)]
    ])
    P_cam = np.array([0.0, 0.0, z0]) # 카메라 설치 원점 위치

    # 로봇 중심 좌표계 기준 방향 벡터 변환
    v_b = np.dot(R, v_c)

    # ==========================================
    # LEFT SCREEN: 좌측 3D 공간 시각화 구문
    # ==========================================
    ax3d.set_xlim(-0.5, 4.0)
    ax3d.set_ylim(-2.0, 2.0)
    ax3d.set_zlim(-0.1, 2.0)
    ax3d.set_xlabel('X (Forward / m)')
    ax3d.set_ylabel('Y (Left / m)')
    ax3d.set_zlabel('Z (Up / m)')
    ax3d.set_title('3D Physical Robot Space', fontsize=12, fontweight='bold')

    # 바닥면(Z=0) 와이어프레임 생성
    grid_x, grid_y = np.meshgrid(np.linspace(-0.5, 4.0, 15), np.linspace(-2.0, 2.0, 15))
    ax3d.plot_wireframe(grid_x, grid_y, np.zeros_like(grid_x), color='lightgray', alpha=0.4, linewidth=0.5)

    # 카메라 물리 원점 플롯
    ax3d.scatter(P_cam[0], P_cam[1], P_cam[2], color='blue', s=100, zorder=5, label='Camera Origin')

    # [하이라이트] 3D 공간상에 2D 가상 이미지 센서 평면 그리드 투영 (초점거리 0.3m 스케일 시각화)
    f_disp = 0.3
    corners_c = np.array([
        [(0 - cx)/fx, (0 - cy)/fy, 1.0],      # Top-Left
        [(img_w - cx)/fx, (0 - cy)/fy, 1.0],  # Top-Right
        [(img_w - cx)/fx, (img_h - cy)/fy, 1.0], # Bottom-Right
        [(0 - cx)/fx, (img_h - cy)/fy, 1.0],  # Bottom-Left
        [(0 - cx)/fx, (0 - cy)/fy, 1.0]       # Loop Close
    ]) * f_disp
    
    corners_b = np.array([P_cam + np.dot(R, c) for c in corners_c])
    ax3d.plot(corners_b[:, 0], corners_b[:, 1], corners_b[:, 2], color='teal', linewidth=1.5, label='Virtual 2D Screen')

    # 이미지 센서를 통과하는 픽셀 포인트 계산
    pixel_on_sensor = P_cam + np.dot(R, v_c * f_disp)
    ax3d.scatter(pixel_on_sensor[0], pixel_on_sensor[1], pixel_on_sensor[2], color='red', s=30, zorder=6)

    # 3. 지면 교점(Ray-Plane Intersection) 수학 공식 실행
    if v_b[2] < 0:
        t = -z0 / v_b[2]
        P_intersect = P_cam + t * v_b

        # 투영 광선 및 최종 3D 역추적 물체 마킹
        ax3d.plot([P_cam[0], P_intersect[0]], [P_cam[1], P_intersect[1]], [P_cam[2], P_intersect[2]], 
                  color='darkorange', linewidth=2, label='Projection Ray')
        ax3d.scatter(P_intersect[0], P_intersect[1], P_intersect[2], color='red', s=150, marker='*', zorder=6, label='Tracked Target')

        # 3D 캔버스 위 텍스트 배포
        info_3d = f"Target 3D:\nX={P_intersect[0]:.2f}m\nY={P_intersect[1]:.2f}m"
        ax3d.text(P_intersect[0], P_intersect[1], P_intersect[2] + 0.15, info_3d, color='black', weight='bold', fontsize=9)
    else:
        # 광선이 바닥을 치지 않는 경우 예외선 처리
        P_end = P_cam + 2.0 * v_b
        ax3d.plot([P_cam[0], P_end[0]], [P_cam[1], P_end[1]], [P_cam[2], P_end[2]], color='purple', linestyle='--', label='Ray Escaped')

    ax3d.legend(loc='upper right', fontsize=8)

    # ==========================================
    # RIGHT SCREEN: 우측 2D 카메라 인텐트 시각화
    # ==========================================
    ax2d.set_xlim(0, img_w)
    ax2d.set_ylim(img_h, 0) # 컴퓨터 비전(OpenCV) 행렬 인덱스 정렬 매칭: 0,0은 좌측 상단
    ax2d.set_xlabel('U (Pixel X)')
    ax2d.set_ylabel('V (Pixel Y)')
    ax2d.set_title(f'2D Camera Viewfinder ({img_w}x{img_h})', fontsize=12, fontweight='bold')
    ax2d.grid(True, linestyle=':', color='gray', alpha=0.5)

    # 카메라 주점(Center Line Crosshair) 시각화
    ax2d.axhline(cy, color='blue', linestyle='--', linewidth=0.7, alpha=0.5)
    ax2d.axvline(cx, color='blue', linestyle='--', linewidth=0.7, alpha=0.5)

    # 슬라이더 기반으로 주입된 바운딩 박스(ROI) 및 타겟 픽셀 표현
    ax2d.scatter(u, v, color='red', s=120, marker='P', label='Detected Feature')
    
    # 지능형 감지 소프트웨어 느낌의 가상 ROI 박스 생성
    box_size = 30
    rect = plt.Rectangle((u - box_size/2, v - box_size/2), box_size, box_size, fill=False, color='lime', linewidth=1.5, label='object_detector.py')
    ax2d.add_patch(rect)
    
    # 2D 캔버스 정보 데이터 출력
    info_2d = f"Input Pixel:\nU = {u:.1f}\nV = {v:.1f}"
    ax2d.text(15, 45, info_2d, color='darkgreen', weight='bold', bbox=dict(facecolor='lightyellow', alpha=0.8, boxstyle='round'))
    ax2d.legend(loc='lower right', fontsize=8)

    fig.canvas.draw_idle()

# 슬라이더 리스너 콜백 결합
s_z0.on_changed(update)
s_pitch.on_changed(update)
s_u.on_changed(update)
s_v.on_changed(update)

# 런타임 초기 프레임 구동
update(None)
plt.show()
