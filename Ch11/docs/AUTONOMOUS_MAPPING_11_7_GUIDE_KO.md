# 11.7 자율 맵핑·지도 저장 프로젝트 실행 및 변경 보고서

## 1. 목표와 구현 범위

패키지는 `my_quadruped_bot`이며 소스는 Ch11에만 적용했다. 브랜치 `feat/ch11-autonomous-mapping`은 11.6의 89d7e1a를 기반으로 하므로 11.5·11.6 코드도 포함한다.

이번 프로젝트는 Nav2 없이 구동하는 **시간 제한 반응형 탐사**다. 지도 frontier를 찾아 경로를 계획하거나 모든 영역을 탐사했음을 판정하지 않는다. 임의 회전은 seed로 재현하고 더 여유 있는 방향을 우선하지만, 복잡한 미로를 완전히 탐사할 보장은 없다. 필요하면 운영자가 일시 정지·수동 구출·재개한다.

| 항목 | 초안 | 적용한 구현 |
|---|---|---|
| 월드 | 남쪽 벽 하나·기둥 하나 | 네 외벽·내부 칸막이·장애물이 있는 10×10m 로컬 SDF |
| 시작 | 고정 5/8초 지연 | 센서·지도·TF·기립 자세가 준비된 뒤 연속 5초 대기 |
| 전방 인덱스 | 배열 중앙 가정 | angle_min + i×angle_increment로 실제 방향 계산 |
| 충돌 판단 | 필터 스캔의 오래된 전방 거리 | 원본 /scan의 360도 유효성·전방·좌우·회전 여유 확인 |
| SLAM 준비 | 확인하지 않음 | /scan_stabilized의 시각·수신 상태도 별도로 확인 |
| 회전 | 타이머 횟수 | 관측 yaw 변화로 완료 확인, 12초 내 진전 없으면 정지 |
| 갇힘 | 무한 전진/회전 가능 | 8초간 이동 진전 부족 감지, 연속 회전 4회 제한, BLOCKED |
| 명령 단절 | 마지막 명령 유지 | FSM의 monotonic 시각 기반 0.5초 watchdog |
| 저장 | CLI 수동 실행 | 시간 종료·서비스 요청 시 정지 명령→비동기 CLI→PGM/YAML 검증 |
| 결과 | 지도가 완성되었다고 가정 | 부분 지도 가능성을 JSON에 명시, 정확도·전체 커버리지는 미검증 |

## 2. 설치·빌드

WSL2 Ubuntu 24.04 / ROS 2 Jazzy / Gazebo Harmonic 환경에서 가상환경을 해제하고 진행한다. 아래 경로는 실제 저장소 위치로 바꾼다.

```bash
cd ~/Pysical_AI_book
git status --short
git fetch origin
git switch --track origin/feat/ch11-autonomous-mapping
source /opt/ros/jazzy/setup.bash
sudo apt update
sudo apt install -y ros-jazzy-slam-toolbox ros-jazzy-nav2-map-server \
  ros-jazzy-teleop-twist-keyboard ros-jazzy-tf2-tools python3-yaml python3-matplotlib
cd Ch11/ros2_ws
rosdep install --from-paths src --ignore-src -r -y --rosdistro jazzy
colcon build --symlink-install --packages-up-to my_quadruped_bot
source install/setup.bash
ros2 pkg prefix my_quadruped_bot
```

로컬 브랜치가 이미 있다면 `git switch feat/ch11-autonomous-mapping`을 쓴다. prefix가 다른 장을 가리키면 새 터미널에서 Ch11 overlay만 적용한다. 모든 새 터미널에서:

```bash
source /opt/ros/jazzy/setup.bash
source ~/Pysical_AI_book/Ch11/ros2_ws/install/setup.bash
```

## 3. 통합 시스템 시작

### 방법 A: 준비 확인 후 탐사 노드를 별도 실행

터미널 1:

```bash
ros2 launch my_quadruped_bot mapping_total.launch.py
```

