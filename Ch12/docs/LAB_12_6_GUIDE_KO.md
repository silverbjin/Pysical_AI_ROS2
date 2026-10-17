# 12.6절: LiDAR 장애물 회피 환경

12.4절의 Ubuntu/WSL 설치를 마친 뒤 리포지토리 루트에서 실행한다. 이 절은 실제 MuJoCo 광선·충돌과 PPO 학습·저장·재생을 연결한다. 제공하는 stand와 random은 학습된 회피 정책이 아니다.

## 장애물과 스캔 확인

```bash
quadruped-goal --task avoidance --policy stand --render --steps 1000
python Ch12/examples/12_6_avoidance_demo.py --policy random --num-rays 32 --steps 1000
MUJOCO_GL=egl quadruped-goal --task avoidance --policy stand --steps 200 \
  --frame-path avoidance.png --trajectory-path avoidance.csv
python Ch12/scripts/plot_trajectory.py avoidance.csv --output avoidance-path.png
```

크기가 다른 최대 10개의 박스, 목표 마커, 최근 경로와 청록색 광선을 표시한다. 박스는 무한 질량의 운동학적 mocap 물체이며 에피소드 reset 때 위치를 바꾼다. 스캔에는 장애물만 포함하고 로봇 전체·바닥·목표는 제외한다. `--obstacle-count 0`으로 빈 스캔도 확인할 수 있다.

```python
import numpy as np
from quadruped_rl import QuadrupedAvoidanceEnv

with QuadrupedAvoidanceEnv(obstacle_count=1, lidar_noise_std=0) as env:
    obs, info = env.reset(seed=42, options={
        'target': [2, 0], 'obstacles': [[0, 2]]})
    obs, reward, terminated, truncated, info = env.step(np.zeros(12))
    print(obs.shape, info['lidar_min'], info['obstacle_collision'], info['fallen'])
    print(info['reward_terms'])
```

관측은 기존 목표 이동 특징 48개와 LiDAR 근접도 16개로 총 64차원이다. 32개 광선을 선택하면 80차원이다. 센서 원점은 몸체 기준 위쪽 0.12m이고 몸체 자세를 따라 360도 스캔한다. 첫 광선은 몸체 전방이며 양의 각도는 왼쪽이다. `1 - clip(거리, 0, 5)/5`를 사용하므로 0은 최대 거리 또는 미검출, 1은 센서 원점 가까이의 장애물이다.

기본 거리 노이즈의 표준편차는 0.05m다. 거리 단위에서 한 번 적용한 뒤 정규화하고, 같은 스텝의 관측 재조회에는 새 노이즈를 생성하지 않는다. Python 설정의 `lidar_dropout`은 최대 거리 반환으로 모사한다. 보상과 `lidar_distances`/`lidar_min` 진단에는 노이즈·dropout 전 거리를 사용한다. 정책이 보지 못하는 깨끗한 거리를 보상에 사용하는 설계임을 고려해 실험을 해석한다.

시작 위치와 박스 표면 사이에는 1m, 목표와 박스 표면 사이에는 도착 반경+0.55m, 박스 사이에는 0.15m를 확보한다. 배치 좌표 범위는 월드 xy 각각 [-4,4]m다. 외부 목표 변경과 목표 재추출도 여유를 검사한다. 이 조건은 시작·목표 주변 공간을 확보하지만 둘 사이의 전역 경로 존재를 보장하지 않는다.

## 보상과 종료

비충돌 스텝에는 12.5절 목표 보상에 다음 비용을 더한다.

```text
safety = -2 × mean(max(0, 0.8 - clean_distance)) / 0.8 × dt
```

0.8m는 센서 원점 기준 임계값이며 로봇 외곽의 여유 거리를 보장하지 않는다. 모든 링크·발과 활성 장애물의 실제 접촉을 검사한다. 제어 스텝 사이의 물리 하위 스텝에서 순간 접촉한 뒤 떨어져도 충돌을 유지하여 종료하고, 기본 총 보상을 정확히 -100으로 한다. 해당 스텝의 도착 보상도 차단한다. 종료 후에는 reset이 필요하다. `obstacle_collision`과 `fallen`은 별도 사건이며 동시에 참일 수도 있다.

## PPO 학습과 재생

```bash
quadruped-train --task avoidance --env-config Ch12/config/section12_6_avoidance.json \
  --output Ch12/runs/avoidance-smoke --total-timesteps 2048 --n-envs 2 \
  --n-steps 128 --batch-size 64 --n-epochs 2 \
  --eval-every 512 --eval-episodes 2 --checkpoint-every 512
quadruped-play --output Ch12/runs/avoidance-smoke --expected-task avoidance \
  --render --steps 1000

# 본 학습 예시: 소요 시간과 회피 성공은 보장하지 않는다.
quadruped-train --task avoidance --env-config Ch12/config/section12_6_avoidance.json \
  --output Ch12/runs/avoidance-2m --backend subproc --n-envs 8 --total-timesteps 2000000
```

평가는 한 목표에 도착하면 종료한다. TensorBoard의 `eval/success_rate`와 여러 미사용 시드의 충돌·낙상·도착률을 함께 확인한다. 16/32개 광선 설정은 관측 크기가 다르므로 새 학습 폴더와 맞는 모델을 사용한다. manifest와 ZIP 관측 schema 검사는 goal·locomotion 정책의 혼용을 막는다.

실제 짧은 실험은 dummy 2,048회·128회와 별도 확인한 subproc 128회 전이에서 파라미터 변경·저장·재생을 확인했으나 평가 도착률은 모두 0%였다. 초기 `subproc` 폴더는 검증 스크립트 인자 누락으로 실제로 dummy를 사용했다. 스크립트를 수정하고 실제 subproc 실행을 `subproc_verified`에 추가했다. 이 결과는 학습 도구의 동작 증거이며 회피 능력 검증이 아니다.

## 재검증과 한계

```bash
MUJOCO_GL=egl CH12_TEST_RENDER=1 python -m pytest Ch12/tests -q
MUJOCO_GL=egl python Ch12/scripts/verify_avoidance_env.py --output Ch12/runs/verify-avoidance
# WSLg/Ubuntu 디스플레이 필요: 5개 프로필, 정상 종료 5회와 SIGINT 10회
python Ch12/scripts/verify_viewer_shutdown.py --output Ch12/runs/verify-shutdown
```

희소 광선 사이의 물체, 스캔 평면 아래의 낮은 장애물과 낭떠러지는 놓칠 수 있다. 로봇이 기울면 스캔도 기울어진다. 전역 경로 계획, 동적 장애물 회피, 지도 기반 탐색, 실제 로봇 전이는 이 환경만으로 해결되지 않는다. Gazebo 증거는 기존 Ch11 ROS 로봇의 센서·기립·종료 회귀이며 PPO를 Gazebo로 전송해 회피시킨 결과가 아니다.

MuJoCo는 검증 버전 3.3.7로 고정한다. 실제 viewer 종료에는 해당 버전의 비동기 정리를 기다리는 호환 처리가 있으므로 업그레이드할 때 창 종료와 Ctrl+C를 재검증한다. 상세 수치와 로그 위치는 `SECTION_12_6_REPORT_KO.md`에 있다.
