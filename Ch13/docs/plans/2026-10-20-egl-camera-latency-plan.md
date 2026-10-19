# EGL Camera Ownership and Latency Tracing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. 사용자 지정 네이티브 단일 작업자 방식이며 서브에이전트·독립 리뷰 에이전트를 호출하지 않는다.

**Goal:** Ch13 snapshot의 GLFW worker 호출을 제거하고 동일 촬영의 native→추론→fusion→제어 시간 예산을 검증 가능한 trace로 남긴다.

**Architecture:** EGL context/surface는 렌더 worker가 생성·사용·해제하고 display 초기화만 프로세스 수명으로 공유한다. 기존 두 슬롯/lease에 고정 크기 시각 metadata를 붙이며 진단은 별도 유계 토픽으로 내보낸다. 정확한 촬영 키·clock 검증을 통과한 trace만 오프라인으로 연결하고 제어 안전 판정과 진단 판정을 분리한다.

**Tech Stack:** ROS2 Jazzy, MuJoCo3.3.7, C++17/EGL/OpenGL, rclcpp/rclpy, Python3.12, gtest/pytest/colcon, 실제 MuJoCo/Gazebo.

**Spec:** [사용자 승인 설계](../specs/2026-10-20-egl-camera-latency-design.md). 방향 확정 후 서면 설계를 사용자 승인받았다. **현재 구현 계획 검토 대기 / 제품 수정 미착수**. 계획 작성 기준 HEAD는656bb06fe0aa0569f63d27e9b4092b4a0d436ca1이다.

## Global Constraints

- Ch13만 수정한다. sources, Ch05~Ch12, 고정 외부 checkout/설치본을 변경하지 않는다.
- ROS2 Jazzy/MuJoCo3.3.7·고정 underlay/venv·320×240·카메라 목표15Hz를 유지한다.
- 추론 기본10Hz, 명시적 선택 최대15Hz. 촬영 ROS age·수신 후 wall age300ms, 과거 TF timeout100ms, 팔 명령 최대5Hz와 기존 소각도/속도 제한을 유지한다.
- 촬영 header를 now로 바꾸거나 최신 TF로 대체하지 않는다. 자동 재시도/재활성화 금지.
- 관절·TF·액션의 단일 소유권과 terminal 결과 확인 규칙을 유지한다.
- 관리자 권한·ptrace/드라이버/해상도/렌더 스레드 환경 설정은 변경하지 않는다.
- snapshot 명시 선택과 upstream 기본값은 유지한다. 이번 범위에서 기본 승격하지 않는다.
- 실제 엔진은 순차 실행한다. 소유한 종료/잔여 검사 미확인 시 다음 엔진을 시작하지 않는다.
- 기존 실패 evidence와 이전 계획 workspace는 덮어쓰거나 삭제하지 않는다. main 병합·13.5는 하지 않는다.
- 각 task의 behavioral RED와 GREEN을 보존한다. import/빌드 설정 오타는 행동 RED와 구분한다.

## Review Focus

1. 같은 display의 다른 context 사용 중 cleanup/재init: 타인의 EGL 자원을 무효화하지 않아야 한다(Task1 peer-context 시험).
2. render lease 중 reset/overwrite: stamp와 timing이 서로 다른 촬영에서 섞이지 않아야 한다(Task2 barrier 시험).
3. clock rollback과 같은 timestamp 재사용·진단 도착 역전: 모호한 연결을 정상 latency로 합산하지 않아야 한다(Task4 ambiguous/clock 시험).
4. trace consumer 없음·상한·UTF-8/잘못된 payload: 진단 부하나 예외가 제어 경로·목표 TTL을 바꾸면 안 된다(Task2/3 bounds·fault 시험).
5. 부모 launch 정상 exit지만 실제 native/terminal 실패: trace의 성공으로 제품 실패를 덮지 않아야 한다(Task4/5 fail-closed 시험).

---

## 파일·책임 경계

새 파일은 구현 승인 뒤 생성한다. 아래 상대 경로는 저장소 루트 기준이다.
본문의 camera/vision/runtime/description 패키지 경로는 각각
Ch13/ros2_ws/src/integrated_robot_camera, integrated_robot_vision,
integrated_robot_runtime, integrated_robot_description이다(마지막 세 이름도 같은 src 아래).

