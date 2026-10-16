from my_robot_env import MuJoCoArmEnv
import numpy as np
import time

# 1. 환경 생성 (화면 출력 모드 활성화)
env = MuJoCoArmEnv(render_mode="human")

# 2. 에피소드 초기화
obs, info = env.reset()
print("초기 관측값 (12D):", obs)

# 3. 시뮬레이션 루프 테스트
for i in range(1000):
    # Agent 대신 Random Action 샘플링 (-1.0 ~ 1.0)
    action = env.action_space.sample()
    
    # 환경과 상호작용
    obs, reward, terminated, truncated, info = env.step(action)
    
    # 렌더링 업데이트 (화면에 로봇을 그림)
    env.render()
    
    # 너무 빨리 지나가지 않도록 렌더링 속도 조절 (Frame Skip=10 기준 50Hz)
    time.sleep(0.02)
    
    if i % 100 == 0:
        print(f"Step {i}: Reward={reward:.4f}, Dist={info['distance']:.4f}")
    
    if terminated:
        print("목표 도달! 환경을 재설정합니다.")
        obs, info = env.reset()

env.close()