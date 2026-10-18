# 13.1 단계별 통합 로봇 실습

## 1. 무엇을 검증하는가

이 실습은 교육용 primitive 모델의 결합, 관절·TF·명령 소유권과 두 물리 엔진의 실행을 검증한다. 제품 Go1의 정밀 CAD 모델이나 실제 하드웨어 보정값이 아니다. 팔 장착은 `base_link → arm_mount`, 위치 `(-0.10, 0, 0.095)m`, 회전 `(0,0,0)rad`다. +X 전방, +Y 좌측, +Z 상방을 사용한다.

다리 순서는 fr/fl/rr/rl × hip/thigh/calf, 팔은 arm_joint_1~6, 손가락은 gripper_left_joint/right_joint다. 배열 순서는 신뢰하지 않고 이름으로 정렬한다. 기본 다리 자세는 `[0,-0.5,1] × 4`다. 원고의 18개는 손가락 2개를 제외한 수다.

## 2. 준비 환경

검증 환경은 Ubuntu 24.04 (Windows의 WSL2), ROS 2 Jazzy, Gazebo Harmonic, Python 3.12, MuJoCo 3.3.7이다. Windows 네이티브 Python만으로 ROS/Gazebo가 실행되는 것은 아니다. 여기서 네이티브 실행은 실제 로컬 엔진 실행을 뜻하며 원격 시뮬레이터로 대체하지 않았다.

ROS Jazzy 및 ros_gz가 이미 설치된 Ubuntu 셸을 사용한다. 필요한 시스템 의존성 예시:

```bash
sudo apt install python3-venv python3-colcon-common-extensions \
  ros-jazzy-xacro ros-jazzy-robot-state-publisher ros-jazzy-ros-gz \
  liburdfdom-tools libegl1
```

저장소 루트로 이동한 뒤 Ch13만 설치한다. 이전 장 overlay가 source된 셸은 닫고 새 셸을 사용한다.

```bash
source /opt/ros/jazzy/setup.bash
python3 -m venv --system-site-packages Ch13/.venv
source Ch13/.venv/bin/activate
python -m pip install -e 'Ch13[test]'
python -c 'import ch13_sim_core, mujoco; print(mujoco.__version__)'
```

PyTorch/SB3는 기본 실행에 필요하지 않다. 정책 실습을 추가할 때만 별도 설치한다. ROS 노드가 가상환경 Python으로 설치되도록 아래처럼 `python /usr/bin/colcon`을 사용한다.

## 3. 독립 빌드와 모델 검사

```bash
cd Ch13/ros2_ws
python /usr/bin/colcon --log-base log13_1 build \
  --build-base build13_1 --install-base install13_1 --symlink-install
source install13_1/local_setup.bash
cd ../..
ros2 pkg prefix ch13_control
ros2 pkg prefix ch13_robot_description
xacro Ch13/ros2_ws/src/ch13_robot_description/urdf/integrated_robot.urdf.xacro > /tmp/ch13.urdf
check_urdf /tmp/ch13.urdf
python -m pytest Ch13/tests Ch13/ros2_ws/src/ch13_control/test -q
```

두 prefix는 Ch13/install13_1 아래여야 한다. Xacro에는 base_footprint 루트가 하나만 있어야 하며 tool0까지 연결되어야 한다. 기존 장의 설치 경로가 나타나면 셸 환경을 정리한다. 루트 관성에 대한 KDL 경고는 알려진 한계다. 작은 양의 루트 관성은 Gazebo 변환에서 자식 링크가 소실되는 문제를 피하지만, KDL은 루트 관성을 계산에 사용하지 않는다.

## 4. 안전 기본값으로 MuJoCo 실행

```bash
export ROS_DOMAIN_ID=181
ros2 launch ch13_control mobile_manipulation.launch.py backend:=mujoco
```

기본 `enabled:=false`는 그룹 동작 생산자를 비활성화한다. 물리 엔진의 위치 actuator와 중재기의 nominal hold까지 꺼지는 것은 아니다. 즉 Torque Off가 아니다. 팔 동작을 명시적으로 선택하려면:

```bash
ros2 launch ch13_control mobile_manipulation.launch.py \
  backend:=mujoco enabled:=true fixture_demo:=true
```

fixture_demo는 관절 공간의 고정된 닫기·들기 시퀀스이며 IK/MoveIt 경로 계획이 아니다. `Ctrl+C`로 종료한다. 기본 headless MuJoCo는 화면 대신 상태를 발행한다. 대표 프레임은 다음 검증기가 저장한다.

```bash
MUJOCO_GL=egl python Ch13/scripts/verify_mujoco.py \
  --output Ch13/evidence/mujoco/result.json --image Ch13/evidence/mujoco/frame.png
python Ch13/scripts/ros_probe.py --backend mujoco \
  --output Ch13/evidence/mujoco/ros-result.json
```

MuJoCo의 success 조건은 실제 cube–양 손가락 접촉, 높이 증가 ≥0.03m, tool/cube 상대 이동 ≤0.025m, 연속 유지 ≥0.5s다. weld/attach/물체 teleport를 사용하지 않는다. 25g 정육면체와 2.0 손가락 마찰, 800N/m 그리퍼 위치 gain으로 제한된 fixture를 검사한다. 기립 후 팔 어깨를 2초간 -0.20rad로 들어 올린다. 초기 배치 이외에는 물리 상태를 직접 수정하지 않는다.

## 5. Gazebo 실행과 독립 판정

앞 실행을 완전히 종료한 뒤 새 domain/partition을 사용한다.

