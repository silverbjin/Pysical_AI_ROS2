# 13.5 실행 원장

구현 시작: `a077ff2b15145e58fca8319595215d0db41cf905`, 브랜치 `feat/ch13-section-13-5`.
작업 범위: 사용자 승인 상세 설계·구현 계획. 네이티브 단일 작업자.
아래 기록은 초기 구현 시험이며 G1~G5 실제 엔진 인수 완료가 아니다.

## G0

- 기존 설치 감사: `python Ch13/scripts/verify_all_13_4.py --audit-install-prefix Ch13/ros2_ws/install13_4_completion_f8c0bed5-cdac-43d8-81ff-84ab88360cdb`.
- 결과: 기존 6패키지 소스/설치 byte 감사 성공. 원본 JSON: `g0-install-audit.json`, stderr: `g0-install-audit.stderr`.
- 기존 소스 시험: `python -m pytest Ch13/tests Ch13/ros2_ws/src/integrated_robot_runtime/test Ch13/ros2_ws/src/integrated_robot_vision/test -q`.
- 결과: **374 passed, 224.38초**, `g0-pytest.log`.
- 원격 조회: 일반 sandbox의 네트워크 연결 실패 뒤 허용된 네트워크 조회로 재확인했다. 동명 13.5 원격 브랜치 없음. main은 `e83fe949553d9a2217c274c0bab23bf8f0713241`. 원격 변경은 하지 않았다.

## Task 1

- RED: `python -m pytest Ch13/ros2_ws/src/integrated_robot_navigation/test -q`.
- 최초 `task1-red.log`: 3 failed/9 fixture errors. 누락 샘플 모듈과 신규 IDL 때문에 실패했다. 모델 계약 시험을 더하고 fixture 부재를 시험 본문에서 드러내도록 고쳤다.
- 재확인 `task1-red-confirmed.log`: **15 failed**, 새 샘플/모델/IDL 부재. 무관한 의존성 실패를 의도한 RED로 세지 않았다.
- 순수 코어 GREEN: 같은 명령에서 `test_samples.py test_model.py` 선택, **12 passed, 3.23초**, `task1-core-green.log`.
- 빌드 명령: `python /usr/bin/colcon --log-base <log13_5_UUID> build --base-paths Ch13/ros2_ws/src --build-base <build13_5_UUID> --install-base <install13_5_UUID> --executor sequential --cmake-args -DPython3_EXECUTABLE=<venv/python>`.
- 기존 ROS/외부 MuJoCo underlay와 지정 venv만 source한다. 이전 장·기존 13.4 overlay를 새 빌드의 의존성으로 사용하지 않는다.
- 전용 build/install/log 접미사는 이 실행 UUID와 같다. `task1-build.log`에 실제 결과를 보존한다. 신규 센서 패키지는 아직 작성 전이므로 이 단계는 7패키지 빌드다.
- 빌드 결과: **7 packages finished, 6분52초**. 기존 제어기 deprecation 경고 외 빌드 실패 없음.
- 전체 소스 회귀: 기존 세 시험 경로+신규 navigation/test, **389 passed, 202.34초**, `task1-all-source.log`.
- colcon 시험: `--packages-select integrated_robot_navigation integrated_robot_interfaces`, test-result **15 tests / 0 errors / 0 failures / 0 skipped**, `task1-package.log`.
- 새 설치본 감사: 기존 6패키지 감사+신규 모듈이 실제 새 prefix에서 로드되는지 및 Python byte 일치를 검사해 통과했다. `task1-install-audit.json`에 모듈·기존 .so 경로와 소스 SHA256를 보존한다.
- 이 시점에는 엔진을 기동하지 않았다. 실제 crawl/Nav2 성공을 주장하지 않는다.

## 환경·결정

