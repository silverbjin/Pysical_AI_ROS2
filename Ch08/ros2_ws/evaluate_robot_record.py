import numpy as np
import gymnasium as gym
from stable_baselines3 import PPO
from rl_env import ReachEnv
from tqdm import tqdm

def evaluate_policy_robotics(model, env, n_eval_episodes=100):
    """
    물리 AI 및 로봇 매니퓰레이션 시스템 특화 정량 성능 평가 함수
    """
    success_count = 0
    episode_rewards = []
    episode_lengths = []
    action_smoothness_scores = []
    final_steady_state_errors = []  # [추가] 정착 오차 (최종 남은 거리) 추적

    print(f"\n==================================================")
    print(f"[평가 개시] 총 {n_eval_episodes}회의 독립 에피소드 테스트를 진행합니다.")
    print(f"==================================================")
    
    for i in tqdm(range(n_eval_episodes), desc="로봇 에이전트 평가 중"):
        obs, info = env.reset()  # Gymnasium 최신 스펙 적용 (info 수신)
        done = False
        total_reward = 0
        steps = 0
        
        last_action = None  # [교정] 첫 스텝 거칠기 왜곡 방지를 위해 None으로 초기화
        episode_action_diff = 0
        
        while not done:
            # Deterministic=True: 결정론적 최적 제어 명령 추출
            action, _ = model.predict(obs, deterministic=True)
            obs, reward, terminated, truncated, info = env.step(action)
            
            total_reward += reward
            steps += 1
            
            # [교정] 부드러움 측정: 두 번째 스텝부터 연속적인 변화량만 순수 측정
            if last_action is not None:
                episode_action_diff += np.linalg.norm(action - last_action)
            last_action = action.copy()

            # [교정] Gymnasium 표준 종료 조건 연산 및 타임아웃 강제 방어
            done = terminated or truncated or steps >= 500
            
            # [보안] 에피소드가 종료(done)되었을 때 성공 조건 확인
            if done:
                # 환경의 info 내 'is_success' 표준 플래그 혹은 terminated 기반 판단
                if info.get('is_success', False) or (terminated and not truncated):
                    success_count += 1
                
                # [추가] 정착 오차 데이터 수집 (마지막 순간 목표물과의 거리)
                if 'distance' in info:
                    final_steady_state_errors.append(info['distance'])
        
        episode_rewards.append(total_reward)
        episode_lengths.append(steps)
        
        # 스텝당 평균 액션 변화량 계산 (최소 1스텝 이상일 때만 분모 연산)
        denom = max(1, steps - 1)
        action_smoothness_scores.append(episode_action_diff / denom)

    # 정량 통계 지표 산출
    success_rate = (success_count / n_eval_episodes) * 100
    mean_reward = np.mean(episode_rewards)
    std_reward = np.std(episode_rewards)
    mean_steps = np.mean(episode_lengths)
    mean_smoothness = np.mean(action_smoothness_scores)
    mean_sse = np.mean(final_steady_state_errors) if final_steady_state_errors else 0.0

    print("\n==================================================")
    print("📊 6-DOF 매니퓰레이터 정량적 성능 평가 결과 보고서")
    print("==================================================")
    print(f"1. 태스크 도달 성공률 (Success Rate)       : {success_rate:.2f}%")
    print(f"2. 평균 정착 오차 (Steady-State Error)    : {mean_sse*1000:.1f} mm (실패 포함)")
    print(f"3. 평균 제어 소요 시간 (Mean Time Steps)   : {mean_steps:.1f} Steps")
    print(f"4. 제어 신호 거칠기 (Action Jerk Score)   : {mean_smoothness:.4f} (낮을수록 소모전력 최적화됨)")
    print(f"5. 에피소드 평균 보상 (Mean Return)        : {mean_reward:.2f} +/- {std_reward:.2f}")
    print("==================================================\n")
    
    return success_rate, mean_reward

# if __name__ == "__main__":
#     env = ReachEnv(render_mode=None)
#     model_path = "./models/ppo_reach_final"
    
#     try:
#         model = PPO.load(model_path)
#         print(f"[시스템] 최적화된 학습 완료 정책 모델 로드 완료: {model_path}")
#         evaluate_policy_robotics(model, env, n_eval_episodes=100)
#     except FileNotFoundError:
#         print(f"[오류] 지정한 경로({model_path})에 가중치 파일 파일이 없습니다. 학습을 먼저 완료하세요.")
#     finally:
#         env.close()
        
if __name__ == "__main__":
    from gymnasium.wrappers import RecordVideo  # Wrapper 임포트
    
    # 1. 베이스 환경을 시각화 모드로 생성
    base_env = ReachEnv(render_mode="rgb_array") 
    
    # 2. 녹화 래퍼로 환경을 감싸기 (첫 3개 에피소드만 샘플링 녹화)
    env = RecordVideo(
        base_env, 
        video_folder="./videos/evaluation/", 
        episode_trigger=lambda ep_id: ep_id < 3
    )
    
    model_path = "./models/ppo_reach_final"
    
    try:
        model = PPO.load(model_path)
        print(f"[시스템] 녹화 기능이 활성화된 평가 프로세스를 개시합니다.")
        
        # 3. 평가 함수 실행 (환경 내부에서 자동으로 MP4가 구워집니다)
        evaluate_policy_robotics(model, env, n_eval_episodes=100)
        
    except FileNotFoundError:
        print("저장된 모델이 없습니다. 학습을 먼저 진행하세요.")
    finally:
        # [중요] env.close()가 호출되는 순간 FFmpeg가 최종 MP4 파일 저장을 마무리합니다.
        env.close()