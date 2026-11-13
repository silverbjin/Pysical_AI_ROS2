# Ch07 §7.2 — 실제 OGRE2 RGB-D Image / CameraInfo 발행 실습 (2026-11-13 인수판)

> 기준: ROS 2 Jazzy, Gazebo Harmonic, `vision_basics`의 **실제 원본 RGB-D 모델**. 2026-11-13 공개 CI에서 이미지·CameraInfo·Optical TF·정상 종료를 검증했다. 이 가이드는 **Headless 실측 재현**을 다루며, 아래 2026-10-20 미수행·BLOCKED 기록은 원문 역사로 남겨둔다.

## 문제를 해결한 이유

- 최초 카메라 내부 `gz-sim-sensors-system`과 월드의 `Sensors`가 **동시에 로드**돼 OGRE2의 동일 HLMS 재질 블록을 생성하면서 Gazebo가 SIGABRT했다.
- 카메라 Xacro에서는 **중복 Sensors 플러그인만 제거**, 월드 SDF에는 하나만 유지한다. 원본 RGB-D sensor와 OGRE2는 그대로다.
- `<gz_frame_id>camera_optical_frame</gz_frame_id>`가 실제 Image/CameraInfo에 부착되므로 고정 optical TF의 이름과 일치한다.
- Gazebo는 공식 `--headless-rendering` 옵션을 사용한다. 센서 렌더러의 간헐적 SIGINT 교착을 피하기 위해 `--iterations 12000`으로 자연 종료한다.
- 관련 원인 분석과 원본 실측: [§7.2 보고서](SECTION_7_2_REPORT_KO.md), [최종 CI #43441463628](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43441463628), [Artifact #14045524144](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43441463628/artifacts/14045524144).

## 방법 A — 원격 공개 CI의 실제 검증 결과 확인

- 전용 workflow: `.github/workflows/book-ch07-127-egl-headless.yml`. `book-next-vision-localization.yml`의 **Ch11 기존 통과 시험은 이 카메라 변경 때문에 다시 실행하지 않는다**.
- 실행기: `ci/docker/ch07_camera_once.sh`, 독립 ROS 관측기: `ci/docker/verify_camera.py`.
- 실제 성공 문자열:
  - `CH07_127_SINGLE_WORLD_SENSORS_STATIC_CONTRACT_PASS`
  - `CH07_127_EXACTLY_ONE_RUNTIME_SENSORS_SYSTEM_PASS`
  - `BOOK_CH07_CAMERA_PASS`
  - `GAZEBO_NATURAL_ITERATIONS_EXIT_RC=0`
  - `CH07_127_FINAL stage=CAMERA_PASS rc=0 shutdown=OWNED_GROUPS_EXITED_NO_SIGKILL`
- 실제 관찰: RGB `640×480 rgb8`, 921600바이트, 유효 Image 3개, CameraInfo 3개, Optical TF 1개, `frame_id=camera_optical_frame`, K의 `fx=fy≈554.3827`.

## 방법 B — 강사 WSL2에서 동일 Headless Docker로 선택적 재현

**이 명령은 사용자가 직접 실행하는 선택적 로컬 검수다.** 2026-11-13 원격 공개 CI에서 PASS했으나 이 가이드 자체가 강사 WSL2 현장 PASS를 증명하는 것은 아니다.

~~~bash
# Windows WSL2 Ubuntu 24.04 / ROS 2 Jazzy 환경
cd ~/Pysical_AI_ROS2
git switch main
git pull --ff-only origin main
mkdir -p ci-results/vision/Ch07

IMAGE='ghcr.io/silverbjin/pysical-ai-book-gazebo@sha256:8288028a25df2dee0f8a4980231b0b9594bfd1048cdab9fc8ac49298e079e82f'
docker pull "$IMAGE"
docker run --rm --init --pull=never --shm-size=1g \
  -e RUN_SOURCE_SHA="$(git rev-parse HEAD)" \
  -e GITHUB_RUN_ID="owner_$(date +%s)" \
  -v "$PWD":/work -w /work "$IMAGE" \
  bash ci/docker/ch07_camera_once.sh

python3 -m json.tool ci-results/vision/Ch07/camera_data.json
python3 -m json.tool ci-results/vision/Ch07/result.json
~~~

임의의 GPU, Xvfb, 새로운 Docker 태그, 다른 Gazebo 월드를 **섞지 않는다**. 원격과 동일 이미지 digest를 재사용한다. `camera_data.json`의 **Image·Info 개수 및 frame_id, 결과의 종료 코드**가 모두 맞아야 Owner scoped PASS다. 실패하면 `gzserver.log`, `ogre2.log`, `stages.log` 원본을 보존한다.

## 예제 데이터 발행과 실제 Depth 인수의 차이

실제 `gz topic -l`에는 `/camera/image`, `/camera/camera_info`, `/camera/depth_image`, `/camera/points`가 존재한다. 다만 **이 검수는 ROS RGB Image와 CameraInfo만 수신해 확인했다**. Depth의 실제 값과 RGB-Depth 일치 여부, PointCloud 좌표 투영, GUI/RViz, 카메라를 이용한 물리 파지는 **별도의 다음 실습**이다.

ROS Topic 확인 명령은 `ros2 topic list -t`, `ros2 topic echo /camera/camera_info --once`, `ros2 topic hz /camera/image_raw`을 사용하되, **시뮬레이터가 실행 중인 별도 ROS 세션**에서 확인한다. 위 원샷은 자연 종료 후 컨테이너까지 정리하므로 종료 후 호스트에서 토픽이 보이지 않는 것이 정상이다.

---

## 과거 2026-10-20 사전 검토와 초기 실습 가이드 (원문 보존)

# LAB_7_2_GUIDE_KO — 7.2절 Gazebo Harmonic 카메라 센서 설정 및 데이터 수신

> 대상: Ubuntu 24.04 / ROS 2 Jazzy / Gazebo Harmonic, Ch07 단독 실습
> 기준 commit: a318c04a69a003e5c5d5998f077f2b8a8f36a1a5 (2026-10-20) · 상태: **BLOCKED — 센서 구성과 실행 경로 불충분**
> 실제 실행 검증: **미수행**. 아래 코드는 교재 실습 절차 및 실행 후 검증 기준이며, 출력 사례를 실측 결과로 제시하지 않는다.

## 실습 전 원칙
- 리포지토리 루트의 **Ch07/ros2_ws**를 작업 공간으로 사용한다. 설치된 패키지명은 **vision_basics**이다(원고의 my_robot_vision과 다름).
- 터미널마다 /opt/ros/jazzy/setup.bash → Ch07/ros2_ws/install/setup.bash 순서로 source한다. Ch08~Ch13 overlay가 AMENT_PREFIX_PATH에 섞이면 검증 결과가 바뀔 수 있다.
- 실제 카메라, 액션 서버, Gazebo controller, MoveIt 2 설정은 **존재 확인이 완료된 후** 해당 노드나 미션을 실행한다.
- ROS 관련 Python 바인딩은 Ubuntu/ROS apt 패키지를 우선한다. 글로벌 pip 설치가 ROS의 NumPy/Qt ABI와 충돌하지 않도록 주의한다.
- Gazebo에서의 노드 실행, 실제 팔/그리퍼 명령은 사람이나 실물 하드웨어가 없는 독립 시뮬레이션에서만 검증한다.

## 사전 점검
~~~bash
# Ubuntu 24.04 / ROS 2 Jazzy 전제. Ch07 단독 overlay에서 실행
source /opt/ros/jazzy/setup.bash
cd Pysical_AI_ROS2/Ch07/ros2_ws
echo "$ROS_DISTRO"
printenv AMENT_PREFIX_PATH | tr ':' '\n' | head -20
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install --event-handlers console_direct+
source install/setup.bash
ros2 pkg prefix vision_basics
~~~
~~~bash
# 실제 모델에 카메라와 optical frame이 있는지 소스 확인
grep -n 'camera_link\|camera_optical_frame\|<sensor' src/vision_basics/urdf/my_robot.urdf.xacro || true
# 원고에 적힌 경로가 있는지 확인 (없는 경로를 만들어졌다고 가정하지 않는다)
find src -type f \( -name '*camera*.xacro' -o -name '*simulation*.launch.py' -o -name '*.sdf' \) | sort
ros2 pkg executables vision_basics
ros2 pkg prefix my_robot_description || true
~~~

**예상 상태(원본):** 위 URDF에 카메라 정의가 없고, simple_image_subscriber는 ros2 pkg executables에서 발견되지 않을 수 있다. 이때 이미지를 받으려고 다음 단계로 넘어가지 말고 구성 결함을 먼저 해결한다.

## 센서/브리지 통합 후 검증
실제 camera가 포함된 Gazebo launch 또는 world를 먼저 실행한다. 어떤 launch 파일이 존재하는지 find로 확인한 뒤 그 **실제 파일명**을 사용한다. 확인하지 않은 simulation.launch.py 명령은 사용하지 않는다.

~~~bash
gz topic -l | grep -E 'camera|image|depth'
ros2 topic list -t | grep -E 'camera|image|depth'
ros2 topic info -v /camera/image_raw
ros2 topic hz /camera/image_raw
ros2 topic echo --once /camera/camera_info
ros2 run rqt_image_view rqt_image_view
~~~

RGB-D 구현을 택했다면 /camera/depth/image_raw의 encoding(32FC1/16UC1), 단위(m/mm), 유효 픽셀 비율과 Color/Depth의 정렬 여부도 확인한다.

## 증거·오류 구분
- gz 토픽 없음: 센서 생성/렌더러/시뮬레이션 일시정지/월드 plugin 문제.
- gz는 있음, ros2는 없음: ros_gz_bridge 토픽명·타입·방향 확인.
- 토픽은 있으나 구독 0: QoS 정책과 frame_id 확인.
- RViz 실행 오류: my_robot_description 및 파일 경로 문제를 카메라 실패와 구분.

**완료 기준:** 화면 1장, hz 측정값, CameraInfo K, image frame_id와 optical TF, depth 계약을 기록한다. 이번 검토에서는 해당 실행 검증을 수행하지 못했다.

## 기록·제출물
실습자는 git rev-parse HEAD, ros2 doctor --report, colcon build 종료 코드, 실행한 명령, topic/TF/action 확인 결과, 정상 및 실패 사례(스크린샷·로그)를 함께 남긴다. **정적 점검 결과와 실측 결과를 혼동하지 않는다.**

관련 리뷰: [SECTION_7_2_REPORT_KO.md](SECTION_7_2_REPORT_KO.md).
