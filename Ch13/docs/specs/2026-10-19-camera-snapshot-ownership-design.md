# 13.4 MuJoCo 카메라 snapshot 소유권 설계

작성일: 2026-10-19. 상태: **사용자 설계서 승인 / 구현 계획 검토 단계 / 새 플러그인 미구현**.
사용자는 일반 권한 진단·구조 검토 후, 외부 원본을 유지하는 Ch13 전용 복사본의
설계서 작성을 승인했다. 설계서 작성 승인을 구현·의존성 변경 승인으로 확대하지 않는다.
설계서 승인 후 구현 계획을 작성하고, 계획 검토와 네이티브 실행 방식 선택을 거친다.
사용자는 이 설계서 검토 요청에 대해 승인했으며 실행 방식은 기존 네이티브 모드를
유지한다. 구현 계획은 별도 검토 대상이다.

## 1. 목적과 범위

13.4 독자가 실제 eye-in-hand RGB-D의 촬영 시각과 대응하는 물리 snapshot으로
3D/TF를 계산할 수 있게 한다. 한 프레임을 렌더링하는 동안 물리 스레드가 그 프레임의
상태를 덮어쓰지 못하게 하는 것이 이 변경의 목적이다. 지연 원인을 모두 해결하거나
hard realtime을 보장한다는 설계가 아니다.

범위는 Ch13 내부의 별도 CameraPlugin과 그 선택·검증에 한정한다. 외부 checkout,
Ch05–Ch12, synced sources, 시스템 권한/ptrace 정책은 변경하지 않는다. 원본 카메라
플러그인의 안전하지 않은 공유 경로를 ROS 후처리로 숨기거나 timestamp를 현재 시각으로
바꾸지 않는다. Gazebo 종료/bridge 문제, CPU 렌더 자원 프로파일, 제어 계산 작업자 분리는
별도 과제다. PPO/MoveIt/물리 파지/Nav2/13.5 구현은 범위 밖이다.

## 2. 관찰 사실과 미확정 원인

- 원본 `camera_plugin.cpp:91–121`: update는 data_mutex 아래 pending flag와
  `mj_camera_data_`를 갱신한다.
- 같은 파일 `update_loop:505–534` 부근: condition 대기 후 mutex를 풀고
  `update_cameras()`를 호출한다.
- 같은 파일 `update_cameras:550–575` 부근: 같은 camera pending flag를 읽고 지우며,
  같은 mjData의 time/scene을 렌더링에 사용한다. 생산자와 공유하는 상태를 동일 mutex로
  보호하지 않는 소스 경로가 있다. 정확한 고정 파일 해시는 아래 출처 절에 있다.
- 실제 MuJoCo 10/15Hz 추적 모두 목표 신선도 미달로 중단했다. LP_NUM_THREADS=2도
  MuJoCo에서는1목표 뒤 LOST였다. 이 측정으로 데이터 경쟁이 모든 지연의 원인이라고
  증명한 것은 아니다. 데이터 소유권 결함 수정과 종단 처리량 판정은 분리한다.
- Gazebo에서는 llvmpipe 렌더 스레드2/exec 조건의 단일 시험이5.2초·15명령·정상 종료를
  통과했다. 이것을 MuJoCo 수정의 증거 또는 전체13.4 인수 PASS로 합치지 않는다.

## 3. 대안과 선택 근거

| 대안 | 이점 | 한계/판정 |
|---|---|---|
| Ch13 전용 불변 snapshot 플러그인 | 실제 렌더 데이터와 시각의 소유권을 직접 보장; 외부 원본 불변 | C++ 패키지·출처 관리·새 native 검증 필요. **권장하며 이 설계의 대상** |
| 원본 mutex를 렌더 전체 동안 유지 | 코드 차이가 작음 | 렌더 지연이 물리/제어 스레드를 막을 수 있어 채택하지 않음 |
| ROS worker/스레드 수만 조정 | 새 native 패키지 없이 지연을 줄일 가능성 | 공유 native snapshot 경쟁을 복구하지 못해 대체 해결책으로 채택하지 않음 |

원본 라이브러리 교체/덮어쓰기를 하지 않는다. 같은 plugin class ID로 shadowing하지 않고
Ch13의 명시적 class ID를 사용한다. 따라서 baseline과 수정본을 혼동하지 않는다.