| 단위 | 파일 |
|---|---|
| EGL RAII | camera 패키지 src/egl_render_context.hpp/.cpp, test/test_egl_context.cpp |
| native timing/trace | camera include/integrated_robot_camera/snapshot_mailbox.hpp, src/snapshot_mailbox.cpp, src/camera_trace.hpp/.cpp, test/test_camera_trace.cpp |
| Python 진단 계약/발행 | vision 패키지 integrated_robot_vision/trace.py, test/test_trace.py |
| 단계별 hook | 기존 object_detector.py, vision_processor.py, runtime의 tracking_support.py 및 대응 ROS 시험 |
| 수집·순수 분석 | Ch13/scripts/vision_observer_13_4.py, 새 latency_trace_13_4.py, 새 Ch13/tests/test_section_13_4_trace.py |
| 인자·실행·출처 | description/runtime/vision의 기존 launch, camera metadata/REUSE, run_vision_13_4.py, verify_all_13_4.py, 기존 runner/launch/summary 시험 |
| 인계 | 기존13.4 guide/report/review, 새 UUID evidence 및 이번 계획 전용 ledger |

새 일반 목적 tracing 프레임워크나 새 ROS interface 패키지를 만들지 않는다.
camera의 CMake source manifest는 새 cpp/hpp/test를 계속 포함해야 한다.

## 실행 준비와 공통 검증 명령

구현 시작 때 기존 절 checkout/HEAD/dirty/AGENTS를 다시 확인한다. 이 checkout을 재사용하고
다른 사용자 변경은 보존한다. 새 plan workspace는 이번 basename으로 구분한다.

새 WSL 사용자 셸에서 아래 값을 정하고 ledger에 실제 UUID/절대 경로를 기록한다.
이 명령은 계획이며 작성 단계에서는 실행하지 않는다.

```bash
source /opt/ros/jazzy/setup.bash
source /home/jinho/ch13_mujoco_ws/install/setup.bash
source /home/jinho/ch13_vision_13_4_venv/bin/activate
export CH13_ROOT="$PWD"
export CH13_EGL_RUN="$(python -c 'import uuid; print(uuid.uuid4())')"
export CH13_EGL_BUILD="$CH13_ROOT/Ch13/ros2_ws/build13_4_egl_$CH13_EGL_RUN"
export CH13_EGL_INSTALL="$CH13_ROOT/Ch13/ros2_ws/install13_4_egl_$CH13_EGL_RUN"
export CH13_EGL_LOG="$CH13_ROOT/Ch13/ros2_ws/log13_4_egl_$CH13_EGL_RUN"
export CH13_EGL_EVIDENCE="$CH13_ROOT/Ch13/evidence/section_13_4/egl-${CH13_EGL_RUN:0:8}"
export ROS_DOMAIN_ID=157
export MUJOCO_GL=egl
```

오래된 overlay를 겹쳐 source하지 않는다. 기존 외부 underlay의 고정 commit
c261f5552edf124d1000a23fb25b6c07cadeb807, venv, EUID1000, renderer/환경을 기록한다.
아래 명령은 새 build/install/log를 사용한다.
evidence의 짧은 경로가 이미 있으면 새 UUID를 만들고 덮어쓰지 않는다. 원래 전체 UUID는
metadata에 보존하며 JUnit을 Git으로 복사할 때는 짧은 파일명+원래 경로 색인을 사용한다.
MUJOCO_GL은 이 C++ EGL 선택의 근거가 아니며 실제 renderer 로그/호출을 확인한다.

```bash
python -m colcon --log-base "$CH13_EGL_LOG" build --base-paths Ch13/ros2_ws/src --build-base "$CH13_EGL_BUILD" --install-base "$CH13_EGL_INSTALL" --packages-select integrated_robot_interfaces integrated_robot_vision integrated_robot_description integrated_robot_runtime integrated_robot_camera --cmake-args -DPython3_EXECUTABLE=/home/jinho/ch13_vision_13_4_venv/bin/python
source "$CH13_EGL_INSTALL/setup.bash"
python -m pytest Ch13/tests Ch13/ros2_ws/src/integrated_robot_vision/test Ch13/ros2_ws/src/integrated_robot_runtime/test -q
python -m colcon --log-base "$CH13_EGL_LOG" test --base-paths Ch13/ros2_ws/src --build-base "$CH13_EGL_BUILD" --install-base "$CH13_EGL_INSTALL" --executor sequential
python -m colcon test-result --test-result-base "$CH13_EGL_BUILD" --verbose
python Ch13/scripts/verify_all_13_4.py --audit-install-prefix "$CH13_EGL_INSTALL"
```

