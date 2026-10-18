# Ch13 카메라 snapshot 소유권 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. 사용자는 네이티브 실행을 선택했다. 서브에이전트/별도 리뷰 에이전트를 호출하지 않는다.

**Goal:** Ch13 전용 MuJoCo 카메라 플러그인에서 촬영 snapshot의 생산자/렌더러 소유권을 분리하고, 실제 엔진으로 시각 정합·안전·설치 재현성을 검증한다.

**Architecture:** 생산자 제어 스레드는 전달받은 control_data snapshot을 두 mjData 중 pending에만 복사하고 단일 렌더러는 교환한 render 버퍼만 읽는다. 시각·epoch·sequence·카메라 선택은 함께 전달하고, 렌더/발행/join 동안 metadata mutex를 보유하지 않는다. 라이브 물리 데이터/pre_step으로 호출 위치를 바꾸지 않으며 원본 외부 플러그인은 그대로 둔다.

**Tech Stack:** ROS 2 Jazzy, ament_cmake/C++17, MuJoCo3.3.7, pluginlib, rclcpp, GLFW/OpenGL EGL, gtest, pytest, colcon, 실제 MuJoCo/Gazebo.

**Spec:** `Ch13/docs/specs/2026-10-19-camera-snapshot-ownership-design.md` — 사용자 승인. 현재 문서는 **구현 계획 검토 대기**이며 제품 코드/외부 복사는 아직 변경하지 않는다.

## Global Constraints

- 기준 HEAD `00cb1d4558289aff666a89941ea783ef06194210`, 절 브랜치 `feat/ch13-section-13-4`. 사용자 변경이 있으면 보존하고 겹치는 변경만 확인한다.
- 외부 원본 `ros-controls/mujoco_ros2_control@c261f5552edf124d1000a23fb25b6c07cadeb807`은 수정/재빌드하지 않는다. Ch05–Ch12와 synced sources도 불변이다.
- 복사 파일은 승인 설계의 camera_plugin.cpp/.hpp와 LICENSE뿐이다. NASA/United States Government·Apache-2.0 헤더를 보존하고 출처/원본 해시/수정 내역을 남긴다.
- 새 패키지 `integrated_robot_camera`, class ID `integrated_robot_camera/SnapshotCameraPlugin`, C++ type `integrated_robot_camera::SnapshotCameraPlugin`. 원본 class ID를 shadowing하지 않는다.
- base header는 설치된 `mujoco_ros2_control_plugins/mujoco_ros2_control_plugins_base.hpp`를 사용한다. base interface 이외의 원본 CameraPlugin implementation에 의존하지 않는다.
- 이미지320×240, RGB-D 목표15Hz, 추론 기본10Hz/명시적 선택15Hz, 촬영/receipt300ms, TF100ms, 팔5Hz, 기존20관절·TF·명령 단일 소유권을 유지한다.
- timestamp를 현재 시각으로 바꾸지 않는다. 단일 렌더러·mjData2개·최신 pending1개, 초기화 이후 프레임별 mjData 할당 없음. disabled 카메라 렌더/readback 없음.
- 관리자 권한·시스템 ptrace/환경 설정·해상도·외부 plugin 변경 없음. LP_NUM_THREADS=2를 기본값/필수 설정으로 추가하지 않는다.
- 실제 호출 근거는 고정 base header의 update 계약과 `mujoco_system_interface.cpp:1213`이다. 원본 camera 주석의 ‘simulation thread’를 그대로 가정하지 않는다. underlay 자체의 snapshot/reset 경합이 재현되면 별도 미달로 기록하고 라이브 데이터 직접 접근으로 우회하지 않는다.
- 실패/미검증/짧은 성공을 분리한다. Gazebo 종료/bridge, PPO/MoveIt/파지/Nav2는 이번 구현의 해결 대상으로 확장하지 않는다.13.5는 전체13.4 미달 동안 재개하지 않는다.

## Review Focus