- WSL은 일반 사용자 jinho/uid1000로 실행한다. sandbox WSL 접근 거절에만 도구 실행 허용을 사용했으며 sudo/관리자 권한을 사용하지 않았다.
- 기존 `/etc/wsl.conf`의 알 수 없는 키 경고를 관측했다. 범위 밖 설정을 수정하지 않았다.
- Windows→WSL 중첩 인용 명령에서 증거 경로 변수가 사라진 실행은 permission denied로 중단됐다. 같은 환경을 별도 shell 파일에서 읽으면 올바른 경로임을 확인해 이후 plan-local 실행 파일을 사용한다. 이 실행 오류를 제품 시험 FAIL/PASS로 계산하지 않는다.
- 기존 제어기 빌드의 deprecated API 경고는 원본 로그에 남기고 새 기능 때문에 관련 없는 소스를 변경하지 않는다.
- 커밋 시 `.git/index.lock` 때문에 실패했다. Windows/WSL의 Git 프로세스·열린 핸들이 없고, 0바이트 잠금의 시각이 16분 넘게 변하지 않았음을 확인했다. 삭제하지 않고 `.git/index.lock.stale-85670137-e73c-4c72-bcb2-0c73e755088b`로 보존해 정상 Git 동작을 복구했다. 실패한 커밋 뒤 자동 완료 원장에 같은 BASE/HEAD가 들어간 항목은 미완료로 정정하고 실제 커밋 뒤 재시험한다.
- pytest 원본 실패 로그에는 프레임워크가 출력한 줄 끝 공백이 있다. 원본 증거를 정리해 바꾸지 않고 보존한다. 소스·문서의 whitespace 검사는 raw evidence를 제외한 별도 검사로 적용한다.

## Task 2

- 시작 기준/Task 1 완료 커밋: `01ad4986cf740673dd8452c111b589dde4805a97`.
- RED: `python -m pytest Ch13/ros2_ws/src/integrated_robot_navigation/test/test_leg_kinematics.py Ch13/ros2_ws/src/integrated_robot_navigation/test/test_support.py Ch13/ros2_ws/src/integrated_robot_navigation/test/test_center_of_mass.py -q`, **15 failed**, `task2-red.log`.
- 최초 GREEN: navigation/test 전체 **30 passed**, `task2-green.log`. 전진 기구학은 별도 MuJoCo native 모델의 8자세×4발과 대조했다. 이는 물리 step/ROS/보행 시험이 아닌 오프라인 FK 교차검사다.
- 자체 검토에서 실제 thigh 상한 4rad와 atan2 주값 범위 차이를 발견했다. q=(0,3.8,0.4)의 유효 자세가 IK에서 거절되는 것을 `task2-angle-wrap-red.log`로 재현했다.
- 최소 수정: 원래 관절 한계 안의 2π 동등 해를 열거하고 직전 자세에 가까운 해를 선택한다. 작업 공간·관절 한계를 clipping해 통과시키지 않는다.
- 수정 GREEN: 전체 navigation/test **31 passed, 3.96초**, `task2-angle-wrap-green.log`.
- 수정 전 패키지 결과 `task2-package.log`와 소스 실행 `task2-all-source.log`는 최종 수정본 증거로 재사용하지 않는다. 수정 후 고정 소스로 `task2-fixed-*`에 재빌드·시험·감사를 수행한다.
- 수정 후 전체 소스 회귀: **405 passed, 202.55초**, `task2-fixed-all-source.log`.
- 수정 후 패키지 시험: **31 tests / 0 errors / 0 failures / 0 skipped**, `task2-fixed-package.log`. 새 설치본 byte 감사도 통과했으며 `task2-fixed-install-audit.json`에 해시를 보존한다.

## Task 3