Expected: build5 packages, pytest 실행수>0/전체 PASS, package 실행수>0/errors0/failures0/skips0,
실제5패키지 source/share/interpreter/C++manifest/camera+mailbox 라이브러리 감사 PASS.
새 건수를 기록하고 과거285/123을 신규 실행 건수로 전재하지 않는다.
긴 로그는 새 evidence/ledger에 저장하고 요점만 읽는다.

### Task 1: EGL 전용 worker와 자원 수명

**Files:** camera/src/egl_render_context.hpp/.cpp와 test/test_egl_context.cpp 생성.
기존 src/snapshot_camera_plugin.cpp/.hpp, test/test_snapshot_camera_plugin.cpp,
CMakeLists.txt, package.xml, REUSE_MANIFEST.md 수정.

**Interfaces:** EglRenderContext는 복사/이동 불가. worker에서
`bool initialize()`, `void close() noexcept`, `bool current() const noexcept`를 사용한다.
같은 worker의 destructor/close는 idempotent다. module의 고정 surfaceless display
초기화는 직렬화해 성공 후 재사용하며 cleanup에서 eglTerminate하지 않는다.
SnapshotCameraPlugin의 외부 init/update/cleanup/class ID는 불변이다.

- [ ] **1. 실패 시험:** 기존 CameraTest에 `WorkerUsesEglWithoutGlfw` 추가.
  시험 실행 파일에서 glfwInit 호출을 세고 false를 반환해 기존 코드도 실제 EGL로 진행하게 한다.
  실제 frame을 받은 뒤 `EXPECT_EQ(glfw_init_calls,0)`가 기존 소스에서1로 실패해야 한다.
  EGL 초기화/실패/cleanup의 호출 TID와 live context/surface 수를 actual API interposition으로 기록한다.
  `PeerContextSurvivesPluginCleanup`은 별도 worker의 실제 peer context로 GL 호출이 계속 유효함을 검사한다.

  기존 CameraTest fixture의 행동 assertion:
  ```cpp
  ASSERT_TRUE(start());
  frame(1.0);
  ASSERT_TRUE(until([&] {return !rgb.empty();}));
  EXPECT_EQ(glfw_init_calls.load(), 0);
  ```
- [ ] **2. RED 실행:** 공통 build 후
  `"$CH13_EGL_BUILD/integrated_robot_camera/test_snapshot_camera_plugin" --gtest_filter=CameraTest.WorkerUsesEglWithoutGlfw`.
  Expected: GLFW 호출1≠0의 행동 FAIL. EGL 미지원은 별도 실패로 기록하고 fake GL로 통과시키지 않는다.
- [ ] **3. 최소 구현:** 기존 init_egl_context/cleanup을 RAII로 이동해 GLFW 우선 분기·헤더·직접 링크를 제거한다.
  EGL pbuffer1×1, MuJoCo offscreen320×240, display 프로세스 수명 정책을 적용한다.
  private context/surface는 worker에서만 정리하고 mjr/mjv 해제는 current인 동안 수행한다.
  실패는 init=false, 자동 fallback/재시작 없음. namespace/class ID·토픽·두 슬롯 정책은 유지한다.
- [ ] **4. 실패 경계·GREEN:** EGL display/init/config/bind/context/surface/make-current 실패를
  각각 fresh 시험 자식에서 주입한다(프로세스별 display cache 때문에 fresh child 필요).
  각 실패에서 `init()==false`, join 완료, live private 자원0, 이중 cleanup 및 명시 재init 성공,
  `eglTerminate_calls==0`를 확인한다. 기존 busy/reset/polled/header/depth/flip/disabled 회귀도 수행한다.
  실행: `ctest --test-dir "$CH13_EGL_BUILD/integrated_robot_camera" --output-on-failure`.
  Expected: nonzero tests/zero failures, GLFW0, actual EGL renderer 증거와 worker TID 일치.