1. 렌더 보류 중 overwrite·clock rollback: 취득 데이터/선택/시각은 불변이고 이전 epoch 발행은 폐기한다 — Task1/2의 결정적 barrier 및 rollback 시험.
2. idle/busy/부분 초기화 중 cleanup·재초기화: 제출을 막고 깨운 뒤 join을 마쳐야 해제하며 중복 cleanup도 안전하다 — Task1/2의 stop/초기화 실패 시험.
3. disabled/polled/streaming 혼합과 경계 입력: pending coalescing은 한 최신 묶음이며 잘못된 index/중복 선택/비유한 시각은 거부한다 — Task1/2의 선택·검증 시험.
4. 오래된 overlay·누락/잘못된 라이브러리·backend 오타: 실제 Ch13 library 경로를 확인하고 엔진 시작 전 실패하며 fallback하지 않는다 — Task2/3/4의 실제 pluginlib probe/설치 감사 시험.
5. renderer/DDS/OS 지연과 취소 결과 미수신: 오래된 프레임을 유효화하거나 cancel ACK를 terminal로 취급하지 않는다 — Task5/6의 native 지연·고장·종료/기존 회귀.

## 파일 경계

| 생성/수정 경로 | 책임 |
|---|---|
| `Ch13/ros2_ws/src/integrated_robot_camera/{package.xml,CMakeLists.txt,LICENSE,REUSE_MANIFEST.md}` | 별도 native 패키지·라이선스·출처 |
| `.../include/integrated_robot_camera/snapshot_mailbox.hpp`, `.../src/snapshot_mailbox.cpp` | GL/ROS와 독립된 실제 mjData 두 버퍼·epoch·생명주기 |
| `.../src/snapshot_camera_plugin.{hpp,cpp}`, `.../integrated_robot_camera_plugins.xml` | 출처를 유지한 카메라 파생 구현, pluginlib 등록 |
| `.../src/camera_plugin_probe.cpp` | 실제 class 생성·library 경로 조회. 카메라 init/GL 실행 없음 |
| `.../test/test_snapshot_mailbox.cpp`, `.../test/test_snapshot_camera_plugin.cpp`, `.../test/test_plugin_loading.cpp` | 소유권·센서·동적 로딩 회귀 |
| `Ch13/ros2_ws/src/integrated_robot_description/launch/mujoco.launch.py`, `config/mujoco_snapshot_vision_plugins.yaml`, `package.xml` | 명시적 backend 선택/사전검사·기존 legacy 보존 |
| `Ch13/ros2_ws/src/integrated_robot_runtime/launch/vision_system.launch.py` | 선택값 검증과 MuJoCo launch 전달만 수행 |
| `Ch13/scripts/{run_vision_13_4.py,verify_vision_13_4.py,verify_all_13_4.py}` | backend 기록·native loaded library 감사·5패키지 검증 |
| `Ch13/tests/test_section_13_4_{launch,runner,verifier,summary}.py` | 기존 launch/runner/증거/일괄 검증 회귀 확장 |
| `Ch13/docs/{LAB_13_4_GUIDE_KO,SECTION_13_4_REPORT_KO,SECTION_13_4_REVIEW_KO,REUSE_MANIFEST}.md`, 새 evidence | 한국어 재현 절차·판정·원본 결과 |

## 실행 환경·명령 규약

실행 때 현재 작업트리/AGENTS를 다시 확인한다. 승인된 절 checkout을 유지할 수 있으면 재사용하며 임의 worktree/브랜치 전환·기존 시뮬레이터 중단을 하지 않는다. 아래는 WSL Ubuntu-24.04/bash 안의 명령이다.

```bash
cd /mnt/c/Users/Jinho/.codex/.chatgpt-projects/g-p-6ad1e56cf8f881919fe23e1ab94d2855/work/Pysical_AI_ROS2
source /opt/ros/jazzy/setup.bash
source /home/jinho/ch13_mujoco_ws/install/setup.bash
source /home/jinho/ch13_vision_13_4_venv/bin/activate
SNAPSHOT_RUN=$(python -c 'import uuid; print(uuid.uuid4())')
SNAPSHOT_BUILD=Ch13/ros2_ws/build13_4_snapshot_$SNAPSHOT_RUN
SNAPSHOT_INSTALL=Ch13/ros2_ws/install13_4_snapshot_$SNAPSHOT_RUN
SNAPSHOT_LOG=Ch13/ros2_ws/log13_4_snapshot_$SNAPSHOT_RUN
SNAPSHOT_EVIDENCE=Ch13/evidence/section_13_4/camera-ownership-$SNAPSHOT_RUN
mkdir -p "$SNAPSHOT_EVIDENCE"
```