## 4. 패키지·출처·빌드 경계

새 패키지: `Ch13/ros2_ws/src/integrated_robot_camera` (ament_cmake).
새 plugin ID: `integrated_robot_camera/SnapshotCameraPlugin`.
C++ type: `integrated_robot_camera::SnapshotCameraPlugin`.
base type은 고정 외부 패키지의
`mujoco_ros2_control_plugins::MuJoCoROS2ControlPluginBase`를 사용한다.

복사 예정 원본은 ros-controls/mujoco_ros2_control의 다음 파일뿐이다.
기준 커밋: `c261f5552edf124d1000a23fb25b6c07cadeb807`.
출처: https://github.com/ros-controls/mujoco_ros2_control/tree/c261f5552edf124d1000a23fb25b6c07cadeb807

| 원본 경로 | SHA-256 |
|---|---|
| mujoco_ros2_control_plugins/src/camera_plugin.cpp | 70c79ed5deac3cec663c1d2cd1ee917c029d2f1562f6f3a6b33513ab4a43418d |
| mujoco_ros2_control_plugins/src/camera_plugin.hpp | e9b1f72e4f9cef107ec038863eece71cdd78f7afadcbfe73f1e390f66dd2b368 |
| LICENSE | 10df721a4406adc5fc3024b9cefc6f62345dda19a28b7d842cc16ee470c6c198 |

기존 NASA/United States Government 저작권 및 Apache-2.0 헤더를 보존하고 Apache
라이선스 원문을 동봉한다. 원본에 존재하는 추가 NOTICE 유무를 복사 시 재확인하고,
새 출처 명세에는 원본 경로·커밋·해시·변경점을 기재한다. 원본 기여를 Ch13 신규 작성물로
바꾸어 표기하지 않는다. base header와 관련 없는 플러그인은 복사하지 않는다.

의존성은 고정된 mujoco_vendor, mujoco_ros2_control_plugins의 exported base interface,
rclcpp/pluginlib/sensor_msgs/std_srvs, GLFW/OpenGL EGL이다. base interface를 링크하되
원본 CameraPlugin implementation을 새 class의 구현으로 재사용하지 않는다.
현재 외부 underlay의 MuJoCo/ROS ABI와 정확히 일치해야 한다. 컴파일러/링크 경고와
TinyXML2–FastDDS 로딩 충돌 여부를 검증하고, 필요하지 않은 원본 CMake 옵션을
무조건 복제하지 않는다. 설치/런타임 경로가 새 Ch13 prefix인지 감사한다.

## 5. 핵심 소유권: 두 mjData 버퍼와 한 최신 대기 슬롯

초기화 때 모델에 맞는 mjData 두 개를 할당한다. 생산자 스레드가 쓸 수 있는 pending
버퍼 하나와 렌더 스레드가 독점하는 render 버퍼 하나다. 무제한 프레임 큐나 프레임별
mjData 할당은 만들지 않는다.

2026-10-19 계획 작성 시 호출 경로를 추가 확인했다. 고정 원본 base interface와
`mujoco_system_interface.cpp:1213`에서 `update()`는 제어 스레드의 `control_data`
snapshot을 전달받는다. 따라서 이전의 ‘물리 스레드/live mjData’ 표현을 생산자
제어 스레드로 교정한다. `pre_step()`이나 라이브 물리 데이터 직접 접근으로 옮기지 않는다.

1. 생산자 update는 해당 호출에 제공된 안정된 control_data snapshot에서만 복사한다.
   짧은 metadata mutex 아래 **pending 버퍼에만** 복사하고, 그 데이터의 simulation
   time, frame sequence, 선택 카메라 목록을 함께 갱신한다. 이미 대기 중이면 최신
   pending 전체 묶음으로 교체한다. render 버퍼에는 접근하지 않는다.
2. 렌더 스레드는 condition 대기에서 깨어나 metadata mutex 아래 pending/render
   포인터와 해당 시각·sequence·카메라 목록을 한 묶음으로 교환한다. pending 유무를
   지운 뒤 mutex를 풀고 render 버퍼만 읽는다.
