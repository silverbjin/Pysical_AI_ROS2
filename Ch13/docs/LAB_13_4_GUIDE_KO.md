# 13.4 통합 시각 정보 처리 실습

> 2026-10-21 갱신: 승인된 EGL 전용 카메라와 촬영별 종단 계측을 구현·실측했다.
> worker의 GLFW 호출 결함은 제거했지만 **전체13.4 인수는 FAIL**이다.
> 실제13.4 시험20회는12 PASS/8 FAIL이며13.3 회귀는 MuJoCo PASS/Gazebo FAIL이다.
> 연속 추적·취소 완료·일부 정상 종료 미달을 유지한다. snapshot은 명시적 실험 옵션이며
> upstream 기본값·300ms·팔5Hz는 불변이다. main 병합·13.5 재개·배포 준비를 선언하지 않는다.
> [새 결과·원인·한계](SECTION_13_4_EGL_TRACE_RESULTS_KO.md),
> [이전 보존 판정(역사)](../evidence/section_13_4/cam-66d636a0/RETENTION_KO.md).

이 실습은 **실제 엔진 RGB-D → 탐지 → 촬영 시각 TF → odom 좌표의 목표**를 연결한다. 팔 추적은 기립 상태의 두 관절에 한정한 명시적 선택 기능이다. Nav2, 학습 보행, MoveIt, 물리 파지나 일반적인 충돌 회피 제어기는 포함하지 않는다. 원고의 “이동 중 항상 정확한 절대 좌표”를 보장하는 예제가 아니다.

현재 구현 범위와 실제 성공·실패는 [변경 보고서](SECTION_13_4_REPORT_KO.md), 각 실행의 `result.json`과 `summary.json`을 함께 확인한다. fixture 기하 시험과 YOLO 의미 인식은 별개다. 작은 빨간 상자는 COCO 객체로 인식되지 않을 수 있으며, 이때 fixture 검출로 몰래 대체하지 않는다.

## 1. 환경 준비

검증 환경은 Ubuntu 24.04 / ROS 2 Jazzy / Gazebo Harmonic / MuJoCo 3.3.7 / Python 3.12다. Windows에서는 이 명령을 PowerShell이 아닌 WSL Ubuntu 안에서 실행한다. 원래 Ch05~Ch12의 workspace나 설치 결과를 source하지 않는다. OpenGL/EGL 또는 WSLg 렌더링이 작동해야 한다. GUI 확인과 실로봇 검증은 별도다.

저장소 루트에서 시작한다. 다음 경로 변수는 이 실습 전용이며 기존 환경을 삭제하거나 덮어쓰지 않는다. 이미 환경이 있으면 새로 만들기 전에 그 환경의 버전을 확인한다.

```bash
export CH13_ROOT="$PWD"
export CH13_VENV="$HOME/ch13_vision_13_4_venv"
source /opt/ros/jazzy/setup.bash
sudo apt install -y python3-venv python3-colcon-common-extensions python3-vcstool \
  ros-jazzy-xacro ros-jazzy-robot-state-publisher ros-jazzy-vision-msgs \
  ros-jazzy-cv-bridge ros-jazzy-tf2-geometry-msgs ros-jazzy-message-filters \
  ros-jazzy-ros-gz-sim ros-jazzy-ros-gz-bridge ros-jazzy-gz-ros2-control \
  ros-jazzy-ros2-control ros-jazzy-ros2-controllers ros-jazzy-mujoco-vendor libglfw3-dev \
  libegl-dev libopengl-dev
python3 -m venv --system-site-packages "$CH13_VENV"
source "$CH13_VENV/bin/activate"
python -m pip install torch==2.5.1 torchvision==0.20.1 \
  --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r Ch13/requirements-vision-13-4.txt
export YOLO_CONFIG_DIR="$CH13_VENV/yolo_config"
mkdir -p "$YOLO_CONFIG_DIR"
export MUJOCO_GL=egl
```

`--system-site-packages`는 ROS의 `cv_bridge` 등을 사용하기 위함이다. NumPy 1.26.4를 유지한다. `pip check`는 확인하되, 시스템에서 상속한 무관한 패키지 오류까지 이 실습이 해결했다고 쓰지 않는다. 검증 환경에도 동일한 시스템 의존성 경고가 남아 있었다.