위 경로 변수도 각 실행의 조건 기록에 남긴다. 기존 Ch13 install은 새 build의 underlay로 source하지 않는다. 단계마다 원본 로그/JUnit·종료 코드를 저장하며, 로그 끝부분 표시로 실패 코드를 숨기지 않는다. 공통 build 명령은 다음과 같다. Task1/2에서는 `--packages-select integrated_robot_camera`를 추가하고, Task4 이후에는 새 5패키지 전체를 빌드한다.

```bash
python -m colcon --log-base "$SNAPSHOT_LOG" build \
  --base-paths Ch13/ros2_ws/src --build-base "$SNAPSHOT_BUILD" \
  --install-base "$SNAPSHOT_INSTALL" --executor sequential \
  --cmake-args -DPython3_EXECUTABLE="$(command -v python)"
source "$SNAPSHOT_INSTALL/setup.bash"
```

현재 계획 단계에서는 위 명령을 실행하지 않는다. 각 시험 단계에 지정한 명령의 종료 코드0과 이름 있는 회귀의 실제 통과를 함께 확인한다.

### Task 1: 두 mjData 버퍼와 결정적 소유권 시험

**Files:** 새 패키지의 package.xml/CMakeLists.txt, snapshot_mailbox.hpp/.cpp, test_snapshot_mailbox.cpp. GL이 필요 없는 core 시험을 별도 `test_snapshot_mailbox` target으로 만든다.

**Interfaces:** namespace는 `integrated_robot_camera`. `SnapshotMailbox(const mjModel*, size_t camera_count)`는 모델을 소유하지 않는다. `ClockObservation observe_time(double sim_time)`은 metadata 락 아래 시각을 관측하고 `{uint64_t epoch; bool rollback;}`를 반환하며 역행 때 이전 pending을 폐기한다. `bool submit(const mjModel*, const mjData*, const std::vector<size_t>&, uint64_t observed_epoch)`은 stop 또는 관측 이후 epoch 변경 시 false다. `std::optional<RenderLease> wait_take()`는 stop 시 nullopt, `bool is_current(uint64_t epoch) const`는 발행 전 유효성 검사, `void reset_epoch()`는 pending/이전 시각 기준 폐기, `void request_stop()`은 제출 차단과 대기 해제다. mailbox의 copy/move는 금지한다. move-only `RenderLease`의 `data() -> const mjData*`, `stamp_seconds() -> double`, `sequence()/epoch() -> uint64_t`, `camera_indices() -> const std::vector<size_t>&`는 lease 동안 불변이다. lease 파괴로 render 사용을 해제하며 동시 consumer/동시 lease 취득은 logic_error다. 외부 모델은 mailbox보다 오래 살아야 하고 두 복사 버퍼/선택 목록은 mailbox가 소유한다.

- [ ] **1. 실패 시험 작성:** `ConsumerLeaseSurvivesProducerOverwrite`에서 작은 실제 MuJoCo 모델·mjData를 생성하고 첫 lease의 pointer/geom_xpos/time/선택을 저장한다. promise/future barrier로 consumer를 보류한 채 다른 스레드에서 frame2/3을 submit한다. 첫 lease는 불변이며 다음 lease는 frame3이어야 한다. fixture는 slide 관절1개·geom1개·카메라2개로 만들고, qpos 변경 뒤 mj_forward를 실행해 실제 시각화 상태를 바꾼다. 복사 범위가 축소된 `mjv_copyData`의 계약에 맞춰 geom_xpos/time을 검사하며 qpos 전체 복사를 가정하지 않는다. `StopWakesIdleConsumer`, `StopRejectsSubmitWhileLeaseRemainsValid`, `RejectsSecondConsumerOrOutstandingLease`도 작성한다.

  핵심 assertion은 다음과 같다. frame2/3 제출·barrier 조율은 fixture가 실제 다른 스레드에서 수행한다.

  ```cpp
  const double captured_x = first->data()->geom_xpos[0];
  EXPECT_DOUBLE_EQ(first->stamp_seconds(), 1.0);
  // producer가 time2/3, 다른 geom_xpos와 camera index1을 제출한 뒤:
  EXPECT_DOUBLE_EQ(first->data()->time, 1.0);
  EXPECT_DOUBLE_EQ(first->data()->geom_xpos[0], captured_x);
  EXPECT_EQ(first->camera_indices(), (std::vector<size_t>{0}));
  first.reset();
  auto latest = mailbox.wait_take();
  ASSERT_TRUE(latest.has_value());
  EXPECT_DOUBLE_EQ(latest->stamp_seconds(), 3.0);
  EXPECT_EQ(latest->camera_indices(), (std::vector<size_t>{1}));
  ```