3. 렌더 스레드는 단 하나다. 다음 교환은 이전 프레임의 scene 생성·RGB/depth readback·
   publish가 끝난 뒤에만 수행한다. 따라서 이전 render 버퍼가 pending 쪽으로 돌아갈
   때 그 버퍼의 렌더 독자는 없다. 생산자는 소비자가 현재 읽는 버퍼를 덮어쓸 수 없다.
4. RGB, depth, CameraInfo는 소비자가 취득한 같은 frame metadata의 timestamp를
   사용한다. 종료 시각/발행 시각으로 stamp를 갱신하지 않는다. 한 pass 도중 새 pending이
   생겨도 현재 렌더의 stamp나 카메라 선택은 바뀌지 않는다.

카메라 모델/정적 설정은 초기화 뒤 불변이다. polled 요청과 streaming due 상태는
metadata mutex로 보호하고, render에서 직접 공유 pending flag를 읽거나 지우지 않는다.
카메라 선택 목록의 두 버퍼도 초기화 때 최대 camera count 용량을 확보한다. 원본의
동일 카메라 요청 병합 의미는 유지하며, polled 요청마다 별도 프레임을 보장한다고
새롭게 주장하지 않는다. disabled 카메라는 render/readback하지 않는다.

mutex는 OpenGL 호출·렌더링·ROS publish·worker join 동안 보유하지 않는다. 생산자
스레드에서 render 완료를 기다리지 않는다. 같은 mutex를 중첩 획득하는 새 경로를
만들지 않는다. 이 규칙을 pointer identity/일시 정지 barrier가 있는 결정적 시험으로
검증하며, 단순한 실행 시간 우연에 의존하는 sleep 기반 경쟁 시험만으로 대체하지 않는다.

## 6. 초기화·종료·시계 변경

- 두 mjData/카메라 metadata를 사용 가능하게 만든 뒤에만 producer를 활성화한다.
  초기화 실패 후 잘못된 포인터를 update에서 읽지 않게 한다.
- stop은 새 snapshot 제출을 막고 대기 condition을 깨운다. metadata mutex를 놓은
  상태에서 worker 종료를 기다린 뒤, worker가 사용하던 mjData/scene/GL 자원을 해제한다.
  cleanup 중 update/trigger가 새 작업을 재개하지 못하게 한다.
- GLFW/EGL 생성·활성화·파괴와 scene/readback은 렌더 스레드가 일관되게 소유한다.
  driver 내부의 무한 정지를 강제로 안전 중단할 수 있다고 보장하지 않는다. 실제 종료가
  기한을 넘으면 기존 runner가 FAIL로 기록하며 detach나 자원 선해제로 숨기지 않는다.
- 시간이 역행하면 pending을 이전 epoch 상태로 발행하지 않는다. 취득한 render job은
  해당 epoch와 함께 끝내되 발행 직전 epoch가 바뀌었으면 폐기한다. detector/fusion의
  기존 ClockGate도 그대로 동작한다. ROS clock과 mjData time이 다르면 현재 시각으로
  덮어쓰지 않고 진단한다. update는 streaming due 판단 전에 mjData time 역행을
  확인해 epoch를 증가시키고 pending과 이전 발행 주기 기준을 초기화한다. 시간이 다시
  이전 값에 도달할 때까지 입력이 멎는 방식으로 reset을 처리하지 않는다.

## 7. 외부 계약과 선택

이미지320×240, 무왜곡 pinhole, 현재 FOV·near/far, meters depth, optical frame,
토픽 이름, RGB/depth 촬영 정합, 카메라 장착 TF, 명령 소유자는 그대로 유지한다.
native CameraInfo R=0을 보정하는 기존 adapter는 이번 소유권 수정과 분리해 유지한다.
PPO/MoveIt/그리퍼 기능이나 새로운 정답 이미지·정답 TF를 주입하지 않는다.

명시적 `vision_camera_backend` 선택값은 `upstream`과 `snapshot` 두 개다. 잘못된 값,
누락된 새 plugin library는 engine 시작 전에 오류를 낸다. 조용한 upstream fallback은 없다.
13.4 vision=true에서 수정본을 최종 기본값으로 전환하는 것은 실제 인수 시험 통과 뒤의
제품 변경이다. vision=false의 기존13.2/13.3 카메라 설정/의미는 유지한다.
비교 결과에는 선택 backend와 실제 loaded class ID/설치 경로를 기록한다. 같은 eye_camera
키의 type만 선택하며 원본/새 카메라가 동시에 같은 토픽을 발행하지 못하게 한다.

