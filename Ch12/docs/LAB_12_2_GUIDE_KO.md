# 12.2절 실습: MuJoCo와 Gymnasium 학습 환경 구축

## 1. 실행 준비

리포지토리 루트에서 Python 3.10 이상을 사용한다. 실제 검증 환경은 Ubuntu-24.04 WSL2, Python 3.12, ROS 2 Jazzy/Gazebo Harmonic이다. MuJoCo 실습 자체는 ROS가 필요 없다.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e './Ch12[test,visual]'
python -m pytest Ch12 -q
```

WSL에서는 Linux 파일시스템에 가상환경을 두면 설치가 빠르다. Windows PowerShell에서는 `py -3 -m venv .venv`, `.\.venv\Scripts\Activate.ps1`을 사용하고 같은 pip 명령을 실행한다. Windows 네이티브 실행은 이번 WSL 검증과 구분한다. Matplotlib은 본 실습 코드가 사용하지 않아 필수 의존성에 넣지 않았다.

## 2. 12.1절과 12.2절의 환경 구분

| 항목 | 12.1절 기본 | 12.2절 기본 |
|---|---|---|
| 클래스 | `quadruped_rl.QuadrupedEnv` | `quadruped_rl.QuadrupedTrainingEnv` |
| 본문 호환 import | 해당 없음 | `from quadruped_env import QuadrupedEnv` |
| 관측 | RPY 기반 30차원, 선택 45차원 | 쿼터니언 기반 31차원 |
| 물리 간격 | 0.002초 | 0.002초 |
| frame_skip | 5 | 10 |
| 제어 간격 | 0.01초, 100 Hz | 0.02초, 50 Hz |
| 기본 행동 의미 | 관절 토크 | 명목 자세 주위 목표 관절각 |
| reset 높이 / 낙상 높이 | 0.41 / 0.14 m | 0.50 / 0.20 m |
| 기본 시간 제한 | 1,000 스텝, 10초 | 1,000 스텝, 20초 |

기존 `quadruped-rl` 명령의 기본은 계속 12.1절이다. 새 실습에는 `--section 12.2`를 지정한다. 관측 모드나 제어 방식을 바꾸면 정책 입력·행동의 의미가 달라지므로 이전 정책을 그대로 재사용하지 않는다.

## 3. 코드 12-2: 실제 12관절 MJCF 읽기

`src/quadruped_rl/models/` 아래에 다음 모델을 제공한다.

- `quadruped_body.xml`: 몸체·네 다리·관성·접촉·바닥·카메라·물리 설정.
- `quadruped_position.xml`: 공통 기구부를 include하고 12개 position actuator를 정의.
- `quadruped.xml`: 같은 기구부와 12개 motor actuator를 사용하여 토크 제어 지원.

위 경로는 `Ch12` 기준이다. 별도 STL 다운로드가 필요 없다. 몸체는 box, 다리는 capsule, 발은 sphere로 모델링했다. 외형 메시와 충돌 형상은 반드시 같을 필요가 없으며, 교육용 충돌 형상과 질량으로 안정적인 실행 기반을 제공한다. 자체 충돌은 비활성화하고 지면 접촉은 활성화했다.

위치 모델의 핵심 구조는 다음과 같다. 실제 파일에는 네 다리의 모든 actuator가 있다.

```xml
<mujoco model="quadruped_position">
  <include file="quadruped_body.xml"/>
  <actuator>
    <position name="fr_hip_motor" joint="fr_hip_joint" gear="1"
      kp="40" kv="2" ctrllimited="true" ctrlrange="-.8 .8"
      forcelimited="true" forcerange="-20 20"/>
  </actuator>
</mujoco>
```

MJCF 각도는 `radian`을 명시한다. 기본 로컬 좌표계를 사용하므로 초안의 `coordinate="local"`은 생략했다. hip/thigh/calf의 kp는 각각 40/100/100, kv는 2/4/4다. actuator 출력 토크 한계는 ±20/±30/±30 N·m이다. 별도의 관절 수동 감쇠도 모델에 있다.

MuJoCo는 URDF를 읽고 `mj_saveLastXML`로 MJCF를 저장할 수 있지만, 저장했다고 바닥·freejoint·actuator·접촉 조건까지 자동 완성되는 것은 아니다. ROS의 xacro는 먼저 URDF로 확장해야 한다. 이 실습은 검증된 MJCF를 직접 제공한다. 자기 로봇으로 바꿀 때는 관성, 관절 영점과 범위, actuator 순서·힘 제한, 초기 발 위치를 다시 검증한다.

## 4. 코드 12-3/12-4: reset, step, 관측

```python
import numpy as np
from quadruped_env import QuadrupedEnv

with QuadrupedEnv() as env:
    observation, info = env.reset(seed=42)
    print(observation.shape, env.dt)  # (31,), 0.02
    action = np.zeros(12, dtype=np.float32)
    observation, reward, terminated, truncated, info = env.step(action)
    print(info["control_mode"], info["reward_terms"])