- [ ] **2. RED 확인:** 새 core target의 build/test를 실행해 API 미구현으로 실패함을 보존한다. 구문/환경 오류와 요구된 소유권 실패를 구별한다. 테스트가 정의되기 전에 소유권 구현을 작성하지 않는다.
- [ ] **3. 최소 구현:** RAII mjData2개를 사전 할당하고 upstream과 같은 `mjv_copyData`로 pending만 갱신한다. 짧은 mutex에서 포인터/metadata를 교환하고 lease 동안 render를 재사용하지 않는다. observe_time은 due 판단 전에 호출하며 반환 epoch를 submit에 전달한다. 비유한/음수 시각, index 범위 초과·중복 선택·모델 포인터 불일치는 invalid_argument로 거부한다.
- [ ] **4. GREEN·경계 확인:** `RollbackDropsPendingAndInvalidatesOldLeaseEpoch`, `ResetBetweenObserveAndSubmitRejectsOldGeneration`, `SameTimeDoesNotResetEpoch`, `RejectsInvalidTimeAndCameraSelection`, `OnlyTwoDataBuffersAreReused`를 포함해 gtest를 실행한다. 렌더 보류 중 producer 완료를 barrier로 확인하며 render/join까지 mutex를 늘리지 않는다. core의 TSAN 전용 CMake 옵션 `INTEGRATED_CAMERA_ENABLE_TSAN=ON`을 별도 build에서 시험한다. 실행 제약은 UNVERIFIED로 보존하고 일반 GREEN과 혼동하지 않는다.
  실행: `"$SNAPSHOT_BUILD/integrated_robot_camera/test_snapshot_mailbox" --gtest_output=xml:"$SNAPSHOT_EVIDENCE/mailbox-green.xml"`. 모든 이름 있는 시험이 통과해야 한다. sanitizer build는 별도 prefix에서 core target만 빌드하며, 계측하지 않은 외부 MuJoCo/GL 라이브러리까지 race-free라고 주장하지 않는다.
- [ ] **5. 검토·commit:** 소유권·락 순서·두 버퍼/유계 메모리를 네이티브 자체 검토하고 `feat(ch13): add bounded camera snapshot mailbox`로 checkpoint한다.

### Task 2: 출처를 보존한 플러그인·실제 ROS/GL 계약

**Files:** snapshot_camera_plugin.hpp/.cpp, integrated_robot_camera_plugins.xml, camera_plugin_probe.cpp, 패키지 LICENSE/REUSE_MANIFEST.md, test_snapshot_camera_plugin.cpp, test_plugin_loading.cpp, Task1 CMake/package.xml.

**Interfaces:** `SnapshotCameraPlugin : MuJoCoROS2ControlPluginBase`의 원래 `init(rclcpp::Node::SharedPtr,const mjModel*,mjData*) -> bool`, `update(const mjModel*,mjData*) -> void`, `cleanup() -> void`를 유지한다. `on_reset(mjData*) -> void`는 Task1의 reset_epoch로 이전 작업을 무효화하며 라이브 데이터를 렌더하지 않는다. producer는 mailbox, worker는 RenderLease만 사용한다. `camera_plugin_probe`는 고정 class ID를 실제 `pluginlib::ClassLoader`로 createSharedInstance하고 getClassLibraryPath로 조회한 절대 library 경로 한 줄만 stdout에 출력한다. 성공0, 예외/비가용 시 비0이며 init/GL은 호출하지 않는다.

