import gymnasium as gym
from stable_baselines3 import PPO
from rl_env import ReachEnv
import time

def main():
    # 1. 환경 생성 (추론 단계이므로 render_mode='human'으로 설정하여 팝업 활성화)
    env = ReachEnv(render_mode="human")
    
    # 2. 저장된 최적의 모델 불러오기
    model_path = "./models/ppo_reach_final"
    print("=" * 50)
    print(f"[시스템] 가중치 파일을 로드합니다: {model_path}.zip")
    try:
        model = PPO.load(model_path)
        print("[시스템] 모델 로드 성공! 추론 시연을 시작합니다.")
    except FileNotFoundError:
        print(f"[오류] 모델을 찾을 수 없습니다. 경로를 확인하세요: {model_path}")
        return
    print("=" * 50)
    
    # 평가 메트릭 측정을 위한 변수 정의
    total_episodes = 0
    success_count = 0
    ep_step = 0

    # 3. 테스트 루프 진입
    obs, _ = env.reset()
    total_episodes += 1
    
    print(f"▶ [Episode {total_episodes}] 테스트 시작")
    
    for i in range(1000):
        # deterministic=True: 가우시안 노이즈(탐험)를 끄고 최고 성능의 결정론적 행동만 선택
        action, _states = model.predict(obs, deterministic=True)
        
        # 환경에 행동 적용 및 피드백 획득
        obs, reward, terminated, truncated, info = env.step(action)
        ep_step += 1
        
        # [교정] 물리 타임스텝 주기(20Hz = 0.05초)와 시각적 싱크 일치
        time.sleep(0.05) 
        
        # [교정] 에피소드 종료 조건 판정 (성공 혹은 타임아웃 전체 방어)
        if terminated or truncated:
            if terminated:
                success_count += 1
                print(f"  ↳ 🎯 성공! 목표 도달 성공 (소요 스텝: {ep_step} steps)")
                time.sleep(0.5) # 성공 순간을 관찰하기 위한 짧은 일시정지
            else:
                print(f"  ↳ ❌ 실패! 시간 초과 (300스텝 이내 도달 실패)")
            
            # 다음 에피소드 준비를 위한 리셋 및 변수 초기화
            obs, _ = env.reset()
            
            # [추가] 리셋 직후 바뀐 공의 위치를 화면 뷰어에 강제로 업데이트 명령!
            if hasattr(env, 'render'):
                env.render()
            
            ep_step = 0
            total_episodes += 1
            
            if i < 999: # 마지막 루프가 아니라면 새 로그 출력
                print(f"▶ [Episode {total_episodes}] 테스트 시작")

    # 4. 최종 성적표 출력
    print("=" * 50)
    print("[시연 종료] 에이전트 평가 결과")
    print(f" - 총 테스트 에피소드 : {total_episodes}회")
    print(f" - 성공 횟수          : {success_count}회")
    print(f" - 최종 성공률        : {(success_count / total_episodes) * 100:.1f}%")
    print("=" * 50)
    
    env.close()

if __name__ == "__main__":
    main()