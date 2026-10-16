# [figure 11-2] Gazebo 시뮬레이션 상의 센서 데이터 시각화

작성일: 2026-10-16. ROS 2 Jazzy / Gazebo Harmonic / Ubuntu 24.04 / Windows 11 WSL2 기준.

2026-10-17 실행 검증: 실제 WSL2에서 발견한 모델 생성·기립 오류를 수정하고 센서·TF 수신 및 23개 테스트 통과를 확인했다. 아래 최초 작성 당시의 미검증 항목과 구분되는 최신 결과는 [실행 디버깅 보고서](FIGURE_11_2_DEBUG_REPORT_KO.md)를 참조한다.

## 1. 무엇을 실행하는가?

기존 `Ch11/ros2_ws/src/my_quadruped_bot`을 사용한다. 새 패키지는 만들지 않았다. 앞서 수정한 IMU·TF·관측 기반 오도메트리 구성을 포함하는 커밋 `d2cdce9939471519fb3641ff556a5411d56388fc`에 그림 전용 파일을 추가했다.

- **Gazebo:** 4족 로봇, 사방의 벽, 주황색·파란색 상자
- **RViz:** 같은 로봇의 URDF, 실제 /scan을 변환한 붉은 점, 실제 /imu/data_raw 자세를 나타내는 XYZ 좌표축
- **실행 기본값:** 기존 FSM으로 기립하며 속도 명령은 발행하지 않는다.
- **그림 구성:** 왼쪽 Gazebo, 오른쪽 RViz. 로봇·스캔·IMU 축의 오버레이는 RViz 화면 안에서 이루어진다.

이 문서와 코드가 실제 WSL2·Gazebo 화면 캡처를 포함하는 것은 아니다. 최초 작성 환경에는 ROS·Gazebo가 없어 실제 렌더링을 확인하지 못했다. 이후 실제 실행 검증은 위 보고서에 기록했으며, 출판용 화면은 별도로 캡처해야 한다.

## 2. 코드 받기

새 그림 브랜치는 이전 수정 브랜치의 내용을 포함한다. main에는 이전 수정이 아직 없으므로 아래 브랜치를 사용한다.

```bash
cd ~/Pysical_AI_ROS2_publish
git status --short
git fetch origin
git switch --track origin/feat/ch11-figure-11-2
```

저장소 위치가 다르면 첫 줄을 바꾼다. 브랜치가 이미 있으면 `git switch feat/ch11-figure-11-2`를 사용한다. 미커밋 작업이 있어 checkout이 차단되면 해당 변경을 먼저 보존한다.

## 3. 최초 한 번 의존성 준비

기존 rl_env·venv·Conda를 해제한 새 WSL 터미널에서 실행한다. ROS 2 Jazzy 기본 설치가 선행되어야 한다.

```bash
source /opt/ros/jazzy/setup.bash
sudo apt update
sudo apt install -y python3-colcon-common-extensions python3-rosdep \
  python3-numpy python3-yaml \
  ros-jazzy-ros-gz ros-jazzy-xacro ros-jazzy-robot-state-publisher \
  ros-jazzy-robot-localization ros-jazzy-rviz2 ros-jazzy-tf2-ros
cd ~/Pysical_AI_ROS2_publish/Ch11/ros2_ws
rosdep install --from-paths src --ignore-src -r -y --rosdistro jazzy
```

rosdep를 한 번도 초기화하지 않았다면 `sudo rosdep init`, `rosdep update`를 먼저 수행한다. 이미 초기화한 경우 init을 반복하지 않는다. WSLg와 GPU 드라이버가 동작해야 하며, GPU LiDAR는 Ogre2 센서 렌더링을 필요로 한다.

## 4. 한 번에 실행

저장소 루트에서:

```bash
bash Ch11/scripts/run_figure_11_2.sh
```

스크립트는 Ch11을 빌드하고 올바른 install 경로를 확인한 뒤 다음 launch를 실행한다.

```bash
ros2 launch my_quadruped_bot figure_11_2.launch.py
```

이미 다른 장이나 Ch11 시뮬레이션이 실행 중이면 먼저 그 세션을 정상 종료한다. 동일한 로봇·브리지·EKF를 두 번 실행하지 않는다. 새 터미널에서의 실험 격리가 필요하면 모든 실험 터미널에 동일한 별도 `ROS_DOMAIN_ID`와 `GZ_PARTITION`을 설정한다.

직접 빌드·실행하려면:

```bash
source /opt/ros/jazzy/setup.bash
cd ~/Pysical_AI_ROS2_publish/Ch11/ros2_ws
colcon build --symlink-install --packages-up-to my_quadruped_bot
source install/setup.bash
ros2 launch my_quadruped_bot figure_11_2.launch.py
```

기립·모델 안정화와 센서 초기화를 기다린다. 기립이 불안정하면 해당 장면을 성공 그림으로 사용하지 말고 Gazebo를 일시정지한 뒤 제어기·기구학을 점검한다. 이번 변경은 기존 모델·보행 제어를 재튜닝한 것이 아니다.

## 5. 화면에서 읽을 것

### Gazebo

