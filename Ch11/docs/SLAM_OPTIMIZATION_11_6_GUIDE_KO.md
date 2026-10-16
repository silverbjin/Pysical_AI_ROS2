# 11.6 사족 보행 SLAM 튜닝 및 3D LiDAR의 2D 투영

## 1. 적용 내용과 실행 경로

11.5절 구현을 포함하는 `feat/ch11-slam-mapping`의 af0ef39를 기반으로 확장했다. 이번 브랜치는 `feat/ch11-slam-optimization`이다. main에 11.5가 아직 병합되지 않았더라도 이 브랜치에는 포함되어 있다.

| 목적 | 실행 런치 | SLAM 입력 |
|---|---|---|
| 11.5 기존 실습 | slam.launch.py | /scan/slam (EKF TF 기반 기울기 게이트) |
| 11.6 IMU 필터·튜닝 | slam_optimized.launch.py | /scan_stabilized |
| 11.6.8 3D 높이 투영 | slam_3d.launch.py | /scan/projected |

세 SLAM 런치를 **동시에 실행하지 않는다**. 각 런치가 SLAM lifecycle을 활성화하고 map→odom을 발행한다. 시뮬레이션은 계속 `SLAM_simulation.launch.py`를 사용하며 기존 EKF·FSM이 포함되어 있다. localization.launch.py를 따로 시작하지 않는다.

튜닝은 성공을 보장하는 보정값이 아니라 비교 실험의 시작점이다. 특히 현재 기본 오도메트리는 Gazebo 모델 관측을 사용한다. 실물의 미끄러짐을 모델링한 접촉 오도메트리라고 해석하지 않는다.

## 2. 설치·빌드

WSL2 Ubuntu 24.04, ROS 2 Jazzy, Gazebo Harmonic 환경에서 가상환경을 해제한다. 저장소 경로는 자신의 경로로 바꾼다.

```bash
cd ~/Pysical_AI_book
git status --short
git fetch origin
git switch --track origin/feat/ch11-slam-optimization
source /opt/ros/jazzy/setup.bash
sudo apt update
sudo apt install -y ros-jazzy-slam-toolbox ros-jazzy-nav2-map-server \
  ros-jazzy-pointcloud-to-laserscan ros-jazzy-teleop-twist-keyboard python3-yaml
cd Ch11/ros2_ws
rosdep install --from-paths src --ignore-src -r -y --rosdistro jazzy
colcon build --symlink-install --packages-up-to my_quadruped_bot
source install/setup.bash
```

이미 로컬 브랜치가 있으면 `git switch feat/ch11-slam-optimization`을 사용한다. 모든 새 터미널은 아래 두 환경만 source한다. 다른 장의 overlay를 섞지 않는다.

```bash
source /opt/ros/jazzy/setup.bash
source ~/Pysical_AI_book/Ch11/ros2_ws/install/setup.bash
```

## 3. 11.6.3 IMU 기반 scan_stabilizer

파일은 `my_quadruped_bot/sensors/scan_stabilizer.py`다. 실행 항목 `scan_stabilizer`를 setup.py에 등록했다. 패키지명은 quadruped_system이 아니라 my_quadruped_bot이다.

원고의 최신 IMU 값 하나만 저장하는 방식 대신 다음을 적용했다.

- 실제 센서 토픽 `/imu/data_raw`를 사용한다. `/imu/rpy_filtered` 배열을 Imu로 간주하지 않는다.
- 스캔 촬영 시각과 가장 가까운 IMU 표본을 최대 400개 이력에서 선택한다. 기본 허용 시각 차이는 0.03초다. 보간하는 필터가 아니라 최근접 표본 매칭이다.
- IMU가 아직 없거나 너무 오래됐거나 orientation_covariance[0]=-1이면 통과시키지 않는다. 유효하지 않은 표본을 수평 자세로 대체하지 않는다.
- IMU quaternion에 IMU→LiDAR 장착 TF를 곱해 **센서 평면 자체의 기울기**를 구한다. 현재 IMU frame은 base_link, 센서는 lidar_link다. IMU orientation이 ENU 중력 기준 자세라는 전제가 필요하다.
- 11.5의 시각·기울기·최소 간격 게이트를 재사용한다. XYZW 정규화·NaN 검사, 최대 0.5초 대기, 최대 5스캔 큐, 시간 역행 처리가 포함된다.
- 통과 시 header.stamp, frame_id, ranges를 그대로 발행한다. stamp를 현재 시각으로 바꾸지 않는다.