- 시작 기준: `ba05b4896922e66f2c5abff06e133e5b26cdb7e8`. profile/footprint 최초 RED **9 failed**, `task3-red.log`.
- 독립 오프라인 검사 `task3-native-geometry-probe.json`: 원래 URDF와 MJCF 각각에서 base_link/네 thigh_link 침투 약0.020m. 렌더링·물리 step·ROS 실행은 하지 않았다.
- 교정 판단: 기존 기본값을 유지하는 Xacro 선택 인수 `hip_mount_y=0.13`을 추가한다. navigation 전용 발 y는±0.18m이며 이전 기본 발 y=±0.15m다. 새 MJCF도 같은 hip origin에서 생성한다. 비인접 충돌 쌍을 제외하거나 collision 크기를 줄이지 않는다.
- 선택 인수 시험: `task3-mount-red.log`에서 실제 미반영 실패→`task3-mount-green.log`의 기본 모델 보존/선택 모델 및 기구학 **8 passed**.
- profile은 오프라인 상태로만 생성한다. G1 검증 기록은 엔진/모델/물리/config hash, 필수 검사와 관측·액션·소스·설치·종료 artifact 해시가 모두 필요하다. 별도 ready 플래그만으로 통과하지 않는다.
- footprint는 허용 gait/arm 오차/roll·pitch 구간 전체의 삼각함수 극값과 보수적 행렬 구간을 사용한다. 몇 자세만 샘플링한 크기가 아니다. 원래 URDF collision과 더 큰 MJCF capsule 경계를 함께 포함한다.
- `task3-green.log`: 42 passed/1 failed. cos(π/2)의 부동소수 잔여가 경계0을 제외하는 문제를 확인해 trig 구간에 반올림 여유와 바깥 방향 반올림을 추가했다.
- `task3-roundoff-green.log`: **43 passed, 14.37초**. 준비 CLI 부재 RED는 `task3-cli-red.log`에 보존한다. 새 출력 생성·기존 출력 덮어쓰기 거절을 실제 명령으로 시험한다.
- 최초 구간 경계의 앞쪽 0.720643m는 접근 후보 상한0.65m와 맞지 않아 `task3-interval-refinement-red.log`로 과대 추정을 재현했다. 연속 구간을 최대0.10rad로 나눈 전체 합집합을 배치 계산하고, 실제 native 형상24자세의 독립 투영과5cm 여유 포함을 대조했다. `task3-interval-refinement-green.log` **5 passed**. 몇 점만 샘플링해 경계를 줄인 것이 아니다.
- 안전 설정 약화(여유·age·기울기·속도)를 허용하던 준비 API는 `task3-safety-limits-red.log`의 **4 failed**로 재현했다. 설정 상·하한 검사를 추가한 뒤 `task3-refined-green.log` **49 passed, 18.16초**.
- 수정 후 전체 소스 회귀: `task3-refined-all-source.log` **423 passed, 198.97초**. 패키지 시험: `task3-refined-package.log` **49 tests / 0 errors / 0 failures / 0 skipped**.
- `task3-refined-install-audit.json`에서 실제 설치 모듈·기존6패키지·신규 config/share bytes 일치를 확인했다. 준비 CLI는 설치본에서 실행했다.
- 새 `task3-refined-offline-profile`은 앞쪽0.579451m/뒤쪽-0.572826m/좌우±0.427560m, inflation_radius0.770118m다. 원래의 더 큰 `offline-profile`도 보존한다. 두 출력 모두 **offline**, G1 증거 없음, 이동 허용 불가다.
- 명목 수납 자세에서 URDF와 MJCF 각각401개 비인접 형상 쌍을 검사했다. 허용 gait 구간의 모든 자세가 자기 충돌 없이 동작한다는 실제 보행 보증은 아니며, G1/G2 실측이 남아 있다.

## Task 4 — navigation 센서·장면·선택 launch