Gazebo·로봇·FSM·센서 브리지·기존 EKF·IMU 처리·IMU 스캔 필터·SLAM·지도 RViz가 실행된다. **아직 자율 이동 명령은 발행하지 않는다.** simulation/localization/slam.launch.py를 추가로 실행하지 않는다.

터미널 2에서 준비 상태를 먼저 확인한다.

```bash
ros2 lifecycle get /slam_toolbox
ros2 topic info /scan_stabilized -v
ros2 topic info /odom -v
ros2 run tf2_ros tf2_echo map base_footprint
```

그다음 터미널 2에서 탐사를 시작한다.

```bash
ros2 run my_quadruped_bot autonomous_explorer --ros-args \
  --params-file "$(ros2 pkg prefix --share my_quadruped_bot)/config/exploration.yaml"
```

별도 노드는 기본 출력 디렉터리 `~/Pysical_AI_maps`를 사용한다. use_sim_time=true가 기본이며, 현재 프로젝트는 시뮬레이션용이다.

### 방법 B: 한 번에 실행

기존 방법 A의 모든 노드를 종료하고 실행한다.

```bash
ros2 launch my_quadruped_bot mapping_total.launch.py start_explorer:=true \
  duration:=300.0 output_dir:="$HOME/Pysical_AI_maps"
```

start_explorer=true는 준비 완료 후 실제 이동 명령을 시작하는 선택이다. GUI를 사용하지 않으려면 rviz:=false, 넓은 탐색 튜닝을 비교하려면 profile:=wide_search를 추가한다. Gazebo 자체 GUI를 제거하는 headless 모드는 이번 인자가 아니다.

고정 TimerAction 없이 노드들을 시작한다. 탐사만 데이터 준비 조건을 기다리며, SLAM의 lifecycle은 공식 launch가 활성화한다. GroupAction으로 하위 런치 인자의 범위를 분리하여 시뮬레이션 RViz 비활성화가 지도 RViz 설정을 덮지 않게 했다.

## 4. 탐사 상태와 준비 조건

상태는 WAITING / FORWARD / TURN / BLOCKED / FINISHED이며, 수동 양보 상태는 PAUSED로 보고한다.

```bash
ros2 topic echo /exploration/status
```

JSON의 state/reason/readiness/save_state/save_error/save_prefix/map을 확인한다.

- 원본 스캔·IMU는 촬영 시각과 wall 수신 시각 모두 최근 0.4초 이내여야 한다.
- odom은 0.5초, 안정화 스캔은 1.2초, 지도는 10초 범위 내여야 한다.
- 스캔은 lidar_link의 360도 정보가 필요하다. NaN·음의 무한대·잘못된 범위·부분 FOV는 전진 허가로 해석하지 않는다. +inf는 센서 최대 거리 안에 반사점이 없다는 의미로 처리한다.
- 유효한 IMU 자세, 15도 이하 몸체 기울기, odom z=0.20~0.60m, free/occupied 셀이 있는 지도, odom 시각의 map→base_footprint TF가 필요하다.
- 모든 조건이 연속 5초 유지된 뒤 이동한다. Gazebo를 일시 정지하면 steady-clock 타이머가 데이터 단절을 감지하여 영속도 명령을 보낸다. 시간 reset은 자동 복구하지 않고 전체 시스템 재시작이 필요하다.

기본 전진은 0.05m/s, 회전은 0.15rad/s다. 전방 ±30도의 장애물이 0.9m 이내이면 일단 정지하고 더 여유 있는 좌·우 방향을 선택한다. 0.6~1.2rad 목표각을 정하며 관측 yaw로 회전 완료를 확인한다. 다음 전진은 1.05m의 여유를 확인한다.

회전과 전진 모두 전체 스캔의 최소 거리 0.5m보다 가까운 물체가 있으면 BLOCKED로 정지한다. 이 값은 다리·보행 여유를 고려한 교육용 보수적 반경이며 검증된 충돌 방지 인증값이 아니다. 2D 스캔 높이 밖의 낮은 장애물, 몸체 흔들림, 제동 지연을 모두 모델링하지 않는다.