```

패키지 자산 경로를 기준으로 모델을 읽으므로 실행 디렉터리가 달라도 `robot.xml`을 찾지 못하는 문제가 없다. reset은 free base 위치·단위 쿼터니언·명목 관절각·시드 노이즈·이전 행동·시간·제어값을 초기화하고 `mj_forward`를 호출한다.

31차원 관측은 다음과 같다. 결과는 float32 배열이다.

| 슬라이스 | 정보 | 좌표계·단위 |
|---|---|---|
| `0:4` | 몸체 쿼터니언 `[w, x, y, z]` | 월드 기준 자세 |
| `4:7` | `qvel[3:6]` 몸체 각속도 | 몸체 좌표계, rad/s |
| `7:19` | 12개 관절 위치 | rad, 모델 영점 기준 |
| `19:31` | 12개 관절 속도 | rad/s |

초안의 `_get_obs()`는 각속도 자리에 `qvel[:3]`을 넣는데, 이 값은 월드 좌표계의 **선속도**다. 구현에서는 `qvel[3:6]`으로 바로잡았다. 관절 인덱스는 이름으로 찾으며, 순서는 fr/fl/rr/rl × hip/thigh/calf다.

이 31차원 관측은 높이·선속도·접촉 상태·직전 행동을 생략한 입문용 부분 관측이다. 실제 걷기 학습의 충분한 마르코프 상태라고 단정하지 않는다.

## 5. 행동의 의미: 위치와 토크

위치 제어의 0 행동은 모든 관절을 0 rad로 보내는 명령이 아니다. 각 다리의 명목 자세 `[0, -0.5, 1.0] rad`를 유지한다.

```text
목표 관절각 = clip(명목 관절각 + 0.35 × clip(action, -1, 1), 관절 하한, 관절 상한)
```

정규화 행동은 12개이고 크기 (12,)여야 한다. NaN/Inf 입력은 물리 계산 전에 거부한다. 유한한 범위 초과 값은 제한하고 `info['action_clipped']`에 표시한다. `data.ctrl`에 목표 각도가 들어가고 MuJoCo가 각 물리 스텝에서 PD 출력을 계산한다. 출력 힘 한계도 MJCF에서 제한한다.

```bash
quadruped-rl --section 12.2 --control-mode position --policy stand --target-velocity 0
quadruped-rl --section 12.2 --control-mode torque --policy stand --target-velocity 0
```

토크 모드는 정규화 행동에 hip/thigh/calf의 20/30/30 N·m를 곱한다. 같은 숫자의 행동이라도 위치 모드와 의미가 다르다. stand는 위치 모드에서 0 행동을, 토크 모드에서 외부 PD 토크를 사용한다. 어느 것도 학습한 정책이 아니다.

외부 토크 PD는 제어 주기에 맞춰 조정했다. 50 Hz에서는 kp 40/100/100, kd 2/2/2를 사용하며, 기존 100 Hz의 kd 2/4/4를 유지한다. 내부 position actuator의 PD는 물리 500 Hz에서 계산되므로 목표를 50 Hz로 주더라도 같은 외부 PD 계수를 그대로 옮기는 문제가 없다. 사용자 임의의 다른 제어 주기에서 이 계수의 안정성을 보장하지 않는다.

에너지 페널티는 목표 각도가 아니라 실제 actuator 출력 토크와 관절 속도로 계산한다. 기본 보상은 12.1절의 생존·목표 속도 추종·에너지·행동 변화·낙상 항목을 재사용한다. 초안의 전진 속도만으로 주는 보상보다 해석할 항목을 늘렸으며, 자세한 보상 설계는 12.3절에서 확장할 수 있다.

## 6. 코드 12-5: 무작위 움직임과 렌더링

```bash
python Ch12/examples/12_2_random_motion.py --steps 1000 --seed 42
python Ch12/examples/12_2_random_motion.py --render --steps 1000 --seed 42
quadruped-rl --section 12.2 --policy stand --render --target-velocity 0
```

기본 실행은 유한한 1,000 스텝이며 종료·시간 제한 후 reset하고 계속한다. `--output PATH`로 요약을 저장한다. human 모드에서는 이미 step 내부에서 화면을 동기화하므로 별도의 `env.render()` 중복 호출이 필요 없다. 실제 시간 대기는 계산 시간을 뺀 제어 간격만큼 수행한다. Ctrl+C를 누르면 with 블록이 viewer를 정리하고 CLI는 종료 코드 130으로 끝난다.

제한된 위치 명령과 PD 제어에서는 random 정책도 20초 동안 넘어지지 않을 수 있다. 실제 검증의 세 시드 모두 그러했다. 이는 학습 성공을 뜻하지 않는다. 같은 명령에 `--control-mode torque`를 추가하면 무작위 토크에 의한 낙상과 reset을 더 분명하게 관찰할 수 있다.

```bash
quadruped-rl --section 12.2 --policy random --steps 1000 \
  --output Ch12/evidence/my_12_2_run.json
MUJOCO_GL=egl python Ch12/scripts/verify_training_env.py \
  --output Ch12/evidence/my_12_2_check.json --image Ch12/evidence/my_12_2_frame.png