MuJoCo ROS 플러그인은 외부 workspace에서 고정 커밋으로 빌드한다. 이미 같은 고정 커밋의 설치본이 있으면 재사용한다. 기존 checkout을 reset하거나 실행 중인 다른 작업을 종료하지 않는다.

```bash
mkdir -p "$HOME/ch13_mujoco_ws/src"
vcs import "$HOME/ch13_mujoco_ws/src" < Ch13/ros2_ws/mujoco_ros2_control.repos
cd "$HOME/ch13_mujoco_ws"
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install
git -C src/mujoco_ros2_control rev-parse HEAD
# c261f5552edf124d1000a23fb25b6c07cadeb807 이어야 한다.
cd "$CH13_ROOT"
```

이 예제에 필요하지 않은 선택적 LiDAR 플러그인의 설치 경고와 필수 CameraPlugin/FreeJointStatePublisherPlugin 빌드 성공을 구분한다. 외부 checkout은 수정하지 않는다. 승인된 snapshot 카메라 파생본만 Ch13 별도 패키지에 제한적으로 복사했으며 [출처 명세](REUSE_MANIFEST.md)를 따른다.

## 2. Ch13 다섯 패키지 독립 빌드

새 터미널에서는 위 경로 변수와 venv를 다시 설정한다. ROS → 외부 MuJoCo → 해당 Ch13 설치본 순서이며, Ch13은 빌드한 뒤에만 source한다.

```bash
source /opt/ros/jazzy/setup.bash
source "$HOME/ch13_mujoco_ws/install/setup.bash"
source "$CH13_VENV/bin/activate"
cd Ch13/ros2_ws
python -m colcon --log-base log13_4 build --base-paths src \
  --build-base build13_4 --install-base install13_4 \
  --packages-select integrated_robot_interfaces integrated_robot_vision \
                    integrated_robot_description integrated_robot_runtime integrated_robot_camera \
  --cmake-args -DPython3_EXECUTABLE="$CH13_VENV/bin/python"
source install13_4/setup.bash
cd "$CH13_ROOT"
ros2 interface show integrated_robot_interfaces/msg/TrackedTarget
```

최종 검증기는 매 실행마다 UUID가 다른 새 build/install/log 경로를 사용한다. 예전 `build13_1`이나 다른 장의 패키지는 필요하지 않으며 자동 삭제하지 않는다.

### 2.1 snapshot 카메라 명시 선택과 설치 감사

`vision_camera_backend:=snapshot`은 두 mjData 버퍼의 소유권을 분리한 Ch13 전용
카메라다. `upstream`은 비교용 기존 구현이며, 최종 국소 인수를 통과하기 전에는
기본값을 바꾸지 않는다. 이 선택은 Gazebo 센서 구현을 바꾸지 않는다.

```bash
python Ch13/scripts/verify_all_13_4.py \
  --audit-install-prefix Ch13/ros2_ws/install13_4
ros2 run integrated_robot_camera camera_plugin_probe
ros2 launch integrated_robot_runtime vision_system.launch.py \
  engine:=mujoco detector_backend:=color_fixture \
  vision_camera_backend:=snapshot tracking_enabled:=false
```

감사는 다섯 패키지의 source/share·Python 실행 환경·configure-time C++ source manifest·
실제 probe·camera/mailbox 두 라이브러리 경로와 해시를 검사한다. probe 단독 성공은
엔진이 해당 .so를 사용했다는 증거는 아니다. native 검증기는 자체 엔진 PID의 실제
매핑과 class ID까지 기록한다. 누락/경로 불일치이면 시작 전에 실패하며 자동 fallback은 없다.

snapshot 비전 경로는 `auto_register_cameras=false`를 전달한다. 별도 class ID를 기존
underlay가 인식하지 못해 원본 카메라를 추가 렌더링하는 것을 막기 위함이다. 정상 로그에
`SnapshotCameraPlugin initialized`는 있어야 하며 원본 CameraPlugin 자동 등록은 없어야 한다.
검증기는 `/overview/*`, `/eye_in_hand/*`의 숨은 기본 발행자도 검사한다.

