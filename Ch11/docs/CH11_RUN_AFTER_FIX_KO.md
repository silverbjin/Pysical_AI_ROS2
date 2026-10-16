# Ch11 수정 후 실행 안내

현재 브랜치: `fix/ch11-localization-observation`

이 브랜치는 IMU 입력·TF 발행 주체·오도메트리 관측 경로를 수정한 후보이며 실제 WSL2·Gazebo 실행 결과는 아직 없다. 자세한 수정과 검증 범위는 [수정 보고서](CH11_LOCALIZATION_FIX_REPORT_KO.md)를 확인한다.

## 1. 변경 브랜치 받기

기존 저장소에서 작업 변경을 먼저 확인한다. 아래 checkout은 미커밋 변경을 강제로 지우지 않는다.

```bash
cd ~/Pysical_AI_ROS2_publish
git status --short
git fetch origin
git switch --track origin/fix/ch11-localization-observation
```

이미 로컬 브랜치가 존재하면 `git switch fix/ch11-localization-observation`을 사용한다. 저장소 위치가 다르면 첫 줄을 수정한다.

## 2. WSL2 Ubuntu 24.04 환경 준비

Python 가상환경·Conda를 해제한 새 WSL2 터미널에서 진행한다. ROS 2 Jazzy가 설치되어 있어야 한다.

```bash
sudo apt update
sudo apt install -y python3-colcon-common-extensions python3-rosdep \
  python3-numpy python3-yaml python3-pytest \
  ros-jazzy-ros-gz ros-jazzy-xacro ros-jazzy-robot-state-publisher \
  ros-jazzy-robot-localization ros-jazzy-rviz2 ros-jazzy-tf2-tools \
  ros-jazzy-ament-copyright ros-jazzy-ament-flake8 ros-jazzy-ament-pep257
source /opt/ros/jazzy/setup.bash
cd Ch11/ros2_ws
rosdep install --from-paths src --ignore-src -r -y --rosdistro jazzy
cd ../..
```

rosdep가 초기화되어 있지 않으면 최초 한 번 `sudo rosdep init` 후 `rosdep update`를 실행한다. 실제 Gazebo GUI와 GPU LiDAR 렌더링을 위해 WSLg·GPU 드라이버가 동작해야 한다.

## 3. 자동 실행·관찰·결과 수집

저장소 루트에서 실행한다. 다른 Ch11 노드를 먼저 실행할 필요가 없다.

```bash
bash Ch11/scripts/verify_wsl2_gazebo.sh
```

기본 DDS 도메인 71이 사용 중이면 다음처럼 다른 도메인을 지정한다.

```bash
CH11_DOMAIN_ID=72 bash Ch11/scripts/verify_wsl2_gazebo.sh
```

스크립트는 해당 실험을 빌드하고 Gazebo를 실행한 뒤 기립 상태를 관찰한다. 조건이 충족되면 0.03 m/s 전진 명령을 3 시뮬레이션 초 동안 보내고 영속도로 정지시킨다. 실제 시간으로 최대 약 2분간 관찰한다. 비정상 움직임을 발견하면 Ctrl+C 또는 Gazebo 일시정지를 사용한다.

결과:

- `Ch11/evidence/wsl2-날짜-시각/result.json`: 종합 PASS / FAIL / BLOCKED
- `runtime.json`: 실제 ROS 그래프·TF·센서·짧은 이동별 판정
- `build.log`: 빌드 로그
- `bringup.log`: Gazebo·센서·추정·보행 로그
- `probe.log`: 런타임 검사 출력
- `colcon-test-result.log`: 기존 패키지 테스트 결과

PASS는 이 짧은 실험의 조건을 만족했다는 뜻이다. SLAM·Nav2·외란 회복·실물 로봇까지 검증한 것은 아니다. 결과 폴더는 자동 커밋되지 않는다.

## 4. 수동 확인

다음 명령은 자동 검증을 종료한 뒤 별도 세션에서 실행한다.

```bash
source /opt/ros/jazzy/setup.bash
source Ch11/ros2_ws/install/setup.bash
ros2 launch my_quadruped_bot ch11_bringup.launch.py
```

다른 터미널에서도 같은 환경을 source한 뒤:

```bash
ros2 topic info /odom -v
ros2 topic echo /imu/data_raw --once --qos-reliability best_effort
ros2 topic echo /simulation/odom --once --qos-reliability best_effort
ros2 run tf2_ros tf2_echo odom base_footprint
```

/odom 발행자는 ekf_filter_node 한 개여야 한다. /imu/data_raw frame_id는 base_link다. /simulation/odom은 명령을 적분한 값이 아니라 Gazebo 모델 관측이다.

FSM이 더 이상 /odom·TF를 발행하지 않으므로 이전 가이드의 /fsm/odom, /fsm/tf remap은 필요 없다. 이전의 `leg_odometry` 실행 명령은 제거되었고, 교육용 적분 예제는 다음 명령으로 독립 실행한다.

```bash
ros2 run my_quadruped_bot command_odometry_demo
```

이 예제는 /demo/cmd_vel만 받아 /demo/odom을 발행하므로 활성 EKF 경로와 연결되지 않는다.

## 5. 다음 검토에 전달할 것

자동 검증이 끝나면 result.json과 실패 시 bringup.log·probe.log·colcon-test-result.log를 함께 제공한다. 실행 실패를 성공으로 간주하지 말고 해당 체크를 기준으로 후속 수정을 진행한다.
