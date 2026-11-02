# LAB 8.1 — 강화학습과 고전적 제어의 역할 비교

**목적:** 관측→행동→보상 사이클의 입·출력 계약을 관찰하고, 왜 8.2~8.8에서 MuJoCo와 PPO를 연결하는지 설명한다. 이 절은 이론 중심이며 별도 `8.1.py` 실행 파일이 없다.

## 사전 준비
- Ubuntu 24.04/WSL2 + Python 3.12 권장. 인터프리터와 가상환경을 구분한다.
- 8.2~8.3의 실습을 위해 다음 설치는 선택적으로 선행한다. ROS 2는 **이 절에서 필요하지 않다**.

```bash
cd ~/Pysical_AI_ROS2/Ch08/ros2_ws  # 실제 clone 위치에 맞게 조정
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install mujoco gymnasium numpy stable-baselines3
python -c "import mujoco, gymnasium, stable_baselines3; print(mujoco.__version__,gymnasium.__version__,stable_baselines3.__version__)"
```

## 시연 → 원리 이해 → 따라하기 → 응용
**시연:** `my_robot_env.py`의 `reset`이 초기 관측을 생성하고 `step(action)`이 새 관측·보상·종료 판정을 출력하는 부분을 찾는다. `rl_env.py`는 별도의 6자유도 단계이므로 실습에 혼용하지 않는다.

**원리:** 다음의 계약을 노트에 적는다.

| 요소 | 3자유도 예제 | 6자유도 발전 예제 |
|---|---|---|
| 환경 | `MuJoCoArmEnv` | `ReachEnv` |
| 행동 | `Box(-1,1,(3,))` | `Box(-1,1,(model.nu,))`, 현재 XML은 6 |
| 관측 | 관절 3+3, 목표 3, 상대벡터 3 = 12 | 관절 위치/속도 각 6, EE 3, 목표 3 = 18 |
| 완료 | 거리 5cm 미만 | `reward_info['is_success']` |
| 학습 인터페이스 | 설명용 Gymnasium Env | 실제 `train_reach.py`의 PPO 입력 |

**따라하기 — 헤드리스 한 스텝 관찰:** 8.3 설치 뒤 저장소의 현재 3자유도 모델을 사용한다.

```bash
cd ~/Pysical_AI_ROS2/Ch08/ros2_ws
source .venv/bin/activate
python - <<'PY'
from my_robot_env import MuJoCoArmEnv
env = MuJoCoArmEnv(render_mode=None)
try:
    obs, info = env.reset(seed=42)
    print("observation", obs.shape, "action", env.action_space.shape)
    action = env.action_space.sample()
    next_obs, reward, terminated, truncated, info = env.step(action)
    print("reward", reward, "distance", info["distance"],
          "terminated", terminated, "truncated", truncated)
finally:
    env.close()
PY
```

**예상 관찰:** 모형이 로드된다면 관측 12개, 행동 3개와 숫자형 보상이 나온다. 성공 여부·구체적 보상 숫자는 난수 및 현재 소스/환경에 달려 있으므로 예측하지 않는다. 위 코드는 **제안한 실행 절차**이며 이 보고서 작성 환경에서 실행한 테스트 결과가 아니다.

**응용 과제:** (1) 목표에 접근할수록 보상이 어떻게 변하는가? (2) `terminated`와 `truncated`의 차이는 무엇인가? (3) 단순 역운동학에 PPO를 추가하는 것이 유리한 상황과 불리한 상황을 각 1개 제시하라. 6자유도 정책을 3자유도 환경에 넣지 않는다.

## 오류·평가 체크
- `ModuleNotFoundError`: 활성 venv와 `python -m pip --version` 확인.
- `FileNotFoundError`: 반드시 `Ch08/ros2_ws`에서 실행. 경로는 실행 위치에 의존한다.
- `reset(seed=42)`로 결과가 항상 같을 것이라 가정하지 않는다. 현재 `my_robot_env.py`는 목표 추출에 전역 `np.random`을 사용한다.
- 완료 기준: 5개 반환값을 이름과 의미로 해설, 관측 차원 확인, 실행 로그 1개 저장. 시뮬레이션이 실행되지 않았다면 '미검증'으로 기재한다.

[정적 리뷰](SECTION_8_1_REPORT_KO.md)