- 시작 기준: `e1331bf5ff363037b7c371a7837b2a3c0049d8fa`. 소유한 중단 프로세스가 없음을 확인하고 재개했다. 기존 13.4 교육 문서40723바이트는 수정·stage하지 않았다.
- RED: `task4-core-red.log`에서 snapshot/normalization 헤더 부재, `task4-contact-wire-red.log`에서 예상 밖 접촉 필드 부재를 재현했다. 별도 미빌드 prefix의 의존성 오류는 feature RED로 세지 않는다.
- 구현: 독립 모델 clone·전체 `mj_copyData` 2슬롯·단일 consumer lease·최신 대기 프레임 덮어쓰기·stop 발행 경계·worker join. 카메라/EGL worker 또는 물리 live 데이터에 쓰지 않는다. reset/clock rollback은 재시작 전까지 차단한다.
- 버전 진단: Python 오프라인 MuJoCo는3.3.7, 실제 ROS C++ vendor는 **3.12.0/header3012000**이었다. `mj_ray` 추가 normal 인수에서 컴파일 실패한 원본은 `task4-core-first-build.log`에 보존한다. underlay/driver는 바꾸지 않았고 정확한 버전의 공개 API로 컴파일했다. 실제 플러그인 시험에서 header/library 모두3012000을 확인했다.
- 실행기 오류: `task4-core-vendor-test.log`는 colcon 탐색 범위 누락으로 Ch01의 기존 인코딩 진단이 나왔다. 소유한 시험기 PID1266에만 SIGINT를 보내고 `--base-paths Ch13/ros2_ws/src`로 교정했다. 시뮬레이터 종료 성공으로 세지 않는다. ROS 시험 콜백의 명시 타입 누락과 C++ Time 변환 오류도 원본 build log에 보존했다.
- 실제 ROS plugin class 부재 RED는 `task4-plugin-load-red-test.log`, 이후 GREEN은 `task4-plugin-time-test.log`다. fixture의 물리 kernel에서 발 하중 합/중력 IMU/원래 world 벽 ray·source 상태 불변, 실제 ROS header·발행·reset 차단·worker stop을 검사했다.
- Gazebo 관측기는 모든 로봇 collision에 `ContactSensorData`를 요청하고 실제 ECM 관성/세계 pose로 CoM을 계산한다. 빈 접촉 tick도 발행한다. fixed joint 결합 후의 실제 SDF collision 이름으로 매핑한다. 센서 core 부재 RED→ECM GREEN은 `task4-gz-observer-*`에 있다. 이는 Gazebo 전체 로봇 실행 정확도 인수는 아니다.
- Gazebo 힘은 세계 좌표의 알려진 평지 지지 하중만 정규화한다. pair 미러링의 collision 순서와 원래 힘 방향을 동일시하지 않으며, 발/ground 명시 매핑·힘 쌍 검증·중복 거절을 사용한다. 경사면/일반 접촉 힘 추정을 주장하지 않는다. native G1 정적 체중 검사는 여전히 필요하다.
- 장면 RED→GREEN: `task4-scene-red.log`, `task4-contact-map-red.log`, `task4-scenes-contacts-green.log`. 실제 MuJoCo parser와 Gazebo SDF 변환으로 검사했다. 평지·pedestal/컵·벽/우회 장애물과 같은 점유 지도를 생성하며 root 강제 이동/외력 plugin을 추가하지 않는다. RGB-D는320×240/15Hz 그대로다.
- exact scene launch·변조 hash RED→GREEN: `task4-launch-red.log` / `task4-scene-launch-first.log` **16 passed**. 실제 생성 URDF/SDF를 선택하며 navigation=false의 기존 경로를 유지한다. Gazebo controller 파일은 기존 긴 경로 문제 때문에 내용 hash 기반의 짧은 `/tmp` 복사본을 사용하고 bundle과 bytes 일치를 검사한다.
- 결합 시험: `task4-gz-join-red.log`의 신규4실패→`task4-gz-join-green.log` **11 passed**. 같은 native 촬영의 접촉/발 위치를 결합하고, 중복 수신으로 원래 wall 나이를 갱신하지 않는다. ROS/wall 각각200ms 및 clock reset 영구 차단을 확인했다.
- 최종 build: `python /usr/bin/colcon --log-base <log13_5_UUID> build --base-paths Ch13/ros2_ws/src --build-base <build13_5_UUID> --install-base <install13_5_UUID> --packages-select integrated_robot_description integrated_robot_navigation_sensors integrated_robot_navigation --executor sequential --cmake-args -DPython3_EXECUTABLE=<venv/python>`; `task4-fixed-build.log`, 성공.
- 최종 package: 같은 prefix에서 `colcon test --base-paths Ch13/ros2_ws/src --packages-select integrated_robot_navigation_sensors integrated_robot_navigation --executor sequential`, 이후 `colcon test-result --test-result-base <build13_5_UUID> --verbose`. **85 tests / 0 errors / 0 failures / 0 skipped**, `task4-fixed-package.log`. 구성은 Python70 + C++ 실제10 + CTest wrapper5이며85개 실제 물리 시험이라는 뜻이 아니다.
- 최종 전체 source: `python -m pytest Ch13/tests Ch13/ros2_ws/src/integrated_robot_runtime/test Ch13/ros2_ws/src/integrated_robot_vision/test Ch13/ros2_ws/src/integrated_robot_navigation/test -q`, **444 passed /257.47초**, `task4-all-source.log`.
- 설치 감사: `task4-fixed-install-audit.json`. 기존6패키지 + navigation + navigation_sensors의 실제 경로/bytes/빌드 소스 manifest를 확인했다. `.so` SHA와 실제 pluginlib probe의 header/runtime 버전, `gz plugin --info --plugin <실제 설치 .so>`의4개 System 인터페이스 등록을 기록했다.
- **미검증:** 전체 ROS 엔진 G1/G2, 실제 Gazebo 접촉·scan 정확도/자기 충돌 활성화, crawl 이동, Nav2, 정상 전체 엔진 종료는 아직 실행하지 않았다. 위 kernel/ROS/ECM/등록 시험을 종단 인수 통과로 세지 않는다.