- [ ] **5. checkpoint:** 외부 status와 복사/라이선스 유지, peer context 보호를 자체 검토한다.
  task 소스/시험/REUSE만 stage하고 `fix(ch13): use worker-owned EGL camera context`로 commit.

### Task 2: lease와 일치하는 native 시각·유계 trace

**Files:** camera/src/camera_trace.hpp/.cpp, test/test_camera_trace.cpp 생성.
snapshot_mailbox.hpp/.cpp, snapshot_camera_plugin.cpp/.hpp, CMakeLists.txt/package.xml과 mailbox/GL 시험 수정.

**Interfaces:** `FrameTiming {uint64_t submit_start_ns, submit_end_ns, acquire_ns;}`.
`SnapshotMailbox(model,camera_count,bool trace_enabled=false)`로 기존 두 인자 호출을 보존한다.
`RenderLease::timing() const noexcept -> const FrameTiming&`.
`CameraTrace(node, enabled, run_id)`, `bool publish(const NativeFrameTrace&)`는 worker에서 사용한다.
NativeFrameTrace는 source_frame/capture_ns/local_epoch/native_sequence와 단계 ns를 가진다.
ROS age용 ros_now_ns는 별도 top-level 필드이며 times_ns의 CLOCK_MONOTONIC 값과 섞지 않는다.
times_ns의 native 키는 submit_start/submit_end/acquire/scene_start/render_start/render_end/
readback_end/rgb_publish_start/rgb_publish_end/depth_publish_start/depth_publish_end/
info_publish_start/info_publish_end로 고정한다.
진단 schema1은 stage=camera, clock_id=linux/CLOCK_MONOTONIC, boot_id/producer UUID/pid/tid,
event_sequence/outcome을 포함한다. enabled UUID 검증은 worker 시작 전에 한다.

- [ ] **1. 실패 시험:** mailbox barrier 시험 `AcquiredTimingSurvivesOverwriteAndReset`에서
  lease stamp1/timing1 보유 중 submit2/reset가 timing1을 바꾸지 않음을 assert한다.
  `TraceDisabledNeverPublishes`, `TraceEscapesStringsAndCapsUtf8Bytes`,
  `TraceStopsAtSessionLimit`, `TraceFailureCannotChangeFramePublication`을 추가한다.
  assert payload≤4096byte, emit≤20000건/인스턴스, QoS BEST_EFFORT/VOLATILE/depth32,
  invalid UUID는 init 실패, drop/oversize/errors는 각각 계수하고 모터/이미지 제어로 전파하지 않는다.
- [ ] **2. RED:** 공통 build와 위 C++ tests 실행. Expected: timing/API/trace 부재로 실패.
  별도 인터페이스 부재 컴파일 RED와 기존 영상 동작의 행위 RED를 구분해 저장한다.
- [ ] **3. 최소 구현:** CLOCK_MONOTONIC 시작 시각은 submit 호출 진입에서 얻고,
  복사 완료 시각은 slot publish 전 mutex 안에서 저장한다. acquire 시각도 같은 slot에 저장한다.
  control producer는 고정 metadata/카운터만 쓴다. worker에서 한 frame/camera 요약을 직렬화한다.
  키는 기존 camera.frame_name과 원 stamp, lease epoch/sequence다. 동적 문자열은 JSON escape한다.
  std_msgs 의존성을 선언하고 새 소스를 configure-time manifest에 포함한다.
- [ ] **4. GREEN:** ctest와 실제 GL readback barrier 회귀를 실행한다.
  timing의 `submit_start<=submit_end<=acquire` 및 scene/render/readback/publish 구간 순서를 확인한다.
  consumer 없는 실제 ROS 시험도 종료 기한 안에 완료해야 한다. 출력 거부가 실제 RGB-D/Info header를 바꾸지 않아야 한다.
  최종 shutdown 로그에 producer별 attempted/emitted/drop/oversize/errors를 한 번 기록한다.
  이 로그가 없으면 후속 분석의 누락 총수는 unknown이지0이 아니다.
