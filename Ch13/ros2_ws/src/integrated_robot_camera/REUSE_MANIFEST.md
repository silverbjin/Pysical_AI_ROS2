# integrated_robot_camera 재사용 명세

원본: [ros-controls/mujoco_ros2_control](https://github.com/ros-controls/mujoco_ros2_control/tree/c261f5552edf124d1000a23fb25b6c07cadeb807),
고정 커밋 `c261f5552edf124d1000a23fb25b6c07cadeb807`.
원본 checkout은 수정하거나 재빌드하지 않는다.

| 원본 파일 | Ch13 경로 | 원본 SHA-256 |
|---|---|---|
| mujoco_ros2_control_plugins/src/camera_plugin.cpp | src/snapshot_camera_plugin.cpp | 70c79ed5deac3cec663c1d2cd1ee917c029d2f1562f6f3a6b33513ab4a43418d |
| mujoco_ros2_control_plugins/src/camera_plugin.hpp | src/snapshot_camera_plugin.hpp | e9b1f72e4f9cef107ec038863eece71cdd78f7afadcbfe73f1e390f66dd2b368 |
| LICENSE | LICENSE | 10df721a4406adc5fc3024b9cefc6f62345dda19a28b7d842cc16ee470c6c198 |

원본 NASA/United States Government 저작권·Apache-2.0 헤더를 보존하고 LICENSE
원문을 포함했다. 복사 시 원본 저장소 깊이2까지 NOTICE 파일은 없었다.
base interface는 복사하지 않고 underlay에서 include/link한다. 원본 구현 library를
새 플러그인의 구현으로 링크하지 않는다.

변경: 별도 namespace/class/class ID, 두 mjData mailbox 기반 렌더 소유권,
snapshot 시각/epoch/선택 전달, worker 소유 GL 및 종료/재초기화 경로.
streaming 업데이트가 아직 취득하지 않은 polled 요청을 지우지 않도록 두 슬롯의
유계 retained-index 목록으로 요청을 보존한다. 취득/reset 뒤에는 반복하지 않는다.
이미지·depth 변환과 CameraInfo 계산은 원본에서 파생된다. CameraInfo R=0 계약은
유지하며 기존 Ch13 adapter가 별도로 보정한다.

snapshot_mailbox.hpp/.cpp, probe와 새 테스트는 Ch13 작성 코드다. test의
mjr_readPixels interposition은 실제 native readback 전의 결정적 barrier이며
가짜 센서 영상이나 제품 테스트 전용 API를 추가하지 않는다.

2026-10-20 EGL 경로: 원본 camera_plugin의 EGL config/context 코드를
별도 egl_render_context.hpp/.cpp로 정리했다. 원본 NASA/US Government
Apache-2.0 표기를 새 파일에도 보존한다. GLFW worker 경로를 제거하며
context/surface는 worker 소유, 공유 display 연결은 프로세스 수명으로 유지한다.
per-camera cleanup의 eglTerminate는 다른 사용자를 무효화할 수 있어 호출하지 않는다.
egl_call_audit.hpp와 새 EGL 시험은 테스트 실행 파일의 실제 API 관측/실패 주입이며
제품에 시험 전용 override나 가짜 렌더러를 추가하지 않는다.

camera_trace.hpp/.cpp와 FrameTiming 계측은 Ch13 신규 작성 코드다.
CLOCK_MONOTONIC metadata는 기존 두 slot에 붙이며 producer는 JSON/ROS/file 작업을 하지 않는다.
선택 진단은 worker에서 BEST_EFFORT/VOLATILE depth32, 최대4096byte/20000attempt로 제한한다.