LP_NUM_THREADS=2는 현재 Gazebo 단일 성공의 실험 조건일 뿐이다. 이번 플러그인의
필수/기본 설정으로 몰래 넣지 않는다. 해상도·RGB-D 목표15Hz·추론 기본10Hz/선택15Hz·
촬영/receipt300ms·TF100ms·팔5Hz를 바꾸지 않는다. 실제 달성률과 drop은 그대로 기록한다.

## 8. 검증 기준

실패 재현 시험을 먼저 만든다. 다음 항목을 단위 성공, native 실행, 물리 결과로 구분한다.

- 실제 두 mjData를 사용하는 결정적 생산자/소비자 경합: 렌더를 보류한 동안 생산자가
  pending을 여러 번 갱신해도 render buffer/state/time은 불변이어야 한다. 취득 시 선택
  목록과 stamp가 같은 sequence여야 하며 최신 pending 하나만 남아야 한다.
- idle/busy 종료·초기화 실패·disabled/polled/streaming·clock rollback 시험. ROS 메시지
  세 종류의 header가 취득 snapshot과 일치해야 한다.
- 가능하면 새 소유권 코드의 ThreadSanitizer 검사. 시스템/driver/WSL 제약으로 실행하지
  못하면 UNVERIFIED와 원인을 기록하며 sanitizer 미실행을 race-free PASS로 쓰지 않는다.
- Ch13의 새5패키지만 새 prefix에 빌드·설치하고 기존 전체 테스트와 새 C++ 회귀를 실행한다.
  source inventory/설치 감사/일괄 검증기의 고정4패키지 가정도 새 패키지를 포함하게 한다.
- 실제 MuJoCo에서 static30고유 촬영, 150ms 인공 지연+실측 카메라 운동30고유 촬영과
  기존 RMS 기준, 의미 컵 YOLO, 관절/TF/명령 단일 소유권을 확인한다. 렌더는 실제 엔진
  RGB-D이며 native 데이터를 정답 토픽으로 대체하지 않는다.
- 10/15Hz 각각의 실제 연속 추적, 이미지/TF/관절 상실, 취소 terminal 및 정상 종료를
  검사한다. 5초 추적 성공 주장은 기존 각도/속도/5Hz/픽셀 오차 감소 기준을 모두 통과한
  새 실행에만 붙인다. 선택한 최종 실행 조건의 연속 추적은 독립3회 모두 통과해야 한다.
- Gazebo와13.3 회귀를 별도로 실행한다. Gazebo SIGTERM/bridge crash가 남으면 새
  MuJoCo 플러그인 성공만으로13.4 전체 또는13.5 준비 완료를 선언하지 않는다.

특정 소스 체크포인트·환경·backend·실행조건을 고정한 새 evidence만 최종 인수에 쓴다.
고장으로 정지한 trial을 재활성화해 이어 붙이지 않는다. 미실행/실패/짧은 단일 성공을
구분하고 한국어 가이드·보고서·REUSE 명세를 갱신한다. commit/push는 기존13.4 절
브랜치에서 수행하고 원격 SHA를 확인한다. main 병합/외부 저장소 push는 하지 않는다.

## 9. 설계 검토 항목과 다음 단계

작성자 자체 검토: 범위는 카메라 snapshot 소유권 하나로 제한했다. 원본 잠금 확장을
렌더 전체에 적용하는 대안은 배제했고, 두 버퍼의 교환·stamp·선택 목록·종료·epoch
소유권을 명시했다. 라이선스/ABI/성능·sanitizer 한계를 분리했으며 기존 안전 기준을
완화하지 않았다. 이것은 독립 리뷰가 아닌 네이티브 자체 검토다.

사용자 검토 후 이 설계서가 승인되면 구현 계획을 작성한다. 구현 계획의 별도 검토와
네이티브 실행 선택 이후에만 소스 복사/새 패키지/launch 기본값 변경을 시작한다.