한 시험씩 실행하고 `result.json`의 cleanup/정상 종료를 확인한 뒤 다음 시험을 시작한다.
새 output 디렉터리를 사용하며, 촬영300ms·TF100ms·팔5Hz 기준을 늘려 통과시키지 않는다.

```bash
python Ch13/scripts/run_vision_13_4.py --engine mujoco --scenario static \
  --detector-backend color_fixture --vision-camera-backend snapshot \
  --output-dir /tmp/ch13-snapshot-static-new
# 위 실행이 완전히 종료된 뒤 delay, yolo, tracking, safety를 각각 새 output으로 실행한다.
# 추론 기본10Hz, 비교 실험은 --inference-rate-hz 15를 명시한다.
```

라이브러리나 Xacro 변경 후에는 재빌드와 설치 감사를 반복한다. 예전 overlay가 먼저 잡히면
새 셸에서 ROS → 고정 외부 underlay → venv → 원하는 Ch13 설치만 순서대로 source한다.
잔여 엔진이 있으면 다음 엔진을 띄우지 말고 자체 소유 프로세스의 종료 기록부터 확인한다.

geometry CLI도 static의 cleanup 기록이 없거나 잔여 PID가 있으면 delay를 시작하지 않는다.
일괄 검증기는 기존13.3 회귀의 실행/종료가 FAIL 또는 미확인이면 다음 엔진을 시작하지
않는다. 중단된 뒤 그룹이 UNVERIFIED로 남는 것은 정상적인 fail-closed 동작이다.
다음 실행 전에 임의 PID를 종료하지 말고 소유권과 로그를 확인한다. batch smoke의
제3자 사진 주석은 weights 폴더가 아닌 해당 batch의 ignored build 경로에 남는다.

## 3. 명시적 모델 준비와 단독 YOLO 시험

가중치와 시험 사진은 Git에 넣지 않는다. 먼저 [자산 명세](../config/vision_assets.json)의 URL·버전·SHA-256·권리 관련 선언을 검토한다. 해시는 동일성 검사이지 법적 사용 허락이나 최초 다운로드의 절대적 신뢰 보장이 아니다. Ultralytics와 모델의 적용 조건을 별도로 확인한다.

```bash
python Ch13/scripts/fetch_vision_assets.py --cache-dir "$HOME/ch13_vision_13_4_assets"
python Ch13/scripts/verify_yolo_13_4.py \
  --weights "$HOME/ch13_vision_13_4_assets/yolov8n.pt" \
  --image "$HOME/ch13_vision_13_4_assets/bus.jpg" \
  --output /tmp/ch13-yolo-smoke-new/result.json \
  --annotation-dir "$HOME/ch13_vision_13_4_assets/annotations"
```

누락·해시 불일치·SDK 오류는 실패다. 노드가 모델 이름만 보고 자동 다운로드하거나 다른 검출기로 바꾸지 않는다. SDK autoinstall은 비활성화한다. CPU predictor의 첫 설정이 스레드 수를 바꾸므로 생성자에서 비공개 준비 추론 후 1개로 복원한다. 준비용 영상을 센서 영상이나 탐지 결과로 발행하지 않는다.

버스 사진의 성공은 실제 엔진 영상에서 객체를 찾았다는 뜻이 아니다. 사진 및 주석 영상은 권리 확인이 끝나지 않았으므로 저장소 밖 캐시에 남긴다.

## 4. 먼저 관찰 전용으로 실행

한 번에 엔진 하나만 실행한다. 서로 다른 엔진을 같은 ROS domain에서 동시에 실행하면 clock·관절·TF 소유권이 충돌한다.

```bash
export ROS_DOMAIN_ID=154
ros2 launch integrated_robot_runtime vision_system.launch.py \
  engine:=gazebo detector_backend:=color_fixture tracking_enabled:=false
# Gazebo를 완전히 종료한 뒤 engine:=mujoco로 바꿔 반복한다.
```

이는 빨간 물체의 기하 시험용 검출기다. 실제 YOLO 실행은 별도 터미널 세션에서 다음처럼 지정한다.

```bash
ros2 launch integrated_robot_runtime vision_system.launch.py \
  engine:=mujoco detector_backend:=yolo \
  weights_path:="$HOME/ch13_vision_13_4_assets/yolov8n.pt" tracking_enabled:=false
```