- [ ] **5. checkpoint:** `feat(ch13): trace native snapshot stages without blocking producer`.

### Task 3: Python 추론·fusion·제어 발생 시각

**Files:** vision/integrated_robot_vision/trace.py와 test/test_trace.py 생성.
기존 object_detector.py, vision_processor.py와 detector/fusion 시험,
runtime/integrated_robot_runtime/tracking_support.py 및 test/test_tracking_ros.py 수정.

**Interfaces:** trace.py의 순수 `validate_record(value:dict)->dict`,
`decode_record(payload:str)->dict`; 유효하지 않으면 ValueError.
`TracePublisher(node,topic,*,enabled:bool,run_id:str)`,
`emit(stage,*,source_frame,capture_ns,local_epoch,times_ns,outcome,native_sequence=None,ros_now_ns=None)->bool`.
모듈 import 시 ROS publisher를 만들지 않는다. offline decoder는 ROS init 없이 사용 가능해야 한다.
emit은 잘못된 record/직렬화/publish 오류에 false와 errors 계수로 응답하며 예외를 제어로 전파하지 않는다.
constructor의 잘못된 enabled UUID는 ValueError로 초기화를 거부한다.
TracePublisher의 상수는 MAX_BYTES=4096, MAX_RECORDS=20000이며 C++과 같은 wire schema를 사용한다.
capture_ns는 원 촬영 정수 ns 또는 제어에 원 목표가 없으면 null이며 null은 join하지 않는다.
source_frame은 target의 odom header가 아니라 source_header의 optical frame이다.
ros_now_ns는 해당 경계에서 얻은 원 ROS now의 정수 ns다. 제어 trace는 lock 안에서
decision/dispatch와 함께 복사하고, 나중에 emit할 때 다시 읽은 now로 대체하지 않는다.

- [ ] **1. 실패 시험:** pure schema 시험과 실제 ROS `test_trace_keeps_capture_and_occurrence_time`,
  `test_trace_failure_does_not_renew_or_disable_target`, `test_trace_serialization_runs_outside_control_lock` 추가.
  disabled0발행, UUID 오류, UTF-8 payload4096/20000 상한, publish 예외의 국소 계수,
  monotonic clock 구현/boot ID 불일치 거부를 assert한다.
  fake clock 구간으로 발생10ns/관측100ns를 주고 emit 발생 시각이100으로 대체되지 않음을 확인한다.
  정확한 상한 assertion은 `assert TracePublisher.MAX_BYTES == 4096`,
  `assert TracePublisher.MAX_RECORDS == 20000`,
  실제 구독 수신 payload의 `assert len(payload.encode('utf-8')) <= 4096`이다.
- [ ] **2. RED:** `python -m pytest Ch13/ros2_ws/src/integrated_robot_vision/test/test_trace.py Ch13/ros2_ws/src/integrated_robot_runtime/test/test_tracking_ros.py -q`.
  Expected: 새 계약·hook 부재의 실패. 초기 환경/import 오타는 고친 뒤 행동 RED를 따로 확인한다.
- [ ] **3. 최소 구현:** 표준 json/uuid/time만 사용한다. Python clock 구현·boot ID는 초기화 때 기록한다.
  detector/fusion job 또는 기존 유계 cache의 해당 촬영 metadata에 시각을 붙인다.
  source/header/TTL/worker slot/cache 크기·검출/추적 정책은 변경하지 않는다.
  tracking은 lock 안에서 원 목표와 decision/dispatch/gate-lost 시각을 짧게 복사하고 밖에서 emit한다.
  예외·활성 상태 변경에도 미뤄 둔 trace만 유실될 수 있고 새 명령이나 TTL 갱신을 만들면 안 된다.
- [ ] **4. GREEN:** 위 시험과 detector/fusion/historical-TF/target-message 및 runtime 추적/owner 시험을 실행한다.
  시간 키는 detector: rgb_receive/slot_put/work_take/convert_start/end/inference_start/end/publish_start/end,
  fusion: rgb_receive/depth_receive/detection_receive/bundle_select/work_take/depth_start/end/tf_start/end/publish_start/end,
  tracking: target_receive/decision/dispatch 또는 gate_lost로 고정한다.
  독립 receive 순서는 강제 정렬하지 않고 각 처리 구간의 causal 순서만 검사한다.
  Expected: 모두 PASS, no fallback/auto retry/새 명령 producer 없음.