기본 임계값은 센서 z축과 수직 방향 사이의 **총 기울기 5도**다. 원고처럼 roll/pitch 각각을 5도와 비교하는 것보다 대각선 기울기에 엄격하다. roll=4도, pitch=4도일 때 각각은 5도 이하지만 총 기울기는 약 5.65도다.

### 실행

터미널 1:

```bash
ros2 launch my_quadruped_bot SLAM_simulation.launch.py start_rviz:=false
```

터미널 2:

```bash
ros2 launch my_quadruped_bot slam_optimized.launch.py
```

터미널 3:

```bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard --ros-args \
  -p speed:=0.05 -p turn:=0.15 -p stamped:=false
```

짧게 전진·회전한 뒤 `k`로 정지한다. 키를 놓는 것만으로 정지를 보장하지 않는다. 11.7 통합 코드부터 FSM에 기본 0.5초 명령 watchdog이 추가되어 있다. 필요하면 정지 명령을 직접 보낸다.

```bash
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist \
  '{linear: {x: 0.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}'
```

필터만 살펴보려면 SLAM을 실행하지 않은 상태에서 단독 실행할 수도 있다.

```bash
ros2 run my_quadruped_bot scan_stabilizer --ros-args -p use_sim_time:=true
ros2 topic hz /scan_stabilized
```

위 두 명령은 각각 별도 터미널에서 실행한다. 단독 필터와 slam_optimized.launch.py를 동시에 실행하지 않는다.

### 조절 가능한 인자

각 비교는 터미널 2의 SLAM을 종료하고 **새 지도 세션**으로 실행한다.

```bash
# 3도: 더 엄격하게 제한
ros2 launch my_quadruped_bot slam_optimized.launch.py max_tilt_degrees:=3.0

# 더 넓은 탐색 폭, 나머지는 동일한 초기 프로필
ros2 launch my_quadruped_bot slam_optimized.launch.py profile:=wide_search

# IMU 직접 매칭 대신 11.5의 EKF TF 기반 자세 게이트와 비교
ros2 launch my_quadruped_bot slam_optimized.launch.py stabilizer:=tf

# IMU 시각 오차 제한과 전달 간격 변경
ros2 launch my_quadruped_bot slam_optimized.launch.py max_imu_delta:=0.02 min_scan_interval:=0.10
```

모든 필터 튜닝 파라미터는 시작 시 읽는 값이다. 실행 중 ros2 param set으로 변경하는 대신 재시작한다. 3~5도가 어떤 환경에서나 최적이라는 뜻은 아니다. 낮은 문턱은 바닥 점을 줄일 수도 있지만 모든 스캔을 끊을 수 있다. 시간 간격 조절은 안정 보행 위상을 찾는 기능이 아니다.

5초마다 필터 로그의 accepted/tilt/interval/stale_or_future/queue_overflow/pending을 확인한다. IMU 또는 장착 TF가 없어 대기하다 만료된 경우도 stale_or_future로 집계된다. 이 값만으로 IMU 누락과 TF 누락을 구분할 수 없으므로 각각의 토픽·시각·TF를 확인한다.

## 4. 11.6.5~7 튜닝 프로필과 원고 보완

| 항목 | 11.5 | balanced | wide_search |
|---|---:|---:|---:|
| correlation_search_space_dimension | 기본값 0.5m | 1.0m | 2.0m |
| correlation_search_space_resolution | 기본값 0.01m | 0.01m | 0.01m |
| minimum_travel_distance | 0.10m | 0.30m | 0.30m |
| minimum_travel_heading | 0.15rad | 0.20rad | 0.20rad |
| check_min_dist_and_heading_precisely | true | true | true |
| link_match_minimum_response_fine | 0.1 | 0.1 | 0.1 |
| transform_timeout | 0.5초 | 0.5초 | 0.5초 |
| tf_buffer_duration | 30초 | 30초 | 30초 |

YAML은 `config/mapper_params_balanced.yaml`, `mapper_params_wide_search.yaml`이다. 원고와 달리 이 저장소의 11.5 기준은 이미 0.1m 이동 문턱과 0.5초 TF timeout이다.

