# 13.3 시스템 아키텍처 실습

13.2 모델 위에서 실제 ROS 2 lifecycle 서비스, 액션과 message_filters를 실행한다.
이 절의 목표는 제어·인지·임무 통신을 분리하고 실패 상황을 재현하는 것이다.

## 1. 준비와 빌드

13.2 가이드의 Ubuntu 24.04 / ROS 2 Jazzy / Gazebo Harmonic 설치를 먼저 완료한다.
MuJoCo는 `Ch13/ros2_ws/mujoco_ros2_control.repos`의 고정 커밋을 source build한다.
기존 Ch05~Ch12를 빌드하거나 source할 필요가 없다.

```bash
cd <저장소-루트>
source /opt/ros/jazzy/setup.bash
sudo apt install -y ros-jazzy-message-filters python3-pytest
cd Ch13/ros2_ws
colcon build --symlink-install
source install/setup.bash
ros2 interface show integrated_robot_interfaces/action/PickObject
ros2 interface show integrated_robot_interfaces/srv/SetMode
```

## 2. 노드와 통신

| 노드 | 입력/서비스/액션 | 출력과 역할 |
|---|---|---|
| `locomotion_node` | `/joint_states`, `~/set_mode` | 50Hz 목표의 다리 기립 기준; 12개 위치 명령 |
| `manipulation_node` | `~/stow`, `~/pick_object` | 팔 안전 영점 궤적; PickObject 프로토콜 실습 |
| `state_manager` | 두 노드의 lifecycle 및 stow 서비스 | 기동 순서·측정 gate·실패 rollback |
| `vision_processor` | `/architecture/image_raw`, `/architecture/odom` | 50ms 이내 시각 쌍, 최신 1쌍 작업 큐 |
| `mission_commander` | `~/rehearse_pick` | 명시적 사용자 요청을 PickObject 액션으로 전달 |

노드마다 별도 프로세스를 사용한다. 제어 노드의 상태 갱신과 타이머에는 분리된
콜백 그룹, 팔 액션·서비스에는 Reentrant 그룹과 4개 실행기 스레드를 사용한다.
무거운 인지 처리는 최신 1쌍만 유지하는 전용 작업자로 전달한다. Python GIL,
OS 스케줄러, 시뮬레이터 속도 때문에 20ms deadline을 보장하지는 않는다.

## 3. 두 터미널로 실행

터미널 A에서 13.2 엔진을 먼저 실행한다.

```bash
source /opt/ros/jazzy/setup.bash
source Ch13/ros2_ws/install/setup.bash
export ROS_DOMAIN_ID=133
ros2 launch integrated_robot_description gazebo.launch.py
# MuJoCo 사용 시 mujoco.launch.py로 바꾼다.
```

네 컨트롤러가 active인지 확인한 뒤 터미널 B에서 런타임을 실행한다.

```bash
source /opt/ros/jazzy/setup.bash
source Ch13/ros2_ws/install/setup.bash
export ROS_DOMAIN_ID=133
ros2 launch integrated_robot_runtime architecture.launch.py processing_delay_s:=0.2
```

출력 `/architecture/startup`에서 `READY`와 다음 순서를 확인한다.

```text
arm_configured → legs_configured → arm_active → arm_safe → legs_active
```

`arm_safe`는 2초짜리 영점 궤적 액션 성공 및 500ms 이내 관절 상태 확인을 모두 요구한다.
팔 영점은 13.2의 위로 뻗은 초기 자세다. 운반용으로 접힌 자세나 충돌 없는 임의
경로 계획을 의미하지 않는다. 알려진 13.2 초기 자세에서 이 기동 절차를 실습한다.

## 4. 모드 서비스와 임무 액션

```bash
ros2 service call /locomotion_node/set_mode integrated_robot_interfaces/srv/SetMode '{mode: HOLD}'
ros2 service call /locomotion_node/set_mode integrated_robot_interfaces/srv/SetMode '{mode: STAND}'
ros2 service call /locomotion_node/set_mode integrated_robot_interfaces/srv/SetMode '{mode: WALK}'
ros2 service call /mission_commander/rehearse_pick std_srvs/srv/Trigger '{}'
```