통합 launch는 엔진 컨트롤러가 실제 active가 된 뒤 팔 stow → 측정 안전 확인 → 다리 기립 순서로 기동한다. 기존 13.3의 지연 데모 vision 노드를 중복 실행하지 않는다. `tracking_enabled=false`는 시선 추적을 끈다는 의미이지 시동 stow/기립까지 금지한다는 의미는 아니다. 이 lifecycle은 모터 Torque Off를 구현하지 않는다.

13.4 통합 launch의 MuJoCo 기본값은 `mujoco_headless:=true`이다. 물리 엔진과
eye-in-hand RGB-D 카메라는 계속 실행하고 큰 시뮬레이터 뷰어만 끈다.
GUI 관찰이 필요하면 `mujoco_headless:=false`를 명시한다. 이 환경에서는 뷰어를
켜면 이미지가 수신 시점부터 150–300ms 오래되어 지연 시험이 실패할 수 있었다.
직접 실행하는 기존 description launch의 기본값은 이전처럼 뷰어 켜짐이다.

| 데이터 | 토픽 / 계약 |
|---|---|
| RGB | `/camera/color/image_raw`, 320×240 RGB8/BGR8 |
| 정렬 depth | `/camera/aligned_depth_to_color/image_raw`, 32FC1 m 또는 16UC1 mm |
| 보정 | `/camera/color/camera_info`, 같은 optical frame·해상도·정렬/무왜곡 조건 |
| 2D 탐지 | `/vision/detections`, 원본 촬영 header 유지 |
| 원시/필터 점 | `/vision/target_raw`, `/vision/target_filtered`, `PointStamped` in `odom` |
| 제어용 유효성 | `/vision/tracked_target`, valid/status/track_id와 원본 촬영 시각 |
| 제어 상태/감사 | `/architecture/visual_tracking`, `/architecture/arm_command` |

카메라 optical 축은 오른쪽 X, 아래쪽 Y, 전방 Z다. TF는 `odom → base_footprint → base_link → arm_* → camera_link → camera_sensor_frame → camera_optical_frame`으로 연결된다. RSP가 내부 관절/고정 TF, native_pose_adapter가 유일한 외부 root TF와 odom을 소유한다. **현재 base_footprint는 본체의 z/roll/pitch도 포함하며 Nav2용 지면 투영 프레임이 아니다.**

## 5. 좌표와 시각의 의미 확인

역투영은 `X=(u-cx)d/fx`, `Y=(v-cy)d/fy`, `Z=d`이다. bbox 안 5×5 패치의 유효 depth 중앙값을 사용하며 최소 5개 표본, [0.1,5]m 범위와 MAD 제한을 확인한다. 행 패딩·endian·mm 변환을 검사한다. 임의의 미정렬 RGB와 depth를 합치지 않는다.

- RGB-depth 시각 차이 ≤30ms, 입력 최대 ROS/벽시계 age 300ms, CameraInfo age ≤1s다.
- 토픽 도착 순서는 보장되지 않는다. 탐지 후보 metadata는 RGB-D 캐시와 같은 최대 10건 안에서 원래 촬영/수신 기한 동안 기다린다. 가장 최신의 **완성된** RGB-D 후보 한 건만 처리 슬롯에 넣으며, 더 최신인 미완성 후보가 신선한 완성 후보를 지우지 않는다. 기다리거나 중복 수신했다고 TTL을 연장하지 않는다.
- TF는 촬영 시각의 정확한 변환을 최대 100ms 기다린다. 실패 시 latest TF로 대체하지 않는다.
- odom에서 대상별 LPF(tau=.2s)를 적용한다. 객체의 절대 pose나 파지 방향을 추정하는 것은 아니다. 공분산은 depth 표본 기반 휴리스틱이며 교정된 불확실성 보장이 아니다.
- 시계 역행·보정 변경·TTL·대상 전환·모호한 후보는 유효성을 잃게 한다. last known 점의 header를 현재 시각으로 바꾸어 재발행하지 않는다.