8초 동안 0.05m도 이동하지 못하면 전진 명령만 반복하지 않고 회전을 시도한다. 0.10m 이상 진전하면 연속 회전 횟수를 초기화한다. 회전 중 yaw 진전이 없거나 반복 회전 제한에 도달하면 운영자 개입을 기다린다. 전체 경로 계획이나 후진 탈출을 자동 수행하지 않는다.

설정은 config/exploration.yaml에 있다. standalone 노드의 예:

```bash
ros2 run my_quadruped_bot autonomous_explorer --ros-args \
  -p duration:=180.0 -p linear_speed:=0.04 -p angular_speed:=0.12 \
  -p output_dir:="$HOME/Pysical_AI_maps/slow_run"
```

속도 상한은 이 교육용 구현에서 0.1m/s·0.3rad/s로 제한하며 시작 파라미터는 read-only다. duration은 최초 준비 완료 이후의 **wall 시간** 예산이며 입력 대기·시뮬레이션 일시 정지 시간도 포함한다. 300초 종료는 전체 지도 완성을 뜻하지 않는다.

## 5. 일시 정지·수동 구출·재개

탐사 노드를 유지하고 다음 서비스로 정지시킨다.

```bash
ros2 service call /exploration/enable std_srvs/srv/SetBool '{data: false}'
```

success=true 응답과 PAUSED 상태를 확인한다. 영속도를 한 번 전송한 뒤 주기적인 /cmd_vel 발행을 양보한다. 이는 물리적으로 정지했음을 보증하는 응답이 아니므로 Gazebo에서 실제 정지를 확인한 뒤 teleop를 시작한다.

```bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard --ros-args \
  -p speed:=0.04 -p turn:=0.12 -p stamped:=false
```

`k`로 정지하고 teleop 프로세스를 Ctrl+C로 종료한 후 재개한다.

```bash
ros2 service call /exploration/enable std_srvs/srv/SetBool '{data: true}'
```

재개는 탐사 상태·시간 예산을 새로 시작하며 준비 조건을 다시 기다린다. 지도는 SLAM 세션을 유지한다. BLOCKED도 이 절차로 수동 구출 후 재개한다.

활성 탐사 중 /cmd_vel 발행자가 둘 이상 보이면 탐사 노드가 영속도를 보내고 PAUSED로 전환한다. 이는 그래프 기반 충돌 감지이며 정식 명령 mux가 아니다. manual/auto를 동시에 발행하지 않는다. teleop를 종료하지 않고 enable=true를 요청하면 거부될 수 있다.

이번 변경에서 FSM에 command_timeout=0.5초 watchdog을 추가했다. 탐사 노드가 비정상 종료되어도 새로운 명령이 없으면 목표 속도를 0으로 하고 보행 주기 종료로 정지한다. 이는 물리적으로 즉시 정지하는 비상 제동기가 아니다. 키보드를 한 번 누르고 놓으면 명령이 만료되므로, 이동은 키 반복 입력으로 유지하고 정지는 `k`로 명시한다.

저장 작업 중에는 수동 모드 전환을 거부한다. SAVED 또는 SAVE_FAILED를 확인한 뒤 양보한다.

## 6. 정지·지도 저장

### 자동 저장

시간 예산 종료 시 FINISHED가 되고 영속도를 계속 발행한다. BLOCKED로 멈춘 경우에도 auto_save=true이면 현재까지의 부분 지도를 저장한다. 1초 동안 정지 명령을 유지한 뒤 별도 map_saver_cli 프로세스를 실행한다. 물리적 정지 여부를 이 지연만으로 측정한 것은 아니다. 저장은 비동기이며 wall 시간 30초를 초과하면 종료한다. Gazebo와 SLAM은 저장 완료까지 실행하고 Gazebo 시간을 재생 상태로 둔다.

기본 출력:

- maze_result_<UTC시각>.pgm: 지도 영상.
- maze_result_<UTC시각>.yaml: 지도 메타데이터.
- maze_result_<UTC시각>.save.log: 실제 CLI 출력.
- maze_result_<UTC시각>.mission.json: 저장 파일 검사·종료 사유·부분 지도 표시.