로봇은 원점 근처에 생성된다. 높이 1.5 m의 벽 네 개가 x/y=±3.5 m에 있고, 높이 0.8~1.0 m의 상자 두 개가 근처에 배치된다. 물체의 visual과 collision이 모두 있으므로 렌더링 LiDAR가 반환점을 생성할 대상을 제공한다.

빈 월드와 달리 벽·상자 단면이 스캔에 나타나는 구성을 의도했다. 실제 검출 여부는 실행 후 /scan과 RViz로 확인한다. 전용 월드 바닥 마찰값은 0.8로 두었으며, 원래 외란·슬립 실습 월드는 바꾸지 않았다.

### RViz

| 표시 | 데이터·설정 | 해석 |
|---|---|---|
| Quadruped | /robot_description + /joint_states + TF | 시뮬레이터와 같은 로봇 모델 |
| LiDAR - measured returns (red) | /scan, LaserScan, 붉은 Spheres | 실제 거리 샘플을 좌표로 변환한 반사점 |
| IMU measured orientation (XYZ) | /figure_11_2/imu_pose, Pose, Shape=Axes | 원시 IMU의 orientation으로 만든 자세 표시 |
| Floor grid (0.5 m) | RViz 보조 격자 | 거리 비교를 돕는 시각 보조선 |
| TF debug | 기본 비활성 | 문제 진단용이며 도서 그림에서는 숨긴다 |

IMU 축 색은 **X=빨강, Y=초록, Z=파랑**이다. IMU 위치가 base_link 원점에 있으므로 로봇 중심에 축을 놓는다. 축은 가속도 벡터가 아니며, 로봇의 이동 방향이나 목표 방향을 뜻하지도 않는다.

RViz Fixed Frame은 odom이다. 몸체에 붙은 base_link를 Fixed Frame으로 쓰면 회전하는 로봇을 함께 따라가므로 자세 변화를 읽기 어려워진다.

## 6. IMU 축을 정확히 표시하는 방식

새 `imu_pose_viz` 노드는 다음 순서로 처리한다.

1. /imu/data_raw의 orientation과 header.stamp를 읽는다.
2. IMU가 base_link와 정렬되어 있는지 frame_id로 확인한다.
3. 같은 시각의 odom → base_link TF에서 **위치만** 가져온다.
4. IMU orientation을 odom 기준 PoseStamped의 방향으로 한 번만 넣는다.
5. /figure_11_2/imu_pose로 발행하고 RViz Pose의 Axes로 표시한다.

TF의 회전을 IMU quaternion에 다시 곱하지 않는다. 그 방식은 같은 몸체 회전을 중복 적용할 수 있다. 최대 0.5초 동안 TF를 기다리며, 오래된 입력·유효하지 않은 quaternion·orientation 미제공(covariance[0]=-1)을 대신할 가짜 자세를 만들지 않는다.

**전제:** 이 그림은 base_link에 정렬된 Gazebo IMU와 yaw=0 초기 스폰을 사용하며 IMU 방향 기준과 odom을 정렬된 것으로 취급한다. 다른 장착 각도·초기 기준·실물 IMU를 쓰면 기준 좌표계 보정을 추가해야 한다. 센서 frame_id만 바꿔서 방향 기준을 맞출 수는 없다.

실제 가속도계·자이로만으로 절대 자세가 저절로 주어지는 것은 아니다. 여기서는 Gazebo IMU가 제공하는 orientation을 사용한다. 실물에서는 센서 내부 또는 외부 자세 추정기의 출력 유효성을 확인해야 한다.

## 7. 도서용 캡처 구도

1. Windows 바탕화면에서 Gazebo를 왼쪽, RViz를 오른쪽으로 배치한다.
2. Gazebo에서 로봇과 주황색 상자가 함께 보이도록 비스듬한 위쪽 시점으로 조정한다.
3. RViz 기본 시점은 원점 중심의 사선 위쪽이다. 휠로 확대·축소해 로봇, XYZ 축, 적어도 한 상자의 단면과 벽 반환점을 함께 담는다.
4. 화면이 너무 넓으면 RViz Views의 Distance를 약 5~6 m로 조정한다. 방 전체 구조를 강조하려면 기본 8 m를 사용한다.
5. RViz 왼쪽 Displays에서 LiDAR·IMU 표시 이름을 보이고, Status가 정상인지 확인한다.
6. 데이터가 안정된 뒤 Windows의 **Win+Shift+S**로 두 창을 함께 캡처한다. PNG 원본으로 보관한다.
7. 편집 단계에서 왼쪽에 “(a) Gazebo: 로봇과 환경”, 오른쪽에 “(b) RViz2: LiDAR와 IMU 자세”를 붙인다.

실행 중인 스캔·축이 확인된 뒤 캡처한다. 센서 렌더링이 정지할 수 있으므로 처음부터 Gazebo를 pause한 상태로 준비하지 않는다. 정지 화면을 쓰더라도 그것이 보행 성능 검증이라는 뜻은 아니다.

출판용 PNG는 실제 캡처 해상도를 기준으로 사용한다. 300 dpi 메타데이터만 추가해도 원본 픽셀 정보가 늘어나지는 않는다.

