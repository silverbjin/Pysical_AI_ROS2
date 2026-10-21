#!/usr/bin/env python3
# 역운동학 및 순운동학 교차 검증 스크립트 (test_ik.py)
import os
import sys
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

# --- [경로 제약 조건 반영] ---
package_parent_path = os.path.join(os.path.dirname(__file__), 'src', 'my_quadruped_bot')
if package_parent_path not in sys.path:
    sys.path.append(package_parent_path)

from my_quadruped_bot.inverse_kinematics import InverseKinematics
# ------------------------------

def forward_kinematics(q: np.ndarray, l1: float = 0.05, l2: float = 0.25, l3: float = 0.25) -> list:
    """Joint geometry consistent with Ch10 URDF: roll + fixed joint rotations."""
    q1, q2, q3 = map(float, q)
    a, b = 1.2 + q2, -2.4 + q3

    def project(x, y, z):
        return np.array([x,
                         y * np.cos(q1) - z * np.sin(q1),
                         y * np.sin(q1) + z * np.cos(q1)])

    xk, zk = -l2 * np.sin(a), -l2 * np.cos(a)
    xf, zf = xk - l3 * np.sin(a+b), zk - l3 * np.cos(a+b)
    return [np.zeros(3), project(0., l1, 0.), project(xk, l1, zk),
            project(xf, l1, zf)]


def run_ik_verification():
    ik_solver = InverseKinematics()
    
    # --- 1. 무작위 100개 목표 좌표 생성 (작업 공간 내 샘플링) ---
    np.random.seed(42)
    num_samples = 100
    x_samples = np.random.uniform(-0.1, 0.1, num_samples)
    y_samples = np.random.uniform(0.04, 0.08, num_samples) # 좌측 다리 Y오프셋 근방
    z_samples = np.random.uniform(-0.35, -0.20, num_samples) # 지면 높이 근방
    
    errors = []
    failed_points = 0
    valid_foot_points = []
    demo_skeleton = None

    print(f"--- 10.4.7 역운동학(IK) 수렴성 테스트 (샘플: {num_samples}개) ---")
    
    for i in range(num_samples):
        target_pos = np.array([x_samples[i], y_samples[i], z_samples[i]])
        
        # IK 연산 (Target 3D -> Joint Angles)
        q_sol = ik_solver.solve(target_pos[0], target_pos[1], target_pos[2], is_right_leg=False)
        
        if q_sol is None:
            failed_points += 1
            continue
            
        # FK 연산 (Joint Angles -> Result 3D)
        skeleton_points = forward_kinematics(q_sol, ik_solver.l1, ik_solver.l2, ik_solver.l3)
        result_foot_pos = skeleton_points[-1] # 마지막 발끝 좌표
        
        # 오차 계산 (유클리드 거리)
        error = np.linalg.norm(target_pos - result_foot_pos)
        errors.append(error)
        valid_foot_points.append(target_pos)
        
        # 시각화를 위해 마지막 성공 지점의 골격을 저장
        demo_skeleton = skeleton_points

    assert len(errors) > 0, 'No reachable points; test must not produce false PASS'

    # --- 2. 오차 정량적 분석 및 검증 단언(Assert) ---
    max_error = np.max(errors) if errors else 0.0
    mean_error = np.mean(errors) if errors else 0.0
    
    print(f"도달 성공률: {num_samples - failed_points}/{num_samples}")
    print(f"최대 위치 오차: {max_error:.8e} m")
    print(f"평균 위치 오차: {mean_error:.8e} m")
    
    # 1mm (0.001m) 이내 오차 검증. 부동 소수점 한계로 인해 1e-6 이하로 떨어지면 완벽한 수식임.
    assert max_error < 1e-3, f"치명적 오류: 최대 오차가 1mm를 초과했습니다! ({max_error}m)"
    print("✅ 성공: 모든 좌표가 1mm 오차 범위 내에서 완벽하게 해석되었습니다.\n")

    # --- 3. 3D Skeleton 시각화 ---
    if demo_skeleton is None:
        return
        
    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection='3d')
    
    # 100개의 무작위 타겟 좌표(구름) 플로팅
    valid_pts = np.array(valid_foot_points)
    ax.scatter(valid_pts[:,0], valid_pts[:,1], valid_pts[:,2], 
               c='gray', alpha=0.2, s=10, label='Workspace Random Targets')
    
    # 마지막 지점의 뼈대(Skeleton) 플로팅
    sk_arr = np.array(demo_skeleton)
    ax.plot(sk_arr[:,0], sk_arr[:,1], sk_arr[:,2], 
            marker='o', markersize=8, linewidth=3, color='blue', label='Leg Skeleton')
    
    # 각 관절 포인트 강조
    joint_names = ['Hip(Origin)', 'Thigh Pitch', 'Knee', 'Foot']
    colors = ['black', 'red', 'green', 'orange']
    for i, txt in enumerate(joint_names):
        ax.scatter(sk_arr[i,0], sk_arr[i,1], sk_arr[i,2], color=colors[i], s=50, zorder=5)
        ax.text(sk_arr[i,0], sk_arr[i,1], sk_arr[i,2]+0.01, f' {txt}', color='black', fontsize=9)
    
    # 그래프 메타데이터 및 비율 설정
    ax.set_title(f'3D Kinematics Verification\n(Max Error: {max_error:.2e} m)', fontsize=14, fontweight='bold')
    ax.set_xlabel('X Distance (m)')
    ax.set_ylabel('Y Distance (m)')
    ax.set_zlabel('Z Height (m)')
    
    # 3D 축 비율을 1:1:1에 가깝게 설정 (왜곡 방지)
    max_range = np.array([sk_arr[:,0].max()-sk_arr[:,0].min(), 
                          sk_arr[:,1].max()-sk_arr[:,1].min(), 
                          sk_arr[:,2].max()-sk_arr[:,2].min()]).max() / 2.0
    mid_x = (sk_arr[:,0].max()+sk_arr[:,0].min()) * 0.5
    mid_y = (sk_arr[:,1].max()+sk_arr[:,1].min()) * 0.5
    mid_z = (sk_arr[:,2].max()+sk_arr[:,2].min()) * 0.5
    ax.set_xlim(mid_x - max_range, mid_x + max_range)
    ax.set_ylim(mid_y - max_range, mid_y + max_range)
    ax.set_zlim(mid_z - max_range, mid_z + max_range)
    
    ax.legend()
    plt.show()

if __name__ == "__main__":
    run_ik_verification()