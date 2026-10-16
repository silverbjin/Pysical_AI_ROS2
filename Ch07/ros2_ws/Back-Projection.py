#!/usr/bin/env python3
# sudo apt install -y fonts-nanum
import platform
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider

# [한글 폰트 설정] OS별 폰트 깨짐 방지
try:
    if platform.system() == 'Windows':
        plt.rc('font', family='Malgun Gothic')
    elif platform.system() == 'Darwin':
        plt.rc('font', family='AppleGothic')
    else:
        plt.rc('font', family='NanumGothic')
except:
    pass

# 가독성을 위한 마이너스 부호 깨짐 방지
plt.rcParams['axes.unicode_minus'] = False

# 1. 초기 카메라 파라미터 및 픽셀 설정 (VGA 해상도 기준)
W, H = 640, 480
init_u, init_v = 450, 150  # 초기 선택 픽셀 좌표 (우상단 물체 예시)
init_z = 1.5               # 초기 깊이값 (1.5m)
init_fx, init_fy = 525.0, 525.0
cx, cy = 320.0, 240.0      # 주점 (Principal Point - 이미지 중심)

# 2. 메인 그래픽스 레이아웃 설정
fig = plt.figure(figsize=(14, 7))
fig.canvas.manager.set_window_title('2D-to-3D 역투영(Back-Projection) 실시간 시뮬레이터')

# 왼쪽: 2D 이미지 평면 / 오른쪽: 3D 카메라 좌표계 공간
ax_2d = fig.add_subplot(121)
ax_3d = fig.add_subplot(122, projection='3d')

# 슬라이더 배치를 위한 하단 여백 확보
plt.subplots_adjust(bottom=0.35)

def calculate_3d(u, v, z, fx, fy, cx, cy):
    """ROS 2 노드에 적용된 역투영 수학 공식 그대로 구현"""
    x_c = (u - cx) * z / fx
    y_c = (v - cy) * z / fy
    z_c = z
    return x_c, y_c, z_c

