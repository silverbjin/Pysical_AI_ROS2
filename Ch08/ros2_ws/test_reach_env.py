from rl_env import ReachEnv
import time

def main():
    # 1. 환경 생성 (render_mode='human'으로 설정하여 시뮬레이터 팝업 활성화)
    env = ReachEnv(render_mode="human")
    
    # 2. 에피소드 반복 테스트 (총 5회 진행)
    for episode in range(5):
        obs, _ = env.reset()
        # 관측 벡터에서 목표물의 절대 좌표 슬라이싱 ([6:9]) 후 출력
        print(f"=== Episode {episode+1} Start. Target Pos: {obs[6:9]} ===")
        
        step = 0
        while True:
            # 환경의 Action Space에서 무작위 행동 샘플링 (3차원 토크 제어값)
            action = env.action_space.sample()
            
            # 환경에 행동 주입 후 결과 반환 (Gymnasium 표준 5개 인자)
            obs, reward, terminated, truncated, info = env.step(action)
            
            # [교정] 환경의 제어 주기(20Hz = 0.05초)와 시각적 싱크를 맞추기 위한 딜레이 조정
            time.sleep(0.05) 
            
            step += 1
            if step % 50 == 0:
                # print(f"  [Step {step}] Reward: {reward:.4f}, Dist to Target: {info['distance']:.4f}m")
                # info['distance'] 대신 info.get('distance', 0.0)을 쓰면 키가 없어도 에러로 터지지 않습니다.
                dist_val = info.get('distance', 0.0)
                print(f"  [Step {step}] Reward: {reward:.4f}, Dist to Target: {dist_val:.4f}m")
            
            # 에이전트가 목표에 성공적으로 도달했거나(terminated), 
            # 300스텝을 초과하여 타임아웃이 발생한 경우(truncated) 루프 탈출
            # (주석: 실전 RL 학습 시에는 환경 내부나 Wrapper에서 truncated를 제어하는 것이 정석입니다)
            if step >= 300:
                truncated = True

            if terminated or truncated:
                print(f"↳ Episode {episode+1} Finished at Step {step}. Reason: {'Success' if terminated else 'Timeout'}\n")
                break

    print("모든 환경 검증이 완료되었습니다. 시뮬레이터를 종료합니다.")
    env.close()

if __name__ == "__main__":
    main()