### 권장 캡션

**[figure 11-2] Gazebo 시뮬레이션 상의 센서 데이터 시각화.** 왼쪽은 벽과 장애물 사이에 놓인 4족 로봇의 Gazebo 모습이며, 오른쪽은 같은 로봇의 센서 데이터를 RViz2에 겹쳐 표시한 화면이다. 붉은 점은 LiDAR가 측정한 주변 물체의 반사 지점을, 로봇 중심의 빨강·초록·파랑 축은 각각 IMU 측정 자세의 X·Y·Z 방향을 나타낸다. 센서 데이터와 로봇 모델을 같은 좌표계에서 비교하면 외부 환경의 형상과 로봇의 자세를 함께 읽을 수 있다.

### 본문에 함께 쓰면 좋은 보충 문장

“LaserScan은 각도별 거리 배열이다. RViz2는 이를 공간 좌표로 변환해 붉은 점으로 표시한다. 점들이 보인다는 사실만으로 드리프트가 자동 보정되는 것은 아니며, 위치 수정에는 이후에 다룰 스캔 매칭이나 SLAM 알고리즘이 필요하다.”

## 8. 표시가 안 될 때

새 터미널에서 ROS와 Ch11 환경을 source한다.

```bash
source /opt/ros/jazzy/setup.bash
source ~/Pysical_AI_ROS2_publish/Ch11/ros2_ws/install/setup.bash
cd ~/Pysical_AI_ROS2_publish
bash Ch11/scripts/check_figure_11_2.sh |& tee /tmp/figure_11_2_check.log
```

| 증상 | 확인 순서 |
|---|---|
| 로봇 모델이 없음 | /robot_description, /joint_states, Ch11 패키지 prefix, RobotModel Status |
| 붉은 점이 없음 | /scan 실제 수신 → 센서 frame_id → odom→lidar_link → Best Effort QoS |
| /scan 토픽만 있고 데이터 없음 | gz topic -l, Ogre2/GPU, Sensors 플러그인, 브리지 로그 |
| IMU 축이 없음 | /imu/data_raw → header.frame_id=base_link → orientation 유효성 → odom→base_link → /figure_11_2/imu_pose |
| TF extrapolation 경고 | 모든 관련 노드 use_sim_time, /clock, reset 이후 재시작 여부 |
| 축이 로봇과 두 배로 회전 | IMU 자세에 TF 회전을 다시 곱한 별도 노드가 있는지 확인 |
| 벽이 없음 | 기본 empty_world가 아니라 sensor_figure_world가 실행됐는지 확인 |
| 몸체는 보이지만 자세가 불안정 | 기존 모델·IK·FSM 리뷰가 필요. 센서 표시 문제와 구분 |

세부 확인 명령:

```bash
ros2 topic echo /figure_11_2/imu_pose --once
ros2 topic echo /scan --once --field header --qos-reliability best_effort
ros2 param get /figure_11_2_rviz use_sim_time
```

별도 RViz를 띄우려면 기존 실행을 종료한 뒤 `start_rviz:=false`로 실행한다. 다른 터미널에서 다음 명령을 쓴다.

```bash
rviz2 -d "$(ros2 pkg prefix --share my_quadruped_bot)/rviz/figure_11_2.rviz" \
  --ros-args -p use_sim_time:=true
```

`start_controller:=false`는 제어기 없이 센서 인프라를 조사할 때만 사용한다. 로봇 기립을 유지하는 옵션이 아니다.

## 9. 검증 상태와 산출물

아래는 2026-10-16 최초 작성 시점의 기록이다. 2026-10-17 실제 실행 및 추가 회귀 검사 결과는 위 디버깅 보고서를 참조한다.

- 새 그림 검사: 수정 전 6 FAIL → 수정 후 6 PASS
- 이전 위치 추정 검사 포함: 총 21 PASS
- ROS 없는 검사 범위: IMU quaternion·위치 변환, 비정상 입력, RViz 데이터 연결·색·Axes 설정, 월드의 collision·visual·센서 시스템
- 문법·자산 파싱: Python, YAML/RViz, SDF, Bash 검사
- **ROS 빌드·실제 WSL2/Gazebo/RViz 실행·출판용 PNG 캡처: 미수행**

코드:

- launch/figure_11_2.launch.py
- worlds/sensor_figure_world.sdf
- rviz/figure_11_2.rviz
- my_quadruped_bot/imu_pose_viz.py
- my_quadruped_bot/imu_visualization_math.py
- Ch11/scripts/run_figure_11_2.sh
- Ch11/scripts/check_figure_11_2.sh

기존 simulation.launch.py에는 world 인수를 추가했으며 기본값은 기존 empty_world.sdf다. setup.py에 imu_pose_viz 실행 항목을 등록했다.

참고: [RViz Jazzy Pose 구현(Arrow/Axes)](https://github.com/ros2/rviz/blob/jazzy/rviz_default_plugins/src/rviz_default_plugins/displays/pose/pose_display.cpp). 이 구현 참조는 실제 화면 검증을 대신하지 않는다.