- [ ] **1. 출처·실패 시험 준비:** main agent가 고정 원본2파일을 전체 읽고 설계서 해시·LICENSE·NOTICE유무를 확인한다. 원본저작권을보존해허용된파일만Ch13으로복사하고원본해시를명세한다. 새로운CameraPlugin type으로rename하되이시점의소유권경로는아직고치지않는다. `FrameHeadersMatchAcquiredSnapshot`, `DisabledCameraNeverRenders`, `PolledRequestsCoalesceWithLatestSnapshot`, `CleanupDuringInitializationAndRender` 및 실제class등록/생성시험을작성한다.

  `FrameHeadersMatchAcquiredSnapshot`은 실제 GL에서 취득 시각1.0의 렌더를 보류하고 producer가2.0을 제출하게 한 뒤 다음을 검사한다. 둘 다 완료 시각으로 stamp를 바꾸면 실패해야 한다.

  ```cpp
  EXPECT_EQ(rgb.header.stamp, depth.header.stamp);
  EXPECT_EQ(rgb.header.stamp, info.header.stamp);
  EXPECT_EQ(rclcpp::Time(rgb.header.stamp).nanoseconds(), 1000000000LL);
  EXPECT_EQ(rgb.header.frame_id, "camera_optical_frame");
  EXPECT_EQ(rgb.width, 320u);
  EXPECT_EQ(rgb.height, 240u);
  ```
- [ ] **2. RED 확인:** 새 등록/헤더 일치/종료회귀를 실행해 빠진새기능과기존경로의실패를기록한다. 원본파생본이이미통과하는항목은baseline으로표시하고새수정의RED라고주장하지않는다.
- [ ] **3. 최소 연결:** 공유 render_pending을 worker가 직접 읽거나 지우는 경로를 제거한다. 생산자 선택/poll 요청은 metadata 락으로 보호하고 frame 선택 목록을 mailbox로 전달한다. plugin 선택 락과 mailbox 락은 동시에 보유하지 않는다. worker는 lease의 data/time/선택만으로 scene·RGB·depth·Info를 생성하고 publish 직전 epoch/stop을 검사한다. stamp를 now로 교체하지 않는다. GLContext는 worker가 생성/파괴하며 RAII 해제로 부분 초기화 실패도 안전하게 한다.
- [ ] **4. GREEN·native library 확인:** 실제GLContext를사용한센서header/해상도/부호/깊이단위시험을실행한다. GL미지원은실패또는명시적UNVERIFIED이며가짜영상으로대체하지않는다. busy종료시험은workerbarrier해제전해제가일어나지않고,해제후join이완료됨을확인한다. `cleanup`두번·실패후destructor·잘못된카메라설정·rollback직후발행폐기도검사한다. probe는새Ch13 .so를가리키고원본class도여전히가용해야한다.
  실행: `python -m colcon --log-base "$SNAPSHOT_LOG" test --build-base "$SNAPSHOT_BUILD" --install-base "$SNAPSHOT_INSTALL" --packages-select integrated_robot_camera --executor sequential`, 이후 `python -m colcon test-result --test-result-base "$SNAPSHOT_BUILD" --verbose`. 새 C++ 시험 실행 수가 0이 아니고 오류/실패0이어야 한다. 부분 초기화 시험은 실제 잘못된 모델/카메라 설정으로 실패 후 update/cleanup을 호출하고, 렌더 진행 중 stop은 core barrier 시험과 실제 GL 종료 시험으로 각각 검사한다.
- [ ] **5. 검토·commit:** 원본diff/Apache표기·복사범위·플러그인기본생성/해제·락없이렌더링을자체검토하고 `feat(ch13): add snapshot-owned MuJoCo camera plugin`으로checkpoint한다. 외부gitstatus불변도기록한다.

### Task 3: 명시적 backend와 엔진 시작 전 실패

**Files:** description/launch/mujoco.launch.py, description/config/mujoco_snapshot_vision_plugins.yaml, description/package.xml, runtime/launch/vision_system.launch.py, Ch13/tests/test_section_13_4_launch.py.