## Task 5 — 평면 투영·이동 게이트

- 시작 기준: Task4 완료 커밋 `5d3c137a08776516642b9c4e1de27df4d90e47b2`. 커밋 후 CTest5 target/실제10 gtest 및 navigation70 시험 재확인 기록은 `task4-commit-gate.log`다.
- RED 명령: `python -m pytest Ch13/ros2_ws/src/integrated_robot_navigation/test/test_projection.py Ch13/ros2_ws/src/integrated_robot_navigation/test/test_motion_guard.py -q`, 누락 기능 **13 failed**, `task5-core-red.log`.
- 첫 구현의 ModelContract 필드명 오류 `.foot_links`는 `task5-core-first.log`의3실패로 확인하고 기존 계약 `.feet`만 사용하도록 수정했다. `task5-core-green.log` **13 passed**.
- 투영은 원본6D pose/twist/촬영·수신 시각을 바꾸지 않는다. 별도 `nav_base` z/roll/pitch0과 그 프레임의 실제 planar twist를 계산한다. `/odom`은 구독만 하고 `/navigation/odom` 및 `odom→nav_base`만 발행한다.
- 실제 DDS wrapper 부재는 `task5-ros-red.log`, offline profile 실제 서비스 거절을 포함한 부재는 `task5-ros-admission-red.log`에서 확인했다. 새 구현은 짧은 수신 실행기와 독립 monotonic watchdog으로 원본 raw 및 각 관측의 나이를 검사한다. 미래 센서는 clock이 따라올 때까지 최초 receipt를 보존해 대기시킨다.
- 헤더 없는 Twist의 RESET 이전 패킷은 동일 host DDS SYSTEM source timestamp cutoff로 거절한다. 엔진 epoch와 명령 generation은 별도이며, RESET은 관측·명령 cache를 비우고 HOLD로 돌아갈 뿐 CRAWL을 자동 허용하지 않는다.
- `task5-ros-first.log` **6 passed**: 실제 DDS·ROS clock pause에서 smoother 계속 발행/raw 중단, 중복 publisher, carry 이탈, scan 만료, 이전 generation, 실제 offline profile 거절. **양성 통신 시험은 외부 native-evidence admission만 stub**한다. controller·물리 보행이나 native G1 통과를 주장하지 않는다. 별도 unstubbed 서비스 시험은 실제 profile validator를 호출해 거절을 확인한다.
- 추가 RED3는 `task5-boundaries-red.log`: 실제 DDS용 투영 Node 미노출, dict 명령의 KeyError, 최종0 발행 후에도 ready=true 상태가 남는 문제. Node 경계를 노출하고 형식을 검사하며 종료 시 STOP/not-ready를 설정해 `task5-boundaries-green.log` **22 passed**로 확인했다. STOPPED는 guard가 증명하지 않는다.
- 실제 소유자 교체 RED: `task5-owner-replacement-red.log`. raw publisher를 파괴·재생성해 수가1로 돌아오면 출력이 계속(.006,.01)이었다. CRAWL 동안10개 입력/명령 stream의 실제 DDS endpoint GID도 고정해 교체 시 fault·0·명시적 재무장을 요구하도록 교정했다. `task5-owner-identity-green.log` **23 passed /26.03초**.
- 최종 build: 같은 전용 prefix에서 `colcon build --base-paths Ch13/ros2_ws/src --packages-select integrated_robot_navigation`; `task5-fixed-build.log`, 성공.
- 최종 package: 같은 prefix에서 `colcon test --base-paths Ch13/ros2_ws/src --packages-select integrated_robot_navigation --executor sequential`, `test-result --test-result-base <build13_5_UUID> --verbose`. `task5-fixed-package.log`: **108 tests/0 errors/0 failures/0 skipped**. Python93 및 이전 고정 C++10+CTest wrapper5 집계이며108개 실제 엔진 인수가 아니다.
- `task5-fixed-install-audit.json`의8패키지 소스/설치 bytes·센서 build manifest/library hash·실제 등록 감사 통과. fixed-topic DDS 시험 프로세스가 서로 다른 producer로 보이지 않도록 package 시험과 전체 source 시험을 같은 domain159에서 **순차** 실행했다.
- 최종 전체 source 명령은 Task4와 같은4개 pytest 경로다. `task5-fixed-all-source.log`: **467 passed /260.61초**.
- **미검증:** 실측 접촉 기반 crawl 및 G1/G2, 실제 Nav2 접근·취소, 전체 엔진 정상 종료와 최종13.3/13.4 실제 엔진 회귀는 후속 작업이다. 이 단계는 native 배포 완료가 아니다.

