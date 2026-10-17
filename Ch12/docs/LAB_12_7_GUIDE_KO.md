# 12.7 Sim-to-Real을 위한 학습 환경 교란

이 실습은 12.3의 관측·보상·위치 제어를 유지하면서 물성, 센서, 지연, 외력을 바꾼다. `RobustQuadrupedEnv`는 기존 환경을 감싸므로 목표/장애물 과제에도 적용된다. 짧은 실행은 인터페이스와 수치적 동작을 검증하며 실제 로봇 전이나 보행 성능을 입증하지 않는다.

## 설치 및 실행

저장소의 `Ch12` 디렉터리에서 실행한다. Python 3.10 이상과 `train`, `test` 선택 의존성이 필요하다. 증거 실행은 Python 3.12.3, MuJoCo 3.3.7, Torch 2.5.1 CPU, SB3 2.7.1의 WSL2 환경에서 수행했다.

```bash
python -m pip install -e '.[train,test]'
python -m pytest tests/test_robust_env.py -q
python scripts/verify_robust_env.py --output evidence/section12_7
python scripts/benchmark_vec_env.py --output evidence/section12_7/benchmark.json --envs 1 2 4 --steps 100
```

```python
import json
from pathlib import Path
import numpy as np
from quadruped_rl.robust_env import RobustQuadrupedEnv

settings = json.loads(Path('config/section12_7_robust.json').read_text())
with RobustQuadrupedEnv(**settings) as env:
    obs, info = env.reset(seed=42)
    for _ in range(100):
        obs, reward, done, cut, info = env.step(np.zeros(12))
        if done or cut:
            obs, info = env.reset()
```

`task='goal'` 또는 `task='avoidance'`도 가능하다. `env=기존환경`을 전달할 수도 있으며 이때 생성자용 추가 인자는 함께 전달하지 않는다. 물리 모델과 상태는 `env.unwrapped.model`, `env.unwrapped.data`에 있다. `enabled=False`는 모든 추가 교란과 큐 지연을 끈 기준 실험이다. 위치 제어 외의 torque 제어는 locomotion 과제에서만 지원한다.

## 에피소드별 물성

| 항목 | 샘플링 및 적용 |
|---|---|
| 질량·관성 | 로봇 동적 몸체별 같은 계수 U(0.8, 1.2)를 질량과 주관성에 적용 |
| 접촉 마찰 | 공통 계수 U(0.5, 1.5)를 바닥 및 네 발의 원래 마찰 3성분에 적용 |
| 모터 강도 | 공통 계수 U(0.9, 1.1)를 gain, bias, 실제 force 제한에 적용 |

매 reset은 로드 직후 보관한 읽기 전용 기준 배열에서 시작한다. 이전 에피소드 값을 계속 곱하지 않는다. `body_rootid`로 base_link 아래 동적 몸체만 고르므로 world와 mocap 목표/장애물은 질량 변경 대상이 아니다. 상수는 임시 `MjData`에서 `mj_setConst`로 계산하고 실제 상태에 `mj_forward`를 호출한다. `mj_setConst`는 전달받은 data의 qpos를 모델 기본값으로 바꾸므로 실제 에피소드 data를 전달하면 시드 초기 자세를 잃는다. 임시 data를 사용하면 초기 높이·관절 자세·속도·목표·mocap 배치를 유지한다. MuJoCo 접촉의 최대값 마찰 혼합 때문에 바닥만 낮추면 발의 높은 마찰이 그대로 남을 수 있다. 그래서 바닥과 발을 함께 스케일한다. 장애물 측면 재질은 이 설정의 변경 대상이 아니다.

위치 PD에서는 `gainprm`의 kp와 `biasprm`의 -kp/-kv를 함께 조정한다. 실제 토크 상한인 `actuator_forcerange`도 같은 비율로 바뀐다. torque 모드에서는 입력 정규화용 명목 토크를 다시 스케일하지 않아 모터 강도가 두 번 곱해지는 오류를 피한다.

`reset(seed=같은값)`은 같은 초기 상태·물성·잡음을 재현한다. 시드를 생략한 다음 reset은 환경 자체 `np_random` 스트림을 이어 쓴다. 정보의 `domain_randomization`에 링크별 계수와 공통 마찰/모터 계수가 기록된다.

## 센서와 지연의 정확한 의미

관측은 locomotion/goal 48개, avoidance 기본 64개를 유지한다. 0:3 몸체 선속도, 3:6 각속도, 6:9 중력 방향, 9:12 명령 또는 목표, 12:24 관절각 잔차, 24:36 관절속도, 36:48 실제 이전 적용 행동이다. avoidance의 48 이후는 기존 LiDAR 정책 입력이다.

| 센서 필드 | 기본 정규 잡음 표준편차 | 단위 |
|---|---:|---|
| 선속도 | 0.05 | m/s |
| 각속도 | 0.02 | rad/s |
| 중력 | 0.01 | 단위 벡터 성분; 이후 재정규화 |
| 관절각 | 0.005 | rad |
| 관절속도 | 0.02 | rad/s |