**Interfaces:** `camera_plugin_config(share, vision, backend='upstream') -> str` 확장. `probe_snapshot_plugin(expected_prefix: Path) -> dict`를mujoco.launch.py에두고, active camera package의libexec/probe를실행해library절대경로/파일존재/선택prefix내부·SHA256을검사한다. 공유되는미설치scripts를launch에서import하지않는다. launch인자 `vision_camera_backend`는upstream/snapshot만허용하며이단계기본upstream이다. vision=false는기존legacy파일을그대로쓴다.

- [ ] **1. 실패 시험:** snapshot선택의새YAML `eye_camera.type`만새class이고 native_pose/토픽/15Hz가원래와동일함을검사한다. `unknown backend`, 누락된probe/library, 다른prefixlibrary는engineaction생성전에실패해야한다. vision=false양backend는legacy와같고, Gazebo에는MuJoCo전용인자를넘기지않는시험을추가한다.

  `test_snapshot_backend_changes_only_camera_class`의 핵심 assertion:

  ```python
  assert snapshot['eye_camera']['type'] == 'integrated_robot_camera/SnapshotCameraPlugin'
  assert snapshot['native_pose'] == upstream['native_pose']
  expected = dict(upstream['eye_camera'], type=snapshot['eye_camera']['type'])
  assert snapshot['eye_camera'] == expected
  ```
- [ ] **2. RED 확인:** 실제launch entities를구성하는기존pytest방식으로새시험을실행해전달/사전검사부재를보존한다.
- [ ] **3. 최소 구현:** snapshot선택때만새packageprefix/probe를확인하고설정파일을선택한다. 결함을숨기는fallback은없다. combined launch는값검증후MuJoCo include에전달한다. `vision_camera_backend`와무관한관절/컨트롤러/TF/CameraInfo adapter는바꾸지않는다.
- [ ] **4. GREEN·실제 동적로딩 검사:** Task2의설치probe로정상prefix를검증하고다른expected_prefix를줘실제라이브러리오선택을거부하는지검사한다. 누락경로시험은빈임시prefix로수행하며외부/설치라이브러리를이동·삭제하지않는다. 기존13.2/13.3 launch·20관절·headless/rate회귀도실행한다.
  실행: `python -m pytest Ch13/tests/test_section_13_4_launch.py Ch13/tests/test_section_13_2_model.py Ch13/tests/test_section_13_2_mujoco.py -q`. 새 backend 검사와 기존 모델/launch 시험이 모두 통과해야 한다.
- [ ] **5. 검토·commit:** 설치후 launch만으로 실행가능하고 저장소scripts 경로에 의존하지 않는지 확인한 뒤 `feat(ch13): select and preflight camera backend explicitly`로checkpoint한다.

### Task 4: 5패키지·실제 loaded library를 포함한 evidence

**Files:** scripts/run_vision_13_4.py, verify_vision_13_4.py, verify_all_13_4.py, tests/test_section_13_4_runner.py, test_section_13_4_verifier.py, test_section_13_4_summary.py.

**Interfaces:** runner CLI `--vision-camera-backend upstream|snapshot`(이 단계 기본 upstream). `audit_camera_backend(process, expected_prefix: Path) -> dict`는 runner가 직접 생성한 launch PGID의 MuJoCo control process만 확인한다. `/proc/PID/maps`의 실제 새 .so 경로/해시와 초기화 class ID 로그를 사전 probe와 대조한다. 반환 키는 `class_id`, `library_path`, `library_sha256`, `native_pid`, `package_prefix`다. `required_checks(scenario, *, engine=None, camera_backend='upstream') -> set[str]`로 확장하여 engine=mujoco/backend=snapshot일 때만 `camera_backend_loaded`를 추가한다. 기존 호출·historical upstream/Gazebo 결과의 필수 검사 집합은 소급 변경하지 않는다.