- [ ] **5. checkpoint:** `feat(ch13): record capture-linked vision and control timing`.

### Task 4: 인자 연결·오프라인 연결 감사·증거 통합

**Files:** 새 Ch13/scripts/latency_trace_13_4.py, Ch13/tests/test_section_13_4_trace.py.
기존 vision_observer_13_4.py, run_vision_13_4.py, verify_all_13_4.py;
description의 launch/mujoco.launch.py, runtime의 launch/vision_system.launch.py와 architecture.launch.py,
vision의 launch/vision.launch.py, 기존 launch/runner/summary 시험 수정.

**Interfaces:** launch trace_enabled=false/trace_run_id=''를 명시 검증해 참여 노드에 전달한다.
`materialize_controller_config(source,plugin_source=None,*,trace_options=None)->str` 확장으로
snapshot일 때만 eye_camera trace 파라미터를 임시 config에 넣는다. 외부 원본 plugin에는 전달하지 않는다.
runner CLI `--trace-enabled`는 store_true이며 새 EvidenceRun UUID를 launch trace_run_id로 사용한다.
`analyze_trace(records:list[dict],*,expected_run_id:str,require_native:bool)->dict`는 순수 offline 함수다.
observer가 저장할 `trace.jsonl` 행은 `{received_ns,record}`, 수신불가 payload는 카운터로 남긴다.
분석 반환 키는 analysis_status, segments, counts, missing_stages, target_gaps_ns,
gate_losses, errors다. segments[name]는 count/p50_ns/p95_ns/max_ns/worst_capture를 가진다.
counts는 seen/valid/malformed/unmatched/ambiguous와 dropped를 가진다.
drop 총수가 증명되지 않으면 dropped=null이며 누락 sequence에서 계산한 하한은 별도 필드로 보존한다.

- [ ] **1. 실패 시험:** `test_trace_arguments_reach_only_requested_nodes`,
  `test_ambiguous_capture_never_produces_latency`, `test_reordered_delivery_uses_producer_times`,
  `test_partial_trace_cannot_promote_native_failure` 및 native→Python decoder 교차 시험 추가.
  예: producer100→200ns/관측1000ns인 구간의 결과100ns를 assert한다.
  실제 단계 키 native_render의 assertion은
  `assert result['segments']['native_render']['p50_ns'] == 100`이다.
  같은 capture의 native epoch0/1 중복, 다른 boot/clock, 음의 구간, missing stage,
  잘못된 UUID, upper-bound/drop/총수 unknown은 유효 연결로 계산하지 않는다.
  received 순서가 역전돼도 source 발생 인과가 올바르면 같은 값임을 assert한다.
- [ ] **2. RED:** `python -m pytest Ch13/tests/test_section_13_4_trace.py Ch13/tests/test_section_13_4_launch.py Ch13/tests/test_section_13_4_runner.py Ch13/tests/test_section_13_4_summary.py -q`.
  Expected: 새 CLI/collector/analyzer 부재로 실패. 새 API의 import/setup 오류는 분리한다.
- [ ] **3. 최소 구현:** observer에 네 trace topic 구독과 최대20000건/producer 유계 수집을 추가한다.
  producer metadata는 최대16종, 세션 총 수집은80000건으로 제한한다. 초과 producer는
  새 dict 항목을 만들지 않고 집계 drop만 증가시키며, 해당 분석은 불완전으로 표시한다.
  수집기 상한 이후에도 손실을 기록하고 제어·센서 callback을 중단하지 않는다.
  join은 run_id/source_frame/capture_ns의 exact match, 중복 epoch 후보는 ambiguous,
  다른 local_epoch 숫자끼리 같음을 전제하지 않는다. no-target/null capture는 별도 상태 통계다.
  표준 quantile(p50/p95는 선형 보간)·count/max/최악 capture·missing/ambiguous/drop와
  target 갱신 간격·gate-lost 당시 age를 기록한다. 모르는 수는 unknown으로 표시한다.
  이 결과의 analysis_status는 PASS/PARTIAL/UNVERIFIED이며 native product status와 독립이다.
