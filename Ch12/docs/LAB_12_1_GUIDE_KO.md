# 12.1절 실습: 상태·행동·보상을 실제 물리 시뮬레이션으로 확인하기

## 1. 실습 목표

본문 코드 12-1의 생략된 부분을 채운 `QuadrupedEnv`를 실행한다. 로봇에 12개 토크를 입력하고 관측 벡터와 보상을 확인한 뒤, 낙상으로 에피소드가 끝나는 과정까지 관찰한다. 무작위 행동과 PD 자세 유지 제어를 비교한다. 이번 절은 학습 환경을 이해하는 실습이며 PPO 학습이나 자율 보행 성공을 뜻하지 않는다.

## 2. 준비와 설치

리포지토리 루트에서 실행한다. Python 3.10 이상이 필요하다. 검증 환경은 Ubuntu 24.04/WSL2의 Python 3.12다. MuJoCo와 Gymnasium 버전은 패키지에 고정했다. ROS용 시스템 Python과 학습용 가상환경을 구분한다.

```bash
git clone https://github.com/silverbjin/Pysical_AI_ROS2.git
cd Pysical_AI_ROS2
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e './Ch12[test,visual]'
python -m pytest Ch12
```

Windows에서도 MuJoCo 실습을 사용할 수 있다. PowerShell에서는 `py -3 -m venv .venv`로 환경을 만들고 `.\.venv\Scripts\Activate.ps1`로 활성화한 뒤 같은 pip·실습 명령을 사용한다. Windows 실행은 별도 검증 결과가 없는 한 지원 경로 안내로 해석한다. Gazebo 비교 실습은 Ubuntu/WSL에서 수행한다.

WSL에서는 많은 작은 파일을 만드는 가상환경을 Linux 파일시스템에 두면 `/mnt/c`보다 설치가 빠르다. 예: `python3 -m venv ~/venvs/ch12` 후 `source ~/venvs/ch12/bin/activate`.

## 3. 먼저 무작위 행동을 관찰한다

```bash
quadruped-rl --policy random --steps 1000 --seed 42 --output Ch12/evidence/my_random.json
quadruped-rl --policy random --steps 1000 --seed 42 --observation-mode full
```

명령은 총 제어 스텝 수만큼 실행하며, 낙상·시간 제한 시 reset하고 계속한다. 요약에는 실행 스텝, 끝난 에피소드 수, 누적 보상, 물리 시간 합계가 포함된다. 무작위 토크로 로봇이 넘어져도 예외나 실패로 숨기지 않고 `terminated`로 기록한다.

```python
import numpy as np
from quadruped_rl import QuadrupedEnv

with QuadrupedEnv(observation_mode="full") as env:
    obs, info = env.reset(seed=42)
    action = np.zeros(12, dtype=np.float32)
    obs, reward, terminated, truncated, info = env.step(action)
    print(obs.shape, reward, terminated, truncated)
    print(info["reward_terms"])
```

실행은 `mujoco.mj_step(model, data)`를 실제 호출한다. 기본 물리 간격은 0.002초, 한 행동을 5번 적용하므로 제어 간격은 0.01초(100 Hz)다. 물리 시간과 실행에 걸린 실제 시간을 구분한다.

## 4. 관측과 행동 규격

| 슬라이스 | 항목 | 단위·좌표계 |
|---|---|---|
| `0:3` | 몸체 roll, pitch, yaw | rad, 월드 기준 XYZ 고정축 RPY |
| `3:6` | 몸체 각속도 | rad/s, 몸체 좌표계 |
| `6:18` | 12개 관절 위치 | rad, 모델의 관절 영점 기준 |
| `18:30` | 12개 관절 속도 | rad/s |
| `30:33` | 몸체 선속도, full에서 추가 | m/s, 월드 좌표계 |
| `33:45` | 직전 적용한 정규화 행동, full에서 추가 | [-1, 1], reset 시 0 |

기본 `textbook` 모드는 코드 12-1과 같은 30차원이다. 본문에서 언급한 선속도와 이전 행동까지 포함하려면 `full`을 사용한다. 둘을 혼용하여 학습한 정책을 불러오면 입력 차원이 달라지므로 같은 모드를 유지한다. 45차원도 몸체 높이·접촉 상태·남은 시간 등을 생략한 입문용 관측이다. 완전한 마르코프 상태를 보장하는 설계는 아니며, 본격적인 학습에서는 관측 설계를 확장해야 한다.

관절과 행동 순서는 다음과 같다.

```text
fr_hip, fr_thigh, fr_calf,
fl_hip, fl_thigh, fl_calf,
rr_hip, rr_thigh, rr_calf,
rl_hip, rl_thigh, rl_calf
```

fr/fl/rr/rl은 앞오른쪽/앞왼쪽/뒤오른쪽/뒤왼쪽이다. 정규화 행동 ±1은 각 다리의 hip ±20 N·m, thigh/calf ±30 N·m에 대응한다. 범위를 초과한 유한 행동은 [-1, 1]로 제한하며 `info['action_clipped']`로 표시한다. 크기가 (12,)가 아니거나 NaN/Inf가 있으면 상태를 변경하기 전에 ValueError를 발생시킨다.

## 5. 보상과 종료 읽기

| 보상 항목 | 식 | 의미 |
|---|---|---|
| survival | 기립 시 +1, 낙상 시 0 | 넘어지지 않기 |
| velocity | `exp(-((vx - target_velocity) / 0.5)**2)` | 목표 전진 속도 추종 |
| energy | `-0.002 * mean(abs(torque * joint_velocity))` | 기계적 출력 크기 억제 |
| action_rate | `-0.01 * mean((action - previous_action)**2)` | 급격한 행동 변화 억제 |
| fall | 낙상 시 -5, 그 외 0 | 낙상 페널티 |