서로 다른 실행은 다른 이름을 사용하고 기존 파일은 덮어쓰지 않는다. save_state가 SAVE_PENDING→SAVING→SAVED인지 확인한다. SAVE_FAILED이면 save_error와 .save.log를 보고 수정한다. 파일 두 개가 존재하고 PGM 길이·메타데이터가 유효하며 free/occupied 픽셀이 있어야 SAVED로 판정한다. 정확도·폐루프·전체 커버리지까지 판정한 결과는 아니다.

### 운영자가 지금 저장

탐사가 활성화된 상태에서:

```bash
ros2 service call /exploration/save_map std_srvs/srv/Trigger '{}'
```

이 요청은 탐사를 FINISHED로 정지시키고 저장을 예약한다. **서비스 success=true는 요청 수락이며 파일 저장 성공이 아니다.** /exploration/status의 SAVED와 생성 파일을 확인한다. PAUSED 중에는 teleop와 충돌하지 않도록 저장 요청을 거부한다. teleop를 종료하고 탐사를 enable한 뒤 저장 요청하거나, 아래 수동 CLI를 사용한다.

auto_save=false로 시작했다면 시간 종료·BLOCKED 후 자동 저장하지 않으며 서비스 저장은 가능하다.

### 수동 저장

로봇을 멈춘 상태에서 저장소 루트에서:

```bash
cd ~/Pysical_AI_book
bash Ch11/scripts/save_slam_map.sh "$HOME/Pysical_AI_maps/maze_manual_run1"
```

이번 저장 경로는 trinary, free_thresh=0.196, occupied_thresh=0.65를 명시한다. 원고의 픽셀 255 고정 설명과 달리 Jazzy map_saver의 일반적인 free 출력은 254이며 occupied=0, unknown=205다. 실제 파일의 mode·threshold를 기준으로 해석한다. free_thresh를 높이면 gray=205가 재로딩 시 free로 분류될 수 있으므로 저장·재로딩 의미도 확인해야 한다.

YAML의 origin은 **map 좌표계**에서 격자 원점의 x/y/yaw다. Gazebo world와 같은 원점이라고 가정하지 않는다. PGM의 영상 좌표와 OccupancyGrid의 행 방향도 다르므로 단순히 영상의 위쪽을 y=0이라고 읽지 않는다.

## 7. 파일 분석·지도 품질 확인

파일명을 실제 생성된 YAML로 바꾼다.

```bash
cd ~/Pysical_AI_book
python3 Ch11/scripts/analyze_saved_map.py "$HOME/Pysical_AI_maps/maze_manual_run1.yaml" \
  --output /tmp/maze_map_report.json --preview /tmp/maze_map_preview.png
```

도구는 P5/P2 8-bit PGM, 가로·세로·배열 길이, 해상도·origin, 검정·밝은색·회색 픽셀 수를 확인하고 PNG 미리보기를 만든다. bounds_area_m2는 저장 격자 바운딩 박스 면적이며 실제 탐사 면적이 아니다. unknown 비율만으로 미로를 완전히 돌았는지 판단하지 않는다. JSON quality_verified=false는 자동 정확도 검증을 하지 않았다는 뜻이다.

실제 연결 점검:

```bash
python3 Ch11/scripts/check_slam_mapping.py --scan-topic /scan_stabilized \
  --seconds 20 --output /tmp/maze_runtime.json
ros2 run tf2_tools view_frames
```

수동 품질 점검은 같은 실험 조건에서 수행한다.

1. 네 외벽과 칸막이가 실제 월드 배치와 대응하는지 확인한다. 예시 미로를 모두 관측했는지는 별도 기록한다.
2. 직선 벽의 두께·휘어짐·중복을 확인한다. IMU만 원인으로 단정하지 말고 시각·TF·스캔 왜곡·매칭도 확인한다.
3. 시작점 귀환과 루프 클로저를 구분한다. 귀환만으로 루프가 최적화되었다고 결론 내리지 않는다.
4. 2D 스캔 높이에서 보이지 않는 장애물과 실제 바닥 점을 구분한다.
5. 관측된 지도와 비교할 때 map/world의 원점·방향 정합을 먼저 확인한다.