- [ ] **4. GREEN·증거 연결:** native C++ trace JSON을 Python decoder가 실제 읽는 계약 시험,
  전달/옵션 기본값/기존20관절·TF 회귀를 실행한다.
  trace와 요약을 EvidenceRun artifact로 등록하되 기존 required_checks나 summarize의
  native/terminal/clean_shutdown FAIL을 진단 성공으로 덮어쓰지 않는다.
  snapshot+trace의 native 분석에는 실제 EGL renderer 로그와 loaded camera/mailbox 증거가 필수다.
  upstream/Gazebo처럼 native camera trace가 없는 분석은 해당 경계를 UNVERIFIED로 둔다.
  Expected: targeted tests PASS, disabled 경로의 기존 인자·결과 계약 불변.
- [ ] **5. checkpoint:** `feat(ch13): audit end-to-end trace identity and evidence`.

### Task 5: 고정 설치본의 실제 엔진 검증·원인 판정

**Files:** 새로운 egl-짧은UUID evidence(전체 UUID는 metadata에 보존). 원래 evidence는 읽기 전용.
변경 소스는 Task1~4 checkpoint에 고정하고 시험 중에는 제품 코드를 수정하지 않는다.

**Interfaces:** Task4 runner CLI/trace.jsonl/trace_summary.json, 기존 result/cleanup/loaded-library 계약.
소유 native 종료가 명확하고 잔여가 없는 경우에만 다음 trial을 시작한다.
개별 제품 FAIL은 보존하고, 정상 정리가 확인되면 별도 trial로 다음 조건을 시험할 수 있다.
종료 미확인/잔여가 있으면 중단해 조사하며 자동 재활성화하지 않는다.

- [ ] **1. 새 고정 build:** 공통 명령으로 five-package build/pytest/colcon/test-result/설치 감사를 실행한다.
  Expected: nonzero tests/zero failures와 실제 source/share/C++manifest/.so 일치.
  C++ EGL interposition 증거를 함께 복사하고 새 source HEAD·dirty·환경을 기록한다.
- [ ] **2. static OFF/ON과 delay ON:** 각기 새 output에서 아래 명령을 순서대로 실행하고 매회 cleanup을 검토한다.
  둘 다 PASS해도 EGL 성능의 보편 보장으로 해석하지 않는다.
  `python Ch13/scripts/run_vision_13_4.py --engine mujoco --scenario static --detector-backend color_fixture --vision-camera-backend snapshot --output-dir "$CH13_EGL_EVIDENCE/static-off"`.
  다음은 같은 명령에 `--trace-enabled`, 새 static-on 경로; delay-on은 scenario=delay,
  `--processing-delay-s .15`와 trace를 명시한다.
  Expected acceptance: static30/RMS≤.03m, 실제 카메라 motion+150ms delay30/RMS≤.05m,
  EGL renderer·단일 TF/관절/카메라 소유권·정상 종료. 미달이면 FAIL 그대로 기록한다.
- [ ] **3. tracking10/15Hz 각3회:** 명령은
  `python Ch13/scripts/run_vision_13_4.py --engine mujoco --scenario tracking --detector-backend color_fixture --vision-camera-backend snapshot --trace-enabled --inference-rate-hz 10 --output-dir "$CH13_EGL_EVIDENCE/m10a"`.
  새 m10b/m10c/m15a/m15b/m15c 경로에서 해당 rate를 명시한다.
  Expected acceptance: 각5초 연속/픽셀20% 감소/각도≤.04rad·측정 속도≤.1rad/s·명령≤5Hz,
  안전/단일 소유권/정상 종료. 모든 trace의 연결·계측 성공 여부는 별도 판정한다.
- [ ] **4. 기존 기능·고장 주입:** MuJoCo/Gazebo 각각 cup YOLO와 images/tf/joints safety,
  Gazebo static/delay/tracking 및 두 엔진13.3 legacy를 각각 새 output에서 순차 실행한다.
  YOLO는 기존 고정 로컬 yolov8n.pt/SHA·자체 cup을 사용하며 다운로드·학습·fallback 없음.
  safety 예: 위 runner의 scenario=safety와 `--fault joints`, 실제 목표/ACK 후 주입을 확인한다.
  Expected acceptance: 기존 recognition·fault·terminal·native exit 기준 불변; engine별 실패는 개별 FAIL.
  미실행·중도 중단은 UNVERIFIED이며 다른 실행의 성공으로 채우지 않는다.