# 3. 실시간 업데이트 함수 (슬라이더 조작 시 호출)
def update(val):
    # 슬라이더에서 현재 값 읽기
    u = s_u.val
    v = s_v.val
    z = s_z.val
    fx = s_fx.val
    # fy = s_fy.val
    fy = s_fx.val  # fx와 fy를 동일하게 조정하는 슬라이더로 단순화 (초점거리 비율 유지)
                   # 릴 하이브리드 형태로 하나의 슬라이더(s_fx) 값을 동일하게 매핑하여 fx와 fy를 동시에 조정할 수 있도록 변경했습니다.
    
    # 3D 좌표 계산
    x_c, y_c, z_c = calculate_3d(u, v, z, fx, fy, cx, cy)
    
    # --- [왼쪽 2D 플롯 업데이트] ---
    ax_2d.clear()
    ax_2d.set_title(f"2D 이미지 평면 (해상도: {W}x{H})", fontsize=12, fontweight='bold')
    # 카메라 이미지 경계 시각화
    ax_2d.add_patch(plt.Rectangle((0, 0), W, H, fill=False, color='black', linewidth=2))
    # 주점(cx, cy)과 현재 검출된 픽셀(u, v) 플로팅
    ax_2d.plot(cx, cy, 'bx', markersize=10, label=f'주점 (cx, cy) = ({cx}, {cy})')
    ax_2d.plot(u, v, 'ro', markersize=8, label=f'검출 픽셀 (u, v) = ({int(u)}, {int(v)})')
    # 중심점과의 거리 점선 표시
    ax_2d.plot([cx, u], [cy, v], 'g--', alpha=0.6)
    
    ax_2d.set_xlim(-40, W + 40)
    ax_2d.set_ylim(H + 40, -40) # 이미지 좌표계 특성상 Y축(v)은 아래가 정방향
    ax_2d.grid(True, linestyle=':', alpha=0.5)
    ax_2d.set_xlabel('U 축 (Pixel)')
    ax_2d.set_ylabel('V 축 (Pixel)')
    ax_2d.legend(loc='upper right')
    
    # --- [오른쪽 3D 플롯 업데이트] ---
    ax_3d.clear()
    ax_3d.set_title("3D 카메라 좌표계 공간 (Camera Frame)", fontsize=12, fontweight='bold')
    
    # 광학 원점 (0,0,0)
    ax_3d.scatter(0, 0, 0, color='black', s=50)
    ax_3d.text(0, 0, 0, "  카메라 원점 (0,0,0)", color='black', fontweight='bold')
    
    # 역투영된 최종 3D 타겟 포인트
    # 직관적인 시각화를 위해 Matplotlib X=Xc, Y=Zc(깊이), Z=-Yc(상하 높이)로 매핑
    ax_3d.scatter(x_c, z_c, -y_c, color='red', s=100, edgecolors='black', label='복원된 3D 위치')
    
    # 원점 구멍에서 타겟까지 뻗어나가는 광선(Ray) 시각화
    ax_3d.plot([0, x_c], [0, z_c], [0, -y_c], 'r--', linewidth=2, alpha=0.8)
    
    # 가상의 이미지 센서 평면 위치 표시 (Z = 0.5m 지점에 투영면 가시화)
    f_plane_z = 0.5
    scale = f_plane_z / z if z > 0 else 0.1
    ax_3d.plot([0, x_c*scale], [0, f_plane_z], [0, -y_c*scale], 'b-', alpha=0.4)
    
    # 3D 축 레이블 및 범위 설정
    ax_3d.set_xlabel('X_c (좌/우 미터)')
    ax_3d.set_ylabel('Z_c (전방 깊이 미터)')
    ax_3d.set_zlabel('-Y_c (상/하 미터)')
    
    ax_3d.set_xlim(-1.5, 1.5)
    ax_3d.set_ylim(0, 4.0)
    ax_3d.set_zlim(-1.5, 1.5)
    ax_3d.grid(True)
    
    # 수학 공식 실시간 계산 분해 조립표 출력 (학생 디버깅 교육용 수식 텍스트)
    formula_text = (
        f"  [실시간 수식 연산 분해 표]\n"
        f"  X_c = (u - cx) * Z / fx  =>  ({int(u)} - {cx}) * {z:.2f} / {fx:.1f} = {x_c:.3f} m\n"
        f"  Y_c = (v - cy) * Z / fy  =>  ({int(v)} - {cy}) * {z:.2f} / {fy:.1f} = {y_c:.3f} m\n"
        f"  Z_c = Measured Depth     =>  {z_c:.3f} m"
    )
    # fig.text(0.1, 0.02, formula_text, fontsize=11, family='monospace', 
    #          bbox=dict(facecolor='lightyellow', alpha=0.8, boxstyle='round,pad=0.5'))
    # 기존 코드에서 family='monospace' 속성을 과감히 제거합니다.
    fig.text(0.1, 0.02, formula_text, fontsize=11,
             bbox=dict(facecolor='lightyellow', alpha=0.8, boxstyle='round,pad=0.5'))
    
    fig.canvas.draw_idle()

# 4. 슬라이더 UI 디자인 설정
ax_color = 'lightgoldenrodyellow'
ax_u = plt.axes([0.15, 0.26, 0.7, 0.02], facecolor=ax_color)
ax_v = plt.axes([0.15, 0.22, 0.7, 0.02], facecolor=ax_color)
ax_z = plt.axes([0.15, 0.18, 0.7, 0.02], facecolor=ax_color)
ax_fx = plt.axes([0.15, 0.14, 0.7, 0.02], facecolor=ax_color)

s_u = Slider(ax_u, '픽셀 좌표 U', 0, W, valinit=init_u, valfmt='%d')
s_v = Slider(ax_v, '픽셀 좌표 V', 0, H, valinit=init_v, valfmt='%d')
s_z = Slider(ax_z, '계측된 깊이 Z (m)', 0.1, 4.0, valinit=init_z, valfmt='%.2f m')
s_fx = Slider(ax_fx, '초점거리 fx/fy', 200.0, 1000.0, valinit=init_fx, valfmt='%.1f')

# 슬라이더 값 변경 시 콜백 연동
s_u.on_changed(update)
s_v.on_changed(update)
s_z.on_changed(update)
s_fx.on_changed(update)

# 최초 1회 강제 실행하여 초기 화면 렌더링
update(None)

plt.show()
