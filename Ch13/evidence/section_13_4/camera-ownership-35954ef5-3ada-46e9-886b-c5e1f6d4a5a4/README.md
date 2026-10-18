# Camera ownership 실행 기록

실행 UUID: `35954ef5-3ada-46e9-886b-c5e1f6d4a5a4`.
시작 source HEAD: `124061f32bc6492ac42a67fe43a7bb67ed245050`.
브랜치: `feat/ch13-section-13-4`. 승인된 계획의 네이티브 실행이며 서브에이전트 없음.
외부 underlay: `mujoco_ros2_control@c261f5552edf124d1000a23fb25b6c07cadeb807` (변경 없음).

## Task1

| 검사 | 결과 / 원본 |
|---|---|
| 기존 소스 회귀 | PASS, 254건, 123.19초, `baseline-pytest.log`, exit0 |
| API 미구현 RED | 의도된 실패, 새 snapshot_mailbox.hpp 부재, `mailbox-red-build.log`, exit2 |
| 새 코어 build | PASS, `mailbox-green-build.log`, exit0 |
| 실제 mjData 소유권 시험 | PASS, 9건/실패0, `mailbox-green.log`, `mailbox-green.xml`, exit0 |
| 변경 후 소스 회귀 | PASS, 254건, 117.42초, `task1-pytest.log`, exit0 |
| TSAN 별도 build | PASS, `mailbox-tsan-build.log`, exit0 |
| TSAN 첫 실행 | 비정상 종료139, 시험 시작 전, `mailbox-tsan.log` 출력0바이트 |
| TSAN 진단 재실행 | exit1, unexpected memory mapping, `mailbox-tsan-diagnostic.log` |
| TSAN underlay+verbosity2 실행 | exit0, 9건 PASS, race warning 없음, `mailbox-tsan-diagnostic-sourced.log` |

TSAN 시작은 이 WSL 환경에서 불안정하다. 성공한 한 번의 코어 검사와 실패한 두 실행을
모두 보존한다. 시스템 정책/ASLR을 바꾸지 않았으며 외부 MuJoCo/GL은 계측하지 않았다.
플러그인·실제 카메라 엔진·종단 추적의 인수 결과는 아직 아니다.

경로는 저장소 기준이다. 일반 build/install/log suffix는
`13_4_snapshot_35954ef5-3ada-46e9-886b-c5e1f6d4a5a4`, TSAN은
`13_4_snapshot_tsan_35954ef5`다. ROS Jazzy + 고정 vendor underlay +
`/home/jinho/ch13_vision_13_4_venv`를 사용했고 기존 Ch13 overlay를 새 코어 build에
source하지 않았다. Python 기존 회귀는 기존 debug install 환경에서 실행했다.

다음 단계: 새 플러그인 구현, 실제 GL 및 동적 로딩 검증, backend 선택/설치 감사,
실제 두 엔진 인수. 전체13.4 완료나13.5 재개를 선언하지 않는다.

## Task2

- 원본 파생본 RED: 재초기화 후 readback 미도달, reset 후 과거 RGB/depth/Info 발행,
  새 class 등록 부재. `plugin-red-camera.xml`, `plugin-red-native.log`,
  `plugin-red-result.log`에 보존했다. 첫 build의 CMake export 이름 오류와 첫
  colcon test의 Ch01 탐색 오류는 환경/명령 오류이며 기능 RED로 세지 않는다.
- 원본에서도 header/깊이 단위/이미지 부호/disabled/polled/잘못된 policy 시험은
  통과했다. 새 수정으로 생긴 성과라고 주장하지 않는다.
- 최초 연결 후 혼합 정책 RED: `plugin-mixed-red.log/.xml`, 실제 readback 보류 중
  polled 요청이 streaming-only 최신 프레임에 유실되어 촬영0건(기대1건).
- 보완: 기존4인자 submit은 유지하고, 두 슬롯에 유계 retained camera 목록을
  전달하는5인자 overload를 추가했다. 아직 취득하지 않은 polled 요청만 최신
  snapshot에 병합하며 취득/reset 뒤에는 반복하지 않는다. 추가 API RED는
  `mailbox-retained-red-build.log`에 보존했다.
- 최종 native C++: **19개 gtest PASS** (core11 + 실제 GL7 + 실제 pluginlib1).
  `plugin-retained-green-{build,tests,result}.log`, `plugin-final-native.log`,
  `plugin-final-camera.xml`, `mailbox-final.xml`. colcon의22건은 등록된3개
  CTest harness까지 포함한 집계이며 별도22개의 기능 시험이라는 뜻이 아니다.
- 기존 소스 회귀: **254건 PASS /148.09초**, `task2-pytest.log`, exit0.
- 최신 코어 TSAN: build PASS, 실행 exit1 / unexpected memory mapping.
  `mailbox-final-tsan-build.log`, `mailbox-final-tsan.log`.
  최신 코드의 sanitizer 인수는 **UNVERIFIED**이며 이전9건 단일 성공으로 채우지 않는다.
- 실제 설치 probe의 경로는 `plugin-final-probe.log`, 바이너리 SHA는
  `plugin-final-binary-sha256.log`. 원본 class와 별도 class를 모두 실제 생성했다.
  `upstream-final-status.log`는0바이트(외부 원본 변경 없음)다.

scope: 실제 작은 MuJoCo 모델과 GL/DDS를 사용한 플러그인 시험이다. 통합 로봇의
종단 추적/물리 파지/두 엔진 인수를 대체하지 않는다. backend 기본값은 바꾸지 않았다.
생산자 제어 스레드는 pending만, 단일 worker는 취득 lease만 사용한다. metadata
mutex와 mailbox mutex를 중첩하지 않으며 렌더/발행/join 동안 metadata lock 없음.
서비스는 weak selection state만 캡처해 cleanup 이후 plugin 객체를 참조하지 않는다.
GLFW 전역 terminate는 호스트의 다른 창을 파괴할 수 있어 호출하지 않고, worker가
자신의 창/context/scene만 해제한다.

## Task3

- RED: `backend-red.log`, 새4건 실패 /기존5건 통과.
- GREEN: `backend-green.log`, launch/13.2 모델21건 PASS /17.14초.
  실제 설치 probe 생성·해시/경로 확인, 잘못된 prefix 거부, 없는 probe/library일 때
  native Node 생성 전 실패, Gazebo에 MuJoCo 전용 인자 미전달을 확인했다.
- 전체 기존+새 소스 회귀: `task3-pytest.log`,258건 PASS /125.20초.
- snapshot YAML은 eye_camera의 type만 변경하며 토픽·15Hz·native_pose는 동일하다.
  `vision=false`는 두 backend 모두 기존 legacy 카메라 파일을 사용한다.
  backend 기본은 upstream이며 자동 fallback이나 기본 전환은 없다.
- probe는 설치된 libexec/class loader를 실제 실행한다. launch는 저장소 scripts를
  import하지 않는다. Ch13의 완전한5패키지 fresh 설치 감사는 다음 Task4에서 수행한다.