## Task 6 — 관측 기반 crawl kernel·lifecycle 다리 소유자

- 시작 기준 `25ba8531f16bb020e5d664df79710b38638c62b4`. Task5 commit gate93 통과는 `task5-commit-gate.log`에 보존했다.
- `test_gait.py`/실제 DDS lifecycle 시험을 먼저 작성했다. 부재·초기 경계 실패는 `task6-gait-red.log`, `task6-gait-boundaries-red.log`, `task6-lifecycle-red.log`다. 첫 kernel11, 공유 수신기/기존 DDS22, lifecycle6 통과는 각각 `task6-gait-first.log`, `task6-shared-receiver-first.log`, `task6-lifecycle-first.log`에 기록했다.
- 확대 시험 `task6-gait-envelope-red.log`: **4 failed/15 passed**. 0명령인데 다음 swing 진행, 현재 지지 밖에서 몸체 목표 발행, 최대 전·후진 중 CoM 여유 부족을 재현했다. 0명령은 현재 발 착지·정지 대기로 바꾸고 현재 지지 검사를 선행했다. `task6-pause-support-green.log` 관련6 통과.
- `task6-com-unit-probe.json`은 수정 전 코드 SHA가 포함된 **ideal-unit-only** 진단이다. 전진 첫 swing 여유0.01530→0.009970m, 후진 RR에서0.02204→0.009922m로 감소했다. 몸통 이동=전체 CoM 이동이라는 근사가 고정 지지 발의 관절·질량 변화를 누락했다. 전체 IK/URDF 질량으로 후보 CoM을 계산하고 제한 구간 내 유계 탐색을 사용했다. 측정 여유0.01m를 완화하지 않았다. `task6-kinematic-com-first.log`: **19 passed/20.19초**.
- 시계 정지/양쪽 시계 역행, 명시적 STOP 후 비영 명령 재개 금지와 inactive 진단 보존도 추가했다. `task6-final-boundaries-red.log`: **1 failed/26 passed**. deactivate가 직전 `clock paused`를 지우는 결함을 실제 DDS에서 확인하고 inactive 상태에도 fault를 보존하도록 수정했다.
- 최초 촬영/수신 나이·미래 inbox를 복제하지 않기 위해 Task5 수신기를 `observations.py`로 추출했다. 기존 motion_guard 실제 DDS도 같은 설치본/전체 source 회귀 대상이다.
- `task6-fixed-build.log` 성공. `task6-fixed-package.log`: **141 tests/0 errors/0 failures/0 skipped** (navigation126+기존 C++10/CTest wrapper5). `task6-fixed-install-audit.json`: 8패키지 설치 bytes·센서 plugin 출처/실제 등록 감사 통과. 전체 source 회귀 결과는 실행 종료 후 별도 기록한다.
- ideal-feedback fixture는 목표에 정확히 반응하는 수학/상태 전이 시험이며 native 물리 성공 증거가 아니다. 별도 무응답 시험은 계획 CoM만으로 발을 들지 못하게 한다. **G1/G2·실제 보행/전체 종료는 아직 미검증**이다.
- 최종 전체 source: `python -m pytest Ch13/tests Ch13/ros2_ws/src/integrated_robot_runtime/test Ch13/ros2_ws/src/integrated_robot_vision/test Ch13/ros2_ws/src/integrated_robot_navigation/test -q`. `task6-fixed-all-source.log`: **500 passed/337.63초**. 검증 뒤 runtime 변경 없이 문서만 보완하고 Task6를 커밋한다.