촬영 당시 base 좌표는 현재 base 좌표와 다르다. 제어기는 odom의 목표를 신선한 측정 관절 시각의 TF로 다시 옮겨 소각도 명령을 계산한다. 이동 물체 예측·노출 시간 보정·일반적인 전신 안정화는 구현하지 않았다.

## 6. 제한적 시선 추적 선택

처음에는 fixture 관찰만 한다. `/architecture/startup`의 READY와 신선한 valid 목표, 측정 기립 자세를 확인한 뒤에만 명시적으로 켠다.

```bash
ros2 service call /manipulation_node/set_visual_tracking std_srvs/srv/SetBool '{data: true}'
ros2 topic echo /architecture/visual_tracking
# 정지 요청
ros2 service call /manipulation_node/set_visual_tracking std_srvs/srv/SetBool '{data: false}'
```

`arm_joint_1`, `arm_joint_5`만 영점 대비 ±.04rad, 목표 증분 ≤.02rad/200ms, 명령 간격 ≥200ms다. 나머지 네 축은 활성화 순간의 안전 측정값으로 고정한다. 작은 국소 Jacobian 제어이지 MoveIt/일반 IK/충돌 회피가 아니다. 실제 위치·속도 제한은 별도 측정으로 확인한다.

팔 stow, PickObject, 시선 추적, 벤치마크는 manipulation_node의 같은 소유자를 거친다. 다른 노드에서 trajectory를 발행하지 않는다. 미확인 send와 cancel 중에도 예약을 유지하며 취소 응답만으로 해제하지 않는다. terminal 결과가 500ms 안에 확인되지 않으면 fault를 유지한다. 신선한 안전 입력과 미완료/외부 명령 부재를 확인한 뒤에만 다음 서비스를 사용한다. 자동 복구·자동 재시작은 없다.

활성화 ACK는 주기 보고를 기다리지 않고 즉시 발행된다. 상태와 명령의
`session_generation`, 명령 `goal_uuid`, 상태의 `owner` 진행 기록을 함께 확인한다.
ACK 후 안전 조건을 잃으면 자동으로 다시 켜지지 않는다.

```bash
ros2 service call /manipulation_node/recover_arm_ownership std_srvs/srv/Trigger '{}'
```

이 서비스는 소유권 fault만 해제하며 팔을 자동으로 움직이지 않는다. 추적 중단 후 `arm_safe`가 거부되면 terminal 결과와 신선한 측정을 확인하고 명시적으로 stow를 요청해 안전 영점을 다시 확인한 뒤 재선택한다. stow 자체는 실제 팔 움직임이므로 주변 간섭이 없는 실습 월드에서만 요청한다.

```bash
ros2 service call /manipulation_node/stow std_srvs/srv/Trigger '{}'
```

활성화를 거부하거나 중간에 OFF가 되면 reason과 원본 로그를 먼저 확인한다. 허용치를 넓히거나 서비스를 반복 호출해 실패를 숨기지 않는다. PickObject는 여전히 dry-run 프로토콜이며 실제 파지 성공을 반환하지 않는다.
시동 stow는 측정한 안전 영점 자세다. 운반용 접힘 자세나 적재 보행의 안전 인증으로 간주하지 않는다. 첫 유효 목표를 아직 획득하지 못했다면 target 토픽의 메시지 부재와 `/vision/status` 진단을 함께 읽는다.

## 7. 재현 가능한 자동 시험

최종 일괄 검증은 새로운 빈 출력 경로를 지정한다. 모든 엔진과 무거운 테스트를 순차 실행하므로 시간이 걸린다. 이전 PASS를 읽어 성공 처리하지 않는다.

```bash
python Ch13/scripts/verify_all_13_4.py \
  --weights "$HOME/ch13_vision_13_4_assets/yolov8n.pt" \
  --image "$HOME/ch13_vision_13_4_assets/bus.jpg" \
  --mujoco-underlay "$HOME/ch13_mujoco_ws/install/setup.bash" \
  --output-dir /tmp/ch13-final-new-run
```

완료 후 `summary.json`의 그룹별 결과를 읽는다. 필수 기하·안전·인프라 실패/누락은 FAIL, 그 외가 통과했어도 YOLO/추적 미달은 PARTIAL이다. 전체 그룹을 실제 실행해 통과한 경우만 PASS다. 반환값 0인 PARTIAL도 “13.4 전체 성공”은 아니다. RUNNING/UNVERIFIED 역시 성공이 아니다.

