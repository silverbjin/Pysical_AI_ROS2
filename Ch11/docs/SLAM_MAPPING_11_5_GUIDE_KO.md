# 11.5 SLAM Toolbox 지도 생성 실습·변경 보고서

## 1. 실행 구성

패키지명은 `quadruped_system`이 아니라 `my_quadruped_bot`이다. 이번 변경은 Ch11에만 적용한다.

| 실행 파일 | 포함된 기능 | 따로 중복 실행하지 않을 것 |
|---|---|---|
| `SLAM_simulation.launch.py` | Gazebo, 센서 브리지, 로봇 TF, FSM, sim_odometry, 기존 EKF, 선택적 센서 RViz | simulation / localization / FSM |
| `slam.launch.py` | 스캔 기울기 필터, 공식 async SLAM lifecycle 실행, 지도 RViz | SLAM Toolbox 또는 map→odom 발행자 |

기존 `figure_11_2.launch.py`는 `SLAM_simulation.launch.py`로 **이름을 변경했다**. 이전 이름은 더 이상 실행하지 않는다. 센서 그림용 RViz와 `/figure_11_2/imu_pose` 토픽은 유지한다. 기존 `run_figure_11_2.sh`도 새 런치를 호출한다. 사용 중인 가이드의 명령을 갱신했으며, 과거 디버깅 보고서와 실행 증거의 이름은 당시 기록을 보존한다.

데이터 및 TF 소유권:

- `/simulation/odom` → sim_odometry → `/odom/raw` → 기존 EKF → `/odom`, `odom→base_footprint`.
- `/imu/data_raw`도 기존 EKF가 사용한다.
- robot_state_publisher가 `base_footprint→base_link→lidar_link`와 관절 TF를 발행한다.
- `/scan` → slam_scan_filter → `/scan/slam` → SLAM Toolbox → `/map`, `map→odom`.

`base_footprint`는 현재 URDF에서 base_link와 원점·자세가 같은 고정 루트다. 이름만 보고 지면에 수평 투영된 프레임이라고 해석하면 안 된다. 필터는 실제 `odom→lidar_link` 자세를 확인한다. SLAM은 x/y/yaw를 사용하는 2D 모델이며, 이 구성 자체가 3D SLAM이 되는 것은 아니다.

11.4의 `/ekf_lab/*` 명령 적분 비교 실습은 매핑에 연결하지 않는다. 기본 위치 추정 입력은 **Gazebo 모델 관측 기반**이며, 실물의 접촉 기반 다리 오도메트리 성능을 검증한 것이 아니다.

## 2. 설치·빌드

WSL2 Ubuntu 24.04 / ROS 2 Jazzy / Gazebo Harmonic을 사용한다. rl_env·Conda는 해제하고, 이전 Ch09/Ch10 overlay를 source하지 않은 새 터미널에서 시작한다. 아래 저장소 경로는 자신의 경로로 바꾼다.

```bash
cd ~/Pysical_AI_book
git status --short
git fetch origin
git switch --track origin/feat/ch11-slam-mapping
source /opt/ros/jazzy/setup.bash
sudo apt update
sudo apt install -y ros-jazzy-slam-toolbox ros-jazzy-nav2-map-server \
  ros-jazzy-teleop-twist-keyboard ros-jazzy-tf2-tools python3-yaml
cd Ch11/ros2_ws
rosdep install --from-paths src --ignore-src -r -y --rosdistro jazzy
colcon build --symlink-install --packages-up-to my_quadruped_bot
source install/setup.bash
ros2 pkg prefix my_quadruped_bot
```

로컬 브랜치가 이미 있으면 `git switch feat/ch11-slam-mapping`을 쓴다. 이미 main에 병합했다면 main의 최신 코드를 사용해도 된다. 출력 prefix는 **Ch11의 install 경로**여야 한다. 다른 장 경로가 나오면 새 터미널에서 올바른 overlay만 source한다.

이후 **모든 새 터미널**에 다음 환경을 적용한다.

```bash
source /opt/ros/jazzy/setup.bash
source ~/Pysical_AI_book/Ch11/ros2_ws/install/setup.bash
```

## 3. 시스템 실행

### 터미널 1 — Gazebo·보행 제어·기존 EKF

```bash
ros2 launch my_quadruped_bot SLAM_simulation.launch.py start_rviz:=false
```