- 실제 파라미터명은 correlation_search_space_dimension이다. 값은 검색 격자의 **폭**이며 무조건 반경으로 읽지 않는다. 1.0m 설정을 '반경 1m 오류까지 복구'로 설명하면 안 된다.
- 같은 0.01m 해상도에서 폭을 0.5m→2.0m로 늘리면 평면 검색 격자 수는 대략 16배가 된다. 전체 실행 시간이 정확히 16배가 되는 것은 아니다. CPU 부담과 반복 구조의 잘못된 매칭이 늘 수 있다.
- 최소 이동·회전 문턱은 새 스캔을 처리할지 결정하는 데 관여한다. `/map` 발행 주기 map_update_interval과 같은 개념이 아니다. 회전 조건도 만족하면 제자리 회전 중 스캔이 처리될 수 있다.
- link_match_minimum_response_fine을 자동으로 낮추지 않았다. 기준을 낮추면 나쁜 연결도 수용할 수 있다. 비교가 필요하면 wide_search YAML을 복사하여 0.08 같은 별도 실험값을 적용하되, 같은 루프를 반복하고 오매칭 여부를 검증한다. 배포 설정으로 바로 채택하지 않는다.
- TF timeout은 존재하지 않는 변환을 만들거나 잘못된 시각을 고치지 못한다. 버퍼 길이는 과거 TF 조회 범위다. SLAM의 포즈 그래프 보관·루프 최적화 메모리와 동일하지 않다. 길수록 항상 좋다는 설명을 피한다.
- 기울기 게이트는 전체 스캔을 제외한다. 수평화, 바닥 분할, 보행 충격 제거, scan deskew를 수행하지 않는다.

각 조건을 동일한 경로·속도·실행 시간으로 비교한다. IMU/TF 시각 오차, 통과 스캔 수, 벽 두께, 루프 연결, CPU·시뮬레이션 실시간 비율을 함께 기록한다. 프로필을 바꿀 때 여러 값을 동시에 무작정 바꾸지 않는다.

실제 연결 확인은 저장소 루트에서 다음과 같이 수행한다.

```bash
cd ~/Pysical_AI_book
python3 Ch11/scripts/check_slam_mapping.py --scan-topic /scan_stabilized \
  --seconds 20 --output /tmp/slam_optimized_runtime.json
ros2 lifecycle get /slam_toolbox
ros2 run tf2_ros tf2_echo map odom
```

지도 저장은 11.5 스크립트를 재사용한다. SLAM은 활성화하고 Gazebo 시간은 진행 상태로 둔다.

```bash
bash Ch11/scripts/save_slam_map.sh "$HOME/Pysical_AI_book/Ch11/maps/optimized_run1"
```

## 5. 11.6.8 심화 솔루션 — 실제 3D LiDAR → 2D Projection

### 5.1 왜 base_footprint를 그대로 사용하지 않는가?

현재 URDF의 base_footprint는 base_link와 같은 원점·자세다. 몸체와 함께 기울어지며 높이도 변하므로 여기에 min_height=0.3을 적용한다고 '지면 위 0.3m'가 되지 않는다. odom 자체로 점군을 투영하면 센서가 이동해도 레이저의 원점이 odom 원점에 남아 거리·각도 의미가 틀어진다.

이번 솔루션은 별도 `scan_ground` 프레임을 사용한다.

- 부모는 odom이며 로봇의 기존 TF 가지를 바꾸지 않는다.
- x/y와 yaw는 `/odom`의 EKF 결과를 따른다.
- roll/pitch는 0으로 두어 수평을 유지한다.
- z는 명시적인 ground_height(기본 0m)다.
- TF stamp는 해당 Odometry 메시지의 시각을 사용한다. 현재 시각이나 최신 임의 자세로 재표기하지 않는다.

TF는 두 가지가 된다. `odom→base_footprint→base_link→lidar_link`는 실제 몸체 자세이고, `odom→scan_ground`는 투영을 위한 가상 수평 프레임이다. SLAM의 base_frame도 scan_ground로 설정하여 수평 x/y/yaw 프레임에서 매칭한다.

### 5.2 가상 3D LiDAR 실행

기존 gpu_lidar에 선택형 수직 16채널(-20~+20도)을 추가했다. 수평 360개 × 수직 16개, 10Hz 설정이다. 제조사 장치의 빔 배열·노이즈·회전 스캔을 그대로 재현한 센서는 아니다. 기본 lidar_3d=false에서는 기존 2D 설정을 유지한다.

앞선 시뮬레이션과 SLAM을 **모두 종료한 뒤**, 터미널 1에서 실행한다.

```bash
ros2 launch my_quadruped_bot SLAM_simulation.launch.py lidar_3d:=true start_rviz:=false
```