- [ ] **1. 실패 시험:** 새camera .cpp를바꾸면source_snapshot해시가달라져야한다. 전체검증build/install감사에5번째패키지·XML·LICENSE·source해시·실제.so해시가있어야한다. backend미기록,다른prefix.so,소유하지않은PID는통과시키지않는다. mock의호출횟수만검사하지말고실제짧은자식과현재/probe라이브러리경로를사용한다.

  `test_snapshot_result_requires_loaded_library`의 핵심 assertion:

  ```python
  required = required_checks('tracking', engine='mujoco', camera_backend='snapshot')
  assert 'camera_backend_loaded' in required
  assert 'camera_backend_loaded' not in required_checks('tracking')
  assert 'camera_backend_loaded' not in required_checks('tracking', engine='gazebo')
  assert verdict(result_without_camera_library_audit, required) == 'FAIL'
  ```

  위 result fixture는 새로운 실행 UUID와 실제 임시 artifact 해시를 갖고, 나머지 기존 필수 검사는 모두 true여야 한다. stale UUID 때문에 우연히 실패한 시험을 loaded-library 회귀로 세지 않는다.
- [ ] **2. RED 확인:** 위누락조건과CLI전달시험을실행해현재4패키지가정과loaded-library검사부재를확인한다.
- [ ] **3. 최소 구현:** source inventory의camera디렉터리와새패키지build선택/설치감사·실행backend기록을추가한다. artifact와backend메타데이터를기존EvidenceRun의원본해시계약에포함한다. 새라이브러리감사는읽기전용이며다른PID에신호를보내지않는다. 상위일괄runner의backend/rate인자도하위명령에명시전달한다.
- [ ] **4. GREEN·설치 감사:** 새prefix에5패키지를처음부터build하고sourcepytest전체·colcon test/test-result를실행한다. venv콘솔shebang·Python/share원본바이트·C++원본해시와.so실제로드를확인한다. 원본plugin과새plugin의중복eye카메라publisher가없어야한다. 기존실패result와새UUID를섞어PASS하지않는회귀도통과해야한다.
  전체 소스 시험 명령: `python -m pytest Ch13/tests Ch13/ros2_ws/src/integrated_robot_vision/test Ch13/ros2_ws/src/integrated_robot_runtime/test -q`. 패키지 시험은 Task2 명령의 packages-select 제한을 제거해 5개 모두 실행한다. 이전254/101건을 새 실행 결과로 복사하지 말고 실제 새 개수·실패·skip을 기록한다.
- [ ] **5. 검토·commit:** 새코드체크포인트를만들고그후의native실행에는설치일치감사를첨부한다. 메시지 `test(ch13): audit five-package camera provenance and native loading`.

### Task 5: 실제 엔진 인수와 기본값 전환 판정

**Files:** 새 `Ch13/evidence/section_13_4/camera-ownership-<UUID>/`와 Task3/4의기본값·해당테스트, docs/SECTION_13_4_REPORT_KO.md. 이미존재하는evidence는수정하지않는다.

**Interfaces:** Task3의명시적backend, Task4의runner와native provenance를사용한다. engine별/scenario별/반복별별도디렉터리. 종료미확인/잔여PID면다음engine을시작하지않는다. 성능시험과build/대량pytest는동시에실행하지않는다.

- [ ] **1. baseline·비교 기록:** 고정source/설치감사후실제MuJoCo를upstream와snapshot으로각각실행한다. 같은10Hz기본·15Hz명시선택을기록하고환경/renderer를같이보존한다. driver 스레드수·기한을실패뒤몰래조정하거나안전정지후자동재활성화하지않는다.
- [ ] **2. 기하·인식 인수:** snapshot으로 static30 고유 촬영(RMS≤.03m), delay150ms+실측 카메라 운동30 고유 촬영(RMS≤.05m)을 기존 기준 그대로 검사한다. 자체 형상 cup YOLO는 기존 최소 신선 결과10/유효 cup3D5 기준이며 정적 fixture와 의미 인식을 구별한다. native RGB/depth/Info/관절/TF/loaded.so·원본 로그를 보존한다.
- [ ] **3. 추적·안전 인수:** `--scenario tracking --detector-backend color_fixture --vision-camera-backend snapshot --inference-rate-hz 10` 및15로각각독립3회실행한다. 모두기존5초·픽셀20%감소·각도.04rad/속도.1rad/s/명령5Hz·단일소유권·정상종료검사를적용한다. safety는images/tf/joints를각각실제목표/ACK후주입하고새명령중단·cancel terminal을검사한다. 하나라도미달이면그조건은FAIL이며앞선성공으로채우지않는다.
- [ ] **4. 기존 기능·전체 상태:** 실제Gazebo의geometry/yolo/tracking/safety와두엔진13.3회귀를순차실행한다. 기존GZ종료/bridge미달은별도FAIL로남기며이작업에서해당구현을수정하지않는다. GUI·실로봇·PPO이동·물리파지는UNVERIFIED다.
- [ ] **5. 기본값 판정·회귀·commit:** MuJoCo snapshot의필수국소인수·10Hz3회·기존MuJoCo/launch회귀가통과한뒤에만 vision=true경로의최종기본을snapshot으로전환한다. 15Hz미달은따로명시하고전체13.4/Gazebo성공으로승격하지않는다. 기본전환에대한기존pytest를먼저실패확인하고최소변경후전체시험·새기본값의실제MuJoCo기하/추적을다시검증한다. 국소인수미달이면upstream기본을유지하고개발중명시선택으로문서화한다. 실측판정과코드를checkpoint하며실패를고쳤다는commit제목은쓰지않는다.