## 8. 문제 해결

| 현상 | 확인·대응 |
|---|---|
| WAITING 지속 | status.readiness에서 raw/stable/odom/imu/map 누락·지연 또는 TF·몸체 자세 원인 확인 |
| stable_missing_stale_or_future | IMU 기울기 필터 탈락·센서 시각·TF 확인. 예전 스캔으로 계속 움직이게 변경하지 않음 |
| 몸체가 기립하지 못함 | 먼저 10장 FSM·센서 그림 실행으로 복구. readiness 임계값을 무작정 완화하지 않음 |
| BLOCKED | 좁은 회전 공간·yaw 변화 없음·진전 부족. PAUSED 후 수동 구출 |
| PAUSED로 갑자기 전환 | 중복 탐사·teleop·CLI 등 /cmd_vel 발행자 확인 |
| SAVE_FAILED | nav2_map_server 설치·/map·Gazebo 시간·출력 폴더·로그 확인 |
| 지도가 뭉개짐 | 중복 TF·취득 시각·오도메트리·기울기·매칭을 순서대로 확인. yaw 입력을 무조건 끄지 않음 |
| SLAM 갱신은 있지만 미로 일부를 못 감 | 반응형 탐사 한계. 수동 개입 또는 이후 frontier/Nav2 구현 필요 |

탐사 노드 Ctrl+C로 종료하면 watchdog이 마지막 명령을 만료시킨다. 전체 launch 종료 전에 저장 완료를 확인한다. 시뮬레이션 시간 reset은 탐사·SLAM·위치 추정을 함께 재시작한다.

## 9. 검증과 한계

오프라인 전체 검사 **104개 실행, 97개 통과, ROS/Gazebo 의존 검사 7개 건너뜀**. 새 검사는 19개다. 준비 전 정지, 실제 각도 ROI, NaN/부분 FOV, 회전 여유, 센서 단절, 관측 yaw 진전, 시간 예산, 갇힘, watchdog, 미로·통합 구성, PGM/YAML 처리 등을 확인했다. 실제 FSM watchdog 연결 검사는 ROS 환경에서 실행하도록 포함했으며 여기서는 건너뛰었다.

현재 환경에는 ROS·Gazebo가 없어 colcon 빌드, 미로 렌더링, 실제 보행·충돌 회피·지도 확장·자동 저장 및 WSL2 GUI 실행은 **NOT_RUN**이다. 과거 센서 그림의 WSL2 검증을 이번 자율 탐사 검증으로 전용하지 않는다. 실제 실행은 readiness→관측 이동→정지/수동 전환→저장 SAVED→PGM/YAML·미로 대조 순서로 확인해야 한다.

순수 상태 머신 테스트와 합성 PGM 분석은 실행 논리·파일 처리를 검증하며 실제 지도 품질이나 탐사 성공을 증명하지 않는다. 이 프로젝트는 2D LiDAR 실습으로 구성했다. 11.6의 3D 투영 런치는 별도 실습이며 이 탐사기에 투영 스캔을 그대로 연결하지 않는다.

주요 변경 파일:

- mission/exploration_core.py: 센서 분석·상태 머신·command watchdog.
- mission/autonomous_explorer.py: ROS 준비 검사·상태·서비스·저장 작업.
- mission/map_artifacts.py, scripts/analyze_saved_map.py: 지도 파일 분석·미리보기.
- trot_controllerFSM.py: 실제 명령 수신 watchdog 연결.
- maze_room.sdf, mapping_total.launch.py, config/exploration.yaml: 통합 프로젝트.
- SLAM_simulation.launch.py: 기존 기본 월드를 유지하면서 world 인자 노출.
- save_slam_map.sh: 저장 임계값 명시.

공식 근거:

- [Jazzy 지도 저장 CLI 인자](https://github.com/ros-navigation/navigation2/blob/jazzy/nav2_map_server/src/map_saver/main_cli.cpp)
- [Jazzy PGM/YAML 저장 구현](https://github.com/ros-navigation/navigation2/blob/jazzy/nav2_map_server/src/map_io.cpp)
