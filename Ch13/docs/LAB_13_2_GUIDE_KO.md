# 13.2 통합 로봇 모델링 실습 가이드

이 실습은 `Ch13`만으로 4족 본체, 6DoF 팔, 2지 그리퍼를 하나의 TF 트리와 하나의 `ros2_control` 시스템으로 구성한다. 가동 관절은 다리 12개, 팔 6개, 그리퍼 2개로 총 20개다. Gazebo Harmonic과 MuJoCo에서 같은 관절 이름과 위치 명령 소유권을 검증한다.

## 1. 검증 기준 환경

- Ubuntu 24.04 / ROS 2 Jazzy
- Gazebo Harmonic과 `gz_ros2_control`
- `controller_manager` 4.48.1, `ros2_controllers` 4.42.1
- MuJoCo 3.3.7(네이티브 검사)
- `mujoco_ros2_control` 커밋 `c261f5552edf124d1000a23fb25b6c07cadeb807`

GUI를 사용할 때는 WSLg 또는 Linux 데스크톱이 필요하다. 아래 명령은 저장소 루트에서 시작한다고 가정한다.

## 2. 기본 의존성 및 빌드

```bash
cd Ch13/ros2_ws
source /opt/ros/jazzy/setup.bash
sudo apt update
sudo apt install -y \
  ros-jazzy-xacro ros-jazzy-urdf \
  ros-jazzy-robot-state-publisher ros-jazzy-joint-state-publisher-gui \
  ros-jazzy-ros-gz-sim ros-jazzy-ros-gz-bridge ros-jazzy-gz-ros2-control \
  ros-jazzy-ros2-control ros-jazzy-ros2-controllers \
  ros-jazzy-mujoco-vendor libglfw3-dev python3-vcstool

# MuJoCo 플러그인은 Jazzy 바이너리가 없으므로 고정 커밋을 가져온다.
vcs import src < mujoco_ros2_control.repos
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install
source install/setup.bash
```

MuJoCo 소스 빌드에서 선택적인 `mujoco_3d_lidar` 플러그인의 `/opt/ros` 복사 경고가 보일 수 있다. 이 절의 모델·관절 제어에는 그 선택 플러그인이 필요하지 않다.

## 3. Xacro와 TF 트리 검사

```bash
xacro src/integrated_robot_description/urdf/robot_system.urdf.xacro \
  control_backend:=mock > /tmp/ch13_robot_system.urdf
check_urdf /tmp/ch13_robot_system.urdf
ros2 launch integrated_robot_description view_robot.launch.py
```

확인할 항목은 다음과 같다.

- 유일한 루트가 `base_footprint`인지 확인한다.
- `base_link -> arm_mount -> arm_base_link`가 끊기지 않아야 한다.
- `base_link -> lidar_link`, `arm_link_6 -> camera_link`가 고정 연결이어야 한다.
- 팔 이름은 `arm_`, 그리퍼 이름은 `gripper_`로 시작해야 한다.
- GUI 슬라이더에서 관절 축이 의도한 방향으로 회전해야 한다.

`robot_state_publisher`의 KDL은 관성이 있는 루트 링크에 경고한다. 현재 `base_footprint`의 아주 작은 관성은 Gazebo에서 루트 링크가 제거되지 않도록 둔 값이다. TF와 물리 엔진 구동에는 문제가 없음을 확인했지만, 이 경고 자체는 남아 있다.

## 4. Gazebo 실습

첫 번째 터미널:

```bash
cd Ch13/ros2_ws
source /opt/ros/jazzy/setup.bash
source install/setup.bash
ROS_DOMAIN_ID=131 ros2 launch integrated_robot_description gazebo.launch.py
```

두 번째 터미널:

```bash
cd <저장소-루트>
source /opt/ros/jazzy/setup.bash
source Ch13/ros2_ws/install/setup.bash
ROS_DOMAIN_ID=131 python3 Ch13/scripts/verify_gazebo_13_2.py \
  --engine gazebo \
  --output Ch13/evidence/section_13_2/gazebo/result.json
```

성공 기준은 20개 유한 관절 상태, 네 컨트롤러의 `active` 상태, `arm_joint_2`의 0.04 rad 이상 응답, 유한한 본체 자세다. 검증 종료 후 첫 터미널에서 `Ctrl+C`로 종료한다.

## 5. MuJoCo 실습

### 5.1 네이티브 동역학 검사

ROS와 분리해 MJCF가 로드되고 안정적으로 적분되는지 먼저 확인한다.

```bash
python3 -m venv /tmp/ch13-mujoco-venv
/tmp/ch13-mujoco-venv/bin/pip install mujoco==3.3.7 numpy pytest
/tmp/ch13-mujoco-venv/bin/python Ch13/scripts/verify_mujoco_13_2.py \
  --model Ch13/ros2_ws/src/integrated_robot_description/mujoco/robot_system.xml \
  --output Ch13/evidence/section_13_2/mujoco/native_result.json
```

### 5.2 MuJoCo와 ros2_control 통합 검사

첫 번째 터미널:

```bash
cd Ch13/ros2_ws
source /opt/ros/jazzy/setup.bash
source install/setup.bash
ROS_DOMAIN_ID=132 ros2 launch integrated_robot_description mujoco.launch.py
```

두 번째 터미널:

```bash
cd <저장소-루트>
source /opt/ros/jazzy/setup.bash
source Ch13/ros2_ws/install/setup.bash
ROS_DOMAIN_ID=132 python3 Ch13/scripts/verify_gazebo_13_2.py \
  --engine mujoco \
  --output Ch13/evidence/section_13_2/mujoco/ros2_control_result.json
```

패키지 이름에 `robot_description`이 포함되므로 `controller_manager` 4.48.1이 원래 YAML 경로를 잘못 걸러내는 문제가 있다. 두 엔진 launch는 설정을 내용 해시 기반 `/tmp/ch13_2_controllers_*.yaml`로 복사해 이 문제를 우회한다.

## 6. 자동 테스트

```bash
cd <저장소-루트>
source /opt/ros/jazzy/setup.bash
python3 -m pytest -q Ch13/tests

cd Ch13/ros2_ws
colcon test --packages-select integrated_robot_description
colcon test-result --verbose
```

## 7. 현재 구현과 미구현 범위

검증된 구현은 Xacro 모듈 조립, 질량·관성·단순 충돌 형상, 단일 TF 트리, 20개 위치 인터페이스, 컨트롤러 소유권 분할, Gazebo/MuJoCo 구동이다.

미구현 항목은 MoveIt 2 설정/SRDF/self-collision matrix, 실제 카메라·LiDAR 센서 플러그인 데이터, 물체 파지 접촉, 보행 정책, PPO 재학습과 탑재 하중 안정성 검증이다. 특히 이 절의 정지 자세 성공을 보행·파지 성공으로 해석하면 안 된다.
