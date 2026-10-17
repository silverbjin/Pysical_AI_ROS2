# 12.5절: 목표 지점 이동 학습

12.4절 설치를 마친 Ubuntu/WSL 터미널에서 리포지토리 루트 기준으로 실행한다.

## 목표와 좌표계부터 확인하기

```bash
quadruped-goal --policy stand --target 2 1 --render --steps 1000
quadruped-goal --policy random --radius-range 2 3 --steps 1000
MUJOCO_GL=egl quadruped-goal --policy stand --target 2 1 \
  --steps 200 --frame-path target.png --trajectory-path path.csv
python Ch12/scripts/plot_trajectory.py path.csv --output path.png
```

stand는 자세 유지, random은 무작위 관절 행동이다. 두 정책 모두 목표로 걸어가는 학습된 정책이 아니다. 빨간 공은 목표이며 파란 점은 최근 5초의 경로다. `--target x y`는 첫 에피소드의 월드 좌표 목표만 지정한다. 이후 reset은 로봇 주변에서 새 목표를 뽑는다.

```python
import numpy as np
from quadruped_rl import QuadrupedGoalEnv
with QuadrupedGoalEnv(radius_range=(2,3), goal_mode='resample') as env:
    obs, info = env.reset(seed=42, options={'target':[2,1]})
    obs, reward, terminated, truncated, info = env.step(np.zeros(12))
    print(obs[9:12], info['reward_terms'], info['is_success'])
    env.set_target([-1,2])  # 외부 목표 변경, 진척도 기준 거리도 함께 갱신
```

로봇 기준 x는 전방, y는 왼쪽, 양의 yaw는 왼쪽 회전이다. 따라서 오른쪽 30도 목표는 음의 헤딩이다. MuJoCo 쿼터니언은 w,x,y,z 순서다. 거리와 atan2(dy,dx)-yaw로 상대 헤딩을 계산한다. 신경망에는 각도 자체 대신 `[거리, sin(헤딩), cos(헤딩)]`를 제공한다. ±π 경계를 부드럽게 연결하며 도착점에서는 [0,0,1]로 정의한다.

관측은 48차원이다. 몸체 선속도·각속도·단위 중력(9), 목표 특징(3), 관절 잔차·속도·이전 행동(36) 순서다. 초안의 거리·각도 2개 방식이면 47차원이지만 이 구현은 연속적인 sin/cos 표현을 택했다. 12.3의 48차원 속도 명령과 의미가 다르므로 기존 locomotion 모델을 그대로 재생할 수 없다. ZIP 내부 schema 검사로 혼용을 막는다.

## 학습과 재생

```bash
quadruped-train --task goal --env-config Ch12/config/section12_5_goal.json \
  --output Ch12/runs/goal-smoke --total-timesteps 512 --n-envs 2 \
  --n-steps 64 --batch-size 64 --n-epochs 2 \
  --eval-every 256 --eval-episodes 2 --checkpoint-every 256
quadruped-play --output Ch12/runs/goal-smoke --expected-task goal --render --steps 1000

# 본 학습: 새 폴더를 사용한다. 학습 시간과 성공 여부는 장비·설정에 따라 다르다.
quadruped-train --task goal --env-config Ch12/config/section12_5_goal.json \
  --output Ch12/runs/goal-2m --backend subproc --n-envs 8 --total-timesteps 2000000
quadruped-play --output Ch12/runs/goal-2m --expected-task goal --steps 2000 \
  --trajectory-path goal-path.csv
python Ch12/scripts/plot_trajectory.py goal-path.csv --output goal-path.png
```

기본 목표 반경은 2~3m, 도착 반경은 0.3m다. 작은 거리를 시험하려면 JSON의 radius_range를 [1,1] 등으로 바꾸어 새 실험을 시작한다. 자동 80% 승급이나 단계 간 정책 이어 학습은 구현하지 않았다. 각 난이도의 성공률·낙상률을 먼저 비교한 뒤 별도 커리큘럼을 설계한다.

보상은 `50 × (이전 거리 - 현재 거리) + 도착 10 + 자세 보상 - 토크/행동 변화/비발 접촉 비용 - 낙상 비용`이다. 기존 직진·회전 속도 추종 보상은 제거한다. 지속적인 자세·비용 항목에는 dt를 곱하고 진척도는 거리 차이 자체를 사용한다. 낙상 스텝에서는 진척도와 도착 보상을 주지 않는다.