반환 보상은 위 항목의 합이다. 에너지는 전력에 비례한 교육용 패널티이며 배터리 소비 모델이 아니다. 기본 목표 속도는 월드 X축 +0.5 m/s다. 이 식만으로 안정적인 보행 학습이 보장되지 않는다.

몸체 높이가 0.14 m 미만이거나 몸체 수직축 기울기가 60°를 넘거나 몸체가 바닥과 접촉하면 `terminated=True`다. 기본 1,000 제어 스텝(10초)에 도달하면 `truncated=True`다. 두 조건은 같은 스텝에 동시에 참일 수 있다. 종료 후에는 `reset()`해야 한다. 비유한 물리 상태는 보상으로 덮지 않고 FloatingPointError로 알려준다.

## 6. 자세 유지 제어 및 화면 보기

```bash
quadruped-rl --policy stand --steps 1000 --target-velocity 0
quadruped-rl --policy stand --steps 1000 --target-velocity 0 --render
```

`stand`는 관절 명목 자세를 유지하려는 PD 제어다. 학습된 신경망 정책이 아니며 목표 전진 속도를 따라 걷지 않는다. 이 실습에서는 무작위 토크와 피드백 제어의 상태·보상 차이를 비교하는 용도다. WSLg에서 창이 열리지 않으면 `echo $DISPLAY`와 WSLg 설정을 확인한다.

화면 없는 물리 검증과 RGB 이미지 검증은 다음 명령으로 재현한다.

```bash
python Ch12/scripts/verify_mujoco.py --output Ch12/evidence/my_mujoco.json
MUJOCO_GL=egl python Ch12/scripts/verify_mujoco.py \
  --output Ch12/evidence/my_mujoco_render.json --image Ch12/evidence/my_frame.png
```

EGL은 Linux의 화면 없는 렌더링 경로다. OpenGL/EGL 라이브러리와 드라이버가 필요하며 Windows에서는 `MUJOCO_GL=egl` 설정 없이 실행한다.

## 7. 실제 Gazebo와 비교한다

새 Ubuntu/WSL 터미널에서 가상환경을 활성화하지 않은 상태로 실행한다. Ubuntu 24.04, ROS 2 Jazzy, Gazebo Harmonic 및 Ch11의 ROS 의존성이 필요하다. 기존 설치 방법은 [Ch11 가이드](../../Ch11/docs/FIGURE_11_2_GUIDE_KO.md)를 참고한다.

```bash
bash Ch12/scripts/verify_gazebo.sh
```

Ch11의 `my_quadruped_bot`과 인터페이스를 빌드한 뒤 Gazebo와 기존 기립 제어기를 실행한다. 기본 DDS domain 82가 사용 중이면 다른 값을 선택한다.

```bash
CH12_DOMAIN_ID=83 CH12_GAZEBO_EVIDENCE=/tmp/ch12-gazebo \
  bash Ch12/scripts/verify_gazebo.sh
```

스크립트는 실제 시뮬레이션 8초 이후부터 30초 동안 몸체 높이 0.20~0.30 m, 기울기 5° 미만, 여섯 데이터 스트림의 수신·최신성, 유효 LiDAR 반환, TF 연결을 검사한다. 결과는 `evidence/gazebo/result.json`, 실행 로그는 같은 디렉터리에 저장한다. 실험 전용 GZ_PARTITION의 `/server_control` 서비스로 Gazebo를 종료한 다음 ROS launch를 정리한다. 강제 정리가 필요하거나 오류 로그가 있으면 최종 FAIL로 처리한다. 관측 통과 여부는 `observation.status`, 종료 검사는 `shutdown_clean`과 `gazebo_stop_ack`에서 확인할 수 있다.

종료 오류 검사는 launch의 `[ERROR]`/Python traceback을 대상으로 한다. 검증 환경에서는 프로세스 정상 종료 후에도 DDS의 `Failed to delete datawriter` 진단이 남았다. 결과 JSON의 PASS를 모든 종료 진단이 해소됐다는 뜻으로 해석하지 않는다. 상세 내용은 수정 보고서에 기록했다.

Gazebo의 기존 관절 위치 제어와 MuJoCo의 토크 행동은 제어 계층이 다르다. MJCF는 Ch11의 주요 치수·질량·관절 영점과 범위를 반영한 교육용 모델이다. LiDAR 등의 부착물은 생략하고, 관성은 형상에서 계산하며, 다리는 capsule로 근사한다. 로봇 자체 충돌은 비활성화하고 지면 접촉은 활성화한다. 따라서 두 엔진의 보상·기립 높이·계산 속도를 정량적으로 같은 조건의 성능 비교라고 해석하지 않는다.

## 8. 권장 진행 순서와 기록

1. 테스트를 실행하고 30/45차원 관측값의 각 구간을 출력한다.
2. 같은 seed로 두 번 실행해 재현성을 확인한다.
3. 무작위 행동과 stand를 실행하고 종료 횟수와 보상 항목을 비교한다.
4. `--target-velocity 0`과 `0.5`의 속도 보상 차이를 관찰한다.
5. Gazebo 비교 검증을 실행해 기존 제어의 실제 기립과 센서 흐름을 확인한다.
6. 로봇 모델·관측·토크·제어 주기를 기록한 뒤 다음 절의 학습 환경 확장으로 넘어간다.

검증 결과와 수정 내역은 [보고서](CHANGE_REPORT_KO.md)에 기록한다. MuJoCo/Gymnasium API 근거: [MuJoCo Python](https://mujoco.readthedocs.io/en/3.3.7/python.html), [Gymnasium Env](https://gymnasium.farama.org/api/env/).