STAND는 2초 보간으로 기립 목표에 접근하고 HOLD는 요청 당시 측정한 관절 위치를
유지한다. STOP은 새 명령 발행을 차단한다. WALK는 PPO 정책이 없으므로 거부한다.
`rehearse_pick`은 액션 흐름을 실행하지만 `success=false`와 미구현 메시지를 반환한다.
물체 파지를 성공했다고 보고하지 않는다. 취소 가능한 실제 PickObject 액션 서버는
`/manipulation_node/pick_object`에 있다.

목표는 `base_link` 프레임, 300ms 이내 시각, 유한 위치와 정규화된 quaternion을
요구한다. 다른 프레임은 상위 인지 모듈이 TF로 변환한 후 전달해야 한다.
시뮬레이션 clock 메시지 전달 순서 차이를 위해 최대 50ms 앞선 시각은 허용한다.
`dry_run=false`는 거부하며 동시에 한 목표만 허용한다. 경로 계획이 없어 거리
피드백은 NaN(알 수 없음)을 사용한다.

## 5. 실제 엔진 기반 자동 검증

아래 실행기는 자신이 시작한 엔진과 런타임만 종료한다. 기존 터미널 A/B는 먼저
Ctrl+C로 종료한다. 실행기에는 별도의 ROS_DOMAIN_ID와 Gazebo partition을 사용한다.

```bash
cd <저장소-루트>
source /opt/ros/jazzy/setup.bash
source Ch13/ros2_ws/install/setup.bash
ROS_DOMAIN_ID=133 python3 Ch13/scripts/run_architecture_13_3.py \
  --engine gazebo --output-dir Ch13/evidence/section_13_3/gazebo
ROS_DOMAIN_ID=134 python3 Ch13/scripts/run_architecture_13_3.py \
  --engine mujoco --output-dir Ch13/evidence/section_13_3/mujoco
ROS_DOMAIN_ID=135 python3 Ch13/scripts/run_architecture_13_3.py \
  --engine none --output-dir Ch13/evidence/section_13_3/startup_failure
```

검증기가 만드는 Image/Odometry는 시간 동기화 시험용 합성 데이터다. 실제 카메라나
SLAM 출력이라고 해석하지 않는다. 실제 입력 연결 시 해당 두 토픽을 remap하고
publisher/subscriber의 QoS를 맞춘다. 시험은 200ms 처리 지연 속에서 다리 명령 간격,
액션의 피드백·중복 거부·취소·미구현 실패, 오래된 센서 쌍 거부와 Inactive 출력
차단을 검사한다. engine none은 팔 컨트롤러 부재 시 rollback과 명령 0회를 검사한다.

```bash
python3 -m pytest -q Ch13/tests
cd Ch13/ros2_ws
colcon test
colcon test-result --verbose
```

네이티브 MuJoCo 테스트도 함께 실행하므로 pytest 환경에 `mujoco==3.3.7`, `numpy`,
`PyYAML`이 있어야 한다. ROS 패키지가 보이는 system-site-packages venv 사용을 권장한다.

```bash
cd <저장소-루트>
python3 -m venv --system-site-packages .venv
source .venv/bin/activate
pip install mujoco==3.3.7 numpy pytest PyYAML
source /opt/ros/jazzy/setup.bash
source Ch13/ros2_ws/install/setup.bash
python -m pytest -q Ch13/tests
```

플러그인 overlay와 가상환경은 재시작 때 사라질 수 있는 `/tmp` 대신 자신의
영속 작업 폴더에 보관한다. `/tmp/ch13_2_controllers_*.yaml`은 launch가 매번
원본 설정에서 다시 생성하는 캐시이므로 사라져도 된다.

## 6. 반드시 구분할 범위

- Lifecycle Inactive는 런타임 명령 차단이며 Torque Off가 아니다. 13.2의 하위
  ros2_control 컨트롤러와 물리 엔진은 마지막 위치 목표를 계속 유지한다.
- 멀티스레드와 프로세스 분리는 처리 경합을 줄인다. High Priority RT 권한이나
  모든 20ms deadline 준수를 자동으로 제공하지 않는다.
- ApproximateTimeSynchronizer는 가까운 시각끼리 묶는다. 보간된 정확한 촬영 시점
  위치·TF 보정·깊이 추정은 제공하지 않는다.
- YOLO, SLAM, MoveIt 2, PPO 보행, Behavior Tree, 물리 파지는 이 절에 구현하지 않았다.