이 거리 감소식은 진척도 shaping이다. gamma<1인 PPO에서 정책 불변성을 보장하는 엄밀한 potential-based shaping이라고 부르지 않는다. 한 목표 구간에서 할인하지 않은 거리 차이 합은 시작·종료 거리 차이로 상쇄되므로 단순 왕복만으로 순이익이 나는 것도 아니다. 할인·목표 전환·에피소드 종료가 함께 작용하므로 실제 성공률로 보상 해킹을 점검한다.

resample 모드는 기존 목표의 보상을 계산한 **뒤에** 새 목표를 고른다. 반환 관측은 새 목표, `evaluated_target`·`distance`는 방금 평가한 기존 목표, `target`·`next_distance`는 다음 관측의 목표다. `is_success`는 해당 스텝의 도착 사건, `goals_reached`는 에피소드 누계다. 목표 변경 시 이전 행동은 유지하고 기준 거리는 재설정하여 보상 급증을 막는다. timeout에서는 새 목표를 생성하지 않는다.

평가 환경은 항상 terminate 모드로 하나의 목표에 도착하면 종료한다. TensorBoard의 eval/success_rate는 이 평가 에피소드의 도착 비율이다. 학습 resample 모드의 중간 도착이 마지막 실패 정보에 묻히는 오류를 피한다. 몸체 낙상과 20초 제한도 적용하며 타임아웃을 성공으로 해석하지 않는다.

## 마커·경로 구현과 한계

Mocap은 자동으로 충돌이 없어지는 기능이 아니다. 전용 MJCF에서 목표 geom의 contype와 conaffinity를 모두 0으로 설정하고, body_mocapid를 이름으로 조회한다. 마커를 로봇과 겹쳐도 기존 물리 궤적과 동일함을 테스트한다.

경로는 공개 `mujoco.viewer.user_scn`과 `mjv_initGeom`을 사용한다. 기본 최대 256점과 시뮬레이션 시간 5초로 제한하고 reset 시 지운다. RGB와 human 모두 같은 경로를 표시하며 카메라는 로봇과 현재 목표를 함께 담도록 자동 조정한다. 초안의 viewer.add_marker(time=...)는 사용하지 않는다. CSV에는 에피소드와 평가 당시 목표도 기록하며 그래프는 reset 전후 궤적을 연결하지 않는다.

MuJoCo는 검증한 3.3.7 버전으로 고정한다. 종료 시 비동기 viewer 정리를 기다리는 호환 처리가 있으므로 버전을 변경하면 native viewer와 Ctrl+C 종료를 반드시 다시 검증한다.

이 과제는 장애물·LiDAR·경로 탐색기를 포함하지 않는다. 짧은 PPO 실험의 목표 성공률은 0%였으며, 목표 이동을 이미 학습했다고 주장하지 않는다. 환경·학습·평가·시각화 경로가 실행되는 것을 검증한 결과다. 장애물 회피와 실제 로봇 적용은 후속 과제다.

참고: [MuJoCo passive viewer와 user_scn](https://mujoco.readthedocs.io/en/stable/python.html#passive-viewer), [SB3 평가와 성공률](https://stable-baselines3.readthedocs.io/en/v2.7.1/guide/callbacks.html).

## 실제 물리·viewer 검증 재실행

```bash
MUJOCO_GL=egl python Ch12/scripts/verify_goal_env.py --output Ch12/runs/verify-goal
# 아래는 Ubuntu/WSLg 디스플레이가 필요하다. 12개 별도 프로세스의 종료를 검사한다.
python Ch12/scripts/verify_viewer_shutdown.py --output Ch12/runs/verify-shutdown

# wheel에서 모델과 포함 XML을 읽는지 확인한다. 먼저 12.4 가이드의 verify-ppo 실행.
python -m pip install build
python -m build --wheel Ch12 --outdir /tmp/ch12-wheels
python -m pip install --no-deps --target /tmp/ch12-installed /tmp/ch12-wheels/*.whl
PYTHONPATH=/tmp/ch12-installed python Ch12/scripts/verify_wheel_viewer.py \
  --bundle Ch12/runs/verify-ppo/goal_dummy --output Ch12/runs/verify-wheel \
  --wheel-root /tmp/ch12-installed
```

Gazebo 검증은 ROS 2 Jazzy와 기존 Ch11 의존성이 갖춰진 새 터미널에서 `bash Ch12/scripts/verify_gazebo.sh`로 실행한다. RL 가상환경을 활성화하지 않고 실행한다. 이 검사는 기존 ROS/Gazebo 로봇의 실행 회귀다.