개별 조사에는 다음을 사용하며 출력 경로를 매번 바꾼다.

```bash
python Ch13/scripts/run_vision_13_4.py --engine gazebo --detector-backend color_fixture \
  --scenario geometry --output-dir /tmp/ch13-gz-geometry-new
python Ch13/scripts/run_vision_13_4.py --engine mujoco --detector-backend color_fixture \
  --scenario tracking --output-dir /tmp/ch13-mj-tracking-new
python Ch13/scripts/run_vision_13_4.py --engine gazebo --detector-backend color_fixture \
  --scenario safety --fault images --output-dir /tmp/ch13-gz-images-new
```

기하는 static/delay 각각 ≥30개 촬영 표본, RMS ≤.03m/≤.05m를 요구한다. 지연 시험은 같은 팔 소유자의 명시적 벤치마크로 q1을 .03rad/2s 진동시키며 150ms **추가** 지연을 준다. 물체의 전면 x=.98m와 광선의 교차점을 비교한다. 중심 x=1m를 표면 정답으로 쓰지 않는다. 이는 촬영 TF에 의존하는 깊이 일관성 시험이지 독립적인 모든 TF 오차 계측은 아니다.

5초 추적 시험은 실제 물체를 y=.02m 옮긴 복사 월드를 사용하고 픽셀 오차 20% 감소·명령 및 측정 제한을 검사한다. 안전 시험은 새 엔진에서 실제 목표를 보낸 후 입력을 끊고 300ms+200ms 이후 새 목표가 없는지 확인한다. `--fault images`는 소비 입력 차단(카메라는 계속 동작), `tf`는 해당 런처의 RSP만 종료, `joints`는 joint_state_broadcaster만 비활성화한다. 후자는 관절 TF도 함께 오래되므로 독립적인 TF 정상 상태에서의 관절 손실 실험은 아니다. 시동/활성화가 거부되어 fault를 주지 못했다면 그 경로는 미검증이다.

원본 RGB/depth/전체 CameraInfo, 촬영 TF, 관절/속도/명령·액션 UUID, 소스 바이트 해시, clock/TF 소유권, 종료와 잔존 PID를 보존한다. Jazzy 수신 API에 GID가 없어 TF 소유권은 그래프·전체 모델 간선·코드 계약의 추론이며 패킷별 발행자 인증은 아니다.

## 8. 종료와 문제 해결

일반 사용은 통합 launch 터미널에서 Ctrl+C로 종료한다. 자동 시험은 먼저 새 명령을 끄고 terminal 취소를 기다린 뒤 ROS 노드와 해당 엔진만 종료한다. Gazebo server stop ACK와 실제 프로세스 종료를 구분한다. 강제 종료는 해당 실행의 FAIL이다. 잔존 PID 또는 종료 미확인이 있으면 다음 엔진을 시작하지 않는다. 무관한 프로세스를 일괄 종료하거나 WSL을 재시작하지 않는다.

- `NO_FRESH_ALIGNED_PAIR`: frame/해상도/정렬/시각 차이와 RGB·depth·Info 수신을 확인한다. 최신 TF로 우회하지 않는다.
- `EXPIRED_*`: 추가 처리 지연뿐 아니라 렌더링·수신·추론·스케줄링 시간을 포함한다. CPU 스레드 예산과 실제 주기를 확인한다. 10Hz/15Hz/50Hz는 상한 또는 목표이지 hard realtime 보장이 아니다.
- `TF_UNAVAILABLE`: 촬영 시각의 odom/root 및 관절 TF가 버퍼 안에 있는지 확인한다. 이미지 시간이 0이거나 시계가 역행하면 새 epoch 입력을 기다린다.
- 추적 OFF/fault: 원인 입력을 먼저 복원하고 새 사용자 요청이 있을 때만 다시 선택한다. 불완전한 취소를 물리 정지나 Torque Off로 간주하지 않는다.
- YOLO 빈 결과: 빨간 상자를 COCO 캔으로 가정하지 않는다. 빈 탐지와 추론 자체가 만료되어 결과를 발행하지 못한 경우를 구분한다.
- 관성 루트/KDL·시뮬레이터 종료 경고: 원본 로그와 결과에 남긴다. 앞선 실행의 성공으로 현재 경고/실패를 덮지 않는다.