### Task 6: 재현 가이드·네이티브 자체 리뷰·push

**Files:** docs/LAB_13_4_GUIDE_KO.md, SECTION_13_4_REPORT_KO.md, SECTION_13_4_REVIEW_KO.md, REUSE_MANIFEST.md, 새evidence 인덱스. 계획의체크박스는실제완료한항목만갱신한다.

**Interfaces:** Task5의고정소스·backend·반복별원본result를사용한다. 전체판정은기존fail-closed일괄검증기로산출하며historical최종실행은보존한다.

- [ ] **1. 가이드·출처 갱신:** fresh5패키지build/source/명시적backend/실제loaded library확인/단계별실습/실패복구를한국어로작성한다. 외부원본커밋/해시/라이선스·복사파일·수정점을새package와장REUSE명세에연결한다.
- [ ] **2. 결과 감사:** native시험횟수·개별PASS/FAIL/UNVERIFIED·종료경고·sanitizer제약·짧은장면한계를기록한다. 모든artifact기록크기/SHA를검증하고소스/설치/바이너리체크포인트를분리한다. summary의전체PASS를과거/다른조건성공으로만들지않는다.
- [ ] **3. 자체 리뷰·최종 회귀:** 서브에이전트없이spec↔코드/시험coverage·락/소유권·ABI/class ID·단일publisher·예외/종료를검토한다. 단위/설치전체시험을다시실행한다. 문서만작성한단계에서새native성공을주장하지않는다.
- [ ] **4. commit·push·SHA 검증:** 이전장/외부원본gitstatus불변과의도한Ch13변경만확인해절브랜치에commit한다. `git push origin HEAD:refs/heads/feat/ch13-section-13-4` 후 `git ls-remote origin refs/heads/feat/ch13-section-13-4`와로컬HEAD일치를확인한다. main/외부저장소push나force는하지않는다.
- [ ] **5. 인계:** 실제해결범위·남은미달·사용자가실행할명령·보고서/검증SHA를전달한다. 전체13.4가미달이면13.5보류를명시한다.

## 계획 자체 검토와 승인 게이트

- 설계1–4절은Task1/2의패키지·출처·native동적로딩,5–6절은Task1/2의두버퍼/lease·epoch·종료,7절은Task3/4,8절은Task4–6에대응한다.
- Review Focus5종류는각소유task의이름있는시험또는실제native인수로연결했다. 버퍼사이의copy/metadata전달은한mutex,렌더/ROS/GL/join은그밖이라는규칙이모든task에서같다.
- 국소camera수정과전체13.4판정,명시적실험과제품기본값,source시험과실제물리센서시험을분리했다. Gazebo미달을새플러그인의책임범위로확장하지않는다.
- 실행방식은네이티브로유지한다. 이계획은독립리뷰가아닌작성자자체검토다. **사용자가구현계획을검토·승인한뒤** executing-plans로Task1부터진행한다. 현재단계에서새소스복사/컴파일/시뮬레이터실행은하지않는다.