네 벽과 두 장애물이 있는 기존 sensor_figure_world.sdf를 재사용한다. 기립이 끝날 때까지 기다린다. 이 명령은 이동 명령을 자동 발행하지 않는다. **localization.launch.py를 별도로 실행하지 않는다.**

센서 그림만 다시 보려면 SLAM 없이 아래 명령을 실행한다.

```bash
ros2 launch my_quadruped_bot SLAM_simulation.launch.py
```

### 터미널 2 — SLAM·지도 RViz

```bash
ros2 launch my_quadruped_bot slam.launch.py
```

공식 `slam_toolbox/online_async_launch.py`를 포함해 configure→activate를 자동 수행한다. 이름만 Node로 실행하고 lifecycle을 활성화하지 않는 원고의 구성을 보완했다. 설치 버전의 지원 인자는 다음으로 확인한다.

```bash
ros2 launch slam_toolbox online_async_launch.py --show-args
ros2 lifecycle get /slam_toolbox
ros2 topic info /map -v
ros2 topic info /scan/slam -v
ros2 run tf2_ros tf2_echo map odom
```

정상 기대: lifecycle `active`, `/map` 발행자 1개, `/scan/slam` 발행자 1개, `map→odom` 변환 수신. 기존 EKF는 `odom→base_footprint`를 담당한다. SLAM 시작 직후 첫 유효 스캔과 TF가 준비될 때까지 지연될 수 있다.

RViz는 Fixed Frame=`map`, Map=`/map`의 Reliable/Transient Local, LaserScan=`/scan`의 Best Effort로 설정되어 있다. 빨간 점은 **원본 스캔**이다. 필터를 통과한 점만 보려면 LaserScan Topic을 `/scan/slam`으로 변경한다. 필터 탈락 시점에는 원본 점만 보일 수 있다.

### 터미널 3 — 키보드 탐험

```bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard --ros-args \
  -p speed:=0.05 -p turn:=0.15 -p stamped:=false
```

키 입력은 Gazebo 창이 아닌 이 터미널에서 받는다. `i`: 전진, `u/o`: 전진하면서 회전, `j/l`: 제자리 회전, `k`: 정지. Shift+J/L의 횡이동은 기존 보행 제어기의 실제 구현·안정성을 확인한 뒤 사용한다.

키를 놓는 것만으로 정지한다고 가정하지 않는다. 구간마다 `k`를 눌러 정지한다. `Ctrl+C` 후에도 움직임이 남으면 별도 터미널에서 다음 정지 명령을 보낸다. 기존 FSM의 명령 수신 watchdog을 이번 작업에서 추가한 것은 아니다.

```bash
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist \
  '{linear: {x: 0.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}'
```

먼저 짧은 직선 이동으로 실제 로봇 이동과 지도 갱신을 확인한다. 벽과 장애물에 닿지 않도록 낮은 속도로 내부를 돌고 출발점 부근으로 돌아온다. 루프 클로저는 충분한 이동·스캔 중첩·기하 특징과 임계값이 충족되어야 하며, 귀환만으로 발생을 보장하지 않는다. 현재 오도메트리는 모델 관측을 사용하므로 지도가 크게 휘었다가 펴지는 장면이 나타나지 않을 수 있다.

## 4. 실제 런타임 점검

Gazebo와 SLAM을 켠 상태에서 저장소 루트에서 실행한다. 명령을 발행하지 않는 읽기 전용 진단이다.

```bash
cd ~/Pysical_AI_book
python3 Ch11/scripts/check_slam_mapping.py --seconds 20 \
  --output /tmp/slam_mapping_runtime.json
ros2 run tf2_tools view_frames
```

진단은 `/map`, `/scan`, `/scan/slam`, `/odom` 수신, map→odom 존재, 스캔 촬영 시각 odom→LiDAR TF를 확인한다. 지도에는 유효한 크기·해상도·배열 길이와 free/occupied 셀이 모두 있어야 PASS다. 종료 코드 0과 JSON의 `pass: true`를 확인한다. 이것은 지도 수신·기본 연결 검사이며 지도 정확도, 충돌 회피, 루프 클로저 성공을 보증하지 않는다.

TF 트리는 `map→odom→base_footprint→base_link→lidar_link` 및 다리 링크가 연결되어야 한다. 같은 TF를 두 노드가 발행하면 view_frames가 연결되어 보여도 문제가 생길 수 있으므로, EKF·SLAM을 중복 실행하지 않는다.

## 5. 지도 저장