- [ ] **5. 원인 판정·checkpoint:** 정확히 연결된 frame의 native wait/render/readback,
  inference/TF/fusion/제어 수신 간격, 최악 age를 대조한다.
  trace 부족이면 내부 원인 미확정, 충분하면 병목과 근거 ID를 기술한다.
  실제 terminal/엔진 종료 실패는 별도 미해결로 유지한다.
  `test(ch13): retain EGL native trials and latency evidence`로 증거를 commit한다.
  이 task는 관측·증거 수행 완료와 제품 acceptance PASS를 혼동하지 않는다.

### Task 6: 회귀·자체 리뷰·한글 인계·push

**Files:** LAB_13_4_GUIDE_KO.md, SECTION_13_4_REPORT_KO.md, SECTION_13_4_REVIEW_KO.md,
SECTION_13_4_ROOT_CAUSE_ANALYSIS_KO.md, REUSE_MANIFEST.md 및 새 evidence INDEX/ledger 보존본.
실측이 끝난 뒤 driver·외부소스·새 액션 정책을 함께 고치지 않는다.

**Interfaces:** 기존 whole summary와 trace analysis_status를 분리해 표시한다.
현재 plan ledger는 이전 계획 ledger와 구분해 보존한다. 독립 리뷰 부재를 명시한다.

- [ ] **1. 최종 회귀:** 공통 pytest/colcon/test-result/설치 감사 재실행.
  Expected: 실제 새 로그/JUnit의 nonzero tests/zero errors/failures/skips와 설치 일치.
  원인 미해결인 native 결과는 이 테스트 성공으로 바꾸지 않는다.
- [ ] **2. 자체 리뷰:** Review Focus5개를 소스·실제 EGL 호출·새 trace/실측과 대조한다.
  important finding은 별도 RED→GREEN 수정 패스로 검증한다.
  API 또는 소스가 바뀌면 영향받은 native 시험은 새 고정 소스로 다시 수행해야 한다.
  아직 중요 미해결이면 clean/release-ready/13.5 가능으로 선언하지 않는다.
- [ ] **3. 문서:** 설치·명시적 snapshot/trace 옵션·trace 해석·미검증·실패 및 변경 출처를 갱신한다.
  EGL 수정의 확정 효과와 시간 예산의 계측 결과, 액션/Gazebo 후속 과제를 분리한다.
  artifact 경로/size/SHA를 새 무결성 audit로 재확인하고 JSON 원본을 수정하지 않는다.
- [ ] **4. commit/push:** Ch13의 실제 해당 변경만 stage, diff --check와 장별 경계를 확인한다.
  `docs(ch13): explain EGL tracing results and remaining failures`로 commit하고
  `git push origin HEAD:refs/heads/feat/ch13-section-13-4`.
  Expected: non-force feature push 성공, local HEAD == ls-remote의 절 브랜치 SHA.
  main/PR/다른 장은 변경하지 않는다. 실패하면 성공이라 보고하지 않는다.
- [ ] **5. 인계:** 실제 성공/실패·미검증·중요 미해결과 원격 SHA, 작업 중 판단·비용을 설명한다.
  다음 액션/Gazebo 구조 수정이 필요하면 새 근거와 범위를 제시하고 별도 설계를 받는다.

## 계획 자체 검토

설계1~3→Task1, 설계4~5→Task2/3, 설계6→Task4, 설계7→Task1~5,
설계8→Task5/6으로 대응한다. 작성자가 공통 값·signature·stage 키·기본값과
Review Focus5개를 소유 task의 시험에 대조했다. placeholder·로컬 링크·shell 예시를
검토했고, shell 예시의 잘못된 연결 문자를 제거했다. ROS age용 ros_now_ns를
monotonic times_ns와 별도 필드로 명시하는 설명도 설계서에 보충했다.
작성 단계에서 제품 테스트/엔진 실행은 하지 않으며, 구현 계획 검토와 승인 후 네이티브 실행한다.