명령/목표와 행동 이력에는 잡음을 넣지 않는다. LiDAR는 avoidance 환경의 자체 거리 잡음 설정을 사용하며 이 wrapper가 다시 잡음을 넣지 않는다. 측정은 reset/transition당 한 번만 생성하여 캐시하고 `_get_obs()`의 반복 조회는 난수를 소비하지 않는다. `noise_std` 사전으로 각 물리 센서 값을 변경할 수 있다.

기본 control interval은 10 × 0.002 = 0.02초이다. `action_delay=2`는 처음 두 step에 영벡터를 적용하고 세 번째에 첫 명령을 적용한다. `observation_delay=2`는 첫 두 step에 동일한 초기 잡음 관측을 반환하고 세 번째에 첫 transition의 측정을 반환한다. 초기 큐에 0 관측을 채우지 않는다. reset은 두 큐를 비운다. 제어 주기를 바꾸면 지연 시간도 달라진다.

반환 관측은 완전한 과거 프레임이므로 목표/명령과 이력도 해당 측정 시각의 값이다. 지연 관측의 행동 이력은 그 프레임에서 실제 적용된 행동이다. 현재 명령은 `info['commanded_action']`, 이번에 적용한 지연 행동은 `info['delayed_action']`에서 구분한다. 보상은 현재 실제 transition으로 계산한다. 정책에 현재의 명령/목표를 별도로 전달하려면 관측 규격과 학습을 함께 변경해야 한다.

## 외력

control step마다 확률 0.01로 base_link에 각 성분 U(-50, 50) N의 세계 좌표계 힘을 가한다. 이는 성분 상한이며 벡터 크기 상한 50 N은 아니다. `push_probability`, `push_force`로 조절한다. 고정된 힘은 해당 control interval의 모든 물리 substep에서 유지하고 step 완료/예외/reset에서 제거한다.

적용 위치는 `data.xfrc_applied[base_id, :3]`이다. `(nbody, 6)` wrench 배열의 뒤 세 성분은 토크다. `qfrc_applied`는 `(nv,)` 일반화 힘 벡터이므로 원고의 `qfrc_applied[body_id, :]` 방식은 사용할 수 없다. 마지막 외력은 `info['external_force_world']`에 기록된다.

## 실제 PPO와 처리량 측정

`verify_robust_env.py`는 세 과제의 SB3 검사, 실제 PPO 갱신, 저장/재로드 추론, 지연 임펄스, 시드 재현과 힘 제거를 검증한다. `robust.json`에 결과와 checkpoint 경로가 남는다. 생성된 정책은 각 128 transition의 연결 확인용이며 보행 정책으로 사용하면 안 된다.

벤치마크는 CPU MuJoCo의 DummyVecEnv/SubprocVecEnv를 비교한다. 시작 시간에는 worker 생성·모델 로드·reset이 포함된다. 별도 warmup 이후 측정한 steady 시간에는 에피소드 자동 reset도 포함된다. subprocess는 `spawn`을 쓰므로 스크립트의 `if __name__ == '__main__'` 진입점이 필요하다. 환경 수가 늘면 통신·Python·CPU 경합 때문에 느려질 수도 있다. GPU 병렬 물리 엔진이나 일정 배수 가속을 주장하지 않는다.

Gazebo는 이 MuJoCo wrapper의 물성 배열을 공유하지 않는다. 기존 Gazebo 관측 검증은 `evidence/section12_6/gazebo/result.json`과 `scripts/verify_gazebo.sh`에서 별도로 확인한다. 정책의 ROS 관측·명령 연결과 주기 검증은 12.8의 범위다.

## 공통 학습 CLI에서 사용

리포지토리 루트에서 다음과 같이 manifest를 포함한 robust 번들을 생성·재생한다. ROS로 연결할 모델은 처음부터 12.8의 NumPy 1.26.4 ROS 가상환경에서 학습한다.

```bash
quadruped-train --task robust --env-config Ch12/config/section12_7_robust.json \
  --output Ch12/runs/robust-smoke --backend subproc --n-envs 2 \
  --total-timesteps 256 --n-steps 64 --batch-size 64 --n-epochs 2 \
  --eval-every 128 --eval-episodes 1
quadruped-play --output Ch12/runs/robust-smoke --expected-task robust --steps 100
```

`task=robust`와 내부 task=locomotion/goal/avoidance를 구분한다. 기본 설정 파일의 내부 task는 locomotion이다. 지연·노이즈·랜덤화 설정도 manifest에 저장해 재생 환경에 적용한다. ROS 배포에서는 센서/통신 자체가 지연과 잡음을 만들므로 학습 wrapper를 ROS 입력에 다시 중복 적용하지 않는다. 이 차이에 대한 실제 로봇 성능은 검증하지 않았다.