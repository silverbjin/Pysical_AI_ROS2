#!/usr/bin/env python3
# 궤적 생성 테스트용 스크립트 (test_trajectory.py)
import numpy as np
import matplotlib.pyplot as plt

import os
import sys
# --- [경로 제약 조건 반영] ---
# test_trajectory.py 위치: /home/jinho/Pysical_AI_book/Ch10/ros2_ws/test_trajectory.py
# trajectory_generator.py 위치: /home/jinho/Pysical_AI_book/Ch10/ros2_ws/src/my_quadruped_bot/my_quadruped_bot/trajectory_generator.py
# my_quadruped_bot 패키지의 상위 디렉토리를 파이썬 검색 경로에 추가합니다.
package_parent_path = os.path.join(os.path.dirname(__file__), 'src', 'my_quadruped_bot')
if package_parent_path not in sys.path:
    sys.path.append(package_parent_path)
# 위에서 정의한 TrajectoryGenerator 클래스를 임포트합니다.
from my_quadruped_bot.trajectory_generator import TrajectoryGenerator

def test_plot() -> None:
    # 1. 궤적 생성기 인스턴스화 (10cm 거상 높이 적용)
    gen = TrajectoryGenerator(step_height=0.1)
    
    # 2. 9장 및 10.1절의 기립 높이(-0.3m) 제약을 반영한 시작/끝점 설정
    # X축 기준 0.0m에서 출발하여 0.2m(20cm) 전진하는 스윙 상태를 시뮬레이션
    start = np.array([0.0, 0.0, -0.3])
    end = np.array([0.2, 0.0, -0.3]) 
    
    x_data = []
    y_data = []
    z_data = []
    
    # 3. 스윙 진행률 s를 0부터 1까지 100단계로 정밀 샘플링
    s_samples = np.linspace(0.0, 1.0, 100)
    for s in s_samples:
        pos = gen.generate_swing(start, end, s)
        x_data.append(pos[0])
        y_data.append(pos[1])
        z_data.append(pos[2])
        
    # 4. Matplotlib을 활용한 2D 평면 시각화
    plt.figure(figsize=(10, 5))
    
    # 생성된 사이클로이드 곡선 플로팅
    plt.plot(x_data, z_data, 'b-', linewidth=2.5, label='Cycloid Swing Trajectory')
    
    # 이착륙 이정표(Start/End) 마킹
    plt.plot([start[0]], [start[2]], 'go', markersize=8, label='Lift-off (Start)')
    plt.plot([end[0]], [end[2]], 'ro', markersize=8, label='Touchdown (End)')
    
    # 최고점 가이드라인 레이블링 (기립 지면 -0.3m + 거상 높이 0.1m = -0.2m 목표)
    plt.axhline(y=-0.2, color='r', linestyle='--', alpha=0.5, label='Target Clearance (-0.2m)')
    
    # 그래프 스타일링 및 메타데이터 설정
    plt.xlabel('X Distance (m)', fontsize=11)
    plt.ylabel('Z Height (m)', fontsize=11)
    plt.title('End-Effector Trajectory Validation (Cycloid Curve)', fontsize=13, fontweight='bold')
    plt.legend(loc='lower center', fontsize=10)
    plt.grid(True, linestyle=':', alpha=0.6)
    plt.axis('equal')  # X축과 Z축의 물리적 스케일 비율을 1:1로 고정
    
    print("Generating trajectory plot... Close the window to continue.")
    plt.show()

if __name__ == "__main__":
    test_plot()