`lidar_3d=true`일 때만 별도 cloud_bridge가 실행된다. Gazebo `/model/my_quadruped/scan/points`의 gz.msgs.PointCloudPacked를 ROS `/lidar/points`의 sensor_msgs/msg/PointCloud2로 변환한다. 브리지 frame_id는 실제 센서 프레임 lidar_link다.

터미널 2:

```bash
ros2 launch my_quadruped_bot slam_3d.launch.py
```

이 런치는 다음을 함께 시작한다.

1. projection_frame: `/odom` → `odom→scan_ground` TF.
2. pointcloud_to_laserscan_node: `/lidar/points`를 촬영 시각 TF로 scan_ground에 변환하고, z=0.3~1.5m의 점만 선택한다.
3. 각 방위각에 남은 점의 최소 평면 거리를 `/scan/projected`로 발행한다.
4. SLAM Toolbox가 `/scan/projected`로 지도를 만든다. 2D tilt gate는 실행하지 않는다.
5. 지도·투영 스캔용 RViz를 실행한다. Raw 3D cloud 항목을 켜면 바닥 점을 함께 관찰할 수 있다.

가상 스캔의 원점은 scan_ground다. 실제 LiDAR 높이의 물리적 단일 광선 평면과 동일한 메시지가 아니라, 선택한 높이 구간의 장애물을 방위각별로 축약한 결과다. 빈 방향은 inf다. 실제 측정 시간 stamp를 보존한다.

터미널 3의 teleop 명령은 앞 절과 동일하다. **3D 모드의 원본 `/scan`을 2D 지도 입력으로 사용하지 않는다.** 다층 LiDAR의 Gazebo LaserScan 변환은 `/scan/projected`와 다른 데이터다.

### 5.3 설정과 높이 기준

`config/pointcloud_projection.yaml`:

```yaml
pointcloud_projection:
  ros__parameters:
    use_sim_time: true
    target_frame: scan_ground
    transform_tolerance: 0.1
    min_height: 0.3
    max_height: 1.5
    angle_min: -3.141592653589793
    angle_max: 3.141592653589793
    angle_increment: 0.017453292519943295
    scan_time: 0.1
    range_min: 0.1
    range_max: 10.0
    use_inf: true
```

0.3~1.5m는 **알고 있는 수평 지면 높이**로부터의 구간이다. 현재 Gazebo 실내 바닥 z=0을 가정한다. 실제 지면의 odom z가 0.2m로 알려져 있다면 다음과 같이 지정한다.

```bash
ros2 launch my_quadruped_bot slam_3d.launch.py ground_height:=0.2
```

높이 구간은 `min_height:=0.2 max_height:=1.2`처럼 시작 인자로 조정할 수 있다. min_height < max_height를 유지한다.

잘못된 높이를 넣으면 바닥을 다시 장애물로 만들거나 낮은 장애물을 지울 수 있다. 하한 0.3m보다 낮은 돌·턱·작은 물체는 이 매핑 스캔에서 제외될 수 있다. 이 스캔 하나만으로 로봇 충돌 회피의 전체 안전 영역을 판단하지 않는다.

### 5.4 검증 순서

Gazebo·SLAM이 실행된 환경에서 각 명령을 순차 수행한다. hz 명령은 관찰 후 Ctrl+C로 종료한다.

```bash
ros2 topic info /lidar/points -v
ros2 topic echo /lidar/points --once --field header
ros2 topic hz /scan/projected
ros2 topic echo /scan/projected --once --field header
ros2 run tf2_ros tf2_echo odom scan_ground
```

기대 프레임은 점군 lidar_link, 투영 스캔 scan_ground다. RViz의 Raw 3D cloud를 켜고, 기울어진 몸체의 점군이 수평 프레임으로 변환되는지 관찰한다. 바닥·상한 초과 점은 원본 점군에서 보여도 투영 스캔에서는 제외되어야 한다. pointcloud_to_laserscan은 scan 구독자가 없으면 점군 구독을 중단할 수 있으므로 SLAM 또는 RViz의 투영 스캔 표시를 켠다.

```bash
cd ~/Pysical_AI_book
python3 Ch11/scripts/check_slam_mapping.py --scan-topic /scan/projected \
  --skip-raw-scan-check --seconds 20 --output /tmp/slam_3d_runtime.json
bash Ch11/scripts/save_slam_map.sh "$HOME/Pysical_AI_book/Ch11/maps/projection_run1"
```