로봇을 정지하고 **Gazebo 시간은 재생 상태로 둔 채**, SLAM이 활성화된 상태에서 실행한다.

```bash
cd ~/Pysical_AI_book
bash Ch11/scripts/save_slam_map.sh
```

기본 출력은 `Ch11/maps/my_lab_map.pgm`과 `.yaml`이다. 폴더는 자동 생성하고 같은 이름의 파일이 있으면 덮어쓰지 않는다. 두 번째 기록은 새 이름을 사용한다.

```bash
bash Ch11/scripts/save_slam_map.sh "$HOME/Pysical_AI_book/Ch11/maps/my_lab_map_run2"
```

직접 CLI를 실행하려면 폴더를 먼저 만들고 확장자 없는 절대 경로를 준다.

```bash
mkdir -p "$HOME/Pysical_AI_book/Ch11/maps"
ros2 run nav2_map_server map_saver_cli -t /map \
  -f "$HOME/Pysical_AI_book/Ch11/maps/manual_run" --fmt pgm \
  --ros-args -p use_sim_time:=true -p save_map_timeout:=10.0 \
  -p map_subscribe_transient_local:=true
```

`.yaml`의 image/resolution/origin/threshold를 함께 보관한다. origin은 map 좌표계에서 격자 원점의 위치와 yaw이며 예시의 `[-10, -10, 0]`으로 고정되지 않는다. PGM만 저장하면 해상도·위치를 잃는다. 점유 격자 파일은 SLAM 포즈 그래프가 아니므로 이어서 매핑하려면 별도 직렬화가 필요하다.

선택: 전체 포즈 그래프를 저장한다. filename은 **서버가 해석할 절대 경로**다.

```bash
mkdir -p "$HOME/Pysical_AI_book/Ch11/maps"
ros2 service call /slam_toolbox/serialize_map slam_toolbox/srv/SerializePoseGraph \
  "{filename: '$HOME/Pysical_AI_book/Ch11/maps/my_lab_posegraph'}"
```

응답의 result와 생성 파일을 확인한다. 이번 실습의 slam.launch.py는 새 mapping 세션을 시작하며 그래프 재로딩을 자동 수행하지 않는다.

## 6. 흔들림 필터와 파라미터

`sensors/scan_gate.py`와 `slam_scan_filter.py`를 추가했다. 필터는 `/scan`을 최대 5개 보관하고, 촬영 시각의 `odom→lidar_link` TF를 최대 0.5초 범위에서 비동기적으로 기다린다. 최신 TF로 바꾸어 끼우지 않는다. TF·메시지 문제, 과거/미래 시각, 5도 초과 기울기, 0.15초 미만 간격은 전달하지 않는다. 성공 시 stamp/frame/ranges를 변경하지 않고 전달한다. 5초마다 누적 통과·탈락 수와 pending을 로그로 남긴다.

현재 10Hz 스캔에서 0.15초 최소 간격은 이상적인 조건에서 대략 5Hz 전달을 만든다. 이는 일정 비율로 대역폭을 줄이는 효과이며 발이 안정된 보행 위상을 선택하는 기능은 아니다. 자세 조건은 별도로 평가한다.

임계값 비교 실험은 SLAM을 종료한 다음 새 세션으로 실행한다.

```bash
# 예: 더 엄격한 기울기 제한
ros2 launch my_quadruped_bot slam.launch.py max_tilt_degrees:=3.0 min_scan_interval:=0.15

# 예: 기울기 제한·추가 시간 간격 없이 비교 (시각·TF 유효성 검사는 유지)
ros2 launch my_quadruped_bot slam.launch.py max_tilt_degrees:=180.0 min_scan_interval:=0.0
```

두 명령을 동시에 실행하지 않는다. 기울기가 임계값 이하여도 먼 거리의 광선은 바닥을 볼 수 있다. 낮은 문턱은 바닥 관측을 줄이는 대신 데이터 부족을 유발한다. 이 필터는 수직 흔들림, 수평 이동, 단일 스캔 안의 모션 왜곡을 보정하지 않는다. 경사면에서 장시간 기울어지면 대부분의 스캔이 탈락할 수 있다. 지도 품질 개선을 자동 보장하지 않는다.