## 추론 주기 비교 옵션 (2026-10-19)

탐지 기본 상한은 10Hz이다. 명시적으로 `max_rate_hz:=15`를 launch에 전달하거나,
검증 도구에 `--inference-rate-hz 15`를 지정해 승인된 15Hz 비교를 수행할 수 있다.
0 초과 15 이하의 유한값만 허용한다. 이는 추론 시작 주기의 상한이지 처리량 보장이나
실시간성 보장이 아니다. 촬영 시각 300ms, 팔 명령 5Hz 안전 기준은 그대로 적용된다.
각 비교는 별도 evidence 디렉터리에 저장하고, 안전 정지는 실패로 기록한다.

## 9. 승인된 EGL snapshot·진단 계측 재현 (2026-10-21)

먼저 위 절차로 Ch13의 다섯 패키지를 빌드하고 **새 설치본 하나만** source한다.
기존 카메라/엔진은 종료·잔여 없음이 확인된 상태에서 시작한다. snapshot은 기본값이
아니며, 자동 fallback하지 않는다. EGL 초기화 실패는 실행 실패다. OpenGL 개발 의존성은
검증된 Ubuntu의 opengl rosdep 경로에도 포함되지만 위 설치 예에는 EGL을 명시했다.

수동 관찰 예(팔 추적을 자동 활성화하지 않음):

```bash
export CH13_TRACE_RUN="$(python -c 'import uuid; print(uuid.uuid4())')"
ros2 launch integrated_robot_runtime vision_system.launch.py \
  engine:=mujoco detector_backend:=color_fixture mujoco_headless:=true \
  vision_camera_backend:=snapshot trace_enabled:=true trace_run_id:="$CH13_TRACE_RUN"
```

이 수동 launch만으로 파일 evidence가 자동 생성되지는 않는다. 종료 후 잔여를 확인하고,
다음 자동 시험으로 관측·소스/설치 감사·원본 파일·해시를 함께 기록한다.

```bash
export CH13_EGL_OUTPUT="$(mktemp -d)"
python Ch13/scripts/run_vision_13_4.py --engine mujoco --scenario static \
  --detector-backend color_fixture --vision-camera-backend snapshot \
  --trace-enabled --output-dir "$CH13_EGL_OUTPUT/static"
python -m json.tool "$CH13_EGL_OUTPUT/static/trace_summary.json"
```

runner는 각 호출의 새 EvidenceRun UUID를 trace에 전달한다. 기존 출력 폴더를 재사용하지
않는다. `result.json`은 제품 검사, `trace_summary.json`은 진단, `system.log`는 실제 종료와
producer별 totals다. `trace.jsonl`에는 발생 시각과 observer 수신 시각을 별도로 보존한다.
정적 OFF 비교는 `--trace-enabled`를 빼고 새 폴더를 쓴다. 지연은 `--scenario delay
--processing-delay-s .15`, 추적은 `--scenario tracking --inference-rate-hz 10` 또는15를
별도 호출로 사용한다. 수신 후/촬영 후300ms·TF100ms·팔5Hz는 변경하지 않는다.

`PARTIAL`은 받은 exact-capture 구간만 관측했다는 뜻이며 전체 유실0이나 성공 보장이 아니다.
상충/다른 boot/다른 clock/불완전 publication은 종단 합산하지 않는다. native render/readback은
API 구간이고 DDS·스케줄링·callback 잔여 시간과 구분한다. ROS 시간과 monotonic을 섞지 않는다.
Gazebo의 native 내부는 UNVERIFIED로 남는다. source provenance/소유 PID/EGL 로그가 없으면
snapshot native 분석도 인정하지 않는다. 실패 뒤 자동 재시도·재활성화하지 않는다.

[실제22회 결과와 다음 수정 경계](SECTION_13_4_EGL_TRACE_RESULTS_KO.md)를 먼저 읽는다.
현재 연속 추적·취소·일부 종료가 미달이므로 이 절차는 배포·파지·13.5 진행 권고가 아니다.