진단 도구는 지도·스캔 수신과 TF 연결을 확인하며 바닥 제거 정확도를 자동 판정하지 않는다. `/scan/projected`가 전부 inf이면 높이 기준·점군 범위·TF·실제 벽의 높이를 확인한다.

### 5.5 실제 Velodyne/Ouster 등의 점군 사용

센서 드라이버가 PointCloud2를 제공하고, `/odom` 및 실제 점군 frame까지의 TF가 있어야 한다. 기존 Gazebo 브리지는 필요 없다. 같은 odom/base_footprint 계약을 만족하는 로컬 추정이 이미 실행된 경우 다음으로 입력만 바꾼다.

```bash
ros2 launch my_quadruped_bot slam_3d.launch.py cloud_topic:=/ouster/points \
  ground_height:=0.0 use_sim_time:=false
```

이 예시는 외부 드라이버 연결 인터페이스이며 실물 장치 검증 결과가 아니다. use_sim_time=false는 SLAM·투영·프레임 발행의 시간 설정에 함께 적용된다. 로컬 추정과 센서 드라이버도 같은 실시간을 사용해야 한다. Gazebo와 연결한 외부/재생 점군은 동일한 시뮬레이션 시간축인지 먼저 확인한다.

### 5.6 경사로에서의 한계

IMU로 수평을 알아도 경사면의 바닥 높이를 자동으로 아는 것은 아니다. 이 솔루션의 ground_height는 고정된 수평 지면값이다. 경사로에서는 올라간 바닥 자체가 0.3m 위에 들어와 장애물로 남을 수 있다. 실제 경사로의 지면 제거에는 지면 평면·국소 지형 추정, 접촉·높이 추정 또는 3D 지도가 필요하다.

높이 필터는 천장·바닥을 지정 구간 밖으로 배제하는 방법이며 모든 경사면·계단·모션 왜곡을 해결하는 방법이 아니다. 센서 장착 각도를 바꾸는 것만으로 360도 전 방향 바닥 문제를 제거할 수도 없다.

## 6. 변경 파일과 검증 결과

- IMU 이력·장착 quaternion 합성: sensors/attitude_history.py.
- IMU 필터: sensors/scan_stabilizer.py. 11.5 slam_scan_filter.py는 자세 조회 함수를 분리해 게이트를 재사용한다.
- 수평 프레임: sensors/projection_frame.py 및 projection_frame.py 노드.
- 선택형 3D: robot.urdf.xacro, gazebo_control.xacro, simulation.launch.py, SLAM_simulation.launch.py, ros_gz_cloud_bridge.yaml.
- 실행·설정: slam_optimized.launch.py, slam_3d.launch.py, 튜닝·투영 YAML 및 slam_3d.rviz.
- 기존 slam.launch.py: 기본 동작을 유지하면서 필터 실행 여부·RViz 파일을 선택 가능하게 확장.
- 진단: check_slam_mapping.py에 --scan-topic 및 --skip-raw-scan-check 추가. 기본 11.5 동작 유지.

오프라인 전체 검사: **85개 실행, 79개 통과, ROS/Gazebo 의존 검사 6개 건너뜀**. 새 검사 12개는 IMU 부재·오래된/무효 자세·촬영 시각 선택·시간 역행·장착 회전 합성·수평 프레임 및 설정 계약을 확인한다. Python/YAML/XML 구문도 확인했다.

현재 환경에는 ROS·Gazebo가 없어 colcon 빌드, 3D 센서 SDF 변환·렌더링, 실제 점군 변환, 지도 생성·저장, WSL2 GUI 실행은 **NOT_RUN**이다. 위 순서로 실제 토픽·TF·지도와 저장 파일까지 확인해야 실습 실행 검증이 완료된다. 테스트 통과를 실측 튜닝 개선 또는 실물 센서 검증으로 표현하지 않는다.

공식 근거:

- [SLAM Toolbox Jazzy 파라미터](https://github.com/SteveMacenski/slam_toolbox/blob/jazzy/config/mapper_params_online_async.yaml)
- [pointcloud_to_laserscan 인터페이스](https://github.com/ros-perception/pointcloud_to_laserscan/blob/rolling/README.md)
- [점군 변환·높이·방위각 처리 구현](https://github.com/ros-perception/pointcloud_to_laserscan/blob/rolling/src/pointcloud_to_laserscan_node.cpp)
- [ros_gz 지원 메시지](https://github.com/gazebosim/ros_gz/blob/ros2/ros_gz_bridge/README.md)