| 원고 항목 | 적용·수정 내용 |
|---|---|
| solver_type: sparse_schur | 실제 파라미터 ceres_linear_solver: SPARSE_NORMAL_CHOLESKY 사용 |
| loop_search_space: 8.0 | 후보 거리 loop_search_maximum_distance=3.0, 매칭 탐색 폭 loop_search_space_dimension=8.0 구분 |
| unknown_space_filled, map_start_x/y | 기본 매핑 설정에서 제거; 미탐사 영역은 OccupancyGrid의 -1 |
| minimum_time_interval | 스캔 시각 간격 제한. 자세 안정 위상을 자동 탐지하는 값이 아님 |
| base_frame: base_link | 기존 EKF의 base_footprint와 정합. 현재 두 프레임은 고정 원점이 같음 |
| 로봇을 기울여 바닥을 안 보게 함 | 360도 LiDAR는 한쪽을 올리면 반대쪽을 내리므로 위쪽 설치 각도만으로 해결하지 않음 |
| 높이 필터의 0.2m | 3D 점군의 기준 프레임과 높이를 명시해야 의미 있음. 2D LaserScan에 z 값은 없음 |
| 완벽한 평면도 | 센서·TF·관측·환경에 따른 오차가 있는 추정 지도 |

loop_match_minimum_chain_size=10 등은 초기 교육용 설정이며 실제 보행·환경에 맞춘 실측 튜닝값은 아니다. 루프 임계값을 낮추는 것만으로 귀환 성공을 유도하면 잘못된 루프가 지도를 망가뜨릴 수 있다.

## 7. 문제별 점검

| 현상 | 먼저 확인할 항목 |
|---|---|
| Map이 표시되지 않음 | lifecycle active, `/scan/slam` 수신, map→odom, RViz map QoS |
| 원본 스캔만 보임 | 필터 누적 tilt/stale/queue_overflow, 촬영 시각 TF, IMU/EKF 자세 |
| Message Filter dropping | TF 시간 범위·시뮬레이션 시간·처리 부하; timeout만 크게 늘려 덮지 않음 |
| 로봇은 보이지만 움직이지 않음 | 기립 완료, teleop 터미널 포커스, Twist 형식, /cmd_vel 수신 |
| TF가 흔들리거나 지도가 점프함 | EKF·SLAM 중복, 이전 실습 노드 잔존, 시뮬레이터 시간 reset |
| 파일 저장 timeout | /map 발행, SLAM 활성화, Gazebo 시간 진행, transient local QoS |
| 벽이 두껍거나 바닥 점 발생 | 기울기와 높이 변화, 센서 시간·TF, 스캔 왜곡; 임계값별 실제 비교 |

시뮬레이터 시간을 초기화했다면 SLAM과 로컬 추정도 종료하고 함께 재시작한다. 필터의 시간 역행 처리가 SLAM 내부 포즈 그래프를 초기화하는 것은 아니다.

## 8. 검증 범위와 공식 근거

오프라인 전체 검사: **73개 실행, 67개 통과, ROS/Gazebo 의존 검사 6개 건너뜀**. 새 검사는 12개이며 모두 통과했다. Python 구문, YAML/XML, 셸 스크립트와 가이드 Bash 명령의 구문도 확인했다.

이번 작업 환경에는 `/opt/ros`와 Gazebo가 없어 colcon 빌드, 실제 lifecycle 전환, 지도 생성·저장 및 WSL2 GUI 실행은 **NOT_RUN**이다. 과거 figure 디버깅의 WSL2 성공 기록을 이번 SLAM 성공으로 전용하지 않는다. 오프라인 검사 결과는 `Ch11/evidence/slam_mapping_green.log`와 `slam_mapping_validation.json`에 남긴다. 위 런타임 진단과 지도 파일 생성까지 실제 WSL에서 통과해야 실습 실행 확인이 완료된다.

공식 소스 확인 기준: 2026-10-17 KST, Jazzy 브랜치.

- [SLAM Toolbox Jazzy lifecycle 런치](https://github.com/SteveMacenski/slam_toolbox/blob/jazzy/launch/online_async_launch.py)
- [Jazzy 매핑 파라미터](https://github.com/SteveMacenski/slam_toolbox/blob/jazzy/config/mapper_params_online_async.yaml)
- [스캔 시간·이동량 처리 구현](https://github.com/SteveMacenski/slam_toolbox/blob/jazzy/src/slam_toolbox_common.cpp)
- [Nav2 Jazzy 지도 저장 CLI](https://github.com/ros-navigation/navigation2/blob/jazzy/nav2_map_server/src/map_saver/main_cli.cpp)
- [ROS 2 teleop 코드](https://github.com/ros2/teleop_twist_keyboard/tree/rolling)