```

EGL은 Linux의 화면 없는 RGB 경로다. viewer는 WSLg/OpenGL을 사용한다. 수동 viewer 검증은 EGL 설정 없이 `python Ch12/scripts/verify_training_env.py --output /tmp/human.json --human`으로 실행한다. optional `visual` 의존성은 이미지 저장을 위한 Pillow를 제공한다. Gymnasium 내부 렌더링 클래스 대신 MuJoCo 공개 viewer/Renderer API를 사용한다.

## 7. 종료와 수치 오류

몸체 높이 0.2 m 미만, 수직축 기울기 60° 초과, 몸통-바닥 접촉이면 terminated다. frame_skip 동안 한 번 검출된 낙상은 반발로 다시 올라와도 종료로 유지한다. 1,000 제어 스텝이면 truncated다. 두 조건은 동시에 참일 수 있다. 종료 후에는 reset해야 한다.

NaN/Inf 상태나 MuJoCo의 BADQPOS/BADQVEL/BADQACC 경고는 FloatingPointError로 알려주고 reset을 요구한다. MuJoCo가 발산 뒤 자동 초기화하여 유한한 배열을 반환하더라도 성공 스텝으로 숨기지 않는다. 일부 테스트는 이 경로를 확인하기 위해 의도적으로 큰 속도를 넣어 엔진 경고를 발생시킨다.

## 8. 권장 실습 순서와 검증

1. 본문 호환 import로 31차원 관측과 0.02초 물리 시간 증가를 확인한다.
2. 동일 seed를 사용해 상태·행동 결과가 재현되는지 확인한다.
3. 위치 모드에서 0과 ±1 행동을 넣고 목표 관절각·실제 actuator 출력을 구분한다.
4. 위치/토크의 random/stand를 비교하고 낙상·시간 제한·보상 항목을 기록한다.
5. viewer 및 RGB 이미지를 확인한다. 다음 명령으로 렌더 테스트까지 실행한다.

```bash
CH12_TEST_RENDER=1 MUJOCO_GL=egl python -m pytest Ch12 -q
```

Gazebo 회귀는 학습 가상환경을 비활성화한 별도 WSL 터미널에서 실행한다.

```bash
CH12_GAZEBO_EVIDENCE=Ch12/evidence/my_12_2_gazebo bash Ch12/scripts/verify_gazebo.sh
```

Gazebo는 기존 Ch11의 관절 위치 제어, MuJoCo는 이번 절의 actuator 모델을 사용하므로 두 엔진의 동역학이 동일하다는 검증은 아니다. 실행 증거·남은 진단·검증 범위는 [12.2절 보고서](SECTION_12_2_REPORT_KO.md)에 기록한다.

API 근거: [MuJoCo 3.3.7 MJCF](https://mujoco.readthedocs.io/en/3.3.7/XMLreference.html), [Python viewer](https://mujoco.readthedocs.io/en/3.3.7/python.html), [Gymnasium Env](https://gymnasium.farama.org/api/env/).


---

## 원고 연계 실습 보강 (2026-10-21 리뷰)

**학습 도달점:** Gymnasium·MuJoCo 위치 제어 환경. 예제 코드의 목적과 실제 패키지의 제어·관측 계약을 구분하고, 재현 가능한 증거를 제출한다. 실행 위치는 `Pysical_AI_ROS2/` 저장소 루트다(기존 가이드가 별도 경로를 지정한 경우 그 지시를 우선한다).

### 따라하기: 최소 검증 루트

```bash
python -m pip install -e './Ch12[test,visual]'
python -m pytest Ch12/tests/test_training_env.py -q
quadruped-rl --section 12.2 --control-mode position --policy stand --steps 1000
python Ch12/examples/12_2_random_motion.py --steps 200 --seed 42
```

### 관찰 → 설명 → 응용

먼저 stand 위치 제어, 이어 random 위치 제어, 마지막에 토크 제어를 비교한다. `reset(seed=42)` 이후 `step(np.zeros(12))`가 관측 31개·보상 유한값을 반환하는지 확인한다. `render`가 불가능한 서버에서는 headless 결과로 판정하고 WSLg 검증을 하지 않은 사실을 명시한다. 한 제어 스텝이 물리 스텝 10회임을 직접 계산한다.

### 제출 증거 및 합격선

- 실행 명령과 사용 Python/라이브러리 버전, git 기준 커밋, seed, 주요 출력 수치/로그를 기록한다.
- **합격선:** 31차원과 frame_skip·dt·제어 50 Hz를 확인하고, 위치/토크 명령을 분리해 설명한다. headless CLI가 오류 없이 끝나고 시각화 선택 시 정상 종료해야 한다.
- 기존 `evidence/`는 **과거 실행 기록**이고 위 명령을 새로 실행한 증거가 아니다. GUI·물리 엔진·ROS 환경을 실제로 확인하지 못했다면 '미검증'으로 기록한다.
- 보고서: [12.2절 코드 리뷰](SECTION_12_2_REPORT_KO.md). 기존 학습/시연 스크립트와 구성 파일 설명은 이 문서의 위쪽 절에 그대로 보존한다.