```bash
export ROS_DOMAIN_ID=182
export GZ_PARTITION=ch13_student_gazebo
ros2 launch ch13_control mobile_manipulation.launch.py \
  backend:=gazebo enabled:=true headless:=true
```

GUI가 가능한 환경은 `headless:=false`로 Gazebo 창을 띄울 수 있다. 이번 검증은 headless 서버 기준이며 GUI 조작은 미검증이다. MuJoCo의 headless:=false GUI viewer는 현재 구현하지 않았으므로 MuJoCo는 검증 프레임을 사용한다.

```bash
bash Ch13/scripts/verify_gazebo.sh
```

이 검증기는 fixture_demo를 선택하고 서버 종료 응답·잔여 프로세스까지 기록한다. 통합 경로는 PASS였지만 현재 Gazebo 파지는 FAIL이다. 물체 위치는 관측했으나 양 손가락 접촉이 확인되지 않았고, 상승량도 기준 미달이다. MuJoCo 파지 결과로 Gazebo 성공을 대체하지 않는다. Gazebo PID/접촉 해석과 초기 미끄러짐 때문에 물리 결과가 동일하지 않으며, 안정적 정지는 높이·roll/pitch 한계 검사이지 XY 위치 유지 보장은 아니다.

## 6. 데이터 흐름 확인

```text
hold 또는 선택적 PPO(다리) / hold·fixture(팔·그리퍼)
  → /ch13/command/legs, /arm, /gripper
  → command_arbiter → /ch13/command/actuators (20개, 단일 발행자)
  → mujoco_bridge 또는 gazebo_router → 물리 엔진
엔진 → /ch13/joint_states_raw → state_monitor → /joint_states
```

```bash
ros2 topic info /ch13/command/actuators --verbose
ros2 topic echo /ch13/status/command
ros2 topic echo /joint_states --once
ros2 topic hz /clock
```

같은 그룹의 두 생산자를 동시에 켜지 않는다. 발행자 충돌·이름 누락·NaN·잘못된 그룹·미래/역순/만료 명령은 거부한다. 만료 시 마지막 안전 목표를 유지한다. simulation clock 역행 후 중재기는 새 epoch를 추측하지 않고 재시작을 요구한다. clock 정지는 물리 명령의 마지막 목표 hold이지 실시간 제어 보장이 아니다.

중재기는 초기 clock 확인 전의 입력을 거부한다. 유효한 입력도 즉시 safe target을 바꾸지 않고 pending에 보관하며, clock이 엄격히 전진한 다음 tick에서만 적용한다. 따라서 최대 한 제어 주기의 추가 대기가 있으며, 정지한 clock에서는 새 목표를 적용하지 않는다. 재개 시 이미 만료된 pending은 적용하지 않는다.

TF 경계는 엔진 어댑터의 `odom → base_footprint`와 robot_state_publisher의 그 아래다. Gazebo 관측 브리지는 GZ_TO_ROS 전용이다. 20개 cmd_pos는 네이티브 router가 각각 하나만 발행한다. Jazzy 콜백에는 per-message GID가 없어 그래프 endpoint와 child-parent 유일성을 검사했으며, 모든 TF 메시지의 발행자를 패킷별로 식별한 것은 아니다.

## 7. 선택적 PPO와 명확한 한계

```bash
ros2 launch ch13_control mobile_manipulation.launch.py backend:=mujoco \
  leg_controller:=ppo bundle_path:=/absolute/path/to/bundle enabled:=true
```

필수 파일은 manifest.json과 best_model/best_model.zip이다. schema `locomotion-v1-48`, 48차원 관측·12차원 action·normalization none만 허용한다. `[0,-.5,1]×4`, action scale .35rad, 50Hz sim-time, 추론 예산 20ms다. 팔/그리퍼 입력은 이름으로 제외하며 출력도 다리 12개뿐이다. 설치된 Ch12.8 manifest에는 2,048 transitions만 기록되어 있고 가중치 ZIP은 저장소에 없다. 따라서 실제 정책 추론 smoke와 안정 보행은 미검증이다. 토치 모델 로드는 신뢰하는 번들에만 수행한다.

## 8. 전체 검증과 문제 해결

활성 엔진을 종료한 뒤 저장소 루트에서 실행한다.

```bash
python Ch13/scripts/verify_all.py
```

수 분이 걸릴 수 있다. 빌드·전체 테스트·colcon test·실제 엔진을 순차 실행해 evidence를 새로 만든다. summary의 PARTIAL은 Gazebo 파지 실패를 숨기지 않는 결과이며 전체 pick-and-place 성공이 아니다. 각 실행의 코드 SHA, dirty 경로, 명령·시간·소스 해시를 함께 확인한다.

- import 실패: 가상환경 활성화와 Ch13 local_setup 여부를 확인한다. launch Python과 노드 실행 Python이 다를 수 있다.
- `/clock`이 2개: 다른 엔진을 종료하거나 다른 ROS_DOMAIN_ID를 사용한다.
- EGL 오류: 렌더링 라이브러리/드라이버를 확인한다. 렌더 실패를 물리 검증 성공으로 간주하지 않는다.
- 관절이 움직이지 않음: enabled, 그룹 소유권, 시각·이름 및 command 진단을 확인한다.
- 이전 branch 산출물 혼입: build13_1/install13_1/log13_1만 사용한다. 다른 작업 디렉터리를 임의로 삭제하지 않는다.
- 종료 문제: 검증기는 자기 launch process group만 정리한다. 사용자 프로세스를 광역 종료하지 않는다.
